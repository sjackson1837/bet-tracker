#!/bin/bash
# Double-click this file in Finder to start the local pick server, so you can
# mark bets with a checkbox directly on site/index.html. Leave the terminal
# window it opens running in the background; close it when you're done.
cd "$(dirname "$0")/.."
python3 scripts/pick_server.py
