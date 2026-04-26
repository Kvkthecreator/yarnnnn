"""
Test gate — ADR-221 Commit C (layered context strategy + recent.md + compaction sunset).

Asserts the load-bearing commitments of Commit C:

A. `recent.md` formatter — the narrative-side rollup is structured by
   role with display ordering reviewer/agent/external/system. Empty roles
   are skipped. Bounded display per role at 10 entries.

B. Compact index pointer — when the recent.md signal indicates entries
   exist, `format_compact_index` emits a one-line pointer. When empty,
   no pointer (no noise).

C. recent.md signal parsing — `_get_recent_md_signal_sync` correctly
   parses the per-role section counts from the markdown header lines
   the formatter writes.

D. Compaction sunset — `maybe_compact_history`, `COMPACTION_THRESHOLD`,
   `truncate_history_by_tokens`, `estimate_message_tokens` no longer
   importable from `routes.chat`. Singular implementation discipline
   per rule 1.

E. Substrate authorship signal still rendered (regression check) —
   ADR-209's existing one-liner survives. The two axes coexist.

Usage:
    cd api && python test_adr221_layered_context.py
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = REPO_ROOT / "api"


def _import_module(name: str):
    sys.path.insert(0, str(API_ROOT))
    import importlib
    return importlib.import_module(name)


# =============================================================================
# A — recent.md formatter
# =============================================================================

def test_format_recent_md_groups_by_role() -> None:
    nd = _import_module("services.back_office.narrative_digest")
    started_at = datetime(2026, 4, 26, 14, 30, tzinfo=timezone.utc)
    recent_by_role = {
        "reviewer": [
            {"summary": "APPROVE order-amzn", "created_at": "2026-04-26T12:00:00+00:00", "task_slug": "trading-execute"},
            {"summary": "REJECT discount-launch", "created_at": "2026-04-26T09:00:00+00:00", "task_slug": "commerce-create-discount"},
        ],
        "agent": [
            {"summary": "competitor-tracker delivered", "created_at": "2026-04-26T10:00:00+00:00", "task_slug": "competitor-scan"},
        ],
        "external": [
            {"summary": "claude.ai wrote to memory:notes", "created_at": "2026-04-26T08:00:00+00:00", "task_slug": None},
        ],
        "system": [],
    }
    out = nd._format_recent_md(started_at, recent_by_role)

    # Header + total counts
    assert "# Recent workspace events" in out
    assert "4 material entries" in out  # 2 + 1 + 1 + 0
    # Per-role section headers in display order with counts
    assert "## Reviewer verdicts (2)" in out
    assert "## Agent task completions (1)" in out
    assert "## External (MCP) writes (1)" in out
    # Empty role section omitted
    assert "## System events" not in out
    # Most-recent-first within reviewer (approve at 12:00 should appear before reject at 09:00)
    rev_section_start = out.index("## Reviewer verdicts")
    approve_idx = out.index("APPROVE order-amzn", rev_section_start)
    reject_idx = out.index("REJECT discount-launch", rev_section_start)
    assert approve_idx < reject_idx, "entries within role should be most-recent first"
    # Task slug surfaced when present
    assert "task: `trading-execute`" in out
    # Author trailer for ADR-221 traceability
    assert "system:narrative-digest" in out


def test_format_recent_md_caps_at_10_per_role() -> None:
    nd = _import_module("services.back_office.narrative_digest")
    started_at = datetime(2026, 4, 26, 14, 30, tzinfo=timezone.utc)
    recent_by_role = {
        "reviewer": [
            {
                "summary": f"verdict {i}",
                "created_at": f"2026-04-26T{(i % 24):02d}:00:00+00:00",
                "task_slug": None,
            }
            for i in range(15)
        ],
        "agent": [],
        "external": [],
        "system": [],
    }
    out = nd._format_recent_md(started_at, recent_by_role)
    # Section count reflects all 15
    assert "## Reviewer verdicts (15)" in out
    # Display caps at 10 — the 5 oldest land in a "+5 more" line
    assert "plus 5 more" in out


# =============================================================================
# B — Compact index pointer rendered when recent.md exists
# =============================================================================

def test_compact_index_renders_recent_md_pointer() -> None:
    wm = _import_module("services.working_memory")
    working_memory = {
        "workspace_state": {
            "identity": "rich",
            "brand": "set",
            "tasks_active": 2,
            "tasks_stale": 0,
            "documents": 3,
            "context_domains": 4,
            "agents_flagged": [],
        },
        "active_tasks": [],
        "context_domains": [],
        "platforms": [],
        "agents": [],
        "recent_uploads": [],
        "recent_authorship": {"window_hours": 24, "total": 0, "by_layer": {}},
        # The new ADR-221 signal — populated → expect pointer to render
        "recent_md": {
            "exists": True,
            "total": 7,
            "by_role": {"reviewer": 3, "agent": 2, "external": 1, "system": 1},
            "updated_at": "2026-04-26T14:30:00+00:00",
        },
    }
    out = wm.format_compact_index(working_memory)
    assert "/workspace/memory/recent.md" in out
    # Per-role breakdown surfaces in the one-liner
    assert "3 reviewer" in out
    assert "2 agent" in out
    assert "1 external" in out
    assert "1 system" in out
    # Total in the section header
    assert "7 material non-conversation" in out


def test_compact_index_no_pointer_when_recent_md_empty() -> None:
    wm = _import_module("services.working_memory")
    working_memory = {
        "workspace_state": {
            "identity": "rich", "brand": "set",
            "tasks_active": 0, "tasks_stale": 0, "documents": 0,
            "context_domains": 0, "agents_flagged": [],
        },
        "active_tasks": [],
        "context_domains": [],
        "platforms": [],
        "agents": [],
        "recent_uploads": [],
        "recent_authorship": {"window_hours": 24, "total": 0, "by_layer": {}},
        "recent_md": {"exists": False, "total": 0, "by_role": {}, "updated_at": None},
    }
    out = wm.format_compact_index(working_memory)
    # No pointer when recent.md doesn't exist or is empty
    assert "/workspace/memory/recent.md" not in out or "Recent events" not in out


# =============================================================================
# C — recent.md signal parsing
# =============================================================================

def test_recent_md_signal_parses_role_counts() -> None:
    """The signal parser reads the markdown headers narrative_digest._format_recent_md
    writes, returning per-role counts without loading the full body."""
    wm = _import_module("services.working_memory")

    # Build a realistic recent.md content blob (matches the formatter shape)
    sample_content = """\
# Recent workspace events
Last updated: 2026-04-26 14:30 UTC · 24h window · 7 material entries

_Material non-conversation invocations rolled up by `back-office-narrative-digest`._

## Reviewer verdicts (3)
- 2h ago — APPROVE thing
- 5h ago — REJECT thing
- 1d ago — APPROVE other

## Agent task completions (2)
- 4h ago — agent A
- 1d ago — agent B

## External (MCP) writes (1)
- 5h ago — claude.ai wrote

## System events (1)
- 1d ago — digest run

<!-- author: system:narrative-digest · ADR-221 -->
"""

    # Mock client with that content for path /workspace/memory/recent.md
    class FakeResp:
        def __init__(self, data):
            self.data = data

    class FakeChain:
        def __init__(self, data):
            self.data = data
        def select(self, *a, **kw): return self
        def eq(self, *a, **kw): return self
        def limit(self, *a, **kw): return self
        def execute(self):
            return FakeResp(self.data)

    class FakeClient:
        def table(self, name):
            assert name == "workspace_files"
            return FakeChain([{"content": sample_content, "updated_at": "2026-04-26T14:30:00+00:00"}])

    signal = wm._get_recent_md_signal_sync("u-1", FakeClient())
    assert signal["exists"] is True
    assert signal["total"] == 7
    assert signal["by_role"] == {"reviewer": 3, "agent": 2, "external": 1, "system": 1}


def test_recent_md_signal_missing_file_safe() -> None:
    wm = _import_module("services.working_memory")

    class FakeChain:
        def select(self, *a, **kw): return self
        def eq(self, *a, **kw): return self
        def limit(self, *a, **kw): return self
        def execute(self):
            class R:
                data = []
            return R()

    class FakeClient:
        def table(self, name): return FakeChain()

    signal = wm._get_recent_md_signal_sync("u-1", FakeClient())
    assert signal["exists"] is False
    assert signal["total"] == 0


# =============================================================================
# D — Compaction sunset
# =============================================================================

def test_compaction_helpers_deleted_from_chat_module() -> None:
    """maybe_compact_history + friends are not importable. Singular
    implementation rule 1 — conversation.md is the singular compaction
    substrate."""
    chat = _import_module("routes.chat")
    deleted_names = [
        "maybe_compact_history",
        "COMPACTION_THRESHOLD",
        "COMPACTION_PROMPT",
        "truncate_history_by_tokens",
        "estimate_message_tokens",
        "MAX_HISTORY_TOKENS",
    ]
    for name in deleted_names:
        assert not hasattr(chat, name), (
            f"routes.chat.{name} should be deleted per ADR-221 Commit C "
            f"(singular implementation; conversation.md is the only compaction substrate)"
        )


def test_build_history_signature_no_max_tokens_or_compaction_block() -> None:
    """build_history_for_claude's signature simplified: only `messages` +
    `use_structured_format`. No `max_tokens`, no `compaction_block`."""
    chat = _import_module("routes.chat")
    import inspect
    sig = inspect.signature(chat.build_history_for_claude)
    params = list(sig.parameters.keys())
    assert params == ["messages", "use_structured_format"], (
        f"build_history_for_claude signature changed unexpectedly: {params}"
    )


# =============================================================================
# E — Substrate authorship signal preserved (regression check)
# =============================================================================

def test_substrate_authorship_signal_still_rendered() -> None:
    """ADR-209's one-liner must survive ADR-221 Commit C alongside
    the new narrative-events one-liner. They are complementary axes."""
    wm = _import_module("services.working_memory")
    working_memory = {
        "workspace_state": {
            "identity": "rich", "brand": "set",
            "tasks_active": 0, "tasks_stale": 0, "documents": 0,
            "context_domains": 0, "agents_flagged": [],
        },
        "active_tasks": [],
        "context_domains": [],
        "platforms": [],
        "agents": [],
        "recent_uploads": [],
        # ADR-209 signal: 23 revisions in 24h
        "recent_authorship": {
            "window_hours": 24,
            "total": 23,
            "by_layer": {"operator": 3, "yarnnn": 12, "agent": 5, "system": 3},
        },
        # ADR-221 signal: 7 narrative events
        "recent_md": {
            "exists": True,
            "total": 7,
            "by_role": {"reviewer": 3, "agent": 2, "external": 1, "system": 1},
            "updated_at": "2026-04-26T14:30:00+00:00",
        },
    }
    out = wm.format_compact_index(working_memory)
    # ADR-209 line still present
    assert "Recent activity (24h, 23 revisions)" in out
    assert "ListRevisions" in out
    # ADR-221 line present alongside
    assert "Recent events (24h, 7 material non-conversation)" in out
    assert "/workspace/memory/recent.md" in out


def test_compact_index_within_token_ceiling() -> None:
    """The 600-token ceiling (ADR-174) must hold even with the new pointer."""
    wm = _import_module("services.working_memory")
    working_memory = {
        "workspace_state": {
            "identity": "rich", "brand": "set",
            "tasks_active": 8, "tasks_stale": 2, "documents": 5,
            "context_domains": 6, "agents_flagged": [],
            "proposals_pending": 3,
        },
        "active_tasks": [
            {"slug": f"task-{i}", "schedule": "daily", "last_run": f"{i}h", "next_run": f"{i+1}h", "output_kind": "produces_deliverable"}
            for i in range(8)
        ],
        "context_domains": [
            {"domain": f"d{i}", "file_count": 5, "health": "healthy", "temporal": False}
            for i in range(6)
        ],
        "platforms": [{"platform": "slack", "status": "active"}],
        "agents": [{"origin": "user_configured", "title": "T"}],
        "recent_uploads": [],
        "recent_authorship": {
            "window_hours": 24, "total": 23,
            "by_layer": {"operator": 3, "yarnnn": 12, "agent": 5, "system": 3},
        },
        "recent_md": {
            "exists": True, "total": 7,
            "by_role": {"reviewer": 3, "agent": 2, "external": 1, "system": 1},
            "updated_at": "2026-04-26T14:30:00+00:00",
        },
    }
    out = wm.format_compact_index(working_memory)
    # Conservative token estimate (4 chars per token) — enforce 600-token ceiling.
    estimated_tokens = len(out) // 4
    assert estimated_tokens <= 600, (
        f"compact index exceeds 600-token ceiling: ~{estimated_tokens} tokens "
        f"({len(out)} chars). New ADR-221 pointer pushed it over."
    )


# =============================================================================
# Driver
# =============================================================================

def main() -> int:
    tests = [
        ("A1 recent.md formatter groups by role with display ordering", test_format_recent_md_groups_by_role),
        ("A2 recent.md formatter caps display at 10 per role", test_format_recent_md_caps_at_10_per_role),
        ("B1 compact index renders recent.md pointer when populated", test_compact_index_renders_recent_md_pointer),
        ("B2 compact index omits pointer when recent.md empty", test_compact_index_no_pointer_when_recent_md_empty),
        ("C1 recent.md signal parser reads role counts", test_recent_md_signal_parses_role_counts),
        ("C2 recent.md signal returns safe default when missing", test_recent_md_signal_missing_file_safe),
        ("D1 compaction helpers deleted from routes.chat", test_compaction_helpers_deleted_from_chat_module),
        ("D2 build_history_for_claude signature simplified", test_build_history_signature_no_max_tokens_or_compaction_block),
        ("E1 ADR-209 substrate authorship signal still rendered", test_substrate_authorship_signal_still_rendered),
        ("E2 compact index stays under 600-token ceiling with new pointer", test_compact_index_within_token_ceiling),
    ]

    failed: list[tuple[str, BaseException]] = []
    for name, fn in tests:
        try:
            fn()
            print(f"  ✓ {name}")
        except BaseException as exc:  # noqa: BLE001
            failed.append((name, exc))
            print(f"  ✗ {name}: {exc}")
            import traceback
            traceback.print_exc()

    print()
    if failed:
        print(f"FAILED — {len(failed)}/{len(tests)} tests failed")
        return 1
    print(f"PASSED — {len(tests)}/{len(tests)} tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
