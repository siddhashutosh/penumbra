"""Force Demo Mode for the whole suite — deterministic, never hits NOAA live."""
import os

os.environ["PENUMBRA_DEMO_MODE"] = "true"
