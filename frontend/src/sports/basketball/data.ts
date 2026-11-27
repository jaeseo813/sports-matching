// 농구 종목 데이터. 팀 인원과 티어 설명은 서버(GET /sports, useSportRules)에서 받고,
// 여기에는 서버에 없는 화면 문구만 둔다.

// 인원 구성 카드의 보충 설명 (키: 팀당 인원). 서버에 새 인원이 생기면 설명 없이 표시된다.
export const formatNotes: Record<number, string> = {
  3: "하프코트 하나로 해요. 공격 전환이 빠르고 개인 기술을 쓸 일이 많아요.",
  5: "풀코트에서 해요. 포지션을 나눠 맡고 팀워크가 중요해요.",
};

// 규칙 FAQ는 서버(backend/app/sports/basketball/faq.py)에 있다. 질문은 GET /sports로 받아 챗봇 추천 질문으로 쓰고, 답은 챗봇이 같은 faq.py로 한다.
