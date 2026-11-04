from typing import Annotated

from fastapi import APIRouter, Path, Response

from app.api.deps import CurrentUser, ProfileRepo
from app.schemas.profile import (
    BlockOut,
    LocationIn,
    LocationOut,
    PreferencesIn,
    PreferencesOut,
    SkillIn,
    SkillOut,
)
from app.services import profile as profile_service

router = APIRouter(prefix="/me", tags=["me"])


@router.get("/skills", response_model=list[SkillOut])
async def list_skills(user: CurrentUser, repo: ProfileRepo) -> list[SkillOut]:
    return await profile_service.list_skills(repo, user)


@router.put("/skills/{sport}", response_model=SkillOut)
async def set_skill(
    sport: Annotated[str, Path(max_length=20)], data: SkillIn, user: CurrentUser, repo: ProfileRepo
) -> SkillOut:
    return await profile_service.set_skill(repo, user, sport, data)


@router.get("/locations", response_model=list[LocationOut])
async def list_locations(user: CurrentUser, repo: ProfileRepo) -> list[LocationOut]:
    return await profile_service.list_locations(repo, user)


@router.put("/locations/{slot}", response_model=LocationOut)
async def set_location(
    slot: Annotated[int, Path(ge=1, le=2)], data: LocationIn, user: CurrentUser, repo: ProfileRepo
) -> LocationOut:
    return await profile_service.set_location(repo, user, slot, data)


@router.delete("/locations/{slot}", status_code=204)
async def delete_location(
    slot: Annotated[int, Path(ge=1, le=2)], user: CurrentUser, repo: ProfileRepo
) -> Response:
    await profile_service.delete_location(repo, user, slot)
    return Response(status_code=204)


@router.get("/preferences", response_model=PreferencesOut)
async def get_preferences(user: CurrentUser) -> PreferencesOut:
    return profile_service.get_preferences(user)


@router.put("/preferences", response_model=PreferencesOut)
async def set_preferences(
    data: PreferencesIn, user: CurrentUser, repo: ProfileRepo
) -> PreferencesOut:
    return await profile_service.set_preferences(repo, user, data)


@router.get("/blocks", response_model=list[BlockOut])
async def list_blocks(user: CurrentUser, repo: ProfileRepo) -> list[BlockOut]:
    return await profile_service.list_blocks(repo, user)


@router.put("/blocks/{user_id}", status_code=204)
async def block(
    user_id: Annotated[int, Path(ge=1)], user: CurrentUser, repo: ProfileRepo
) -> Response:
    await profile_service.block(repo, user, user_id)
    return Response(status_code=204)


@router.delete("/blocks/{user_id}", status_code=204)
async def unblock(
    user_id: Annotated[int, Path(ge=1)], user: CurrentUser, repo: ProfileRepo
) -> Response:
    await profile_service.unblock(repo, user, user_id)
    return Response(status_code=204)
