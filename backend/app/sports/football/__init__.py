from app.sports.base import SportRules

# TODO(축구/풋살 담당): 인원(풋살 5/6, 축구 11), 티어 설명 확정
RULES = SportRules(
    id="football",
    name="축구/풋살",
    team_count=2,
    players_per_team=(5, 6, 11),
    positions=("GK", "FIELD"),
    required_per_team={"GK": 1},
)
