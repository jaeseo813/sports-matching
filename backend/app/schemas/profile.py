from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.venue import Lat, Lng


class SkillIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    self_tier: int = Field(ge=1, le=5)
    years_played: int = Field(ge=0, le=60)
    positions: list[str] | None = Field(default=None, max_length=10)


class SkillOut(BaseModel):
    """숫자 레이팅은 싣지 않는다. 티어 배지와 추이만 보여준다."""

    sport: str
    tier: int
    years_played: int
    positions: list[str] | None
    trend: Literal["up", "same", "down"]


class LocationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=50)
    lat: Lat
    lng: Lng
    max_distance_km: int = Field(default=10, ge=1, le=50)


class LocationOut(BaseModel):
    """등록한 기준점의 이름과 반경만 돌려준다. 좌표 원본은 응답에 싣지 않는다."""

    slot: int
    label: str
    max_distance_km: int


TimeSlot = Literal["dawn", "morning", "afternoon", "evening"]  # 0-6 / 6-12 / 12-18 / 18-24시


class PreferencesIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preferred_slots: list[TimeSlot] = Field(max_length=4)


class PreferencesOut(BaseModel):
    preferred_slots: list[TimeSlot]


class BlockOut(BaseModel):
    user_id: int
    nickname: str
