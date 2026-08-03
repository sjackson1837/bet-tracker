"""
One-off helper: prints every sport key The Odds API currently supports, so you can
verify the keys in config/leagues.json are still valid (they occasionally rename
or add/remove leagues). Run with: python scripts/list_sports.py
"""
import requests

from utils import get_env

resp = requests.get(
    "https://api.the-odds-api.com/v4/sports",
    params={"apiKey": get_env("ODDS_API_KEY")},
    timeout=30,
)
resp.raise_for_status()
for s in resp.json():
    print(f"{s['key']:35s} {s['title']} ({s['group']})")
