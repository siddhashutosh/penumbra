# GENERATED from backend/app/logic — edit there, then run packages/sync.py
"""F10.7 probabilistic forecast (FR-F107): persistence + mean-reversion point
model, and quantile bands from out-of-sample error distributions.

Pure logic: no I/O. See PEN-LLD-001 §3.2.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from penumbra_toolkit.series import DailySeries, trailing_mean

# Reversion time-constant (days): how quickly persistence gives way to the
# climatological target as lead time grows.
_TAU_DAYS = 10.0
_ROTATION_DAYS = 27          # solar-rotation period
_CYCLE_WINDOW_DAYS = 90      # slow cycle level

F107_FLOOR_SFU = 64.0        # quiet-Sun minimum (FR-F107-3)
_QUANTILES = (5, 25, 50, 75, 95)


@dataclass
class F107Result:
    lead_days: int
    point: np.ndarray                       # [lead]
    bands: dict[int, np.ndarray]            # quantile -> [lead]


def point_forecast(
    history: DailySeries, lead_days: int, floor: float = F107_FLOOR_SFU
) -> np.ndarray:
    """Persistence toward a climatological target.

    f(L) = x0 + (target(L) - x0) * w(L),  w(L) = 1 - exp(-L / TAU).
    target blends the trailing 27-day rotation mean (short lead) with the slower
    90-day cycle level (long lead). Floored at the quiet-Sun minimum.
    """
    if len(history) == 0:
        raise ValueError("empty history")
    x0 = float(history.values[-1])
    m27 = trailing_mean(history.values, _ROTATION_DAYS)
    mcyc = trailing_mean(history.values, _CYCLE_WINDOW_DAYS)

    out = np.empty(lead_days, dtype=float)
    for i in range(lead_days):
        lead = i + 1
        w = 1.0 - math.exp(-lead / _TAU_DAYS)
        # long-lead target leans toward the cycle level
        cyc_weight = 1.0 - math.exp(-lead / (_ROTATION_DAYS * 1.5))
        target = (1.0 - cyc_weight) * m27 + cyc_weight * mcyc
        f = x0 + (target - x0) * w
        out[i] = max(f, floor)
    return out


def quantile_bands(
    point: np.ndarray,
    error_quantiles: dict[int, dict[int, float]],
    floor: float = F107_FLOOR_SFU,
) -> dict[int, np.ndarray]:
    """Add per-lead empirical error quantiles to the point forecast.

    error_quantiles[lead][q] = the q-th percentile of (obs - point) at that lead,
    measured out-of-sample by the walk-forward backtest. Bands are enforced
    monotone across quantiles and floored.
    """
    lead_days = len(point)
    bands = {q: np.empty(lead_days, dtype=float) for q in _QUANTILES}
    for i in range(lead_days):
        lead = i + 1
        eq = error_quantiles.get(lead, {})
        for q in _QUANTILES:
            offset = eq.get(q, 0.0)
            bands[q][i] = max(point[i] + offset, floor)
        # enforce monotonicity p05 <= p25 <= ... <= p95 at this lead
        prev = bands[_QUANTILES[0]][i]
        for q in _QUANTILES[1:]:
            if bands[q][i] < prev:
                bands[q][i] = prev
            prev = bands[q][i]
    return bands


def forecast(
    history: DailySeries,
    lead_days: int,
    error_quantiles: dict[int, dict[int, float]],
    floor: float = F107_FLOOR_SFU,
) -> F107Result:
    point = point_forecast(history, lead_days, floor)
    bands = quantile_bands(point, error_quantiles, floor)
    return F107Result(lead_days=lead_days, point=point, bands=bands)
