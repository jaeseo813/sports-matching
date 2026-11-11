import { Link } from "react-router-dom";
import type { LocationOut, SkillOut } from "../lib/api/types";
import { useAuth } from "../lib/auth";
import { trendLabel } from "../lib/labels";
import { useSportRules } from "../lib/sports";
import { useApi } from "../lib/useApi";
import { sports } from "../sports/registry";

const genderLabel = { male: "남성", female: "여성", other: "기타" } as const;

export default function MyPage() {
  const { user, logout } = useAuth();
  const rules = useSportRules();
  const skills = useApi<SkillOut[]>("/me/skills");
  const locations = useApi<LocationOut[]>("/me/locations");
  if (!user) return null;

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <h1 className="text-2xl font-extrabold">내 정보</h1>

      <section className="rounded-xl border border-edge bg-white p-5">
        <p className="text-xl font-black">{user.nickname}</p>
        <p className="mt-1 text-sm text-muted">
          {user.email} · {genderLabel[user.gender]}
        </p>
      </section>

      <section aria-labelledby="skills" className="rounded-xl border border-edge bg-white p-5">
        <div className="flex items-center justify-between">
          <h2 id="skills" className="text-lg font-extrabold">종목과 실력</h2>
          <Link to="/onboarding" className="flex min-h-11 items-center text-sm font-bold underline">수정</Link>
        </div>
        {skills.data && skills.data.length === 0 && <p className="mt-2 text-sm text-muted">아직 등록한 종목이 없어요.</p>}
        <ul className="mt-2 divide-y divide-edge">
          {skills.data?.map((s) => {
            const sport = sports.find((x) => x.id === s.sport);
            const label = rules?.find((r) => r.id === s.sport)?.tier_labels[String(s.tier)];
            return (
              <li key={s.sport} className="flex items-center gap-3 py-3">
                <span className="flex size-11 shrink-0 items-center justify-center rounded-lg bg-lime font-black" aria-label={`${s.tier}단계`}>
                  {s.tier}
                </span>
                <span className="flex-1 text-sm">
                  <span className="block font-bold">{sport?.name ?? s.sport}</span>
                  {label && <span className="block text-muted">{label}</span>}
                </span>
                <span className="text-sm font-semibold">{trendLabel[s.trend]}</span>
              </li>
            );
          })}
        </ul>
        <p className="mt-2 text-xs text-muted">단계는 경기 후 상호 평가로 조금씩 맞춰져요.</p>
      </section>

      <section aria-labelledby="locs" className="rounded-xl border border-edge bg-white p-5">
        <div className="flex items-center justify-between">
          <h2 id="locs" className="text-lg font-extrabold">활동 지역</h2>
          <Link to="/onboarding" className="flex min-h-11 items-center text-sm font-bold underline">수정</Link>
        </div>
        {locations.data && locations.data.length === 0 && <p className="mt-2 text-sm text-muted">아직 등록한 지역이 없어요.</p>}
        <ul className="mt-2 space-y-1 text-sm">
          {locations.data?.map((l) => (
            <li key={l.slot}>
              <span className="font-bold">{l.label}</span> · 약 {l.max_distance_km}km 이내
            </li>
          ))}
        </ul>
      </section>

      <button
        type="button"
        onClick={() => void logout()}
        className="min-h-12 w-full rounded-lg border border-edge bg-white font-bold"
      >
        로그아웃
      </button>
    </div>
  );
}
