"""
For every game in data/games.json that's "predicted" and whose start time has passed,
pulls the final score from The Odds API's /scores endpoint and grades the prediction
(straight-up winner and against-the-spread) so the site can show a track record.

The Odds API's free/standard scores endpoint only looks back a few days, which is a
fine match for our "last 7 days" track record window, but games older than that won't
be gradeable retroactively if a run was missed — the daily GitHub Action schedule is
what keeps this window filled in.

Requires env var: ODDS_API_KEY
"""
import sys
from datetime import datetime, timezone

import requests

from utils import load_config, get_env
from games_store import load_games, save_games

BASE_URL = "https://api.the-odds-api.com/v4/sports/{sport}/scores"


def fetch_scores(sport_key, api_key):
    params = {"apiKey": api_key, "daysFrom": 3, "dateFormat": "iso"}
    resp = requests.get(BASE_URL.format(sport=sport_key), params=params, timeout=30)
    if resp.status_code != 200:
        print(f"  ! {sport_key} scores: HTTP {resp.status_code} - {resp.text[:200]}", file=sys.stderr)
        return []
    return resp.json()


def match_score(scored_events, home_team, away_team, commence_time):
    for ev in scored_events:
        if not ev.get("completed"):
            continue
        if ev["home_team"] == home_team and ev["away_team"] == away_team and ev["commence_time"] == commence_time:
            return ev
    return None


def grade(game, score_event):
    scores = {s["name"]: s["score"] for s in score_event.get("scores", []) if s.get("score") is not None}
    if game["home_team"] not in scores or game["away_team"] not in scores:
        return None

    home_score = int(scores[game["home_team"]])
    away_score = int(scores[game["away_team"]])
    actual_winner = game["home_team"] if home_score > away_score else (
        game["away_team"] if away_score > home_score else "push")

    prediction = game["prediction"]
    su_correct = prediction.get("predicted_winner") == actual_winner

    ats_result = None
    home_spread = (game.get("odds", {}).get("spread") or {}).get(game["home_team"])
    if home_spread is not None:
        adjusted_home_score = home_score + home_spread
        if adjusted_home_score > away_score:
            actual_ats_winner = game["home_team"]
        elif adjusted_home_score < away_score:
            actual_ats_winner = game["away_team"]
        else:
            actual_ats_winner = "push"
        ats_result = {
            "actual_ats_winner": actual_ats_winner,
            "correct": prediction.get("predicted_against_spread") == actual_ats_winner if actual_ats_winner != "push" else None,
        }

    return {
        "home_score": home_score,
        "away_score": away_score,
        "actual_winner": actual_winner,
        "straight_up_correct": su_correct if actual_winner != "push" else None,
        "against_the_spread": ats_result,
        "graded_at": datetime.now(timezone.utc).isoformat(),
    }


def main():
    config = load_config()
    api_key = get_env("ODDS_API_KEY")
    games = load_games()
    now = datetime.now(timezone.utc)

    # Only hit each sport's scores endpoint once, even if we have many games for it.
    sport_keys_needed = set()
    for game in games.values():
        if game["status"] != "predicted":
            continue
        commence = datetime.fromisoformat(game["commence_time"].replace("Z", "+00:00"))
        if commence < now:
            sport_keys_needed.add(game.get("sport_key") or _infer_sport_key(config, game["league"]))

    scores_by_sport = {}
    for sk in sport_keys_needed:
        if not sk:
            continue
        print(f"Fetching scores for {sk}...")
        scores_by_sport[sk] = fetch_scores(sk, api_key)

    graded_count = 0
    for gid, game in games.items():
        if game["status"] != "predicted":
            continue
        commence = datetime.fromisoformat(game["commence_time"].replace("Z", "+00:00"))
        if commence >= now:
            continue

        sk = game.get("sport_key") or _infer_sport_key(config, game["league"])
        events = scores_by_sport.get(sk, [])
        match = match_score(events, game["home_team"], game["away_team"], game["commence_time"])
        if not match:
            continue  # not final yet, or outside the lookback window

        result = grade(game, match)
        if result is None:
            continue

        game["actual"] = result
        game["status"] = "graded"
        graded_count += 1
        flag = "correct" if result["straight_up_correct"] else "wrong"
        print(f"  {game['away_team']} @ {game['home_team']}: final {result['away_score']}-{result['home_score']} "
              f"(prediction was {flag})")

    save_games(games)
    print(f"Graded {graded_count} completed games.")


def _infer_sport_key(config, league_name):
    for league in config["leagues"]:
        if league["name"] == league_name:
            return league["odds_api_key"]
    return None


if __name__ == "__main__":
    main()
