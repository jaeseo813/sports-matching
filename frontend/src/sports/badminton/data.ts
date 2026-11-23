// 배드민턴 종목 데이터. 팀 인원과 티어 설명은 서버(GET /sports, useSportRules)에서 받고,
// 여기에는 서버에 없는 화면 문구만 둔다.

// 인원 구성 카드의 보충 설명 (키: 팀당 인원). 서버에 새 인원이 생기면 설명 없이 표시된다.
export const formatNotes: Record<number, string> = {
  1: "코트가 좁고 길어서 혼자 넓게 움직여요.",
  2: "코트가 넓어지고, 파트너와 자리를 나눠 맡아요.",
};

// 규칙 FAQ는 서버(backend/app/sports/badminton/faq.py)에 있다. 질문은 GET /sports로 받아 챗봇 추천 질문으로 쓰고, 답은 챗봇이 같은 faq.py로 한다.
