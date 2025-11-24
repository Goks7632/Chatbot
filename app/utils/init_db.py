from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.services.tenant_service import TenantService
from app.services.auth_service import AuthService


def init_database():
    db = SessionLocal()
    try:
        tenant_service = TenantService(db)
        auth_service = AuthService(db)
        
        existing_tenant = tenant_service.get_tenant_by_domain("default.local")
        if not existing_tenant:
            print("Creating default tenant...")
            tenant = tenant_service.create_tenant(
                name="Default Tenant",
                domain="default.local",
                groq_api_key=None
            )
            print(f"Tenant created: {tenant.id}")
            
            print("Creating admin user...")
            admin_user = auth_service.register_user(
                email="admin@default.local",
                username="admin",
                password="admin123",
                tenant_id=tenant.id
            )
            
            admin_user.is_admin = True
            db.commit()
            print(f"Admin user created: {admin_user.email}")
            print("Default credentials - Email: admin@default.local, Password: admin123")
        else:
            print("Default tenant already exists")
            
    finally:
        db.close()


if __name__ == "__main__":
    init_database()




