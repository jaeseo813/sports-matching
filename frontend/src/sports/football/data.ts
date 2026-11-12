// 풋살 종목 데이터. 백엔드 app/sports/football/과 인원 구성·티어 설명·FAQ 문구를 맞춘다.

export type Format = 5 | 6; // 팀당 인원

export const formats: { size: Format; name: string; note: string }[] = [
  { size: 5, name: "5:5", note: "골키퍼 1명 + 필드 4명. 공을 잡을 기회가 많고 활동량이 커요." },
  { size: 6, name: "6:6", note: "골키퍼 1명 + 필드 5명. 조금 넓은 구장에서 여유 있게 뛰어요." },
];

// 온보딩 자기평가용. 서열보다 경험으로 고르게 쓴다.
export const tiers: { tier: number; label: string }[] = [
  { tier: 1, label: "풋살이 처음이거나 몇 번 차본 정도예요" },
  { tier: 2, label: "가끔 친구들과 즐겁게 차요" },
  { tier: 3, label: "꾸준히 차고, 패스와 슈팅이 익숙해요" },
  { tier: 4, label: "동아리나 리그에서 뛰고, 경기 흐름을 읽어요" },
  { tier: 5, label: "선수 출신이거나 대회에 나가는 수준이에요" },
];

// (질문, 답변). backend/app/sports/football/faq.py와 같은 문구. 방장이 정한 규칙이 있으면 그쪽이 우선이다.
export const faq: { q: string; a: string }[] = [
  { q: "공이 옆줄 밖으로 나가면 어떻게 하나요?", a: "던지지 않고 킥인으로 재개해요. 공을 옆줄 위에 멈춰 두고 발로 차서 넣어요." },
  { q: "경기를 다시 시작할 때 시간 제한이 있나요?", a: "킥인, 코너킥, 프리킥, 골키퍼 골 클리어런스는 준비된 뒤 4초 안에 해야 해요. 넘기면 상대 공이 돼요." },
  { q: "골키퍼에게 백패스해도 되나요?", a: "같은 팀이 일부러 발로 준 공은 골키퍼가 손으로 잡을 수 없어요. 발로는 받을 수 있어요." },
  { q: "오프사이드가 있나요?", a: "없어요. 풋살에는 오프사이드 규칙이 없어요." },
  { q: "선수 교체는 어떻게 하나요?", a: "횟수 제한 없이 경기 중에 언제든 교체할 수 있어요. 나가는 사람이 먼저 나온 뒤 들어가요." },
  { q: "누적 파울은 무엇인가요?", a: "전·후반마다 팀 파울을 세요. 6번째 파울부터는 상대에게 수비벽 없는 프리킥을 줘요." },
  { q: "태클해도 되나요?", a: "다치기 쉬워서 픽업 경기는 보통 슬라이딩 태클을 금지해요. 방 소개의 규칙을 확인하세요." },
];

export interface FutsalMatch {
  id: number;
  title: string;
  format: Format;
  venue: string;
  when: string;
  distance: string;
  joined: number;
  tierRange: [number, number];
  reasons: string[];
  description: string;
}

// TODO: 예시 데이터(mock). API 연동 시 교체. 구장 이름은 가상 (더미 데이터에 실명·실주소 금지)
export const matches: FutsalMatch[] = [
  { id: 1, title: "수요일 저녁 가볍게 한 판", format: 5, venue: "새봄 풋살파크", when: "11/11(수) 19:00", distance: "약 1km", joined: 7, tierRange: [1, 3], reasons: ["실력대 비슷", "초보 환영"], description: "처음 오셔도 괜찮아요. 골키퍼는 5분마다 돌아가며 봐요." },
  { id: 2, title: "목요일 공강 풋살", format: 6, venue: "캠퍼스 인조잔디 구장", when: "11/12(목) 15:00", distance: "약 0.5km", joined: 9, tierRange: [2, 4], reasons: ["선호 시간대"], description: "공강 시간에 1시간 뛰어요. 조끼는 준비해 갈게요." },
  { id: 3, title: "금요일 밤 빡겜", format: 5, venue: "한빛 풋살센터", when: "11/13(금) 21:00", distance: "약 3km", joined: 4, tierRange: [3, 5], reasons: ["매너 좋은 방장"], description: "경기 위주로 진지하게 뛰어요. 슬라이딩 태클은 금지예요." },
  { id: 4, title: "토요일 오전 풋살", format: 6, venue: "새봄 풋살파크", when: "11/14(토) 10:00", distance: "약 1km", joined: 11, tierRange: [2, 3], reasons: ["실력대 비슷", "한 자리 남음"], description: "한 자리 남았어요. 끝나고 같이 점심 먹어요." },
  { id: 5, title: "일요일 오후 즐겜", format: 5, venue: "캠퍼스 인조잔디 구장", when: "11/15(일) 16:00", distance: "약 0.5km", joined: 2, tierRange: [1, 2], reasons: ["초보 환영"], description: "승패보다 즐겁게 차는 게 목표예요. 풋살화 없으면 운동화도 괜찮아요." },
];
