"""F10.7 forecast: reversion, band monotonicity, floor, synthetic recovery."""
import numpy as np

from app.logic import f107_forecast as ff
from app.logic.calibration import walk_forward_errors
from tests._helpers import synthetic_f107


class TestPoint:
    def test_reverts_toward_mean_at_long_lead(self):
        # history ending well above its own 27-day mean should revert downward
        s = synthetic_f107(n=400, base=130, amp=40, seed=3)
        # force last value high
        s.values[-1] = 220.0
        pred = ff.point_forecast(s, 45)
        assert pred[0] > pred[-1]                      # decays from the spike
        assert pred[-1] < 200.0                        # pulled toward climatology

    def test_floor_enforced(self):
        s = synthetic_f107(n=200, base=66, amp=1, seed=4)
        s.values[-1] = 64.0
        pred = ff.point_forecast(s, 45)
        assert np.all(pred >= 64.0)

    def test_recovers_flat_signal(self):
        s = synthetic_f107(n=400, base=150, amp=0.0, noise=0.0, seed=5)
        pred = ff.point_forecast(s, 10)
        assert np.allclose(pred, 150.0, atol=1.0)


class TestBands:
    def _bt(self):
        s = synthetic_f107(n=700, base=140, amp=35, noise=6, seed=6)
        return s, walk_forward_errors(s, lead_days=20, min_train=300, step=5)

    def test_bands_monotone_across_quantiles(self):
        s, bt = self._bt()
        res = ff.forecast(s, 20, bt.error_quantiles)
        for i in range(20):
            row = [res.bands[q][i] for q in (5, 25, 50, 75, 95)]
            assert row == sorted(row), f"non-monotone band at lead {i+1}: {row}"

    def test_bands_widen_with_lead(self):
        s, bt = self._bt()
        res = ff.forecast(s, 20, bt.error_quantiles)
        width_near = res.bands[95][0] - res.bands[5][0]
        width_far = res.bands[95][-1] - res.bands[5][-1]
        assert width_far >= width_near   # uncertainty grows with horizon

    def test_p50_close_to_point(self):
        s, bt = self._bt()
        res = ff.forecast(s, 20, bt.error_quantiles)
        # median band should track the point forecast within the median error
        assert np.all(np.abs(res.bands[50] - res.point) < 30.0)
