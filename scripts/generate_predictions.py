"""
Cloud replacement for the "ask Claude in Cowork" step.

Reads data/pending_predictions.json, sends every game to the Claude API in one
request, and writes data/my_predictions.json in the exact shape
apply_predictions.py expects.

Needs ANTHROPIC_API_KEY in the environment (a GitHub Actions secret, or .env
locally). Uses urllib so there's no extra dependency to install.

If there are no pending games, it writes an empty object and exits 0 -- a quiet
day is not a failure.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

from utils import DATA_DIR, load_config, get_env

PENDING_PATH = DATA_DIR / "pending_predictions.json"
OUT_PATH = DATA_DIR / "my_predictions.json"

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
MAX_ATTEMPTS = 3

REQUIRED_FIELDS = {
    "predicted_winner",
    "predicted_against_spread",
    "confidence",
    "key_factors",
    "reasoning",
}

SYSTEM_PROMPT = """You are a sharp, disciplined sports betting analyst.

For each game you are given, weigh the actual trend data provided -- recent form,
streaks, head-to-head history, starting pitcher matchups, and weather -- and form
an independent judgment. Do NOT simply pick whichever side the betting market
favors. It is expected that you will sometimes disagree with the market when the
trends support it.

Calibration rules, which matter more than being interesting:
- If trend data is sparse or contradictory for a game, say so and let that LOWER
  your confidence rather than defaulting to the favorite.
- Confidence is a real probability estimate, not enthusiasm. A coin-flip game is
  50-55. Use 75+ only when multiple independent signals agree.
- Do not cluster everything in the 60s. Spread your confidences honestly.

For each game_id you're given, submit a prediction via the submit_predictions
tool. Every game_id you were given must appear exactly once."""

TOOL_NAME = "submit_predictions"
TOOL = {
    "name": TOOL_NAME,
    "description": "Submit a prediction for every game_id provided.",
    "input_schema": {
        "type": "object",
        "properties": {
            "predictions": {
                "type": "object",
                "description": "Maps each game_id to its prediction.",
                "additionalProperties": {
                    "type": "object",
                    "properties": {
                        "predicted_winner": {
                            "type": "string",
                            "description": "Exact team name as given",
                        },
                        "predicted_against_spread": {
                            "type": "string",
                            "description": "Exact team name as given",
                        },
                        "confidence": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                        },
                        "key_factors": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 2,
                            "maxItems": 4,
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "2-4 sentences citing the specific trend data provided",
                        },
                    },
                    "required": list(REQUIRED_FIELDS),
                },
            },
        },
        "required": ["predictions"],
    },
}


def call_claude(model, payload_text, max_tokens):
    body = json.dumps({
        "model": model,
        "max_tokens": max_tokens,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": payload_text}],
        "tools": [TOOL],
        "tool_choice": {"type": "tool", "name": TOOL_NAME},
    }).encode("utf-8")

    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={
            "content-type": "application/json",
            "anthropic-version": API_VERSION,
            "x-api-key": get_env("ANTHROPIC_API_KEY"),
        },
        method="POST",
    )

    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                data = json.load(resp)
            for block in data.get("content", []):
                if block.get("type") == "tool_use" and block.get("name") == TOOL_NAME:
                    return block.get("input", {}).get("predictions", {})
            last_error = f"no {TOOL_NAME} tool call in response: {json.dumps(data)[:500]}"
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:500]
            last_error = f"HTTP {e.code}: {detail}"
            # 4xx other than 429 won't get better by retrying.
            if e.code < 500 and e.code != 429:
                break
        except Exception as e:
            last_error = str(e)

        if attempt < MAX_ATTEMPTS:
            wait = 5 * attempt
            print(f"  attempt {attempt} failed ({last_error}); retrying in {wait}s")
            time.sleep(wait)

    raise RuntimeError(f"Claude API call failed after {attempt} attempt(s): {last_error}")


def main():
    if not PENDING_PATH.exists():
        print("No pending_predictions.json -- nothing to predict.")
        OUT_PATH.write_text("{}")
        return

    with open(PENDING_PATH) as f:
        pending = json.load(f)

    games = pending.get("games", {})
    if not games:
        print("No pending games -- writing empty predictions.")
        OUT_PATH.write_text("{}")
        return

    model = load_config()["settings"].get("claude_model", "claude-sonnet-5")
    print(f"Reasoning through {len(games)} game(s) with {model}...")

    payload_text = (
        f"{pending.get('instructions', '')}\n\n"
        f"Here are the {len(games)} games as JSON:\n\n"
        f"{json.dumps(games, indent=2)}"
    )
    # Roughly 700 output tokens per game, with generous headroom.
    max_tokens = min(32000, 1500 + 900 * len(games))

    predictions = call_claude(model, payload_text, max_tokens)

    # Drop anything malformed rather than letting apply_predictions.py choke.
    clean = {}
    for gid, pred in predictions.items():
        if gid not in games:
            print(f"  ! skipping unknown game_id from model: {gid}")
            continue
        missing = REQUIRED_FIELDS - set(pred)
        if missing:
            print(f"  ! skipping {gid}, missing fields: {sorted(missing)}")
            continue
        try:
            pred["confidence"] = int(round(float(pred["confidence"])))
        except (TypeError, ValueError):
            print(f"  ! skipping {gid}, non-numeric confidence")
            continue
        clean[gid] = pred

    missing_games = set(games) - set(clean)
    if missing_games:
        print(f"  ! model returned no usable pick for {len(missing_games)} game(s)")

    with open(OUT_PATH, "w") as f:
        json.dump(clean, f, indent=2)

    print(f"Wrote {len(clean)} prediction(s) to {OUT_PATH}")
    if not clean:
        print("No usable predictions -- the site will still rebuild with existing data.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
