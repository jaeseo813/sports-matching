from fastapi import APIRouter, Depends, Response

from app.api.deps import CurrentUser, UserRepo
from app.core.ratelimit import login_limiter
from app.core.token_store import token_store
from app.schemas.auth import LoginIn, RefreshIn, SignupIn, TokenOut, UserOut
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=UserOut, status_code=201)
async def signup(data: SignupIn, repo: UserRepo) -> UserOut:
    user = await auth_service.signup(repo, data)
    return UserOut.model_validate(user, from_attributes=True)


@router.post("/login", response_model=TokenOut, dependencies=[Depends(login_limiter)])
async def login(data: LoginIn, repo: UserRepo) -> TokenOut:
    return await auth_service.login(repo, token_store, data.email, data.password)


@router.post("/refresh", response_model=TokenOut)
async def refresh(data: RefreshIn, repo: UserRepo) -> TokenOut:
    return await auth_service.refresh(repo, token_store, data.refresh_token)


@router.post("/logout", status_code=204)
async def logout(data: RefreshIn) -> Response:
    auth_service.logout(token_store, data.refresh_token)
    return Response(status_code=204)


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user, from_attributes=True)
