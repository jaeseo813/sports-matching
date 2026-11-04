import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { sports } from "../sports/registry";

// 종목을 골라 해당 종목 페이지(/sports/:id)로 이동한다. 종목은 registry.ts에 등록된 것이 자동으로 나온다.
export default function SportPicker() {
  return (
    <ul className="grid gap-3 md:grid-cols-3">
      {sports.map(({ id, name, tagline, icon: Icon, bg, fg }) => (
        <li key={id}>
          <Link to={`/sports/${id}`} className="lift flex min-h-24 items-center gap-4 rounded-xl border border-edge bg-white p-4">
            <span className={`flex size-14 shrink-0 items-center justify-center rounded-lg ${bg} ${fg}`}>
              <Icon size={26} aria-hidden="true" />
            </span>
            <span className="flex-1">
              <span className="block text-lg font-bold">{name}</span>
              <span className="block text-sm text-muted">{tagline}</span>
            </span>
            <ArrowRight size={18} aria-hidden="true" />
          </Link>
        </li>
      ))}
    </ul>
  );
}
