from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TenantCreate(BaseModel):
    name: str
    domain: str
    groq_api_key: Optional[str] = None
    settings: Optional[dict] = {}


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    groq_api_key: Optional[str] = None
    settings: Optional[dict] = None
    is_active: Optional[bool] = None


class TenantResponse(BaseModel):
    id: str
    name: str
    domain: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True




