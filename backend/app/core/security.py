import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings

hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def create_token(subject: str, role: str, workspace_id: str, token_type: str = "access") -> tuple[str, str, datetime]:
    now = datetime.now(UTC)
    ttl = timedelta(minutes=settings.access_token_expire_minutes) if token_type == "access" else timedelta(days=settings.refresh_token_expire_days)
    expires = now + ttl
    jti = secrets.token_urlsafe(24)
    secret = settings.jwt_secret if token_type == "access" else settings.jwt_refresh_secret
    token = jwt.encode({"sub": subject, "role": role, "workspace_id": workspace_id, "type": token_type, "jti": jti, "iat": now, "exp": expires}, secret, algorithm="HS256")
    return token, jti, expires


def decode_token(token: str, token_type: str = "access") -> dict:
    secret = settings.jwt_secret if token_type == "access" else settings.jwt_refresh_secret
    payload = jwt.decode(token, secret, algorithms=["HS256"])
    if payload.get("type") != token_type:
        raise jwt.InvalidTokenError("Incorrect token type")
    return payload


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

