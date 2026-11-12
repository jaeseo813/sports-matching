import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import Field from "../components/Field";
import { ApiError, post } from "../lib/api/client";
import type { GenderPolicy, MatchOut, VenueOut } from "../lib/api/types";
import { genderPolicyLabel, teamSizeLabel } from "../lib/labels";
import { useSportRules } from "../lib/sports";
import { useApi } from "../lib/useApi";
import { sports } from "../sports/registry";

const selectCls = "min-h-11 w-full rounded-lg border border-edge bg-white px-3 text-sm";

function tomorrowLocal(): { date: string; time: string } {
  const d = new Date(Date.now() + 24 * 3600 * 1000);
  const pad = (n: number) => String(n).padStart(2, "0");
  return { date: `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`, time: "19:00" };
}

export default function MatchNew() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const rules = useSportRules();
  const [sport, setSport] = useState(params.get("sport") ?? "badminton");
  const rule = rules?.find((r) => r.id === sport);
  const venues = useApi<VenueOut[]>(`/me/venues?sport=${encodeURIComponent(sport)}`);

  const init = tomorrowLocal();
  const [form, setForm] = useState({ title: "", description: "", date: init.date, time: init.time, duration: "90" });
  const [venueId, setVenueId] = useState<number | null>(null);
  const [teamSize, setTeamSize] = useState<number | null>(null);
  const [tier, setTier] = useState<[number, number]>([1, 5]);
  const [gender, setGender] = useState<GenderPolicy>("any");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // 종목이 바뀌면 그 종목의 구장·팀 인원으로 다시 고른다
  useEffect(() => setVenueId(venues.data?.[0]?.id ?? null), [venues.data]);
  useEffect(() => setTeamSize(rule?.players_per_team.at(-1) ?? null), [rule]);

  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (venueId === null || teamSize === null) return;
    setBusy(true);
    setErrors({});
    setFormError(null);
    try {
      const created = await post<MatchOut>("/matches", {
        sport,
        venue_id: venueId,
        title: form.title,
        description: form.description || null,
        starts_at: new Date(`${form.date}T${form.time}`).toISOString(),
        duration_min: Number(form.duration),
        team_size: teamSize,
        tier_min: tier[0],
        tier_max: tier[1],
        gender_policy: gender,
      });
      navigate(`/matches/${created.id}`, { replace: true });
    } catch (err) {
      if (err instanceof ApiError) {
        setErrors(err.fields);
        if (Object.keys(err.fields).length === 0) setFormError(err.message);
      } else setFormError("서버에 연결할 수 없어요");
    } finally {
      setBusy(false);
    }
  };

  const needsLocation = venues.error?.code === "LOCATION_NOT_SET";

  return (
    <div className="mx-auto max-w-xl">
      <h1 className="text-2xl font-black">매치 열기</h1>
      <p className="mt-1 text-sm text-muted">정원은 종목 규칙에 따라 자동으로 정해져요. 나도 참가자로 포함돼요.</p>
      <form onSubmit={submit} className="mt-6 space-y-4">
        <div>
          <label htmlFor="sport" className="mb-1 block text-sm font-bold">종목</label>
          <select id="sport" value={sport} onChange={(e) => setSport(e.target.value)} className={selectCls}>
            {sports.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="venue" className="mb-1 block text-sm font-bold">구장 (내 활동 지역 근처)</label>
          {needsLocation ? (
            <p className="rounded-lg border border-edge bg-white p-3 text-sm">
              ⚠ 활동 지역을 먼저 등록해 주세요.{" "}
              <Link to="/onboarding" className="font-bold underline">등록하기</Link>
            </p>
          ) : venues.data && venues.data.length === 0 ? (
            <p className="rounded-lg border border-edge bg-white p-3 text-sm">⚠ 활동 지역 근처에 이 종목을 할 수 있는 구장이 없어요. 거리를 넓히거나 다른 종목을 골라 보세요.</p>
          ) : (
            <select id="venue" required value={venueId ?? ""} onChange={(e) => setVenueId(Number(e.target.value))} className={selectCls}>
              {(venues.data ?? []).map((v) => (
                <option key={v.id} value={v.id}>
                  {v.name}{v.distance_km !== null ? ` · 약 ${Math.max(1, Math.round(v.distance_km))}km` : ""}
                </option>
              ))}
            </select>
          )}
        </div>

        <Field label="제목" required maxLength={100} placeholder="예: 평일 저녁 복식" value={form.title} onChange={set("title")} error={errors.title} />
        <div>
          <label htmlFor="desc" className="mb-1 block text-sm font-bold">소개 (선택)</label>
          <textarea id="desc" maxLength={1000} rows={3} value={form.description} onChange={set("description")} className="w-full rounded-lg border border-edge bg-white p-3 text-sm" />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Field label="날짜" type="date" required value={form.date} onChange={set("date")} error={errors.starts_at} />
          <Field label="시작 시간" type="time" required value={form.time} onChange={set("time")} />
        </div>
        <div>
          <label htmlFor="duration" className="mb-1 block text-sm font-bold">경기 시간</label>
          <select id="duration" value={form.duration} onChange={set("duration")} className={selectCls}>
            {[60, 90, 120, 180].map((n) => (
              <option key={n} value={n}>{n}분</option>
            ))}
          </select>
        </div>

        {rule && (
          <fieldset>
            <legend className="mb-1 text-sm font-bold">형식</legend>
            <div className="flex gap-2">
              {rule.players_per_team.map((n) => (
                <label key={n} className="flex min-h-11 flex-1 cursor-pointer items-center justify-center rounded-lg border border-edge bg-white text-sm font-bold has-[:checked]:bg-lime">
                  <input type="radio" name="team" className="sr-only" checked={teamSize === n} onChange={() => setTeamSize(n)} />
                  {teamSizeLabel(sport, n)} · 총 {n * rule.team_count}명
                </label>
              ))}
            </div>
          </fieldset>
        )}

        <fieldset>
          <legend className="mb-1 text-sm font-bold">참가 단계</legend>
          <div className="flex items-center gap-2 text-sm">
            <select aria-label="최소 단계" value={tier[0]} onChange={(e) => setTier([Number(e.target.value), Math.max(Number(e.target.value), tier[1])])} className={selectCls}>
              {[1, 2, 3, 4, 5].map((t) => <option key={t} value={t}>{t}단계</option>)}
            </select>
            <span>~</span>
            <select aria-label="최대 단계" value={tier[1]} onChange={(e) => setTier([Math.min(tier[0], Number(e.target.value)), Number(e.target.value)])} className={selectCls}>
              {[1, 2, 3, 4, 5].map((t) => <option key={t} value={t}>{t}단계</option>)}
            </select>
          </div>
        </fieldset>

        <div>
          <label htmlFor="gender" className="mb-1 block text-sm font-bold">성별</label>
          <select id="gender" value={gender} onChange={(e) => setGender(e.target.value as GenderPolicy)} className={selectCls}>
            {(Object.keys(genderPolicyLabel) as GenderPolicy[]).map((g) => (
              <option key={g} value={g}>{genderPolicyLabel[g]}</option>
            ))}
          </select>
        </div>

        {formError && <p role="alert" className="text-sm font-semibold">⚠ {formError}</p>}
        <button type="submit" disabled={busy || venueId === null || teamSize === null} className="min-h-12 w-full rounded-lg bg-night font-bold text-lime disabled:opacity-50">
          {busy ? "여는 중…" : "매치 열기"}
        </button>
      </form>
    </div>
  );
}
