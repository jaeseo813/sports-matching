from app.sports.badminton.faq import FAQ
from app.sports.base import SportRules

__all__ = ["FAQ", "RULES"]

# 단식(팀당 1명)과 복식(팀당 2명). 포지션은 쓰지 않는다. id는 프론트와 맞춰 badminton 유지.
RULES = SportRules(
    id="badminton",
    name="배드민턴",
    team_count=2,
    players_per_team=(1, 2),
    # 서열보다 경험으로 고를 수 있게 쓴다 (온보딩 자기평가용). 프론트 sports/badminton/data.ts와 같은 문구
    tier_labels={
        1: "배드민턴이 처음이거나 몇 번 쳐본 정도예요",
        2: "가끔 친구들과 랠리를 즐겨요",
        3: "꾸준히 치고, 클리어와 스매시가 익숙해요",
        4: "동호회나 클럽에서 경기를 뛰어요",
        5: "선수 출신이거나 대회에 나가는 수준이에요",
    },
)
