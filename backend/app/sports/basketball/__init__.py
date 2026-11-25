from app.sports.base import SportRules
from app.sports.basketball.faq import FAQ

RULES = SportRules(
    id="basketball",
    name="농구",
    team_count=2,
    players_per_team=(3, 5),
    positions=("PG", "SG", "SF", "PF", "C"),
    tier_labels={
        1: "농구를 처음 시작했거나 기본적인 규칙과 기술을 배우는 단계",
        2: "기본적인 드리블, 패스, 슛을 할 수 있는 단계",
        3: "기본적인 팀플레이와 공격·수비에 참여할 수 있는 단계",
        4: "안정적인 공격과 수비 능력을 갖추고 경기 흐름을 이해하는 단계",
        5: "높은 경기 이해도와 숙련도를 바탕으로 팀을 이끌 수 있는 단계",
    },
)

__all__ = ["FAQ", "RULES"]