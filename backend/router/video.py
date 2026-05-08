# video_router.py
import logging
import time
from fastapi import APIRouter, Depends, File, Request, UploadFile, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from ..video_detection import analyze_video_upload
from ..database import Astronaut, session_object
from ..oauth2 import get_current_user
from ..rate_limiter import limiter
from ..chat_service import ChatService
from ..rag_service import chat_with_rag
from ..config import settings
from groq import Groq
from ..models import VideoDetectionResponse

logger = logging.getLogger("maitri.video_router")
router = APIRouter(prefix="/api/v1/video", tags=["Video Detection"])


@router.post("/detect", response_model=VideoDetectionResponse)
@limiter.limit("10/minute")
async def detect_video_health_signals(
    request: Request,
    file: UploadFile = File(...),
    current_user: Astronaut = Depends(get_current_user),
):
    result = await analyze_video_upload(file=file, astronaut_id=current_user.id)
    logger.info(
        "Video detection complete astronaut:%s severity:%s",
        current_user.id,
        result["risk"]["severity"],
    )
    return result


@router.post("/detect-and-chat")
@limiter.limit("10/minute")
async def detect_video_and_get_llm_response(
    request: Request,
    db:session_object,
    file: UploadFile = File(...),
    current_user: Astronaut = Depends(get_current_user),
):

    logger.info("detect_video_and_get_llm_response called for astronaut:%s", current_user.id)
    # ── Step 1: Analyze Facial Emotions ──
    try:
        video_analysis = await analyze_video_upload(file=file, astronaut_id=current_user.id)
    except Exception as e:
        logger.error(f"Video analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Video analysis failed: {str(e)}")

    # Extract dominant emotion and summary for context
    dominant_emotion = video_analysis.get("analysis", {}).get("dominant_emotion") or "unknown"
    emotion_dist = video_analysis.get("analysis", {}).get("emotion_distribution", {})
    
    # Build a text summary of the video emotional state
    emotion_summary_parts = []
    for emotion, data in emotion_dist.items():
        if data.get("percentage", 0) > 5:
            emotion_summary_parts.append(f"{emotion} ({data['percentage']}%)")
    
    emotional_state_text = ", ".join(emotion_summary_parts) if emotion_summary_parts else "neutral"

    # ── Step 2: Get or Create active Chat Session ──
    try:
        conversation = await ChatService.get_or_create_conversation(db, current_user.id)
    except Exception as e:
        logger.error(f"Failed to get/create conversation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chat service error")

    # Save the video analysis as a system-context message
    video_msg_metadata = {
        "video_severity": video_analysis.get("risk", {}).get("severity", "none"),
        "video_risk_score": video_analysis.get("risk", {}).get("risk_score", 0.0),
        "dominant_emotion": dominant_emotion,
        "emotion_distribution": emotion_dist,
        "is_video_input": True
    }
    
    # ── Step 3: Save User Video Message ──
    try:
        await ChatService.save_message(
            db=db,
            conversation_id=conversation.id,
            astronaut_id=current_user.id,
            role="user",
            content=f"[Video Emotional State: {emotional_state_text}]",
            message_type="video_analysis",
            metadata=video_msg_metadata
        )
    except Exception as e:
        logger.error(f"Failed to save video message: {e}", exc_info=True)
        # Non-fatal: continue even if save fails

    # ── Step 4: Build Conversation History ──
    try:
        history_rows = await ChatService.get_conversation_history(
            db, conversation.id, limit=settings.conversation_history_limit
        )
        
        history_list = [
            {"role": msg.role, "content": msg.content} 
            for msg in reversed(history_rows)
        ]
    except Exception as e:
        logger.error(f"Failed to load conversation history: {e}", exc_info=True)
        history_list = []

    # Inject video stress context into the most recent message
    stress_context = (
        f"\n[System Video Diagnostic Input: The user's facial expression analysis shows "
        f"dominant emotion '{(dominant_emotion or 'unknown').upper()}' with stress severity "
        f"'{video_msg_metadata['video_severity'].upper()}' and risk score "
        f"{video_msg_metadata['video_risk_score']}. "
        f"Emotional distribution: {emotional_state_text}. "
        f"Please adjust your counseling tone to match their visual emotional baseline compassionately.]"
    )
    
    if len(history_list) > 0:
        history_list[-1]["content"] += stress_context

    # ── Step 5: Run RAG Pipeline ──
    try:
        logger.info("starting groq call")
        rag_response = await chat_with_rag(
            db=db,
            user_message="I've shared a video of my current emotional state. Can you help me process what I'm feeling?",
            conversation_history=history_list,
            top_k=settings.rag_top_k
        )
        logger.info("groq call completed")
    except Exception as e:
        logger.error(f"RAG chat failed: {e}", exc_info=True)
        # Return a fallback response so the user isn't left hanging
        return {
            "assistant_response": "I received your video check-in. I noticed some signals in your facial expressions, but I'm having trouble generating a full response right now. Please try again or type out how you're feeling.",
            "conversation_id": conversation.id,
            "video_analysis": video_analysis,
            "sources": []
        }

    # ── Step 6: Save AI Response ──
    saved_ai_msg = None
    try:
        saved_ai_msg = await ChatService.save_message(
            db=db,
            conversation_id=conversation.id,
            astronaut_id=current_user.id,
            role="assistant",
            content=rag_response["response"],
            message_type="text",
            metadata={"sources": rag_response.get("sources", [])}
        )
    except Exception as e:
        logger.error(f"Failed to save AI response: {e}", exc_info=True)
        # Non-fatal: still return the response to the user

    # ── Step 7: Update Conversation Timestamp ──
    try:
        if saved_ai_msg:
            await db.refresh(conversation)
            conversation.updated_at = saved_ai_msg.created_at
            db.add(conversation)
            await db.commit()
    except Exception as e:
        logger.error(f"Failed to update conversation timestamp: {e}", exc_info=True)
        await db.rollback()

    # ── Step 8: Return Response Package ──
    return {
        "assistant_response": rag_response["response"],
        "conversation_id": conversation.id,
        "video_analysis": video_analysis,
        "sources": rag_response.get("sources", [])
    }