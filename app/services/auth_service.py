from datetime import timedelta
from sqlalchemy.orm import Session
from typing import Optional
from app.core.security import verify_password, get_password_hash, create_access_token
from app.repositories.user_repository import UserRepository
from app.repositories.tenant_repository import TenantRepository
from app.core.config import settings


class AuthService:
    def __init__(self, db: Session):
        self.user_repo = UserRepository(db)
        self.tenant_repo = TenantRepository(db)
    
    def authenticate_user(self, email: str, password: str):
        user = self.user_repo.get_by_email(email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user
    
    def create_token(self, user_id: str, tenant_id: str) -> str:
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user_id, "tenant_id": tenant_id},
            expires_delta=access_token_expires
        )
        return access_token
    
    def register_user(self, email: str, username: str, password: str, tenant_id: str):
        hashed_password = get_password_hash(password)
        user_data = {
            "email": email,
            "username": username,
            "hashed_password": hashed_password,
            "tenant_id": tenant_id
        }
        return self.user_repo.create(user_data)




