from sqlalchemy.orm import Session
from typing import Optional, List
from app.models.message import Message


class MessageRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, message_data: dict) -> Message:
        message = Message(**message_data)
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message
    
    def get_by_id(self, message_id: str) -> Optional[Message]:
        return self.db.query(Message).filter(Message.id == message_id).first()
    
    def get_by_conversation(self, conversation_id: str, skip: int = 0, limit: int = 100) -> List[Message]:
        return self.db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).offset(skip).limit(limit).all()
    
    def delete(self, message_id: str) -> bool:
        message = self.get_by_id(message_id)
        if message:
            self.db.delete(message)
            self.db.commit()
            return True
        return False




