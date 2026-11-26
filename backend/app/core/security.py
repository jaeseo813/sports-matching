"""비밀번호 처리와 JWT. 비밀번호는 hash_password / verify_password 두 함수에만 의존한다.

비밀번호는 Argon2로 해시하여 저장하고 검증한다.
실제 비밀번호나 개인정보를 넣지 말고 로컬·스테이징 더미 데이터로만 쓴다.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.core.config import get_settings

_ALGORITHM = "HS256"
_ALLOWED_ALGORITHMS = [
    _ALGORITHM,
]  # 알고리즘 화이트리스트 (none, 비대칭키 혼동 방지)
_password_hasher = PasswordHasher()


class TokenError(Exception):
    """만료·위조·형식 오류. 호출자는 사유를 응답에 노출하지 않는다."""


def hash_password(plain: str) -> str:
    return _password_hasher.hash(plain)


def verify_password(plain: str, stored: str) -> bool:
    try:
        return _password_hasher.verify(stored, plain)
    except (VerifyMismatchError, InvalidHashError):
        return False


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
