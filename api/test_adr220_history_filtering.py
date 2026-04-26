"""
Test gate — ADR-220 Commit A (filter non-conversation roles from API history).

Per FOUNDATIONS Axiom 9 + ADR-219, session_messages carries six Identity
classes (user, assistant, system, reviewer, agent, external). Only
user/assistant are conversation turns; the others are narrative-bearing
workspace events that surface on /chat (frontend reads them directly)
but must never enter the Claude API messages list — Claude only accepts
user/assistant.

This is the structural backstop that the bug Commit A fixes can never
silently regress. If anyone re-introduces a non-conversation role into
build_history_for_claude's output, the assertion below fails and the
build breaks.

Usage:
    cd api && python test_adr220_history_filtering.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = REPO_ROOT / "api"


def _import_history_builder():
    sys.path.insert(0, str(API_ROOT))
    from routes.chat import build_history_for_claude
    return build_history_for_claude


# =============================================================================
# A1 — every non-conversation role is filtered out of API messages
# =============================================================================

def test_filters_non_conversation_roles() -> None:
    """Six Identity classes go in; only user/assistant come out."""
    build_history_for_claude = _import_history_builder()

    messages = [
        {"role": "user", "content": "hello", "metadata": {}},
        {"role": "assistant", "content": "hi back", "metadata": {}},
        {"role": "system", "content": "workspace event", "metadata": {}},
        {"role": "reviewer", "content": "approved proposal", "metadata": {}},
        {"role": "agent", "content": "task delivered", "metadata": {}},
        {"role": "external", "content": "MCP wrote to memory", "metadata": {}},
    ]

    history = build_history_for_claude(messages, use_structured_format=False)

    roles_in_api = [m["role"] for m in history]
    # Claude API only accepts user + assistant.
    assert all(r in ("user", "assistant") for r in roles_in_api), (
        f"build_history_for_claude leaked non-conversation roles: {roles_in_api}"
    )
    # The four non-conversation rows are dropped entirely.
    assert "system" not in roles_in_api
    assert "reviewer" not in roles_in_api
    assert "agent" not in roles_in_api
    assert "external" not in roles_in_api


def test_user_assistant_still_pass_through() -> None:
    """Conversation rows survive the filter."""
    build_history_for_claude = _import_history_builder()

    messages = [
        {"role": "user", "content": "what's the queue?", "metadata": {}},
        {"role": "assistant", "content": "3 pending proposals.", "metadata": {}},
        {"role": "user", "content": "approve the first one", "metadata": {}},
    ]

    history = build_history_for_claude(messages, use_structured_format=False)
    assert len(history) == 3, f"expected 3 messages through, got {len(history)}"
    # Anthropic's alternation requirement still satisfied (user → assistant → user).
    assert [m["role"] for m in history] == ["user", "assistant", "user"]


def test_filtered_history_starts_with_user() -> None:
    """When the first survivor would be 'assistant' (rare — happens if an
    operator's first turn was preceded by background events) the existing
    'history must start with user' guard still trims. ADR-220 Commit A does
    not interact with that guard — but the combination must still produce
    valid Anthropic-shaped history."""
    build_history_for_claude = _import_history_builder()

    messages = [
        # Simulated: a reviewer verdict before the operator typed anything.
        {"role": "reviewer", "content": "approved", "metadata": {}},
        # First operator turn.
        {"role": "user", "content": "go", "metadata": {}},
        {"role": "assistant", "content": "done", "metadata": {}},
    ]

    history = build_history_for_claude(messages, use_structured_format=False)
    # Reviewer dropped; user/assistant survive in order.
    assert [m["role"] for m in history] == ["user", "assistant"]


def test_mixed_metadata_carrying_envelope() -> None:
    """ADR-219 envelope on an `assistant` row (e.g., a YARNNN reply) must
    survive through the filter unchanged — the filter only looks at role,
    not metadata."""
    build_history_for_claude = _import_history_builder()

    messages = [
        {"role": "user", "content": "what's recent?", "metadata": {}},
        {
            "role": "assistant",
            "content": "I checked the narrative.",
            "metadata": {
                "summary": "Narrative scan",
                "weight": "material",
                "pulse": "addressed",
            },
        },
    ]

    history = build_history_for_claude(messages, use_structured_format=False)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"


# =============================================================================
# Driver
# =============================================================================

def main() -> int:
    tests = [
        ("A1 non-conversation roles filtered out of API messages", test_filters_non_conversation_roles),
        ("A2 user/assistant pass-through", test_user_assistant_still_pass_through),
        ("A3 filtered history still starts with user (Anthropic invariant)", test_filtered_history_starts_with_user),
        ("A4 ADR-219 envelope on assistant row passes through unchanged", test_mixed_metadata_carrying_envelope),
    ]

    failed: list[tuple[str, BaseException]] = []
    for name, fn in tests:
        try:
            fn()
            print(f"  ✓ {name}")
        except BaseException as exc:  # noqa: BLE001
            failed.append((name, exc))
            print(f"  ✗ {name}: {exc}")

    print()
    if failed:
        print(f"FAILED — {len(failed)}/{len(tests)} tests failed")
        return 1
    print(f"PASSED — {len(tests)}/{len(tests)} tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
