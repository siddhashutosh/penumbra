"""Optional Claude space-weather analyst briefing (graceful fallback).

Uses the official Anthropic SDK when PENUMBRA_ANTHROPIC_API_KEY is set; otherwise
(or on any failure) returns a deterministic template. Never raises to caller.
"""
from __future__ import annotations

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

_MODEL = "claude-opus-4-8"
_TIMEOUT_S = 10.0

_SYSTEM = (
    "You are PENUMBRA's space-weather analyst. Given a current forecast summary "
    "as JSON (F10.7 point + p05/p95 band at select leads, dominant Kp categories, "
    "and calibration coverage/skill), write a 2-4 sentence operator note: how "
    "settled or active the Sun is, how wide the F10.7 uncertainty is and what that "
    "implies for orbit-drag prediction, and whether the bands are well-calibrated. "
    "Plain prose, no markdown, no preamble."
)


def _template(summary: dict) -> str:
    f = summary.get("f107", {})
    p50 = f.get("point_7d")
    lo = f.get("p05_7d")
    hi = f.get("p95_7d")
    kp = summary.get("kp_dominant_tomorrow", "quiet")
    cov = summary.get("coverage_90")
    band = ""
    if lo is not None and hi is not None:
        band = f" The 7-day F10.7 range is {lo:.0f}–{hi:.0f} sfu"
        if p50 is not None:
            band += f" around {p50:.0f}"
        band += "."
    cov_note = ""
    if cov is not None:
        cov_note = (f" The 90% bands are empirically calibrated at {cov:.0%} coverage, "
                    "so the stated uncertainty is trustworthy.")
    return (
        f"Geomagnetic conditions are forecast {kp} in the near term.{band}"
        f" Wider F10.7 bands translate directly into larger orbit-drag and "
        f"along-track position uncertainty for low-altitude satellites.{cov_note}"
    )


class BriefingService:
    def __init__(self) -> None:
        self._client = None
        if settings.anthropic_api_key:
            try:
                import anthropic

                self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
                logger.info("BriefingService: AI briefings enabled (%s)", _MODEL)
            except Exception as exc:
                logger.warning("BriefingService: AI unavailable (%s); using templates", exc)
        else:
            logger.info("BriefingService: no API key; using template briefings")

    def briefing(self, summary: dict) -> tuple[str, str]:
        if self._client is None:
            return _template(summary), "template"
        try:
            import json

            import anthropic

            response = self._client.with_options(timeout=_TIMEOUT_S).messages.create(
                model=_MODEL,
                max_tokens=400,
                thinking={"type": "adaptive"},
                system=_SYSTEM,
                messages=[{"role": "user", "content": json.dumps(summary, default=str)}],
            )
            text = next((b.text for b in response.content if b.type == "text"), "").strip()
            if not text:
                raise ValueError("empty AI response")
            return text, "ai"
        except anthropic.RateLimitError:
            logger.warning("BriefingService: rate limited; template fallback")
        except anthropic.APIStatusError as exc:
            logger.warning("BriefingService: API %s; template fallback", exc.status_code)
        except Exception as exc:
            logger.warning("BriefingService: %s; template fallback", exc)
        return _template(summary), "template"
