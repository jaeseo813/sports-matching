import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError, api } from "../lib/api/client";
import type { LocationOut, SkillOut } from "../lib/api/types";
import { useAuth } from "../lib/auth";
import { useSportRules } from "../lib/sports";
import { sports } from "../sports/registry";

// 활동 지역 후보. 구 중심 근처의 대략적인 좌표만 쓴다 (정확한 현재 위치를 상시 수집하지 않는다)
const areas = [
  { label: "강남구", lat: 37.517, lng: 127.047 },
  { label: "서초구", lat: 37.484, lng: 127.033 },
  { label: "송파구", lat: 37.514, lng: 127.106 },
  { label: "동대문구", lat: 37.574, lng: 127.04 },
  { label: "성북구", lat: 37.589, lng: 127.017 },
  { label: "마포구", lat: 37.566, lng: 126.902 },
  { label: "용산구", lat: 37.532, lng: 126.99 },
  { label: "관악구", lat: 37.478, lng: 126.951 },
];

const steps = ["종목", "실력", "활동 지역"];

export default function Onboarding() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const rules = useSportRules();
  const [step, setStep] = useState(0);
  const [picked, setPicked] = useState<string[]>([]);
  const [skill, setSkill] = useState<Record<string, { tier: number; years: number }>>({});
  const [area, setArea] = useState<string>(areas[0].label);
  const [radius, setRadius] = useState(5);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // 이미 등록한 값이 있으면 불러와 수정할 수 있게 한다
  useEffect(() => {
    api<SkillOut[]>("/me/skills")
      .then((list) => {
        setPicked(list.map((s) => s.sport));
        setSkill(Object.fromEntries(list.map((s) => [s.sport, { tier: s.tier, years: s.years_played }])));
      })
      .catch(() => undefined);
    api<LocationOut[]>("/me/locations")
      .then((list) => {
        const first = list[0];
        if (first) {
          if (areas.some((a) => a.label === first.label)) setArea(first.label);
          setRadius(first.max_distance_km);
        }
      })
      .catch(() => undefined);
  }, []);

  const toggle = (id: string) => setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : [...p, id]));
  const skillOf = (id: string) => skill[id] ?? { tier: 2, years: 0 };

  const finish = async () => {
    setBusy(true);
    setError(null);
    try {
      for (const id of picked) {
        const s = skillOf(id);
        await api(`/me/skills/${id}`, { method: "PUT", body: JSON.stringify({ self_tier: s.tier, years_played: s.years }) });
      }
      const a = areas.find((x) => x.label === area)!;
      await api("/me/locations/1", { method: "PUT", body: JSON.stringify({ label: a.label, lat: a.lat, lng: a.lng, max_distance_km: radius }) });
      navigate("/dashboard", { replace: true });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "저장하지 못했어요");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-xl">
      <p className="text-sm text-muted">{user?.nickname}님, 몇 가지만 알려 주세요</p>
      <h1 className="mt-1 text-2xl font-black">맞춤 매치 설정</h1>
      <ol className="mt-4 flex gap-2 text-sm font-bold" aria-label="진행 단계">
        {steps.map((s, i) => (
          <li key={s} aria-current={i === step ? "step" : undefined} className={`flex-1 rounded-lg px-3 py-2 text-center ${i === step ? "bg-lime" : i < step ? "bg-edge" : "border border-edge text-muted"}`}>
            {i + 1}. {s}
          </li>
        ))}
      </ol>

      <div className="mt-6 space-y-4">
        {step === 0 && (
          <fieldset>
            <legend className="mb-2 font-bold">어떤 운동을 하나요? (여러 개 선택 가능)</legend>
            <div className="grid gap-2">
              {sports.map((s) => (
                <label key={s.id} className="flex min-h-14 cursor-pointer items-center gap-3 rounded-xl border border-edge bg-white px-4 font-bold has-[:checked]:bg-lime">
                  <input type="checkbox" checked={picked.includes(s.id)} onChange={() => toggle(s.id)} className="size-5" />
                  <s.icon size={20} aria-hidden="true" />
                  {s.name}
                </label>
              ))}
            </div>
          </fieldset>
        )}

        {step === 1 &&
          picked.map((id) => {
            const s = sports.find((x) => x.id === id)!;
            const labels = rules?.find((r) => r.id === id)?.tier_labels ?? {};
            return (
              <fieldset key={id} className="rounded-xl border border-edge bg-white p-4">
                <legend className="px-1 font-bold">{s.name}: 나와 가장 가까운 설명은?</legend>
                <div className="mt-2 space-y-2">
                  {[1, 2, 3, 4, 5].map((t) => (
                    <label key={t} className="flex min-h-11 cursor-pointer items-center gap-3 rounded-lg border border-edge px-3 text-sm has-[:checked]:bg-lime">
                      <input type="radio" name={`tier-${id}`} checked={skillOf(id).tier === t} onChange={() => setSkill({ ...skill, [id]: { ...skillOf(id), tier: t } })} />
                      <span className="font-bold">{t}단계</span>
                      <span>{labels[String(t)] ?? ""}</span>
                    </label>
                  ))}
                </div>
                <label className="mt-3 flex items-center gap-2 text-sm">
                  해온 기간
                  <select value={skillOf(id).years} onChange={(e) => setSkill({ ...skill, [id]: { ...skillOf(id), years: Number(e.target.value) } })} className="min-h-11 rounded-lg border border-edge bg-white px-3">
                    {[0, 1, 2, 3, 5, 10].map((y) => (
                      <option key={y} value={y}>{y === 0 ? "1년 미만" : `${y}년${y === 10 ? " 이상" : ""}`}</option>
                    ))}
                  </select>
                </label>
              </fieldset>
            );
          })}

        {step === 2 && (
          <>
            <div>
              <label htmlFor="area" className="mb-1 block font-bold">주로 운동하는 지역</label>
              <select id="area" value={area} onChange={(e) => setArea(e.target.value)} className="min-h-11 w-full rounded-lg border border-edge bg-white px-3 text-sm">
                {areas.map((a) => (
                  <option key={a.label} value={a.label}>{a.label}</option>
                ))}
              </select>
              <p className="mt-1 text-sm text-muted">정확한 위치는 받지 않아요. 지역 중심을 기준으로 거리를 계산해요.</p>
            </div>
            <div>
              <label htmlFor="radius" className="mb-1 block font-bold">이동 가능 거리: 약 {radius}km</label>
              <input id="radius" type="range" min={1} max={30} value={radius} onChange={(e) => setRadius(Number(e.target.value))} className="h-11 w-full accent-night" />
            </div>
          </>
        )}

        {error && <p role="alert" className="text-sm font-semibold">⚠ {error}</p>}

        <div className="flex gap-2">
          {step > 0 && (
            <button type="button" onClick={() => setStep(step - 1)} className="min-h-12 flex-1 rounded-lg border border-edge font-bold">
              이전
            </button>
          )}
          {step < 2 ? (
            <button type="button" disabled={picked.length === 0} onClick={() => setStep(step + 1)} className="min-h-12 flex-1 rounded-lg bg-night font-bold text-lime disabled:opacity-50">
              다음
            </button>
          ) : (
            <button type="button" disabled={busy} onClick={finish} className="min-h-12 flex-1 rounded-lg bg-night font-bold text-lime disabled:opacity-50">
              {busy ? "저장 중…" : "완료"}
            </button>
          )}
        </div>
        {step === 0 && picked.length === 0 && <p className="text-sm text-muted">종목을 하나 이상 골라 주세요.</p>}
      </div>
    </div>
  );
}
