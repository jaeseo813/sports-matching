# ruff: noqa: F401, F811  (pytest 픽스처를 test_matches_api에서 가져와 쓴다)
"""출석·상호 평가·레이팅 반영. 실제 MariaDB로 검증하고 항상 롤백한다."""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.match import Match
from app.models.user import User, UserSkill
from tests.test_matches_api import api, login, make_match, session, venue_id
from tests.test_teams_api import doubles_full, fill

SKILL = {"self_tier": 3, "years_played": 2}


class Game:
    def __init__(
        self, host: dict[str, str], users: list[dict[str, str]], mid: int, ids: list[int]
    ) -> None:
        self.host, self.users, self.mid = host, users, mid
        self.ids = ids  # [host, u2, u3, u4]
        self.base = f"/api/v1/matches/{mid}"
        self.everyone = [host, *users]


async def user_id(api: AsyncClient, headers: dict[str, str]) -> int:
    return int((await api.get("/api/v1/auth/me", headers=headers)).json()["id"])


async def start_game(api: AsyncClient, venue_id: int) -> Game:
    host, users, mid = await doubles_full(api, venue_id)
    ids = [await user_id(api, h) for h in (host, *users)]
    for h in (host, *users):
        assert (
            await api.put("/api/v1/me/skills/badminton", json=SKILL, headers=h)
        ).status_code == 200
    return Game(host, users, mid, ids)


async def finish(api: AsyncClient, g: Game, *, attended: bool = True) -> None:
    for step in ("confirm", "start"):
        assert (await api.post(f"{g.base}/{step}", headers=g.host)).status_code == 200
    body = {"attendances": [{"user_id": uid, "attended": attended} for uid in g.ids]}
    assert (await api.put(f"{g.base}/attendance", json=body, headers=g.host)).status_code == 204
    assert (await api.post(f"{g.base}/complete", headers=g.host)).status_code == 200


def review(reviewee: int, verdict: str, flag: bool = False) -> dict[str, object]:
    return {"reviewee_id": reviewee, "verdict": verdict, "manner_flag": flag}


async def rating_of(session: AsyncSession, uid: int) -> float:
    return float(
        (
            await session.execute(select(UserSkill.rating).where(UserSkill.user_id == uid))
        ).scalar_one()
    )


async def test_rating_flow_updates_ratings_trend_and_marks_rated(
    api: AsyncClient, venue_id: int, session: AsyncSession
) -> None:
    g = await start_game(api, venue_id)
    await finish(api, g)
    h, (u2, u3, u4) = g.host, g.users
    host_id, id2, id3, id4 = g.ids
    for who, target, verdict in (
        (u2, id3, "better"),
        (u3, id2, "worse"),
        (u4, host_id, "similar"),
        (h, id4, "similar"),
    ):
        assert (
            await api.post(f"{g.base}/reviews", json=review(target, verdict), headers=who)
        ).status_code == 204
    before = {uid: await rating_of(session, uid) for uid in g.ids}
    res = await api.post(f"{g.base}/rate", headers=h)
    assert res.json() == {"applied": True, "updated": 4}
    assert await rating_of(session, id3) > before[id3]  # 더 낫다고 평가받음
    assert await rating_of(session, id2) < before[id2]
    assert abs(await rating_of(session, id3) - before[id3]) <= 80  # 경기당 상한
    match = (await session.execute(select(Match).where(Match.id == g.mid))).scalar_one()
    assert match.rated_at is not None
    assert (
        await session.execute(select(User.games_played).where(User.id == id3))
    ).scalar_one() == 1
    skills = (await api.get("/api/v1/me/skills", headers=u3)).json()
    assert skills[0]["trend"] == "up" and "rating" not in str(skills)
    again = await api.post(f"{g.base}/rate", headers=h)
    assert again.status_code == 409 and again.json()["detail"]["code"] == "ALREADY_RATED"
    late = await api.post(f"{g.base}/reviews", json=review(id2, "similar"), headers=u4)
    assert late.status_code == 409 and late.json()["detail"]["code"] == "REVIEW_CLOSED"


async def test_rating_held_when_too_few_reviewers_and_retry_later(
    api: AsyncClient, venue_id: int, session: AsyncSession
) -> None:
    g = await start_game(api, venue_id)
    await finish(api, g)
    u2, u3 = g.users[0], g.users[1]
    await api.post(
        f"{g.base}/reviews", json=review(g.ids[2], "better"), headers=u2
    )  # 4명 중 1명만 평가
    held = await api.post(f"{g.base}/rate", headers=g.host)
    assert held.json() == {"applied": False, "updated": 0}
    match = (await session.execute(select(Match).where(Match.id == g.mid))).scalar_one()
    assert match.rated_at is None  # 보류라서 표시하지 않는다
    await api.post(f"{g.base}/reviews", json=review(g.ids[1], "worse"), headers=u3)
    assert (await api.post(f"{g.base}/rate", headers=g.host)).json()["applied"] is True


async def test_same_pair_within_30_days_is_not_counted_twice(
    api: AsyncClient, venue_id: int
) -> None:
    g = await start_game(api, venue_id)
    await finish(api, g)
    id2, id3 = g.ids[1], g.ids[2]
    await api.post(f"{g.base}/reviews", json=review(id3, "better"), headers=g.users[0])
    await api.post(f"{g.base}/reviews", json=review(id2, "worse"), headers=g.users[1])
    assert (await api.post(f"{g.base}/rate", headers=g.host)).json()["applied"] is True
    # 같은 사람들로 새 경기를 열어 같은 쌍을 다시 평가해도 반영되지 않는다
    second = await make_match(api, g.host, venue_id, team_size=2)
    await fill(api, g.host, second, g.users)
    g2 = Game(g.host, g.users, second, g.ids)
    await finish(api, g2)
    await api.post(f"{g2.base}/reviews", json=review(id3, "better"), headers=g.users[0])
    await api.post(f"{g2.base}/reviews", json=review(id2, "worse"), headers=g.users[1])
    assert (await api.post(f"{g2.base}/rate", headers=g.host)).json() == {
        "applied": False,
        "updated": 0,
    }


async def test_manner_flag_lowers_manner_score_separately_from_rating(
    api: AsyncClient, venue_id: int, session: AsyncSession
) -> None:
    g = await start_game(api, venue_id)
    await finish(api, g)
    id2, id3 = g.ids[1], g.ids[2]
    await api.post(f"{g.base}/reviews", json=review(id3, "similar", flag=True), headers=g.users[0])
    await api.post(f"{g.base}/reviews", json=review(id2, "similar"), headers=g.users[1])
    await api.post(f"{g.base}/rate", headers=g.host)
    flagged = (await session.execute(select(User.manner_score).where(User.id == id3))).scalar_one()
    clean = (await session.execute(select(User.manner_score).where(User.id == id2))).scalar_one()
    assert flagged < 3.0 < clean
    assert await rating_of(session, id3) == await rating_of(
        session, id2
    )  # 서로 비슷하다고 했으므로 레이팅은 같다


async def test_no_show_is_counted_and_can_be_corrected(
    api: AsyncClient, venue_id: int, session: AsyncSession
) -> None:
    g = await start_game(api, venue_id)
    for step in ("confirm", "start"):
        await api.post(f"{g.base}/{step}", headers=g.host)
    absent = g.ids[3]
    put = lambda attended: api.put(  # noqa: E731
        f"{g.base}/attendance",
        json={"attendances": [{"user_id": absent, "attended": attended}]},
        headers=g.host,
    )
    assert (await put(False)).status_code == 204
    assert (await put(False)).status_code == 204  # 같은 값을 다시 보내도 중복 집계되지 않는다
    count = lambda: session.execute(select(User.no_show_count).where(User.id == absent))  # noqa: E731
    assert (await count()).scalar_one() == 1
    assert (await put(True)).status_code == 204  # 잘못 기록했다면 되돌린다
    assert (await count()).scalar_one() == 0
