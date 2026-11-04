from datetime import UTC, datetime

from fastapi import HTTPException

from app.core.security import (
    TokenError,
    create_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.token_store import TokenStore
from app.models.user import User
from app.repositories.user import DuplicateUserError, UserRepository
from app.schemas.auth import SignupIn, TokenOut

_MIN_AGE = 19  # 미성년자 가입 제외 (연도 기준 근사)


def _error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


_INVALID_CREDENTIALS = _error(
    401, "INVALID_CREDENTIALS", "이메일 또는 비밀번호가 올바르지 않습니다"
)
_INVALID_TOKEN = _error(401, "INVALID_TOKEN", "유효하지 않은 토큰입니다")


def _issue_pair(user_id: int, store: TokenStore, family: str | None = None) -> TokenOut:
    access, _ = create_token(user_id, "access")
    refresh, jti = create_token(user_id, "refresh", family=family)
    claims = decode_token(refresh, "refresh")
    store.issue(jti, claims["fam"])
    return TokenOut(access_token=access, refresh_token=refresh)


async def signup(repo: UserRepository, data: SignupIn) -> User:
    if datetime.now(UTC).year - data.birth_year < _MIN_AGE:
        raise _error(422, "UNDERAGE", "만 19세 이상만 가입할 수 있습니다")
    try:
        return await repo.create(
            email=data.email.lower(),
            password=hash_password(data.password),
            nickname=data.nickname,
            gender=data.gender,
            birth_year=data.birth_year,
        )
    except DuplicateUserError:
        raise _error(409, "ALREADY_EXISTS", "이미 사용 중인 이메일 또는 닉네임입니다") from None


async def login(repo: UserRepository, store: TokenStore, email: str, password: str) -> TokenOut:
    user = await repo.get_by_email(email.lower())
    # 이메일 존재 여부를 응답으로 구분하지 못하게 같은 오류를 돌려준다
    if user is None or not user.is_active or not verify_password(password, user.password):
        raise _INVALID_CREDENTIALS
    return _issue_pair(user.id, store)


async def refresh(repo: UserRepository, store: TokenStore, refresh_token: str) -> TokenOut:
    try:
        claims = decode_token(refresh_token, "refresh")
    except TokenError:
        raise _INVALID_TOKEN from None
    if store.consume(claims["jti"], claims["fam"]) != "ok":
        raise _INVALID_TOKEN  # 재사용이면 consume이 family 전체를 이미 폐기했다
    user = await repo.get_by_id(int(claims["sub"]))
    if user is None or not user.is_active:
        raise _INVALID_TOKEN
    return _issue_pair(user.id, store, family=claims["fam"])


def logout(store: TokenStore, refresh_token: str) -> None:
    try:
        claims = decode_token(refresh_token, "refresh")
    except TokenError:
        return  # 이미 무효인 토큰은 로그아웃된 것과 같다
    store.revoke_family(claims["fam"])
