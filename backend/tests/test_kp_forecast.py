"""Kp forecast: probability normalisation, storm sensitivity, Ap band order."""
import numpy as np

from app.logic import kp_forecast as kf
from app.logic.series import DailySeries, kp_to_ap
from tests._helpers import synthetic_kp


class TestCategories:
    def test_boundaries(self):
        assert kf.category(2.9) == "quiet"
        assert kf.category(3.0) == "unsettled"
        assert kf.category(4.0) == "active"
        assert kf.category(5.0) == "storm"
        assert kf.category(8.5) == "storm"

    def test_probabilities_sum_to_one(self):
        s = synthetic_kp(n=400, seed=2)
        probs = kf.category_probabilities(s, lead_days=7)
        assert len(probs) == 7
        for day in probs:
            assert abs(sum(day.values()) - 1.0) < 1e-9
            assert set(day) == set(kf.CATEGORIES)

    def test_recent_storm_raises_storm_probability(self):
        # a history whose last day is a storm should show elevated storm prob
        # relative to one whose last day is quiet
        quiet = synthetic_kp(n=400, seed=7)
        quiet.values[-1] = 1.0
        stormy = DailySeries(list(quiet.dates), quiet.values.copy())
        stormy.values[-1] = 7.0
        # seed some storm->storm persistence in stormy history
        for i in range(-30, 0, 10):
            stormy.values[i] = 6.0
        p_quiet = kf.category_probabilities(quiet, 3)[0]["storm"]
        p_storm = kf.category_probabilities(stormy, 3)[0]["storm"]
        assert p_storm >= p_quiet


class TestAp:
    def test_ap_band_ordered(self):
        ap_vals = np.array([kp_to_ap(v) for v in synthetic_kp(n=400).values])
        s = DailySeries(synthetic_kp(n=400).dates, ap_vals)
        band = kf.expected_ap(s, 7)
        for lo, point, hi in band:
            assert lo <= point <= hi

    def test_full_forecast_shape(self):
        maxkp = synthetic_kp(n=400, seed=9)
        ap = DailySeries(maxkp.dates, np.array([kp_to_ap(v) for v in maxkp.values]))
        res = kf.forecast(maxkp, ap, 7)
        assert res.lead_days == 7
        assert len(res.probs) == 7
        assert len(res.expected_ap) == 7
