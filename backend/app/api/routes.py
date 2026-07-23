"""REST API (FR-API). Errors surface via the global handlers in main.py."""
from __future__ import annotations

import time

from fastapi import APIRouter, BackgroundTasks, Query, Request

from app.core.config import settings
from app.models.schemas import (
    Briefing,
    CalibrationReport,
    DragImpact,
    F107Forecast,
    Health,
    KpForecast,
    ObservationSeries,
    PipelineStatus,
)

router = APIRouter(prefix="/api/v1")
_START = time.monotonic()


def _svc(request: Request):
    return request.app.state.forecasts


@router.get("/health", response_model=Health)
def health(request: Request):
    return {"status": "ok", "version": settings.version,
            "data_mode": _svc(request).data_mode,
            "uptime_s": round(time.monotonic() - _START, 1)}


@router.get("/forecast/f107", response_model=F107Forecast)
def forecast_f107(request: Request):
    return _svc(request).f107_forecast()


@router.get("/forecast/kp", response_model=KpForecast)
def forecast_kp(request: Request):
    return _svc(request).kp_forecast()


@router.get("/forecast/drag", response_model=DragImpact)
def forecast_drag(request: Request):
    return _svc(request).drag_impact()


@router.get("/calibration", response_model=CalibrationReport)
def calibration(request: Request):
    return _svc(request).calibration()


@router.get("/observations/f107", response_model=ObservationSeries)
def observations_f107(request: Request, days: int = Query(default=730, ge=30, le=3650)):
    return _svc(request).observations(days)


@router.get("/briefing", response_model=Briefing)
def briefing(request: Request):
    return _svc(request).briefing_note()


@router.get("/pipeline/status", response_model=PipelineStatus)
def pipeline_status(request: Request):
    svc = _svc(request)
    return {"data_mode": svc.data_mode, "agents": svc.pipeline.status()}


@router.post("/pipeline/refresh")
def pipeline_refresh(request: Request, background: BackgroundTasks):
    background.add_task(_svc(request).refresh)
    return {"status": "scheduled"}
