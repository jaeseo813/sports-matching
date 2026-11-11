import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "./api/client";

// GET 한 건을 불러오는 작은 훅. path가 null이면 부르지 않는다. reload()로 다시 불러온다
export function useApi<T>(path: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (path === null) return;
    let alive = true;
    setError(null);
    api<T>(path)
      .then((d) => alive && setData(d))
      .catch((e: unknown) => alive && setError(e instanceof ApiError ? e : new ApiError(0, "NETWORK", "서버에 연결할 수 없어요")));
    return () => {
      alive = false;
    };
  }, [path, tick]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { data, error, loading: path !== null && data === null && error === null, reload };
}
