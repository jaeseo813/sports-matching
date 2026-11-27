import { useState, type FormEvent } from "react";
import Field from "../components/Field";
import { ApiError, post } from "../lib/api/client";
import type { VenueOut } from "../lib/api/types";
import { useAuth } from "../lib/auth";
import { sports } from "../sports/registry";

const empty = { name: "", address: "", lat: "", lng: "" };

// 관리자 전용. 화면을 숨기는 것은 편의일 뿐이고 권한은 서버(require_admin)가 검사한다
export default function VenueNew() {
  const { user } = useAuth();
  const [form, setForm] = useState(empty);
  const [picked, setPicked] = useState<string[]>([]);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!user?.is_admin) return <p role="alert" className="rounded-xl border border-edge bg-white p-5 text-sm">⚠ 관리자만 구장을 등록할 수 있어요.</p>;

  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (picked.length === 0) {
      setErrors({ sports: "종목을 하나 이상 골라 주세요" });
      return;
    }
    setBusy(true);
    setErrors({});
    setMsg(null);
    try {
      const venue = await post<VenueOut>("/venues", { ...form, lat: Number(form.lat), lng: Number(form.lng), sports: picked });
      setMsg(`"${venue.name}"을(를) 등록했어요.`);
      setForm(empty);
      setPicked([]);
    } catch (err) {
      if (err instanceof ApiError) setErrors(err.fields);
      setMsg(`⚠ ${err instanceof ApiError ? err.message : "서버에 연결할 수 없어요"}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-xl">
      <h1 className="text-2xl font-black">구장 등록</h1>
      <form onSubmit={submit} className="mt-6 space-y-4">
        <Field label="이름" required maxLength={100} value={form.name} onChange={set("name")} error={errors.name} />
        <Field label="주소" required maxLength={255} value={form.address} onChange={set("address")} error={errors.address} />
        <div className="grid grid-cols-2 gap-3">
          <Field label="위도 (33~39)" type="number" required min={33} max={39} step="any" value={form.lat} onChange={set("lat")} error={errors.lat} />
          <Field label="경도 (124~132)" type="number" required min={124} max={132} step="any" value={form.lng} onChange={set("lng")} error={errors.lng} />
        </div>
        <fieldset>
          <legend className="mb-1 text-sm font-bold">할 수 있는 종목</legend>
          <div className="flex gap-2">
            {sports.map((s) => (
              <label key={s.id} className="flex min-h-11 flex-1 cursor-pointer items-center justify-center gap-2 rounded-lg border border-edge bg-white text-sm font-bold has-[:checked]:bg-lime">
                <input
                  type="checkbox"
                  checked={picked.includes(s.id)}
                  onChange={() => setPicked(picked.includes(s.id) ? picked.filter((x) => x !== s.id) : [...picked, s.id])}
                />
                {s.name}
              </label>
            ))}
          </div>
          {errors.sports && <p className="mt-1 text-sm font-semibold">⚠ {errors.sports}</p>}
        </fieldset>
        {msg && <p role="status" className="text-sm font-semibold">{msg}</p>}
        <button type="submit" disabled={busy} className="min-h-12 w-full rounded-lg bg-night font-bold text-lime disabled:opacity-50">
          {busy ? "등록하는 중…" : "구장 등록"}
        </button>
      </form>
    </div>
  );
}
