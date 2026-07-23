"""PENUMBRA runtime configuration (env-driven, .env supported)."""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PENUMBRA_",
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "PENUMBRA"
    version: str = "1.0.0"

    # None -> auto: demo unless PENUMBRA_LIVE is truthy
    demo_mode: bool | None = None
    live: bool = False
    anthropic_api_key: str | None = None

    data_dir: Path = BACKEND_DIR / "app" / "data"
    log_dir: Path = BACKEND_DIR / "logs"

    # CON-4: cache-first, polite intervals
    obs_ttl_seconds: int = 10800        # 3 h
    forecast_ttl_seconds: int = 21600   # 6 h
    pipeline_refresh_seconds: int = 10800

    max_lead_days: int = 45
    kp_max_lead_days: int = 7
    f107_floor_sfu: float = 64.0        # quiet-Sun minimum (FR-F107-3)
    backtest_min_history_days: int = 400

    @property
    def effective_demo_mode(self) -> bool:
        if self.demo_mode is not None:
            return self.demo_mode
        return not self.live


settings = Settings()
