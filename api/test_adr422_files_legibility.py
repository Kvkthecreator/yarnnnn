"""
ADR-422 — Files-surface non-editable-state affordances.

The Python-side gate (the FE affordances are TS, covered by `tsc --noEmit` +
the FE conventions). The one backend touch is ADR-422 D2: `inbound/` joins the
`operator_can_organize` carve set — the raw intake lane is immutable (ADR-376
DP32: retained, never rewritten), so a record of what came in is not
operator-organizable. uploads/ (the HUMAN raw lane) stays organizable.

This asserts the carve directly + guards the FE-mirror agreement invariant.
"""

import pytest


# ── D2: inbound/ is not operator-organizable (immutable raw intake) ──────────

@pytest.mark.parametrize("path,ok", [
    # inbound/ = immutable machine/external raw lane → NOT organizable (D2).
    ("/workspace/inbound/mcp/claude/inbox.md", False),
    ("/workspace/inbound/mcp/chatgpt/inbox.md", False),
    ("/workspace/inbound/web/example-feed/2026-07-08.xml", False),
    ("/workspace/inbound/slack/general/2026-07-08.md", False),
    # a bare inbound/ file (no sublane) still carves.
    ("/workspace/inbound/note.md", False),
    # uploads/ = the HUMAN raw lane → STILL organizable (the operator owns what
    # they uploaded; the D2 carve is inbound/ only, not the raw-lane concept).
    ("/workspace/uploads/report.pdf", True),
    ("/workspace/uploads/deep/nested/x.md", True),
    # sanity: the pre-existing carves are unaffected.
    ("/workspace/system/_recent_execution.md", False),
    ("/workspace/governance/_budget.yaml", False),
    ("/workspace/operation/report.md", True),
    ("/workspace/persona/IDENTITY.md", True),
])
def test_inbound_carve(path, ok):
    from services.workspace_paths import operator_can_organize
    assert operator_can_organize(path) is ok, f"{path} organizable should be {ok}"


def test_inbound_prefix_is_the_carve_not_a_leaf_rule():
    """The carve is the inbound/ PREFIX, not any filename pattern — a plain
    prose .md under inbound/ is still locked (it's a record), while the same
    filename elsewhere is organizable."""
    from services.workspace_paths import operator_can_organize
    assert operator_can_organize("/workspace/inbound/mcp/claude/notes.md") is False
    assert operator_can_organize("/workspace/operation/notes.md") is True


def test_inbound_normalization_matches_backend():
    """Path normalization (leading slash + optional workspace/ prefix) must
    agree with the other carves — a workspace-relative form carves the same."""
    from services.workspace_paths import operator_can_organize
    assert operator_can_organize("inbound/mcp/claude/inbox.md") is False
    assert operator_can_organize("workspace/inbound/mcp/claude/inbox.md") is False
    assert operator_can_organize("/workspace/inbound/mcp/claude/inbox.md") is False


# ── FE-mirror agreement: the carve constant is documented as shared ──────────

def test_fe_mirror_carve_documented():
    """The FE mirror (web/lib/workspace/ownership.ts) must carve inbound/ too —
    a guard so a future edit to the backend carve remembers the FE lockstep.
    We can't run TS here; we assert the FE file names the inbound/ carve (the
    SAME lockstep the system/ + machine-config carves already have)."""
    import os
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fe = os.path.join(here, "web", "lib", "workspace", "ownership.ts")
    with open(fe, encoding="utf-8") as f:
        src = f.read()
    assert "inbound/" in src, "FE ownership.ts must carve inbound/ (ADR-422 D2 lockstep)"
    assert "ADR-422" in src, "FE ownership.ts must cite ADR-422 for the inbound/ carve"


def test_fe_legibility_helper_exists():
    """The three-state legibility helper (D1) is the FE foundation — assert it
    exists and exports the classifier so the surface can't silently regress to
    the coarse `_`-prefix `sys` treatment."""
    import os
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    lib = os.path.join(here, "web", "lib", "workspace", "legibility.ts")
    assert os.path.exists(lib), "web/lib/workspace/legibility.ts (ADR-422 D1) must exist"
    with open(lib, encoding="utf-8") as f:
        src = f.read()
    for token in ("fileLegibilityState", "machine-config", "raw-intake", "agent-authored"):
        assert token in src, f"legibility.ts must define {token}"


def test_sys_word_removed_from_tree():
    """ADR-422 D1 / ADR-410 D4: the developer `sys` word is gone from the tree —
    the not-editable state is a glyph + Get-Info copy, not a dev tag."""
    import os
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tree = os.path.join(here, "web", "components", "workspace", "WorkspaceTree.tsx")
    with open(tree, encoding="utf-8") as f:
        src = f.read()
    # The literal `sys` badge span text is gone (the glyph replaces it).
    assert ">\n            sys\n" not in src and ">sys<" not in src, \
        "the `sys` badge text must be removed (ADR-422 D1)"
    assert "fileLegibilityState" in src, "the tree must classify via fileLegibilityState"


if __name__ == "__main__":
    import sys
    # Run the __main__ path so a check()-counter gate reports real N-failed
    # (pytest can mask a False-returning check as PASSED — memory lesson).
    failed = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            # parametrized fns need pytest; skip the parametrized one here.
            if name == "test_inbound_carve":
                continue
            try:
                fn()
                print(f"  ✓ {name}")
            except Exception as e:  # noqa: BLE001
                failed += 1
                print(f"  ✗ {name}: {e}")
    print(f"\n{failed} failed (excl. parametrized — run via pytest for full)")
    sys.exit(1 if failed else 0)
