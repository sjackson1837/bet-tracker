# Bet Tracker

Pulls betting lines, reasons through each game using recent form, streaks,
head-to-head history, and weather (not just "who's favored"), and builds a local
website you open in your browser showing upcoming predictions plus a rolling track
record of how predictions did against actual results.

This is set up to run **entirely for free**, but it does need two different
places to run: one script runs on *your machine* (VS Code terminal), because it
needs open internet access to real sports data sites that a Claude/Cowork session
can't reach directly; the AI reasoning step runs *in this Cowork conversation*,
because that's free as part of your existing Claude access instead of a billed API.

## How it works

**On your machine (VS Code terminal)** — run `scripts/refresh_data.sh` (or the
three scripts inside it individually):
1. **`fetch_odds.py`** — pulls upcoming games and consensus betting lines (averaged
   across sportsbooks) from [The Odds API](https://the-odds-api.com). Free tier.
2. **`fetch_results.py`** — for any earlier prediction whose game has since
   finished, pulls the final score and grades it (straight-up and against the
   spread). Free.
3. **`prepare_predictions.py`** — for each new game starting soon, pulls recent
   form/streaks/head-to-head from ESPN's public scoreboard data plus game-day
   weather, and writes it all to `data/pending_predictions.json`. Free, no key.

**Back here in Cowork** — ask Claude to pick it up from there:
4. Claude reads `data/pending_predictions.json`, reasons through each game (not
   just picking the favorite), and writes picks to `data/my_predictions.json`.
5. **`apply_predictions.py`** — merges those picks into `data/games.json`. Claude
   runs this itself; it's a local file operation, no internet needed.
6. **`build_site.py`** — regenerates the local site in `site/`. Also local-only.

Everything accumulates in one file, `data/games.json` — that's what powers the
"last 7 days" track record over time.

## One-time setup

### 1. Get a free Odds API key
Sign up at [the-odds-api.com](https://the-odds-api.com) (free tier: 500
requests/month — one refresh uses about 20, one per league). Copy your API key.

### 2. Save your key
Copy `.env.example` to `.env` in this same folder, and paste your key in:
```
ODDS_API_KEY=your_key_here
```
That's the only credential this project needs. `.env` is gitignored if you ever
add version control, so it won't accidentally get shared.

### 3. Install dependencies (once)
In VS Code's terminal, from this folder:
```
pip install -r requirements.txt
```

## Refreshing it

If you've set up the automatic 8am refresh (see below), you don't need to do
anything — just open the site in the morning. To refresh manually any other
time (e.g. mid-day line movement, or before automation is set up):

1. In VS Code's terminal, from this folder, run:
   ```
   ./scripts/refresh_data.sh
   ```
   (First time only: `chmod +x scripts/refresh_data.sh` if it's not already
   executable.) This pulls fresh odds, grades any finished games, and gathers
   trend/weather context for anything starting soon — all free, all on your
   machine's normal internet connection.
2. Back in this Cowork conversation, say something like "generate predictions from
   the pending file." Claude reads the context, reasons through each game, applies
   the picks, and rebuilds the site.
3. Open `site/index.html` in your browser to see it.

## Viewing the site

Open `site/index.html` in your browser (double-click it in Finder/Explorer, or in
VS Code right-click → "Open with Live Server") to see upcoming predictions.
`site/results.html` has the track record.

## Customizing

- **Leagues**: edit `config/leagues.json`. Run `python scripts/list_sports.py`
  (with your key in `.env`) to see the exact, current sport keys The Odds API
  supports if any of the pre-filled ones stop working.
- **Weather**: `config/stadiums.json` currently has coordinates for all 32 NFL
  stadiums. To get weather factored in for other outdoor leagues (MLB, soccer,
  NCAAF), add entries there keyed by the exact home team name — the code already
  supports it, it just needs the coordinates.
- **Track record window**: `config/leagues.json` → `settings.track_record_window_days`
  (defaults to 7).
- **Site title / timezone**: same `settings` block.

## Automatic morning refresh (8am)

The site now updates itself every morning, in two halves:

1. **Your machine fetches fresh data** (needs real internet access, so it can't
   run inside Cowork). Set this up once with either `cron` or `launchd`:
   - **Simplest — cron**: run `crontab -e` in Terminal and add a line like:
     ```
     30 7 * * * cd "/full/path/to/Bet Tracker" && ./scripts/refresh_data.sh >> /tmp/bet-tracker-refresh.log 2>&1
     ```
     (Find the full path by dragging the Bet Tracker folder into Terminal after
     typing `cd ` — it'll autofill.) This runs 30 minutes before the 8am
     Cowork step below, so there's fresh data waiting for it.
   - **Alternative — launchd** (if cron gets blocked by macOS permissions):
     copy `scripts/com.stevenjackson.bettracker.refresh.plist` to
     `~/Library/LaunchAgents/`, edit the path inside it to your real folder
     path, then run:
     ```
     launchctl load ~/Library/LaunchAgents/com.stevenjackson.bettracker.refresh.plist
     ```
2. **Cowork reasons through the games and rebuilds the site.** A scheduled
   Cowork task ("bet-tracker-morning-refresh") runs automatically at 8am,
   reads whatever `refresh_data.sh` left in `data/pending_predictions.json`,
   reasons through each game the same way this project always has (recent
   form, streaks, head-to-head, weather — not just picking the favorite),
   applies the picks, and rebuilds `site/index.html` and `site/results.html`.
   You can view, pause, or edit this task any time from Cowork's "Scheduled"
   sidebar section.

If step 1 doesn't run on a given morning (laptop asleep, no internet, etc.),
step 2 just skips reasoning for that day and rebuilds the site anyway — nothing
breaks, it just won't have new picks until the next successful local refresh.

**Want a shareable link too?** Push this folder to a free GitHub repo and turn
on GitHub Pages, so the site is reachable from any device via a URL instead of
only this computer. Ask Claude and it can set that up.

## Marking which games you actually bet on

Two ways to do this — pick whichever's more convenient in the moment:

- **On the site itself**: open `site/index.html` and check the "I bet on this"
  box under any game. This needs a tiny local helper running on your machine
  first:
  ```
  python3 scripts/pick_server.py
  ```
  (or double-click `scripts/start_pick_server.command` on a Mac). Leave it
  running in the background while you browse and click checkboxes; it talks
  to the site over `localhost` only (never your network) and updates
  `data/games.json` + rebuilds the site immediately when you toggle a pick.
- **In chat**: tell Claude something like "I bet on the Cubs and the Rays
  today" and it'll run `scripts/mark_picks.py` for you. Same underlying data,
  so both methods stay in sync.

Either way, `site/results.html` shows a separate "Your picks" record
alongside the model's overall record for its 55%+ confidence picks, so you can
compare how your bets did against the model's best calls.

## Known limitations, honestly

- **ESPN's schedule API is unofficial** (no public docs, no key — it's what powers
  espn.com itself). Reliable in practice but could change shape or break without
  notice. If it does, predictions still get generated — they just won't have trend
  data to reason from, and the prediction will say so.
- **Head-to-head and form data currently look only at the current season** via
  ESPN's schedule endpoint. Deeper multi-season history isn't pulled — a reasonable
  place to extend the code if you want longer-horizon trends.
- **The Odds API's scores endpoint only looks back ~3 days**, which matches the
  track-record window, but if you go more than a few days between refreshes, some
  completed games could go ungraded.
- Predictions are Claude's best reasoning over the data provided — not a
  guarantee, and there's no backtesting/calibration built in. Treat the "Track
  Record" page as the actual, honest scoreboard of how it's doing.
