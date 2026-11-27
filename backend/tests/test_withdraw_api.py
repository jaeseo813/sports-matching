# ruff: noqa: F401, F811  (pytest 픽스처를 test_matches_api에서 가져와 쓴다)
"""회원 탈퇴: 개인정보 삭제, 기록 보존, 주최 중이면 막기."""

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ratelimit import login_limiter
from app.models.review import PeerReview
from app.models.user import User, UserBlock, UserLocation, UserSkill
from tests.test_matches_api import api, login, make_match, session, venue_id
from tests.test_recommend_api import onboard

PW = "pw-12345678"  # tests.test_matches_api.login이 쓰는 비밀번호
W = "/api/v1/me/withdraw"


async def withdraw(api: AsyncClient, headers: dict[str, str], password: str = PW) -> int:
    login_limiter.reset()
    return (await api.post(W, json={"password": password}, headers=headers)).status_code


async def test_withdraw_removes_personal_data(
    api: AsyncClient, session: AsyncSession, venue_id: int
) -> None:
    host, me = await login(api, 1), await login(api, 2)
    await onboard(api, me)  # 실력·위치 등록
    me_id = (await api.get("/api/v1/auth/me", headers=me)).json()["id"]
    host_id = (await api.get("/api/v1/auth/me", headers=host)).json()["id"]
    await api.put(f"/api/v1/me/blocks/{host_id}", headers=me)
    assert await withdraw(api, me) == 204

    user = await session.get(User, me_id)
    assert user is not None and not user.is_active and user.deleted_at is not None
    assert "user2" not in user.nickname and user.email.endswith("@withdrawn.invalid")
    for model, col in ((UserLocation, UserLocation.user_id), (UserSkill, UserSkill.user_id)):
        n = await session.scalar(select(func.count()).select_from(model).where(col == me_id))
        assert n == 0
    blocks = await session.scalar(select(func.count()).select_from(UserBlock))
    assert blocks == 0

    # 토큰은 바로 무효, 같은 이메일·닉네임으로 다시 가입할 수 있다
    assert (await api.get("/api/v1/auth/me", headers=me)).status_code == 401
    login_limiter.reset()
    res = await api.post("/api/v1/auth/login", json={"email": "user2@example.com", "password": PW})
    assert res.status_code == 401
    await login(api, 2)


async def test_withdraw_cancels_applications_and_reopens_match(
    api: AsyncClient, venue_id: int
) -> None:
    host, me = await login(api, 1), await login(api, 2)
    mid = await make_match(api, host, venue_id)  # 단식, 정원 2
    await api.post(f"/api/v1/matches/{mid}/apply", headers=me)
    parts = (await api.get(f"/api/v1/matches/{mid}/participations", headers=host)).json()
    pid = next(p["id"] for p in parts if p["status"] == "applied")
    await api.post(f"/api/v1/matches/{mid}/participations/{pid}/accept", headers=host)
    assert (await api.get(f"/api/v1/matches/{mid}", headers=host)).json()["status"] == "full"
    assert await withdraw(api, me) == 204
    detail = (await api.get(f"/api/v1/matches/{mid}", headers=host)).json()
    assert (detail["status"], detail["joined"]) == ("open", 1)


async def test_withdraw_keeps_reviews(
    api: AsyncClient, session: AsyncSession, venue_id: int
) -> None:
    host, me = await login(api, 1), await login(api, 2)
    host_id = (await api.get("/api/v1/auth/me", headers=host)).json()["id"]
    me_id = (await api.get("/api/v1/auth/me", headers=me)).json()["id"]
    mid = await make_match(api, host, venue_id)
    session.add(PeerReview(match_id=mid, reviewer_id=me_id, reviewee_id=host_id, verdict="similar"))
    await session.flush()
    assert await withdraw(api, me) == 204
    kept = await session.scalar(select(func.count()).select_from(PeerReview))
    assert kept == 1


async def test_withdraw_blocked_while_hosting(api: AsyncClient, venue_id: int) -> None:
    host = await login(api, 1)
    mid = await make_match(api, host, venue_id)
    login_limiter.reset()
    res = await api.post(W, json={"password": PW}, headers=host)
    assert res.status_code == 409 and res.json()["detail"]["code"] == "HOSTING_MATCH"
    await api.post(f"/api/v1/matches/{mid}/cancel", headers=host)
    assert await withdraw(api, host) == 204  # 취소한 뒤에는 탈퇴할 수 있다


async def test_withdraw_wrong_password_and_auth(api: AsyncClient) -> None:
    me = await login(api, 1)
    assert await withdraw(api, me, "wrong-password") == 403
    assert (await api.get("/api/v1/auth/me", headers=me)).status_code == 200  # 그대로 남아 있다
    assert (await api.post(W, json={"password": PW})).status_code == 401
    login_limiter.reset()
    bad = await api.post(W, json={"password": PW, "x": 1}, headers=me)
    assert bad.status_code == 422
