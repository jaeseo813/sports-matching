// 백엔드 응답 스키마(app/schemas)와 같은 모양. 화이트리스트 필드만 온다.

export type ParticipationStatus = "applied" | "accepted" | "rejected" | "canceled" | "attended" | "no_show";

export interface MatchOut {
  id: number;
  sport: string;
  host_nickname: string;
  venue_id: number;
  venue_name: string;
  title: string;
  description: string | null;
  starts_at: string; // ISO, UTC
  duration_min: number;
  team_size: number;
  capacity: number;
  joined: number;
  min_players: number;
  tier_min: number;
  tier_max: number;
  status: "open" | "full" | "confirmed" | "playing" | "completed" | "canceled";
  my_status: ParticipationStatus | null;
}

export interface RecommendedOut {
  match: MatchOut;
  score: number;
  breakdown: { dist: number; skill: number; time: number; host: number; fill: number };
  reasons: string[];
}

export interface MySummaryOut {
  upcoming: number;
  attended: number;
  manner_score: number;
}

export interface SkillOut {
  sport: string;
  tier: number;
  years_played: number;
  positions: string[] | null;
  trend: "up" | "same" | "down";
}
