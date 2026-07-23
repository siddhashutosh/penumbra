"""penumbra-toolkit — probabilistic space-weather driver forecasting primitives.

Generated modules are synced from the PENUMBRA backend logic layer
(backend/app/logic), which is the source of truth.
"""
from penumbra_toolkit.calibration import (
    BacktestResult,
    coverage,
    pinball_by_lead,
    pinball_loss,
    reliability,
    skill_vs_reference,
    walk_forward_errors,
)
from penumbra_toolkit.drag import (
    NOTE,
    decay_along_track_km,
    decay_band,
    density_at,
    density_band,
)
from penumbra_toolkit.exceptions import (
    ForecastError,
    InsufficientDataError,
    PenumbraError,
)
from penumbra_toolkit.f107_forecast import (
    F107Result,
    forecast,
    point_forecast,
    quantile_bands,
)
from penumbra_toolkit.kp_forecast import (
    CATEGORIES,
    KpResult,
    category,
    category_probabilities,
    expected_ap,
)
from penumbra_toolkit.series import (
    DailySeries,
    gap_fill,
    kp_to_ap,
    kp_to_daily,
    load_daily_f107,
    trailing_mean,
)

__version__ = "0.1.0"

__all__ = [
    "DailySeries", "load_daily_f107", "kp_to_daily", "kp_to_ap", "gap_fill", "trailing_mean",
    "F107Result", "point_forecast", "quantile_bands", "forecast",
    "CATEGORIES", "KpResult", "category", "category_probabilities", "expected_ap",
    "BacktestResult", "walk_forward_errors", "coverage", "pinball_loss",
    "pinball_by_lead", "skill_vs_reference", "reliability",
    "density_at", "density_band", "decay_along_track_km", "decay_band", "NOTE",
    "PenumbraError", "InsufficientDataError", "ForecastError",
    "__version__",
]
