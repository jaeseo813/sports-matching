from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

Lat = Annotated[float, Field(ge=33, le=39)]  # 국내 범위
Lng = Annotated[float, Field(ge=124, le=132)]


class VenueCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    address: str = Field(min_length=1, max_length=255)
    lat: Lat
    lng: Lng
    sports: list[str] = Field(min_length=1, max_length=10)


class VenueOut(BaseModel):
    id: int
    name: str
    address: str
    lat: float
    lng: float
    sports: list[str]
    distance_km: float | None = None  # nearby 조회에서만, 0.1km 단위로 반올림
