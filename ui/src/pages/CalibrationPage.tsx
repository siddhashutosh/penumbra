import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { CalibrationReport } from "../types";
import CoverageChart from "../components/CoverageChart";

export default function CalibrationPage() {
  const [data, setData] = useState<CalibrationReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<CalibrationReport>("/api/v1/calibration")
      .then(setData)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load"));
  }, []);

  if (!data) {
    return (
      <div className="page">
        <div className="loading">{error ?? "LOADING CALIBRATION…"}</div>
      </div>
    );
  }

  const meanCov =
    data.coverage_by_lead.reduce((s, c) => s + c.empirical_90, 0) /
    Math.max(data.coverage_by_lead.length, 1);
  const posSkill = data.skill_vs_noaa.filter((s) => s.skill != null && s.skill > 0).length;
  const meanPinball =
    data.pinball_by_lead.reduce((s, p) => s + p, 0) / Math.max(data.pinball_by_lead.length, 1);

  return (
    <div className="page">
      <div className="page-head">
        <h1>Forecast Calibration</h1>
        <p>
          The credibility artifact. A forecast's uncertainty is only useful if it is honest — a
          stated 90% band must actually contain the truth 90% of the time. Every metric here comes
          from a leakage-free walk-forward backtest over the historical record.
        </p>
      </div>

      <div className="metric-row">
        <div className="metric">
          <div className="k">Mean 90% coverage</div>
          <div className={`v ${Math.abs(meanCov - 0.9) < 0.05 ? "good" : "amber"}`}>
            {(meanCov * 100).toFixed(0)}%
          </div>
        </div>
        <div className="metric">
          <div className="k">Beats persistence</div>
          <div className="v good">
            {posSkill}/{data.skill_vs_noaa.length}
          </div>
        </div>
        <div className="metric">
          <div className="k">Mean pinball loss</div>
          <div className="v">{meanPinball.toFixed(1)}</div>
        </div>
      </div>

      <div className="summary-box">{data.summary}</div>

      <div className="grid cols2">
        <div className="panel">
          <h2>Band coverage by lead <span className="unit">empirical vs target</span></h2>
          <CoverageChart data={data} kind="coverage" />
          <div className="legend-row">
            <div className="item"><span className="ln" style={{ borderColor: "#ffb454" }} />90% band</div>
            <div className="item"><span className="ln" style={{ borderColor: "#4fd4c4" }} />50% band</div>
            <div className="item"><span className="ln" style={{ borderColor: "#6ee787", borderStyle: "dashed" }} />target</div>
          </div>
        </div>
        <div className="panel">
          <h2>Skill vs baseline <span className="unit">1 − RMSE/persistence</span></h2>
          <CoverageChart data={data} kind="skill" />
        </div>
      </div>

      <div className="grid" style={{ marginTop: 18 }}>
        <div className="panel">
          <h2>Kp storm reliability <span className="unit">predicted vs observed frequency</span></h2>
          <CoverageChart data={data} kind="reliability" />
          <div className="note">
            Points on the diagonal mean the forecast probabilities match reality; marker size
            reflects the number of cases in each bin.
          </div>
        </div>
      </div>
    </div>
  );
}
