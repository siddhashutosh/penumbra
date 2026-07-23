"""Calibration: leakage-freedom, coverage, pinball, skill, reliability."""
import numpy as np
import pytest

from app.logic import calibration as cal
from app.logic.series import DailySeries
from tests._helpers import synthetic_f107


class TestLeakage:
    def test_future_cannot_change_past_origin_errors(self):
        """The single most important correctness property (CON-2): mutating the
        tail of the series must not change errors computed at earlier origins."""
        s = synthetic_f107(n=600, base=140, amp=30, noise=5, seed=11)
        bt_full = cal.walk_forward_errors(s, lead_days=10, min_train=300, step=10)

        # corrupt only the last 50 samples (all beyond the last usable origin's
        # forecast window for early origins)
        s2 = DailySeries(list(s.dates), s.values.copy())
        s2.values[-50:] += 999.0
        bt_mut = cal.walk_forward_errors(s2, lead_days=10, min_train=300, step=10)

        # errors at leads originating well before the corruption must be identical
        # compare the first origin's contribution: errors[lead][0]
        for lead in range(1, 11):
            assert bt_full.errors[lead][0] == pytest.approx(bt_mut.errors[lead][0])


class TestCoverage:
    def test_nominal_coverage_on_stationary_signal(self):
        s = synthetic_f107(n=900, base=150, amp=20, noise=8, seed=12)
        bt = cal.walk_forward_errors(s, lead_days=15, min_train=400, step=3)
        cov = cal.coverage(bt)
        # by construction the empirical 90% band covers ~90% of the SAME errors
        for row in cov:
            assert 0.82 <= row["empirical_90"] <= 0.98
            assert 0.40 <= row["empirical_50"] <= 0.62


class TestPinball:
    def test_zero_at_perfect_quantile(self):
        # if predicted quantile equals the value, pinball loss is 0
        assert cal.pinball_loss(5.0, 5.0, 0.5) == 0.0

    def test_asymmetry(self):
        # under-prediction of a high quantile penalised by q; over by (1-q)
        under = cal.pinball_loss(10.0, 8.0, 0.9)   # y>pred -> 0.9*2
        over = cal.pinball_loss(6.0, 8.0, 0.9)     # y<pred -> 0.1*2
        assert under > over

    def test_by_lead_nonnegative(self):
        s = synthetic_f107(n=700, noise=6, seed=13)
        bt = cal.walk_forward_errors(s, lead_days=10, min_train=350, step=5)
        pins = cal.pinball_by_lead(bt)
        assert len(pins) == 10
        assert all(p >= 0 for p in pins)


class TestSkill:
    def test_skill_sign(self):
        s = synthetic_f107(n=700, noise=6, seed=14)
        bt = cal.walk_forward_errors(s, lead_days=5, min_train=350, step=5)
        # NOAA worse (higher RMSE) -> positive skill
        noaa = {lead: r * 2.0 for lead, r in bt.penumbra_rmse.items()}
        good = cal.skill_vs_reference(bt, noaa)
        assert all(row["skill"] > 0 for row in good)
        # NOAA better -> negative skill
        noaa_better = {lead: r * 0.5 for lead, r in bt.penumbra_rmse.items()}
        bad = cal.skill_vs_reference(bt, noaa_better)
        assert all(row["skill"] < 0 for row in bad)

    def test_skill_none_without_reference(self):
        s = synthetic_f107(n=700, noise=6, seed=15)
        bt = cal.walk_forward_errors(s, lead_days=5, min_train=350, step=5)
        rows = cal.skill_vs_reference(bt, None)
        assert all(row["skill"] is None for row in rows)


class TestReliability:
    def test_perfect_reliability(self):
        # predicted probs equal observed frequencies exactly
        preds = [0.05] * 100 + [0.95] * 100
        outs = [0] * 95 + [1] * 5 + [0] * 5 + [1] * 95
        rel = cal.reliability(preds, outs, bins=10)
        for b in rel:
            assert abs(b["predicted"] - b["observed"]) < 0.1
