
import { useEffect, useState } from "react";
import MatchCard from "./MatchCard";
import { sports } from "../sports/registry";

interface Match {
  id: number;
  title: string;
  venue_name: string;
  starts_at: string;
  joined: number;
  capacity: number;
  tier_min: number;
  tier_max: number;
}

interface MatchListProps {
  sport: string;
}

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export default function MatchList({ sport }: MatchListProps) {
  const [matches, setMatches] = useState<Match[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const sportInfo = sports.find((item) => item.id === sport);

  useEffect(() => {
    const controller = new AbortController();

    async function fetchMatches() {
      try {
        setLoading(true);
        setError("");

        const response = await fetch(
          `${API_BASE_URL}/matches?sport=${encodeURIComponent(sport)}`,
          { signal: controller.signal }
        );

        if (!response.ok) {
          if (response.status === 401 || response.status === 403) {
            throw new Error("매치를 확인하려면 로그인이 필요합니다.");
          }
          throw new Error("매치 목록을 불러오지 못했습니다.");
        }

        const data: Match[] = await response.json();
        setMatches(data);
      } catch (err) {
        if (err instanceof Error && err.name === "AbortError") return;
        setError(
          err instanceof Error ? err.message : "알 수 없는 오류가 발생했습니다."
        );
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    fetchMatches();

    return () => controller.abort();
  }, [sport]);

  if (!sportInfo) {
    return <p>존재하지 않는 종목입니다.</p>;
  }

  if (loading) {
    return <p className="py-8 text-center text-muted">매치를 불러오는 중...</p>;
  }

  if (error) {
    return <p className="py-8 text-center text-muted">{error}</p>;
  }

  if (matches.length === 0) {
    return <p className="py-8 text-center text-muted">모집 중인 매치가 없습니다.</p>;
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {matches.map((match) => (
        <MatchCard
          key={match.id}
          sport={sportInfo}
          title={match.title}
          venue={match.venue_name}
          when={new Date(match.starts_at).toLocaleString("ko-KR", {
            month: "long",
            day: "numeric",
            weekday: "short",
            hour: "2-digit",
            minute: "2-digit",
          })}
          joined={match.joined}
          capacity={match.capacity}
          tierRange={[match.tier_min, match.tier_max]}
        />
      ))}
    </div>
  );
}
