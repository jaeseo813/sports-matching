from app.sports.badminton import RULES as BADMINTON
from app.sports.base import SportRules
from app.sports.basketball import RULES as BASKETBALL
from app.sports.football import RULES as FOOTBALL

# 종목을 추가하려면 app/sports/<id>/ 를 만들고 여기에 등록한다. (프론트 registry.ts와 id를 맞춘다)
SPORTS: dict[str, SportRules] = {r.id: r for r in (BASKETBALL, FOOTBALL, BADMINTON)}


def get_rules(sport_id: str) -> SportRules:
    return SPORTS[sport_id]
