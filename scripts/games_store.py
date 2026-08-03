"""
data/games.json is the single source of truth for the whole pipeline. Each game
moves through three states as the daily job runs:

  scheduled -> predicted -> graded

  { "<game_id>": {
       "league": "NFL", "home_team": ..., "away_team": ..., "commence_time": ...,
       "status": "scheduled" | "predicted" | "graded",
       "odds": { ...consensus line captured when first seen... },
       "prediction": { ... filled in by generate_predictions.py ... } | null,
       "actual": { ... filled in by fetch_results.py ... } | null
  }, ... }
"""
from utils import DATA_DIR, read_json, write_json

GAMES_PATH = DATA_DIR / "games.json"


def load_games():
    return read_json(GAMES_PATH, default={})


def save_games(games):
    write_json(GAMES_PATH, games)


def upsert_scheduled(games, game):
    """Adds a newly-seen game, or refreshes its odds if we've already seen it but
    haven't generated a prediction yet (lines move as game time approaches)."""
    existing = games.get(game["id"])
    if existing is None:
        games[game["id"]] = {
            "league": game["league"],
            "sport_key": game["sport_key"],
            "home_team": game["home_team"],
            "away_team": game["away_team"],
            "commence_time": game["commence_time"],
            "espn_sport": game.get("espn_sport"),
            "espn_league": game.get("espn_league"),
            "outdoor": game.get("outdoor", False),
            "status": "scheduled",
            "odds": game["lines"],
            "prediction": None,
            "actual": None,
        }
    elif existing["status"] == "scheduled":
        existing["odds"] = game["lines"]
    return games
