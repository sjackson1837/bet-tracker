"""
Pulls recent form, win/loss streaks, and head-to-head history from ESPN's public
(unofficial, no-key-required) scoreboard API. This is what lets predictions look
beyond "who's favored" — recent results, streaks, and past matchups vs this opponent.

Note: this is an undocumented public API ESPN uses for its own site. It's widely
used and generally reliable, but endpoints/shapes can change without notice. If it
ever breaks, generate_predictions.py will just proceed without form data rather
than failing the whole run.
"""
import re
from difflib import get_close_matches

import requests

from utils import DATA_DIR, read_json, write_json

ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}"
TEAM_CACHE_PATH = DATA_DIR / "team_ids_cache.json"


def _load_cache():
    return read_json(TEAM_CACHE_PATH, default={})


def _save_cache(cache):
    write_json(TEAM_CACHE_PATH, cache)


def get_team_id(espn_sport, espn_league, team_name):
    """Looks up (and caches) the ESPN numeric team id for a team display name."""
    cache = _load_cache()
    key = f"{espn_sport}/{espn_league}"
    league_cache = cache.setdefault(key, {})

    if team_name in league_cache:
        return league_cache[team_name]

    url = ESPN_BASE.format(sport=espn_sport, league=espn_league) + "/teams"
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        teams = resp.json()["sports"][0]["leagues"][0]["teams"]
    except Exception as e:
        print(f"    ! could not load team list for {key}: {e}")
        return None

    names = {}
    for t in teams:
        info = t["team"]
        for candidate in [info.get("displayName"), info.get("shortDisplayName"),
                           info.get("name"), info.get("abbreviation")]:
            if candidate:
                names[candidate] = info["id"]

    # exact match first, then fuzzy
    team_id = names.get(team_name)
    if not team_id:
        match = get_close_matches(team_name, names.keys(), n=1, cutoff=0.6)
        team_id = names[match[0]] if match else None

    league_cache[team_name] = team_id
    _save_cache(cache)
    return team_id


def get_team_schedule(espn_sport, espn_league, team_id):
    if not team_id:
        return []
    url = ESPN_BASE.format(sport=espn_sport, league=espn_league) + f"/teams/{team_id}/schedule"
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        return resp.json().get("events", [])
    except Exception as e:
        print(f"    ! could not load schedule for team {team_id}: {e}")
        return []


def _completed_results(events, team_name):
    """Returns a chronological list of {'date', 'opponent', 'won', 'score'} for
    completed games only."""
    results = []
    for ev in events:
        comp = ev.get("competitions", [{}])[0]
        status = comp.get("status", {}).get("type", {})
        if not status.get("completed"):
            continue
        competitors = comp.get("competitors", [])
        if len(competitors) != 2:
            continue
        me = next((c for c in competitors if _is_same_team(c, team_name)), None)
        opp = next((c for c in competitors if c is not me), None)
        if not me or not opp:
            continue
        results.append({
            "date": ev.get("date", "")[:10],
            "opponent": opp.get("team", {}).get("displayName", "Unknown"),
            "won": me.get("winner", False),
            "score": f"{me.get('score', {}).get('displayValue', '?')}-{opp.get('score', {}).get('displayValue', '?')}",
        })
    results.sort(key=lambda r: r["date"])
    return results


def _is_same_team(competitor, team_name):
    info = competitor.get("team", {})
    candidates = [info.get("displayName"), info.get("shortDisplayName"), info.get("name")]
    return any(c and c.lower() == team_name.lower() for c in candidates) or \
        bool(get_close_matches(team_name, [c for c in candidates if c], n=1, cutoff=0.6))


def get_team_trends(espn_sport, espn_league, team_name, opponent_name=None):
    """Main entry point: returns recent form, streak, and (optionally) head-to-head
    history vs a specific opponent, for one team."""
    trends = {"team": team_name, "last5": None, "streak": None, "record": None, "h2h_vs_opponent": None}

    if not espn_sport or not espn_league:
        return trends

    team_id = get_team_id(espn_sport, espn_league, team_name)
    events = get_team_schedule(espn_sport, espn_league, team_id)
    results = _completed_results(events, team_name)

    if results:
        last5 = results[-5:]
        wins = sum(1 for r in last5 if r["won"])
        trends["last5"] = f"{wins}-{len(last5) - wins}"

        # current streak
        streak_type = "W" if results[-1]["won"] else "L"
        streak_len = 0
        for r in reversed(results):
            if (r["won"] and streak_type == "W") or (not r["won"] and streak_type == "L"):
                streak_len += 1
            else:
                break
        trends["streak"] = f"{streak_type}{streak_len}"

        wins_total = sum(1 for r in results if r["won"])
        trends["record"] = f"{wins_total}-{len(results) - wins_total}"

    if opponent_name:
        h2h = [r for r in results if opponent_name.lower() in r["opponent"].lower()
               or r["opponent"].lower() in opponent_name.lower()]
        if h2h:
            wins = sum(1 for r in h2h if r["won"])
            last_meeting = h2h[-1]
            trends["h2h_vs_opponent"] = {
                "record_this_season": f"{wins}-{len(h2h) - wins}",
                "last_meeting_result": ("won" if last_meeting["won"] else "lost") + f" {last_meeting['score']} on {last_meeting['date']}",
            }

    return trends
