"""Shared helpers used by every script in the pipeline."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "leagues.json"
DATA_DIR = ROOT / "data"
SITE_DIR = ROOT / "site"
ENV_PATH = ROOT / ".env"


def _load_dotenv():
    """Minimal .env loader (no extra dependency) so you only have to enter your
    free Odds API key once instead of exporting it every session."""
    if not ENV_PATH.exists():
        return
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip().strip('"').strip("'")
            os.environ.setdefault(key, val)


_load_dotenv()


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def today_str():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def read_json(path, default=None):
    path = Path(path)
    if not path.exists():
        return default if default is not None else {}
    with open(path) as f:
        return json.load(f)


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def get_env(name, required=True):
    val = os.environ.get(name)
    if required and not val:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            f"Add it to the .env file in the project root (see .env.example)."
        )
    return val


def game_id(sport_key, commence_time, home_team, away_team):
    """Stable ID for a game so we don't double-predict or double-grade it."""
    safe = lambda s: s.lower().replace(" ", "-")
    date_part = commence_time[:10] if commence_time else "unknown"
    return f"{sport_key}_{date_part}_{safe(away_team)}_at_{safe(home_team)}"
