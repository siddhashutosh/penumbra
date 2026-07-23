"""API contract tests via TestClient (FR-API)."""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:  # runs lifespan (demo pipeline refresh)
        yield c


class TestHealth:
    def test_health(self, client):
        r = client.get("/api/v1/health")
        assert r.status_code == 200
        assert r.json()["data_mode"] == "demo"


class TestF107:
    def test_forecast_contract_and_monotonicity(self, client):
        r = client.get("/api/v1/forecast/f107")
        assert r.status_code == 200
        b = r.json()
        assert b["lead_days"] == 45
        assert len(b["point"]) == 45
        assert "X-Request-Id" in r.headers
        # band monotonicity per lead
        for i in range(45):
            row = [b["bands"][q][i] for q in ("p05", "p25", "p50", "p75", "p95")]
            assert row == sorted(row)
        # floor
        assert all(v >= 64.0 for v in b["bands"]["p05"])
        # NOAA overlay present
        assert len(b["noaa_point"]) == 45


class TestKp:
    def test_kp_forecast(self, client):
        r = client.get("/api/v1/forecast/kp")
        assert r.status_code == 200
        b = r.json()
        assert len(b["days"]) == 7
        for day in b["days"]:
            # displayed probs are rounded to 3 dp; tolerate rounding drift
            assert abs(sum(day["probs"].values()) - 1.0) < 0.01
            assert day["dominant"] in b["categories"]


class TestDragAndCalibration:
    def test_drag(self, client):
        r = client.get("/api/v1/forecast/drag")
        assert r.status_code == 200
        b = r.json()
        assert len(b["altitudes"]) == 3
        # lower altitude -> more decay
        by_alt = {a["alt_km"]: a["decay_along_track_km"]["p50"] for a in b["altitudes"]}
        assert by_alt[400.0] > by_alt[800.0]
        assert "reduced" in b["note"].lower()

    def test_calibration(self, client):
        r = client.get("/api/v1/calibration")
        assert r.status_code == 200
        b = r.json()
        assert len(b["coverage_by_lead"]) > 0
        assert len(b["skill_vs_noaa"]) > 0
        assert "coverage" in b["summary"].lower()


class TestMisc:
    def test_observations(self, client):
        r = client.get("/api/v1/observations/f107?days=180")
        assert r.status_code == 200
        assert len(r.json()["values"]) <= 180

    def test_briefing(self, client):
        r = client.get("/api/v1/briefing")
        assert r.status_code == 200
        assert r.json()["source"] in ("ai", "template")
        assert len(r.json()["briefing"]) > 40

    def test_pipeline_status(self, client):
        r = client.get("/api/v1/pipeline/status")
        assert r.status_code == 200
        ids = {a["id"] for a in r.json()["agents"]}
        assert {"swpc_sync", "history", "backtest", "forecast", "calib", "publish"} <= ids

    def test_validation_envelope(self, client):
        r = client.get("/api/v1/observations/f107?days=5")  # below ge=30
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "VALIDATION_ERROR"

    def test_unknown_route_404(self, client):
        r = client.get("/api/v1/nope")
        assert r.status_code == 404
