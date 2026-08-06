#!/usr/bin/env python3
"""
Final step in the betting automation: apply predictions, build the site,
commit, and push to GitHub to trigger Pages deployment.

This script is meant to be called by a Cowork scheduled task after predictions
have been generated, or by launchd each morning at 8:05 AM.

If predictions haven't been generated yet, it just skips to rebuilding the site
with current data.
"""
import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a shell command and handle errors."""
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}")
    try:
        result = subprocess.run(cmd, shell=True, check=True, cwd=PROJECT_ROOT)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return False

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent
PREDICTIONS_FILE = PROJECT_ROOT / "data" / "my_predictions.json"

# Step 1: Apply predictions (if they exist)
if PREDICTIONS_FILE.exists():
    if not run_command(
        "python3 scripts/apply_predictions.py",
        "Step 1/4: Applying predictions to games.json"
    ):
        sys.exit(1)
    step_num = 2
    message = "Step 2/4: Building static site"
else:
    print(f"\n{'='*60}")
    print("ℹ️  No predictions file found — rebuilding site with current data")
    print(f"{'='*60}")
    step_num = 1
    message = "Step 1/3: Building static site"

# Step 2+: Build the site
if not run_command(
    "python3 scripts/build_site.py",
    f"{message} (index.html + results.html)"
):
    sys.exit(1)

# Step 3+: Commit changes
commit_step = step_num + 1
if not run_command(
    'git add -A && git commit -m "Auto-update: refresh data and regenerate site" || true',
    f"Step {commit_step}/{step_num + 2}: Committing changes (ok if nothing to commit)"
):
    # This is ok to fail silently — nothing to commit is not an error
    pass

# Step 4+: Push to GitHub
push_step = step_num + 2
if not run_command(
    "git push origin main",
    f"Step {push_step}/{step_num + 2}: Pushing to GitHub (triggers Pages deployment)"
):
    print("⚠️  Warning: Could not push to GitHub. Site is updated locally but not deployed.")
    sys.exit(1)

print("\n" + "="*60)
print("✅ Success! Site updated and deployed to GitHub Pages")
print("   View it at: https://sjackson1837.github.io/bet-tracker/")
print("="*60)
