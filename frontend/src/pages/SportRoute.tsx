import { Navigate, useParams } from "react-router-dom";
import { sports } from "../sports/registry";

export default function SportRoute() {
  const { sportId } = useParams();
  const sport = sports.find((s) => s.id === sportId);
  if (!sport) return <Navigate to="/matches" replace />;
  return <sport.Page />;
}
