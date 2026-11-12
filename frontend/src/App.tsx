import { Route, Routes } from "react-router-dom";
import AppLayout from "./components/AppLayout";
import RequireAuth from "./components/RequireAuth";
import Dashboard from "./pages/Dashboard";
import Home from "./pages/Home";
import Login from "./pages/Login";
import MatchDetail from "./pages/MatchDetail";
import MatchNew from "./pages/MatchNew";
import Matches from "./pages/Matches";
import MyPage from "./pages/MyPage";
import Onboarding from "./pages/Onboarding";
import Signup from "./pages/Signup";
import SportRoute from "./pages/SportRoute";

export default function App() {
  return (
    <Routes>
      <Route index element={<Home />} />
      <Route path="login" element={<Login />} />
      <Route path="signup" element={<Signup />} />
      {/* 아래는 로그인한 사용자만 */}
      <Route element={<RequireAuth />}>
        <Route element={<AppLayout />}>
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="onboarding" element={<Onboarding />} />
          <Route path="matches" element={<Matches />} />
          <Route path="matches/new" element={<MatchNew />} />
          <Route path="matches/:id" element={<MatchDetail />} />
          <Route path="sports/:sportId" element={<SportRoute />} />
          <Route path="me" element={<MyPage />} />
        </Route>
      </Route>
    </Routes>
  );
}
