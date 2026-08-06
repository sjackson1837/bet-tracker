#!/bin/bash
# Setup script to install automated tasks for bet-tracker
# Run this once to set up all automation

set -e

PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
LAUNCHAGENTS_DIR="$HOME/Library/LaunchAgents"

echo "=========================================="
echo "Bet Tracker Automation Setup"
echo "=========================================="
echo ""

# Ensure LaunchAgents directory exists
mkdir -p "$LAUNCHAGENTS_DIR"

# Install the data refresh task (7:30 AM)
echo "✓ Installing data refresh task (7:30 AM)..."
cp "$PROJECT_DIR/scripts/com.stevenjackson.bettracker.refresh.plist" \
   "$LAUNCHAGENTS_DIR/"
launchctl load "$LAUNCHAGENTS_DIR/com.stevenjackson.bettracker.refresh.plist" 2>/dev/null || \
launchctl unload "$LAUNCHAGENTS_DIR/com.stevenjackson.bettracker.refresh.plist" 2>/dev/null || true
launchctl load "$LAUNCHAGENTS_DIR/com.stevenjackson.bettracker.refresh.plist"

# Install the site finalization task (8:05 AM)
echo "✓ Installing site finalization task (8:05 AM)..."
cp "$PROJECT_DIR/scripts/com.stevenjackson.bettracker.finalize.plist" \
   "$LAUNCHAGENTS_DIR/"
launchctl load "$LAUNCHAGENTS_DIR/com.stevenjackson.bettracker.finalize.plist" 2>/dev/null || \
launchctl unload "$LAUNCHAGENTS_DIR/com.stevenjackson.bettracker.finalize.plist" 2>/dev/null || true
launchctl load "$LAUNCHAGENTS_DIR/com.stevenjackson.bettracker.finalize.plist"

echo ""
echo "=========================================="
echo "✅ Automation installed successfully!"
echo "=========================================="
echo ""
echo "Daily schedule:"
echo "  7:30 AM - Local machine: fetch odds, grade results, prepare predictions"
echo "  8:00 AM - Cowork (manual):  generate predictions from pending data"
echo "  8:05 AM - Local machine: apply predictions, build site, deploy to GitHub"
echo ""
echo "Next steps:"
echo "  1. Set up a Cowork scheduled task to generate predictions at 8:00 AM"
echo "     Ask Claude: 'Set up an 8 AM task to generate bet predictions daily'"
echo ""
echo "To check logs:"
echo "  • Data refresh: tail -f /tmp/bet-tracker-refresh.log"
echo "  • Site finalize: tail -f /tmp/bet-tracker-finalize.log"
echo ""
echo "To disable automation:"
echo "  launchctl unload $LAUNCHAGENTS_DIR/com.stevenjackson.bettracker.refresh.plist"
echo "  launchctl unload $LAUNCHAGENTS_DIR/com.stevenjackson.bettracker.finalize.plist"
