import logging
import time
from fastapi import APIRouter, Depends, File, Request, UploadFile, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from ..audio_detection import analyze_audio_upload
from ..database import Astronaut, session_object
from ..oauth2 import get_current_user
from ..rate_limiter import limiter
from ..chat_service import ChatService
from ..rag_service import chat_with_rag
from ..config import settings
from groq import Groq
from ..models import AudioDetectionResponse

logger = logging.getLogger("maitri.audio_router")
router = APIRouter(prefix="/api/v1/audio", tags=["Audio Detection"])


@router.post("/detect", response_model=AudioDetectionResponse)
@limiter.limit("10/minute")
async def detect_audio_health_signals(
    request: Request,
    file: UploadFile = File(...),
    current_user: Astronaut = Depends(get_current_user),
):
    result = await analyze_audio_upload(file=file, astronaut_id=current_user.id)
    logger.info(
        "Audio detection complete astronaut:%s severity:%s",
        current_user.id,
        result["risk"]["severity"],
    )
    return result

@router.post("/detect-and-chat")
@limiter.limit("10/minute")
async def detect_audio_and_get_llm_response(
    request: Request,
    db: session_object,
    file: UploadFile = File(...),
    current_user: Astronaut = Depends(get_current_user),
):
    # ── Step 1: Analyze Voice Stress (Acoustic Properties) ──
    try:
        audio_analysis = await analyze_audio_upload(file=file, astronaut_id=current_user.id)
    except Exception as e:
        logger.error(f"Acoustic analysis failed: {e}")
        raise HTTPException(status_code=400, detail=f"Audio analysis failed: {str(e)}")

    # Reset file pointer to read it again for transcription
    await file.seek(0)
    audio_bytes = await file.read()

    # ── Step 2: Transcribe the Audio Speech to Text using Groq Whisper ──
    try:
        groq_client = Groq(api_key=settings.groq_api_key)
        
        # Whisper expects a file tuple (name, bytes, mime)
        transcription_response = groq_client.audio.transcriptions.create(
            file=(file.filename or "recording.wav", audio_bytes, file.content_type or "audio/wav"),
            model="whisper-large-v3",
            prompt="The user is an astronaut communicating with their AI well-being assistant, Maitri.",
            response_format="json"
        )
        user_transcript = transcription_response.text
    except Exception as e:
        logger.error(f"Audio transcription failed: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Speech transcription failed. Please try speaking clearly. Error: {str(e)}"
        )

    if not user_transcript.strip():
         raise HTTPException(status_code=400, detail="No speech detected in audio file.")

    # ── Step 3: Get or Create active Chat Session ──
    conversation = await ChatService.get_or_create_conversation(db, current_user.id)

    # Save the user's spoken transcript as a message in database
    user_msg_metadata = {
        "audio_severity": audio_analysis.get("risk", {}).get("severity", "none"),
        "audio_risk_score": audio_analysis.get("risk", {}).get("risk_score", 0.0),
        "is_voice_input": True
    }
    
    await ChatService.save_message(
        db=db,
        conversation_id=conversation.id,
        astronaut_id=current_user.id,
        role="user",
        content=user_transcript,
        message_type="voice_transcript",
        metadata=user_msg_metadata
    )

    # ── Step 4: Call RAG Chat with Stress Context Injection ──
    # Retrieve past message history
    history_rows = await ChatService.get_conversation_history(
        db, conversation.id, limit=settings.conversation_history_limit
    )
    
    history_list = [
        {"role": msg.role, "content": msg.content} 
        for msg in reversed(history_rows)
    ]

    # Injecting current acoustic stress context directly to help the model adjust its empathy/tone
    stress_context = (
        f"\n[System Audio Diagnostic Input: The user's vocal stress level is currently flagged as "
        f"'{user_msg_metadata['audio_severity'].upper()}' with a stress index of {user_msg_metadata['audio_risk_score']}. "
        f"Please adjust your counseling tone to match their emotional baseline compassionately.]"
    )
    
    # Append physical diagnostic modifier strictly for the current frame run
    if len(history_list) > 0:
        history_list[-1]["content"] += stress_context

    # Run RAG pipeline (retrieves relevant documents, synthesizes response)
    rag_response = await chat_with_rag(
        db=db,
        user_message=user_transcript,
        conversation_history=history_list,
        top_k=settings.rag_top_k
    )

    # ── Step 5: Save AI Response to Database ──
    saved_ai_msg = await ChatService.save_message(
        db=db,
        conversation_id=conversation.id,
        astronaut_id=current_user.id,
        role="assistant",
        content=rag_response["response"],
        message_type="text",
        metadata={"sources": rag_response.get("sources", [])}
    )

    # Update conversation's timestamp
    conversation.updated_at = saved_ai_msg.created_at
    db.add(conversation)
    await db.commit()

    # ── Step 6: Return Response Package to Frontend ──
    return {
        "user_transcript": user_transcript,
        "assistant_response": rag_response["response"],
        "conversation_id": conversation.id,
        "audio_analysis": audio_analysis,
        "sources": rag_response.get("sources", []),
    }