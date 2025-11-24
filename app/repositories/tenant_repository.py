from sqlalchemy.orm import Session
from typing import Optional, List
from app.models.tenant import Tenant


class TenantRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, tenant_data: dict) -> Tenant:
        import uuid
        if 'id' not in tenant_data:
            tenant_data['id'] = str(uuid.uuid4())
        tenant = Tenant(**tenant_data)
        self.db.add(tenant)
        self.db.commit()
        self.db.refresh(tenant)
        return tenant
    
    def get_by_id(self, tenant_id: str) -> Optional[Tenant]:
        return self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    def get_by_domain(self, domain: str) -> Optional[Tenant]:
        return self.db.query(Tenant).filter(Tenant.domain == domain).first()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[Tenant]:
        return self.db.query(Tenant).offset(skip).limit(limit).all()
    
    def update(self, tenant_id: str, tenant_data: dict) -> Optional[Tenant]:
        tenant = self.get_by_id(tenant_id)
        if tenant:
            for key, value in tenant_data.items():
                setattr(tenant, key, value)
            self.db.commit()
            self.db.refresh(tenant)
        return tenant
    
    def delete(self, tenant_id: str) -> bool:
        tenant = self.get_by_id(tenant_id)
        if tenant:
            self.db.delete(tenant)
            self.db.commit()
            return True
        return False



