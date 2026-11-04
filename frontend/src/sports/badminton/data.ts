// 배드민턴 종목 데이터. 백엔드 app/sports/badminton/과 id·인원 구성을 맞춘다.

export const formats = [
  { name: "단식", team: "1:1", total: 2, note: "코트가 좁고 길어서 혼자 넓게 움직여요." },
  { name: "복식", team: "2:2", total: 4, note: "코트가 넓어지고, 파트너와 자리를 나눠 맡아요." },
];

// 온보딩 자기평가용. 서열보다 경험으로 고르게 쓴다.
export const tiers = [
  { tier: 1, label: "배드민턴이 처음이거나 몇 번 쳐본 정도예요" },
  { tier: 2, label: "가끔 친구들과 랠리를 즐겨요" },
  { tier: 3, label: "꾸준히 치고, 클리어와 스매시가 익숙해요" },
  { tier: 4, label: "동호회나 클럽에서 경기를 뛰어요" },
  { tier: 5, label: "선수 출신이거나 대회에 나가는 수준이에요" },
];

// (질문, 답변). 방장이 정한 규칙이 있으면 그쪽이 우선이다.
export const faq = [
  {
    q: "한 경기는 몇 점까지 하나요?",
    a: "21점을 먼저 따면 한 게임을 이겨요. 3게임 중 2게임을 이기면 경기가 끝나요.",
  },
  {
    q: "20대20이 되면 어떻게 하나요?",
    a: "2점 차가 날 때까지 계속해요. 29대29가 되면 30점을 먼저 따는 쪽이 이겨요.",
  },
  {
    q: "서브는 어떻게 넣나요?",
    a: "공을 허리 아래에서 쳐서, 대각선 방향 상대 코트에 넣어요. 서브를 하는 쪽이 점수를 따면 계속 서브해요.",
  },
  {
    q: "단식과 복식은 코트가 다른가요?",
    a: "단식은 안쪽 옆줄까지, 복식은 바깥 옆줄까지 써요. 서브는 단식이 뒤쪽 끝줄까지, 복식은 뒤쪽 짧은 줄까지 허용돼요.",
  },
  {
    q: "셔틀콕이 선에 닿으면요?",
    a: "선에 닿은 공은 인으로 봐요.",
  },
];

// TODO: 예시 데이터(mock). API 연동 시 교체
export const matches = [
  { id: 1, title: "평일 저녁 복식", venue: "새솔 실내체육관", when: "10/13(화) 19:30", distance: "약 4km", joined: 3, capacity: 4, tierRange: [2, 3] as [number, number], reasons: ["실력대 비슷", "선호 시간대"], description: "퇴근하고 가볍게 치는 복식이에요. 셔틀콕은 제가 챙겨 갈게요." },
  { id: 2, title: "토요일 오후 복식", venue: "누리 체육관", when: "10/10(토) 14:00", distance: "약 1km", joined: 2, capacity: 4, tierRange: [3, 4] as [number, number], reasons: ["집에서 약 1km", "실력대 비슷"], description: "2게임씩 파트너를 바꿔 가며 쳐요. 라켓이 없으면 빌려 드려요." },
  { id: 3, title: "일요일 아침 단식", venue: "다온 체육관", when: "10/11(일) 09:00", distance: "약 3km", joined: 1, capacity: 2, tierRange: [1, 2] as [number, number], reasons: ["집에서 약 3km"], description: "아침 운동 삼아 1:1로 랠리 위주로 쳐요." },
];
