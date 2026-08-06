# Fully automated setup

Everything now runs in the cloud. Your Mac can be closed, asleep, or off.

**The daily loop:** every morning at 7:30am Eastern, GitHub Actions fetches odds,
grades yesterday's games, gathers trend and weather data, asks Claude to reason
through each matchup, rebuilds the site, and publishes it. You open the app on
your phone, see the picks, tap the ones you're betting, and the results show up
the next morning alongside the new slate.

There are four one-time steps below. Budget about 15 minutes.

---

## Why the site was stuck on 8/4

Worth understanding, since it explains one of the changes.

The old workflow only deployed when files under `site/**` changed:

```yaml
on:
  push:
    paths:
      - "site/**"
```

The last push only changed `data/games.json` — the rebuilt HTML had already been
committed in an earlier push. So the path filter matched nothing, GitHub skipped
the deploy entirely, and the 8/4 build stayed live. No error, no failed run, just
silence. That filter is now gone.

---

## Step 1 — Add your API keys as GitHub secrets

Go to your repo → **Settings** → **Secrets and variables** → **Actions** →
**New repository secret**. Add two:

| Name | Value |
|------|-------|
| `ODDS_API_KEY` | The same key that's in your local `.env` |
| `ANTHROPIC_API_KEY` | From [console.anthropic.com](https://console.anthropic.com) → API Keys |

The Anthropic key is billed separately from your Claude subscription. At ~15
games a day this runs a few cents per day. You can cap it under **Billing** →
**Spend limits** if you'd like a hard ceiling.

## Step 2 — Point GitHub Pages at Actions

Repo → **Settings** → **Pages** → **Source**: select **GitHub Actions**.

If this is currently set to "Deploy from a branch," that alone could explain
future deploys not appearing. It must be **GitHub Actions**.

## Step 3 — Deploy the picks backend

This is what makes the "I bet on this" checkbox work from your phone. Right now
it posts to `http://127.0.0.1:8934` — a Python server on your Mac — which is why
the live site says *"Couldn't reach the local pick server."*

In Terminal:

```bash
cd "/Users/stevenjackson/Documents/VS Code Programs/Bet Tracker/workers"

# One-time: sign in to Cloudflare (opens a browser; free, no card needed)
npx wrangler login

# Create the storage namespace
npx wrangler kv namespace create PICKS
```

That last command prints something like:

```
[[kv_namespaces]]
binding = "PICKS"
id = "a1b2c3d4e5f6..."
```

Copy that `id` into `workers/wrangler.toml`, replacing
`PASTE_KV_NAMESPACE_ID_HERE`. Then:

```bash
npx wrangler deploy
```

It prints a URL like `https://bet-tracker-picks.<your-subdomain>.workers.dev`.
Put that in `config/leagues.json` → `settings.picks_api_base`, replacing the
`example.workers.dev` placeholder.

> Until you do this, the checkboxes fall back to the old local server — nothing
> breaks, phone picks just won't save yet.

**On security:** the endpoint is open by default. For a personal tracker that's
usually fine, but it does mean anyone who found the URL could toggle your
checkboxes. To lock it down, run `npx wrangler secret put PICKS_TOKEN`; the
Worker will then require that header on writes.

## Step 4 — Push everything and run it once

```bash
cd "/Users/stevenjackson/Documents/VS Code Programs/Bet Tracker"
git add -A
git commit -m "Move automation to GitHub Actions, add PWA and picks API"
git push
```

Then repo → **Actions** → **Daily refresh and deploy** → **Run workflow**.

Watch it run. If a step fails, the log tells you which one — most first-run
failures are a missing or mistyped secret from Step 1.

---

## Install it on your iPhone

1. Open your site in **Safari** (must be Safari — Chrome on iOS can't install)
2. Tap the **Share** button
3. Scroll down → **Add to Home Screen**

You get an app icon, it opens fullscreen with no address bar, and it caches the
last view so it still opens on a bad connection. For your purposes this is
indistinguishable from a native app — without the $99/year developer account,
Xcode, or an App Store review for every change.

---

## Turn off the old Mac automation

The launchd jobs are now redundant and would double up on API calls:

```bash
launchctl unload ~/Library/LaunchAgents/com.stevenjackson.bettracker.refresh.plist
launchctl unload ~/Library/LaunchAgents/com.stevenjackson.bettracker.finalize.plist
```

`scripts/refresh_data.sh` and `finalize_and_deploy.py` still work if you ever
want to refresh manually from the Mac.

---

## Your daily rhythm

| When | What |
|------|------|
| 7:30am ET | Actions refreshes data, generates picks, deploys |
| Morning | Open the app, review picks and confidence |
| Anytime | Tap "I bet on this" — syncs instantly from any device |
| Next morning | Track Record shows how your picks and the model's did |

---

## Timezone note

GitHub cron runs on UTC and doesn't observe daylight saving. `30 11 * * *` is
**7:30am Eastern in summer, 6:30am in winter**. If the winter hour bothers you,
change the cron in `.github/workflows/daily.yml` to `30 12 * * *` around
November and back in March.

---

## If something looks stale again

1. **Actions tab** — did today's run succeed? A red X names the failing step.
2. **Was it skipped?** The old path filter is gone, so this shouldn't recur.
3. **Service worker cache** — on iPhone, close the app fully (swipe up) and
   reopen. The worker is network-first, so it won't serve stale pages when
   you're online, but a hard reopen forces the issue.
4. **Check the deployed timestamp** — the header now shows local time
   ("Aug 06, 2026 at 07:31 AM EDT") rather than a bare UTC date, so it's obvious
   at a glance whether the deploy is fresh.

---

## What changed

| File | Purpose |
|------|---------|
| `.github/workflows/daily.yml` | The whole pipeline on a cron, plus Pages deploy |
| `.github/workflows/pages.yml` | Now manual-only; publishes site/ without a data refresh |
| `scripts/generate_predictions.py` | Claude API replacement for the Cowork step |
| `scripts/sync_picks.py` | Pulls your selections back into `games.json` |
| `workers/picks-worker.js` | Stores bet selections; works from any device |
| `scripts/build_site.py` | PWA manifest, service worker, app icons, mobile layout, local timestamp |
| `config/leagues.json` | Added `picks_api_base` and `short_title` |

Both workflows share a `pages` concurrency group, so they queue instead of
racing each other to publish.
