import type { GenderPolicy, MatchOut, ParticipationStatus } from "./api/types";

export const matchStatusLabel: Record<MatchOut["status"], string> = {
  open: "모집 중",
  full: "정원 마감",
  confirmed: "확정",
  playing: "진행 중",
  completed: "종료",
  canceled: "취소됨",
};

export const myStatusLabel: Record<ParticipationStatus, string> = {
  applied: "승인 대기",
  accepted: "참가 확정",
  rejected: "거절됨",
  canceled: "신청 취소",
  attended: "출석",
  no_show: "불참",
};

export const genderPolicyLabel: Record<GenderPolicy, string> = {
  any: "성별 무관",
  male_only: "남성만",
  female_only: "여성만",
};

export const trendLabel = { up: "↑ 오르는 중", same: "→ 유지", down: "↓ 내려가는 중" } as const;

export function teamSizeLabel(sport: string, size: number): string {
  if (sport === "badminton") return size === 1 ? "단식" : "복식";
  return `${size}:${size}`;
}
