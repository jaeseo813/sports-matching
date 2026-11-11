import { Route, Routes } from "react-router-dom";
import AppLayout from "./components/AppLayout";
import Dashboard from "./pages/Dashboard";
import Home from "./pages/Home";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Matches from "./pages/Matches";
import SportRoute from "./pages/SportRoute";
import MyPage from "./pages/MyPage";

export default function App() {
  return (
    <Routes>
      <Route index element={<Home />} />
      <Route path="login" element={<Login />} />
      <Route path="signup" element={<Signup />} />
      <Route element={<AppLayout />}>
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="matches" element={<Matches />} />
        <Route path="sports/:sportId" element={<SportRoute />} />
        <Route path="me" element={<MyPage />} />
      </Route>
    </Routes>
  );
}
