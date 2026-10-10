"""
Pulls upcoming games + betting lines from The Odds API (https://the-odds-api.com)
for every league listed in config/leagues.json, and writes a consolidated file to
data/upcoming/<date>.json.

Requires env var: ODDS_API_KEY
"""
import sys

import requests

from utils import load_config, write_json, today_str, get_env, game_id, DATA_DIR
from games_store import load_games, save_games, upsert_scheduled

BASE_URL = "https://api.the-odds-api.com/v4/sports/{sport}/odds"

DEFAULT_BOOKMAKER = "draftkings"


def single_book_line(bookmakers, preferred_key):
    """Pull moneyline/spread/total from one specific sportsbook rather than
    averaging across every book reporting -- so the line shown matches what
    you'd actually see at that book. Falls back to whichever book The Odds API
    did return if the preferred one isn't reporting for this game."""
    bm = next((b for b in bookmakers if b["key"] == preferred_key), None)
    if bm is None and bookmakers:
        bm = bookmakers[0]
    if bm is None:
        return {"moneyline": {}, "spread": {}, "total": None, "bookmaker": None}

    moneyline = {}
    spread = {}
    total = None
    for market in bm.get("markets", []):
        if market["key"] == "h2h":
            for o in market["outcomes"]:
                moneyline[o["name"]] = round(o["price"])
        elif market["key"] == "spreads":
            for o in market["outcomes"]:
                spread[o["name"]] = o["point"]
        elif market["key"] == "totals":
            for o in market["outcomes"]:
                if o["name"].lower() == "over":
                    total = o["point"]

    return {
        "moneyline": moneyline,
        "spread": spread,
        "total": total,
        "bookmaker": bm.get("title", bm["key"]),
    }


def fetch_league(league, api_key, preferred_bookmaker):
    params = {
        "apiKey": api_key,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american",
        "dateFormat": "iso",
        "bookmakers": preferred_bookmaker,
    }
    resp = requests.get(BASE_URL.format(sport=league["odds_api_key"]), params=params, timeout=30)
    if resp.status_code != 200:
        print(f"  ! {league['name']}: HTTP {resp.status_code} - {resp.text[:200]}", file=sys.stderr)
        return []

    games = []
    for g in resp.json():
        games.append({
            "id": game_id(league["odds_api_key"], g["commence_time"], g["home_team"], g["away_team"]),
            "sport_key": league["odds_api_key"],
            "league": league["name"],
            "outdoor": league.get("outdoor", False),
            "espn_sport": league.get("espn_sport"),
            "espn_league": league.get("espn_league"),
            "commence_time": g["commence_time"],
            "home_team": g["home_team"],
            "away_team": g["away_team"],
            "lines": single_book_line(g.get("bookmakers", []), preferred_bookmaker),
        })

    remaining = resp.headers.get("x-requests-remaining")
    print(f"  {league['name']}: {len(games)} upcoming games (API requests remaining: {remaining})")
    return games


def main():
    config = load_config()
    api_key = get_env("ODDS_API_KEY")
    preferred_bookmaker = config.get("settings", {}).get("preferred_bookmaker", DEFAULT_BOOKMAKER)

    all_games = []
    print(f"Fetching odds from {preferred_bookmaker}...")
    for league in config["leagues"]:
        all_games.extend(fetch_league(league, api_key, preferred_bookmaker))

    # Keep a raw dated snapshot for debugging/audit purposes.
    out_path = DATA_DIR / "upcoming" / f"{today_str()}.json"
    write_json(out_path, {"fetched_at": today_str(), "games": all_games})

    # Upsert into the master games store that drives the rest of the pipeline.
    games = load_games()
    for g in all_games:
        upsert_scheduled(games, g)
    save_games(games)

    print(f"Wrote {len(all_games)} games to {out_path}")
    print(f"games.json now tracking {len(games)} total games")


if __name__ == "__main__":
    main()
