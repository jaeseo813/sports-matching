import { useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { CalendarCheck, Settings, Star, Users } from "lucide-react";
import MatchCard from "../components/MatchCard";
import SportPicker from "../components/SportPicker";
import { api, ApiError } from "../lib/api/client";
import type { MatchOut, MySummaryOut, RecommendedOut, SkillOut } from "../lib/api/types";
import { useAuth } from "../lib/auth";
import { formatWhen } from "../lib/format";
import { sports } from "../sports/registry";

const sportOf = (id: string) => sports.find((s) => s.id === id);

interface Activity {
  summary: MySummaryOut;
  upcoming: MatchOut[];
  recommended: RecommendedOut[];
  needsOnboarding: boolean; // 자기평가·활동 기준점이 없어 추천을 못 한다
}

// 등록한 종목마다 추천을 받아 점수순으로 섞는다. 순위는 서버 스코어링이 정한다
async function loadRecommended(): Promise<{ items: RecommendedOut[]; needsOnboarding: boolean }> {
  const skills = await api<SkillOut[]>("/me/skills");
  if (skills.length === 0) return { items: [], needsOnboarding: true };
  try {
    const lists = await Promise.all(
      skills.map((s) => api<RecommendedOut[]>(`/matches/recommended?sport=${encodeURIComponent(s.sport)}&limit=3`)),
    );
    return { items: lists.flat().sort((a, b) => b.score - a.score).slice(0, 3), needsOnboarding: false };
  } catch (err) {
    if (err instanceof ApiError && err.status === 409) return { items: [], needsOnboarding: true };
    throw err;
  }
}

function useActivity(enabled: boolean) {
  const [data, setData] = useState<Activity | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!enabled) return;
    let alive = true;
    (async () => {
      try {
        const [summary, upcoming, rec] = await Promise.all([
          api<MySummaryOut>("/me/summary"),
          api<MatchOut[]>("/me/matches?limit=4"),
          loadRecommended(),
        ]);
        if (alive) setData({ summary, upcoming, recommended: rec.items, needsOnboarding: rec.needsOnboarding });
      } catch {
        if (alive) setError(true);
      }
    })();
    return () => {
      alive = false;
    };
  }, [enabled]);

  return { data, error };
}

function Empty({ children }: { children: ReactNode }) {
  return <p className="rounded-xl border border-edge bg-white p-5 text-sm text-muted">{children}</p>;
}

function Card({ m, reasons }: { m: MatchOut; reasons?: string[] }) {
  const sport = sportOf(m.sport);
  if (!sport) return null;
  return (
    <MatchCard
      sport={sport}
      title={m.title}
      venue={m.venue_name}
      when={formatWhen(m.starts_at)}
      joined={m.joined}
      capacity={m.capacity}
      tierRange={[m.tier_min, m.tier_max]}
      reasons={reasons}
    />
  );
}

export default function Dashboard() {
  const { user, loading } = useAuth();
  const { data, error } = useActivity(!!user);

  const stats = data && [
    { label: "참가 예정", value: String(data.summary.upcoming), icon: CalendarCheck },
    { label: "참가 완료", value: String(data.summary.attended), icon: Users },
    { label: "매너 점수", value: data.summary.manner_score.toFixed(1), icon: Star },
  ];

  return (
    <>
      {/* 인사 블록 */}
      <section className="rounded-xl bg-lime p-6 md:p-8">
        <div className="mx-auto flex max-w-6xl items-start justify-between">
          <div>
            <p className="text-sm">{user ? `${user.nickname}님, 반가워요` : "TeamUp에 오신 걸 환영해요"}</p>
            <h1 className="mt-1 text-2xl font-black md:text-4xl">
              {data && data.summary.upcoming > 0 ? `참가 예정 경기가 ${data.summary.upcoming}개 있어요` : "함께 뛸 사람을 찾아볼까요?"}
            </h1>
          </div>
          <Link to="/me" aria-label="설정" className="flex size-11 shrink-0 items-center justify-center rounded-lg bg-night text-lime">
            <Settings size={20} aria-hidden="true" />
          </Link>
        </div>
      </section>

      <section aria-labelledby="pick-sport" className="!mt-8">
        <h2 id="pick-sport" className="mb-4 text-xl font-extrabold">어떤 운동을 할까요?</h2>
        <SportPicker />
      </section>

      {!loading && !user && (
        <Empty>
          <Link to="/login" className="font-bold text-night underline">로그인</Link>하면 내 활동 기록과 추천 매치가 보여요.
        </Empty>
      )}

      {user && error && <Empty>활동 정보를 불러오지 못했어요. 잠시 후 다시 시도해 주세요.</Empty>}

      {user && !error && (
        <>
          {/* 큰 아이콘 버튼 형태의 활동 요약 */}
          <section aria-labelledby="summary" className="!mt-8" aria-busy={!data}>
            <h2 id="summary" className="mb-4 text-xl font-extrabold">내 활동 기록</h2>
            <ul className="grid grid-cols-3 gap-3 md:max-w-2xl">
              {(stats ?? [{ label: "참가 예정", icon: CalendarCheck }, { label: "참가 완료", icon: Users }, { label: "매너 점수", icon: Star }]).map(
                ({ label, icon: Icon, ...rest }) => (
                  <li key={label} className="flex aspect-square flex-col items-center justify-center gap-1 rounded-xl bg-night text-center text-white">
                    <span className="flex size-10 items-center justify-center rounded-lg bg-lime text-night">
                      <Icon size={20} aria-hidden="true" />
                    </span>
                    <span className="text-2xl font-black">{"value" in rest ? rest.value : "–"}</span>
                    <span className="text-xs text-white/70">{label}</span>
                  </li>
                ),
              )}
            </ul>
          </section>

          <section aria-labelledby="upcoming" aria-busy={!data}>
            <h2 id="upcoming" className="mb-4 text-xl font-extrabold">참가 예정 매치</h2>
            {data && data.upcoming.length === 0 && <Empty>참가 예정인 매치가 없어요. 종목을 골라 매치를 찾아보세요.</Empty>}
            <ul className="grid gap-4 md:grid-cols-2">
              {data?.upcoming.map((m) => (
                <li key={m.id} className="lift">
                  <Card m={m} />
                </li>
              ))}
            </ul>
          </section>

          <section aria-labelledby="recommended" aria-busy={!data}>
            <div className="mb-4 flex items-center justify-between">
              <h2 id="recommended" className="text-xl font-extrabold">나를 위한 추천</h2>
              <Link to="/matches" className="flex min-h-11 items-center text-sm font-bold underline underline-offset-4">더 보기</Link>
            </div>
            {data?.needsOnboarding && <Empty>종목 자기평가와 활동 지역을 등록하면 가까운 곳의 비슷한 실력 매치를 추천해 드려요.</Empty>}
            {data && !data.needsOnboarding && data.recommended.length === 0 && <Empty>지금 조건에 맞는 매치가 없어요.</Empty>}
            <ul className="grid gap-4 md:grid-cols-3">
              {data?.recommended.map((r) => (
                <li key={r.match.id} className="lift">
                  <Card m={r.match} reasons={r.reasons} />
                </li>
              ))}
            </ul>
          </section>
        </>
      )}
    </>
  );
}
