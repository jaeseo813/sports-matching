# ruff: noqa: F401, F811  (pytest 픽스처를 test_matches_api에서 가져와 쓴다)
from httpx import AsyncClient

from app.api.v1.matches import apply_limiter
from tests.test_matches_api import api, login, make_match, session, venue_id


async def test_match_endpoints_require_login(api: AsyncClient) -> None:
    for method, path in (
        ("get", "/api/v1/matches"),
        ("get", "/api/v1/matches/1"),
        ("post", "/api/v1/matches/1/apply"),
        ("post", "/api/v1/matches/1/confirm"),
        ("post", "/api/v1/matches/1/cancel"),
    ):
        assert (await getattr(api, method)(path)).status_code == 401, path


async def test_only_host_can_manage_match(api: AsyncClient, venue_id: int) -> None:
    host, other = await login(api, 1), await login(api, 2)
    mid = await make_match(api, host, venue_id)
    await api.post(f"/api/v1/matches/{mid}/apply", headers=other)
    for path in (
        f"/api/v1/matches/{mid}/confirm",
        f"/api/v1/matches/{mid}/cancel",
        f"/api/v1/matches/{mid}/participations/1/accept",
        f"/api/v1/matches/{mid}/participations/1/reject",
    ):
        res = await api.post(path, headers=other)
        assert res.status_code == 403, path
    assert (
        await api.get(f"/api/v1/matches/{mid}/participations", headers=other)
    ).status_code == 403


async def test_participation_id_of_another_match_is_not_accessible(
    api: AsyncClient, venue_id: int
) -> None:
    host_a, host_b, user = await login(api, 1), await login(api, 2), await login(api, 3)
    match_a = await make_match(api, host_a, venue_id)
    match_b = await make_match(api, host_b, venue_id)
    await api.post(f"/api/v1/matches/{match_a}/apply", headers=user)
    pid = (await api.get(f"/api/v1/matches/{match_a}/participations", headers=host_a)).json()[0][
        "id"
    ]
    # host_b는 자기 매치 경로에 남의 매치 신청 id를 넣어도 처리할 수 없다
    res = await api.post(f"/api/v1/matches/{match_b}/participations/{pid}/accept", headers=host_b)
    assert res.status_code == 404


async def test_cannot_cancel_someone_elses_application(api: AsyncClient, venue_id: int) -> None:
    host, user, attacker = await login(api, 1), await login(api, 2), await login(api, 3)
    mid = await make_match(api, host, venue_id)
    await api.post(f"/api/v1/matches/{mid}/apply", headers=user)
    assert (await api.delete(f"/api/v1/matches/{mid}/apply", headers=attacker)).status_code == 404
    assert (await api.get(f"/api/v1/matches/{mid}", headers=user)).json()["my_status"] == "applied"


async def test_apply_is_rate_limited(api: AsyncClient, venue_id: int) -> None:
    host, user = await login(api, 1), await login(api, 2)
    mid = await make_match(api, host, venue_id)
    codes = [
        (await api.post(f"/api/v1/matches/{mid}/apply", headers=user)).status_code
        for _ in range(11)
    ]
    assert codes[-1] == 429


async def test_response_exposes_no_pii(api: AsyncClient, venue_id: int) -> None:
    host = await login(api, 1)
    mid = await make_match(api, host, venue_id)
    text = (await api.get(f"/api/v1/matches/{mid}", headers=host)).text
    assert "example.com" not in text and "birth" not in text and "host_id" not in text


async def test_my_activity_requires_login_and_shows_only_own(
    api: AsyncClient, venue_id: int
) -> None:
    for path in ("/api/v1/me/summary", "/api/v1/me/matches"):
        assert (await api.get(path)).status_code == 401, path
    owner, other = await login(api, 1), await login(api, 2)
    await make_match(api, owner, venue_id)
    # 남의 매치는 내 예정 목록·요약에 보이지 않고, 사용자 id를 지정하는 파라미터도 없다
    assert (await api.get("/api/v1/me/matches", headers=other)).json() == []
    assert (await api.get("/api/v1/me/summary", headers=other)).json()["upcoming"] == 0
    res = await api.get("/api/v1/me/summary?user_id=1", headers=other)
    assert res.json()["upcoming"] == 0
