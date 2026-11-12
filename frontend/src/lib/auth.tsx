import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, getStoredRefresh, post, refreshOnce, setTokens, type Tokens } from "./api/client";

export type Gender = "male" | "female" | "other";

export interface User {
  id: number;
  email: string;
  nickname: string;
  gender: Gender;
}

export interface SignupInput {
  email: string;
  password: string;
  nickname: string;
  gender: Gender;
  birth_year: number;
}

interface AuthState {
  user: User | null;
  loading: boolean; // 새로고침 직후 저장된 refresh로 세션을 복구하는 중
  signedOut: boolean; // 방금 직접 로그아웃했다 (로그인 화면이 아니라 시작 화면으로 보낸다)
  login: (email: string, password: string) => Promise<void>;
  signup: (input: SignupInput) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [signedOut, setSignedOut] = useState(false);
  const [loading, setLoading] = useState(() => getStoredRefresh() !== null);

  useEffect(() => {
    if (!loading) return;
    let alive = true;
    (async () => {
      try {
        if (await refreshOnce()) {
          const me = await api<User>("/auth/me");
          if (alive) setUser(me);
        }
      } catch {
        setTokens(null);
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [loading]);

  const login = useCallback(async (email: string, password: string) => {
    setTokens(await post<Tokens>("/auth/login", { email, password }, { auth: false }));
    setUser(await api<User>("/auth/me"));
    setSignedOut(false);
  }, []);

  const signup = useCallback(
    async (input: SignupInput) => {
      await post<User>("/auth/signup", input, { auth: false });
      await login(input.email, input.password);
    },
    [login],
  );

  const logout = useCallback(async () => {
    const refresh = getStoredRefresh();
    setTokens(null);
    setSignedOut(true);
    setUser(null);
    if (refresh) await post("/auth/logout", { refresh_token: refresh }, { auth: false }).catch(() => undefined);
  }, []);

  const value = useMemo(() => ({ user, loading, signedOut, login, signup, logout }), [user, loading, signedOut, login, signup, logout]);
  return <AuthContext value={value}>{children}</AuthContext>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth는 AuthProvider 안에서만 쓸 수 있어요");
  return ctx;
}
