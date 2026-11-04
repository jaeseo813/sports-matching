from collections.abc import AsyncIterator, Iterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_user_repo
from app.core.ratelimit import login_limiter
from app.core.token_store import token_store
from app.main import app
from app.models.enums import Gender
from app.models.user import User
from app.repositories.user import DuplicateUserError


class FakeUserRepo:
    """DB 없이 인증 흐름을 검증하기 위한 인메모리 저장소."""

    def __init__(self) -> None:
        self.users: dict[int, User] = {}

    async def get_by_email(self, email: str) -> User | None:
        return next((u for u in self.users.values() if u.email == email), None)

    async def get_by_id(self, user_id: int) -> User | None:
        return self.users.get(user_id)

    async def create(
        self, *, email: str, password: str, nickname: str, gender: Gender, birth_year: int
    ) -> User:
        if any(u.email == email or u.nickname == nickname for u in self.users.values()):
            raise DuplicateUserError
        user = User(
            id=len(self.users) + 1,
            email=email,
            password=password,
            nickname=nickname,
            gender=gender,
            birth_year=birth_year,
            is_active=True,
        )
        self.users[user.id] = user
        return user


SIGNUP = {
    "email": "a@example.com",
    "password": "pw-12345678",
    "nickname": "tester",
    "gender": "male",
    "birth_year": 1999,
}


@pytest.fixture
def repo() -> Iterator[FakeUserRepo]:
    fake = FakeUserRepo()
    app.dependency_overrides[get_user_repo] = lambda: fake
    login_limiter.reset()
    token_store.__init__()  # type: ignore[misc]
    yield fake
    app.dependency_overrides.clear()


@pytest.fixture
async def api(repo: FakeUserRepo) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def _login(api: AsyncClient) -> dict[str, str]:
    await api.post("/api/v1/auth/signup", json=SIGNUP)
    res = await api.post(
        "/api/v1/auth/login", json={"email": SIGNUP["email"], "password": SIGNUP["password"]}
    )
    assert res.status_code == 200
    body: dict[str, str] = res.json()
    return body


async def test_signup_login_me(api: AsyncClient) -> None:
    tokens = await _login(api)
    res = await api.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert res.status_code == 200
    assert res.json() == {"id": 1, "email": "a@example.com", "nickname": "tester", "gender": "male"}


async def test_signup_duplicate_and_underage(api: AsyncClient) -> None:
    await api.post("/api/v1/auth/signup", json=SIGNUP)
    dup = await api.post("/api/v1/auth/signup", json=SIGNUP)
    assert dup.status_code == 409
    assert dup.json()["detail"]["code"] == "ALREADY_EXISTS"
    young = await api.post(
        "/api/v1/auth/signup",
        json={**SIGNUP, "email": "b@example.com", "nickname": "kid", "birth_year": 2100},
    )
    assert young.status_code == 422


async def test_login_wrong_password(api: AsyncClient) -> None:
    await api.post("/api/v1/auth/signup", json=SIGNUP)
    res = await api.post("/api/v1/auth/login", json={"email": SIGNUP["email"], "password": "nope"})
    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "INVALID_CREDENTIALS"


async def test_refresh_rotates(api: AsyncClient) -> None:
    tokens = await _login(api)
    res = await api.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert res.status_code == 200
    assert res.json()["refresh_token"] != tokens["refresh_token"]


async def test_logout_invalidates_refresh(api: AsyncClient) -> None:
    tokens = await _login(api)
    out = await api.post("/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert out.status_code == 204
    res = await api.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert res.status_code == 401
