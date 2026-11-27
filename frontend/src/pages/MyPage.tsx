import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api/client";
import type { BlockOut, LocationOut, SkillOut } from "../lib/api/types";
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
  const blocks = useApi<BlockOut[]>("/me/blocks");
  const [blockError, setBlockError] = useState(false);
  if (!user) return null;

  const unblock = async (id: number) => {
    setBlockError(false);
    try {
      await api(`/me/blocks/${id}`, { method: "DELETE" });
      blocks.reload();
    } catch {
      setBlockError(true);
    }
  };

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

      <section aria-labelledby="blocks" className="rounded-xl border border-edge bg-white p-5">
        <h2 id="blocks" className="text-lg font-extrabold">차단한 사람</h2>
        <p className="mt-1 text-xs text-muted">차단한 사람이 연 매치는 추천과 목록에 나오지 않아요.</p>
        {blocks.data && blocks.data.length === 0 && <p className="mt-2 text-sm text-muted">차단한 사람이 없어요.</p>}
        {blockError && <p role="alert" className="mt-2 text-sm font-semibold">⚠ 차단을 풀지 못했어요</p>}
        <ul className="mt-2 divide-y divide-edge">
          {blocks.data?.map((b) => (
            <li key={b.user_id} className="flex items-center justify-between py-2 text-sm">
              <span className="font-bold">{b.nickname}</span>
              <button type="button" onClick={() => void unblock(b.user_id)} className="min-h-11 rounded-lg border border-edge px-4 font-bold">
                차단 해제
              </button>
            </li>
          ))}
        </ul>
      </section>

      {user.is_admin && (
        <Link to="/venues/new" className="flex min-h-12 items-center justify-center rounded-lg bg-night font-bold text-lime">
          구장 등록 (관리자)
        </Link>
      )}

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
