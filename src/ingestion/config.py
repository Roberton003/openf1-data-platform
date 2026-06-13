# Centralized Ingestion Configurations for OpenF1 Data Platform
import os


# Helper to load .env variables locally for standalone ingestion scripts
def _load_dotenv_local() -> None:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    env_path = os.path.join(base_dir, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
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
DEFAULT_DRIVERS = {
    1: "Max Verstappen",
    4: "Lando Norris",
    16: "Charles Leclerc",
    44: "Lewis Hamilton",
    63: "George Russell",
    81: "Oscar Piastri",
}

focus_drivers_env = os.getenv("FOCUS_DRIVERS")

if focus_drivers_env:
    PILOTOS_FOCO = {}
    try:
        for item in focus_drivers_env.split(","):
            if ":" in item:
                num_str, name = item.split(":", 1)
                PILOTOS_FOCO[int(num_str.strip())] = name.strip()
            else:
                num = int(item.strip())
                PILOTOS_FOCO[num] = f"Driver {num}"
    except Exception:
        PILOTOS_FOCO = DEFAULT_DRIVERS
else:
    PILOTOS_FOCO = DEFAULT_DRIVERS
