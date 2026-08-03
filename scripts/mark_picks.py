"""
Mark specific games as ones you actually placed a bet on, so the site can show a
checkmark next to them and track a separate "your picks" record on the results page
(alongside the model's overall 55%+ confidence record).

This is meant to be run by Claude on your behalf whenever you say something like
"I bet on the Cubs and the Rays today" -- just tell Claude which teams, and it will
run this script for you. You can also run it yourself from the terminal:

    python3 scripts/mark_picks.py "Chicago Cubs" "Tampa Bay Rays"
    python3 scripts/mark_picks.py --clear "Chicago Cubs"   # undo a mistaken mark

Matching rules:
  - Case-insensitive substring match against "<away team> <home team>" for every
    game currently in "predicted" or "graded" status (i.e. games that actually have
    a live line/pick, not the far-out odds-only games).
  - You can also pass an exact game_id (from data/games.json) for a precise match.
"""
import sys

from games_store import load_games, save_games


def main():
    args = sys.argv[1:]
    clear = False
    if args and args[0] == "--clear":
        clear = True
        args = args[1:]

    if not args:
        print('Usage: python3 scripts/mark_picks.py ["--clear"] "Team Name" ["Team Name" ...]')
        sys.exit(1)

    needles = [n.lower() for n in args]
    games = load_games()
    matched = []

    for gid, g in games.items():
        if g["status"] not in ("predicted", "graded"):
            continue
        haystack = f"{g['away_team']} {g['home_team']}".lower()
        if gid in args or any(n in haystack for n in needles):
            g["user_selected"] = not clear
            matched.append(f"{g['away_team']} @ {g['home_team']}")

    save_games(games)

    verb = "Unmarked" if clear else "Marked"
    if matched:
        print(f"{verb} {len(matched)} game(s):")
        for m in matched:
            print(f"  - {m}")
    else:
        print("No matching games found (they need to already have a line -- status 'predicted' or 'graded'). Check team name spelling.")


if __name__ == "__main__":
    main()
