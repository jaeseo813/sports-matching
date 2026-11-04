from app.sports.base import SportRules
from app.sports.football.faq import FAQ

__all__ = ["FAQ", "RULES"]

# 풋살만 지원한다 (11인제 축구는 인원 모집이 어려워 범위 밖). id는 프론트와 맞춰 football 유지.
RULES = SportRules(
    id="football",
    name="풋살",
    team_count=2,
    players_per_team=(5, 6),
    positions=("GK", "FIELD"),
    required_per_team={"GK": 1},
    # 서열보다 경험으로 고를 수 있게 쓴다 (온보딩 자기평가용)
    tier_labels={
        1: "풋살이 처음이거나 몇 번 차본 정도예요",
        2: "가끔 친구들과 즐겁게 차요",
        3: "꾸준히 차고, 패스와 슈팅이 익숙해요",
        4: "동아리나 리그에서 뛰고, 경기 흐름을 읽어요",
        5: "선수 출신이거나 대회에 나가는 수준이에요",
    },
)
