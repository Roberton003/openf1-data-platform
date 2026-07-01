from __future__ import annotations

import os
from pathlib import Path


DEFAULT_DRIVERS: dict[int, str] = {
    1: "Max Verstappen",
    4: "Lando Norris",
    16: "Charles Leclerc",
    44: "Lewis Hamilton",
    63: "George Russell",
    81: "Oscar Piastri",
}


def _load_dotenv_local() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    env_path = repo_root / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ[key.strip()] = value.strip().strip('"').strip("'")


def parse_focus_drivers(raw_value: str | None = None) -> dict[int, str]:
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
                driver_number, name = item.split(":", 1)
                parsed[int(driver_number.strip())] = name.strip()
            else:
                number = int(item)
                parsed[number] = f"Driver {number}"
    except Exception:
        return dict(DEFAULT_DRIVERS)

    return parsed or dict(DEFAULT_DRIVERS)


def get_focus_drivers(raw_value: str | None = None) -> dict[int, str]:
    return parse_focus_drivers(raw_value)


_load_dotenv_local()
PILOTOS_FOCO = get_focus_drivers()
