from app.sports.base import SportRules

# TODO(농구 담당): 포지션 사용 여부, 티어 설명 확정
RULES = SportRules(id="basketball", name="농구", team_count=2, players_per_team=(3, 5))
