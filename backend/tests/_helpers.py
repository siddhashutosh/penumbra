"""Synthetic series generators for deterministic tests."""
from __future__ import annotations

import math
from datetime import date, timedelta

import numpy as np

from app.logic.series import DailySeries


def synthetic_f107(n: int = 800, base: float = 130.0, amp: float = 40.0,
                   trend: float = 0.0, noise: float = 0.0, seed: int = 0) -> DailySeries:
    """Sinusoid on the 27-day rotation + optional slow trend + optional noise."""
    rng = np.random.default_rng(seed)
    start = date(2024, 1, 1)
    dates = [start + timedelta(days=i) for i in range(n)]
    t = np.arange(n)
    vals = base + amp * np.sin(2 * math.pi * t / 27.0) + trend * t
    if noise:
        vals = vals + rng.normal(0, noise, n)
    vals = np.clip(vals, 64.0, None)
    return DailySeries(dates, vals.astype(float))


def synthetic_kp(n: int = 400, storm_every: int = 40, seed: int = 1) -> DailySeries:
    """Mostly-quiet Kp with periodic storms."""
    rng = np.random.default_rng(seed)
    start = date(2024, 1, 1)
    dates = [start + timedelta(days=i) for i in range(n)]
    vals = np.clip(rng.normal(2.0, 0.7, n), 0, 9)
    for i in range(0, n, storm_every):
        vals[i] = 6.0  # a storm
    return DailySeries(dates, vals.astype(float))
