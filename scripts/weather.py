"""
Game-day weather via Open-Meteo (https://open-meteo.com) — free, no API key required.
Only returns data for outdoor stadiums we have coordinates for (see config/stadiums.json).
Indoor/domed venues and unknown venues are skipped gracefully (returns None) rather
than breaking the pipeline.
"""
import requests

from utils import ROOT, read_json

STADIUMS_PATH = ROOT / "config" / "stadiums.json"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def get_game_weather(home_team, game_date):
    """game_date should be 'YYYY-MM-DD'. Returns a short dict or None."""
    stadiums = read_json(STADIUMS_PATH, default={}).get("teams", {})
    info = stadiums.get(home_team)
    if not info or info.get("indoor"):
        return None

    params = {
        "latitude": info["lat"],
        "longitude": info["lon"],
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max",
        "temperature_unit": "fahrenheit",
        "windspeed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": "auto",
        "start_date": game_date,
        "end_date": game_date,
    }
    try:
        resp = requests.get(FORECAST_URL, params=params, timeout=15)
        resp.raise_for_status()
        daily = resp.json().get("daily", {})
        if not daily.get("time"):
            return None
        return {
            "high_f": daily["temperature_2m_max"][0],
            "low_f": daily["temperature_2m_min"][0],
            "precipitation_in": daily["precipitation_sum"][0],
            "wind_mph": daily["windspeed_10m_max"][0],
        }
    except Exception as e:
        print(f"    ! weather lookup failed for {home_team}: {e}")
        return None
