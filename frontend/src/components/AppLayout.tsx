import { Link, NavLink, Outlet } from "react-router-dom";
import { CalendarDays, LayoutDashboard, User } from "lucide-react";
import { useAuth } from "../lib/auth";

const tabs = [
  { to: "/dashboard", label: "대시보드", icon: LayoutDashboard },
  { to: "/matches", label: "매치", icon: CalendarDays },
  { to: "/me", label: "내 정보", icon: User },
];

// 데스크톱: 상단 내비게이션 / 모바일: 하단 탭바
export default function AppLayout() {
  const { user, loading, logout } = useAuth();
  return (
    <div className="min-h-dvh">
      <header className="sticky top-0 z-20 border-b border-edge bg-white/90 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4">
          <Link to="/" className="text-xl font-black tracking-tight">
            Team<span className="rounded-md bg-lime px-1">Up</span>
          </Link>
          <nav aria-label="주 메뉴" className="hidden gap-1 md:flex">
            {tabs.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `flex min-h-11 items-center rounded-lg px-5 text-sm font-bold ${
                    isActive ? "bg-lime" : "text-muted hover:bg-edge"
                  }`
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>
          {!loading &&
            (user ? (
              <div className="flex items-center gap-3 text-sm">
                <span className="hidden font-bold sm:inline">{user.nickname}</span>
                <button type="button" onClick={() => void logout()} className="min-h-11 rounded-lg border border-edge px-4 font-bold hover:bg-edge">
                  로그아웃
                </button>
              </div>
            ) : (
              <Link to="/login" className="flex min-h-11 items-center rounded-lg bg-night px-5 text-sm font-bold text-lime hover:opacity-90">
                로그인
              </Link>
            ))}
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-10 px-4 pb-28 pt-6 md:pb-12">
        <Outlet />
      </main>

      <nav
        aria-label="하단 메뉴"
        className="fixed inset-x-3 bottom-3 z-20 grid grid-cols-3 rounded-lg border border-edge bg-white p-1.5 shadow-lg shadow-night/10 md:hidden"
      >
        {tabs.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex min-h-14 flex-col items-center justify-center gap-0.5 rounded-lg text-xs font-bold ${
                isActive ? "bg-lime" : "text-muted"
              }`
            }
          >
            <Icon size={20} aria-hidden="true" />
            {label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
