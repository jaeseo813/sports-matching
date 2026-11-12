"""개발 DB 더미(시드) 데이터. 화면을 실제 API 경로로 확인할 때 쓴다.

    cd backend && uv run python -m scripts.seed_dev           # 시드를 지우고 다시 넣는다
    cd backend && uv run python -m scripts.seed_dev --clear   # 시드만 지운다

- 사용자·자기평가·활동 지역·매치·신청은 실제 API를 앱 안에서 호출해 만든다
  (가입·레이팅 초기값·정원 계산이 서비스와 똑같이 처리된다).
- 구장은 관리자 전용 마스터 데이터라 모델로 직접 넣는다.
- 시드는 이메일 도메인(@seed.teamup.test)과 구장 이름 접미사("(시드)")로 구분한다.
  다시 실행해도 쌓이지 않고, 시드가 아닌 데이터는 건드리지 않는다.
- 실명·실주소 없음(AGENTS.md 8절). 좌표는 구 중심 근처의 가상 지점이다.
- 개발 DB에서만 실행된다(ENV=local, 테스트 DB 금지).
"""

import argparse
import asyncio
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, or_, select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.api.v1.matches import apply_limiter
from app.core.config import get_settings
from app.core.ratelimit import login_limiter
from app.main import app
from app.models.match import Match, Participation, TeamAssignment
from app.models.user import User
from app.models.venue import Venue, VenueSport

SEED_DOMAIN = "seed.teamup.test"
SEED_VENUE_SUFFIX = "(시드)"
PASSWORD = "password123"  # noqa: S105 (시드 계정 공용 더미 비밀번호, 개발 DB 전용)
KST = ZoneInfo("Asia/Seoul")

# 활동 지역 후보는 온보딩 화면(frontend/src/pages/Onboarding.tsx)과 같은 구 중심 좌표
AREAS = {
    "동대문구": (37.574, 127.04),
    "성북구": (37.589, 127.017),
    "강남구": (37.517, 127.047),
    "마포구": (37.566, 126.902),
}

# (이름, (lng, lat), 종목) — POINT(lng, lat) 순서
VENUES = [
    ("새솔 실내체육관", (127.045, 37.578), ("badminton", "basketball")),
    ("한빛 풋살파크", (127.035, 37.570), ("football",)),
    ("다온 체육관", (127.020, 37.592), ("badminton", "basketball")),
    ("누리 풋살장", (127.012, 37.585), ("football",)),
    ("모아 스포츠센터", (127.050, 37.512), ("badminton", "basketball", "football")),
    ("하늘 체육관", (126.905, 37.563), ("badminton", "basketball")),
]


@dataclass
class SeedUser:
    key: str
    nickname: str
    gender: str
    skills: dict[str, tuple[int, int]]  # 종목: (자기평가 티어, 경력 연수)
    area: str
    radius_km: int


USERS = [
    SeedUser("s1", "민트슈터", "male", {"basketball": (3, 4), "football": (2, 1)}, "동대문구", 10),
    SeedUser("s2", "라임스매시", "female", {"badminton": (4, 6)}, "동대문구", 5),
    SeedUser("s3", "코트러너", "male", {"basketball": (4, 8)}, "성북구", 10),
    SeedUser("s4", "골키퍼곰", "male", {"football": (3, 3)}, "동대문구", 10),
    SeedUser("s5", "셔틀콕", "female", {"badminton": (2, 1)}, "성북구", 5),
    SeedUser("s6", "새벽드리블", "other", {"basketball": (2, 2), "football": (3, 2)}, "강남구", 10),
    SeedUser("s7", "클리어장인", "male", {"badminton": (3, 3)}, "마포구", 5),
    SeedUser("s8", "패스요정", "female", {"football": (1, 0), "badminton": (1, 0)}, "동대문구", 10),
]


@dataclass
class SeedMatch:
    host: str
    sport: str
    venue: str
    title: str
    days: int  # 오늘부터 며칠 뒤 (실행할 때마다 다시 계산해 지난 경기가 되지 않게)
    at: str  # KST "HH:MM"
    team_size: int
    tiers: tuple[int, int]
    description: str
    gender_policy: str = "any"
    accepted: list[str] = field(default_factory=list)  # 수락까지 된 신청자
    applied: list[str] = field(default_factory=list)  # 승인 대기 신청자


MATCHES = [
    SeedMatch(
        "s1",
        "basketball",
        "새솔 실내체육관",
        "평일 저녁 3:3 픽업",
        1,
        "19:00",
        3,
        (2, 4),
        "가볍게 3:3 돌려요. 끝나고 자유투 내기.",
        accepted=["s3"],
        applied=["s6"],
    ),
    SeedMatch(
        "s3",
        "basketball",
        "다온 체육관",
        "주말 5:5 풀코트",
        3,
        "14:00",
        5,
        (1, 5),
        "실력 상관없이 모두 환영해요. 팀은 밸런서로 나눠요.",
        accepted=["s1"],
    ),
    SeedMatch(
        "s4",
        "football",
        "한빛 풋살파크",
        "목요일 공강 풋살",
        2,
        "15:00",
        5,
        (1, 3),
        "공강 시간에 1시간 뛰어요. 조끼는 준비해 갈게요.",
        accepted=["s8"],
        applied=["s6"],
    ),
    SeedMatch(
        "s6",
        "football",
        "모아 스포츠센터",
        "금요일 밤 6:6",
        4,
        "21:00",
        6,
        (2, 5),
        "경기 위주로 진지하게 뛰어요. 슬라이딩 태클은 금지예요.",
    ),
    SeedMatch(
        "s2",
        "badminton",
        "새솔 실내체육관",
        "퇴근 후 복식",
        1,
        "20:00",
        2,
        (3, 5),
        "2게임씩 파트너를 바꿔 가며 쳐요.",
        accepted=["s7"],
        applied=["s5"],
    ),
    SeedMatch(
        "s5",
        "badminton",
        "다온 체육관",
        "아침 단식 랠리",
        2,
        "08:00",
        1,
        (1, 3),
        "아침 운동 삼아 랠리 위주로 쳐요.",
        gender_policy="female_only",
        accepted=["s8"],
    ),
    SeedMatch(
        "s7",
        "badminton",
        "하늘 체육관",
        "마포 복식 모임",
        5,
        "19:30",
        2,
        (2, 4),
        "라켓이 없으면 빌려 드려요.",
    ),
    SeedMatch(
        "s8",
        "football",
        "누리 풋살장",
        "초보 환영 풋살",
        6,
        "10:00",
        5,
        (1, 2),
        "처음 오셔도 괜찮아요. 골키퍼는 돌아가며 봐요.",
    ),
]


def email_of(key: str) -> str:
    return f"{key}@{SEED_DOMAIN}"


def check_target() -> str:
    """시드는 개발 DB에만 넣는다. 운영·스테이징·테스트 DB면 멈춘다."""
    settings = get_settings()
    name = make_url(settings.database_url).database or ""
    if settings.env != "local":
        sys.exit(f"ENV={settings.env}: 시드는 로컬 개발 DB에서만 실행합니다")
    if name.endswith("_test") or make_url(settings.database_url) == make_url(
        settings.test_database_url
    ):
        sys.exit(f"{name}: 테스트 DB에는 시드를 넣지 않습니다")
    return name


async def clear(session: AsyncSession) -> int:
    """시드만 지운다. 외래키 RESTRICT 때문에 매치 → 남은 신청·팀 배정 → 사용자 → 구장 순서."""
    seed_users = select(User.id).where(User.email.like(f"%@{SEED_DOMAIN}"))
    seed_venues = select(Venue.id).where(Venue.name.like(f"%{SEED_VENUE_SUFFIX}"))
    user_ids = list((await session.execute(seed_users)).scalars())
    # 매치를 지우면 신청·팀 배정·리뷰는 CASCADE로 함께 지워진다
    await session.execute(
        delete(Match).where(or_(Match.host_id.in_(seed_users), Match.venue_id.in_(seed_venues)))
    )
    # 시드 사용자가 시드가 아닌 매치에 남긴 기록
    await session.execute(delete(Participation).where(Participation.user_id.in_(user_ids)))
    await session.execute(delete(TeamAssignment).where(TeamAssignment.user_id.in_(user_ids)))
    # 자기평가·활동 지역·차단은 CASCADE, 리뷰 작성자·대상은 SET NULL
    await session.execute(delete(User).where(User.id.in_(user_ids)))
    await session.execute(delete(Venue).where(Venue.name.like(f"%{SEED_VENUE_SUFFIX}")))
    await session.commit()
    return len(user_ids)


async def add_venues(session: AsyncSession) -> dict[str, int]:
    ids: dict[str, int] = {}
    for name, point, sports in VENUES:
        venue = Venue(name=f"{name}{SEED_VENUE_SUFFIX}", address="가상 주소", point=point)
        session.add(venue)
        await session.flush()
        ids[name] = venue.id
        session.add_all(VenueSport(venue_id=venue.id, sport=s) for s in sports)
    await session.commit()
    return ids


class Api:
    """앱을 HTTP 서버 없이 그대로 호출한다. 실패하면 응답을 보여 주고 멈춘다."""

    def __init__(self, client: AsyncClient) -> None:
        self.client = client
        self.headers: dict[str, dict[str, str]] = {}

    async def call(self, method: str, path: str, key: str | None = None, **kw: object) -> object:
        headers = self.headers[key] if key else None
        res = await self.client.request(method, f"/api/v1{path}", headers=headers, **kw)  # type: ignore[arg-type]
        if res.status_code >= 400:
            sys.exit(f"{method} {path} → {res.status_code} {res.text}")
        return res.json() if res.content else None

    async def signup_and_login(self, u: SeedUser) -> None:
        body = {
            "email": email_of(u.key),
            "password": PASSWORD,
            "nickname": u.nickname,
            "gender": u.gender,
            "birth_year": 2000,
        }
        await self.call("POST", "/auth/signup", json=body)
        login_limiter.reset()  # 시드 계정을 연달아 로그인하므로 분당 한도를 비운다
        tokens = await self.call(
            "POST", "/auth/login", json={"email": body["email"], "password": PASSWORD}
        )
        assert isinstance(tokens, dict)  # noqa: S101
        self.headers[u.key] = {"Authorization": f"Bearer {tokens['access_token']}"}


def starts_at(days: int, at: str) -> str:
    hour, minute = map(int, at.split(":"))
    day = datetime.now(KST).date() + timedelta(days=days)
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=KST).isoformat()


async def seed(venue_ids: dict[str, int]) -> int:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://seed") as client:
        api = Api(client)
        nick = {u.key: u.nickname for u in USERS}
        for u in USERS:
            await api.signup_and_login(u)
            for sport, (tier, years) in u.skills.items():
                body = {"self_tier": tier, "years_played": years}
                await api.call("PUT", f"/me/skills/{sport}", u.key, json=body)
            lat, lng = AREAS[u.area]
            loc = {"label": u.area, "lat": lat, "lng": lng, "max_distance_km": u.radius_km}
            await api.call("PUT", "/me/locations/1", u.key, json=loc)

        for m in MATCHES:
            created = await api.call(
                "POST",
                "/matches",
                m.host,
                json={
                    "sport": m.sport,
                    "venue_id": venue_ids[m.venue],
                    "title": m.title,
                    "description": m.description,
                    "starts_at": starts_at(m.days, m.at),
                    "duration_min": 90,
                    "team_size": m.team_size,
                    "tier_min": m.tiers[0],
                    "tier_max": m.tiers[1],
                    "gender_policy": m.gender_policy,
                },
            )
            assert isinstance(created, dict)  # noqa: S101
            mid = created["id"]
            for key in m.accepted + m.applied:
                apply_limiter.reset()
                await api.call("POST", f"/matches/{mid}/apply", key, json={})
            parts = await api.call("GET", f"/matches/{mid}/participations", m.host)
            assert isinstance(parts, list)  # noqa: S101
            by_nick = {p["nickname"]: p["id"] for p in parts}
            for key in m.accepted:
                await api.call(
                    "POST", f"/matches/{mid}/participations/{by_nick[nick[key]]}/accept", m.host
                )
        return len(MATCHES)


async def main(clear_only: bool) -> None:
    db = check_target()
    engine = create_async_engine(get_settings().database_url)
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            removed = await clear(session)
            print(f"[{db}] 기존 시드 사용자 {removed}명과 시드 매치·구장을 지웠습니다")
            if clear_only:
                return
            venue_ids = await add_venues(session)
        n = await seed(venue_ids)
    finally:
        await engine.dispose()
    print(f"[{db}] 구장 {len(VENUES)}곳, 사용자 {len(USERS)}명, 매치 {n}개를 넣었습니다")
    print(f"\n로그인 (비밀번호 모두 {PASSWORD})")
    for u in USERS:
        sports = ", ".join(f"{s} {t}단계" for s, (t, _) in u.skills.items())
        print(f"  {email_of(u.key):<24} {u.nickname:<8} {u.area} · {sports}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="개발 DB 시드 데이터")
    parser.add_argument("--clear", action="store_true", help="시드만 지우고 끝낸다")
    asyncio.run(main(parser.parse_args().clear))
