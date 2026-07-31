#!/bin/bash
# Mark verification lanes validated at current HEAD.
# Usage: .claude/hooks/mark-validated.sh <lane> [<lane> ...]
# Lanes: prompt api web migrations evals claude-md
# Run ONLY after the lane's exit criteria (docs/evaluations/VERIFICATION.md)
# are actually met — a marked lane silences the radar until the next change.

cd "$(dirname "$0")/../.." || exit 1
[ $# -eq 0 ] && { echo "usage: mark-validated.sh <lane>..."; exit 1; }

python3 - "$@" <<'PYEOF'
import json, subprocess, sys, datetime

LEDGER = ".claude/validation-ledger.json"
VALID = {"prompt", "api", "web", "migrations", "evals", "claude-md"}
lanes = sys.argv[1:]
bad = [l for l in lanes if l not in VALID]
if bad:
    raise SystemExit(f"unknown lane(s) {bad}; valid: {sorted(VALID)}")

head = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                      capture_output=True, text=True).stdout.strip()
today = datetime.date.today().isoformat()
ledger = json.load(open(LEDGER))
for lane in lanes:
    ledger["lanes"][lane] = {"sha": head, "at": today}
json.dump(ledger, open(LEDGER, "w"), indent=2)
print(f"marked {', '.join(lanes)} validated @ {head} ({today}) — commit the ledger with your validation commit")
PYEOF
