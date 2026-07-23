"""NOAA SWPC data client — keyless, cache-first friendly (FR-ING-1..3)."""
from __future__ import annotations

import logging
import time

import httpx

from app.core.exceptions import DataSourceError

logger = logging.getLogger(__name__)

_BASE = "https://services.swpc.noaa.gov"
_TIMEOUT = 30.0
_RETRIES = 2

_ENDPOINTS = {
    "f107": "/json/f107_cm_flux.json",
    "kp": "/products/noaa-planetary-k-index.json",
    "noaa45": "/json/45-day-forecast.json",
    "history": "/json/solar-cycle/observed-solar-cycle-indices.json",
}


class SwpcClient:
    def _get(self, path: str) -> list:
        last: Exception | None = None
        for attempt in range(_RETRIES + 1):
            try:
                with httpx.Client(timeout=_TIMEOUT, follow_redirects=True) as client:
                    resp = client.get(_BASE + path)
                    resp.raise_for_status()
                    data = resp.json()
                if not isinstance(data, list):
                    raise DataSourceError(
                        "NOAA returned unexpected payload shape",
                        detail={"path": path, "type": type(data).__name__},
                    )
                return data
            except (httpx.HTTPError, ValueError) as exc:
                last = exc
                logger.warning("NOAA fetch %d/%d failed (%s): %s",
                               attempt + 1, _RETRIES + 1, path, exc)
                if attempt < _RETRIES:
                    time.sleep(1.5 * (attempt + 1))
        raise DataSourceError(f"NOAA fetch failed ({path})",
                              detail={"cause": str(last)}) from last

    def fetch_f107(self) -> list:
        rows = self._get(_ENDPOINTS["f107"])
        logger.info("NOAA: fetched %d F10.7 rows", len(rows))
        return rows

    def fetch_kp(self) -> list:
        rows = self._get(_ENDPOINTS["kp"])
        logger.info("NOAA: fetched %d Kp rows", len(rows))
        return rows

    def fetch_noaa45(self) -> list:
        rows = self._get(_ENDPOINTS["noaa45"])
        logger.info("NOAA: fetched %d 45-day forecast rows", len(rows))
        return rows

    def fetch_history(self) -> list:
        rows = self._get(_ENDPOINTS["history"])
        logger.info("NOAA: fetched %d long-history rows", len(rows))
        return rows
