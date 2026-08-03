"""
For every game in data/games.json that's still "scheduled" (has odds, no prediction
yet), gathers trend context (recent form, streaks, head-to-head, weather) and writes
it to data/pending_predictions.json.

This is step 1 of 2 in the free/manual prediction flow: instead of paying for API
access to have a script call Claude in the background, you ask Claude directly (in
this Cowork session) to read this file, reason through each game the same way an
automated prompt would, and write its picks to data/my_predictions.json. Then run
apply_predictions.py to merge those picks back into games.json.

No API key required — this script only touches the free ESPN/Open-Meteo data.
"""
import json
from datetime import datetime, timezone, timedelta

from utils import DATA_DIR, load_config
from games_store import load_games
from form import get_team_trends
from weather import get_game_weather

OUT_PATH = DATA_DIR / "pending_predictions.json"

INSTRUCTIONS = (
    "For each game below, act as a sharp, disciplined sports betting analyst. Do NOT simply "
    "pick whichever side the betting market favors -- weigh the actual trend data provided "
    "(recent form, streaks, head-to-head history, and weather where relevant) and form an "
    "independent judgment. It's fine, and expected, to disagree with the market when the "
    "trends support it. If trend data is sparse for a game, say so and let that lower your "
    "confidence rather than defaulting to the favorite. For each game_id, produce: "
    "predicted_winner (exact team name), predicted_against_spread (exact team name), "
    "confidence (integer 1-100), key_factors (2-4 short strings), and reasoning "
    "(2-4 sentences referencing the specific trend data given)."
)


def build_context(game):
    away_trends = get_team_trends(game.get("espn_sport"), game.get("espn_league"),
                                   game["away_team"], opponent_name=game["home_team"])
    home_trends = get_team_trends(game.get("espn_sport"), game.get("espn_league"),
                                   game["home_team"], opponent_name=game["away_team"])
    weather = None
    if game.get("outdoor"):
        weather = get_game_weather(game["home_team"], game["commence_time"][:10])
    return away_trends, home_trends, weather


def main():
    games = load_games()
    now = datetime.now(timezone.utc)
    window_days = load_config()["settings"].get("days_of_upcoming_odds", 3)
    cutoff = now + timedelta(days=window_days)

    pending = {}
    skipped_far_out = 0
    for gid, game in games.items():
        if game["status"] != "scheduled":
            continue
        commence = datetime.fromisoformat(game["commence_time"].replace("Z", "+00:00"))
        if commence < now:
            continue  # already started/passed, don't bother
        if commence > cutoff:
            skipped_far_out += 1
            continue  # too far out — lines will move a lot before kickoff, predict closer to game time

        away_trends, home_trends, weather = build_context(game)
        pending[gid] = {
            "league": game["league"],
            "away_team": game["away_team"],
            "home_team": game["home_team"],
            "commence_time": game["commence_time"],
            "market_line": game["odds"],
            "away_team_trends": away_trends,
            "home_team_trends": home_trends,
            "weather_at_kickoff": weather,
        }

    with open(OUT_PATH, "w") as f:
        json.dump({"instructions": INSTRUCTIONS, "games": pending}, f, indent=2, default=str)

    print(f"{len(pending)} games (within {window_days} days) need predictions. Context written to {OUT_PATH}")
    if skipped_far_out:
        print(f"({skipped_far_out} scheduled games are more than {window_days} days out — "
              f"skipped for now, will be picked up automatically as they get closer.)")
    if pending:
        print("Next: ask Claude to read that file, reason through each game, and write picks "
              "to data/my_predictions.json (see README for the exact expected shape), then run "
              "apply_predictions.py.")


if __name__ == "__main__":
    main()
