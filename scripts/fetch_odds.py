"""
Pulls upcoming games + betting lines from The Odds API (https://the-odds-api.com)
for every league listed in config/leagues.json, and writes a consolidated file to
data/upcoming/<date>.json.

Requires env var: ODDS_API_KEY
"""
import sys
from statistics import mean

import requests

from utils import load_config, write_json, today_str, get_env, game_id, DATA_DIR
from games_store import load_games, save_games, upsert_scheduled

BASE_URL = "https://api.the-odds-api.com/v4/sports/{sport}/odds"


def consensus_line(bookmakers):
    """Average moneyline/spread/total across all reporting bookmakers so one
    sportsbook's outlier line doesn't skew the prediction."""
    h2h_prices = {}   # team -> list of prices
    spreads = {}       # team -> list of points
    totals = []

    for bm in bookmakers:
        for market in bm.get("markets", []):
            if market["key"] == "h2h":
                for o in market["outcomes"]:
                    h2h_prices.setdefault(o["name"], []).append(o["price"])
            elif market["key"] == "spreads":
                for o in market["outcomes"]:
                    spreads.setdefault(o["name"], []).append(o["point"])
            elif market["key"] == "totals":
                for o in market["outcomes"]:
                    if o["name"].lower() == "over":
                        totals.append(o["point"])

    return {
        "moneyline": {team: round(mean(prices)) for team, prices in h2h_prices.items()},
        "spread": {team: round(mean(pts), 1) for team, pts in spreads.items()},
        "total": round(mean(totals), 1) if totals else None,
        "num_bookmakers": len(bookmakers),
    }


def fetch_league(league, api_key):
    params = {
        "apiKey": api_key,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american",
        "dateFormat": "iso",
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
            "lines": consensus_line(g.get("bookmakers", [])),
        })

    remaining = resp.headers.get("x-requests-remaining")
    print(f"  {league['name']}: {len(games)} upcoming games (API requests remaining: {remaining})")
    return games


def main():
    config = load_config()
    api_key = get_env("ODDS_API_KEY")

    all_games = []
    print("Fetching odds...")
    for league in config["leagues"]:
        all_games.extend(fetch_league(league, api_key))

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
