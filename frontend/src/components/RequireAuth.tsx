import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../lib/auth";

// 로그인한 사용자만 들어갈 수 있는 구간. 비로그인이면 로그인 화면으로 보내고, 로그인 후 원래 주소로 돌아온다
export default function RequireAuth() {
  const { user, loading, signedOut } = useAuth();
  const location = useLocation();
  if (loading) {
    return (
      <p role="status" className="p-8 text-center text-sm text-muted">
        로그인 정보를 확인하고 있어요…
      </p>
    );
  }
  if (!user && signedOut) return <Navigate to="/" replace />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  return <Outlet />;
}
