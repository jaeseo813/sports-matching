from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Gender

_EMAIL = r"^[^@\s]{1,64}@[^@\s]{1,189}\.[^@\s]{2,}$"


class SignupIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(max_length=255, pattern=_EMAIL)
    password: str = Field(min_length=8, max_length=128)
    nickname: str = Field(min_length=2, max_length=30)
    gender: Gender
    birth_year: int = Field(ge=1920, le=2100)


class LoginIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(max_length=255)
    password: str = Field(max_length=128)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 (OAuth2 토큰 종류 이름)


class UserOut(BaseModel):
    """본인 정보 응답. 비밀번호·내부 카운터는 싣지 않는다."""

    id: int
    email: str
    nickname: str
    gender: Gender
    is_admin: bool  # 화면에서 관리자 메뉴를 보일지 정한다. 실제 권한은 require_admin이 검사한다
