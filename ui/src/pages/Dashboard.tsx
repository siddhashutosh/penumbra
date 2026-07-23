import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { Briefing, DragImpact, F107Forecast, KpForecast } from "../types";
import FanChart from "../components/FanChart";
import KpStrip from "../components/KpStrip";
import DragPanel from "../components/DragPanel";

export default function Dashboard() {
  const [f107, setF107] = useState<F107Forecast | null>(null);
  const [kp, setKp] = useState<KpForecast | null>(null);
  const [drag, setDrag] = useState<DragImpact | null>(null);
  const [brief, setBrief] = useState<Briefing | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [f, k, d, b] = await Promise.all([
        api.get<F107Forecast>("/api/v1/forecast/f107"),
        api.get<KpForecast>("/api/v1/forecast/kp"),
        api.get<DragImpact>("/api/v1/forecast/drag"),
        api.get<Briefing>("/api/v1/briefing"),
      ]);
      setF107(f);
      setKp(k);
      setDrag(d);
      setBrief(b);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load forecast");
    }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 120000);
    return () => clearInterval(id);
  }, [load]);

  const issued = f107 ? new Date(f107.issued_at).toISOString().slice(0, 16).replace("T", " ") : "";

  return (
    <div className="page">
      <div className="page-head">
        <h1>Space-Weather Driver Forecast</h1>
        <p>
          Probabilistic forecasts of the solar and geomagnetic drivers that govern satellite
          orbital drag — F10.7 solar flux and Kp — each carrying a calibrated uncertainty band,
          and their translation into orbit-decay risk.
        </p>
        {f107 && <div className="issued">Issued {issued} UTC · {f107.data_mode} data</div>}
      </div>

      <div className="grid cols2">
        <div className="panel">
          <h2>F10.7 solar radio flux <span className="unit">45-day forecast · sfu</span></h2>
          {f107 ? <FanChart data={f107} /> : <div className="loading">LOADING…</div>}
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
          <div className="panel">
            <h2>Geomagnetic activity <span className="unit">Kp storm probability</span></h2>
            {kp ? <KpStrip data={kp} /> : <div className="loading">LOADING…</div>}
          </div>
          {brief && (
            <div className="panel">
              <h2>Analyst note</h2>
              <div className="briefing">
                <div className="src">
                  {brief.source === "ai" ? "AI analyst" : "Analyst summary"}
                </div>
                {brief.briefing}
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="grid" style={{ marginTop: 18 }}>
        <div className="panel">
          <h2>Orbital-drag impact <span className="unit">in-track position uncertainty from F10.7</span></h2>
          {drag ? <DragPanel data={drag} /> : <div className="loading">LOADING…</div>}
        </div>
      </div>

      <div className="footer-note">
        <b>PENUMBRA v1.0</b> · Probabilistic space-weather driver forecasting · Apache-2.0 licensed ·
        the phase-2 companion to KESSLER, forming an open orbital-risk stack.<br />
        {f107?.attribution}
      </div>

      {error && (
        <div className="toast">
          {error}
          <button onClick={load}>Retry</button>
        </div>
      )}
    </div>
  );
}
