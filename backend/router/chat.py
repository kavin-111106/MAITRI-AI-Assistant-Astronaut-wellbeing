from fastapi import APIRouter, Depends, HTTPException, status, Request
from ..database import session_object, Astronaut, Conversation
from ..oauth2 import get_current_user
from ..chat_service import ChatService
from ..rag_service import chat_with_rag
from ..models import ChatRequest, ChatResponse
from ..rate_limiter import limiter
from ..config import settings
import logging

logger = logging.getLogger("maitri.chat")
router = APIRouter(prefix="/api/v1/chat", tags=["Chat"])


@router.post("/send", response_model=ChatResponse)
@limiter.limit("20/minute")
async def send_message(
    request: Request,
    chat_request: ChatRequest,
    db: session_object,
    current_user: Astronaut = Depends(get_current_user),
):
    try:
        # ── 1. Get or create the active conversation ───────────────────────
        conversation = await ChatService.get_or_create_conversation(db, current_user.id)

        # ── 2. Persist the user's message ─────────────────────────────────
        await ChatService.save_message(
            db=db,
            conversation_id=conversation.id,
            astronaut_id=current_user.id,
            role="user",
            content=chat_request.message,
            message_type=chat_request.message_type,
            metadata=chat_request.metadata,
        )

        # ── 3. Load recent history to give the LLM conversational context ─
        history_rows = await ChatService.get_conversation_history(
            db,
            conversation.id,
            limit=settings.conversation_history_limit,
        )
        # Convert to plain dicts for the LLM, excluding the message we just saved
        # (chat_with_rag appends the current user message itself)
        messages_for_llm = [
            {"role": msg.role, "content": msg.content}
            for msg in history_rows
            if not (msg.role == "user" and msg.content == chat_request.message
                    and msg == history_rows[-1])
        ]

        # ── 4. RAG-augmented generation ────────────────────────────────────
        rag_result = await chat_with_rag(
            db=db,
            user_message=chat_request.message,
            conversation_history=messages_for_llm,
            top_k=2
        )
        ai_response = rag_result["response"]

        # ── 5. Persist the assistant reply ─────────────────────────────────
        await ChatService.save_message(
            db=db,
            conversation_id=conversation.id,
            astronaut_id=current_user.id,
            role="assistant",
            content=ai_response,
            metadata={
                "rag_sources": rag_result["sources"],
                "timing": rag_result["timing"],
            },
        )

        logger.info(
            f"Message processed — astronaut:{current_user.id} "
            f"conv:{conversation.id} "
            f"total:{rag_result['timing']['total_ms']}ms "
            f"sources:{len(rag_result['sources'])}"
        )

        return ChatResponse(
            response=ai_response,
            conversation_id=conversation.id,
            sources=rag_result["sources"],
            timing=rag_result["timing"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error processing message for astronaut {current_user.id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your message",
        )


@router.post("/new-conversation")
async def new_conversation(
    db: session_object,
    current_user: Astronaut = Depends(get_current_user),
    title: str | None = None,
):
    """Explicitly start a fresh conversation thread."""
    conversation = await ChatService.create_new_conversation(db, current_user.id, title=title)
    return {
        "conversation_id": conversation.id,
        "title": conversation.title,
        "created_at": conversation.created_at,
    }


@router.get("/history")
async def get_chat_history(
    conversation_id: int,
    db: session_object,
    current_user: Astronaut = Depends(get_current_user),
):
    conversation = await db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    if conversation.astronaut_id != current_user.id:
        logger.warning(
            f"Astronaut {current_user.id} tried to access conversation "
            f"{conversation_id} owned by {conversation.astronaut_id}"
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    messages = await ChatService.get_conversation_history(db, conversation_id)
    return {
        "conversation_id": conversation_id,
        "messages": [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "message_type": msg.message_type,
                "metadata": msg.message_metadata,
                "created_at": msg.created_at,
            }
            for msg in messages
        ],
    }


@router.get("/conversations")
async def list_all_conversations(
    db: session_object,
    current_user: Astronaut = Depends(get_current_user),
):
    conversations = await ChatService.get_all_conversations(db, current_user.id)
    return {
        "total": len(conversations),
        "conversations": [
            {
                "id": conv.id,
                "title": conv.title,
                "created_at": conv.created_at,
                "updated_at": conv.updated_at,
            }
            for conv in conversations
        ],
    }


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: int,
    db: session_object,
    current_user: Astronaut = Depends(get_current_user),
):
    deleted = await ChatService.delete_conversation(db, conversation_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")


@router.get("/search")
async def search_conversations(
    keyword: str,
    db: session_object,
    current_user: Astronaut = Depends(get_current_user),
):
    messages = await ChatService.search_past_conversations(db, current_user.id, keyword)
    logger.info(f"Astronaut {current_user.id} searched '{keyword}', found {len(messages)} results")
    return {
        "keyword": keyword,
        "found": len(messages),
        "messages": [
            {
                "id": msg.id,
                "content": msg.content,
                "conversation_id": msg.conversation_id,
                "created_at": msg.created_at,
            }
            for msg in messages
        ],
    }