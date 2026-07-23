# GENERATED from backend/app/logic — edit there, then run packages/sync.py
"""Drag-impact translation (FR-DRAG): F10.7 uncertainty → density → along-track
decay uncertainty. Reduced, order-of-magnitude model — the bridge to KESSLER.

Pure logic. See PEN-LLD-001 §3.5.
"""
from __future__ import annotations

import math

import numpy as np

# Reference exponential-atmosphere density at F10.7 = F_REF (kg/m^3), by altitude.
# Order-of-magnitude reference values (quiet-to-moderate solar activity).
_RHO_REF = {
    400: 3.0e-12,
    550: 4.0e-13,
    800: 2.0e-14,
}
_F_REF = 150.0        # reference F10.7 (sfu)
_F_SCALE = 90.0       # sfu per e-fold of density (documented reduced model)
_MU = 3.986004418e14  # m^3/s^2 (SI)
_R_EARTH = 6378.137   # km

NOTE = (
    "Reduced-model, order-of-magnitude guidance: density scales exponentially "
    "with F10.7 about a tabulated reference; along-track spread integrates a "
    "simplified drag law over the forecast band. Not a high-fidelity propagation."
)


def density_at(alt_km: float, f107: float) -> float:
    """rho(h, F) = rho_ref(h) * exp((F - F_REF) / F_SCALE)."""
    rho_ref = _interp_ref(alt_km)
    return rho_ref * math.exp((f107 - _F_REF) / _F_SCALE)


def _interp_ref(alt_km: float) -> float:
    if alt_km in _RHO_REF:
        return _RHO_REF[alt_km]
    alts = sorted(_RHO_REF)
    if alt_km < alts[0]:
        return _RHO_REF[alts[0]]
    if alt_km > alts[-1]:
        return _RHO_REF[alts[-1]]
    for a0, a1 in zip(alts, alts[1:]):
        if a0 <= alt_km <= a1:
            # log-linear interpolation (density falls ~exponentially with alt)
            f = (alt_km - a0) / (a1 - a0)
            return math.exp(
                (1 - f) * math.log(_RHO_REF[a0]) + f * math.log(_RHO_REF[a1])
            )
    return _RHO_REF[alts[-1]]


def density_band(alt_km: float, f107_p05: float, f107_p50: float,
                 f107_p95: float) -> dict[str, float]:
    return {
        "p05": density_at(alt_km, f107_p05),
        "p50": density_at(alt_km, f107_p50),
        "p95": density_at(alt_km, f107_p95),
    }


def decay_along_track_km(
    alt_km: float, f107_series_p: np.ndarray, ballistic_coeff: float, window_days: int
) -> float:
    """Along-track displacement (km) accumulated over the window under drag driven
    by the given daily F10.7 path.

    Day-by-day integration against an undragged reference orbit:
      * per-rev decay      Δa = -2π · BC · ρ · a²          (m)
      * the shrinking orbit speeds up (n = √(μ/a³)); the along-track lead grows as
        Δs += (n(a) - n(a0)) · a0 · 86400 each day.
    Physically transparent, order-of-magnitude (FR-DRAG-3). BC = Cd·A/m [m²/kg].
    """
    a0 = (_R_EARTH + alt_km) * 1000.0        # m
    n0 = math.sqrt(_MU / a0 ** 3)            # rad/s
    a = a0
    along_track_m = 0.0
    days = min(window_days, len(f107_series_p))
    for i in range(days):
        rho = density_at(alt_km, float(f107_series_p[i]))
        n = math.sqrt(_MU / a ** 3)
        revs_day = 86400.0 / (2.0 * math.pi / n)
        # accumulate along-track drift from the current mean-motion difference
        along_track_m += (n - n0) * a0 * 86400.0
        # apply this day's decay to the semi-major axis
        da_day = -2.0 * math.pi * ballistic_coeff * rho * a ** 2 * revs_day
        a += da_day
    return abs(along_track_m) / 1000.0


def decay_band(
    alt_km: float,
    f107_p05: np.ndarray,
    f107_p50: np.ndarray,
    f107_p95: np.ndarray,
    window_days: int,
    ballistic_coeff: float = 0.005,   # representative compact satellite Cd·A/m [m²/kg]
) -> dict[str, float]:
    return {
        "p05": round(decay_along_track_km(alt_km, f107_p05, ballistic_coeff, window_days), 2),
        "p50": round(decay_along_track_km(alt_km, f107_p50, ballistic_coeff, window_days), 2),
        "p95": round(decay_along_track_km(alt_km, f107_p95, ballistic_coeff, window_days), 2),
    }
