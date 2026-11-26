"""密码哈希与 JWT 签发/校验。"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

TokenType = Literal["access", "refresh"]

# bcrypt 只处理前 72 字节，超出部分需自行截断，避免新版库抛 ValueError
_BCRYPT_MAX_BYTES = 72


def _encode(raw: str) -> bytes:
    return raw.encode("utf-8")[:_BCRYPT_MAX_BYTES]


# --------------------------------------------------------------------------- #
# 密码
# --------------------------------------------------------------------------- #
def hash_password(raw: str) -> str:
    return bcrypt.hashpw(_encode(raw), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_encode(raw), hashed.encode("utf-8"))
    except Exception:
        return False


def validate_password_strength(raw: str) -> tuple[bool, str]:
    """密码强度校验：长度 + 字母 + 数字，返回 (是否通过, 提示语)。"""
    if len(raw) < settings.PASSWORD_MIN_LENGTH:
        return False, f"密码长度不得少于 {settings.PASSWORD_MIN_LENGTH} 位"
    if not any(c.isalpha() for c in raw):
        return False, "密码必须包含字母"
    if not any(c.isdigit() for c in raw):
        return False, "密码必须包含数字"
    return True, ""


# --------------------------------------------------------------------------- #
# JWT
# --------------------------------------------------------------------------- #
def _create_token(subject: str, token_type: TokenType, expires: timedelta,
                  extra: dict[str, Any] | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires).timestamp()),
        "jti": uuid.uuid4().hex,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(subject: str, tenant_id: int, **extra: Any) -> str:
    return _create_token(
        subject, "access",
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        {"tenant_id": tenant_id, **extra},
    )


def create_refresh_token(subject: str, tenant_id: int, **extra: Any) -> str:
    return _create_token(
        subject, "refresh",
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        {"tenant_id": tenant_id, **extra},
    )


def decode_token(token: str, expect: TokenType = "access") -> dict[str, Any]:
    """解析并校验 token，失败抛 JWTError。"""
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    if payload.get("type") != expect:
        raise JWTError("token 类型不匹配")
    return payload
