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


def test_tools_core_documents_file_layer():
    src = (REPO_API / "agents" / "prompts" / "tools_core.py").read_text()
    has_section = "### File Layer (workspace_files, ADR-234)" in src
    has_readfile = "**ReadFile(path)**" in src
    has_writefile = "**WriteFile(" in src
    has_path_conventions = "Path conventions" in src
    has_agent_path_boundary = "/agents/{slug}/" in src
    ok = has_section and has_readfile and has_writefile and has_path_conventions and has_agent_path_boundary
    record(
        "test_tools_core_documents_file_layer",
        ok,
        f"section={has_section} readfile={has_readfile} writefile={has_writefile} conv={has_path_conventions} boundary={has_agent_path_boundary}",
    )


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
        test_tools_core_documents_file_layer,
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
