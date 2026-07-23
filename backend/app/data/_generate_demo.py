"""Generate bundled demo datasets for PENUMBRA Demo Mode.

Produces realistic F10.7 and Kp histories (matching NOAA JSON shapes) plus a
NOAA-style 45-day forecast. Deterministic (fixed seed) so the demo is stable.
Run once:  python app/data/_generate_demo.py
"""
from __future__ import annotations

import json
import math
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
N_DAYS = 900
END = date(2026, 7, 20)
rng = np.random.default_rng(20260720)


def build_f107():
    start = END - timedelta(days=N_DAYS - 1)
    dates = [start + timedelta(days=i) for i in range(N_DAYS)]
    t = np.arange(N_DAYS)
    # slow solar-cycle segment (rising then gently falling) + 27-day rotation + noise
    cycle = 120 + 45 * np.sin(2 * math.pi * (t / N_DAYS) * 0.9 - 0.5)
    rotation = 22 * np.sin(2 * math.pi * t / 27.0 + 0.6)
    rotation += 8 * np.sin(2 * math.pi * t / 13.5 + 1.1)
    noise = rng.normal(0, 4.5, N_DAYS)
    vals = np.clip(cycle + rotation + noise, 66, None)
    rows = [{"time_tag": d.isoformat() + "T00:00:00", "flux": round(float(v), 1)}
            for d, v in zip(dates, vals)]
    return dates, vals, rows


def build_kp():
    # 3-hourly Kp for the last 400 days
    kp_days = 400
    start = END - timedelta(days=kp_days - 1)
    rows = [["time_tag", "Kp", "a_running", "station_count"]]
    quiet_level = 1.8
    running = 8.0
    for i in range(kp_days):
        d = start + timedelta(days=i)
        # occasional storms
        storm = 4.0 if rng.random() < 0.05 else 0.0
        for h in range(0, 24, 3):
            base = quiet_level + 0.6 * math.sin(2 * math.pi * i / 27.0)
            kp = float(np.clip(rng.normal(base, 0.5) + storm * rng.random(), 0, 9))
            kp = round(kp * 3) / 3.0  # thirds
            running = 0.9 * running + 0.1 * (kp * 12)
            ts = datetime(d.year, d.month, d.day, h).isoformat()
            rows.append([ts, round(kp, 2), round(running, 1), 8])
    return rows


def build_noaa45(f107_dates, f107_vals):
    """NOAA-style 45-day F10.7/Ap point forecast issued at END.

    Simulates a persistence-flavoured official forecast (intentionally a touch
    worse than PENUMBRA's mean-reversion at long lead) for the live overlay.
    """
    last = float(f107_vals[-1])
    m27 = float(np.mean(f107_vals[-27:]))
    rows = []
    for lead in range(1, 46):
        d = END + timedelta(days=lead)
        # naive-ish: mostly persistence, weak drift to 27-day mean, small bias
        w = min(lead / 40.0, 1.0)
        f = last + (m27 - last) * w * 0.6 + rng.normal(0, 2)
        rows.append({
            "date": d.isoformat(),
            "f10.7": round(float(max(f, 66)), 1),
            "ap": int(np.clip(rng.normal(8, 3), 2, 40)),
        })
    return rows


def main():
    f_dates, f_vals, f_rows = build_f107()
    (HERE / "sample_f107.json").write_text(json.dumps(f_rows), encoding="utf-8")
    (HERE / "sample_kp.json").write_text(json.dumps(build_kp()), encoding="utf-8")
    (HERE / "sample_noaa45.json").write_text(
        json.dumps(build_noaa45(f_dates, f_vals)), encoding="utf-8")
    print(f"wrote sample_f107.json ({len(f_rows)} rows), sample_kp.json, sample_noaa45.json")


if __name__ == "__main__":
    main()
