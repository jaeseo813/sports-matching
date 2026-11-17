// 매치 상세 아래쪽의 경기 진행: 확정 → 팀 → (경기는 앱 밖에서) → 종료 → 출석·상호 평가 → 레이팅 반영
import { useState, type ReactNode } from "react";
import { ApiError, api, post } from "../lib/api/client";
import type { MatchOut, ParticipationOut, RateOut, ReviewTargetOut, TeamsOut, Verdict } from "../lib/api/types";
import { useSportRules } from "../lib/sports";
import { useApi } from "../lib/useApi";

// 버튼 하나의 처리 중 상태와 오류 문구
function useAction(onDone: () => void) {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const run = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setMsg(null);
    try {
      await fn();
      onDone();
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : "처리하지 못했어요");
    } finally {
      setBusy(false);
    }
  };
  return { busy, msg, run };
}

function Panel({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return (
    <section aria-labelledby={id} className="rounded-xl border border-edge bg-white p-5">
      <h2 id={id} className="text-lg font-extrabold">{title}</h2>
      {children}
    </section>
  );
}

function Alert({ msg }: { msg: string | null }) {
  return msg ? <p role="alert" className="mt-2 text-sm font-semibold">⚠ {msg}</p> : null;
}

const primary = "min-h-12 rounded-lg bg-night px-5 font-bold text-lime disabled:opacity-50";
const secondary = "min-h-11 rounded-lg border border-edge px-4 font-bold disabled:opacity-50";

// 주최자: 지금 단계에서 누를 다음 버튼 하나
function HostStep({ m, onChange }: { m: MatchOut; onChange: () => void }) {
  const { busy, msg, run } = useAction(onChange);
  const step =
    m.status === "open" || m.status === "full"
      ? { path: "confirm", label: "경기 확정", hint: `최소 ${m.min_players}명이 모이면 확정할 수 있어요. 확정하면 더 이상 신청을 받지 않아요.` }
      : m.status === "confirmed"
        ? { path: "complete", label: "경기 종료", hint: "경기를 마쳤으면 눌러 주세요. 종료하면 출석을 기록하고 참가자들이 서로 평가할 수 있어요." }
        : null;
  if (!step) return null;
  return (
    <Panel id="host-step" title="경기 진행">
      <p className="mt-1 text-sm text-muted">{step.hint}</p>
      <Alert msg={msg} />
      <button
        type="button"
        disabled={busy}
        onClick={() => confirm(`${step.label}할까요? 되돌릴 수 없어요.`) && run(() => post(`/matches/${m.id}/${step.path}`, {}))}
        className={`mt-3 w-full ${primary}`}
      >
        {step.label}
      </button>
    </Panel>
  );
}

// 접전도 1~5: 칸 수와 문구를 함께 보여 준다 (색만으로 구분하지 않는다)
const closenessText = ["", "한쪽으로 기울어요", "조금 기울어요", "비슷해요", "팽팽해요", "아주 팽팽해요"];

function Closeness({ level }: { level: number }) {
  return (
    <div className="mt-3 flex items-center gap-3 text-sm">
      <span className="font-bold">접전도</span>
      <span className="flex gap-1" aria-hidden="true">
        {[1, 2, 3, 4, 5].map((i) => (
          <span key={i} className={`h-3 w-6 rounded-sm ${i <= level ? "bg-night" : "bg-edge"}`} />
        ))}
      </span>
      <span>
        {level}/5 · {closenessText[level]}
      </span>
    </div>
  );
}

function Teams({ m }: { m: MatchOut }) {
  const { data, error, reload } = useApi<TeamsOut>(`/matches/${m.id}/teams`);
  const teamCount = useSportRules()?.find((r) => r.id === m.sport)?.team_count ?? 2;
  const [draft, setDraft] = useState<Record<number, number> | null>(null); // 수동 조정 중: user_id → 팀 번호
  const { busy, msg, run } = useAction(() => {
    setDraft(null);
    reload();
  });
  const editable = m.is_host && (m.status === "full" || m.status === "confirmed");
  const notYet = error?.code === "TEAMS_NOT_FOUND";

  const startEdit = () => {
    if (!data) return;
    setDraft(Object.fromEntries(data.teams.flatMap((t) => t.members.map((p) => [p.user_id, t.team_no]))));
  };
  const save = () =>
    draft &&
    run(() =>
      api(`/matches/${m.id}/teams`, {
        method: "PUT",
        body: JSON.stringify({ assignments: Object.entries(draft).map(([uid, team]) => ({ user_id: Number(uid), team_no: team })) }),
      }),
    );

  return (
    <Panel id="teams" title="팀">
      {error && !notYet && <Alert msg={error.message} />}
      {notYet && <p className="mt-2 text-sm text-muted">아직 팀이 나뉘지 않았어요.{editable ? "" : " 주최자가 나누면 여기에 보여요."}</p>}
      {data && (
        <>
          <Closeness level={data.closeness} />
          <p className="mt-1 text-xs text-muted">{data.is_manual ? "주최자가 직접 조정한 팀이에요." : "실력과 포지션을 고려해 자동으로 나눈 팀이에요."}</p>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            {data.teams.map((t) => (
              <div key={t.team_no} className="rounded-lg bg-cream p-3">
                <h3 className="font-extrabold">{t.team_no}팀</h3>
                <ul className="mt-2 space-y-2 text-sm">
                  {t.members.map((p) => (
                    <li key={p.user_id} className="flex flex-wrap items-center gap-2">
                      <span className="rounded-md bg-lime px-2 py-0.5 text-xs font-bold" aria-label={`${p.tier}단계`}>
                        {p.tier}단계
                      </span>
                      <span className="font-bold">{p.nickname}</span>
                      {p.position && <span className="text-xs text-muted">{p.position}</span>}
                      {draft && (
                        <label className="ml-auto flex items-center gap-1 text-xs">
                          <span className="sr-only">{p.nickname}의 팀</span>
                          <select
                            value={draft[p.user_id]}
                            onChange={(e) => setDraft({ ...draft, [p.user_id]: Number(e.target.value) })}
                            className="min-h-11 rounded-lg border border-edge bg-white px-2"
                          >
                            {Array.from({ length: teamCount }, (_, i) => i + 1).map((n) => (
                              <option key={n} value={n}>
                                {n}팀
                              </option>
                            ))}
                          </select>
                        </label>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </>
      )}
      <Alert msg={msg} />
      {editable && (
        <div className="mt-3 flex flex-wrap gap-2">
          {draft ? (
            <>
              <button type="button" disabled={busy} onClick={save} className={primary}>
                이대로 저장
              </button>
              <button type="button" disabled={busy} onClick={() => setDraft(null)} className={secondary}>
                취소
              </button>
            </>
          ) : (
            <>
              <button type="button" disabled={busy} onClick={() => run(() => post(`/matches/${m.id}/teams/balance`, {}))} className={primary}>
                {data ? "자동으로 다시 나누기" : "자동으로 팀 나누기"}
              </button>
              {data && (
                <button type="button" disabled={busy} onClick={startEdit} className={secondary}>
                  직접 조정
                </button>
              )}
            </>
          )}
        </div>
      )}
    </Panel>
  );
}

// 주최자: 출석 체크 (경기 종료 뒤 ~ 레이팅 반영 전)
function Attendance({ m }: { m: MatchOut }) {
  const { data, error, reload } = useApi<ParticipationOut[]>(`/matches/${m.id}/participations`);
  const [marks, setMarks] = useState<Record<number, boolean>>({});
  const [saved, setSaved] = useState(false);
  const { busy, msg, run } = useAction(() => {
    setSaved(true);
    reload();
  });
  const players = (data ?? []).filter((p) => p.status === "accepted" || p.status === "attended" || p.status === "no_show");
  const attended = (p: ParticipationOut) => marks[p.user_id] ?? p.status !== "no_show";

  const save = () =>
    run(() =>
      api(`/matches/${m.id}/attendance`, {
        method: "PUT",
        body: JSON.stringify({ attendances: players.map((p) => ({ user_id: p.user_id, attended: attended(p) })) }),
      }),
    );

  return (
    <Panel id="attendance" title="출석 체크">
      <p className="mt-1 text-sm text-muted">오지 않은 사람만 "불참"으로 바꿔 주세요. 불참은 노쇼 기록에 남아요.</p>
      {error && <Alert msg={error.message} />}
      <ul className="mt-3 divide-y divide-edge">
        {players.map((p) => (
          <li key={p.user_id} className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm">
            <span className="font-bold">{p.nickname}</span>
            <span className="flex gap-2" role="group" aria-label={`${p.nickname} 출석`}>
              {[true, false].map((value) => (
                <button
                  key={String(value)}
                  type="button"
                  aria-pressed={attended(p) === value}
                  onClick={() => {
                    setSaved(false);
                    setMarks({ ...marks, [p.user_id]: value });
                  }}
                  className={`min-h-11 rounded-lg px-4 font-bold ${attended(p) === value ? "bg-night text-lime" : "border border-edge"}`}
                >
                  {attended(p) === value ? "✓ " : ""}
                  {value ? "출석" : "불참"}
                </button>
              ))}
            </span>
          </li>
        ))}
      </ul>
      <Alert msg={msg} />
      {saved && !msg && <p role="status" className="mt-2 text-sm">출석을 저장했어요.</p>}
      <button type="button" disabled={busy || players.length === 0} onClick={save} className={`mt-3 w-full ${primary}`}>
        출석 저장
      </button>
    </Panel>
  );
}

// "상대가 나보다 어떤가" (백엔드 Verdict와 같은 뜻)
const verdictLabel: Record<Verdict, string> = { better: "나보다 잘해요", similar: "비슷해요", worse: "나보다 아쉬워요" };

function ReviewRow({ matchId, target, onDone }: { matchId: number; target: ReviewTargetOut; onDone: () => void }) {
  const [verdict, setVerdict] = useState<Verdict | null>(null);
  const [mannerFlag, setMannerFlag] = useState(false);
  const { busy, msg, run } = useAction(onDone);

  if (target.reviewed) {
    return (
      <li className="flex items-center justify-between py-3 text-sm">
        <span className="font-bold">{target.nickname}</span>
        <span className="text-muted">✓ 평가 완료</span>
      </li>
    );
  }
  return (
    <li className="py-3 text-sm">
      <p className="font-bold">{target.nickname}</p>
      <div className="mt-2 flex flex-wrap gap-2" role="group" aria-label={`${target.nickname} 실력 평가`}>
        {(Object.keys(verdictLabel) as Verdict[]).map((v) => (
          <button
            key={v}
            type="button"
            aria-pressed={verdict === v}
            onClick={() => setVerdict(v)}
            className={`min-h-11 rounded-lg px-4 font-bold ${verdict === v ? "bg-night text-lime" : "border border-edge"}`}
          >
            {verdict === v ? "✓ " : ""}
            {verdictLabel[v]}
          </button>
        ))}
      </div>
      <label className="mt-2 flex min-h-11 items-center gap-2">
        <input type="checkbox" checked={mannerFlag} onChange={(e) => setMannerFlag(e.target.checked)} className="size-5" />
        매너가 좋지 않았어요 (실력 평가와 따로 반영돼요)
      </label>
      <Alert msg={msg} />
      <button
        type="button"
        disabled={busy || !verdict}
        onClick={() => run(() => post(`/matches/${matchId}/reviews`, { reviewee_id: target.user_id, verdict, manner_flag: mannerFlag }))}
        className={`mt-1 ${secondary}`}
      >
        평가 보내기
      </button>
    </li>
  );
}

function Reviews({ m }: { m: MatchOut }) {
  const { data, error, reload } = useApi<ReviewTargetOut[]>(`/matches/${m.id}/reviews/targets`);
  const left = data?.filter((t) => !t.reviewed).length ?? 0;
  return (
    <Panel id="reviews" title="함께 뛴 사람 평가">
      <p className="mt-1 text-sm text-muted">평가는 상대에게 공개되지 않고, 티어를 맞추는 데만 쓰여요. {data && (left > 0 ? `${left}명 남았어요.` : "모두 평가했어요.")}</p>
      {error && <Alert msg={error.message} />}
      <ul className="mt-2 divide-y divide-edge">
        {data?.map((t) => <ReviewRow key={t.user_id} matchId={m.id} target={t} onDone={reload} />)}
      </ul>
    </Panel>
  );
}

// 주최자: 모인 평가를 레이팅에 반영 (한 번만)
function Rate({ m, onChange }: { m: MatchOut; onChange: () => void }) {
  const [result, setResult] = useState<RateOut | null>(null);
  const { busy, msg, run } = useAction(onChange);
  return (
    <Panel id="rate" title="티어 반영">
      <p className="mt-1 text-sm text-muted">참가자 절반 이상이 평가하면 반영할 수 있어요. 반영한 뒤에는 출석과 평가를 바꿀 수 없어요.</p>
      <Alert msg={msg} />
      {result && !result.applied && <p role="status" className="mt-2 text-sm font-semibold">아직 평가가 부족해 반영을 미뤘어요. 평가가 더 모이면 다시 눌러 주세요.</p>}
      <button
        type="button"
        disabled={busy}
        onClick={() => confirm("지금까지 모인 평가로 티어를 반영할까요?") && run(async () => setResult(await post<RateOut>(`/matches/${m.id}/rate`, {})))}
        className={`mt-3 w-full ${primary}`}
      >
        티어 반영하기
      </button>
    </Panel>
  );
}

export default function MatchProgress({ m, onChange }: { m: MatchOut; onChange: () => void }) {
  const player = m.is_host || m.my_status === "accepted" || m.my_status === "attended";
  if (!player || m.status === "canceled") return null;
  if (m.status === "open") return m.is_host ? <HostStep m={m} onChange={onChange} /> : null; // 팀은 정원이 찬 뒤부터
  return (
    <>
      {m.is_host && <HostStep m={m} onChange={onChange} />}
      <Teams m={m} />
      {m.is_host && m.status === "completed" && !m.rated && <Attendance m={m} />}
      {m.status === "completed" && !m.rated && <Reviews m={m} />}
      {m.is_host && m.status === "completed" && !m.rated && <Rate m={m} onChange={onChange} />}
      {m.rated && (
        <p role="status" className="rounded-xl border border-edge bg-white p-5 text-sm">
          티어 반영이 끝난 경기예요. 내 티어 추이는 내 정보에서 볼 수 있어요.
        </p>
      )}
    </>
  );
}
