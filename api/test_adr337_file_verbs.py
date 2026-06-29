"""
Regression gate — ADR-337 File-Layer Verb Completion.

Guards the working-tree verbs (EditFile / DeleteFile / MoveFile + SearchFiles
exact match) — the rm/mv/Edit half of the repo analogy. The decision rule the
ADR ratifies: names + safety semantics are YARNNN's; parameter contracts
follow Claude Code's tool shapes where a trained model prior exists.

Coverage:
  1. The Edit contract (pure function — Claude Code Edit semantics)
  2. DB-free handler validations (missing inputs, same-path move)
  3. Registry membership (chat + headless + reviewer + HANDLERS)
  4. Permission gate wiring (queueable, path-addressed, dual-path MoveFile,
     governance-lock DENY for the Reviewer caller)
  5. Doc-radius (matrix rows + analogy table + ADR file)

Usage:
    cd api && python test_adr337_file_verbs.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parent
REPO_ROOT = API_ROOT.parent
sys.path.insert(0, str(API_ROOT))

PASS = 0
FAIL = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}  {detail}")


asyncio.set_event_loop(asyncio.new_event_loop())


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# =============================================================================
# 1. The Edit contract — pure function (Claude Code Edit semantics)
# =============================================================================

from services.primitives.workspace import _apply_edit, _exact_snippet  # noqa: E402

content = "alpha: 1\nbeta: 2\nalpha: 1\ngamma: 3\n"

_, err = _apply_edit(content, "delta: 9", "delta: 10", False)
check("edit: old_string_not_found", err is not None and err["error"] == "old_string_not_found")

_, err = _apply_edit(content, "alpha: 1", "alpha: 2", False)
check("edit: old_string_not_unique without replace_all", err is not None and err["error"] == "old_string_not_unique")

new, err = _apply_edit(content, "alpha: 1", "alpha: 2", True)
check("edit: replace_all replaces every occurrence", err is None and new.count("alpha: 2") == 2 and "alpha: 1" not in new)

new, err = _apply_edit(content, "beta: 2", "beta: 5", False)
check("edit: unique match replaces exactly once", err is None and "beta: 5" in new and new.count("alpha: 1") == 2)

_, err = _apply_edit(content, "beta: 2", "beta: 2", False)
check("edit: no_change when old == new", err is not None and err["error"] == "no_change")

_, err = _apply_edit(content, "", "x", False)
check("edit: missing old_string rejected", err is not None and err["error"] == "missing_old_string")

snippet = _exact_snippet("A" * 500 + "NEEDLE" + "B" * 500, "needle")
check("exact-search snippet centers the match (case-insensitive)", "NEEDLE" in snippet and len(snippet) < 300)


# =============================================================================
# 2. DB-free handler validations
# =============================================================================

from services.primitives.workspace import (  # noqa: E402
    handle_edit_file, handle_delete_file, handle_move_file,
)


class _StubAuth:
    client = None
    user_id = "00000000-0000-0000-0000-000000000000"
    caller_identity = "system:test"
    reviewer_caller = False
    agent = None


res = _run(handle_edit_file(_StubAuth(), {"old_string": "a", "new_string": "b"}))
check("EditFile: missing path rejected", res.get("error") == "missing_path", f"got {res}")

res = _run(handle_delete_file(_StubAuth(), {}))
check("DeleteFile: missing path rejected", res.get("error") == "missing_path", f"got {res}")

res = _run(handle_move_file(_StubAuth(), {"path": "system/x.md"}))
check("MoveFile: missing new_path rejected", res.get("error") == "missing_path", f"got {res}")

res = _run(handle_move_file(_StubAuth(), {"path": "system/x.md", "new_path": "system/x.md"}))
check("MoveFile: same source and destination rejected", res.get("error") == "no_change", f"got {res}")


# =============================================================================
# 3. Registry membership — the verbs live on all three surfaces
# =============================================================================

from services.primitives.registry import (  # noqa: E402
    CHAT_PRIMITIVES, HEADLESS_PRIMITIVES, FREDDIE_PRIMITIVES, HANDLERS,
)

for verb in ("EditFile", "DeleteFile", "MoveFile"):
    check(f"{verb} in CHAT_PRIMITIVES", any(t["name"] == verb for t in CHAT_PRIMITIVES))
    check(f"{verb} in HEADLESS_PRIMITIVES", any(t["name"] == verb for t in HEADLESS_PRIMITIVES))
    check(f"{verb} in FREDDIE_PRIMITIVES (ADR-337 D5)", any(t["name"] == verb for t in FREDDIE_PRIMITIVES))
    check(f"{verb} in HANDLERS", verb in HANDLERS)

edit_tool = next(t for t in CHAT_PRIMITIVES if t["name"] == "EditFile")
props = edit_tool["input_schema"]["properties"]
check(
    "EditFile schema is the Claude Code Edit contract (borrowed prior)",
    all(k in props for k in ("path", "old_string", "new_string", "replace_all"))
    and edit_tool["input_schema"]["required"] == ["path", "old_string", "new_string"],
)

search_tool = next(t for t in CHAT_PRIMITIVES if t["name"] == "SearchFiles")
check(
    "SearchFiles schema declares match=semantic|exact (ADR-337 D4)",
    search_tool["input_schema"]["properties"].get("match", {}).get("enum") == ["semantic", "exact"],
)


# =============================================================================
# 4. Permission gate wiring (ADR-307 × ADR-337)
# =============================================================================

from services.primitives.permission import (  # noqa: E402
    GATE_QUEUEABLE_PRIMITIVES, _PATH_ADDRESSED_QUEUEABLE,
    resolve_permission, PermissionDecision, is_read_only,
)
from services.primitives.workspace import _resolve_gate_paths  # noqa: E402

check(
    "all three verbs gate-queueable",
    {"EditFile", "DeleteFile", "MoveFile"} <= GATE_QUEUEABLE_PRIMITIVES,
)
check(
    "path-addressed set is exactly the four write verbs",
    _PATH_ADDRESSED_QUEUEABLE == frozenset({"WriteFile", "EditFile", "DeleteFile", "MoveFile"}),
)
check(
    "new verbs are consequential (fail-closed, not read_only)",
    not any(is_read_only(v) for v in ("EditFile", "DeleteFile", "MoveFile")),
)
check(
    "MoveFile resolves BOTH paths for the gate",
    _resolve_gate_paths("MoveFile", {"path": "operation/a.md", "new_path": "operation/b.md"})
    == ["operation/a.md", "operation/b.md"],
)
check(
    "single-path verbs resolve one path",
    _resolve_gate_paths("DeleteFile", {"path": "/workspace/system/x.md"}) == ["system/x.md"],
)


class _ReviewerAuth:
    client = None
    user_id = "00000000-0000-0000-0000-000000000000"
    caller_identity = "freddie:ai:test"
    reviewer_caller = True
    agent = None


decision, reason = _run(resolve_permission(_ReviewerAuth(), "DeleteFile", {"path": "governance/AUTONOMY.md"}))
check(
    "Reviewer DeleteFile on governance-locked path → DENY (bypass-immune)",
    decision == PermissionDecision.DENY and "topology_locked" in reason,
    f"got {decision} {reason}",
)

# Destination in a locked root (governance/ is reviewer-locked per ADR-320
# CALLER_WRITE_POLICY; constitution/ is NOT — the seat amends it per ADR-319).
decision, reason = _run(resolve_permission(
    _ReviewerAuth(), "MoveFile",
    {"path": "operation/notes.md", "new_path": "governance/_budget.yaml"},
))
check(
    "Reviewer MoveFile INTO a locked root → DENY (dual-path gate)",
    decision == PermissionDecision.DENY and "topology_locked" in reason,
    f"got {decision} {reason}",
)


# =============================================================================
# 5. Doc radius
# =============================================================================

matrix = (REPO_ROOT / "docs" / "architecture" / "primitives-matrix.md").read_text()
check("matrix has EditFile/DeleteFile/MoveFile rows", all(f"`{v}` | file" in matrix for v in ("EditFile", "DeleteFile", "MoveFile")))
check("matrix has the repo-analogy mapping table", "Repo-analogy mapping (ADR-337)" in matrix)
check("ADR-337 exists", (REPO_ROOT / "docs" / "adr" / "ADR-337-file-layer-verb-completion.md").exists())
changelog = (API_ROOT / "prompts" / "CHANGELOG.md").read_text()
check("prompts CHANGELOG has the ADR-337 entry", "ADR-337: working-tree verbs" in changelog)


print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
