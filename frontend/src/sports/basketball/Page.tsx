import MatchList from "../../components/MatchList";
import { SportChat } from "../../components/ChatPanel";
import { useSportRules } from "../../lib/sports";
import { basketball } from ".";
import { formats, positions } from "./data";

// 농구 담당 영역: 이 폴더(src/sports/basketball) 안에서만 작업한다.
export default function Page() {
  const sports = useSportRules();
  const basketballRules = sports?.find(
    (sport) => sport.id === basketball.id,
  );

  const tiers = basketballRules
    ? Object.entries(basketballRules.tier_labels).sort(
        ([a], [b]) => Number(a) - Number(b),
      )
    : [];

  return (
    <div className="space-y-10">
      {/* 종목 소개 */}
      <section
        className={`rounded-xl p-6 md:p-8 ${basketball.bg} ${basketball.fg}`}
      >
        <basketball.icon size={28} aria-hidden="true" />

        <h1 className="mt-3 text-2xl font-black md:text-4xl">
          {basketball.name}
        </h1>

        <p className="mt-2 text-sm">
          3대3부터 5대5까지! 비슷한 실력의 사람들과 가까운 곳에서 농구를 즐겨 보세요.
        </p>
      </section>

      {/* 경기 인원 구성 */}
      <section aria-labelledby="formats">
        <h2 id="formats" className="mb-3 text-xl font-extrabold">
          경기 방식
        </h2>

        <div className="grid gap-4 md:grid-cols-2">
          {formats.map((format) => (
            <article
              key={format.name}
              className="rounded-xl border border-edge bg-white p-5"
            >
              <h3 className="text-lg font-bold">{format.name}</h3>
              <p className="mt-1 text-sm text-muted">
                팀당 {format.team}
              </p>
              <p className="mt-2 text-sm">
                총 {format.total}명이 필요한 경기예요.
              </p>
              <p className="mt-2 text-sm text-muted">
                {format.note}
              </p>
            </article>
          ))}
        </div>
      </section>

      {/* 포지션 */}
      <section aria-labelledby="positions">
        <h2 id="positions" className="mb-3 text-xl font-extrabold">
          농구 포지션
        </h2>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {positions.map((position) => (
            <article
              key={position.code}
              className="rounded-xl border border-edge bg-white p-5"
            >
              <div className="flex items-center gap-2">
                <span className="rounded-lg bg-lime px-3 py-1 font-black">
                  {position.code}
                </span>
                <h3 className="font-bold">{position.name}</h3>
              </div>

              <p className="mt-3 text-sm text-muted">
                {position.description}
              </p>

              <p className="mt-2 text-xs text-muted">
                 유명한 선수: {position.players.join(", ")}
              </p>
            </article>
          ))}
        </div>
      </section>

      {/* 티어 및 챗봇 */}
      <div className="grid gap-10 md:grid-cols-2">
        <section aria-labelledby="tiers">
          <h2 id="tiers" className="mb-3 text-xl font-extrabold">
            농구 실력 티어
          </h2>

          {!basketballRules ? (
            <p className="text-sm text-muted">
              티어 정보를 불러오는 중이거나 불러오지 못했습니다.
            </p>
          ) : (
            <ol className="space-y-2">
              {tiers.map(([tier, label]) => (
                <li
                  key={tier}
                  className="flex items-start gap-3 rounded-xl border border-edge bg-white p-4"
                >
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-lime font-black">
                    {tier}
                  </span>

                  <span className="text-sm">{label}</span>
                </li>
              ))}
            </ol>
          )}
        </section>

        <SportChat sport={basketball.id} />
      </div>

      {/* 매치 목록 */}
      <section aria-labelledby="matches">
        <h2 id="matches" className="mb-3 text-xl font-extrabold">
          모집 중인 농구 매치
        </h2>

        <MatchList sport={basketball.id} />
      </section>
    </div>
  );
}
