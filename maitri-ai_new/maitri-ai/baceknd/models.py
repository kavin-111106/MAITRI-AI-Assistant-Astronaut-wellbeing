from typing import Optional
from pydantic import BaseModel,EmailStr
from datetime import datetime

class Token(BaseModel):
    access_token: str
    token_type: str

class Users(BaseModel):
    email:EmailStr

class astronaut_register(BaseModel):
    email:EmailStr
    password:str

class AstronautResponse(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime

class TokenData(BaseModel):
    id: str|None

class ChatRequest(BaseModel):
    message: str
    message_type: str = 'text'
    metadata: Optional[dict] = None
