#!/bin/bash
# Run this from VS Code's terminal (or any terminal on your own machine) whenever
# you want fresh data. It needs real internet access to The Odds API, ESPN, and
# Open-Meteo, which is why it can't be run from inside a Claude/Cowork session --
# run it here, then go ask Claude to generate predictions from the results.
set -e
cd "$(dirname "$0")/.."

echo "== 1/3: fetching latest odds =="
python3 scripts/fetch_odds.py

echo ""
echo "== 2/3: grading any games that finished since the last refresh =="
python3 scripts/fetch_results.py

echo ""
echo "== 3/3: gathering trend/weather context for upcoming games =="
python3 scripts/prepare_predictions.py

echo ""
echo "Done. Now go back to Claude in Cowork and say something like:"
echo '  "Generate predictions from data/pending_predictions.json"'
echo "Claude will reason through each game and finish rebuilding the site."
