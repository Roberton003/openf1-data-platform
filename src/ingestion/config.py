# Centralized Ingestion Configurations for OpenF1 Data Platform
from __future__ import annotations

import os


# Helper to load .env variables locally for standalone ingestion scripts
def _load_dotenv_local() -> None:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    env_path = os.path.join(base_dir, ".env")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    os.environ[key] = val


_load_dotenv_local()

# Grid of focus drivers for detailed spatial and telemetry analysis (2025 season)
# Can be configured via environment variable "FOCUS_DRIVERS" as a comma-separated list of "number:name"
# Example in .env: FOCUS_DRIVERS="1:Max Verstappen,4:Lando Norris,16:Charles Leclerc"
# Default: Top-6 drivers from top-4 constructors (RBR, McLaren, Ferrari, Mercedes)
DEFAULT_DRIVERS: dict[int, str] = {
    1: "Max Verstappen",
    4: "Lando Norris",
    16: "Charles Leclerc",
    44: "Lewis Hamilton",
    63: "George Russell",
    81: "Oscar Piastri",
}


def parse_focus_drivers(raw_value: str | None = None) -> dict[int, str]:
    """Parse a comma-separated driver spec into a stable mapping."""
    focus_drivers_env = raw_value if raw_value is not None else os.getenv("FOCUS_DRIVERS")
    if not focus_drivers_env:
        return dict(DEFAULT_DRIVERS)

    parsed: dict[int, str] = {}
    try:
        for item in focus_drivers_env.split(","):
            item = item.strip()
            if not item:
                continue
            if ":" in item:
                num_str, name = item.split(":", 1)
                parsed[int(num_str.strip())] = name.strip()
            else:
                num = int(item.strip())
                parsed[num] = f"Driver {num}"
    except Exception:
        return dict(DEFAULT_DRIVERS)

    return parsed or dict(DEFAULT_DRIVERS)


def get_focus_drivers(raw_value: str | None = None) -> dict[int, str]:
    return parse_focus_drivers(raw_value)


PILOTOS_FOCO = get_focus_drivers()
