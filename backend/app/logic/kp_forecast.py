"""Kp / geomagnetic storm-category forecast (FR-KP).

Recency-weighted historical transition frequencies conditioned on current
activity → per-lead-day category probabilities. Pure logic. See PEN-LLD-001 §3.3.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from app.logic.series import DailySeries, kp_to_ap

CATEGORIES = ["quiet", "unsettled", "active", "storm"]
_HALFLIFE_DAYS = 180.0
_LAPLACE = 0.5


def category(kp: float) -> str:
    if kp < 3.0:
        return "quiet"
    if kp < 4.0:
        return "unsettled"
    if kp < 5.0:
        return "active"
    return "storm"


@dataclass
class KpResult:
    lead_days: int
    probs: list[dict[str, float]]           # per lead: category -> prob
    expected_ap: list[tuple[float, float, float]]  # per lead: (p05, p50, p95)


def category_probabilities(
    daily_max_kp: DailySeries, lead_days: int, halflife: float = _HALFLIFE_DAYS
) -> list[dict[str, float]]:
    """P(category at t+L | category at t), from recency-weighted history."""
    kp = daily_max_kp.values
    n = len(kp)
    cats = [category(v) for v in kp]
    if n < 10:
        # not enough history: fall back to a flat climatology
        base = {c: 1.0 / len(CATEGORIES) for c in CATEGORIES}
        return [dict(base) for _ in range(lead_days)]

    s0 = cats[-1]
    out: list[dict[str, float]] = []
    ln2 = math.log(2.0)
    for lead in range(1, lead_days + 1):
        counts = {c: _LAPLACE for c in CATEGORIES}
        total = _LAPLACE * len(CATEGORIES)
        for t in range(n - lead):
            if cats[t] != s0:
                continue
            age = (n - 1 - lead - t)  # days before "now"
            w = math.exp(-ln2 * max(age, 0) / halflife)
            dest = cats[t + lead]
            counts[dest] += w
            total += w
        out.append({c: counts[c] / total for c in CATEGORIES})
    return out


def expected_ap(
    daily_ap: DailySeries, lead_days: int
) -> list[tuple[float, float, float]]:
    """Expected daily Ap with a climatological uncertainty band per lead.

    Point = blend of recent Ap and climatology; band from the historical Ap
    spread, widening slightly with lead.
    """
    ap = daily_ap.values
    if len(ap) == 0:
        return [(0.0, 0.0, 0.0)] * lead_days
    recent = float(np.mean(ap[-7:]))
    clim = float(np.mean(ap))
    lo_q = float(np.percentile(ap, 10))
    hi_q = float(np.percentile(ap, 90))
    out = []
    for lead in range(1, lead_days + 1):
        w = 1.0 - math.exp(-lead / 5.0)
        point = (1.0 - w) * recent + w * clim
        widen = 1.0 + 0.05 * lead
        lo = max(0.0, min(point, lo_q)) / widen
        hi = max(point, hi_q) * widen
        out.append((round(lo, 1), round(point, 1), round(hi, 1)))
    return out


def forecast(
    daily_max_kp: DailySeries, daily_ap: DailySeries, lead_days: int
) -> KpResult:
    probs = category_probabilities(daily_max_kp, lead_days)
    ap = expected_ap(daily_ap, lead_days)
    return KpResult(lead_days=lead_days, probs=probs, expected_ap=ap)
