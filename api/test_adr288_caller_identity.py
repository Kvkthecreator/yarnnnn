"""ADR-288 regression gate — caller_identity as first-class auth field.

Tests three structural invariants:

1. Every auth-construction site sets ``caller_identity`` per ADR-209 taxonomy.
2. Substrate primitives that default ``authored_by`` read it from
   ``auth.caller_identity`` (parallel pattern in ``handle_write_file`` and
   ``handle_schedule``).
3. The three pre-ADR-288 compensating sites are deleted:
   - ``services/primitives/workspace.py`` hardcoded ``"yarnnn:chat"`` default
   - ``agents/yarnnn.py`` per-call Schedule injection block
   - ``agents/reviewer_agent.py`` per-call Schedule injection block

Phase 2 + 3 assertions added in their respective phase commits.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Make api/ importable
API_DIR = Path(__file__).resolve().parent
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _file(*parts: str) -> Path:
    return API_DIR.joinpath(*parts)


# -----------------------------------------------------------------------------
# Phase 1 assertions — caller_identity is first-class
# -----------------------------------------------------------------------------

def test_authenticated_client_has_caller_identity_default():
    """ADR-288 D1: AuthenticatedClient ships caller_identity='operator' default.

    The only path that constructs AuthenticatedClient via FastAPI dependency
    is the operator JWT handler — the operator hit the API. MCP overrides at
    construction; specialist/reviewer/mechanical paths use separate auth
    namespaces.
    """
    from services.supabase import AuthenticatedClient

    auth = AuthenticatedClient(client=MagicMock(), user_id="uid")
    assert auth.caller_identity == "operator", (
        "AuthenticatedClient must default caller_identity='operator' per ADR-288 D1."
    )


def test_mcp_auth_sets_caller_identity_yarnnn_mcp():
    """ADR-288 D1: MCP boundary sets caller_identity='yarnnn:mcp'.

    Replaces the three explicit per-call authored_by='yarnnn:mcp' passes at
    services/mcp_composition.py:677/683/687.
    """
    src = _read_text(_file("mcp_server", "auth.py"))
    assert 'caller_identity="yarnnn:mcp"' in src, (
        "mcp_server/auth.py must construct AuthenticatedClient with "
        "caller_identity='yarnnn:mcp' per ADR-288 D1."
    )


def test_reviewer_auth_sets_caller_identity():
    """ADR-288 D1: Reviewer wake builds auth with caller_identity='reviewer:...'.

    Replaces the per-call Schedule injection block at reviewer_agent.py:1180
    (pre-ADR-288).
    """
    src = _read_text(_file("agents", "reviewer_agent.py"))
    # Auth construction at ~line 1026
    assert re.search(
        r'caller_identity=f"reviewer:\{REVIEWER_MODEL_IDENTITY\}"',
        src,
    ), (
        "reviewer_agent.py SimpleNamespace must set caller_identity="
        "f'reviewer:{REVIEWER_MODEL_IDENTITY}' per ADR-288 D1."
    )


def test_mechanical_auth_sets_caller_identity():
    """ADR-288 D1: _MechanicalAuth carries caller_identity=f'system:{slug}'."""
    src = _read_text(_file("services", "invocation_dispatcher.py"))
    assert 'caller_identity=f"system:{recurrence.slug}"' in src, (
        "_MechanicalAuth must set caller_identity=f'system:{recurrence.slug}' "
        "per ADR-288 D1."
    )


def test_headless_auth_sets_caller_identity():
    """ADR-288 D1: HeadlessAuth derives caller_identity from agent role."""
    from services.primitives.registry import HeadlessAuth

    # With agent role
    auth_with_role = HeadlessAuth(
        client=MagicMock(),
        user_id="uid",
        agent={"role": "researcher"},
    )
    assert auth_with_role.caller_identity == "specialist:researcher", (
        "HeadlessAuth with agent role must set caller_identity="
        "f'specialist:{role}' per ADR-288 D1."
    )

    # Without agent (tripwire fallback)
    auth_no_agent = HeadlessAuth(client=MagicMock(), user_id="uid")
    assert auth_no_agent.caller_identity == "specialist:unknown", (
        "HeadlessAuth without agent must fall back to 'specialist:unknown' "
        "(telemetry tripwire) per ADR-288 D1."
    )


def test_write_file_default_resolves_from_caller_identity():
    """ADR-288 D2: handle_write_file defaults authored_by from auth.caller_identity.

    Hardcoded 'yarnnn:chat' default is deleted; the resolver reads
    auth.caller_identity with 'system:unknown' tripwire fallback.
    """
    src = _read_text(_file("services", "primitives", "workspace.py"))
    # Negative: no hardcoded yarnnn:chat default
    assert 'authored_by or "yarnnn:chat"' not in src, (
        "Hardcoded 'yarnnn:chat' default in handle_write_file is the "
        "pre-ADR-288 leak — must be replaced by caller_identity resolution."
    )
    # Positive: caller_identity resolution present
    assert 'getattr(auth, "caller_identity"' in src, (
        "handle_write_file must read default authored_by from "
        "auth.caller_identity per ADR-288 D2."
    )
    # Tripwire: system:unknown fallback present
    assert '"system:unknown"' in src, (
        "handle_write_file must include 'system:unknown' fallback as "
        "telemetry tripwire per ADR-288 D2."
    )


def test_schedule_default_resolves_from_caller_identity():
    """ADR-288 D2 parallel: Schedule reads auth.caller_identity as fallback.

    Pre-ADR-288: Schedule fail-fast on missing authored_by; agent-layer
    injection compensated at two sites. Post-ADR-288: auth.caller_identity
    is the canonical source; fail-fast remains for direct callers
    (routes/scripts) that bypass auth construction.
    """
    src = _read_text(_file("services", "primitives", "schedule.py"))
    assert 'getattr(auth, "caller_identity"' in src, (
        "handle_schedule must read default authored_by from "
        "auth.caller_identity per ADR-288 D2."
    )


def test_yarnnn_schedule_injection_deleted():
    """ADR-288 D3: agents/yarnnn.py tool_executor no longer injects per-call.

    The pre-ADR-288 block ``if tool_name == "Schedule" and isinstance(...) and
    not tool_input.get("authored_by"): tool_input = {**tool_input,
    "authored_by": "operator"}`` is deleted. auth.caller_identity carries it.
    """
    src = _read_text(_file("agents", "yarnnn.py"))
    # The literal injection pattern must be absent
    assert not re.search(
        r'if tool_name == "Schedule".*not tool_input\.get\("authored_by"\)',
        src,
        re.DOTALL,
    ), (
        "agents/yarnnn.py Schedule injection block must be deleted per "
        "ADR-288 D3 — auth.caller_identity supersedes per-call compensation."
    )


def test_reviewer_schedule_injection_deleted():
    """ADR-288 D3: reviewer_agent.py dispatch loop no longer injects per-call.

    Same shape as the yarnnn.py deletion — the per-tool conditional
    ``if name == "Schedule" and ... not inp.get("authored_by"): inp = {...,
    "authored_by": f"reviewer:..."}`` is deleted.
    """
    src = _read_text(_file("agents", "reviewer_agent.py"))
    assert not re.search(
        r'if name == "Schedule".*not inp\.get\("authored_by"\)',
        src,
        re.DOTALL,
    ), (
        "reviewer_agent.py Schedule injection block must be deleted per "
        "ADR-288 D3 — auth.caller_identity supersedes per-call compensation."
    )


def test_no_live_yarnnn_chat_string_in_code():
    """ADR-288 D4: 'yarnnn:chat' string no longer in live code (live writes).

    Allow-listed exceptions:
    - test fixtures (this file)
    - ADR-288 documentation (the ADR + CHANGELOG entries describing the rename)
    - historical-row notes in ADR-209/ADR-235/ADR-251 explanations
    - FE label-mapping code that handles the 'yarnnn:' prefix generically
    """
    import subprocess
    result = subprocess.run(
        ["grep", "-rn", "yarnnn:chat", "--include=*.py", str(API_DIR)],
        capture_output=True,
        text=True,
    )
    matches = [
        line for line in result.stdout.splitlines()
        if line and "test_adr288" not in line and "__pycache__" not in line
    ]
    # Filter docstring-explaining matches (the workspace.py docstring should
    # not say "defaults to yarnnn:chat" — that was already updated).
    forbidden = [
        line for line in matches
        if "'yarnnn:chat'" in line or '"yarnnn:chat"' in line
    ]
    assert not forbidden, (
        f"'yarnnn:chat' string found in live api/ code "
        f"(should only appear in test fixtures or historical commentary):\n"
        + "\n".join(forbidden)
    )


# -----------------------------------------------------------------------------
# Phase 2 assertions — envelope key + stale path residue
# -----------------------------------------------------------------------------

def test_envelope_key_renamed_to_ground_truth_md():
    """ADR-288 D5: kernel envelope key `performance_md` → `ground_truth_md`.

    Slot name is the kernel concept (FOUNDATIONS Axiom 8); bundles declare
    what fills it. `performance_md` was ADR-267 residue — pre-rename file path
    `_performance.md` baked into the slot name.
    """
    # Kernel-side: ReviewerContext field + readers
    src = _read_text(_file("agents", "reviewer_agent.py"))
    assert "ground_truth_md: str" in src, (
        "ReviewerContext field must be `ground_truth_md` per ADR-288 D5."
    )
    assert "performance_md" not in src, (
        "`performance_md` identifier must not appear in reviewer_agent.py."
    )

    # Envelope helper docstring
    src = _read_text(_file("services", "reviewer_envelope.py"))
    assert "ground_truth_md" in src, (
        "reviewer_envelope.py docstring must reference `ground_truth_md`."
    )
    assert "performance_md" not in src, (
        "`performance_md` identifier must not appear in reviewer_envelope.py."
    )

    # Proposal-arrival reader
    src = _read_text(_file("services", "review_proposal_dispatch.py"))
    assert "ground_truth_md" in src, (
        "review_proposal_dispatch.py must use `ground_truth_md` envelope key."
    )
    assert "performance_md" not in src, (
        "`performance_md` identifier must not appear in review_proposal_dispatch.py."
    )


def test_bundle_manifests_renamed_to_ground_truth_md():
    """ADR-288 D5: every bundle MANIFEST that declared `performance_md`
    envelope key now declares `ground_truth_md`. Defensive comments
    rationalizing the old name DELETED."""
    import subprocess
    result = subprocess.run(
        ["grep", "-rn", "performance_md", str(API_DIR.parent / "docs" / "programs")],
        capture_output=True,
        text=True,
    )
    matches = [
        line for line in result.stdout.splitlines()
        if line and "test_adr288" not in line
    ]
    assert not matches, (
        f"`performance_md` envelope key must not appear in any bundle "
        f"under docs/programs/ per ADR-288 D5:\n" + "\n".join(matches)
    )

    # Positive: alpha-trader bundle must declare ground_truth_md
    bundle_manifest = _read_text(
        API_DIR.parent / "docs" / "programs" / "alpha-trader" / "MANIFEST.yaml"
    )
    assert "key: ground_truth_md" in bundle_manifest, (
        "alpha-trader bundle MANIFEST must declare `key: ground_truth_md` "
        "as the envelope key per ADR-288 D5."
    )


def test_dead_helper_domain_performance_path_deleted():
    """ADR-288 D6: `domain_performance_path()` helper in conventions.py
    is dead code (zero callers verified pre-deletion). Deletion completes
    singular-implementation discipline."""
    src = _read_text(_file("services", "conventions.py"))
    assert "def domain_performance_path" not in src, (
        "Dead helper `domain_performance_path` must be deleted per ADR-288 D6."
    )
    # Also removed from __all__ export list
    assert '"domain_performance_path"' not in src, (
        "Dead helper export `domain_performance_path` must be removed from "
        "__all__ in conventions.py."
    )


# -----------------------------------------------------------------------------
# Phase 3 assertions — kernel money-truth de-instancing
# -----------------------------------------------------------------------------

def test_default_review_identity_md_speaks_in_ground_truth_substrate():
    """ADR-288 D8 / Phase 3: DEFAULT_REVIEW_IDENTITY_MD must not hardcode
    alpha-trader instance vocabulary as kernel-default.

    Negative: no `_performance.md` or alpha-trader-specific reasoning shape
    in kernel-default prose.
    Positive: speaks in `ground-truth substrate` (kernel concept) and
    points at `_workspace_guide.md` for the instance.
    """
    src = _read_text(_file("services", "orchestration.py"))
    # Extract the IDENTITY constant body
    import re as _re
    m = _re.search(
        r'DEFAULT_REVIEW_IDENTITY_MD\s*=\s*"""(.*?)"""', src, _re.DOTALL,
    )
    assert m, "DEFAULT_REVIEW_IDENTITY_MD constant not found in orchestration.py"
    body = m.group(1)

    # Negative assertions
    assert "_performance.md" not in body, (
        "DEFAULT_REVIEW_IDENTITY_MD must not reference `_performance.md` — "
        "this is alpha-trader pre-rename residue shipped to every Reviewer."
    )

    # Positive assertions
    assert "ground-truth substrate" in body, (
        "DEFAULT_REVIEW_IDENTITY_MD must reference the kernel concept "
        "`ground-truth substrate` (FOUNDATIONS Axiom 8)."
    )
    assert "_workspace_guide.md" in body, (
        "DEFAULT_REVIEW_IDENTITY_MD must point at `_workspace_guide.md` "
        "as the carrier of bundle-specific substrate paths per ADR-280."
    )


def test_default_review_principles_md_speaks_in_ground_truth_substrate():
    """Phase 3: DEFAULT_REVIEW_PRINCIPLES_MD same de-instancing as IDENTITY."""
    src = _read_text(_file("services", "orchestration.py"))
    import re as _re
    m = _re.search(
        r'DEFAULT_REVIEW_PRINCIPLES_MD\s*=\s*"""(.*?)"""', src, _re.DOTALL,
    )
    assert m, "DEFAULT_REVIEW_PRINCIPLES_MD constant not found in orchestration.py"
    body = m.group(1)

    assert "_performance.md" not in body, (
        "DEFAULT_REVIEW_PRINCIPLES_MD must not reference `_performance.md`."
    )
    assert "ground-truth substrate" in body, (
        "DEFAULT_REVIEW_PRINCIPLES_MD must reference `ground-truth substrate`."
    )


def test_cockpit_awareness_de_instanced():
    """Phase 3: agents/cockpit_awareness.py must not hardcode `_money_truth.md`
    as kernel-universal Reviewer substrate. The bundle's `_workspace_guide.md`
    is the authoritative carrier of program-specific substrate paths.
    """
    src = _read_text(_file("agents", "cockpit_awareness.py"))

    # The domain-substrate path list must point at `_workspace_guide.md`
    # rather than hardcoding `_money_truth.md` as a kernel-universal slot.
    # Allow instance-pointer mentions of `_money_truth.md` (e.g. "alpha-
    # trader's instance is `_money_truth.md`") as long as the kernel-concept
    # phrasing is also present.
    assert "_workspace_guide.md" in src, (
        "cockpit_awareness.py must point at `_workspace_guide.md` as the "
        "authoritative carrier of bundle-specific substrate paths per "
        "ADR-280 + ADR-288 Phase 3."
    )
    assert "ground-truth" in src.lower() or "ground truth" in src.lower(), (
        "cockpit_awareness.py must reference ground-truth substrate "
        "(kernel concept per FOUNDATIONS Axiom 8)."
    )

    # The empty-state guidance "Missing _money_truth.md" framing should be
    # generalized — alpha-author Reviewer has no `_money_truth.md` to miss.
    # The framing should say "missing ground-truth substrate" with the
    # bundle's instance as example.
    assert "Missing _money_truth.md" not in src, (
        "Empty-state guidance must be de-instanced — alpha-author Reviewer "
        "has no `_money_truth.md` to miss. Phrase as `missing ground-truth "
        "substrate (per workspace guide — alpha-trader: _money_truth.md)`."
    )


def test_tools_core_de_instanced():
    """Phase 3: `tools_core.py` must not prescribe alpha-trader instance
    vocabulary as kernel reasoning shape for the Reviewer description.

    Mentions of `_money_truth.md` as alpha-trader's instance example are
    allowed (kernel concept + instance pointer is correct per ADR-282
    instance-of phrasings); claims that the Reviewer reasons "against
    _money_truth.md money-truth" as if it were the universal substrate
    are NOT (that hardcodes alpha-trader vocabulary as kernel reasoning).
    """
    src = _read_text(_file("agents", "prompts", "tools_core.py"))

    # Negative: no kernel-as-universal claims tying Reviewer to _money_truth.md
    # alone. Allow instance-pointer phrasings ("alpha-trader's instance:
    # `_money_truth.md`").
    assert "against `_money_truth.md` money-truth" not in src, (
        "tools_core.py must not claim Reviewer reasons against "
        "`_money_truth.md` as if it were the universal substrate. Use "
        "kernel concept + instance-pointer phrasing per ADR-282."
    )
    assert "Capital-EV reasoning against `_money_truth.md`" not in src, (
        "tools_core.py must not prescribe Capital-EV as kernel reasoning "
        "shape. Capital-EV is alpha-trader's instance reasoning."
    )

    # Positive: ground-truth substrate framing present
    assert "ground-truth substrate" in src, (
        "tools_core.py must reference `ground-truth substrate` (kernel "
        "concept per FOUNDATIONS Axiom 8)."
    )


def test_reviewer_agent_docstring_de_instanced():
    """Phase 3: reviewer_agent.py module docstring + persona-frame Independence
    block must use ADR-282 vocabulary (ground-truth substrate as kernel
    concept; money-truth as alpha-trader instance pointer).
    """
    src = _read_text(_file("agents", "reviewer_agent.py"))

    # Module-level Axiom 8 reference (L33 region) must use kernel concept
    assert "Axiom 8 (Ground-Truth Substrate)" in src, (
        "reviewer_agent.py Axiom 8 reference must use the kernel concept "
        "name `Ground-Truth Substrate` per ADR-282."
    )
    # Old name should be gone from this site
    assert "Axiom 8 (Money-Truth)" not in src, (
        "reviewer_agent.py must not refer to Axiom 8 by its retired name "
        "`Money-Truth` (kernel-level)."
    )


def test_stale_performance_md_in_docstrings_updated():
    """ADR-288 D7: docstring examples that cite a concrete file path use
    the instance file name (`_money_truth.md`), not the pre-ADR-267 stale
    path `_performance.md`.

    Phase 2 scope: non-prompt docstrings (narrative.py, execution_router.py,
    primitives/dispatch_specialist.py, primitives/revisions.py,
    outcomes/reconciler.py). Phase 3 scope: kernel prompt content in
    orchestration.py + cockpit_awareness.py + tools_core.py.
    """
    targets = [
        ("services", "narrative.py"),
        ("services", "execution_router.py"),
        ("services", "primitives", "dispatch_specialist.py"),
        ("services", "primitives", "revisions.py"),
        ("services", "outcomes", "reconciler.py"),
    ]
    for parts in targets:
        src = _read_text(_file(*parts))
        assert "_performance.md" not in src, (
            f"Stale `_performance.md` reference in {'/'.join(parts)} "
            f"must be updated to `_money_truth.md` per ADR-288 D7."
        )

    # Conventions.py module docstring + helper docstring updated
    src = _read_text(_file("services", "conventions.py"))
    assert "_performance.md" not in src, (
        "conventions.py module docstring + helper docstrings must not "
        "reference `_performance.md` per ADR-288 D7."
    )


# -----------------------------------------------------------------------------
# Test runner
# -----------------------------------------------------------------------------
#
# Phase 1 regression gate is STATIC-ONLY by design. End-to-end behavioral
# tests of `handle_write_file` and `handle_schedule` require mocking
# `services.workspace.UserMemory`, which triggers the full services-package
# import chain (Supabase client, Anthropic SDK, embeddings, etc.) — slow at
# best, prone to import-cycle hangs in CI/local. The static assertions below
# already prove the structural invariants:
#
# - D1: every auth-construction site carries `caller_identity` (5 sites)
# - D2: both substrate primitives read `getattr(auth, "caller_identity", ...)`
#   as the default resolver (one branch — no behavioral matrix to test)
# - D3: the compensating injection patches at the agent layer are deleted
# - D4: the `yarnnn:chat` hardcoded string is gone from live code
#
# The attribution-flow invariant is provable by inspection: the resolver in
# `handle_write_file` is `authored_by or getattr(auth, "caller_identity",
# None) or "system:unknown"`. Given the static assertions above, this
# resolves to the correct attribution for every caller path by construction.

def main() -> int:
    tests = [
        ("D1: AuthenticatedClient default", test_authenticated_client_has_caller_identity_default),
        ("D1: MCP auth", test_mcp_auth_sets_caller_identity_yarnnn_mcp),
        ("D1: Reviewer auth", test_reviewer_auth_sets_caller_identity),
        ("D1: Mechanical auth", test_mechanical_auth_sets_caller_identity),
        ("D1: Headless auth", test_headless_auth_sets_caller_identity),
        ("D2: WriteFile resolver", test_write_file_default_resolves_from_caller_identity),
        ("D2: Schedule resolver", test_schedule_default_resolves_from_caller_identity),
        ("D3: yarnnn.py injection deleted", test_yarnnn_schedule_injection_deleted),
        ("D3: reviewer_agent.py injection deleted", test_reviewer_schedule_injection_deleted),
        ("D4: no live yarnnn:chat", test_no_live_yarnnn_chat_string_in_code),
        # Phase 2 assertions
        ("D5: envelope key renamed", test_envelope_key_renamed_to_ground_truth_md),
        ("D5: bundle MANIFESTs renamed", test_bundle_manifests_renamed_to_ground_truth_md),
        ("D6: dead helper deleted", test_dead_helper_domain_performance_path_deleted),
        ("D7: stale _performance.md docstrings", test_stale_performance_md_in_docstrings_updated),
        # Phase 3 assertions
        ("D8: DEFAULT_REVIEW_IDENTITY_MD de-instanced", test_default_review_identity_md_speaks_in_ground_truth_substrate),
        ("D8: DEFAULT_REVIEW_PRINCIPLES_MD de-instanced", test_default_review_principles_md_speaks_in_ground_truth_substrate),
        ("D8: cockpit_awareness.py de-instanced", test_cockpit_awareness_de_instanced),
        ("D8: tools_core.py de-instanced", test_tools_core_de_instanced),
        ("D8: reviewer_agent.py docstring de-instanced", test_reviewer_agent_docstring_de_instanced),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  ✓ {name}")
            passed += 1
        except AssertionError as e:
            print(f"  ✗ {name}")
            print(f"      {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ {name} — unexpected error")
            print(f"      {type(e).__name__}: {e}")
            failed += 1

    print()
    print(f"ADR-288 regression gate: {passed}/{passed+failed} assertions passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
