# Bet Tracker - Full Automation Setup

This guide walks you through enabling **fully automated daily updates** for your bet tracker. Once set up, your site will refresh every morning without any manual intervention.

## What Gets Automated

The system now runs in three coordinated steps:

| Time | What Happens | Where |
|------|--------------|-------|
| **7:30 AM** | Fetch fresh odds, grade finished games, prepare prediction data | Your machine (launchd) |
| **8:00 AM** | Generate predictions from pending data via AI reasoning | Cowork (scheduled task) |
| **8:05 AM** | Apply predictions, rebuild site, deploy to GitHub Pages | Your machine (launchd) |

Your website updates automatically and is live at: **https://sjackson1837.github.io/bet-tracker/**

---

## Step 1: Install Local Automation (7:30 AM & 8:05 AM)

These two steps run on your machine via **launchd** (macOS task scheduler).

### Option A: Automatic Installation (Recommended)

From your Bet Tracker folder in Terminal:

```bash
chmod +x scripts/setup_automation.sh
./scripts/setup_automation.sh
```

This installs both launchd tasks automatically. Done!

### Option B: Manual Installation

If automatic setup doesn't work, install manually:

#### 1. Data Refresh (7:30 AM)
```bash
cp scripts/com.stevenjackson.bettracker.refresh.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.stevenjackson.bettracker.refresh.plist
```

#### 2. Site Finalization (8:05 AM)
```bash
cp scripts/com.stevenjackson.bettracker.finalize.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.stevenjackson.bettracker.finalize.plist
```

### Verify Installation

Check logs to see if tasks ran:
```bash
tail -f /tmp/bet-tracker-refresh.log    # Data fetch logs
tail -f /tmp/bet-tracker-finalize.log   # Site build logs
```

---

## Step 2: Set Up Cowork Scheduled Task (8:00 AM)

The middle piece — prediction generation — runs in Cowork because it needs Claude's AI reasoning.

### Create the Scheduled Task

In Cowork, ask Claude:

> "Set up an 8 AM daily scheduled task called 'bet-tracker-morning-refresh' that:
>
> 1. Reads `/Users/stevenjackson/Documents/VS Code Programs/Bet Tracker/data/pending_predictions.json`
> 2. Reasons through each game (recent form, streaks, head-to-head, weather — not just picking favorites)
> 3. Writes picks to `/Users/stevenjackson/Documents/VS Code Programs/Bet Tracker/data/my_predictions.json` in this format:
>    ```json
>    {
>      "<game_id>": {
>        "predicted_winner": "Team Name",
>        "predicted_against_spread": "Team Name [+/-X.5]",
>        "confidence": 65,
>        "key_factors": ["Recent form", "Weather"],
>        "reasoning": "Brief explanation"
>      }
>    }
>    ```
> 4. Runs `/sessions/exciting-gracious-maxwell/mnt/Bet Tracker/scripts/finalize_and_deploy.py` via bash to apply predictions, build the site, and push to GitHub
>
> If no games are pending (empty or missing file), just run the finalize script — it rebuilds with current data."

Claude will set this up for you.

---

## How It All Works Together

```
7:30 AM ┌─────────────────────────────────────────┐
        │ Your machine runs refresh_data.sh       │
        │ • Fetches latest odds                   │
        │ • Grades finished games                 │
        │ • Prepares prediction data              │
        │ → Writes to pending_predictions.json    │
        └──────────────────┬──────────────────────┘
                           │
                           ↓
8:00 AM ┌─────────────────────────────────────────┐
        │ Cowork runs scheduled task              │
        │ • Reads pending_predictions.json        │
        │ • Reasons through games                 │
        │ • Writes predictions to my_predictions  │
        └──────────────────┬──────────────────────┘
                           │
                           ↓
8:05 AM ┌─────────────────────────────────────────┐
        │ Your machine runs finalize_and_deploy   │
        │ • Applies predictions                   │
        │ • Rebuilds static site                  │
        │ • Commits & pushes to GitHub            │
        │ → GitHub Pages auto-deploys live        │
        └─────────────────────────────────────────┘
```

---

## Manual Runs (Anytime)

If you want to refresh outside the schedule:

### Just refresh data (no new predictions):
```bash
./scripts/refresh_data.sh
```

### Generate predictions & deploy:
In Cowork, ask Claude to generate predictions from your pending file, then run:
```bash
python3 scripts/finalize_and_deploy.py
```

---

## What You'll See

Once running:

- **7:30 AM:** Fresh odds loaded, yesterday's games graded
- **8:00 AM:** Cowork generates predictions (watch the chat)
- **8:05 AM:** Site rebuilds and deploys automatically
- **Morning:** Open https://sjackson1837.github.io/bet-tracker/ to see updated picks

The site is **live from any device** — no need to open it locally.

---

## Troubleshooting

### Launchd tasks won't load
```bash
# List active tasks:
launchctl list | grep bettracker

# Try loading manually:
launchctl load ~/Library/LaunchAgents/com.stevenjackson.bettracker.refresh.plist
```

### Git push fails
Check that:
1. Your GitHub credentials are set up (should work if `git` works normally)
2. You have push access to the repo
3. SSH key is loaded if using SSH authentication

### Cowork task doesn't run at 8:00 AM
- Cowork must be running for scheduled tasks to execute
- If the app is closed at 8 AM, the task runs on next launch
- You can also manually trigger it anytime from Cowork's Scheduled sidebar

### No predictions generated (empty picks)
If `my_predictions.json` is empty or missing when finalize runs, the script just rebuilds the site with current data — nothing breaks.

---

## Disabling Automation

If you want to pause or stop:

```bash
# Stop both tasks:
launchctl unload ~/Library/LaunchAgents/com.stevenjackson.bettracker.refresh.plist
launchctl unload ~/Library/LaunchAgents/com.stevenjackson.bettracker.finalize.plist

# Re-enable later:
launchctl load ~/Library/LaunchAgents/com.stevenjackson.bettracker.refresh.plist
launchctl load ~/Library/LaunchAgents/com.stevenjackson.bettracker.finalize.plist
```

---

## Files Created/Modified

- `scripts/finalize_and_deploy.py` — Applies predictions, builds site, pushes to GitHub
- `scripts/com.stevenjackson.bettracker.finalize.plist` — Launchd config for 8:05 AM
- `scripts/setup_automation.sh` — One-command installer
- `AUTOMATION_SETUP.md` — This file

---

## Questions?

Ask Claude in Cowork! It can help troubleshoot, view logs, or adjust the schedule.
