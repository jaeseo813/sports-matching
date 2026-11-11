import { useState, type FormEvent } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import Field from "../components/Field";
import { ApiError } from "../lib/api/client";
import { useAuth } from "../lib/auth";

export default function Login() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const from = (useLocation().state as { from?: string } | null)?.from ?? "/dashboard";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to={from} replace />;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "서버에 연결할 수 없어요");
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="mx-auto max-w-sm px-4 py-12">
      <h1 className="text-2xl font-black">로그인</h1>
      <form onSubmit={submit} className="mt-6 space-y-4">
        <Field label="이메일" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        <Field label="비밀번호" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
        {error && (
          <p role="alert" className="text-sm font-semibold">
            ⚠ {error}
          </p>
        )}
        <button type="submit" disabled={busy} className="min-h-12 w-full rounded-lg bg-night font-bold text-lime disabled:opacity-50">
          {busy ? "로그인 중…" : "로그인"}
        </button>
      </form>
      <p className="mt-4 text-sm text-muted">
        계정이 없나요?{" "}
        <Link to="/signup" className="font-bold text-night underline">
          가입하기
        </Link>
      </p>
    </main>
  );
}
