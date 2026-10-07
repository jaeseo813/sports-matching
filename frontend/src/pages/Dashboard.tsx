import { Link } from "react-router-dom";
import { CalendarCheck, Settings, Star, Users } from "lucide-react";
import MatchCard from "../components/MatchCard";
import { sports } from "../sports/registry";

// TODO: 예시 데이터(mock). API 연동 시 교체
const stats = [
  { label: "참가 예정", value: "2", icon: CalendarCheck },
  { label: "참가 완료", value: "14", icon: Users },
  { label: "매너 점수", value: "4.8", icon: Star },
];

const upcoming = [
  { id: 1, sport: "basketball", title: "토요일 오전 매치", venue: "모아 체육관", when: "10/10(토) 10:00", distance: "약 2km", joined: 8, capacity: 10 },
  { id: 2, sport: "badminton", title: "평일 저녁 복식", venue: "새솔 실내체육관", when: "10/13(화) 19:30", distance: "약 4km", joined: 3, capacity: 4 },
];

const recommended = [
  { id: 3, sport: "football", title: "일요일 오후 풋살", venue: "다온 풋살장", when: "10/11(일) 15:00", reasons: ["집에서 약 3km", "실력대 비슷"] },
  { id: 4, sport: "basketball", title: "금요일 밤 매치", venue: "한결 스포츠센터", when: "10/16(금) 21:00", reasons: ["학교에서 약 5km", "선호 시간대"] },
  { id: 5, sport: "badminton", title: "토요일 오후 복식", venue: "누리 체육관", when: "10/10(토) 14:00", reasons: ["집에서 약 1km", "실력대 비슷"] },
];

const sportOf = (id: string) => sports.find((s) => s.id === id)!;

export default function Dashboard() {
  return (
    <>
      {/* 인사 블록 */}
      <section className="mt-6 rounded-xl bg-lime p-6 md:p-8">
        <div className="mx-auto flex max-w-6xl items-start justify-between">
          <div>
            <p className="text-sm">다시 만나서 반가워요</p>
            <h1 className="mt-1 text-2xl font-black md:text-4xl">이번 주 경기 2개가 예정되어 있어요</h1>
          </div>
          <Link to="/me" aria-label="설정" className="flex size-11 shrink-0 items-center justify-center rounded-lg bg-night text-lime">
            <Settings size={20} aria-hidden="true" />
          </Link>
        </div>
      </section>

      {/* 큰 아이콘 버튼 형태의 활동 요약 */}
      <section aria-labelledby="summary" className="!mt-8">
        <h2 id="summary" className="mb-4 text-xl font-extrabold">내 활동 기록</h2>
        <ul className="grid grid-cols-3 gap-3 md:max-w-2xl">
          {stats.map(({ label, value, icon: Icon }) => (
            <li key={label} className="flex aspect-square flex-col items-center justify-center gap-1 rounded-xl bg-night text-center text-white">
              <span className="flex size-10 items-center justify-center rounded-lg bg-lime text-night">
                <Icon size={20} aria-hidden="true" />
              </span>
              <span className="text-2xl font-black">{value}</span>
              <span className="text-xs text-white/70">{label}</span>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="upcoming">
        <h2 id="upcoming" className="mb-4 text-xl font-extrabold">참가 예정 매치</h2>
        <ul className="grid gap-4 md:grid-cols-2">
          {upcoming.map(({ id, sport, ...m }) => (
            <li key={id} className="lift">
              <MatchCard sport={sportOf(sport)} {...m} />
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="recommended">
        <div className="mb-4 flex items-center justify-between">
          <h2 id="recommended" className="text-xl font-extrabold">나를 위한 추천</h2>
          <Link to="/matches" className="flex min-h-11 items-center text-sm font-bold underline underline-offset-4">더 보기</Link>
        </div>
        <ul className="grid gap-4 md:grid-cols-3">
          {recommended.map(({ id, sport, ...m }) => (
            <li key={id} className="lift">
              <MatchCard sport={sportOf(sport)} {...m} />
            </li>
          ))}
        </ul>
      </section>
    </>
  );
}
