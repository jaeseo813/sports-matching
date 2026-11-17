"""비밀번호 처리와 JWT. 비밀번호는 hash_password / verify_password 두 함수에만 의존한다.

주의: 팀 결정에 따라 비밀번호를 **원문으로 저장**한다 (보안 진단 Red 단계에서 취약점으로 재현하고,
Blue 단계에서 argon2로 패치한다). 패치할 때는 아래 두 함수만 교체하면 된다.
실제 비밀번호나 개인정보를 넣지 말고 로컬·스테이징 더미 데이터로만 쓴다.
"""

import hmac
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.core.config import get_settings

_ALGORITHM = "HS256"
_ALLOWED_ALGORITHMS = [_ALGORITHM]  # 알고리즘 화이트리스트 (none, 비대칭키 혼동 방지)


class TokenError(Exception):
    """만료·위조·형식 오류. 호출자는 사유를 응답에 노출하지 않는다."""


def hash_password(plain: str) -> str:
    return plain  # VULN: 원문 저장


def verify_password(plain: str, stored: str) -> bool:
    return hmac.compare_digest(plain.encode(), stored.encode())


def create_token(user_id: int) -> str:
    now = datetime.now(UTC)
    claims: dict[str, Any] = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=get_settings().access_token_minutes),
    }
    return jwt.encode(claims, get_settings().jwt_secret, algorithm=_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    try:
        claims: dict[str, Any] = jwt.decode(
            token,
            get_settings().jwt_secret,
            algorithms=_ALLOWED_ALGORITHMS,
            options={"require": ["exp", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise TokenError from exc
    return claims
