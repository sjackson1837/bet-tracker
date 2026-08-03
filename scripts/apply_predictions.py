"""
Step 2 of 2 in the free/manual prediction flow. Reads data/my_predictions.json
(written by Claude after reasoning through data/pending_predictions.json) and merges
each pick into data/games.json, moving those games from "scheduled" to "predicted".

Expected shape of data/my_predictions.json:
{
  "<game_id>": {
    "predicted_winner": "...",
    "predicted_against_spread": "...",
    "confidence": 1-100,
    "key_factors": ["...", "..."],
    "reasoning": "..."
  },
  ...
}

No API key required.
"""
import json
from datetime import datetime, timezone

from utils import DATA_DIR
from games_store import load_games, save_games

IN_PATH = DATA_DIR / "my_predictions.json"
PENDING_PATH = DATA_DIR / "pending_predictions.json"

REQUIRED_FIELDS = {"predicted_winner", "predicted_against_spread", "confidence", "key_factors", "reasoning"}


def main():
    if not IN_PATH.exists():
        print(f"No {IN_PATH} found. Run prepare_predictions.py first, then have Claude write "
              f"picks to that file before running this script.")
        return

    with open(IN_PATH) as f:
        my_predictions = json.load(f)

    pending_context = {}
    if PENDING_PATH.exists():
        with open(PENDING_PATH) as f:
            pending_context = json.load(f).get("games", {})

    games = load_games()
    now = datetime.now(timezone.utc)
    applied = 0

    for gid, prediction in my_predictions.items():
        if gid not in games:
            print(f"  ! skipping {gid}: not found in games.json")
            continue
        missing = REQUIRED_FIELDS - prediction.keys()
        if missing:
            print(f"  ! skipping {gid}: missing fields {missing}")
            continue

        game = games[gid]
        if game["status"] == "graded":
            print(f"  ! skipping {gid}: already graded, won't overwrite with a stale prediction")
            continue
        context = pending_context.get(gid, {})
        prediction = dict(prediction)  # don't mutate input
        prediction["context_used"] = {
            "away_trends": context.get("away_team_trends"),
            "home_trends": context.get("home_team_trends"),
            "weather": context.get("weather_at_kickoff"),
        }
        prediction["generated_at"] = now.isoformat()
        prediction["model"] = "claude (cowork session, manual)"
        prediction["line_at_prediction"] = game["odds"]

        game["prediction"] = prediction
        game["status"] = "predicted"
        applied += 1
        print(f"  {game['away_team']} @ {game['home_team']}: picked {prediction['predicted_winner']} "
              f"({prediction['confidence']}% confidence)")

    save_games(games)
    print(f"Applied {applied} predictions to games.json")


if __name__ == "__main__":
    main()
