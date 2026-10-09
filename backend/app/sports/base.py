"""종목별 규칙의 공통 형태. DB·IO 없는 순수 데이터만 둔다 (services/balancer.py 등이 이걸 읽는다)."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SportRules:
    id: str  # 프론트 src/sports/<id>/ 와 동일
    name: str
    team_count: int  # 매치당 팀 수
    players_per_team: tuple[int, ...]  # 허용되는 팀당 인원 (예: 농구 3, 5)
    positions: tuple[str, ...] = ()  # 빈 튜플이면 포지션 없음
    required_per_team: dict[str, int] = field(default_factory=dict)  # 팀당 필수 포지션 (예: GK 1)
    tier_labels: dict[int, str] = field(default_factory=dict)  # 티어 1~5 설명 (온보딩용)
