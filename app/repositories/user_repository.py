from sqlalchemy.orm import Session
from typing import Optional, List
from app.models.user import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, user_data: dict) -> User:
        import uuid
        if 'id' not in user_data:
            user_data['id'] = str(uuid.uuid4())
        user = User(**user_data)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def get_by_id(self, user_id: str) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()
    
    def get_by_tenant(self, tenant_id: str, skip: int = 0, limit: int = 100) -> List[User]:
        return self.db.query(User).filter(User.tenant_id == tenant_id).offset(skip).limit(limit).all()
    
    def update(self, user_id: str, user_data: dict) -> Optional[User]:
        user = self.get_by_id(user_id)
        if user:
            for key, value in user_data.items():
                setattr(user, key, value)
            self.db.commit()
            self.db.refresh(user)
        return user
    
    def delete(self, user_id: str) -> bool:
        user = self.get_by_id(user_id)
        if user:
            self.db.delete(user)
            self.db.commit()
            return True
        return False



