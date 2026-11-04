from datetime import datetime

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from app.models.enums import GenderPolicy, MatchStatus, ParticipationStatus


class MatchCreateIn(BaseModel):
    """정원(capacity)은 받지 않는다. 종목 규칙의 팀 수 × team_size로 서버가 계산한다."""

    model_config = ConfigDict(extra="forbid")

    sport: str = Field(max_length=20)
    venue_id: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    starts_at: AwareDatetime
    duration_min: int = Field(ge=30, le=480)
    team_size: int = Field(ge=1, le=11)
    min_players: int | None = Field(default=None, ge=2)
    position: str | None = Field(default=None, max_length=20)  # 주최자 본인의 포지션
    gender_policy: GenderPolicy = GenderPolicy.ANY
    tier_min: int = Field(default=1, ge=1, le=5)
    tier_max: int = Field(default=5, ge=1, le=5)

    @model_validator(mode="after")
    def _tier_order(self) -> "MatchCreateIn":
        if self.tier_min > self.tier_max:
            raise ValueError("tier_min은 tier_max보다 클 수 없습니다")
        return self


class MatchOut(BaseModel):
    id: int
    sport: str
    host_nickname: str
    venue_id: int
    venue_name: str
    title: str
    description: str | None
    starts_at: datetime
    duration_min: int
    team_size: int
    capacity: int
    joined: int  # 수락된 인원
    min_players: int
    gender_policy: GenderPolicy
    tier_min: int
    tier_max: int
    status: MatchStatus
    my_status: ParticipationStatus | None = None  # 요청자의 신청 상태


class ParticipationOut(BaseModel):
    id: int
    nickname: str
    status: ParticipationStatus


class BreakdownOut(BaseModel):
    dist: float
    skill: float
    time: float
    host: float
    fill: float


class RecommendedOut(BaseModel):
    """설명 가능성이 핵심이라 score·breakdown·reasons를 항상 함께 내보낸다."""

    match: MatchOut
    score: float
    breakdown: BreakdownOut
    reasons: list[str]


class ApplyIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    position: str | None = Field(default=None, max_length=20)  # 희망 포지션 (종목 규칙으로 검증)


class TeamMemberOut(BaseModel):
    nickname: str
    tier: int  # 티어 배지. 숫자 레이팅은 노출하지 않는다
    position: str | None


class TeamOut(BaseModel):
    team_no: int
    members: list[TeamMemberOut]


class TeamsOut(BaseModel):
    teams: list[TeamOut]
    closeness: int  # 접전도 게이지 1~5
    is_manual: bool


class TeamAssignmentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: int = Field(ge=1)
    team_no: int = Field(ge=1, le=10)


class ManualTeamsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assignments: list[TeamAssignmentIn] = Field(min_length=2, max_length=60)
