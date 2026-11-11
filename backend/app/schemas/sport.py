from pydantic import BaseModel


class SportOut(BaseModel):
    """종목 규칙(공개 마스터 데이터). 화면의 팀 인원·포지션·티어 설명이 이 값을 쓴다."""

    id: str
    name: str
    team_count: int
    players_per_team: list[int]
    positions: list[str]
    tier_labels: dict[int, str]
