"""
Renders data/games.json into a static site (site/index.html + site/results.html +
site/style.css) suitable for GitHub Pages. No JS framework, no build step — plain
HTML/CSS (plus one small inline script for the sidebar filter) so it's easy to tweak
by hand later if you want.
"""
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from utils import load_config, SITE_DIR, today_str
from games_store import load_games

PICK_SERVER_PORT = 8934

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
.pick-toggle { display: inline-flex; align-items: center; gap: 6px; margin-top: 10px; font-size: 0.85rem; color: var(--muted); cursor: pointer; user-select: none; }
.pick-toggle input { cursor: pointer; }
.pick-status { margin-top: 6px; font-size: 0.78rem; color: var(--bad); display: none; }
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

PICK_SCRIPT = f"""
<script>
function togglePick(gameId, checkbox) {{
  var badge = document.getElementById('badge-' + gameId);
  var status = document.getElementById('status-' + gameId);
  checkbox.disabled = true;
  fetch('http://127.0.0.1:{PICK_SERVER_PORT}/toggle-pick', {{
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
</script>
"""


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


def page_shell(title, active, body, site_title, sidebar_html=""):
    nav_home = ' class="active"' if active == "home" else ""
    nav_results = ' class="active"' if active == "results" else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
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
{PICK_SCRIPT}
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
    <input type="checkbox" id="chk-{gid}" {checked} onchange="togglePick('{gid}', this)"> I bet on this
  </label>
  <div class="pick-status" id="status-{gid}">Couldn't reach the local pick server &mdash; run <code>python3 scripts/pick_server.py</code> on your machine, then try again.</div>"""


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
    results_window_days = settings.get("track_record_window_days", 7)
    upcoming_window_days = settings.get("days_of_upcoming_odds", 3)
    min_confidence = settings.get("min_confidence_to_show", 55)

    league_order = [l["name"] for l in config.get("leagues", [])]

    games = load_games()

    SITE_DIR.mkdir(parents=True, exist_ok=True)

    upcoming_html, upcoming_leagues = render_upcoming(games, tz_name, upcoming_window_days, min_confidence)
    if not upcoming_html:
        upcoming_html = '<p class="empty">No upcoming games right now. Check back after the next data refresh.</p>'
        upcoming_sidebar = ""
    else:
        upcoming_sidebar = render_sidebar(upcoming_leagues, league_order)
    index_body = f'<p class="updated">Last updated {today_str()} UTC</p>' + upcoming_html
    with open(SITE_DIR / "index.html", "w") as f:
        f.write(page_shell(site_title, "home", index_body, site_title, upcoming_sidebar))

    results_html, results_leagues = render_results(games, tz_name, results_window_days, min_confidence)
    results_sidebar = render_sidebar(results_leagues, league_order) if results_leagues else ""
    results_body = f'<p class="updated">Last updated {today_str()} UTC</p>' + results_html
    with open(SITE_DIR / "results.html", "w") as f:
        f.write(page_shell(f"{site_title} - Track Record", "results", results_body, site_title, results_sidebar))

    print(f"Site built to {SITE_DIR}")


if __name__ == "__main__":
    main()
