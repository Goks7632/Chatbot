"""
Session Context Manager for Haibot API Integration.
Stores verified user session data for function calling operations.
"""
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class SessionContext:
    """
    Stores verified user session data for function calling.
    
    This context is created after successful auth/verify and is used
    to provide profileId and tenantId for subsequent API calls.
    """
    user_id: str
    profile_id: Optional[str] = None
    tenant_id: Optional[str] = None
    verified: bool = False
    
    def is_verified(self) -> bool:
        """Check if session has been verified."""
        return self.verified and self.profile_id is not None
    
    def update_from_verification(self, verification_response: dict) -> None:
        """
        Update context from auth/verify response.
        
        The response structure is:
        {
            "success": true,
            "user": {
                "id": "...",
                "profile": {
                    "id": "...",
                    "email": "...",
                    ...
                }
            }
        }
        
        Args:
            verification_response: Response from /api/auth/verify endpoint
        """
        # Handle nested structure from real API
        user = verification_response.get("user", {})
        profile = user.get("profile", {})
        
        # Extract profile_id from nested structure
        self.profile_id = (
            profile.get("id") or 
            user.get("id") or 
            verification_response.get("profileId") or 
            verification_response.get("profile_id")
        )
        
        # tenant_id might not be present in the response
        self.tenant_id = (
            verification_response.get("tenantId") or 
            verification_response.get("tenant_id") or
            self.profile_id  # Use profile_id as tenant_id fallback
        )
        
        self.verified = verification_response.get("success", True)
    
    def to_dict(self) -> dict:
        """Convert context to dictionary for serialization."""
        return {
            "user_id": self.user_id,
            "profile_id": self.profile_id,
            "tenant_id": self.tenant_id,
            "verified": self.verified
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "SessionContext":
        """Create context from dictionary."""
        return cls(
            user_id=data["user_id"],
            profile_id=data.get("profile_id"),
            tenant_id=data.get("tenant_id"),
            verified=data.get("verified", False)
        )
