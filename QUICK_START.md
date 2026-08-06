# Automation Setup - Quick Start

## One-Minute Setup

1. **Install launchd tasks** (runs 7:30 AM & 8:05 AM):
   ```bash
   cd "/Users/stevenjackson/Documents/VS Code Programs/Bet Tracker"
   chmod +x scripts/setup_automation.sh
   ./scripts/setup_automation.sh
   ```

2. **Ask Claude to set up the 8:00 AM prediction task** (in Cowork):

   > Set up an 8 AM daily scheduled task called 'bet-tracker-morning-refresh' that reads `/Users/stevenjackson/Documents/VS Code Programs/Bet Tracker/data/pending_predictions.json`, generates predictions, writes them to `data/my_predictions.json`, and runs `scripts/finalize_and_deploy.py` via bash.

3. **Done!** Your site now updates daily at:
   - 7:30 AM — Fetch data
   - 8:00 AM — Generate predictions (Cowork)
   - 8:05 AM — Deploy to GitHub Pages

View it: https://sjackson1837.github.io/bet-tracker/

---

## What Was Created

- `scripts/finalize_and_deploy.py` — Applies predictions & deploys
- `scripts/com.stevenjackson.bettracker.finalize.plist` — Launchd config (8:05 AM)
- `scripts/setup_automation.sh` — One-click installer
- `AUTOMATION_SETUP.md` — Full documentation

---

## Logs

```bash
tail -f /tmp/bet-tracker-refresh.log    # 7:30 AM fetch
tail -f /tmp/bet-tracker-finalize.log   # 8:05 AM deploy
```

---

See **AUTOMATION_SETUP.md** for full details & troubleshooting.
