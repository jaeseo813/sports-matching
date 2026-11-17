// 챗봇 (AGENTS.md 6절). 찾기·설명·티어 안내·규칙 FAQ만 하고, 신청은 버튼으로 화면에 넘긴다.
// 챗봇이 꺼져 있거나 실패해도 매치 목록 필터로 같은 일을 할 수 있게 안내한다.
// - SportChat: 종목 페이지 안에 붙는 대화창 (규칙 FAQ 자리). 추천 질문은 그 종목의 FAQ 질문
// - ChatButton: 그 밖의 화면에 떠 있는 "챗봇에게 묻기" 버튼과 창
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { MessageCircle, Send, X } from "lucide-react";
import { ApiError, postStream } from "../lib/api/client";
import { useSportRules } from "../lib/sports";

type ChatEvent =
  | { type: "status"; text: string }
  | { type: "action"; label: string; href: string }
  | { type: "message"; text: string }
  | { type: "error"; code: string; message: string }
  | { type: "done" };

interface Turn {
  role: "user" | "assistant";
  text: string;
  actions?: { label: string; href: string }[];
  error?: boolean; // 오류 안내는 대화 이력으로 서버에 보내지 않는다
}

const MAX_INPUT = 500; // 백엔드 chat_guard.MAX_INPUT_CHARS와 같게
const MAX_HISTORY = 20;
const GENERAL = ["가까운 매치 찾아줘", "실력 단계는 어떻게 나뉘어?"];

// 굵게(**)와 줄 앞 "- " 목록만 지원한다. 텍스트는 React가 이스케이프하므로 HTML은 그대로 글자로 나온다. 링크는 만들지 않는다
function Rich({ text }: { text: string }) {
  return (
    <>
      {text.split("\n").map((line, i) => {
        const bullet = /^\s*[-*] /.test(line);
        const body = bullet ? line.replace(/^\s*[-*] /, "") : line;
        const parts: ReactNode[] = body.split(/\*\*(.+?)\*\*/g).map((p, j) => (j % 2 ? <strong key={j}>{p}</strong> : p));
        if (!body.trim()) return <br key={i} />;
        return bullet ? (
          <p key={i} className="pl-3 -indent-3">
            · {parts}
          </p>
        ) : (
          <p key={i}>{parts}</p>
        );
      })}
    </>
  );
}

// 서버가 만든 앱 안 경로만 버튼으로 연다
const safeHref = (href: string) => href.startsWith("/") && !href.startsWith("//");

// 대화 목록 + 입력창. sport가 null이면 특정 종목이 아닌 화면에서 묻는 것
function Conversation({ sport, suggestions, autoFocus }: { sport: string | null; suggestions: string[]; autoFocus: boolean }) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // 대화창 안에서만 아래로 내린다 (페이지 전체가 챗봇 쪽으로 튀지 않게)
  useEffect(() => {
    const list = listRef.current;
    if (list) list.scrollTop = list.scrollHeight;
  }, [turns, status]);
  useEffect(() => {
    if (autoFocus) inputRef.current?.focus();
  }, [autoFocus]);

  const ask = async (text: string) => {
    const question = text.trim();
    if (!question || busy) return;
    // 띄운 버튼도 이력에 적어 둔다: "그 매치 몇 명 남았어?" 같은 후속 질문에서 챗봇이 매치 번호를 알 수 있게
    const history = turns
      .filter((t) => !t.error)
      .map(({ role, text: content, actions }) => ({ role, content: content + (actions ?? []).map((a) => `\n[버튼: ${a.label} ${a.href}]`).join("") }));
    const messages = [...history, { role: "user" as const, content: question }].slice(-MAX_HISTORY);
    setTurns((prev) => [...prev, { role: "user", text: question }]);
    setInput("");
    setBusy(true);
    setStatus("생각하고 있어요");

    const reply: Turn = { role: "assistant", text: "", actions: [] };
    try {
      await postStream<ChatEvent>("/chat", { sport, messages }, (e) => {
        if (e.type === "status") setStatus(e.text);
        else if (e.type === "action" && safeHref(e.href)) reply.actions = [...(reply.actions ?? []), { label: e.label, href: e.href }];
        else if (e.type === "message") reply.text = e.text;
        else if (e.type === "error") {
          reply.text = e.message;
          reply.error = true;
        }
      });
    } catch (e) {
      reply.error = true;
      reply.text =
        e instanceof ApiError && e.status === 429
          ? "질문이 너무 많아요. 잠시 뒤에 다시 물어봐 주세요."
          : e instanceof ApiError && e.status !== 0
            ? e.message
            : "지금은 챗봇이 응답하지 못해요. 매치 목록의 필터로 찾아 주세요.";
    } finally {
      setTurns((prev) => [...prev, reply]);
      setStatus(null);
      setBusy(false);
    }
  };

  const submit = (e: FormEvent) => {
    e.preventDefault();
    void ask(input);
  };

  return (
    <>
      <div ref={listRef} className="min-h-0 flex-1 space-y-3 overflow-y-auto p-4 text-sm" aria-live="polite">
        {turns.length === 0 && (
          <div>
            <p className="text-muted">눌러서 바로 물어보거나, 아래에 직접 적어 주세요.</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {suggestions.map((s) => (
                <button key={s} type="button" disabled={busy} onClick={() => void ask(s)} className="min-h-11 rounded-full border border-edge px-3 py-2 text-left font-semibold">
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {turns.map((t, i) =>
          t.role === "user" ? (
            <p key={i} className="ml-8 whitespace-pre-wrap rounded-lg bg-night px-3 py-2 text-lime">
              {t.text}
            </p>
          ) : (
            <div key={i} className={`mr-4 space-y-1 rounded-lg px-3 py-2 ${t.error ? "border border-edge" : "bg-cream"}`}>
              {t.error && <p className="font-bold">⚠ 안내</p>}
              <Rich text={t.text} />
              {t.error && (
                <Link to="/matches" className="mt-1 inline-flex min-h-11 items-center font-bold underline">
                  매치 목록에서 찾기
                </Link>
              )}
              {t.actions && t.actions.length > 0 && (
                <div className="flex flex-wrap gap-2 pt-1">
                  {t.actions.map((a) => (
                    <Link key={a.href} to={a.href} className="flex min-h-11 items-center rounded-lg bg-lime px-4 font-bold">
                      {a.label}
                    </Link>
                  ))}
                </div>
              )}
            </div>
          ),
        )}
        {status && (
          <p role="status" className="text-muted">
            {status}…
          </p>
        )}
      </div>

      <form onSubmit={submit} className="border-t border-edge p-3">
        <label htmlFor={`chat-input-${sport ?? "all"}`} className="sr-only">
          챗봇에게 보낼 질문
        </label>
        <div className="flex items-end gap-2">
          <textarea
            id={`chat-input-${sport ?? "all"}`}
            ref={inputRef}
            rows={2}
            maxLength={MAX_INPUT}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault();
                void ask(input);
              }
            }}
            placeholder="예: 토요일 저녁에 가까운 매치 있어?"
            className="min-h-11 flex-1 resize-none rounded-lg border border-edge px-3 py-2"
          />
          <button type="submit" disabled={busy || !input.trim()} aria-label="보내기" className="flex size-11 items-center justify-center rounded-lg bg-night text-lime disabled:opacity-50">
            <Send size={18} aria-hidden="true" />
          </button>
        </div>
        <p className="mt-1 text-right text-xs text-muted">
          {input.length}/{MAX_INPUT}
        </p>
      </form>
    </>
  );
}

// 종목 페이지의 규칙 FAQ 자리에 들어가는 대화창. 추천 질문 = 그 종목의 규칙 FAQ 질문(서버 faq.py)
export function SportChat({ sport }: { sport: string }) {
  const rules = useSportRules()?.find((r) => r.id === sport);
  return (
    // 데스크톱에서는 옆 칸(티어 설명)과 높이를 맞춘다: 대화창이 칸 높이만큼 늘어나고 안에서 스크롤한다
    <section aria-labelledby={`chat-${sport}`} className="flex flex-col">
      <h2 id={`chat-${sport}`} className="text-xl font-extrabold">
        {rules ? `${rules.name} 규칙·매치 질문` : "규칙·매치 질문"}
      </h2>
      <p className="mt-1 text-sm text-muted">규칙이나 나에게 맞는 매치를 물어보세요. 방장 규칙이 우선이에요.</p>
      <div className="mt-3 flex h-[28rem] flex-col rounded-xl border border-edge bg-white md:h-auto md:min-h-80 md:flex-1 md:[contain:size]">
        <Conversation sport={sport} suggestions={[...(rules?.faq ?? []), ...GENERAL]} autoFocus={false} />
      </div>
    </section>
  );
}

// 종목 페이지가 아닌 화면에 떠 있는 버튼과 창. 닫아도 대화는 남는다(화면을 옮겨도 레이아웃에 붙어 있다)
export function ChatButton() {
  const [open, setOpen] = useState(false);
  return (
    <>
      {!open && (
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="fixed bottom-24 right-4 z-30 flex min-h-12 items-center gap-2 rounded-full bg-night px-5 font-bold text-lime shadow-lg shadow-night/20 md:bottom-6"
        >
          <MessageCircle size={20} aria-hidden="true" /> 챗봇에게 묻기
        </button>
      )}
      <section
        role="dialog"
        aria-label="매치 도우미 챗봇"
        hidden={!open}
        className={`fixed inset-x-3 bottom-24 top-20 z-30 flex-col rounded-xl ${open ? "flex" : ""} border border-edge bg-white shadow-xl shadow-night/20 md:inset-x-auto md:bottom-6 md:right-6 md:top-auto md:h-[min(600px,80vh)] md:w-96`}
    >
      <header className="flex items-center justify-between border-b border-edge px-4 py-2">
        <div>
          <h2 className="font-extrabold">매치 도우미</h2>
          <p className="text-xs text-muted">매치 찾기·추천 설명·실력 단계·규칙을 물어보세요</p>
        </div>
        <button type="button" onClick={() => setOpen(false)} aria-label="챗봇 닫기" className="flex size-11 items-center justify-center rounded-lg">
          <X size={20} aria-hidden="true" />
        </button>
      </header>
        <Conversation sport={null} suggestions={GENERAL} autoFocus={open} />
      </section>
    </>
  );
}
