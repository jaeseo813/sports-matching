import { useEffect, useState } from "react";
import { api } from "./api/client";
import type { SportOut } from "./api/types";

let cache: Promise<SportOut[]> | null = null;

// 종목 규칙(팀 인원·티어 설명)은 서버 값을 쓴다. 한 번만 불러와 재사용한다
export function useSportRules(): SportOut[] | null {
  const [rules, setRules] = useState<SportOut[] | null>(null);
  useEffect(() => {
    cache ??= api<SportOut[]>("/sports").catch((e: unknown) => {
      cache = null;
      throw e;
    });
    let alive = true;
    cache.then((r) => alive && setRules(r)).catch(() => undefined);
    return () => {
      alive = false;
    };
  }, []);
  return rules;
}
