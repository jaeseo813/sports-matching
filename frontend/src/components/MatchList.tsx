import { Link } from "react-router-dom";
import { Plus, SearchX } from "lucide-react";
import MatchCard from "./MatchCard";
import type { MatchOut } from "../lib/api/types";
import { formatWhen } from "../lib/format";
import { matchStatusLabel, myStatusLabel } from "../lib/labels";
import { useApi } from "../lib/useApi";
import { sports } from "../sports/registry";

// 모집 중인 매치 목록(실제 API). 카드를 누르면 상세(/matches/:id)로 간다. 종목 페이지에서도 가져다 쓴다
export default function MatchList({ sport }: { sport?: string }) {
  const { data, error, loading } = useApi<MatchOut[]>(`/matches?limit=50${sport ? `&sport=${encodeURIComponent(sport)}` : ""}`);

  if (loading) return <p role="status" className="text-sm text-muted">매치를 불러오고 있어요…</p>;
  if (error) return <p role="alert" className="rounded-xl border border-edge bg-white p-5 text-sm">⚠ {error.message}</p>;
  if (!data || data.length === 0) {
    return (
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-edge bg-white p-5 text-sm text-muted">
        <span className="flex items-center gap-2">
          <SearchX size={18} aria-hidden="true" />
          지금 모집 중인 매치가 없어요. 직접 열어 보세요.
        </span>
        <Link to={`/matches/new${sport ? `?sport=${sport}` : ""}`} className="flex min-h-11 items-center gap-1 rounded-lg bg-night px-4 font-bold text-lime">
          <Plus size={16} aria-hidden="true" /> 매치 열기
        </Link>
      </div>
    );
  }
  return (
    <ul className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {data.map((m) => {
        const s = sports.find((x) => x.id === m.sport);
        if (!s) return null;
        return (
          <li key={m.id}>
            <Link to={`/matches/${m.id}`} className="lift block rounded-xl" aria-label={`${m.title} 상세 보기`}>
              <MatchCard
                sport={s}
                title={m.title}
                venue={m.venue_name}
                when={formatWhen(m.starts_at)}
                joined={m.joined}
                capacity={m.capacity}
                tierRange={[m.tier_min, m.tier_max]}
                reasons={[m.is_host ? "내가 연 매치" : m.my_status ? myStatusLabel[m.my_status] : matchStatusLabel[m.status]]}
              />
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
