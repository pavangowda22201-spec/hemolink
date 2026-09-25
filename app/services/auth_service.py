from datetime import datetime, timedelta, timezone
import os

import jwt
from pwdlib import PasswordHash


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

JWT_SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    "hemolink-development-secret-change-this",
)

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))

password_hash = PasswordHash.recommended()


# ---------------------------------------------------------------------------
# Password handling
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Create a secure password hash."""
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a plain password against its stored hash."""
    return password_hash.verify(password, hashed_password)


# ---------------------------------------------------------------------------
# JWT handling
# ---------------------------------------------------------------------------

def create_access_token(user_id: str, user_type: str) -> str:
    """Create a JWT access token for an authenticated HemoLink user."""
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=JWT_EXPIRE_MINUTES)

    payload = {
        "sub": str(user_id),
        "user_type": user_type,
        "iat": now,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict:
    """Validate and decode a HemoLink JWT access token."""
    return jwt.decode(
        token,
        JWT_SECRET_KEY,
        algorithms=[JWT_ALGORITHM],
    )