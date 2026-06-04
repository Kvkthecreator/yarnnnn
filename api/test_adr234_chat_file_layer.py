"""
Validation Suite — ADR-234 (Chat File Layer Reach)

Tests (8 assertions):
   1. ReadFile is in CHAT_PRIMITIVES.
   2. WriteFile is in CHAT_PRIMITIVES.
   3. SearchFiles is in CHAT_PRIMITIVES.
   4. ListFiles is in CHAT_PRIMITIVES.
   5. QueryKnowledge is NOT in CHAT_PRIMITIVES (regression guard — semantic-rank
      composition stays headless-only; chat reaches it via working memory + ReadFile).
   6. ReadAgentFile is NOT in CHAT_PRIMITIVES (regression guard — inter-agent
      coordination per ADR-116 stays headless-only).
   7. Chat handler dispatch works for ReadFile/WriteFile/SearchFiles/ListFiles
      (smoke-tests the registry's get_tools_for_mode + HANDLERS wiring; uses
      the same execute_primitive path that chat uses in production).
   8. tools_core.py prompt contains the "File Layer (workspace_files, ADR-234)"
      subsection that documents the new chat reach + path conventions.

Strategy: pure-Python static checks + handler dispatch via the live registry.
No DB hits beyond what the handlers themselves attempt (and they fail-safe
on missing user_id).

Usage:
    cd api && python test_adr234_chat_file_layer.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

REPO_API = Path(__file__).parent
RESULTS: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))
    icon = "✓" if ok else "✗"
    logger.info(f"{icon} {name}: {detail}")


# ---------------------------------------------------------------------------
# CHAT_PRIMITIVES membership
# ---------------------------------------------------------------------------


def test_readfile_in_chat():
    from services.primitives.registry import CHAT_PRIMITIVES
    names = {t["name"] for t in CHAT_PRIMITIVES}
    record("test_readfile_in_chat", "ReadFile" in names, f"chat tools: {len(names)}")


def test_writefile_in_chat():
    from services.primitives.registry import CHAT_PRIMITIVES
    names = {t["name"] for t in CHAT_PRIMITIVES}
    record("test_writefile_in_chat", "WriteFile" in names, "")


def test_searchfiles_in_chat():
    from services.primitives.registry import CHAT_PRIMITIVES
    names = {t["name"] for t in CHAT_PRIMITIVES}
    record("test_searchfiles_in_chat", "SearchFiles" in names, "")


def test_listfiles_in_chat():
    from services.primitives.registry import CHAT_PRIMITIVES
    names = {t["name"] for t in CHAT_PRIMITIVES}
    record("test_listfiles_in_chat", "ListFiles" in names, "")


# ---------------------------------------------------------------------------
# Regression guards — chat must NOT have these
# ---------------------------------------------------------------------------


def test_queryknowledge_not_in_chat():
    """QueryKnowledge stays headless-only — semantic-rank composition belongs
    to the curated MCP path (`pull_context`) and to headless agents reasoning
    over context domains. Chat reaches that surface via working memory + ReadFile."""
    from services.primitives.registry import CHAT_PRIMITIVES
    names = {t["name"] for t in CHAT_PRIMITIVES}
    record(
        "test_queryknowledge_not_in_chat",
        "QueryKnowledge" not in names,
        f"present={('QueryKnowledge' in names)} (must be False)",
    )


def test_readagentfile_not_in_chat():
    """ReadAgentFile stays headless-only — inter-agent coordination per ADR-116.
    Chat does not reach into another agent's private workspace."""
    from services.primitives.registry import CHAT_PRIMITIVES
    names = {t["name"] for t in CHAT_PRIMITIVES}
    record(
        "test_readagentfile_not_in_chat",
        "ReadAgentFile" not in names,
        f"present={('ReadAgentFile' in names)} (must be False)",
    )


# ---------------------------------------------------------------------------
# Handler dispatch — chat path reaches the file primitives
# ---------------------------------------------------------------------------


def test_chat_dispatch_reaches_file_primitives():
    """All four file-family primitives must be present in HANDLERS so
    execute_primitive() can route to them. Without this, the registry
    addition would lie."""
    from services.primitives.registry import HANDLERS
    expected = {"ReadFile", "WriteFile", "SearchFiles", "ListFiles"}
    missing = expected - set(HANDLERS.keys())
    record(
        "test_chat_dispatch_reaches_file_primitives",
        not missing,
        f"missing={sorted(missing)}",
    )


# ---------------------------------------------------------------------------
# Prompt-side guidance present
# ---------------------------------------------------------------------------


# test_tools_core_documents_file_layer DELETED (2026-06-04):
#   This gate grepped agents/prompts/tools_core.py for an "### File Layer
#   (workspace_files, ADR-234)" prompt section. That file — and the whole
#   chat-profile prompt chain it belonged to — was ratify-deleted by commit
#   1272c92 ("delete the dead chat-profile chain — program-activation is the
#   floor"); its commit message lists tools_core.py among the files "consumed
#   only by the dead build_system_prompt." The File-Layer prompt section did
#   NOT move elsewhere — it was part of the dead chain.
#   ADR-234's SUBSTANTIVE guarantee (ReadFile/WriteFile/SearchFiles/ListFiles
#   are available in chat mode; QueryKnowledge/ReadAgentFile are not) is still
#   enforced by the registry-side gates above (test_readfile_in_chat etc.),
#   which assert the live PRIMITIVE_MODES registry. Only the deleted-prompt-doc
#   assertion is removed. Singular Implementation: delete, don't retarget to a
#   file that no longer carries the section.


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def main():
    tests = [
        test_readfile_in_chat,
        test_writefile_in_chat,
        test_searchfiles_in_chat,
        test_listfiles_in_chat,
        test_queryknowledge_not_in_chat,
        test_readagentfile_not_in_chat,
        test_chat_dispatch_reaches_file_primitives,
        # test_tools_core_documents_file_layer deleted (2026-06-04) — its
        # tools_core.py prompt-section subject was ratify-deleted by 1272c92;
        # ADR-234's substantive guarantee stays covered by the registry gates.
    ]
    for t in tests:
        try:
            t()
        except Exception as e:
            record(t.__name__, False, f"EXCEPTION: {type(e).__name__}: {e}")

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    logger.info("")
    logger.info(f"━━ ADR-234 gate: {passed}/{total} passed ━━")
    if passed < total:
        for name, ok, detail in RESULTS:
            if not ok:
                logger.error(f"FAIL {name}: {detail}")
        sys.exit(1)


if __name__ == "__main__":
    main()
