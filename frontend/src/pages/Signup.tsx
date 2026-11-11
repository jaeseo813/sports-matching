import { useState, type FormEvent } from "react";
import { Link, Navigate } from "react-router-dom";
import Field from "../components/Field";
import { ApiError } from "../lib/api/client";
import { useAuth, type Gender } from "../lib/auth";

const genders: { value: Gender; label: string }[] = [
  { value: "male", label: "남성" },
  { value: "female", label: "여성" },
  { value: "other", label: "기타" },
];

export default function Signup() {
  const { user, signup } = useAuth();
  const [form, setForm] = useState({ email: "", password: "", nickname: "", birthYear: "" });
  const [gender, setGender] = useState<Gender>("male");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false); // 방금 가입했으면 온보딩으로 보낸다

  if (user && !busy) return <Navigate to={done ? "/onboarding" : "/dashboard"} replace />;

  const set = (key: keyof typeof form) => (e: { target: { value: string } }) => setForm({ ...form, [key]: e.target.value });

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setErrors({});
    setFormError(null);
    try {
      await signup({
        email: form.email,
        password: form.password,
        nickname: form.nickname,
        gender,
        birth_year: Number(form.birthYear),
      });
      setDone(true);
    } catch (err) {
      if (err instanceof ApiError) {
        setErrors(err.fields);
        if (Object.keys(err.fields).length === 0) setFormError(err.message);
      } else {
        setFormError("서버에 연결할 수 없어요");
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="mx-auto max-w-sm px-4 py-12">
      <h1 className="text-2xl font-black">가입하기</h1>
      <p className="mt-1 text-sm text-muted">개발용 서비스예요. 실제 이메일·비밀번호 대신 더미 값을 써 주세요.</p>
      <form onSubmit={submit} className="mt-6 space-y-4">
        <Field label="이메일" type="email" autoComplete="email" required value={form.email} onChange={set("email")} error={errors.email} />
        <Field label="비밀번호 (8자 이상)" type="password" autoComplete="new-password" required minLength={8} value={form.password} onChange={set("password")} error={errors.password} />
        <Field label="닉네임 (2~30자)" required minLength={2} maxLength={30} value={form.nickname} onChange={set("nickname")} error={errors.nickname} />
        <fieldset>
          <legend className="mb-1 text-sm font-bold">성별</legend>
          <div className="flex gap-2">
            {genders.map((g) => (
              <label key={g.value} className="flex min-h-11 flex-1 cursor-pointer items-center justify-center rounded-lg border border-edge bg-white text-sm font-bold has-[:checked]:bg-lime">
                <input type="radio" name="gender" value={g.value} checked={gender === g.value} onChange={() => setGender(g.value)} className="sr-only" />
                {g.label}
              </label>
            ))}
          </div>
          {errors.gender && <p className="mt-1 text-sm font-semibold">⚠ {errors.gender}</p>}
        </fieldset>
        <Field label="출생연도" type="number" inputMode="numeric" required min={1920} max={2100} placeholder="예: 2002" value={form.birthYear} onChange={set("birthYear")} error={errors.birth_year} />
        {formError && (
          <p role="alert" className="text-sm font-semibold">
            ⚠ {formError}
          </p>
        )}
        <button type="submit" disabled={busy} className="min-h-12 w-full rounded-lg bg-night font-bold text-lime disabled:opacity-50">
          {busy ? "가입 중…" : "가입하기"}
        </button>
      </form>
      <p className="mt-4 text-sm text-muted">
        이미 계정이 있나요?{" "}
        <Link to="/login" className="font-bold text-night underline">
          로그인
        </Link>
      </p>
    </main>
  );
}
