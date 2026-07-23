"""Typed exception hierarchy — the only errors allowed to cross layer boundaries.

Boundary rule (HLD §5): logic raises, service contextualises/falls back,
API converts to the JSON error envelope.
"""
from __future__ import annotations

from typing import Any


class PenumbraError(Exception):
    code = "PENUMBRA_ERROR"
    http_status = 500

    def __init__(self, message: str, detail: Any = None):
        super().__init__(message)
        self.message = message
        self.detail = detail

    def envelope(self, request_id: str = "-") -> dict:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "detail": self.detail,
                "request_id": request_id,
            }
        }


class ConfigError(PenumbraError):
    code = "CONFIG_ERROR"
    http_status = 500


class DataSourceError(PenumbraError):
    code = "DATA_SOURCE_ERROR"
    http_status = 502


class InsufficientDataError(PenumbraError):
    code = "INSUFFICIENT_DATA"
    http_status = 422


class ForecastError(PenumbraError):
    code = "FORECAST_ERROR"
    http_status = 500


class NotFoundError(PenumbraError):
    code = "NOT_FOUND"
    http_status = 404


class ValidationFailure(PenumbraError):
    code = "VALIDATION_ERROR"
    http_status = 422
