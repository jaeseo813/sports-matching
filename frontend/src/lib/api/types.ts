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
  is_host: boolean;
  gender_policy: GenderPolicy;
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

export interface SportOut {
  id: string;
  name: string;
  team_count: number;
  players_per_team: number[];
  positions: string[];
  tier_labels: Record<string, string>; // "1"~"5"
}

export interface VenueOut {
  id: number;
  name: string;
  sports: string[];
  distance_km: number | null;
}

export interface ParticipationOut {
  id: number;
  nickname: string;
  status: ParticipationStatus;
}

export interface LocationOut {
  slot: number;
  label: string;
  max_distance_km: number;
}

export type GenderPolicy = "any" | "male_only" | "female_only";
