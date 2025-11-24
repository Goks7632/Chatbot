from sqlalchemy.orm import Session
from typing import Optional, List
from app.models.conversation import Conversation


class ConversationRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, conversation_data: dict) -> Conversation:
        conversation = Conversation(**conversation_data)
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation
    
    def get_by_id(self, conversation_id: str) -> Optional[Conversation]:
        return self.db.query(Conversation).filter(Conversation.id == conversation_id).first()
    
    def get_by_user(self, user_id: str, skip: int = 0, limit: int = 100) -> List[Conversation]:
        return self.db.query(Conversation).filter(
            Conversation.user_id == user_id
        ).offset(skip).limit(limit).all()
    
    def get_by_tenant(self, tenant_id: str, skip: int = 0, limit: int = 100) -> List[Conversation]:
        return self.db.query(Conversation).filter(
            Conversation.tenant_id == tenant_id
        ).offset(skip).limit(limit).all()
    
    def update(self, conversation_id: str, conversation_data: dict) -> Optional[Conversation]:
        conversation = self.get_by_id(conversation_id)
        if conversation:
            for key, value in conversation_data.items():
                setattr(conversation, key, value)
            self.db.commit()
            self.db.refresh(conversation)
        return conversation
    
    def delete(self, conversation_id: str) -> bool:
        conversation = self.get_by_id(conversation_id)
        if conversation:
            self.db.delete(conversation)
            self.db.commit()
            return True
        return False




