"""Pydantic v2 DTOs — the API contract (mirrored by ui/src/types.ts)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

DataMode = Literal["live", "demo"]


class F107Bands(BaseModel):
    p05: list[float]
    p25: list[float]
    p50: list[float]
    p75: list[float]
    p95: list[float]


class F107Forecast(BaseModel):
    data_mode: DataMode
    issued_at: datetime
    lead_days: int
    dates: list[date]
    point: list[float]
    bands: F107Bands
    noaa_point: list[float | None]
    history_dates: list[date]
    history_values: list[float]
    unit: str = "sfu"
    attribution: str


class ApBand(BaseModel):
    p05: float
    p50: float
    p95: float


class KpDay(BaseModel):
    lead: int
    date: date
    probs: dict[str, float]  # quiet/unsettled/active/storm
    expected_ap: ApBand
    dominant: str


class KpForecast(BaseModel):
    data_mode: DataMode
    issued_at: datetime
    days: list[KpDay]
    categories: list[str]
    attribution: str


class DensityBand(BaseModel):
    p05: float
    p50: float
    p95: float


class DragAltitude(BaseModel):
    alt_km: float
    density_kg_m3: DensityBand
    decay_along_track_km: DensityBand


class DragImpact(BaseModel):
    data_mode: DataMode
    issued_at: datetime
    window_days: int
    altitudes: list[DragAltitude]
    note: str


class CoveragePoint(BaseModel):
    lead: int
    target_90: float
    empirical_90: float
    empirical_50: float


class SkillPoint(BaseModel):
    lead: int
    penumbra_rmse: float
    baseline_rmse: float | None
    skill: float | None


class ReliabilityBin(BaseModel):
    predicted: float
    observed: float
    count: int


class CalibrationReport(BaseModel):
    data_mode: DataMode
    issued_at: datetime
    coverage_by_lead: list[CoveragePoint]
    pinball_by_lead: list[float]
    skill_vs_noaa: list[SkillPoint]
    kp_reliability: list[ReliabilityBin]
    summary: str


class ObservationSeries(BaseModel):
    dates: list[date]
    values: list[float]
    unit: str


class Briefing(BaseModel):
    briefing: str
    source: Literal["ai", "template"]


class PipelineAgent(BaseModel):
    id: str
    name: str
    status: Literal["idle", "running", "ok", "degraded", "error"]
    last_run: datetime | None = None
    duration_ms: int | None = None
    items: int = 0
    error: str | None = None


class PipelineStatus(BaseModel):
    data_mode: DataMode
    agents: list[PipelineAgent]


class Health(BaseModel):
    status: str
    version: str
    data_mode: DataMode
    uptime_s: float
