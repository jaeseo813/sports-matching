# ruff: noqa: F401, F811  (pytest 픽스처를 test_auth_api에서 가져와 쓴다)
import jwt
import pytest
from httpx import AsyncClient

from app.core.config import get_settings
from tests.test_auth_api import SIGNUP, FakeUserRepo, _login, api, repo  # noqa: F401


async def test_me_requires_token(api: AsyncClient) -> None:
    res = await api.get("/api/v1/auth/me")
    assert res.status_code == 401


async def test_refresh_token_cannot_be_used_as_access(api: AsyncClient) -> None:
    tokens = await _login(api)
    res = await api.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['refresh_token']}"}
    )
    assert res.status_code == 401


async def test_alg_none_token_rejected(api: AsyncClient) -> None:
    await _login(api)
    forged = jwt.encode(
        {"sub": "1", "type": "access", "jti": "x", "exp": 9999999999}, key="", algorithm="none"
    )
    res = await api.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert res.status_code == 401


async def test_token_signed_with_wrong_secret_rejected(api: AsyncClient) -> None:
    await _login(api)
    forged = jwt.encode(
        {"sub": "1", "type": "access", "jti": "x", "exp": 9999999999},
        "wrong-secret-" * 4,
        algorithm="HS256",
    )
    res = await api.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert res.status_code == 401


async def test_refresh_reuse_revokes_whole_family(api: AsyncClient) -> None:
    tokens = await _login(api)
    first = await api.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert first.status_code == 200
    replay = await api.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert replay.status_code == 401
    # 재사용이 감지되면 정상 갱신으로 받은 새 토큰도 함께 무효화된다
    newer = await api.post(
        "/api/v1/auth/refresh", json={"refresh_token": first.json()["refresh_token"]}
    )
    assert newer.status_code == 401


async def test_login_rate_limited(api: AsyncClient) -> None:
    await api.post("/api/v1/auth/signup", json=SIGNUP)
    codes = [
        (
            await api.post("/api/v1/auth/login", json={"email": SIGNUP["email"], "password": "bad"})
        ).status_code
        for _ in range(6)
    ]
    assert codes[:5] == [401] * 5
    assert codes[5] == 429


async def test_responses_never_include_password(api: AsyncClient) -> None:
    res = await api.post("/api/v1/auth/signup", json=SIGNUP)
    assert "password" not in res.text
    assert SIGNUP["password"] not in res.text


def test_jwt_secret_default_is_rejected_in_production() -> None:
    from app.core.config import Settings

    with pytest.raises(ValueError):
        Settings(env="production", jwt_secret="change-me")
    assert get_settings().jwt_secret  # 로컬 기본값은 허용
