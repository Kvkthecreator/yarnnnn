"""
ADR-237 regression gate — chat role-based design system.

Asserts seven invariants for the dispatch grammar landed in ADR-237
(Round 2 of the ADR-236 frontend cockpit coherence pass).

Same Python-test-over-TS-source pattern as ADR-238 (no JS test runner
in this repo today; see ADR-236 Rule 3 + ADR-238 §"Test gate" for
rationale).

Run via:
    python -m pytest api/test_adr237_chat_role_grammar.py -v

Or as a standalone script:
    python api/test_adr237_chat_role_grammar.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

WEB_DISPATCH = REPO_ROOT / "web" / "components" / "tp" / "MessageDispatch.tsx"
WEB_ROW = REPO_ROOT / "web" / "components" / "tp" / "MessageRow.tsx"
WEB_TPMESSAGES_LEGACY = REPO_ROOT / "web" / "components" / "tp" / "TPMessages.tsx"
WEB_CHAT_PANEL = REPO_ROOT / "web" / "components" / "tp" / "ChatPanel.tsx"
WEB_DESK_TYPES = REPO_ROOT / "web" / "types" / "desk.ts"


def _read(p: Path) -> str:
    if not p.exists():
        raise AssertionError(f"Missing file: {p.relative_to(REPO_ROOT)}")
    return p.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Test gate
# ---------------------------------------------------------------------------

def test_message_dispatch_module_exists_with_required_surface():
    """Assertion #1: MessageDispatch.tsx exposes the dispatch grammar
    surface — `MessageShape` type, `resolveMessageShape` function,
    `MessageRenderer` component."""
    src = _read(WEB_DISPATCH)
    expected = [
        "export type MessageShape",
        "export function resolveMessageShape",
        "export function MessageRenderer",
    ]
    for ex in expected:
        assert ex in src, f"MessageDispatch.tsx missing export: {ex}"


def test_message_row_module_exists_with_required_surface():
    """Assertion #2: MessageRow.tsx exposes the row wrapper surface."""
    src = _read(WEB_ROW)
    assert "export function MessageRow" in src, (
        "MessageRow.tsx must export `MessageRow` per ADR-237 D2."
    )
    assert "export interface MessageRowProps" in src, (
        "MessageRow.tsx must export `MessageRowProps` interface."
    )


def test_legacy_tpmessages_deleted():
    """Assertion #3: TPMessages.tsx (ADR-023 legacy, dead code) is
    deleted. Regression guard against accidental re-creation."""
    assert not WEB_TPMESSAGES_LEGACY.exists(), (
        "web/components/tp/TPMessages.tsx must NOT exist — deleted by "
        "ADR-237 D4 (verified dead, zero imports across the repo)."
    )


def test_chat_panel_imports_dispatch_and_row():
    """Assertion #4: ChatPanel.tsx imports MessageRenderer / MessageRow
    from the new modules. The dispatch path is the singular render
    grammar; ChatPanel does not reach for per-role components directly."""
    src = _read(WEB_CHAT_PANEL)
    assert "from '@/components/tp/MessageRow'" in src, (
        "ChatPanel.tsx must import MessageRow per ADR-237 D5."
    )
    assert "MessageRow" in src, (
        "ChatPanel.tsx must reference MessageRow."
    )


def test_chat_panel_no_inline_role_dispatch():
    """Assertion #5: ChatPanel.tsx no longer contains the inline
    `if (msg.role === 'reviewer')` dispatch from the pre-ADR-237 body.
    Regression guard against re-inlining the role switch — the
    dispatcher owns role-shape resolution now."""
    src = _read(WEB_CHAT_PANEL)
    forbidden = [
        "if (msg.role === 'reviewer')",
        "if (msg.role === 'agent')",
    ]
    for f in forbidden:
        assert f not in src, (
            f"ChatPanel.tsx contains forbidden inline role dispatch "
            f"`{f}` — Singular Implementation violation per ADR-237 D5. "
            "All role-shape resolution must live in MessageDispatch.tsx."
        )


def test_dispatch_handles_all_six_roles_exhaustively():
    """Assertion #6: resolveMessageShape in MessageDispatch.tsx
    references every role value declared in web/types/desk.ts. New
    role values that bypass MessageDispatch's exhaustive switch
    fail this assertion."""
    dispatch_src = _read(WEB_DISPATCH)
    # The six values per web/types/desk.ts:117
    expected_roles = ["user", "assistant", "system", "reviewer", "agent", "external"]
    for role in expected_roles:
        # Look for a role-string literal in the dispatcher
        needle = f"'{role}'"
        assert needle in dispatch_src, (
            f"MessageDispatch.tsx must reference role {role!r} in "
            f"resolveMessageShape per ADR-237 D1 exhaustive switch. "
            f"(Looking for {needle!r})"
        )


def test_chat_panel_retains_autonomy_chip():
    """Assertion #7: ChatPanel.tsx retains the ADR-238 autonomy chip
    render. ADR-237 R2 composition guard — confirms ADR-237 didn't
    accidentally move ADR-238's chip to the row level (it stays at
    composer level per ADR-238 + ADR-237 D6)."""
    src = _read(WEB_CHAT_PANEL)
    assert "showAutonomyChip" in src, (
        "ChatPanel.tsx must retain the ADR-238 autonomy chip render. "
        "ADR-237 R2 explicitly preserves composer-level placement."
    )
    assert "useAutonomy" in src, (
        "ChatPanel.tsx must continue to call useAutonomy for the chip."
    )


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------

def _run_all() -> int:
    tests = [
        test_message_dispatch_module_exists_with_required_surface,
        test_message_row_module_exists_with_required_surface,
        test_legacy_tpmessages_deleted,
        test_chat_panel_imports_dispatch_and_row,
        test_chat_panel_no_inline_role_dispatch,
        test_dispatch_handles_all_six_roles_exhaustively,
        test_chat_panel_retains_autonomy_chip,
    ]
    failed = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {fn.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} ADR-237 assertions passed.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(_run_all())
