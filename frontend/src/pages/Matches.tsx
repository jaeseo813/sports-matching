import { Link, useSearchParams } from "react-router-dom";
import { Plus } from "lucide-react";
import MatchList from "../components/MatchList";
import { sports } from "../sports/registry";

export default function Matches() {
  const [params, setParams] = useSearchParams();
  const sport = params.get("sport") ?? undefined;
  const tabs = [{ id: undefined, name: "전체" }, ...sports.map((s) => ({ id: s.id as string | undefined, name: s.name }))];

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-extrabold">매치 찾기</h1>
        <Link to={`/matches/new${sport ? `?sport=${sport}` : ""}`} className="flex min-h-11 items-center gap-1 rounded-lg bg-night px-5 text-sm font-bold text-lime">
          <Plus size={16} aria-hidden="true" /> 매치 열기
        </Link>
      </div>
      <div role="group" aria-label="종목" className="flex flex-wrap gap-1 rounded-lg border border-edge bg-white p-1">
        {tabs.map((t) => {
          const active = t.id === sport;
          return (
            <button
              key={t.name}
              type="button"
              aria-pressed={active}
              onClick={() => setParams(t.id ? { sport: t.id } : {})}
              className={`min-h-11 flex-1 rounded-md px-4 text-sm font-bold ${active ? "bg-lime" : "text-muted hover:bg-edge"}`}
            >
              {t.name}
            </button>
          );
        })}
      </div>
      <MatchList key={sport ?? "all"} sport={sport} />
    </section>
  );
}
