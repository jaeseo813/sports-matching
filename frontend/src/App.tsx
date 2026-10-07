import { Route, Routes } from "react-router-dom";
import AppLayout from "./components/AppLayout";
import Dashboard from "./pages/Dashboard";
import Home from "./pages/Home";
import Matches from "./pages/Matches";
import SportRoute from "./pages/SportRoute";
import MyPage from "./pages/MyPage";

export default function App() {
  return (
    <Routes>
      <Route index element={<Home />} />
      <Route element={<AppLayout />}>
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="matches" element={<Matches />} />
        <Route path="sports/:sportId" element={<SportRoute />} />
        <Route path="me" element={<MyPage />} />
      </Route>
    </Routes>
  );
}
