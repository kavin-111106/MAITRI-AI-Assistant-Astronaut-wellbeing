from typing import Optional, List, Any
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

class AudioDetectionResponse(BaseModel):
    filename: str | None
    content_type: str | None
    analysis: dict[str, Any]
    risk: dict[str, Any]
    notes: list[str]