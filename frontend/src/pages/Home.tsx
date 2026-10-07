import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import MatchCard from "../components/MatchCard";
import { football } from "../sports/football";
import { sports } from "../sports/registry";

// 흰/크림 바탕 + 사선 라임 띠. 주색은 라임, 남색은 글자와 일부 블록에만.

// TODO: 예시 데이터(mock)
const breakdown = [
  { label: "거리", value: 0.9, note: "집에서 약 3km" },
  { label: "실력", value: 0.72, note: "실력대 비슷" },
  { label: "시간", value: 1, note: "선호 시간대" },
  { label: "주최자", value: 0.8, note: "매너 좋음" },
];

const teams = [
  { name: "A팀", players: [["새벽슈터", "중급"], ["골밑장인", "상급"], ["패스요정", "초급"], ["점프왕", "중급"], ["리바운더", "중급"]] },
  { name: "B팀", players: [["코트러너", "상급"], ["3점머신", "중급"], ["수비벽", "중급"], ["드리블러", "초급"], ["센터킹", "중급"]] },
];

// 히어로 오른쪽: 종목 선택 패널 + 추천 매치 카드
function HeroPanel() {
  return (
    <div className="relative">
      <div className="rounded-xl bg-night p-6 text-white md:p-8">
        <p className="text-sm text-white/70">좋은 아침이에요</p>
        <p className="text-xl font-extrabold">오늘 어떤 운동할까요</p>
        <ul className="mt-5 grid grid-cols-3 gap-3">
          {sports.map(({ id, name, icon: Icon }) => (
            <li key={id}>
              <Link to={`/sports/${id}`} className="lift flex aspect-square flex-col items-center justify-center gap-2 rounded-xl bg-night-2 text-center text-sm font-bold">
                <span className="flex size-11 items-center justify-center rounded-lg bg-lime text-night">
                  <Icon size={22} aria-hidden="true" />
                </span>
                {name}
              </Link>
            </li>
          ))}
        </ul>
      </div>
      <div className="relative -mt-6 ml-6 md:-mr-8 md:ml-16">
        <MatchCard sport={football} title="일요일 오후 풋살" venue="다온 풋살장" when="10/11(일) 15:00" joined={7} capacity={10} reasons={["집에서 약 3km", "실력대 비슷"]} />
      </div>
    </div>
  );
}

export default function Home() {
  return (
    <div className="min-h-dvh bg-white">
      <header className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4">
        <span className="text-xl font-black tracking-tight">
          Team<span className="rounded-md bg-lime px-1">Up</span>
        </span>
        <div className="flex items-center gap-1">
          <Link to="/dashboard" className="flex min-h-11 items-center rounded-lg px-4 text-sm font-bold text-muted hover:bg-edge">
            로그인
          </Link>
          <Link to="/dashboard" className="flex min-h-11 items-center rounded-lg bg-night px-5 text-sm font-bold text-lime hover:opacity-90">
            시작하기
          </Link>
        </div>
      </header>

      {/* HERO: 왼쪽 문구, 오른쪽 종목 패널. 뒤에 사선 라임 띠 */}
      <section className="relative overflow-hidden">
        <div aria-hidden="true" className="absolute -top-24 left-[55%] h-[160%] w-[38%] rotate-[24deg] bg-lime" />
        <div className="relative mx-auto grid max-w-6xl items-center gap-12 px-4 pb-20 pt-10 md:grid-cols-2 md:pb-28 md:pt-16">
          <div className="rise">
            <h1 className="text-4xl font-black leading-[1.2] tracking-tight md:text-6xl">
              혼자 와도
              <br />
              <span className="bg-lime px-1">경기는 열려 있어요</span>
            </h1>
            <p className="mt-6 max-w-[36ch] text-lg leading-relaxed text-muted">
              가까운 곳에서 실력이 비슷한 사람들과 팀을 이뤄요. 농구, 축구/풋살, 배드민턴을 지원해요.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link to="/dashboard" className="inline-flex min-h-12 items-center gap-2 rounded-lg bg-night px-7 font-bold text-lime hover:opacity-90 active:scale-[0.98]">
                매치 찾기 <ArrowRight size={18} aria-hidden="true" />
              </Link>
              <a href="#why" className="inline-flex min-h-12 items-center rounded-lg border border-edge bg-white px-7 font-bold hover:bg-edge">
                추천 방식 보기
              </a>
            </div>
          </div>
          <div className="rise">
            <HeroPanel />
          </div>
        </div>
      </section>

      <main className="bg-cream">
        {/* 추천 이유를 숫자로 보여준다 (서비스 핵심: 설명 가능한 추천) */}
        <section aria-labelledby="why" className="mx-auto grid max-w-6xl items-center gap-10 px-4 py-20 md:grid-cols-2">
          <div>
            <h2 id="why" className="text-3xl font-black leading-tight tracking-tight md:text-4xl">
              왜 이 매치를 추천했는지
              <br />
              <span className="bg-lime px-1">전부 보여줘요</span>
            </h2>
            <p className="mt-4 max-w-[40ch] text-lg text-muted">
              거리, 실력, 시간대, 주최자 매너를 함께 따져 점수를 매겨요. 거리와 실력 중 무엇이 더 중요한지도 직접 조절할 수 있어요.
            </p>
          </div>
          <div className="rounded-xl bg-night p-6 text-white md:p-8">
            <div className="flex items-baseline justify-between">
              <p className="font-bold">일요일 오후 풋살</p>
              <p className="text-sm text-white/70">추천 점수 <span className="text-2xl font-black text-lime">86</span></p>
            </div>
            <ul className="mt-6 space-y-4">
              {breakdown.map(({ label, value, note }) => (
                <li key={label}>
                  <div className="flex justify-between text-sm">
                    <span className="font-semibold">{label}</span>
                    <span className="text-white/70">{note}</span>
                  </div>
                  <div className="mt-1.5 h-2.5 rounded-full bg-night-2" role="meter" aria-label={label} aria-valuenow={Math.round(value * 100)} aria-valuemin={0} aria-valuemax={100}>
                    <div className="h-full rounded-full bg-lime" style={{ width: `${value * 100}%` }} />
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* 팀 자동 분배 */}
        <section aria-labelledby="teams" className="mx-auto max-w-6xl px-4 pb-20">
          <h2 id="teams" className="text-3xl font-black tracking-tight md:text-4xl">
            정원이 차면, <span className="bg-lime px-1">두 팀으로 고르게</span>
          </h2>
          <p className="mt-3 text-lg text-muted">실력 합이 비슷하도록 자동으로 나누고, 주최자가 직접 조정할 수도 있어요.</p>
          <div className="mt-8 grid items-center gap-4 md:grid-cols-[1fr_auto_1fr]">
            {teams.map((t, i) => (
              <div key={t.name} className={`rounded-xl p-6 ${i === 0 ? "bg-white border border-edge md:order-1" : "bg-white border border-edge md:order-3"}`}>
                <p className="mb-3 text-lg font-black">{t.name}</p>
                <ul className="space-y-2">
                  {t.players.map(([nick, tier]) => (
                    <li key={nick} className="flex items-center justify-between rounded-lg bg-cream px-4 py-2 text-sm">
                      <span className="font-semibold">{nick}</span>
                      <span className="rounded-lg bg-lime px-2.5 py-0.5 text-xs font-bold">{tier}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
            <div className="flex flex-col items-center gap-2 rounded-xl bg-night px-6 py-5 text-center text-white md:order-2">
              <span className="text-sm text-white/70">예상 접전도</span>
              <span className="flex gap-1" role="img" aria-label="5단계 중 4단계">
                {[0, 1, 2, 3, 4].map((n) => (
                  <span key={n} className={`size-3 rounded-full ${n < 4 ? "bg-lime" : "bg-night-2"}`} />
                ))}
              </span>
              <span className="font-black text-lime">높음</span>
            </div>
          </div>
        </section>

        {/* 마무리 */}
        <section className="mx-auto max-w-6xl px-4 pb-16">
          <div className="flex flex-col items-start justify-between gap-6 rounded-xl bg-lime p-8 md:flex-row md:items-center md:p-12">
            <h2 className="text-3xl font-black md:text-4xl">이번 주말, 한 경기 뛰어봐요</h2>
            <Link to="/dashboard" className="inline-flex min-h-12 items-center gap-2 rounded-lg bg-night px-8 font-bold text-lime hover:opacity-90 active:scale-[0.98]">
              매치 찾기 <ArrowRight size={18} aria-hidden="true" />
            </Link>
          </div>
        </section>
        <footer className="border-t border-edge py-8 text-center text-sm text-muted">© TeamUp, 학회 프로젝트</footer>
      </main>
    </div>
  );
}
