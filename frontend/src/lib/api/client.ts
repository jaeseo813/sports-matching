// API 클라이언트. access 토큰 하나를 localStorage에 둔다 (refresh 없음, 만료되면 다시 로그인).

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";
const TOKEN_KEY = "teamup.token";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly fields: Record<string, string> = {},
  ) {
    super(message);
  }
}

export interface Tokens {
  access_token: string;
}

function readStoredToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

let accessToken: string | null = readStoredToken();

export const hasToken = () => accessToken !== null;

export function setToken(token: string | null) {
  accessToken = token;
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    // 저장소를 못 쓰는 환경(사생활 보호 모드 등)에서는 새로고침 시 로그아웃된다
  }
}

// 서버 오류 형태: {"detail": {"code", "message"}} 또는 검증 실패 시 {"detail": [{loc, msg}]}
async function toError(res: Response): Promise<ApiError> {
  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    // JSON이 아닌 응답
  }
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (Array.isArray(detail)) {
    const fields: Record<string, string> = {};
    for (const d of detail as { loc?: unknown[] }[]) {
      const name = String(d.loc?.[d.loc.length - 1] ?? "");
      // 서버 메시지는 영어 정규식 원문이라 그대로 보여주지 않는다. 제약은 라벨에 적는다
      if (name && !fields[name]) fields[name] = "값을 확인해 주세요";
    }
    return new ApiError(res.status, "VALIDATION_ERROR", "입력값을 확인해 주세요", fields);
  }
  if (detail && typeof detail === "object") {
    const { code, message } = detail as { code?: string; message?: string };
    return new ApiError(res.status, code ?? "ERROR", message ?? "요청에 실패했어요");
  }
  return new ApiError(res.status, "ERROR", "요청에 실패했어요");
}

async function send(path: string, init: RequestInit, auth: boolean): Promise<Response> {
  const headers = new Headers(init.headers);
  if (init.body) headers.set("Content-Type", "application/json");
  if (auth && accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  return fetch(`${BASE_URL}${path}`, { ...init, headers });
}

export async function api<T>(path: string, init: RequestInit = {}, options: { auth?: boolean } = {}): Promise<T> {
  const auth = options.auth ?? true;
  const res = await send(path, init, auth);
  if (res.status === 401 && auth) setToken(null); // 만료·위조 토큰은 버리고 다시 로그인하게 한다
  if (!res.ok) throw await toError(res);
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

export const post = <T>(path: string, body: unknown, options?: { auth?: boolean }) =>
  api<T>(path, { method: "POST", body: JSON.stringify(body) }, options);
