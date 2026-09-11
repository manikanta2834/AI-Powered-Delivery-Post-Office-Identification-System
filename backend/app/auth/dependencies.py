"""FastAPI Dependency injectors for RBAC, JWT validation, and Resource Scoping."""

from datetime import datetime, timezone
from typing import Annotated, Sequence
from uuid import UUID

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_db_session
from app.core.security_ext import ALGORITHM, SECRET_KEY, verify_reauth_token
from app.models import User

security_bearer = HTTPBearer(auto_error=False)
settings = get_settings()


async def get_redis_client() -> Redis:
    client = None
    try:
        client = Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=2.0,
            socket_timeout=2.0,
        )
        yield client
    finally:
        if client:
            try:
                await client.aclose()
            except Exception:
                pass


async def get_current_user_optional(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security_bearer)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User | None:
    """Optional user extractor (returns None if unauthenticated)."""
    if not credentials:
        return None
    try:
        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            audience="indiapost:postal-ai",
        )
        user_id = payload.get("sub")
        if not user_id:
            return None
        return await session.scalar(select(User).where(User.id == UUID(user_id), User.is_active == True))
    except Exception:
        return None


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security_bearer)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> User:
    """Strict authenticated user extractor verifying active status & Redis session."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            audience="indiapost:postal-ai",
        )
        user_id = payload.get("sub")
        session_id = payload.get("sid")
        role = payload.get("role")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

        # Inactivity & Revocation check in Redis
        if session_id:
            try:
                if await redis.get(f"revoked:session:{session_id}"):
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session has been revoked")

                # Shared-kiosk operator/admin 15-minute idle timeout
                if role in ["operator", "admin"]:
                    last_act = await redis.get(f"session:activity:{session_id}")
                    now = datetime.now(timezone.utc).timestamp()
                    if last_act and (now - float(last_act)) > 900:  # 15 minutes
                        await redis.set(f"revoked:session:{session_id}", "true", ex=86400)
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Operator session expired due to 15 minutes of inactivity",
                        )
                    await redis.set(f"session:activity:{session_id}", str(now), ex=1800)
            except HTTPException:
                raise
            except Exception:
                # If redis is unavailable, continue in simulation/fallback mode
                pass

    except (jwt.PyJWTError, ValueError) as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or malformed access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err

    try:
        user = await session.scalar(select(User).where(User.id == UUID(user_id), User.is_active == True))
    except Exception:
        user = None

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account disabled or deleted")
    return user


def require_roles(allowed_roles: Sequence[str]):
    """Server-side route-level RBAC enforcement."""
    async def role_guard(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        user_role = getattr(current_user, "role", "citizen")
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: This action requires one of {list(allowed_roles)} privileges.",
            )
        return current_user
    return role_guard


def require_reauth():
    """Requires elevated re-authentication within the last 5 minutes for high-risk operations."""
    async def reauth_guard(
        current_admin: Annotated[User, Depends(require_roles(["admin"]))],
        x_reauth_token: Annotated[str | None, Header(alias="X-ReAuth-Token")] = None,
    ) -> User:
        if not x_reauth_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="High-privilege operation requires elevated re-authentication. Provide 'X-ReAuth-Token' header.",
            )
        if not verify_reauth_token(x_reauth_token, current_admin.id):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired re-authentication token",
            )
        return current_admin
    return reauth_guard
