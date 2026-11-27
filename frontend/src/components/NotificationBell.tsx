// 매칭 알림: 신청 수락·매치 확정. 30초마다 새로 확인하고, 열면 읽음으로 바꾼다
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bell } from "lucide-react";
import { post } from "../lib/api/client";
import type { NotificationsOut } from "../lib/api/types";
import { formatWhen } from "../lib/format";
import { useApi } from "../lib/useApi";

const text = { accepted: "신청이 수락됐어요", confirmed: "매치가 확정됐어요" } as const;

export default function NotificationBell() {
  const { data, error, reload } = useApi<NotificationsOut>("/me/notifications");
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const timer = setInterval(reload, 30_000);
    return () => clearInterval(timer);
  }, [reload]);

  const toggle = () => {
    // 닫을 때 다시 불러와, 열어 둔 동안은 "새 알림" 표시가 남아 있게 한다
    if (open) reload();
    else if (data && data.unread > 0) void post("/me/notifications/read", {}).catch(() => undefined);
    setOpen(!open);
  };

  const unread = open ? 0 : (data?.unread ?? 0);
  return (
    <div className="relative">
      <button
        type="button"
        onClick={toggle}
        aria-expanded={open}
        aria-label={unread > 0 ? `알림, 새 알림 ${unread}개` : "알림"}
        className="relative flex size-11 items-center justify-center rounded-lg border border-edge hover:bg-edge"
      >
        <Bell size={20} aria-hidden="true" />
        {unread > 0 && (
          <span aria-hidden="true" className="absolute -right-1 -top-1 min-w-5 rounded-full bg-night px-1 text-center text-xs font-bold leading-5 text-lime">
            {unread}
          </span>
        )}
      </button>
      {open && (
        <section aria-label="알림 목록" className="fixed inset-x-3 top-17 z-30 max-h-96 overflow-y-auto md:absolute md:inset-x-auto md:right-0 md:top-13 md:w-72 rounded-xl border border-edge bg-white p-2 shadow-xl shadow-night/20">
          {error && <p role="alert" className="p-3 text-sm">⚠ {error.message}</p>}
          {data && data.items.length === 0 && <p className="p-3 text-sm text-muted">아직 알림이 없어요.</p>}
          <ul>
            {data?.items.map((n) => (
              <li key={n.id}>
                <Link to={`/matches/${n.match_id}`} onClick={toggle} className="block min-h-11 rounded-lg p-3 text-sm hover:bg-cream">
                  <span className="block font-bold">
                    {!n.read && <span className="mr-1 rounded bg-lime px-1 text-xs">새 알림</span>}
                    {text[n.kind]}
                  </span>
                  <span className="block truncate">{n.match_title}</span>
                  <span className="block text-xs text-muted">{formatWhen(n.created_at)}</span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
