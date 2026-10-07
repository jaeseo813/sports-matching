import { MapPin, Users } from "lucide-react";
import type { Sport } from "../sports/types";

export interface MatchCardProps {
  sport: Sport;
  title: string;
  venue: string;
  when: string;
  distance?: string;
  joined?: number;
  capacity?: number;
  reasons?: string[];
}

export default function MatchCard({ sport, title, venue, when, distance, joined, capacity, reasons }: MatchCardProps) {
  return (
    <article className="rounded-xl border border-edge bg-white p-5">
      <div className="flex items-center justify-between">
        <span className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1 text-xs font-bold ${sport.bg} ${sport.fg}`}>
          <sport.icon size={14} aria-hidden="true" />
          {sport.name}
        </span>
        {joined !== undefined && capacity !== undefined && (
          <span className="inline-flex items-center gap-1 text-xs font-medium text-muted">
            <Users size={14} aria-hidden="true" />
            {joined}/{capacity}명
          </span>
        )}
      </div>
      <h3 className="mt-4 text-lg font-bold">{title}</h3>
      <p className="mt-1 flex items-center gap-1 text-sm text-muted">
        <MapPin size={14} aria-hidden="true" />
        {venue}
        {distance ? `, ${distance}` : ""}
      </p>
      <p className="text-sm text-muted">{when}</p>
      {reasons && (
        <ul className="mt-3 flex flex-wrap gap-1.5">
          {reasons.map((r) => (
            <li key={r} className="rounded-lg bg-lime px-2.5 py-1 text-xs font-semibold">
              {r}
            </li>
          ))}
        </ul>
      )}
    </article>
  );
}
