# GENERATED from backend/app/logic — edit there, then run packages/sync.py
"""Time-series utilities: load, align, gap-fill, Kp->daily aggregation.

Pure logic: numpy + stdlib only, no I/O, no framework imports.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta

import numpy as np
from dateutil import parser as dtparser

from penumbra_toolkit.exceptions import InsufficientDataError

logger = logging.getLogger(__name__)

# Standard ap-from-Kp lookup (Kp in thirds -> daily-equivalent ap amplitude).
# Index by Kp*3 rounded (0.0, 0.33, 0.67, 1.0, ...). Values per IAGA convention.
_KP_STEPS = [0.0, 0.33, 0.67, 1.0, 1.33, 1.67, 2.0, 2.33, 2.67, 3.0, 3.33, 3.67,
             4.0, 4.33, 4.67, 5.0, 5.33, 5.67, 6.0, 6.33, 6.67, 7.0, 7.33, 7.67,
             8.0, 8.33, 8.67, 9.0]
_AP_VALUES = [0, 2, 3, 4, 5, 6, 7, 9, 12, 15, 18, 22, 27, 32, 39, 48, 56, 67, 80,
              94, 111, 132, 154, 179, 207, 236, 300, 400]


@dataclass
class DailySeries:
    dates: list[date]
    values: np.ndarray  # float64, aligned 1:1 with dates

    def __len__(self) -> int:
        return len(self.dates)

    @property
    def last_date(self) -> date:
        return self.dates[-1]


def _to_date(value) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    return dtparser.parse(str(value)).date()


def kp_to_ap(kp: float) -> float:
    """Convert a single Kp value to its ap amplitude via the standard lookup."""
    idx = int(round(kp * 3))
    idx = max(0, min(idx, len(_AP_VALUES) - 1))
    return float(_AP_VALUES[idx])


def load_daily_f107(records: list[dict]) -> DailySeries:
    """Parse NOAA f107_cm_flux.json rows into a daily series.

    Each row: {"time_tag": "2026-07-20T00:00:00", "flux": 148.2} (field name may
    be 'flux' or 'f107'); tolerant of either.
    """
    pairs: dict[date, float] = {}
    for row in records:
        t = row.get("time_tag") or row.get("time-tag") or row.get("date")
        v = row.get("flux", row.get("f107", row.get("f10.7")))
        if t is None or v in (None, "", -1, -1.0):
            continue
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        if f <= 0:
            continue
        pairs[_to_date(t)] = f
    if len(pairs) < 30:
        raise InsufficientDataError(
            "Too few valid F10.7 observations", detail={"count": len(pairs)}
        )
    ordered = sorted(pairs.items())
    return DailySeries([d for d, _ in ordered], np.array([v for _, v in ordered]))


def kp_to_daily(records: list[dict]) -> tuple[DailySeries, DailySeries]:
    """Aggregate 3-hourly Kp rows into daily max-Kp and daily Ap series.

    NOAA products/noaa-planetary-k-index.json is a list-of-lists with a header
    row: [time_tag, Kp, a_running, station_count]. Also tolerant of dict rows.
    """
    by_day_max: dict[date, float] = {}
    by_day_aps: dict[date, list[float]] = {}

    rows = records
    if rows and isinstance(rows[0], list):
        header = [str(h).lower() for h in rows[0]]
        try:
            ti = header.index("time_tag")
            ki = header.index("kp")
        except ValueError:
            ti, ki = 0, 1
        rows = [{"time_tag": r[ti], "kp": r[ki]} for r in rows[1:]]

    for row in rows:
        t = row.get("time_tag") or row.get("time-tag")
        v = row.get("kp", row.get("Kp", row.get("kp_index")))
        if t is None or v in (None, ""):
            continue
        try:
            kp = float(v)
        except (TypeError, ValueError):
            continue
        d = _to_date(t)
        by_day_max[d] = max(by_day_max.get(d, 0.0), kp)
        by_day_aps.setdefault(d, []).append(kp_to_ap(kp))

    if len(by_day_max) < 10:
        raise InsufficientDataError(
            "Too few valid Kp observations", detail={"count": len(by_day_max)}
        )
    days = sorted(by_day_max)
    max_kp = DailySeries(days, np.array([by_day_max[d] for d in days]))
    ap = DailySeries(days, np.array([float(np.mean(by_day_aps[d])) for d in days]))
    return max_kp, ap


def gap_fill(series: DailySeries, max_gap_days: int = 3) -> DailySeries:
    """Fill a daily series onto a contiguous grid; linear-interpolate short gaps,
    forward-fill anything longer (marked implicitly by carrying the last value)."""
    if len(series) == 0:
        return series
    start, end = series.dates[0], series.dates[-1]
    n = (end - start).days + 1
    grid = [start + timedelta(days=i) for i in range(n)]
    known = {d: v for d, v in zip(series.dates, series.values)}

    out = np.empty(n, dtype=float)
    last_val = series.values[0]
    i = 0
    while i < n:
        d = grid[i]
        if d in known:
            out[i] = known[d]
            last_val = out[i]
            i += 1
            continue
        # find next known point
        j = i
        while j < n and grid[j] not in known:
            j += 1
        if j < n and (grid[j] - grid[i - 1]).days <= max_gap_days:
            v0, v1 = out[i - 1], known[grid[j]]
            span = j - (i - 1)
            for k in range(i, j):
                out[k] = v0 + (v1 - v0) * (k - (i - 1)) / span
        else:
            for k in range(i, min(j, n)):
                out[k] = last_val
        i = j
    return DailySeries(grid, out)


def trailing_mean(values: np.ndarray, window: int) -> float:
    """Mean of the last `window` samples (or all if fewer)."""
    if len(values) == 0:
        return 0.0
    return float(np.mean(values[-window:]))
