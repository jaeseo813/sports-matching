from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, UserRepo
from app.core.ratelimit import login_limiter
from app.schemas.auth import LoginIn, SignupIn, TokenOut, UserOut
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=UserOut, status_code=201)
async def signup(data: SignupIn, repo: UserRepo) -> UserOut:
    user = await auth_service.signup(repo, data)
    return UserOut.model_validate(user, from_attributes=True)


@router.post("/login", response_model=TokenOut, dependencies=[Depends(login_limiter)])
async def login(data: LoginIn, repo: UserRepo) -> TokenOut:
    return await auth_service.login(repo, data.email, data.password)


# 로그아웃은 클라이언트가 토큰을 지우는 것으로 끝난다 (서버에 세션 상태 없음)
@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user, from_attributes=True)
