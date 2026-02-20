from sqlmodel import Session, select, desc, or_
from typing import List, Optional
from datetime import datetime
from .database import Astronaut, Conversation, Messages,session_object

class ChatService:
    
    @staticmethod
    async def get_or_create_conversation(db: session_object, astronaut_id: int) -> Conversation:
        statement = (
            select(Conversation)
            .where(Conversation.astronaut_id == astronaut_id)
            .order_by(desc(Conversation.updated_at))
        )
        result = await db.exec(statement)
        conversation = result.first()
        
        if not conversation:
            conversation = Conversation(astronaut_id=astronaut_id)
            db.add(conversation)
            await db.commit()
            await db.refresh(conversation)
        
        return conversation
    
    @staticmethod
    async def save_message(db: session_object,conversation_id: int,astronaut_id: int,role: str,content: str,message_type: str = 'text',metadata: Optional[dict] = None) -> Messages:
        message = Messages(
            conversation_id=conversation_id,
            astronaut_id=astronaut_id,
            role=role,
            content=content,
            message_type=message_type,
            message_metadata=metadata or {}
        )
        db.add(message)
        await db.commit()
        await db.refresh(message)

        conversation = await db.get(Conversation, conversation_id)
        if conversation:
            conversation.updated_at = datetime.utcnow()
            db.add(conversation)
            await db.commit()
        
        return message
    
    @staticmethod
    async def get_conversation_history(db: session_object, conversation_id: int,limit: Optional[int] = None) -> List[Messages]:
        statement = (
            select(Messages)
            .where(Messages.conversation_id == conversation_id)
            .order_by(Messages.created_at)
        )
        
        if limit:
            statement = statement.limit(limit)
        
        result = await db.exec(statement)
        messages = result.all()
        return list(messages)
    
    @staticmethod
    async def get_recent_messages(db: session_object,astronaut_id: int,limit: int = 10) -> List[Messages]:
        statement = (
            select(Messages)
            .where(Messages.astronaut_id == astronaut_id)
            .order_by(desc(Messages.created_at))
            .limit(limit)
        )
        
        result = await db.exec(statement)
        messages = result.all()
        return list(messages)
    
    @staticmethod
    async def search_past_conversations(db: session_object,astronaut_id: int,keyword: str) -> List[Messages]:
        statement = (
            select(Messages)
            .where(
                Messages.astronaut_id == astronaut_id,
                Messages.content.ilike(f'%{keyword}%')
            )
            .order_by(desc(Messages.created_at))
        )
        
        result = await db.exec(statement)
        messages = result.all()
        return list(messages)
    
    @staticmethod
    async def get_all_conversations(db: session_object,astronaut_id: int) -> List[Conversation]:
        statement = (
            select(Conversation)
            .where(Conversation.astronaut_id == astronaut_id)
            .order_by(desc(Conversation.updated_at))
        )
        
        result = await db.exec(statement)
        conversations = result.all()
        return list(conversations)
    
    @staticmethod
    async def delete_conversation(db: session_object,conversation_id: int,astronaut_id: int) -> bool:
        conversation = await db.get(Conversation, conversation_id)
        
        if not conversation or conversation.astronaut_id != astronaut_id:
            return False
        
        statement = select(Messages).where(Messages.conversation_id == conversation_id)
        result = await db.exec(statement)
        messages = result.all()
        
        for message in messages:
            await db.delete(message)
        
        await db.delete(conversation)
        await db.commit()
        return True
    
    @staticmethod
    async def create_new_conversation(
        db: session_object,
        astronaut_id: int,
        title: Optional[str] = None
    ) -> Conversation:
        
        conversation = Conversation(
            astronaut_id=astronaut_id,
            title=title
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        return conversation