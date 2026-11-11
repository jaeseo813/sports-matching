import { useRef, useState } from "react";
import { Check, ChevronDown, SearchX, X } from "lucide-react";
import MatchCard from "../../components/MatchCard";
import { football } from ".";
import { faq, formats, matches, tiers, type Format, type FutsalMatch } from "./data";

// 축구/풋살 담당 영역: 이 폴더(src/sports/football) 안에서만 작업한다.

const filters: { value: Format | "all"; label: string }[] = [
  { value: "all", label: "전체" },
  { value: 5, label: "5:5" },
  { value: 6, label: "6:6" },
];

const facts = ["5:5 · 6:6", "팀당 골키퍼 1명", "오프사이드 없음"];

// 히어로: 남색 바탕에 경기장 라인(하프라인 + 센터서클)
function Hero() {
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

function Formats() {
  return (
    <section aria-labelledby="formats">
      <h2 id="formats" className="mb-3 text-xl font-extrabold">인원 구성</h2>
      <ul className="grid gap-3 md:grid-cols-2">
        {formats.map((f) => (
          <li key={f.size} className="rounded-xl border border-edge bg-white p-5">
            <p className="flex items-baseline justify-between">
              <span className="text-lg font-bold">{f.name}</span>
              <span className="text-sm font-medium text-muted">팀당 {f.size}명 · 총 {f.size * 2}명</span>
            </p>
            <p className="mt-2 text-sm text-muted">{f.note}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}

function MatchList({ onOpen }: { onOpen: (m: FutsalMatch) => void }) {
  const [format, setFormat] = useState<Format | "all">("all");
  const shown = format === "all" ? matches : matches.filter((m) => m.format === format);

  return (
    <section aria-labelledby="matches">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <h2 id="matches" className="text-xl font-extrabold">
          모집 중인 풋살 매치 <span className="text-muted">{shown.length}</span>
        </h2>
        <div role="group" aria-label="경기 인원" className="flex gap-1 rounded-lg border border-edge bg-white p-1">
          {filters.map(({ value, label }) => {
            const active = format === value;
            return (
              <button
                key={label}
                type="button"
                aria-pressed={active}
                onClick={() => setFormat(value)}
                className={`flex min-h-11 items-center gap-1 rounded-md px-4 text-sm font-bold ${
                  active ? "bg-lime" : "text-muted hover:bg-edge"
                }`}
              >
                {active && <Check size={16} aria-hidden="true" />}
                {label}
              </button>
            );
          })}
        </div>
      </div>

      {shown.length > 0 ? (
        <ul className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {shown.map((m) => (
            <li key={m.id} className="lift relative">
              <MatchCard
                sport={football}
                title={`${m.title} · ${m.format}:${m.format}`}
                venue={m.venue}
                when={m.when}
                distance={m.distance}
                joined={m.joined}
                capacity={m.format * 2}
                tierRange={m.tierRange}
                reasons={m.reasons}
              />
              <button type="button" onClick={() => onOpen(m)} aria-label={`${m.title} 상세 보기`} className="absolute inset-0 rounded-xl" />
            </li>
          ))}
        </ul>
      ) : (
        <p className="flex items-center gap-2 rounded-xl border border-edge bg-white p-5 text-sm text-muted">
          <SearchX size={18} aria-hidden="true" />
          조건에 맞는 매치가 없어요.
        </p>
      )}
    </section>
  );
}

function TierGuide() {
  return (
    <section aria-labelledby="tiers">
      <h2 id="tiers" className="text-xl font-extrabold">나는 어느 단계일까요?</h2>
      <p className="mt-1 text-sm text-muted">서열이 아니라 팀을 고르게 나누기 위한 참고예요. 경기를 하면서 조금씩 맞춰져요.</p>
      <ol className="mt-3 space-y-2">
        {tiers.map(({ tier, label }) => (
          <li key={tier} className="flex items-center gap-3 rounded-xl border border-edge bg-white p-3">
            <span className="flex size-11 shrink-0 items-center justify-center rounded-lg bg-lime font-black" aria-label={`${tier}단계`}>
              {tier}
            </span>
            <span className="text-sm">{label}</span>
          </li>
        ))}
      </ol>
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
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [selected, setSelected] = useState<FutsalMatch | null>(null);

  const open = (m: FutsalMatch) => {
    setSelected(m);
    dialogRef.current?.showModal();
  };
  const close = () => dialogRef.current?.close();

  return (
    <div className="space-y-10">
      <Hero />
      <Formats />
      <MatchList onOpen={open} />
      <div className="grid gap-10 md:grid-cols-2">
        <TierGuide />
        <RuleFaq />
      </div>

      <dialog
        ref={dialogRef}
        onClose={() => setSelected(null)}
        onClick={(e) => e.target === dialogRef.current && close()}
        aria-labelledby="match-title"
        className="m-auto w-[calc(100%-2rem)] max-w-md rounded-xl bg-white p-0 text-night backdrop:bg-night/50"
      >
        {selected && (
          <div className="p-6">
            <div className="flex items-start justify-between gap-4">
              <h2 id="match-title" className="text-xl font-black">{selected.title}</h2>
              <button type="button" onClick={close} aria-label="닫기" className="flex size-11 shrink-0 items-center justify-center rounded-lg hover:bg-edge">
                <X size={20} aria-hidden="true" />
              </button>
            </div>
            <dl className="mt-4 space-y-2 text-sm">
              <div className="flex gap-3"><dt className="w-16 shrink-0 text-muted">장소</dt><dd>{selected.venue}, {selected.distance}</dd></div>
              <div className="flex gap-3"><dt className="w-16 shrink-0 text-muted">시간</dt><dd>{selected.when}</dd></div>
              <div className="flex gap-3"><dt className="w-16 shrink-0 text-muted">형식</dt><dd>{selected.format}:{selected.format} · {selected.joined}/{selected.format * 2}명</dd></div>
              <div className="flex gap-3">
                <dt className="w-16 shrink-0 text-muted">참가 단계</dt>
                <dd>
                  {tiers.filter((t) => t.tier >= selected.tierRange[0] && t.tier <= selected.tierRange[1]).map((t) => (
                    <span key={t.tier} className="block">{t.tier}단계 · {t.label}</span>
                  ))}
                </dd>
              </div>
            </dl>
            <p className="mt-4 rounded-lg bg-cream p-3 text-sm">{selected.description}</p>
            <ul className="mt-3 flex flex-wrap gap-1.5">
              {selected.reasons.map((r) => (
                <li key={r} className="rounded-lg bg-lime px-2.5 py-1 text-xs font-semibold">{r}</li>
              ))}
            </ul>
            {/* TODO: 신청 API 연동 */}
            <button type="button" disabled className="mt-5 min-h-12 w-full rounded-lg bg-night font-bold text-lime disabled:opacity-50">
              신청하기 (준비 중)
            </button>
          </div>
        )}
      </dialog>
    </div>
  );
}
