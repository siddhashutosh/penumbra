# GENERATED from backend/app/logic — edit there, then run packages/sync.py
"""Verification & calibration (FR-VER) — the product's credibility engine.

Walk-forward, leakage-free backtest → per-lead error quantiles (which feed the
F10.7 bands), band coverage, pinball loss, skill vs NOAA, and Kp reliability.
Pure logic. See PEN-LLD-001 §3.4.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

from penumbra_toolkit.f107_forecast import point_forecast
from penumbra_toolkit.series import DailySeries

logger = logging.getLogger(__name__)

_QUANTILES = (5, 25, 50, 75, 95)


@dataclass
class BacktestResult:
    lead_days: int
    errors: dict[int, np.ndarray]           # lead -> signed (obs - pred) OOS
    error_quantiles: dict[int, dict[int, float]]
    penumbra_rmse: dict[int, float]         # lead -> RMSE
    reference_rmse: dict[int, float]        # lead -> persistence-baseline RMSE


def _slice(history: DailySeries, upto: int) -> DailySeries:
    return DailySeries(history.dates[: upto + 1], history.values[: upto + 1])


def walk_forward_errors(
    history: DailySeries,
    lead_days: int,
    min_train: int,
    step: int = 3,
) -> BacktestResult:
    """At each origin t >= min_train, forecast forward using ONLY history[:t+1],
    then record the signed error at each lead against the realised value.

    Strict causality (CON-2): the training slice never contains any sample at or
    after the origin, so no future information can leak into a past-origin error.
    """
    n = len(history)
    if n < min_train + lead_days:
        raise ValueError(
            f"history too short for backtest: need {min_train + lead_days}, have {n}"
        )
    errors: dict[int, list[float]] = {lead: [] for lead in range(1, lead_days + 1)}
    ref_sq: dict[int, list[float]] = {lead: [] for lead in range(1, lead_days + 1)}
    for t in range(min_train, n - 1):
        if (t - min_train) % step != 0:
            continue
        train = _slice(history, t)
        max_lead = min(lead_days, n - 1 - t)
        pred = point_forecast(train, max_lead)
        persistence = float(train.values[-1])   # naive reference: last observed
        for lead in range(1, max_lead + 1):
            obs = float(history.values[t + lead])
            errors[lead].append(obs - float(pred[lead - 1]))
            ref_sq[lead].append((obs - persistence) ** 2)

    err_arr = {lead: np.array(v) for lead, v in errors.items() if v}
    eq: dict[int, dict[int, float]] = {}
    rmse: dict[int, float] = {}
    ref_rmse: dict[int, float] = {}
    for lead, arr in err_arr.items():
        eq[lead] = {q: float(np.percentile(arr, q)) for q in _QUANTILES}
        rmse[lead] = float(np.sqrt(np.mean(arr ** 2)))
        ref_rmse[lead] = float(np.sqrt(np.mean(np.array(ref_sq[lead]))))
    return BacktestResult(lead_days=lead_days, errors=err_arr, error_quantiles=eq,
                          penumbra_rmse=rmse, reference_rmse=ref_rmse)


def coverage(backtest: BacktestResult) -> list[dict]:
    """Empirical coverage of the p05–p95 (90%) and p25–p75 (50%) bands per lead.

    Because bands = point + error-quantiles, an observation falls inside the 90%
    band iff its error lies within [q05, q95]. Computed here from the OOS errors.
    """
    out = []
    for lead in sorted(backtest.errors):
        arr = backtest.errors[lead]
        eq = backtest.error_quantiles[lead]
        inside90 = np.mean((arr >= eq[5]) & (arr <= eq[95]))
        inside50 = np.mean((arr >= eq[25]) & (arr <= eq[75]))
        out.append({
            "lead": lead,
            "target_90": 0.90,
            "empirical_90": round(float(inside90), 3),
            "empirical_50": round(float(inside50), 3),
        })
    return out


def pinball_loss(y: float, q_pred: float, q: float) -> float:
    """Quantile (pinball) loss for a single quantile level q in (0,1)."""
    if y >= q_pred:
        return q * (y - q_pred)
    return (1.0 - q) * (q_pred - y)


def pinball_by_lead(backtest: BacktestResult) -> list[float]:
    """Mean pinball loss across quantiles, per lead — lower is better."""
    out = []
    for lead in sorted(backtest.errors):
        arr = backtest.errors[lead]
        eq = backtest.error_quantiles[lead]
        losses = []
        for q_int in _QUANTILES:
            q = q_int / 100.0
            offset = eq[q_int]
            # residual r = obs - point; quantile prediction of r is `offset`
            losses.extend(pinball_loss(float(r), offset, q) for r in arr)
        out.append(round(float(np.mean(losses)), 3))
    return out


def skill_vs_reference(
    backtest: BacktestResult, reference_rmse: dict[int, float] | None = None
) -> list[dict]:
    """Skill = 1 - RMSE_penumbra / RMSE_reference, per lead (positive = better).

    Default reference is the persistence baseline computed in the same
    walk-forward backtest — reproducible and leakage-free. NOAA's live forecast
    is overlaid separately on the forecast chart for direct visual comparison.
    """
    ref = reference_rmse if reference_rmse is not None else backtest.reference_rmse
    out = []
    for lead in sorted(backtest.penumbra_rmse):
        pen = backtest.penumbra_rmse[lead]
        nref = (ref or {}).get(lead)
        skill = None
        if nref and nref > 0:
            skill = round(1.0 - pen / nref, 3)
        out.append({
            "lead": lead,
            "penumbra_rmse": round(pen, 2),
            "baseline_rmse": round(nref, 2) if nref else None,
            "skill": skill,
        })
    return out


def reliability(
    predicted_probs: list[float], outcomes: list[int], bins: int = 10
) -> list[dict]:
    """Reliability diagram: for each probability bin, predicted vs observed freq.

    predicted_probs: forecast probability of the event (e.g. storm) per case.
    outcomes: 1 if the event occurred, else 0.
    """
    out = []
    p = np.array(predicted_probs)
    y = np.array(outcomes)
    if len(p) == 0:
        return out
    edges = np.linspace(0.0, 1.0, bins + 1)
    for b in range(bins):
        lo, hi = edges[b], edges[b + 1]
        mask = (p >= lo) & (p < hi) if b < bins - 1 else (p >= lo) & (p <= hi)
        cnt = int(np.sum(mask))
        if cnt == 0:
            continue
        out.append({
            "predicted": round(float(np.mean(p[mask])), 3),
            "observed": round(float(np.mean(y[mask])), 3),
            "count": cnt,
        })
    return out
