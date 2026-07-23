// TS mirrors of the backend Pydantic DTOs (PEN-LLD-001 §5).

export interface F107Bands {
  p05: number[];
  p25: number[];
  p50: number[];
  p75: number[];
  p95: number[];
}

export interface F107Forecast {
  data_mode: "live" | "demo";
  issued_at: string;
  lead_days: number;
  dates: string[];
  point: number[];
  bands: F107Bands;
  noaa_point: (number | null)[];
  history_dates: string[];
  history_values: number[];
  unit: string;
  attribution: string;
}

export interface ApBand {
  p05: number;
  p50: number;
  p95: number;
}

export interface KpDay {
  lead: number;
  date: string;
  probs: Record<string, number>;
  expected_ap: ApBand;
  dominant: string;
}

export interface KpForecast {
  data_mode: "live" | "demo";
  issued_at: string;
  days: KpDay[];
  categories: string[];
  attribution: string;
}

export interface DragAltitude {
  alt_km: number;
  density_kg_m3: { p05: number; p50: number; p95: number };
  decay_along_track_km: { p05: number; p50: number; p95: number };
}

export interface DragImpact {
  data_mode: "live" | "demo";
  issued_at: string;
  window_days: number;
  altitudes: DragAltitude[];
  note: string;
}

export interface CoveragePoint {
  lead: number;
  target_90: number;
  empirical_90: number;
  empirical_50: number;
}

export interface SkillPoint {
  lead: number;
  penumbra_rmse: number;
  baseline_rmse: number | null;
  skill: number | null;
}

export interface ReliabilityBin {
  predicted: number;
  observed: number;
  count: number;
}

export interface CalibrationReport {
  data_mode: "live" | "demo";
  issued_at: string;
  coverage_by_lead: CoveragePoint[];
  pinball_by_lead: number[];
  skill_vs_noaa: SkillPoint[];
  kp_reliability: ReliabilityBin[];
  summary: string;
}

export interface Briefing {
  briefing: string;
  source: "ai" | "template";
}

export interface PipelineAgent {
  id: string;
  name: string;
  status: "idle" | "running" | "ok" | "degraded" | "error";
  last_run: string | null;
  duration_ms: number | null;
  items: number;
  error: string | null;
}

export interface PipelineStatus {
  data_mode: "live" | "demo";
  agents: PipelineAgent[];
}

export interface Health {
  status: string;
  version: string;
  data_mode: "live" | "demo";
  uptime_s: number;
}
