"""
Renders data/games.json into a static site (site/index.html + site/results.html +
site/style.css) suitable for GitHub Pages. No JS framework, no build step — plain
HTML/CSS (plus one small inline script for the sidebar filter) so it's easy to tweak
by hand later if you want.
"""
import json
import struct
import zlib
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from utils import load_config, SITE_DIR
from games_store import load_games

PICK_SERVER_PORT = 8934

BG_RGB = (15, 17, 21)        # --bg
ACCENT_RGB = (79, 140, 255)  # --accent
GOOD_RGB = (51, 193, 122)    # --good

CSS = """
:root {
  --bg: #0f1115; --card: #171a21; --border: #262b36; --text: #e8eaed;
  --muted: #9aa4b2; --accent: #4f8cff; --good: #33c17a; --bad: #e6564c; --push: #c9a227;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
header { padding: 24px 20px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; }
header h1 { margin: 0; font-size: 1.4rem; }
nav a { color: var(--muted); text-decoration: none; margin-left: 18px; font-size: 0.95rem; }
nav a.active, nav a:hover { color: var(--text); }
.layout { max-width: 1200px; margin: 0 auto; display: flex; align-items: flex-start; }
.sidebar { width: 190px; flex-shrink: 0; padding: 24px 12px 60px; position: sticky; top: 0; align-self: flex-start; }
.sidebar h3 { color: var(--muted); font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.04em; margin: 0 0 10px 10px; }
.sidebar button { display: block; width: 100%; text-align: left; background: none; border: none; color: var(--muted); padding: 8px 10px; border-radius: 6px; cursor: pointer; font-size: 0.9rem; margin-bottom: 2px; font-family: inherit; }
.sidebar button:hover { background: #1f2430; color: var(--text); }
.sidebar button.active { background: rgba(79,140,255,0.15); color: var(--accent); font-weight: 600; }
main { flex: 1; min-width: 0; padding: 24px 20px 60px; }
.updated { color: var(--muted); font-size: 0.85rem; margin-bottom: 24px; }
.league-group h2 { font-size: 1.1rem; color: var(--accent); margin-bottom: 12px; }
.card { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 16px 18px; margin-bottom: 12px; }
.matchup { font-size: 1.05rem; font-weight: 600; margin-bottom: 4px; }
.meta { color: var(--muted); font-size: 0.85rem; margin-bottom: 10px; }
.odds-row { display: flex; gap: 22px; flex-wrap: wrap; margin: 10px 0; padding: 10px 12px; background: #1f2430; border-radius: 8px; }
.odds-item .odds-label { color: var(--muted); font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.03em; margin-bottom: 2px; }
.odds-item .odds-value { color: var(--text); font-size: 0.85rem; font-weight: 600; }
.your-pick-badge { display: inline-flex; align-items: center; gap: 5px; background: rgba(51,193,122,0.15); color: var(--good); padding: 2px 9px; border-radius: 20px; font-size: 0.78rem; font-weight: 600; margin-left: 8px; }
.pick-row { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; flex-wrap: wrap; }
.pick { font-weight: 600; color: var(--accent); }
.confidence { background: rgba(79,140,255,0.15); color: var(--accent); padding: 2px 9px; border-radius: 20px; font-size: 0.8rem; }
.factors { list-style: none; padding: 0; margin: 8px 0 0; display: flex; flex-wrap: wrap; gap: 6px; }
.factors li { background: #1f2430; border: 1px solid var(--border); border-radius: 6px; padding: 3px 9px; font-size: 0.78rem; color: var(--muted); }
.reasoning { margin-top: 10px; font-size: 0.88rem; color: var(--muted); line-height: 1.4; }
.empty { color: var(--muted); font-style: italic; padding: 30px 0; text-align: center; }
.stats-row { display: flex; gap: 12px; margin-bottom: 28px; flex-wrap: wrap; }
.stat-box { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 16px 22px; min-width: 140px; }
.stat-box .num { font-size: 1.6rem; font-weight: 700; }
.stat-box .label { color: var(--muted); font-size: 0.8rem; }
table { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
th, td { text-align: left; padding: 9px 10px; border-bottom: 1px solid var(--border); }
th { color: var(--muted); font-weight: 500; font-size: 0.78rem; text-transform: uppercase; }
.result-good { color: var(--good); font-weight: 600; }
.result-bad { color: var(--bad); font-weight: 600; }
.result-push { color: var(--push); font-weight: 600; }
.pick-toggle { display: inline-flex; align-items: center; gap: 8px; margin-top: 10px; font-size: 0.9rem; color: var(--muted); cursor: pointer; user-select: none; -webkit-tap-highlight-color: transparent; }
.pick-toggle input { cursor: pointer; width: 20px; height: 20px; accent-color: var(--good); }
.pick-status { margin-top: 6px; font-size: 0.78rem; color: var(--bad); display: none; }

/* Phone layout: stack the sidebar into a horizontal scroller and give the
   cards the full width. Also respects the iPhone home indicator inset. */
@media (max-width: 720px) {
  body { padding-bottom: env(safe-area-inset-bottom); }
  header { padding: 16px 16px; }
  header h1 { font-size: 1.15rem; }
  nav a { margin-left: 0; margin-right: 16px; }
  .layout { display: block; }
  .sidebar {
    width: auto; position: static; padding: 12px 12px 4px;
    display: flex; gap: 8px; overflow-x: auto; -webkit-overflow-scrolling: touch;
    border-bottom: 1px solid var(--border);
  }
  .sidebar h3 { display: none; }
  .sidebar button { width: auto; white-space: nowrap; flex: 0 0 auto; margin-bottom: 0; }
  main { padding: 16px 14px 48px; }
  .card { padding: 14px; }
  .odds-row { gap: 14px; }
  .stat-box { flex: 1 1 40%; min-width: 0; padding: 14px; }
  table { font-size: 0.8rem; }
  th, td { padding: 7px 6px; }
}
"""

FILTER_SCRIPT = """
<script>
function filterLeague(league, btn) {
  document.querySelectorAll('.filterable-item').forEach(function(el) {
    el.style.display = (league === 'all' || el.dataset.league === league) ? '' : 'none';
  });
  document.querySelectorAll('.league-btn').forEach(function(b) { b.classList.remove('active'); });
  btn.classList.add('active');
}
</script>
"""

def pick_script(picks_api_base):
    """Checkbox wiring. Points at the Cloudflare Worker when one is configured
    (so picks sync from any device), otherwise falls back to the old local
    Python pick server."""
    base = (picks_api_base or "").rstrip("/")
    if not base or "example.workers.dev" in base:
        base = f"http://127.0.0.1:{PICK_SERVER_PORT}"

    return f"""
<script>
var PICKS_API = "{base}";

// Pull current selections on load so the phone and the laptop agree.
document.addEventListener('DOMContentLoaded', function() {{
  fetch(PICKS_API + '/picks', {{cache: 'no-store'}})
    .then(function(res) {{ if (!res.ok) throw new Error('bad response'); return res.json(); }})
    .then(function(data) {{
      var picks = (data && data.picks) || {{}};
      document.querySelectorAll('input[data-game-id]').forEach(function(box) {{
        var gid = box.dataset.gameId;
        var selected = !!picks[gid];
        box.checked = selected;
        var badge = document.getElementById('badge-' + gid);
        if (badge) badge.style.display = selected ? 'inline-flex' : 'none';
      }});
    }})
    .catch(function() {{ /* offline or not configured yet -- leave rendered state */ }});
}});

function togglePick(gameId, checkbox) {{
  var badge = document.getElementById('badge-' + gameId);
  var status = document.getElementById('status-' + gameId);
  checkbox.disabled = true;
  fetch(PICKS_API + '/toggle-pick', {{
    method: 'POST',
    headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{game_id: gameId}})
  }})
  .then(function(res) {{ if (!res.ok) throw new Error('bad response'); return res.json(); }})
  .then(function(data) {{
    if (badge) badge.style.display = data.user_selected ? 'inline-flex' : 'none';
    checkbox.checked = data.user_selected;
    if (status) status.style.display = 'none';
  }})
  .catch(function(err) {{
    checkbox.checked = !checkbox.checked;
    if (status) status.style.display = 'block';
  }})
  .finally(function() {{ checkbox.disabled = false; }});
}}

if ('serviceWorker' in navigator) {{
  window.addEventListener('load', function() {{
    navigator.serviceWorker.register('sw.js').catch(function() {{}});
  }});
}}
</script>
"""


def _png_chunk(tag, data):
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def make_icon_png(size):
    """Generate the app icon without pulling in Pillow -- three ascending bars
    on the site's dark background, which reads fine at home-screen size.
    Full-bleed background so it works as a maskable icon too."""
    bars = [
        (0.22, 0.55, ACCENT_RGB),
        (0.43, 0.40, ACCENT_RGB),
        (0.64, 0.26, GOOD_RGB),
    ]
    bar_w = 0.14
    baseline = 0.76

    # Precompute pixel-space bar rectangles.
    rects = []
    for left_f, top_f, color in bars:
        rects.append((
            int(left_f * size),
            int((left_f + bar_w) * size),
            int(top_f * size),
            int(baseline * size),
            color,
        ))

    raw = bytearray()
    for y in range(size):
        raw.append(0)  # filter type 0 (None)
        row = bytearray()
        for x in range(size):
            px = BG_RGB
            for x0, x1, y0, y1, color in rects:
                if x0 <= x < x1 and y0 <= y < y1:
                    px = color
                    break
            row += bytes(px)
        raw += row

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + _png_chunk(b"IEND", b"")
    )


SERVICE_WORKER = """/* Bet Tracker service worker.
   Network-first for pages so a fresh deploy is never masked by a stale cache --
   that failure mode is worse than being briefly offline. Cache is only a
   fallback for when there's genuinely no connection. */
const CACHE = 'bet-tracker-v1';
const SHELL = ['index.html', 'results.html', 'manifest.json', 'icon-192.png', 'icon-512.png'];

self.addEventListener('install', function(event) {
  self.skipWaiting();
  event.waitUntil(caches.open(CACHE).then(function(c) { return c.addAll(SHELL).catch(function() {}); }));
});

self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys().then(function(keys) {
      return Promise.all(keys.filter(function(k) { return k !== CACHE; })
                             .map(function(k) { return caches.delete(k); }));
    }).then(function() { return self.clients.claim(); })
  );
});

self.addEventListener('fetch', function(event) {
  var req = event.request;
  if (req.method !== 'GET') return;
  // Never cache the picks API.
  if (req.url.indexOf('/picks') !== -1 || req.url.indexOf('/toggle-pick') !== -1) return;

  event.respondWith(
    fetch(req).then(function(res) {
      var copy = res.clone();
      caches.open(CACHE).then(function(c) { c.put(req, copy); });
      return res;
    }).catch(function() {
      return caches.match(req).then(function(hit) {
        return hit || caches.match('index.html');
      });
    })
  );
});
"""


def write_pwa_assets(site_title, short_title):
    manifest = {
        "name": site_title,
        "short_name": short_title,
        "start_url": "index.html",
        "scope": ".",
        "display": "standalone",
        "orientation": "portrait",
        "background_color": "#0f1115",
        "theme_color": "#0f1115",
        "icons": [
            {"src": "icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
        ],
    }
    with open(SITE_DIR / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    with open(SITE_DIR / "sw.js", "w") as f:
        f.write(SERVICE_WORKER)

    for size in (192, 512):
        path = SITE_DIR / f"icon-{size}.png"
        if not path.exists():
            path.write_bytes(make_icon_png(size))

    # Tell GitHub Pages not to run Jekyll, which would otherwise ignore some files.
    (SITE_DIR / ".nojekyll").write_text("")


def fmt_time(iso_str, tz_name):
    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    try:
        local = dt.astimezone(ZoneInfo(tz_name))
    except Exception:
        local = dt
    return local.strftime("%a %b %d, %I:%M %p %Z")


def fmt_price(price):
    if price is None:
        return "-"
    price = int(round(price))
    return f"+{price}" if price > 0 else str(price)


def fmt_spread(value):
    if value is None:
        return "-"
    return f"+{value}" if value > 0 else str(value)


def render_odds_row(g):
    odds = g.get("odds")
    if not odds:
        return ""
    ml = odds.get("moneyline", {})
    sp = odds.get("spread", {})
    total = odds.get("total")
    away, home = g["away_team"], g["home_team"]

    ml_parts = [f"{team} {fmt_price(price)}" for team, price in ml.items()]
    sp_parts = [f"{team} {fmt_spread(val)}" for team, val in sp.items()]

    items = []
    if ml_parts:
        items.append(f'<div class="odds-item"><div class="odds-label">Moneyline</div><div class="odds-value">{" &middot; ".join(ml_parts)}</div></div>')
    if sp_parts:
        items.append(f'<div class="odds-item"><div class="odds-label">Spread</div><div class="odds-value">{" &middot; ".join(sp_parts)}</div></div>')
    if total is not None:
        items.append(f'<div class="odds-item"><div class="odds-label">Total (O/U)</div><div class="odds-value">{total}</div></div>')
    if odds.get("num_bookmakers"):
        items.append(f'<div class="odds-item"><div class="odds-label">Books</div><div class="odds-value">{odds["num_bookmakers"]}</div></div>')

    if not items:
        return ""
    return f'<div class="odds-row">{"".join(items)}</div>'


def render_sidebar(leagues_present, league_order):
    ordered = [l for l in league_order if l in leagues_present] + \
              [l for l in leagues_present if l not in league_order]
    buttons = ['<button class="league-btn active" data-league="all" onclick="filterLeague(\'all\', this)">All Sports</button>']
    for league in ordered:
        buttons.append(
            f'<button class="league-btn" data-league="{league}" onclick="filterLeague(\'{league}\', this)">{league}</button>'
        )
    return f'<div class="sidebar"><h3>Sports</h3>{"".join(buttons)}</div>'


def page_shell(title, active, body, site_title, sidebar_html="", picks_script=""):
    nav_home = ' class="active"' if active == "home" else ""
    nav_results = ' class="active"' if active == "results" else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<title>{title}</title>
<link rel="manifest" href="manifest.json">
<meta name="theme-color" content="#0f1115">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="{site_title}">
<link rel="apple-touch-icon" href="icon-192.png">
<link rel="icon" type="image/png" href="icon-192.png">
<style>{CSS}</style>
</head>
<body>
<header>
  <h1>{site_title}</h1>
  <nav>
    <a href="index.html"{nav_home}>Upcoming Predictions</a>
    <a href="results.html"{nav_results}>Track Record</a>
  </nav>
</header>
<div class="layout">
{sidebar_html}
<main>
{body}
</main>
</div>
{FILTER_SCRIPT}
{picks_script}
</body>
</html>
"""


def render_upcoming(games, tz_name, window_days, min_confidence):
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=window_days)
    upcoming = []
    for gid, g in games.items():
        if g["status"] not in ("scheduled", "predicted"):
            continue
        commence = datetime.fromisoformat(g["commence_time"].replace("Z", "+00:00"))
        if commence < now:
            continue
        # Already-predicted games stay visible until kickoff even if the window
        # has since moved on; odds-only games are hidden until they're within the
        # window so the page isn't cluttered with games months away.
        if g["status"] == "scheduled" and commence > cutoff:
            continue
        # Only surface games with an actual confident pick -- no bare-odds
        # cards and no sub-threshold "no lean" cards cluttering the page.
        pred = g.get("prediction")
        if not pred or pred.get("confidence", 0) <= min_confidence:
            continue
        g = dict(g)
        g["id"] = gid
        upcoming.append(g)

    if not upcoming:
        return "", []

    by_league = {}
    for g in upcoming:
        by_league.setdefault(g["league"], []).append(g)

    def confidence_sort_key(g):
        pred = g.get("prediction")
        confidence = pred.get("confidence", -1) if pred else -1
        # Highest confidence first; games without a prediction yet sink to the
        # bottom; ties broken by soonest kickoff.
        return (-confidence, g["commence_time"])

    html = []
    for league, glist in by_league.items():
        glist.sort(key=confidence_sort_key)
        html.append(f'<div class="league-group filterable-item" data-league="{league}"><h2>{league}</h2>')
        for g in glist:
            html.append(render_game_card(g, tz_name))
        html.append("</div>")
    return "\n".join(html), list(by_league.keys())


def render_pick_toggle(gid, selected):
    """Checkbox that lets you mark a game as one you actually bet on, straight
    from the site (talks to scripts/pick_server.py running locally)."""
    checked = "checked" if selected else ""
    return f"""<label class="pick-toggle">
    <input type="checkbox" id="chk-{gid}" data-game-id="{gid}" {checked} onchange="togglePick('{gid}', this)"> I bet on this
  </label>
  <div class="pick-status" id="status-{gid}">Couldn't save that pick &mdash; check your connection and try again.</div>"""


def render_game_card(g, tz_name):
    when = fmt_time(g["commence_time"], tz_name)
    odds_html = render_odds_row(g)
    pred = g["prediction"]
    gid = g.get("id", "")
    display = "inline-flex" if g.get("user_selected") else "none"
    badge = f' <span class="your-pick-badge" id="badge-{gid}" style="display:{display};">&#10003; Your pick</span>'

    pick_toggle = render_pick_toggle(gid, g.get("user_selected", False))

    factors = "".join(f"<li>{f}</li>" for f in pred.get("key_factors", []))
    return f"""<div class="card">
  <div class="matchup">{g['away_team']} @ {g['home_team']}{badge}</div>
  <div class="meta">{when}</div>
  {odds_html}
  <div class="pick-row">
    <span>Pick:</span> <span class="pick">{pred.get('predicted_winner')}</span>
    <span class="confidence">{pred.get('confidence')}% confidence</span>
  </div>
  <div class="pick-row"><span>Against the spread:</span> <span class="pick">{pred.get('predicted_against_spread')}</span></div>
  <ul class="factors">{factors}</ul>
  <div class="reasoning">{pred.get('reasoning', '')}</div>
  {pick_toggle}
</div>"""


def _su_ats_record(games_subset):
    su_gradeable = [g for g in games_subset if g["actual"]["straight_up_correct"] is not None]
    su_correct = sum(1 for g in su_gradeable if g["actual"]["straight_up_correct"])
    ats_gradeable = [g for g in games_subset if g["actual"].get("against_the_spread")
                      and g["actual"]["against_the_spread"]["correct"] is not None]
    ats_correct = sum(1 for g in ats_gradeable if g["actual"]["against_the_spread"]["correct"])
    su_pct = round(100 * su_correct / len(su_gradeable)) if su_gradeable else 0
    ats_pct = round(100 * ats_correct / len(ats_gradeable)) if ats_gradeable else 0
    return su_correct, len(su_gradeable), su_pct, ats_correct, len(ats_gradeable), ats_pct


def _stats_block(title, games_subset):
    su_correct, su_total, su_pct, ats_correct, ats_total, ats_pct = _su_ats_record(games_subset)
    return f"""<h3 style="color:var(--muted);font-size:0.8rem;text-transform:uppercase;letter-spacing:0.04em;margin:20px 0 8px;">{title}</h3>
<div class="stats-row">
  <div class="stat-box"><div class="num">{su_correct}-{su_total - su_correct}</div><div class="label">Straight-up ({su_pct}%)</div></div>
  <div class="stat-box"><div class="num">{ats_correct}-{ats_total - ats_correct}</div><div class="label">Against the spread ({ats_pct}%)</div></div>
  <div class="stat-box"><div class="num">{len(games_subset)}</div><div class="label">Games graded</div></div>
</div>"""


def render_results(games, tz_name, window_days, min_confidence):
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    graded = [g for g in games.values()
              if g["status"] == "graded"
              and datetime.fromisoformat(g["commence_time"].replace("Z", "+00:00")) >= cutoff]
    graded.sort(key=lambda g: g["commence_time"], reverse=True)

    your_picks = [g for g in graded if g.get("user_selected")]
    overall_55 = [g for g in graded if g.get("prediction") and g["prediction"].get("confidence", 0) > min_confidence]

    stats = _stats_block("Your picks", your_picks) + _stats_block(f"Model overall ({min_confidence}%+ confidence)", overall_55)

    if not graded:
        return stats + '<p class="empty">No graded results yet for this window.</p>', []

    rows = []
    leagues_present = []
    for g in graded:
        if g["league"] not in leagues_present:
            leagues_present.append(g["league"])
        actual = g["actual"]
        pred = g["prediction"] or {}
        when = fmt_time(g["commence_time"], tz_name)
        su_class = "result-push"
        su_label = "push"
        if actual["straight_up_correct"] is True:
            su_class, su_label = "result-good", "correct"
        elif actual["straight_up_correct"] is False:
            su_class, su_label = "result-bad", "wrong"

        ats = actual.get("against_the_spread")
        ats_class, ats_label = "result-push", "n/a"
        if ats and ats["correct"] is True:
            ats_class, ats_label = "result-good", "correct"
        elif ats and ats["correct"] is False:
            ats_class, ats_label = "result-bad", "wrong"

        your_pick_mark = '<span class="result-good">&#10003;</span>' if g.get("user_selected") else ""

        rows.append(f"""<tr class="filterable-item" data-league="{g['league']}">
  <td>{your_pick_mark}</td>
  <td>{when}</td>
  <td>{g['league']}</td>
  <td>{g['away_team']} @ {g['home_team']}</td>
  <td>{actual['away_score']}-{actual['home_score']}</td>
  <td>{pred.get('predicted_winner', '?')}</td>
  <td class="{su_class}">{su_label}</td>
  <td class="{ats_class}">{ats_label}</td>
</tr>""")

    table = f"""<table>
<thead><tr><th>Your Pick</th><th>Kickoff</th><th>League</th><th>Matchup</th><th>Final</th><th>Predicted Winner</th><th>Straight-up</th><th>ATS</th></tr></thead>
<tbody>{''.join(rows)}</tbody>
</table>"""

    return stats + table, leagues_present


def main():
    config = load_config()
    settings = config["settings"]
    tz_name = settings.get("timezone", "UTC")
    site_title = settings.get("site_title", "Bet Tracker")
    short_title = settings.get("short_title", "Bet Tracker")
    results_window_days = settings.get("track_record_window_days", 7)
    upcoming_window_days = settings.get("days_of_upcoming_odds", 3)
    min_confidence = settings.get("min_confidence_to_show", 55)
    picks_api_base = settings.get("picks_api_base", "")

    league_order = [l["name"] for l in config.get("leagues", [])]

    games = load_games()

    SITE_DIR.mkdir(parents=True, exist_ok=True)
    write_pwa_assets(site_title, short_title)
    picks_script = pick_script(picks_api_base)

    # Timestamp in your local timezone -- "updated 2026-08-06 UTC" is confusing
    # when you're reading it at 9pm Eastern the night before.
    stamp = datetime.now(timezone.utc).astimezone(ZoneInfo(tz_name)).strftime("%b %d, %Y at %I:%M %p %Z")

    upcoming_html, upcoming_leagues = render_upcoming(games, tz_name, upcoming_window_days, min_confidence)
    if not upcoming_html:
        upcoming_html = '<p class="empty">No upcoming games right now. Check back after the next data refresh.</p>'
        upcoming_sidebar = ""
    else:
        upcoming_sidebar = render_sidebar(upcoming_leagues, league_order)
    index_body = f'<p class="updated">Last updated {stamp}</p>' + upcoming_html
    with open(SITE_DIR / "index.html", "w") as f:
        f.write(page_shell(site_title, "home", index_body, site_title, upcoming_sidebar, picks_script))

    results_html, results_leagues = render_results(games, tz_name, results_window_days, min_confidence)
    results_sidebar = render_sidebar(results_leagues, league_order) if results_leagues else ""
    results_body = f'<p class="updated">Last updated {stamp}</p>' + results_html
    with open(SITE_DIR / "results.html", "w") as f:
        f.write(page_shell(f"{site_title} - Track Record", "results", results_body, site_title, results_sidebar, picks_script))

    print(f"Site built to {SITE_DIR}")


if __name__ == "__main__":
    main()
