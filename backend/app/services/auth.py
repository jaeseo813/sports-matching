from datetime import UTC, datetime

from fastapi import HTTPException

from app.core.security import create_token, hash_password, verify_password
from app.models.user import User
from app.repositories.user import DuplicateUserError, UserRepository
from app.schemas.auth import SignupIn, TokenOut

_MIN_AGE = 19  # 미성년자 가입 제외 (연도 기준 근사)


def _error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


_INVALID_CREDENTIALS = _error(
    401, "INVALID_CREDENTIALS", "이메일 또는 비밀번호가 올바르지 않습니다"
)


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


async def login(repo: UserRepository, email: str, password: str) -> TokenOut:
    user = await repo.get_by_email(email.lower())
    # 이메일 존재 여부를 응답으로 구분하지 못하게 같은 오류를 돌려준다
    if user is None or not user.is_active or not verify_password(password, user.password):
        raise _INVALID_CREDENTIALS
    return TokenOut(access_token=create_token(user.id))
