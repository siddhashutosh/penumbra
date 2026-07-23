// Drag-impact panel (FR-UI-2): in-track position uncertainty at reference
// altitudes, driven by the F10.7 forecast band. The bridge to KESSLER.
import type { DragImpact } from "../types";

export default function DragPanel({ data }: { data: DragImpact }) {
  const maxDecay = Math.max(...data.altitudes.map((a) => a.decay_along_track_km.p95));
  return (
    <div>
      <div className="drag-grid">
        {data.altitudes.map((a) => {
          const d = a.decay_along_track_km;
          const spread = d.p95 - d.p05;
          const fillLo = (d.p05 / maxDecay) * 100;
          const fillW = ((d.p95 - d.p05) / maxDecay) * 100;
          return (
            <div className="drag-alt" key={a.alt_km}>
              <div className="top">
                <span className="alt">{a.alt_km.toFixed(0)} km</span>
                <span className="decay">
                  ±{d.p50.toFixed(0)}
                  <small> km in-track ({data.window_days}d)</small>
                </span>
              </div>
              <div className="spread">
                90% range {d.p05.toFixed(0)}–{d.p95.toFixed(0)} km · spread {spread.toFixed(0)} km
              </div>
              <div className="drag-bar">
                <div className="fill" style={{ left: `${fillLo}%`, width: `${Math.max(fillW, 1)}%` }} />
              </div>
            </div>
          );
        })}
      </div>
      <div className="note">{data.note}</div>
    </div>
  );
}
