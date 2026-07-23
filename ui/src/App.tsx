import { useEffect, useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import { api } from "./api/client";
import type { Health } from "./types";
import Dashboard from "./pages/Dashboard";
import CalibrationPage from "./pages/CalibrationPage";
import PipelinePage from "./pages/PipelinePage";

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);

  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      try {
        const h = await api.get<Health>("/api/v1/health");
        if (!cancelled) setHealth(h);
      } catch {
        if (!cancelled) setHealth(null);
      }
    };
    poll();
    const id = setInterval(poll, 20000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          PENUMBRA<span> ◗</span>
        </div>
        <nav>
          <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
            Forecast
          </NavLink>
          <NavLink to="/calibration" className={({ isActive }) => (isActive ? "active" : "")}>
            Calibration
          </NavLink>
          <NavLink to="/pipeline" className={({ isActive }) => (isActive ? "active" : "")}>
            Pipeline
          </NavLink>
        </nav>
        <div className="status">
          {health ? (
            <>
              <span className={`mode-chip ${health.data_mode}`}>{health.data_mode} data</span>
              <span>v{health.version}</span>
              <span style={{ color: "var(--ok)" }}>● online</span>
            </>
          ) : (
            <span style={{ color: "var(--storm)" }}>● backend offline</span>
          )}
        </div>
      </header>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/calibration" element={<CalibrationPage />} />
        <Route path="/pipeline" element={<PipelinePage />} />
      </Routes>
    </div>
  );
}
