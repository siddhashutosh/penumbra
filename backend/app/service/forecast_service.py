"""Pipeline orchestrator: load -> align -> backtest -> forecast -> calibrate ->
publish. Stage failures degrade to last-known-good; the pipeline never aborts
the app (FR-ING-6). See PEN-HLD-001 §2.2 and PEN-LLD-001 §6.2.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
from dateutil import parser as dtparser

from app.core.config import settings
from app.core.exceptions import DataSourceError, InsufficientDataError, NotFoundError
from app.logic import calibration as cal
from app.logic import drag
from app.logic import f107_forecast as ff
from app.logic import kp_forecast as kf
from app.logic import series as sr
from app.service.briefing_service import BriefingService
from app.service.cache_service import CacheService
from app.service.pipeline_service import PipelineService
from app.service.swpc_client import SwpcClient

logger = logging.getLogger(__name__)

_ATTRIBUTION = (
    "Space-weather data courtesy of NOAA SWPC (public domain) and GFZ Potsdam. "
    "Drag translation is a reduced, order-of-magnitude model."
)
_ALTITUDES = [400.0, 550.0, 800.0]


class ForecastService:
    def __init__(self):
        self.cache = CacheService(settings.data_dir / "cache.db")
        self.pipeline = PipelineService(self.cache)
        self.swpc = SwpcClient()
        self.briefing = BriefingService()
        self._issued_at: datetime | None = None

    @property
    def data_mode(self) -> str:
        return "demo" if settings.effective_demo_mode else "live"

    def _load_sample(self, filename: str) -> list:
        path = Path(settings.data_dir) / filename
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DataSourceError(f"Bundled sample unreadable: {filename}",
                                  detail={"cause": str(exc)}) from exc

    # -------------------------------------------------------- data loading
    def _raw_f107(self):
        if self.data_mode == "demo":
            return self._load_sample("sample_f107.json")
        return self.cache.get_or_fetch("noaa:f107", settings.obs_ttl_seconds,
                                       self.swpc.fetch_f107)

    def _raw_kp(self):
        if self.data_mode == "demo":
            return self._load_sample("sample_kp.json")
        return self.cache.get_or_fetch("noaa:kp", settings.obs_ttl_seconds,
                                       self.swpc.fetch_kp)

    def _raw_noaa45(self):
        if self.data_mode == "demo":
            return self._load_sample("sample_noaa45.json")
        return self.cache.get_or_fetch("noaa:45", settings.forecast_ttl_seconds,
                                       self.swpc.fetch_noaa45)

    # ------------------------------------------------------------ pipeline
    def refresh(self) -> int:
        logger.info("Pipeline refresh starting (mode=%s)", self.data_mode)
        with self.pipeline.stage("swpc_sync") as st:
            try:
                raw_f107 = self._raw_f107()
                raw_kp = self._raw_kp()
                raw_noaa = self._raw_noaa45()
                st["items"] = len(raw_f107) + len(raw_kp)
            except (DataSourceError,) as exc:
                st["status"] = "degraded"
                st["error"] = str(exc)
                logger.warning("SWPC sync degraded: %s", exc)
                raise

        with self.pipeline.stage("history") as st:
            f107 = sr.gap_fill(sr.load_daily_f107(raw_f107))
            max_kp, ap = sr.kp_to_daily(raw_kp)
            max_kp = sr.gap_fill(max_kp)
            ap = sr.gap_fill(ap)
            st["items"] = len(f107)

        lead = settings.max_lead_days
        with self.pipeline.stage("backtest") as st:
            min_train = min(settings.backtest_min_history_days, max(60, len(f107) - lead - 30))
            backtest = cal.walk_forward_errors(f107, lead, min_train=min_train, step=3)
            st["items"] = sum(len(v) for v in backtest.errors.values())

        with self.pipeline.stage("forecast") as st:
            f107_res = ff.forecast(f107, lead, backtest.error_quantiles)
            kp_res = kf.forecast(max_kp, ap, settings.kp_max_lead_days)
            st["items"] = lead

        with self.pipeline.stage("calib") as st:
            coverage = cal.coverage(backtest)
            pinball = cal.pinball_by_lead(backtest)
            skill = cal.skill_vs_reference(backtest)
            kp_rel = self._kp_reliability(max_kp)
            st["items"] = len(coverage)

        with self.pipeline.stage("publish") as st:
            issued = datetime.now(timezone.utc)
            self._issued_at = issued
            docs = self._build_documents(issued, f107, f107_res, kp_res, max_kp,
                                         raw_noaa, coverage, pinball, skill, kp_rel)
            for name, doc in docs.items():
                self.cache.save_snapshot(name, doc)
            st["items"] = len(docs)

        logger.info("Pipeline refresh complete")
        return lead

    # ------------------------------------------------------- read-models
    def _build_documents(self, issued, f107, f107_res, kp_res, max_kp, raw_noaa,
                         coverage, pinball, skill, kp_rel) -> dict:
        start = f107.last_date
        dates = [(start + timedelta(days=i + 1)).isoformat() for i in range(f107_res.lead_days)]

        noaa_by_lead = self._noaa_point(raw_noaa, f107_res.lead_days)
        hist_tail = 180
        f107_doc = {
            "data_mode": self.data_mode,
            "issued_at": issued.isoformat(),
            "lead_days": f107_res.lead_days,
            "dates": dates,
            "point": [round(float(x), 1) for x in f107_res.point],
            "bands": {f"p{q:02d}": [round(float(x), 1) for x in f107_res.bands[q]]
                      for q in (5, 25, 50, 75, 95)},
            "noaa_point": noaa_by_lead,
            "history_dates": [d.isoformat() for d in f107.dates[-hist_tail:]],
            "history_values": [round(float(v), 1) for v in f107.values[-hist_tail:]],
            "unit": "sfu",
            "attribution": _ATTRIBUTION,
        }

        kp_days = []
        for i, (probs, (lo, pt, hi)) in enumerate(zip(kp_res.probs, kp_res.expected_ap)):
            d = start + timedelta(days=i + 1)
            dominant = max(probs, key=probs.get)
            kp_days.append({
                "lead": i + 1, "date": d.isoformat(),
                "probs": {k: round(v, 3) for k, v in probs.items()},
                "expected_ap": {"p05": lo, "p50": pt, "p95": hi},
                "dominant": dominant,
            })
        kp_doc = {
            "data_mode": self.data_mode, "issued_at": issued.isoformat(),
            "days": kp_days, "categories": kf.CATEGORIES, "attribution": _ATTRIBUTION,
        }

        window = min(30, f107_res.lead_days)
        p05 = f107_res.bands[5][:window]
        p50 = f107_res.bands[50][:window]
        p95 = f107_res.bands[95][:window]
        alts = []
        for alt in _ALTITUDES:
            dband = drag.density_band(alt, float(p05[0]), float(p50[0]), float(p95[0]))
            decay = drag.decay_band(alt, p05, p50, p95, window)
            alts.append({
                "alt_km": alt,
                "density_kg_m3": {k: float(v) for k, v in dband.items()},
                "decay_along_track_km": decay,
            })
        drag_doc = {
            "data_mode": self.data_mode, "issued_at": issued.isoformat(),
            "window_days": window, "altitudes": alts, "note": drag.NOTE,
        }

        mean_cov = float(np.mean([c["empirical_90"] for c in coverage])) if coverage else 0.0
        pos_skill = [s["skill"] for s in skill if s["skill"] is not None and s["skill"] > 0]
        calib_doc = {
            "data_mode": self.data_mode, "issued_at": issued.isoformat(),
            "coverage_by_lead": coverage, "pinball_by_lead": pinball,
            "skill_vs_noaa": skill, "kp_reliability": kp_rel,
            "summary": (
                f"90% F10.7 bands achieve {mean_cov:.0%} empirical coverage of out-of-sample "
                f"observations across leads (target 90%). PENUMBRA beats the persistence "
                f"baseline at {len(pos_skill)} of {len(skill)} lead times. Skill is measured "
                f"against a reproducible persistence reference; NOAA's live 45-day forecast is "
                f"overlaid on the forecast chart for direct comparison."
            ),
        }

        obs_doc = {
            "dates": [d.isoformat() for d in f107.dates[-3650:]],
            "values": [round(float(v), 1) for v in f107.values[-3650:]],
            "unit": "sfu",
        }

        summary = {
            "f107": {
                "point_7d": round(float(f107_res.point[6]), 1) if f107_res.lead_days > 6 else None,
                "p05_7d": round(float(f107_res.bands[5][6]), 1) if f107_res.lead_days > 6 else None,
                "p95_7d": round(float(f107_res.bands[95][6]), 1) if f107_res.lead_days > 6 else None,
            },
            "kp_dominant_tomorrow": kp_days[0]["dominant"] if kp_days else "quiet",
            "coverage_90": round(mean_cov, 2),
        }

        return {
            "f107": f107_doc, "kp": kp_doc, "drag": drag_doc,
            "calibration": calib_doc, "observations": obs_doc, "summary": summary,
        }

    def _noaa_point(self, raw_noaa, lead_days) -> list:
        """Extract NOAA's 45-day F10.7 point forecast aligned to lead 1..N."""
        pts: list[float | None] = [None] * lead_days
        for i, row in enumerate(raw_noaa[:lead_days]):
            v = row.get("f10.7", row.get("f107", row.get("flux")))
            try:
                pts[i] = round(float(v), 1)
            except (TypeError, ValueError):
                pts[i] = None
        return pts

    def _kp_reliability(self, max_kp: sr.DailySeries) -> list:
        """In-sample storm reliability: for each day, predict tomorrow's storm
        probability from the categorical model and score against the realised
        outcome. Illustrative reliability diagram for the demo."""
        preds, outs = [], []
        vals = max_kp.values
        n = len(vals)
        if n < 60:
            return []
        for t in range(30, n - 1):
            hist = sr.DailySeries(max_kp.dates[: t + 1], vals[: t + 1])
            p = kf.category_probabilities(hist, 1)[0]["storm"]
            preds.append(p)
            outs.append(1 if kf.category(float(vals[t + 1])) == "storm" else 0)
        return cal.reliability(preds, outs, bins=8)

    # ------------------------------------------------------------- queries
    def _snap(self, name: str) -> dict:
        doc = self.cache.load_snapshot(name)
        if doc is None:
            raise NotFoundError(f"Forecast snapshot '{name}' not available yet")
        return doc

    def f107_forecast(self) -> dict:
        return self._snap("f107")

    def kp_forecast(self) -> dict:
        return self._snap("kp")

    def drag_impact(self) -> dict:
        return self._snap("drag")

    def calibration(self) -> dict:
        return self._snap("calibration")

    def observations(self, days: int) -> dict:
        doc = self._snap("observations")
        if days < len(doc["dates"]):
            doc = {"dates": doc["dates"][-days:], "values": doc["values"][-days:],
                   "unit": doc["unit"]}
        return doc

    def briefing_note(self) -> dict:
        summary = self.cache.load_snapshot("summary") or {}
        text, source = self.briefing.briefing(summary)
        return {"briefing": text, "source": source}
