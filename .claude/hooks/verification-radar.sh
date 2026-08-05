#!/bin/bash
# Verification radar — SessionStart hook (2026-07-31 eval-layer hardening).
#
# DYNAMIC STATE ONLY (CLAUDE.md §8): computes which verification lanes have
# changes since their last-validated SHA (.claude/validation-ledger.json) and
# nudges toward the right instrument. The criteria live in
# docs/evaluations/VERIFICATION.md — this hook points, it does not teach.
# After a lane's exit criteria are met: .claude/hooks/mark-validated.sh <lane>

cd "$CLAUDE_PROJECT_DIR" 2>/dev/null || cd "$(dirname "$0")/../.."

python3 - <<'PYEOF'
import json, subprocess, os

LEDGER = ".claude/validation-ledger.json"

# lane -> (pathspecs, one-line nudge)
LANES = {
    "prompt":     (["api/agents/", "api/services/primitives/", "api/prompts/"],
                   "prompt ratchets (test_adr383 + test_adr323 + test_envelope_scaffold_ratchet) + CHANGELOG entry"),
    "api":        (["api/services/", "api/routes/", "api/jobs/", "api/mcp_server/"],
                   "targeted pytest gates; wake-path touched -> bare-steward probe preflight; studio -> python3 gates from api/"),
    "web":        (["web/"],
                   "cd web && pnpm build (tsc alone is not verification); UI change -> browser click-pass (E2E lane)"),
    "migrations": (["supabase/migrations/"],
                   "apply via scripts/db/run-migration.sh (--dry-run first); verify the LIVE object "
                   "(pg_policies/\\d+) — the runner's exit code is not verification; RLS touched -> "
                   "falsify as the real principal in a ROLLBACK txn; then mark-validated.sh migrations"),
    "evals":      (["api/scripts/operator/", "docs/evaluations/eval-suites/", "docs/alpha/personas.yaml"],
                   "staleness gates (test_probe_staleness_gate + test_eval_suite_gate)"),
    "claude-md":  (["CLAUDE.md"],
                   "test_claude_md_ratchet + reference sweep"),
}

def sh(*args):
    return subprocess.run(args, capture_output=True, text=True).stdout.strip()

try:
    ledger = json.load(open(LEDGER))
except Exception:
    print(f"[verification-radar] ledger unreadable at {LEDGER} — treat ALL lanes as due; see docs/evaluations/VERIFICATION.md")
    raise SystemExit(0)

head = sh("git", "rev-parse", "--short", "HEAD")
due, clean = [], []
for lane, (specs, nudge) in LANES.items():
    sha = ledger.get("lanes", {}).get(lane, {}).get("sha", "")
    committed = sh("git", "diff", "--name-only", f"{sha}..HEAD", "--", *specs) if sha and sha != "HEAD_INIT" else ""
    uncommitted = sh("git", "status", "--porcelain", "--", *specs)
    files = [l for l in (committed.splitlines()
                         + [u[2:].strip() for u in uncommitted.splitlines()]) if l]
    if files:
        tag = " (+uncommitted)" if uncommitted else ""
        due.append(f"  DUE {lane}{tag} — {len(files)} path(s) since {sha or '?'} (e.g. {files[0]}) -> {nudge}")
    else:
        clean.append(lane)

print(f"VERIFICATION RADAR @ {head} (criteria: docs/evaluations/VERIFICATION.md · mark done: .claude/hooks/mark-validated.sh <lane>)")
if due:
    print("\n".join(due))
else:
    print(f"  all lanes validated at their recorded SHAs")
if clean and due:
    print(f"  clean: {', '.join(clean)}")
PYEOF
