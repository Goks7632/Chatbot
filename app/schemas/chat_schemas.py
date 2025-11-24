from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class MessageCreate(BaseModel):
    content: str
    model: Optional[str] = "llama-3.3-70b-versatile"
    temperature: Optional[float] = 0.7


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    tokens_used: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class ConversationCreate(BaseModel):
    title: Optional[str] = None


class ConversationResponse(BaseModel):
    id: str
    tenant_id: str
    user_id: str
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ConversationDetailResponse(BaseModel):
    id: str
    tenant_id: str
    user_id: str
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = []
    
    class Config:
        from_attributes = True

