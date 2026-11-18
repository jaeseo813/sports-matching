
export const formats = [
  {
    name: "3대3",
    team: "3명씩",
    total: 6,
    note: "하프코트에서 진행하는 경기예요. 빠른 공격과 개인 기술이 중요해요.",
  },
  {
    name: "5대5",
    team: "5명씩",
    total: 10,
    note: "풀코트에서 진행하는 일반적인 농구 경기예요. 팀워크와 포지션 밸런스가 중요해요.",
  },
];

export const tiers = [
  {
    tier: 1,
    label: "농구를 처음 시작했거나 기본적인 규칙과 기술을 배우는 단계",
  },
  {
    tier: 2,
    label: "기본적인 드리블, 패스, 슛을 할 수 있는 단계",
  },
  {
    tier: 3,
    label: "기본적인 팀플레이와 공격·수비에 참여할 수 있는 단계",
  },
  {
    tier: 4,
    label: "안정적인 공격과 수비 능력을 갖추고 경기 흐름을 이해하는 단계",
  },
  {
    tier: 5,
    label: "높은 경기 이해도와 숙련도를 바탕으로 팀을 이끌 수 있는 단계",
  },
];

export const matches = [
  {
    id: "basketball-001",
    title: "수원 주말 3대3 농구",
    venue: "수원 실내 농구장",
    distance: "약 2km",
    when: "토요일 오후 2:00",
    format: "3대3",
    capacity: 6,
    joined: 4,
    tierRange: [2, 4] as [number, number],
    positions: ["PG", "SG", "SF"],
    description:
      "가볍게 즐기는 3대3 경기입니다. 서로 배려하며 즐겁게 경기할 분들을 모집합니다.",
    reasons: ["가까운 거리", "실력 적합", "인원 모집 중"],
  },
  {
    id: "basketball-002",
    title: "일요일 5대5 친선 경기",
    venue: "용인 실내 체육관",
    distance: "약 5km",
    when: "일요일 오후 4:00",
    format: "5대5",
    capacity: 10,
    joined: 7,
    tierRange: [3, 5] as [number, number],
    positions: ["PG", "SG", "SF", "PF", "C"],
    description:
      "팀워크와 밸런스를 중요하게 생각하는 친선 경기입니다. 포지션별 인원을 고려해 팀을 구성합니다.",
    reasons: ["실력 적합", "5대5 경기", "팀 밸런스"],
  },
  {
    id: "basketball-003",
    title: "평일 저녁 3대3 매치",
    venue: "성남 시민 농구장",
    distance: "약 8km",
    when: "수요일 오후 7:00",
    format: "3대3",
    capacity: 6,
    joined: 3,
    tierRange: [1, 3] as [number, number],
    positions: ["PG", "SF", "C"],
    description:
      "초보자도 부담 없이 참여할 수 있는 캐주얼 농구 경기입니다.",
    reasons: ["초보자 환영", "평일 저녁", "인원 모집 중"],
  },
];

 export const faq = [
  {
    q: "농구는 한 팀에 몇 명이 뛰나요?",
    a: "일반적인 5대5 경기는 한 팀에 5명, 3대3 경기는 한 팀에 3명이 뛰어요.",
  },
  {
    q: "3점슛은 어디서부터 인정되나요?",
    a: "3점 라인 바깥에서 던져 성공하면 3점, 라인 안쪽에서 성공하면 2점이에요.",
  },
  {
    q: "자유투는 몇 점인가요?",
    a: "자유투에 성공하면 1점을 얻어요.",
  },
  {
    q: "파울을 당하면 어떻게 되나요?",
    a: "슛 동작 중 파울을 당하면 자유투를 받을 수 있어요. 상황에 따라 공격권이 상대 팀으로 넘어갈 수도 있어요.",
  },
  {
    q: "농구에서 더블 드리블이 뭔가요?",
    a: "드리블을 멈추고 공을 잡은 뒤 다시 드리블하거나, 양손으로 동시에 드리블하면 더블 드리블 반칙이에요.",
  },
  {
    q: "공이 코트 밖으로 나가면 어떻게 되나요?",
    a: "공이 코트 밖으로 나가면 마지막으로 공을 건드린 팀의 상대 팀이 공격권을 가져가요.",
  },
];




// 농구 포지션
export const positions = [
  {
    code: "PG",
    name: "포인트 가드",
    description: "경기를 운영하고 패스로 공격 기회를 만들어요.",
    famousPlayer: " (유명한 선수: 스테판 커리, 크리스 폴,허훈)",
  },
  {
    code: "SG",
    name: "슈팅 가드",
    description: "외곽 슈팅과 득점에 강점을 가진 포지션이에요.",
    famousPlayer: " (유명한 선수: 코비 브라이언트, 제임스 하든, 유기상)",
  },
  {
    code: "SF",
    name: "스몰 포워드",
    description: "공격과 수비 모두에서 균형 잡힌 역할을 해요.",
    famousPlayer: " (유명한 선수: 르브론 제임스, 케빈 듀란트, 이현중)",
  },
  {
    code: "PF",
    name: "파워 포워드",
    description: "리바운드와 골밑 공격에 적극적으로 참여해요.",
    famousPlayer: "(유명한 선수: 팀 던컨, 앤서니 데이비스, 김종규)",
  },
  {
    code: "C",
    name: "센터",
    description: "골밑 수비와 리바운드, 블록을 담당해요.",
    famousPlayer: "(유명한 선수: 샤킬 오닐, 조엘 엠비드, 양희종)",
  },
];