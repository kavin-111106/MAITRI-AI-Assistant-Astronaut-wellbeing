from sqlmodel import Column, SQLModel,Field,Session,create_engine,text,Relationship
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import JSONB
from pydantic import EmailStr
from typing import Annotated,Optional,List,Any
from fastapi import Depends
from urllib.parse import quote
from .config import settings
from datetime import datetime

raw_password = settings.database_password
safe_password = quote(raw_password)

engine=create_async_engine(f"postgresql+psycopg://{settings.database_username}:{safe_password}@{settings.database_hostname}:{settings.database_port}/{settings.database_name}",echo=True)

async def get_session():
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session

session_object=Annotated[AsyncSession,Depends(get_session)]

#def create_db_and_tables():
#   SQLModel.metadata.create_all(engine)

class Astronaut(SQLModel,table=True):
    id:int|None = Field(default=None,primary_key=True)
    email:EmailStr = Field(nullable=False,unique=True)
    password:str = Field(nullable=False)
    created_at:datetime = Field(default_factory=datetime.utcnow)

    conversations: List["Conversation"] = Relationship(back_populates="astronaut")
    messages: List["Messages"] = Relationship(back_populates="astronaut")
    health_insights: List["HealthInsight"] = Relationship(back_populates="astronaut")

class Conversation(SQLModel,table=True):
    id:int|None = Field(default=None,primary_key=True)
    astronaut_id:int = Field(foreign_key="astronaut.id")
    title:str|None = Field(nullable=True)
    created_at:datetime = Field(default_factory=datetime.utcnow)
    updated_at:datetime = Field(default_factory=datetime.utcnow)   

    astronaut: Optional[Astronaut] = Relationship(back_populates="conversations")
    messages: List["Messages"] = Relationship(back_populates="conversation")

class Messages(SQLModel,table=True):
    id:int|None = Field(default=None,primary_key=True)
    conversation_id:int = Field(foreign_key="conversation.id")
    astronaut_id:int = Field(foreign_key="astronaut.id")
    role:str = Field(nullable=False)
    content:str = Field(nullable=False)
    message_type:str = Field(nullable=False)
    message_metadata: Optional[dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB)
    )
    created_at:datetime = Field(default_factory=datetime.utcnow)

    conversation: Optional[Conversation] = Relationship(back_populates="messages")
    astronaut: Optional[Astronaut] = Relationship(back_populates="messages")
    health_insight: Optional["HealthInsight"] = Relationship(back_populates="message")

class HealthInsight(SQLModel,table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    astronaut_id: int = Field(foreign_key="astronaut.id")
    message_id: Optional[int] = Field(default=None, foreign_key="messages.id")
    insight_type: str = Field(max_length=100) 
    severity: str = Field(max_length=50)  
    details: Optional[dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB)
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    astronaut: Optional[Astronaut] = Relationship(back_populates="health_insights")
    message: Optional[Messages] = Relationship(back_populates="health_insight")