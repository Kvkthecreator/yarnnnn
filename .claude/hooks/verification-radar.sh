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
                   "prompt ratchets (test_adr632 §5 + test_adr630 index ceiling) + CHANGELOG entry"),
    "api":        (["api/services/", "api/routes/", "api/jobs/", "api/mcp_server/"],
                   "targeted pytest gates; standing-work path touched -> test_adr618 + test_adr569; studio -> python3 gates from api/"),
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
    # ADR-647/648 — THE CONTEXT BUDGET. These four files decide what enters a
    # prompt and what it costs, and every one of their invariants is invisible
    # at review: a caching rule that silently applies to one router door, a
    # clip that forgets its notice, a trim that drops from the middle and
    # re-writes the cache at 1.25x. All are green-on-read and wrong in
    # production. SINGULAR IMPLEMENTATION: caching lives ONLY in
    # model_router._build_messages (callers stay provider-blind), the read cap
    # ONLY in workspace._clip_read, the history ceiling ONLY in
    # lanes._clamp_history_chars. A second home for any of them is the defect.
    "context-budget": (["api/services/model_router.py",
                        "api/services/primitives/workspace.py",
                        "api/routes/lanes.py",
                        "api/services/lane_runner.py"],
                       "python3 test_adr647_history_caching.py + test_adr648_bounded_context.py "
                       "+ test_adr634_prompt_caching.py (ALL script-shaped — read the count, not "
                       "the exit code); a caching/clip/trim change must be FALSIFIED, and a gate "
                       "that crashes reports nothing"),
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
