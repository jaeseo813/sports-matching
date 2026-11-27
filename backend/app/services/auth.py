import secrets
from datetime import UTC, datetime

from fastapi import HTTPException

from app.core.security import create_token, hash_password, verify_password
from app.models.enums import ParticipationStatus
from app.models.user import User
from app.repositories.match import MatchRepository
from app.repositories.profile import ProfileRepository
from app.repositories.user import DuplicateUserError, UserRepository
from app.schemas.auth import SignupIn, TokenOut
from app.services.match_state import status_after_headcount

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


async def withdraw(
    matches: MatchRepository, profiles: ProfileRepository, user: User, password: str
) -> None:
    """회원 탈퇴 (AGENTS.md 8절). 사용자 행은 지우지 않고 개인정보만 지운다.

    지우는 것: 이메일·비밀번호·닉네임(무작위 값으로 바꿈), 위치·실력·차단·알림, 선호 시간대.
    남기는 것: 매치 기록과 평가(이름 없는 사용자로 남아 다른 사람의 레이팅이 바뀌지 않는다).
    """
    if not verify_password(password, user.password):
        # 401이면 화면이 로그아웃시켜 버리므로 403으로 알린다
        raise _error(403, "WRONG_PASSWORD", "비밀번호가 올바르지 않습니다")
    if await matches.count_active_hosted(user.id) > 0:
        raise _error(409, "HOSTING_MATCH", "주최 중인 매치가 있어요. 먼저 매치를 취소해 주세요")
    for part, match in await matches.active_applications(user.id):
        part.status = ParticipationStatus.CANCELED
        accepted = await matches.count_accepted(match.id)  # 취소가 반영된 인원
        match.status = status_after_headcount(match.status, accepted, match.capacity)
    await profiles.delete_personal_data(user.id)
    tag = secrets.token_hex(4)
    user.email = f"withdrawn-{user.id}-{tag}@withdrawn.invalid"
    user.nickname = f"탈퇴한 사용자 {tag}"
    user.password = "!" + secrets.token_hex(
        16
    )  # 해시 형식이 아니라 어떤 비밀번호로도 로그인되지 않는다
    user.preferred_slots = None
    user.is_active = False
    user.deleted_at = datetime.now(UTC).replace(tzinfo=None)
    await matches.commit()
