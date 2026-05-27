"""Password hashing (bcrypt) and JWT token utilities."""

from datetime import datetime, timedelta, timezone
from typing import Annotated

from bcrypt import checkpw, gensalt, hashpw
from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from db.models import User
from db.session import get_db
from db.session import get_db as get_async_session

_settings = get_settings()


# ------ Password hashing ------


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return hashpw(password.encode(), gensalt()).decode()


def verify_password(password: str, hash_value: str) -> bool:
    """Verify a password against a bcrypt hash."""
    return checkpw(password.encode(), hash_value.encode())


# ------ JWT tokens ------


def create_access_token(subject: str, *, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token with the user id as the subject claim."""
    if expires_delta is None:
        expires_delta = timedelta(minutes=_settings.jwt_expire_minutes)
    expire = datetime.now(timezone.utc) + expires_delta
    payload = {"sub": subject, "exp": expire, "type": "access"}
    return jwt.encode(payload, _settings.jwt_secret, algorithm=_settings.jwt_algorithm)


def decode_access_token(token: str) -> str | None:
    """Decode a JWT token and return the subject (user id) or None if invalid."""
    try:
        payload = jwt.decode(token, _settings.jwt_secret, algorithms=[_settings.jwt_algorithm])
        if payload.get("type") != "access":
            return None
        return payload["sub"]
    except JWTError:
        return None


# ------ FastAPI dependencies ------


async def get_current_user(
    authorization: Annotated[str, Header()],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> User:
    """Extract the authenticated User from the Authorization header."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid scheme")
    token = authorization.split(" ", 1)[1]
    subject = decode_access_token(token)
    if subject is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid/ expired token")
    try:
        user_id = int(subject)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bad token subject")
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user
