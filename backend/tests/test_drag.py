"""Drag translation: monotonicity in F10.7, altitude ordering, band widening."""
import numpy as np

from app.logic import drag


class TestDensity:
    def test_increases_with_f107(self):
        lo = drag.density_at(400, 100.0)
        hi = drag.density_at(400, 200.0)
        assert hi > lo

    def test_altitude_ordering(self):
        # lower altitude -> denser atmosphere
        assert drag.density_at(400, 150.0) > drag.density_at(550, 150.0)
        assert drag.density_at(550, 150.0) > drag.density_at(800, 150.0)

    def test_reference_value_at_f_ref(self):
        # at F10.7 = 150 (F_REF) the 400 km density equals the tabulated ref
        assert drag.density_at(400, 150.0) == drag._RHO_REF[400]


class TestDecayBand:
    def test_higher_flux_widens_decay(self):
        days = 30
        p05 = np.full(days, 90.0)
        p50 = np.full(days, 150.0)
        p95 = np.full(days, 220.0)
        band = drag.decay_band(400, p05, p50, p95, days)
        assert band["p05"] <= band["p50"] <= band["p95"]
        assert band["p95"] > band["p05"]

    def test_lower_altitude_more_decay(self):
        days = 30
        p = np.full(days, 150.0)
        low = drag.decay_band(400, p, p, p, days)["p50"]
        high = drag.decay_band(800, p, p, p, days)["p50"]
        assert low > high
