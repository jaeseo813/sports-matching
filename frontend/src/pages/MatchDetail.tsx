import { useState, type ReactNode } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Check, X } from "lucide-react";
import { ApiError, api, post } from "../lib/api/client";
import type { MatchOut, ParticipationOut } from "../lib/api/types";
import { formatWhen } from "../lib/format";
import { genderPolicyLabel, matchStatusLabel, myStatusLabel, teamSizeLabel } from "../lib/labels";
import { useSportRules } from "../lib/sports";
import { useApi } from "../lib/useApi";
import { sports } from "../sports/registry";

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex gap-3 py-2">
      <dt className="w-20 shrink-0 text-muted">{label}</dt>
      <dd className="flex-1">{children}</dd>
    </div>
  );
}

// 주최자 전용: 신청자 수락·거절
function Applicants({ matchId, onChange }: { matchId: number; onChange: () => void }) {
  const { data, error, reload } = useApi<ParticipationOut[]>(`/matches/${matchId}/participations`);
  const [busy, setBusy] = useState<number | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const decide = async (pid: number, accept: boolean) => {
    setBusy(pid);
    setMsg(null);
    try {
      await post(`/matches/${matchId}/participations/${pid}/${accept ? "accept" : "reject"}`, {});
      reload();
      onChange();
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : "처리하지 못했어요");
    } finally {
      setBusy(null);
    }
  };

  if (error) return <p role="alert" className="text-sm">⚠ {error.message}</p>;
  const others = (data ?? []).filter((p) => p.status !== "canceled");
  return (
    <section aria-labelledby="applicants" className="rounded-xl border border-edge bg-white p-5">
      <h2 id="applicants" className="text-lg font-extrabold">참가자·신청자</h2>
      {msg && <p role="alert" className="mt-2 text-sm font-semibold">⚠ {msg}</p>}
      <ul className="mt-3 divide-y divide-edge">
        {others.map((p) => (
          <li key={p.id} className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm">
            <span className="font-bold">{p.nickname}</span>
            {p.status === "applied" ? (
              <span className="flex gap-2">
                <button type="button" disabled={busy === p.id} onClick={() => decide(p.id, true)} className="flex min-h-11 items-center gap-1 rounded-lg bg-lime px-4 font-bold disabled:opacity-50">
                  <Check size={16} aria-hidden="true" /> 수락
                </button>
                <button type="button" disabled={busy === p.id} onClick={() => decide(p.id, false)} className="flex min-h-11 items-center gap-1 rounded-lg border border-edge px-4 font-bold disabled:opacity-50">
                  <X size={16} aria-hidden="true" /> 거절
                </button>
              </span>
            ) : (
              <span className="text-muted">{myStatusLabel[p.status]}</span>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}

export default function MatchDetail() {
  const { id } = useParams();
  const { data: m, error, reload } = useApi<MatchOut>(`/matches/${Number(id)}`);
  const rules = useSportRules();
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  if (error) {
    return (
      <section className="space-y-3">
        <p role="alert" className="rounded-xl border border-edge bg-white p-5 text-sm">⚠ {error.message}</p>
        <Link to="/matches" className="font-bold underline">매치 목록으로</Link>
      </section>
    );
  }
  if (!m) return <p role="status" className="text-sm text-muted">매치를 불러오고 있어요…</p>;

  const sport = sports.find((s) => s.id === m.sport);
  const tierLabels = rules?.find((r) => r.id === m.sport)?.tier_labels ?? {};
  const active = m.status === "open" || m.status === "full" || m.status === "confirmed";
  const applied = m.my_status === "applied" || m.my_status === "accepted";

  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setMsg(null);
    try {
      await fn();
      reload();
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : "처리하지 못했어요");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <Link to="/matches" className="inline-flex min-h-11 items-center gap-1 text-sm font-bold text-muted">
        <ArrowLeft size={16} aria-hidden="true" /> 매치 목록
      </Link>
      <section className="rounded-xl border border-edge bg-white p-6">
        <div className="flex flex-wrap items-center gap-2 text-xs font-bold">
          {sport && (
            <span className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1 ${sport.bg} ${sport.fg}`}>
              <sport.icon size={14} aria-hidden="true" />
              {sport.name}
            </span>
          )}
          <span className="rounded-lg bg-edge px-3 py-1">{matchStatusLabel[m.status]}</span>
          {m.is_host ? (
            <span className="rounded-lg bg-night px-3 py-1 text-lime">내가 연 매치</span>
          ) : (
            m.my_status && <span className="rounded-lg bg-lime px-3 py-1">{myStatusLabel[m.my_status]}</span>
          )}
        </div>
        <h1 className="mt-3 text-2xl font-black">{m.title}</h1>
        <dl className="mt-4 divide-y divide-edge text-sm">
          <Row label="장소">{m.venue_name}</Row>
          <Row label="시간">
            {formatWhen(m.starts_at)} · {m.duration_min}분
          </Row>
          <Row label="형식">
            {teamSizeLabel(m.sport, m.team_size)} · {m.joined}/{m.capacity}명 (최소 {m.min_players}명)
          </Row>
          <Row label="참가 단계">
            {Array.from({ length: m.tier_max - m.tier_min + 1 }, (_, i) => m.tier_min + i).map((t) => (
              <span key={t} className="block">
                {t}단계{tierLabels[String(t)] ? ` · ${tierLabels[String(t)]}` : ""}
              </span>
            ))}
          </Row>
          <Row label="성별">{genderPolicyLabel[m.gender_policy]}</Row>
          <Row label="주최자">{m.host_nickname}</Row>
        </dl>
        {m.description && <p className="mt-4 whitespace-pre-line rounded-lg bg-cream p-3 text-sm">{m.description}</p>}

        {msg && <p role="alert" className="mt-4 text-sm font-semibold">⚠ {msg}</p>}

        {m.is_host ? (
          active && (
            <button
              type="button"
              disabled={busy}
              onClick={() => confirm("매치를 취소할까요? 참가자 모두에게 취소돼요.") && act(() => post(`/matches/${m.id}/cancel`, {}))}
              className="mt-5 min-h-12 w-full rounded-lg border border-edge font-bold disabled:opacity-50"
            >
              매치 취소
            </button>
          )
        ) : applied ? (
          active && (
            <button type="button" disabled={busy} onClick={() => act(() => api(`/matches/${m.id}/apply`, { method: "DELETE" }))} className="mt-5 min-h-12 w-full rounded-lg border border-edge font-bold disabled:opacity-50">
              신청 취소
            </button>
          )
        ) : (
          <button
            type="button"
            disabled={busy || m.status !== "open" || m.my_status === "rejected"}
            onClick={() => act(() => post(`/matches/${m.id}/apply`, {}))}
            className="mt-5 min-h-12 w-full rounded-lg bg-night font-bold text-lime disabled:opacity-50"
          >
            {m.status !== "open" ? `신청할 수 없어요 (${matchStatusLabel[m.status]})` : m.my_status === "rejected" ? "거절된 매치예요" : "신청하기"}
          </button>
        )}
        {!m.is_host && m.my_status === "applied" && <p className="mt-2 text-center text-sm text-muted">주최자가 수락하면 참가가 확정돼요.</p>}
      </section>

      {m.is_host && <Applicants matchId={m.id} onChange={reload} />}
    </div>
  );
}
