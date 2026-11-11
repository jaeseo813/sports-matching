import { ChevronDown } from "lucide-react";
import MatchList from "../../components/MatchList";
import type { SportOut } from "../../lib/api/types";
import { useSportRules } from "../../lib/sports";
import { football } from ".";
import { faq, formatNotes } from "./data";

// 축구/풋살 담당 영역: 이 폴더(src/sports/football) 안에서만 작업한다.
// 팀 인원·티어 설명은 서버 규칙(GET /sports)을 쓴다.

// 히어로: 남색 바탕에 경기장 라인(하프라인 + 센터서클)
function Hero({ rules }: { rules: SportOut | undefined }) {
  const facts = [
    rules && rules.players_per_team.map((n) => `${n}:${n}`).join(" · "),
    rules?.positions.includes("GK") && "골키퍼가 있어요",
    "오프사이드 없음",
  ].filter((f): f is string => Boolean(f));

  return (
    <section className="relative overflow-hidden rounded-xl bg-night p-6 text-white md:p-10">
      <div aria-hidden="true" className="pointer-events-none absolute inset-y-0 right-[18%] w-px bg-white/10" />
      <div aria-hidden="true" className="pointer-events-none absolute right-[18%] top-1/2 size-56 -translate-y-1/2 translate-x-1/2 rounded-full border border-white/10" />
      <div className="relative">
        <span className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1 text-xs font-bold ${football.bg} ${football.fg}`}>
          <football.icon size={14} aria-hidden="true" />
          {football.name}
        </span>
        <h1 className="mt-4 text-3xl font-black leading-tight tracking-tight md:text-5xl">
          공강에 한 판,
          <br />
          <span className="text-lime">실력 비슷한 학우들과</span>
        </h1>
        <p className="mt-3 max-w-[40ch] text-white/70">
          방에 들어가 인원이 차면 매치가 확정되고, 두 팀으로 고르게 나눠요.
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
                {rules.positions.includes("GK") && `골키퍼 1명 + 필드 ${n - 1}명. `}
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

function RuleFaq() {
  return (
    <section aria-labelledby="faq">
      <h2 id="faq" className="text-xl font-extrabold">풋살 규칙 FAQ</h2>
      <p className="mt-1 text-sm text-muted">방장이 정한 규칙이 있으면 그쪽이 우선이에요.</p>
      <ul className="mt-3 space-y-2">
        {faq.map(({ q, a }) => (
          <li key={q}>
            <details className="group rounded-xl border border-edge bg-white">
              <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 p-3 text-sm font-bold [&::-webkit-details-marker]:hidden">
                {q}
                <ChevronDown size={18} aria-hidden="true" className="shrink-0 transition-transform group-open:rotate-180" />
              </summary>
              <p className="px-3 pb-3 text-sm leading-relaxed text-muted">{a}</p>
            </details>
          </li>
        ))}
      </ul>
    </section>
  );
}

export default function Page() {
  const rules = useSportRules()?.find((s) => s.id === football.id);

  return (
    <div className="space-y-10">
      <Hero rules={rules} />
      <Formats rules={rules} />
      <section aria-labelledby="matches">
        <h2 id="matches" className="mb-3 text-xl font-extrabold">모집 중인 풋살 매치</h2>
        <MatchList sport={football.id} />
      </section>
      <div className="grid gap-10 md:grid-cols-2">
        <TierGuide rules={rules} />
        <RuleFaq />
      </div>
    </div>
  );
}
