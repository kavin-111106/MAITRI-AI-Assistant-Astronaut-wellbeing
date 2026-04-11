from typing import Optional, List
from pydantic import BaseModel, EmailStr
from datetime import datetime


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    id: str | None = None
    role: str | None = None


class Users(BaseModel):
    email: EmailStr


class astronaut_register(BaseModel):
    email: EmailStr
    password: str


class AstronautResponse(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime



class AdminRegister(BaseModel):
    email: EmailStr
    password: str


class AdminResponse(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime



class ChatRequest(BaseModel):
    message: str
    message_type: str = "text"
    metadata: Optional[dict] = None


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    message_type: str
    metadata: Optional[dict]
    created_at: datetime


class ChatResponse(BaseModel):
    response: str
    conversation_id: int
    sources: List[dict] = []        
    timing: Optional[dict] = None   



class DocumentOut(BaseModel):
    id: int
    filename: str
    file_type: str
    file_size: int
    chunk_count: int
    status: str
    error_message: Optional[str]
    created_at: datetime


class DocumentListResponse(BaseModel):
    total: int
    documents: List[DocumentOut]


class RAGQueryRequest(BaseModel):
    question: str
    top_k: int = 5


class RAGSource(BaseModel):
    filename: str
    document_id: int
    similarity: float
    excerpt: str


class RAGQueryResponse(BaseModel):
    answer: str
    sources: List[RAGSource]
    timing: dict
    model: str


class AudioAnalysisMetrics(BaseModel):
    duration_sec: float
    sample_rate_hz: int
    rms_mean: float
    zcr_mean: float
    spectral_centroid_hz: float
    spectral_rolloff_hz: float
    estimated_tempo_bpm: float
    estimated_pitch_hz: float
    estimated_speech_rate_wpm: float
    silence_ratio: float
    clipping_ratio: float
    quality_flags: List[str] = []


class AudioRiskAssessment(BaseModel):
    severity: str
    state: str
    risk_score: float
    confidence: float
    indicators: List[str] = []
    recommended_action: str


class AudioDetectionResponse(BaseModel):
    filename: Optional[str] = None
    content_type: Optional[str] = None
    analysis: AudioAnalysisMetrics
    risk: AudioRiskAssessment
    notes: List[str] = []