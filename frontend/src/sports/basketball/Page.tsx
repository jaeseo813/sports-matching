import MatchList from "../../components/MatchList";
import type { SportOut } from "../../lib/api/types";
import { SportChat } from "../../components/ChatPanel";
import { useSportRules } from "../../lib/sports";
import { basketball } from ".";
import { formatNotes } from "./data";

// 농구 담당 영역: 이 폴더(src/sports/basketball) 안에서만 작업한다.
// 팀 인원·포지션·티어 설명은 서버 규칙(GET /sports)을 쓴다. 구성은 풋살·배드민턴 페이지와 같다.

// 히어로: 남색 바탕에 코트 라인(3점 라인 + 페인트존)
function Hero({ rules }: { rules: SportOut | undefined }) {
  const facts = [
    rules && rules.players_per_team.map((n) => `${n}:${n}`).join(" · "),
    rules && rules.positions.length > 0 && `포지션 ${rules.positions.length}개`,
    "3점 라인 밖은 3점",
  ].filter((f): f is string => Boolean(f));

  return (
    <section className="relative overflow-hidden rounded-xl bg-night p-6 text-white md:p-10">
      <div aria-hidden="true" className="pointer-events-none absolute -right-28 top-1/2 size-72 -translate-y-1/2 rounded-full border border-white/10" />
      <div aria-hidden="true" className="pointer-events-none absolute right-0 top-1/2 h-28 w-24 -translate-y-1/2 border border-r-0 border-white/10" />
      <div className="relative">
        <span className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1 text-xs font-bold ${basketball.bg} ${basketball.fg}`}>
          <basketball.icon size={14} aria-hidden="true" />
          {basketball.name}
        </span>
        <h1 className="mt-4 text-3xl font-black leading-tight tracking-tight md:text-5xl">
          코트만 정하세요,
          <br />
          <span className="text-lime">손발 맞는 팀원은 찾아 줄게요</span>
        </h1>
        <p className="mt-3 max-w-[40ch] text-white/70">
          3대3은 하프코트에서, 5대5는 풀코트에서 해요. 비슷한 실력의 사람을 가까운 곳에서 만나 보세요.
        </p>
        <ul className="mt-6 flex flex-wrap gap-2">
          {facts.map((f) => (
            <li key={f} className="rounded-lg bg-night-2 px-3 py-1.5 text-sm font-semibold">
              {f}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

const loadingText = <p role="status" className="text-sm text-muted">종목 규칙을 불러오고 있어요…</p>;

function Formats({ rules }: { rules: SportOut | undefined }) {
  return (
    <section aria-labelledby="formats">
      <h2 id="formats" className="mb-3 text-xl font-extrabold">인원 구성</h2>
      {rules ? (
        <ul className="grid gap-3 md:grid-cols-2">
          {rules.players_per_team.map((n) => (
            <li key={n} className="rounded-xl border border-edge bg-white p-5">
              <p className="flex items-baseline justify-between">
                <span className="text-lg font-bold">{n}:{n}</span>
                <span className="text-sm font-medium text-muted">팀당 {n}명 · 총 {n * rules.team_count}명</span>
              </p>
              <p className="mt-2 text-sm text-muted">
                {n === rules.positions.length && `포지션 ${rules.positions.length}개(${rules.positions.join("·")})를 한 명씩 맡아요. `}
                {formatNotes[n]}
              </p>
            </li>
          ))}
        </ul>
      ) : (
        loadingText
      )}
    </section>
  );
}

function TierGuide({ rules }: { rules: SportOut | undefined }) {
  const tiers = rules ? Object.entries(rules.tier_labels).sort(([a], [b]) => Number(a) - Number(b)) : [];
  return (
    <section aria-labelledby="tiers">
      <h2 id="tiers" className="text-xl font-extrabold">나는 어느 단계일까요?</h2>
      <p className="mt-1 text-sm text-muted">서열이 아니라 팀을 고르게 나누기 위한 참고예요. 경기를 하면서 조금씩 맞춰져요.</p>
      {rules ? (
        <ol className="mt-3 space-y-2">
          {tiers.map(([tier, label]) => (
            <li key={tier} className="flex items-center gap-3 rounded-xl border border-edge bg-white p-3">
              <span className="flex size-11 shrink-0 items-center justify-center rounded-lg bg-lime font-black" aria-label={`${tier}단계`}>
                {tier}
              </span>
              <span className="text-sm">{label}</span>
            </li>
          ))}
        </ol>
      ) : (
        <div className="mt-3">{loadingText}</div>
      )}
    </section>
  );
}

export default function Page() {
  const rules = useSportRules()?.find((s) => s.id === basketball.id);

  return (
    <div className="space-y-10">
      <Hero rules={rules} />
      <Formats rules={rules} />
      <section aria-labelledby="matches">
        <h2 id="matches" className="mb-3 text-xl font-extrabold">모집 중인 농구 매치</h2>
        <MatchList sport={basketball.id} />
      </section>
      <div className="grid gap-10 md:grid-cols-2">
        <TierGuide rules={rules} />
        <SportChat sport={basketball.id} />
      </div>
    </div>
  );
}
