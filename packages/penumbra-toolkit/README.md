# penumbra-toolkit

Probabilistic space-weather driver forecasting for Python: forecast the F10.7 solar radio
flux and the Kp geomagnetic index with **calibrated uncertainty bands**, verify that
calibration with a leakage-free walk-forward backtest, and translate the uncertainty into
orbital-drag risk.

Extracted from [PENUMBRA](https://github.com/siddhashutosh/penumbra), where the same code powers
a live dashboard over the public NOAA feeds. The phase-2 companion to
[kessler-toolkit](https://pypi.org/project/kessler-toolkit/).

```bash
pip install penumbra-toolkit
```

## What's inside

| Module | Purpose |
|---|---|
| `series` | Parse NOAA F10.7 / Kp, aggregate Kp→daily Ap, align and gap-fill daily series |
| `f107_forecast` | Persistence + mean-reversion point forecast with empirical quantile bands |
| `kp_forecast` | Recency-weighted geomagnetic storm-category probabilities + Ap band |
| `calibration` | Leakage-free walk-forward backtest, coverage, pinball loss, skill, reliability |
| `drag` | F10.7 band → thermospheric density → in-track orbit-decay uncertainty |

## Quick start

```python
import numpy as np
from penumbra_toolkit import (
    DailySeries, walk_forward_errors, forecast, coverage, skill_vs_reference,
)

# a daily F10.7 history (dates + values)
history = DailySeries(dates, values)

# learn the out-of-sample error distribution, then forecast with calibrated bands
bt = walk_forward_errors(history, lead_days=45, min_train=400)
fc = forecast(history, 45, bt.error_quantiles)

print(fc.point[6], fc.bands[5][6], fc.bands[95][6])   # 7-day point + 90% band
print(coverage(bt)[0])                                # empirical vs target coverage
print(skill_vs_reference(bt)[0])                      # skill vs persistence baseline
```

Every uncertainty band is **learned from real out-of-sample forecast errors** — calibrated by
construction if the backtest is leakage-free, which is enforced by test. Drag translation is a
reduced, order-of-magnitude model (not a high-fidelity propagation).

Apache-2.0. Space-weather data used with PENUMBRA courtesy of NOAA SWPC and GFZ Potsdam.
