from fastapi import HTTPException

from app.models.user import User, UserLocation, UserSkill
from app.repositories.profile import ProfileRepository
from app.schemas.profile import LocationIn, LocationOut, SkillIn, SkillOut
from app.services.skill import initial_skill, tier_from_rating
from app.sports.registry import SPORTS

_TREND = {-1: "down", 0: "same", 1: "up"}


def _error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


def skill_out(skill: UserSkill) -> SkillOut:
    return SkillOut(
        sport=skill.sport,
        tier=tier_from_rating(skill.rating),
        years_played=skill.years_played,
        positions=skill.positions,
        trend=_TREND.get(skill.trend, "same"),
    )


async def list_skills(repo: ProfileRepository, user: User) -> list[SkillOut]:
    return [skill_out(s) for s in await repo.list_skills(user.id)]


async def set_skill(repo: ProfileRepository, user: User, sport: str, data: SkillIn) -> SkillOut:
    rules = SPORTS.get(sport)
    if rules is None:
        raise _error(422, "UNKNOWN_SPORT", "지원하지 않는 종목입니다")
    if data.positions and not set(data.positions) <= set(rules.positions):
        raise _error(422, "UNKNOWN_POSITION", "이 종목에 없는 포지션입니다")
    skill = await repo.get_skill(user.id, sport)
    if skill is None:
        start = initial_skill(data.self_tier, data.years_played)
        skill = await repo.add_skill(
            UserSkill(
                user_id=user.id,
                sport=sport,
                self_tier=data.self_tier,
                years_played=data.years_played,
                rating=start.rating,
                rd=start.rd,
                volatility=start.volatility,
                positions=data.positions,
            )
        )
    else:  # 이미 경기를 하며 쌓인 rating은 자기평가를 바꿔도 초기화하지 않는다
        skill.self_tier = data.self_tier
        skill.years_played = data.years_played
        skill.positions = data.positions
    await repo.commit()
    return skill_out(skill)


async def list_locations(repo: ProfileRepository, user: User) -> list[LocationOut]:
    return [
        LocationOut(slot=loc.slot, label=loc.label, max_distance_km=loc.max_distance_km)
        for loc in await repo.list_locations(user.id)
    ]


async def set_location(
    repo: ProfileRepository, user: User, slot: int, data: LocationIn
) -> LocationOut:
    if slot not in (1, 2):
        raise _error(422, "INVALID_SLOT", "기준점은 1번 또는 2번만 쓸 수 있습니다")
    loc = await repo.get_location(user.id, slot)
    if loc is None:
        loc = await repo.add_location(
            UserLocation(
                user_id=user.id,
                slot=slot,
                label=data.label,
                point=(data.lng, data.lat),  # (lng, lat) 순서
                max_distance_km=data.max_distance_km,
            )
        )
    else:
        loc.label = data.label
        loc.point = (data.lng, data.lat)
        loc.max_distance_km = data.max_distance_km
    await repo.commit()
    return LocationOut(slot=loc.slot, label=loc.label, max_distance_km=loc.max_distance_km)


async def delete_location(repo: ProfileRepository, user: User, slot: int) -> None:
    await repo.delete_location(user.id, slot)  # user_id 조건이 걸려 있어 본인 것만 지워진다
    await repo.commit()
