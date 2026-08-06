"""
Pulls your bet selections down from the Cloudflare Worker and writes them into
data/games.json, so results.html can show how *your* picks did (not just the
model's).

Runs in the GitHub Actions pipeline right before build_site.py. Safe to run
locally too.

Reads the Worker URL from config/leagues.json -> settings.picks_api_base.
If that isn't set, or the Worker is unreachable, this exits quietly without
touching anything -- a picks outage should never break the daily refresh.
"""
import json
import sys
import urllib.error
import urllib.request

from utils import load_config
from games_store import load_games, save_games


def fetch_picks(base_url):
    url = base_url.rstrip("/") + "/picks"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.load(resp)
    picks = data.get("picks", {})
    if not isinstance(picks, dict):
        raise ValueError("unexpected /picks response shape")
    return picks


def main():
    settings = load_config()["settings"]
    base_url = settings.get("picks_api_base")

    if not base_url or "example.workers.dev" in base_url:
        print("No picks_api_base configured -- skipping pick sync.")
        return

    try:
        picks = fetch_picks(base_url)
    except (urllib.error.URLError, ValueError, TimeoutError) as e:
        print(f"Could not reach picks API ({e}) -- leaving existing picks alone.")
        return

    games = load_games()
    changed = 0
    for gid, game in games.items():
        selected = bool(picks.get(gid))
        if game.get("user_selected", False) != selected:
            game["user_selected"] = selected
            changed += 1

    if changed:
        save_games(games)
        print(f"Synced picks: {len(picks)} selected, {changed} game(s) updated.")
    else:
        print(f"Synced picks: {len(picks)} selected, already up to date.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Never fail the pipeline over picks.
        print(f"WARNING: pick sync failed: {e}", file=sys.stderr)
