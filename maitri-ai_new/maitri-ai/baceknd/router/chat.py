from fastapi import APIRouter,Depends
from ..database import session_object,Astronaut
from ..oauth2 import get_current_user
from ..chat_service import ChatService
from ..models import ChatRequest

router = APIRouter(tags=['Chat'])

@router.post("/send")
async def send_message(
    request: ChatRequest,
    db: session_object,
    current_user: Astronaut = Depends(get_current_user)  
):
  
    conversation = await ChatService.get_or_create_conversation(db, current_user.id)

    await ChatService.save_message(
        db=db,
        conversation_id=conversation.id,
        astronaut_id=current_user.id,
        role='user',  
        content=request.message,
        message_type=request.message_type,
        metadata=request.metadata  
    )

    history = await ChatService.get_conversation_history(db, conversation.id, limit=20)
    
    messages_for_ai = [
        {"role": msg.role, "content": msg.content}
        for msg in history
    ]
    
    ai_response = "I'm here to help! How are you feeling today?"
    
    await ChatService.save_message(
        db=db,
        conversation_id=conversation.id,
        astronaut_id=current_user.id,
        role='assistant',  
        content=ai_response
    )
    
    return {
        "response": ai_response,
        "conversation_id": conversation.id
    }


@router.get("/history")
async def get_chat_history(
    conversation_id: int,
    db: session_object,
    current_user: Astronaut = Depends(get_current_user)
):

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
                "created_at": msg.created_at
            }
            for msg in messages
        ]
    }


@router.get("/conversations")
async def list_all_conversations(
    db: session_object,
    current_user: Astronaut = Depends(get_current_user)
):

    conversations = await ChatService.get_all_conversations(db, current_user.id)
    
    return {
        "total": len(conversations),
        "conversations": [
            {
                "id": conv.id,
                "title": conv.title,
                "created_at": conv.created_at,
                "updated_at": conv.updated_at
            }
            for conv in conversations
        ]
    }


@router.get("/search")
async def search_conversations(
    keyword: str,
    db: session_object,
    current_user: Astronaut = Depends(get_current_user)
):

    messages = await ChatService.search_past_conversations(db, current_user.id, keyword)
    
    return {
        "keyword": keyword,
        "found": len(messages),
        "messages": [
            {
                "id": msg.id,
                "content": msg.content,
                "conversation_id": msg.conversation_id,
                "created_at": msg.created_at
            }
            for msg in messages
        ]
    }