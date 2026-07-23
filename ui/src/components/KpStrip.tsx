// Kp storm-probability strip (FR-UI-2): per-day stacked category bars.
import type { KpForecast } from "../types";

const ORDER = ["quiet", "unsettled", "active", "storm"];
const CLASS: Record<string, string> = {
  quiet: "cat-quiet",
  unsettled: "cat-unsettled",
  active: "cat-active",
  storm: "cat-storm",
};

export default function KpStrip({ data }: { data: KpForecast }) {
  return (
    <div>
      <div className="kp-strip">
        {data.days.map((day) => (
          <div className="kp-day" key={day.lead}>
            <span className="lbl">
              +{day.lead}d · {day.date.slice(5)}
            </span>
            <div className="bar" title={`storm ${(day.probs.storm * 100).toFixed(0)}%`}>
              {ORDER.map((cat) => {
                const p = day.probs[cat] ?? 0;
                return p > 0.001 ? (
                  <span
                    key={cat}
                    className={CLASS[cat]}
                    style={{ width: `${p * 100}%` }}
                  />
                ) : null;
              })}
            </div>
            <span className="ap">Ap {day.expected_ap.p50.toFixed(0)}</span>
          </div>
        ))}
      </div>
      <div className="kp-legend">
        {ORDER.map((cat) => (
          <div className="item" key={cat}>
            <span className={`sw ${CLASS[cat]}`} />
            {cat}
          </div>
        ))}
      </div>
    </div>
  );
}
