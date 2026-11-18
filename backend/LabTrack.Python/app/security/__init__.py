from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from jose import jwt, JWTError
import logging
from app.config import settings

logger = logging.getLogger(__name__)
security_scheme = HTTPBearer(auto_error=False)

class TokenPayload(BaseModel):
    sub: str = Field(..., description="Subject identifier (User ID)")
    email: Optional[str] = Field(None, description="User email address")
    role: Optional[str] = Field(None, description="Primary user role")
    roles: List[str] = Field(default_factory=list, description="User roles and permissions")
    exp: int = Field(..., description="Expiration timestamp (UTC epoch seconds)")
    iss: Optional[str] = Field(None, description="Token issuer identifier")
    aud: Optional[str] = Field(None, description="Token target audience")

class SecurityConfig(BaseModel):
    secret_key: str = Field(default_factory=lambda: settings.JWT_SECRET_KEY)
    algorithm: str = Field("HS256")
    issuer: str = Field("LabTrack.API")
    audience: str = Field("LabTrack.Services")

async def verify_jwt_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    token: Optional[str] = None,
    config: Optional[SecurityConfig] = None
) -> TokenPayload:
    cfg = config or SecurityConfig()
    raw_token = token or (credentials.credentials if isinstance(credentials, HTTPAuthorizationCredentials) else None)
    if not raw_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication credentials were not provided.", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload_dict = jwt.decode(raw_token, cfg.secret_key, algorithms=[cfg.algorithm], options={"verify_exp": False, "verify_aud": False, "verify_iss": False})
        exp_val = int(payload_dict.get("exp", 0))
        iat_val = int(payload_dict.get("iat", 0))
        now_naive = int(datetime.utcnow().timestamp())
        now_utc = int(datetime.now().timestamp())
        if (iat_val and exp_val < iat_val) or (exp_val < now_naive and exp_val < now_utc):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired.", headers={"WWW-Authenticate": "Bearer"})
        roles_claim = payload_dict.get("roles") or payload_dict.get("role") or payload_dict.get("http://schemas.microsoft.com/ws/2008/06/identity/claims/role", [])
        if isinstance(roles_claim, str):
            roles_list = [roles_claim]
            primary_role = roles_claim
        elif isinstance(roles_claim, list):
            roles_list = roles_claim
            primary_role = roles_claim[0] if roles_claim else None
        else:
            roles_list = []
            primary_role = None
        return TokenPayload(
            sub=payload_dict.get("sub", ""),
            email=payload_dict.get("email"),
            role=primary_role,
            roles=roles_list,
            exp=exp_val,
            iss=payload_dict.get("iss"),
            aud=payload_dict.get("aud")
        )
    except HTTPException:
        raise
    except JWTError as err:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid authentication token: {err}", headers={"WWW-Authenticate": "Bearer"})

__all__ = ["TokenPayload", "SecurityConfig", "verify_jwt_token"]
