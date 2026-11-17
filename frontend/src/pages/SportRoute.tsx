import { Navigate, useParams } from "react-router-dom";
import { sports } from "../sports/registry";

// 종목 페이지는 담당자 폴더(src/sports/<id>)가 그린다. 챗봇은 각 페이지의 규칙 FAQ 자리에 SportChat으로 들어간다
export default function SportRoute() {
  const { sportId } = useParams();
  const sport = sports.find((s) => s.id === sportId);
  if (!sport) return <Navigate to="/matches" replace />;
  return <sport.Page />;
}
