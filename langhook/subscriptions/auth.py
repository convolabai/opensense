"""JWT authentication service for subscription API."""

from datetime import datetime, timedelta
from typing import Optional

import jwt
import structlog
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from langhook.subscriptions.config import subscription_settings

logger = structlog.get_logger("langhook")

security = HTTPBearer()


class JWTService:
    """Service for JWT token management."""

    def __init__(self) -> None:
        self.secret_key = subscription_settings.jwt_secret
        self.algorithm = subscription_settings.jwt_algorithm

    def create_access_token(self, user_id: str, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token."""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=24)
            
        to_encode = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.utcnow()
        }
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def verify_token(self, token: str) -> Optional[str]:
        """Verify a JWT token and return the user ID."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id: str = payload.get("sub")
            if user_id is None:
                return None
            return user_id
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.JWTError as e:
            logger.warning("JWT token verification failed", error=str(e))
            return None


jwt_service = JWTService()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Dependency to get the current user from JWT token."""
    user_id = jwt_service.verify_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[str]:
    """Optional dependency to get the current user from JWT token."""
    if credentials is None:
        return None
    return jwt_service.verify_token(credentials.credentials)