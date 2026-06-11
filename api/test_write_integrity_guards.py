"""
Regression gate — Write-Integrity Guards (2026-06-11 alpha substrate audit).

Guards the three-part fix for the 0-byte-WriteFile class surfaced by the
2026-06-11 alpha workspace audit (receipts: kvk weekly-performance-review/
2026-06-08/output.md — 12 consecutive 0-byte revisions; yarnnn-author
operation/authored/_signal.md — 4,908 bytes of ground truth wiped to 0
bytes on 2026-06-09 by nine consecutive empty writes):

  1. Reviewer dispatch loop (api/agents/reviewer_agent.py)
     - max_tokens raised 2048 → 8192 (composed deliverables exceed 2048
       output tokens once JSON-escaped into a single WriteFile input)
     - stop_reason == "max_tokens" truncation guard: the FINAL tool_use of
       a truncated response carries incomplete input and must NOT execute.

  2. WriteFile primitive (api/services/primitives/workspace.py)
     - empty/whitespace content is rejected with error=empty_content_blocked
       (defense-in-depth: a truncated tool input drops `content`, which
       previously defaulted to "" and overwrote real substrate).

  3. Output routes (api/routes/recurrences.py)
     - dated-folder discovery walks ANY file under the report root (the
       Reviewer writes sections/ + sys_manifest.json; output.md may be
       absent or empty), and the read path falls back to the singular
       compose helper (compose_task_output_html) when output.md is
       missing/empty.

Usage:
    cd api && python test_write_integrity_guards.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parent
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


# =============================================================================
# 1. Reviewer dispatch loop — truncation guard + raised ceiling
# =============================================================================

reviewer_src = (API_ROOT / "agents" / "reviewer_agent.py").read_text()

check(
    "reviewer loop max_tokens raised to 8192",
    "max_tokens=8192" in reviewer_src,
)
check(
    "reviewer loop no longer uses max_tokens=2048",
    "max_tokens=2048" not in reviewer_src,
)
check(
    "reviewer loop detects stop_reason == 'max_tokens'",
    'stop_reason", None) == "max_tokens"' in reviewer_src,
)
check(
    "truncated final tool call is skipped (not executed)",
    "response_truncated and _tu_idx == len(tool_uses) - 1" in reviewer_src,
)
check(
    "truncated tool call returns is_error tool_result to the model",
    '"is_error": True' in reviewer_src and "NOT executed" in reviewer_src,
)


# =============================================================================
# 2. WriteFile primitive — empty-content guard (functional)
# =============================================================================

from services.primitives.workspace import handle_write_file  # noqa: E402


class _StubAuth:
    """The guard fires before any scope/DB access — no client needed."""
    client = None
    user_id = "00000000-0000-0000-0000-000000000000"
    caller_identity = "system:test"
    agent = None


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


asyncio.set_event_loop(asyncio.new_event_loop())

res_empty = _run(handle_write_file(_StubAuth(), {"path": "persona/standing_intent.md", "content": ""}))
check(
    "WriteFile blocks content='' (missing-content truncation shape)",
    res_empty.get("success") is False and res_empty.get("error") == "empty_content_blocked",
    f"got: {res_empty}",
)

res_ws = _run(handle_write_file(_StubAuth(), {"path": "persona/standing_intent.md", "content": "   \n\t "}))
check(
    "WriteFile blocks whitespace-only content",
    res_ws.get("success") is False and res_ws.get("error") == "empty_content_blocked",
    f"got: {res_ws}",
)

res_missing = _run(handle_write_file(_StubAuth(), {"path": "persona/standing_intent.md"}))
check(
    "WriteFile blocks absent content key (defaulted '')",
    res_missing.get("success") is False and res_missing.get("error") == "empty_content_blocked",
    f"got: {res_missing}",
)

res_append_empty = _run(handle_write_file(_StubAuth(), {"path": "x.md", "content": "", "mode": "append"}))
check(
    "WriteFile blocks empty append too (no-op append is a truncation symptom)",
    res_append_empty.get("success") is False,
    f"got: {res_append_empty}",
)


# =============================================================================
# 3. Output routes — folder discovery + compose fallback
# =============================================================================

from routes.recurrences import _derive_date_folders  # noqa: E402

root = "/workspace/operation/reports/weekly-performance-review"
paths = [
    f"{root}/2026-06-08/sections/1-portfolio-totals.md",
    f"{root}/2026-06-08/sys_manifest.json",
    f"{root}/2026-06-08/output.md",
    f"{root}/2026-06-01/sections/1-portfolio-totals.md",  # no output.md — must still surface
    f"{root}/run_log.md",  # root-level file — must NOT surface as a folder
    "/workspace/operation/reports/other-slug/2026-06-09/output.md",  # different root
]
folders = _derive_date_folders(paths, root)
check(
    "folder discovery surfaces sections-only folders (no output.md required)",
    folders == ["2026-06-08", "2026-06-01"],
    f"got: {folders}",
)
check(
    "folder discovery excludes root-level files and foreign roots",
    "run_log.md" not in folders and "2026-06-09" not in folders,
)

routes_src = (API_ROOT / "routes" / "recurrences.py").read_text()
check(
    "read path falls back to compose_task_output_html when output.md empty",
    "_read_output_for_folder" in routes_src
    and "compose_task_output_html" in routes_src
    and "output_md and output_md.strip()" in routes_src,
)
check(
    "no route discovers outputs via output.md-only LIKE anymore",
    '/%/output.md"' not in routes_src,
)


# =============================================================================

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
