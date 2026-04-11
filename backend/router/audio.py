import logging

from fastapi import APIRouter, Depends, File, Request, UploadFile

from ..audio_detection import analyze_audio_upload
from ..database import Astronaut
from ..models import AudioDetectionResponse
from ..oauth2 import get_current_user
from ..rate_limiter import limiter

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
