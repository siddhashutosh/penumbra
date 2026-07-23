# PENUMBRA — Demo Video Narration Script

The bundled `penumbra-demo.mp4` uses synthesized narration. To replace it with a natural
voice (e.g. ElevenLabs), generate **one clip per scene** named `voice01`…`voice10`, and the
video can be re-muxed to your clip lengths. Clean text (no TTS spelling hacks) below.

**Scene 1 — Title**
> This is PENUMBRA. It forecasts the space weather that governs satellite orbits — and unlike every operational product, it tells you how much to trust each forecast.

**Scene 2 — The problem**
> Here's the problem. Atmospheric drag is the largest source of orbit-prediction error in low Earth orbit. The forecasts that drive it — solar flux and geomagnetic activity — are published as single numbers, with no uncertainty at all. In 2022, a single solar storm de-orbited around forty new Starlink satellites — exactly this blind spot.

**Scene 3 — What it does**
> PENUMBRA is a six-stage pipeline. It pulls the free NOAA feeds, then runs a leakage-free walk-forward backtest to learn the real distribution of forecast errors, and produces forecasts of F10.7 and Kp with uncertainty bands you can actually trust.

**Scene 4 — Dashboard**
> This is the live dashboard. The solar flux forecast is drawn as a fan, with nested 50% and 90% uncertainty bands, and NOAA's own forecast overlaid. Alongside it, the daily probability of a geomagnetic storm.

**Scene 5 — Honest by construction**
> The uncertainty is honest by construction. The bands are learned from out-of-sample errors, never fit in-sample. So a 90% band actually contains the truth 90% of the time — and PENUMBRA beats the persistence baseline at 36 of 45 lead times.

**Scene 6 — Calibration**
> This is the calibration page — the credibility artifact. Every metric comes from the backtest: coverage against target, skill against baseline, and storm reliability. It even shows where the model is weaker.

**Scene 7 — Why it matters**
> And here's why it matters. That flux uncertainty becomes position uncertainty. At 400 kilometers, the F10.7 band alone implies nineteen hundred kilometers of in-track uncertainty over a month. PENUMBRA feeds this straight into KESSLER, its conjunction-assessment companion. Together — an open orbital-risk stack.

**Scene 8 — Implement it**
> To run it: clone the repository, create a virtual environment, install the requirements, and start the server. It works instantly on bundled data. No accounts, no keys. Set one flag for live NOAA data.

**Scene 9 — The API**
> Everything is a typed REST API. Solar flux forecasts. Storm probabilities. Drag uncertainty by altitude. The full calibration report. And interactive documentation at slash-docs.

**Scene 10 — Close**
> PENUMBRA is open source, calibrated, and running live right now. Try the demo, read the code, or pair it with KESSLER. Links on screen.
