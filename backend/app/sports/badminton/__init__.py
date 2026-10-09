from app.sports.base import SportRules

# TODO(배드민턴 담당): 단식/복식 처리, 티어 설명 확정
RULES = SportRules(id="badminton", name="배드민턴", team_count=2, players_per_team=(1, 2))
