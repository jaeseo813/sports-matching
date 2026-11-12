# ruff: noqa: F401, F811  (pytest 픽스처를 test_matches_api에서 가져와 쓴다)
"""종목 규칙(/sports), 내 근처 구장(/me/venues), 매치 응답의 is_host. 실제 MariaDB, 항상 롤백."""

from httpx import AsyncClient

from tests.test_matches_api import api, login, make_match, session, venue_id

NEAR = {
    "label": "집",
    "lat": 37.5,
    "lng": 127.01,
    "max_distance_km": 5,
}  # 테스트 구장(127.0, 37.5)에서 약 1km
FAR = {"label": "먼 곳", "lat": 35.1, "lng": 129.0, "max_distance_km": 5}


async def test_sports_lists_rules_from_registry(api: AsyncClient) -> None:
    me = await login(api, 1)
    res = await api.get("/api/v1/sports", headers=me)
    assert res.status_code == 200
    by_id = {s["id"]: s for s in res.json()}
    assert set(by_id) == {"basketball", "football", "badminton"}
    assert by_id["badminton"]["players_per_team"] == [1, 2]
    assert sorted(by_id["badminton"]["tier_labels"]) == ["1", "2", "3", "4", "5"]


async def test_venues_near_me_needs_location(api: AsyncClient, venue_id: int) -> None:
    me = await login(api, 1)
    res = await api.get("/api/v1/me/venues", headers=me)
    assert res.status_code == 409
    assert res.json()["detail"]["code"] == "LOCATION_NOT_SET"


async def test_venues_near_me_uses_registered_points(api: AsyncClient, venue_id: int) -> None:
    me = await login(api, 1)
    await api.put("/api/v1/me/locations/1", json=FAR, headers=me)
    assert (await api.get("/api/v1/me/venues", headers=me)).json() == []
    await api.put("/api/v1/me/locations/2", json=NEAR, headers=me)
    found = (await api.get("/api/v1/me/venues?sport=badminton", headers=me)).json()
    assert [v["id"] for v in found] == [venue_id]
    assert 0 < found[0]["distance_km"] < 2
    assert (await api.get("/api/v1/me/venues?sport=football", headers=me)).json() == []
    assert (await api.get("/api/v1/me/venues?sport=curling", headers=me)).status_code == 422


async def test_is_host_only_for_the_host(api: AsyncClient, venue_id: int) -> None:
    host, other = await login(api, 1), await login(api, 2)
    created = await api.post(
        "/api/v1/matches",
        json={
            "sport": "badminton",
            "venue_id": venue_id,
            "title": "주최자 확인",
            "starts_at": "2099-01-01T10:00:00+00:00",
            "duration_min": 60,
            "team_size": 1,
        },
        headers=host,
    )
    assert created.json()["is_host"] is True
    assert created.json()["my_status"] == "accepted"
    mid = created.json()["id"]
    assert (await api.get(f"/api/v1/matches/{mid}", headers=host)).json()["is_host"] is True
    assert (await api.get(f"/api/v1/matches/{mid}", headers=other)).json()["is_host"] is False
    listed = {m["id"]: m for m in (await api.get("/api/v1/matches", headers=other)).json()}
    assert listed[mid]["is_host"] is False
