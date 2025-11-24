from sqlalchemy.orm import Session
from typing import Optional, List
from app.repositories.tenant_repository import TenantRepository


class TenantService:
    def __init__(self, db: Session):
        self.tenant_repo = TenantRepository(db)
    
    def create_tenant(self, name: str, domain: str, groq_api_key: Optional[str] = None, settings: dict = None):
        tenant_data = {
            "name": name,
            "domain": domain,
            "groq_api_key": groq_api_key,
            "settings": settings or {}
        }
        return self.tenant_repo.create(tenant_data)
    
    def get_tenant_by_id(self, tenant_id: str):
        return self.tenant_repo.get_by_id(tenant_id)
    
    def get_tenant_by_domain(self, domain: str):
        return self.tenant_repo.get_by_domain(domain)
    
    def update_tenant(self, tenant_id: str, update_data: dict):
        return self.tenant_repo.update(tenant_id, update_data)
    
    def get_all_tenants(self, skip: int = 0, limit: int = 100) -> List:
        return self.tenant_repo.get_all(skip, limit)




