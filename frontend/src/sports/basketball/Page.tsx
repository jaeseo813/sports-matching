
import { X } from "lucide-react";
import { useRef, useState } from "react";
import MatchCard from "../../components/MatchCard";
import { basketball } from ".";
import { faq, formats, matches, positions, tiers } from "./data";

type Match = (typeof matches)[number];

// 농구 담당 영역: 이 폴더(src/sports/basketball) 안에서만 작업한다.
export default function Page() {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [selected, setSelected] = useState<Match | null>(null);

  const open = (m: Match) => {
    setSelected(m);
    dialogRef.current?.showModal();
  };

  const close = () => dialogRef.current?.close();

  return (
    <div className="space-y-10">
      {/* 종목 소개 */}
      <section className={`rounded-xl p-6 md:p-8 ${basketball.bg} ${basketball.fg}`}>
        <basketball.icon size={28} aria-hidden="true" />
        <h1 className="mt-3 text-2xl font-black md:text-4xl">
          {basketball.name}
        </h1>
        <p className="mt-2 text-sm">
          3대3부터 5대5까지! 비슷한 실력의 사람들과 가까운 곳에서 농구를 즐겨 보세요.
        </p>
      </section>

      {/* 인원 구성 */}
      <section aria-labelledby="formats">
        <h2 id="formats" className="mb-3 text-xl font-extrabold">
          인원 구성
        </h2>
        <ul className="grid gap-3 md:grid-cols-2">
          {formats.map((f) => (
            <li
              key={f.name}
              className="rounded-xl border border-edge bg-white p-5"
            >
              <p className="flex items-baseline justify-between">
                <span className="text-lg font-bold">{f.name}</span>
                <span className="text-sm font-medium text-muted">
                  {f.team} · 총 {f.total}명
                </span>
              </p>
              <p className="mt-2 text-sm text-muted">{f.note}</p>
            </li>
          ))}
        </ul>
      </section>

      {/* 포지션 */}
      <section aria-labelledby="positions">
        <h2 id="positions" className="mb-3 text-xl font-extrabold">
          농구 포지션
        </h2>
        <ul className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          {positions.map((p) => (
            <li
              key={p.code}
              className="rounded-xl border border-edge bg-white p-5"
            >
            
              <p className="flex items-baseline gap-2">
                <span className="rounded-lg bg-lime px-2.5 py-1 text-sm font-black">
                  {p.code}
                </span>
                <span className="font-bold">{p.name}</span>
              </p>
              <p className="mt-2 text-sm text-muted">{p.description}</p>
              <p className="mt-2 text-sm text-muted">{p.famousPlayer}</p>
            </li>
          ))}
        </ul>
      </section>

      {/* 티어 */}
      <section aria-labelledby="tiers">
        <h2 id="tiers" className="mb-1 text-xl font-extrabold">
          나는 어느 단계일까요?
        </h2>
        <p className="mb-3 text-sm text-muted">
          가장 가까운 설명을 고르면 돼요. 경기를 하면서 조금씩 맞춰져요.
        </p>
        <ol className="space-y-2">
          {tiers.map((t) => (
            <li
              key={t.tier}
              className="flex items-center gap-3 rounded-xl border border-edge bg-white p-4"
            >
              <span
                className="flex size-11 shrink-0 items-center justify-center rounded-lg bg-lime font-bold"
                aria-label={`${t.tier}단계`}
              >
                {t.tier}
              </span>
              <span className="text-sm">{t.label}</span>
            </li>
          ))}
        </ol>
      </section>

      {/* 매치 목록 */}
      <section aria-labelledby="matches">
        <h2 id="matches" className="mb-3 text-xl font-extrabold">
          모집 중인 농구 매치
        </h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {matches.map((m) => (
            <div key={m.id} className="lift relative">
              <MatchCard sport={basketball} {...m} />
              <button
                type="button"
                onClick={() => open(m)}
                aria-label={`${m.title} 상세 보기`}
                className="absolute inset-0 rounded-xl"
              />
            </div>
          ))}
        </div>
      </section>

      {/* FAQ */}
      <section aria-labelledby="faq">
        <h2 id="faq" className="mb-3 text-xl font-extrabold">
          규칙 FAQ
        </h2>
        <div className="space-y-2">
          {faq.map((item) => (
            <details
              key={item.q}
              className="rounded-xl border border-edge bg-white p-4"
            >
              <summary className="min-h-11 cursor-pointer py-2 text-sm font-bold">
                {item.q}
              </summary>
              <p className="mt-1 text-sm text-muted">{item.a}</p>
            </details>
          ))}
        </div>
        <p className="mt-2 text-xs text-muted">
          방장이 정한 규칙이 있으면 그쪽이 우선이에요.
        </p>
      </section>

      {/* 매치 상세 모달 */}
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
              <h2 id="match-title" className="text-xl font-black">
                {selected.title}
              </h2>
              <button
                type="button"
                onClick={close}
                aria-label="닫기"
                className="flex size-11 shrink-0 items-center justify-center rounded-lg hover:bg-edge"
              >
                <X size={20} aria-hidden="true" />
              </button>
            </div>

            <dl className="mt-4 space-y-2 text-sm">
              <div className="flex gap-3">
                <dt className="w-16 shrink-0 text-muted">장소</dt>
                <dd>{selected.venue}, {selected.distance}</dd>
              </div>

              <div className="flex gap-3">
                <dt className="w-16 shrink-0 text-muted">시간</dt>
                <dd>{selected.when}</dd>
              </div>

              <div className="flex gap-3">
                <dt className="w-16 shrink-0 text-muted">형식</dt>
                <dd>
                  {selected.capacity === 6 ? "3대3" : "5대5"}
                  {" · "}
                  {selected.joined}/{selected.capacity}명
                </dd>
              </div>

              <div className="flex gap-3">
                <dt className="w-16 shrink-0 text-muted">참가 단계</dt>
                <dd>
                  {tiers
                    .filter(
                      (t) =>
                        t.tier >= selected.tierRange[0] &&
                        t.tier <= selected.tierRange[1]
                    )
                    .map((t) => (
                      <span key={t.tier} className="block">
                        {t.tier}단계 · {t.label}
                      </span>
                    ))}
                </dd>
              </div>
            </dl>

            <p className="mt-4 rounded-lg bg-cream p-3 text-sm">
              {selected.description}
            </p>

            <ul className="mt-3 flex flex-wrap gap-1.5">
              {selected.reasons.map((r) => (
                <li
                  key={r}
                  className="rounded-lg bg-lime px-2.5 py-1 text-xs font-semibold"
                >
                  {r}
                </li>
              ))}
            </ul>

            {/* TODO: 신청 API 연동 */}
            <button
              type="button"
              disabled
              className="mt-5 min-h-12 w-full rounded-lg bg-night font-bold text-lime disabled:opacity-50"
            >
              신청하기 (준비 중)
            </button>
          </div>
        )}
      </dialog>
    </div>
  );
}
