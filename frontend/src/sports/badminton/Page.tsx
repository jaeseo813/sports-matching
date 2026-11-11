import MatchList from "../../components/MatchList";
import { badminton } from ".";
import { faq, formats, tiers } from "./data";

// 배드민턴 담당 영역: 이 폴더(src/sports/badminton) 안에서만 작업한다.
export default function Page() {
  return (
    <div className="space-y-10">
      <section className={`rounded-xl p-6 md:p-8 ${badminton.bg} ${badminton.fg}`}>
        <badminton.icon size={28} aria-hidden="true" />
        <h1 className="mt-3 text-2xl font-black md:text-4xl">{badminton.name}</h1>
        <p className="mt-2 text-sm">
          단식은 둘이서, 복식은 넷이서 쳐요. 비슷한 실력의 사람을 가까운 곳에서 만나 보세요.
        </p>
      </section>

      <section aria-labelledby="formats">
        <h2 id="formats" className="mb-3 text-xl font-extrabold">인원 구성</h2>
        <ul className="grid gap-3 md:grid-cols-2">
          {formats.map((f) => (
            <li key={f.name} className="rounded-xl border border-edge bg-white p-5">
              <p className="flex items-baseline justify-between">
                <span className="text-lg font-bold">{f.name}</span>
                <span className="text-sm font-medium text-muted">{f.team} · 총 {f.total}명</span>
              </p>
              <p className="mt-2 text-sm text-muted">{f.note}</p>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="tiers">
        <h2 id="tiers" className="mb-1 text-xl font-extrabold">나는 어느 단계일까요?</h2>
        <p className="mb-3 text-sm text-muted">가장 가까운 설명을 고르면 돼요. 경기를 하면서 조금씩 맞춰져요.</p>
        <ol className="space-y-2">
          {tiers.map((t) => (
            <li key={t.tier} className="flex items-center gap-3 rounded-xl border border-edge bg-white p-4">
              <span className="flex size-11 shrink-0 items-center justify-center rounded-lg bg-lime font-bold" aria-label={`${t.tier}단계`}>
                {t.tier}
              </span>
              <span className="text-sm">{t.label}</span>
            </li>
          ))}
        </ol>
      </section>

      <section aria-labelledby="matches">
        <h2 id="matches" className="mb-3 text-xl font-extrabold">모집 중인 배드민턴 매치</h2>
        <MatchList sport="badminton" />
      </section>

      <section aria-labelledby="faq">
        <h2 id="faq" className="mb-3 text-xl font-extrabold">규칙 FAQ</h2>
        <div className="space-y-2">
          {faq.map((item) => (
            <details key={item.q} className="rounded-xl border border-edge bg-white p-4">
              <summary className="min-h-11 cursor-pointer py-2 text-sm font-bold">{item.q}</summary>
              <p className="mt-1 text-sm text-muted">{item.a}</p>
            </details>
          ))}
        </div>
        <p className="mt-2 text-xs text-muted">방장이 정한 규칙이 있으면 그쪽이 우선이에요.</p>
      </section>
    </div>
  );
}
