#!/bin/bash
# Verification radar — SessionStart hook.
#
# DYNAMIC STATE ONLY (CLAUDE.md §Hooks): computes which verification lanes have
# changes since their last-validated SHA (.claude/validation-ledger.json) and
# nudges toward the right instrument. The criteria live in
# docs/evaluations/VERIFICATION.md — this hook points, it does not teach.
# After a lane's exit criteria are met: .claude/hooks/mark-validated.sh <lane>
# (mark-validated derives its lane list from the LANES keys below — one source).

cd "$CLAUDE_PROJECT_DIR" 2>/dev/null || cd "$(dirname "$0")/../.."

python3 - <<'PYEOF'
import json, subprocess

LEDGER = ".claude/validation-ledger.json"

# lane -> (pathspecs, one-line nudge). Pathspecs mirror the lane headers in VERIFICATION.md.
LANES = {
    "prompt":     (["api/services/lane_runner.py", "api/services/authoring.py", "api/services/apps/",
                    "api/services/standing_work.py", "api/services/workspace_paths.py",
                    "api/services/skills/", "api/services/primitives/", "api/prompts/"],
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
                   "python3 -m pytest api/test_claude_md_ratchet.py -q (ceiling + cited paths exist)"),
    "context-budget": (["api/services/model_router.py", "api/services/primitives/workspace.py",
                        "api/routes/lanes.py", "api/services/lane_runner.py"],
                       "test_adr647_history_caching + test_adr648_bounded_context + test_adr634_prompt_caching "
                       "(script-shaped — read the count, not the exit code); a caching/clip/trim change must be FALSIFIED"),
}

def sh(*args):
    return subprocess.run(args, capture_output=True, text=True).stdout.strip()

try:
    ledger = json.load(open(LEDGER))
except Exception:
    print(f"[verification-radar] ledger unreadable at {LEDGER} — treat ALL lanes as due; see docs/evaluations/VERIFICATION.md")
    raise SystemExit(0)

def diff_base(lane, sha):
    """The recorded sha is HEAD at marking time — one commit BEFORE the validation
    commit that carries both the change and the ledger. Diffing from it reports every
    lane DUE by exactly one commit forever. Walk forward to the commit that recorded
    this mark and diff from there; fall back to the recorded sha."""
    for c in sh("git", "log", "--reverse", "--format=%h", f"{sha}..HEAD", "--", LEDGER).splitlines():
        try:
            recorded = json.loads(sh("git", "show", f"{c}:{LEDGER}"))["lanes"][lane]["sha"] == sha
        except Exception:
            continue
        # Only a commit whose PARENT is the recorded sha is the validation commit. A
        # retroactively seeded entry (or an interleaved foreign commit) fails this and
        # falls back to the recorded sha: a false DUE is noise, a false clean is a lie.
        if recorded and sh("git", "rev-parse", "--short", f"{c}^") == sha:
            return c
    return sha

head = sh("git", "rev-parse", "--short", "HEAD")
due, clean = [], []
for lane, (specs, nudge) in LANES.items():
    sha = ledger.get("lanes", {}).get(lane, {}).get("sha", "")
    if not sha:
        due.append(f"  DUE {lane} — never validated (no ledger entry) -> {nudge}")
        continue
    committed = sh("git", "diff", "--name-only", f"{diff_base(lane, sha)}..HEAD", "--", *specs)
    uncommitted = sh("git", "status", "--porcelain", "--", *specs)
    files = [l for l in (committed.splitlines()
                         + [u[2:].strip() for u in uncommitted.splitlines()]) if l]
    if files:
        tag = " (+uncommitted)" if uncommitted else ""
        due.append(f"  DUE {lane}{tag} — {len(files)} path(s) since {sha} (e.g. {files[0]}) -> {nudge}")
    else:
        clean.append(lane)

print(f"VERIFICATION RADAR @ {head} (criteria: docs/evaluations/VERIFICATION.md · mark done: .claude/hooks/mark-validated.sh <lane>)")
if due:
    print("\n".join(due))
else:
    print("  all lanes validated at their recorded SHAs")
if clean and due:
    print(f"  clean: {', '.join(clean)}")
PYEOF
