"""Regression gate for ADR-274 / FOUNDATIONS v8.5 Axiom 4 amendment.

Trigger authoring is an Identity-layer responsibility. The Schedule
primitive must fail fast on missing `authored_by`. Reviewer wakes must
carry an Operating Context block. All three runtime Schedule callers
(Reviewer dispatch, YARNNN tool_executor, execution_router pause/resume)
must inject `authored_by` correctly.

Run:
    python -m api.test_adr274_trigger_authoring
"""

from __future__ import annotations

import asyncio
import importlib
import inspect
import sys
from pathlib import Path


# Path bootstrap (mirrors other ADR gates)
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


_PASS: list[str] = []
_FAIL: list[tuple[str, str]] = []


def _ok(name: str) -> None:
    _PASS.append(name)
    print(f"  ✓ {name}")


def _bad(name: str, reason: str) -> None:
    _FAIL.append((name, reason))
    print(f"  ✗ {name}\n      {reason}")


# ---------------------------------------------------------------------------
# 1. Schedule primitive fail-fast on missing authored_by
# ---------------------------------------------------------------------------

def test_schedule_fails_fast_on_missing_authored_by() -> None:
    from services.primitives.schedule import handle_schedule

    class _Auth:
        user_id = "00000000-0000-0000-0000-000000000000"
        client = None

    # Missing entirely
    result = asyncio.run(handle_schedule(_Auth(), {"action": "create", "slug": "x"}))
    if result.get("success") is False and result.get("error") == "missing_authored_by":
        _ok("Schedule rejects missing authored_by with error='missing_authored_by'")
    else:
        _bad(
            "Schedule rejects missing authored_by",
            f"Expected success=False + error=missing_authored_by, got {result!r}",
        )

    # Empty string
    result = asyncio.run(
        handle_schedule(_Auth(), {"action": "create", "slug": "x", "authored_by": ""})
    )
    if result.get("success") is False and result.get("error") == "missing_authored_by":
        _ok("Schedule rejects empty-string authored_by")
    else:
        _bad(
            "Schedule rejects empty-string authored_by",
            f"Expected success=False + error=missing_authored_by, got {result!r}",
        )

    # Whitespace-only
    result = asyncio.run(
        handle_schedule(_Auth(), {"action": "create", "slug": "x", "authored_by": "   "})
    )
    if result.get("success") is False and result.get("error") == "missing_authored_by":
        _ok("Schedule rejects whitespace-only authored_by")
    else:
        _bad(
            "Schedule rejects whitespace-only authored_by",
            f"Expected success=False + error=missing_authored_by, got {result!r}",
        )

    # Non-string
    result = asyncio.run(
        handle_schedule(_Auth(), {"action": "create", "slug": "x", "authored_by": 42})
    )
    if result.get("success") is False and result.get("error") == "missing_authored_by":
        _ok("Schedule rejects non-string authored_by")
    else:
        _bad(
            "Schedule rejects non-string authored_by",
            f"Expected success=False + error=missing_authored_by, got {result!r}",
        )


# ---------------------------------------------------------------------------
# 2. Operating Context block helper exists + returns Axiom-4-shaped content
# ---------------------------------------------------------------------------

def test_operating_context_block_helper() -> None:
    from agents.freddie_agent import build_operating_context_block

    sig = inspect.signature(build_operating_context_block)
    if list(sig.parameters.keys()) == ["client", "user_id"]:
        _ok("build_operating_context_block(client, user_id) signature")
    else:
        _bad(
            "build_operating_context_block signature",
            f"Expected (client, user_id), got {list(sig.parameters.keys())}",
        )

    # Helper must be defensive — None client + None user_id still produces a
    # block (it gracefully degrades; market/tenure fields are best-effort).
    block = build_operating_context_block(client=None, user_id="00000000-0000-0000-0000-000000000000")
    if "Operating Context" in block and "Axiom 4 v8.5" in block:
        _ok("Operating Context block contains Axiom-4-versioned header")
    else:
        _bad(
            "Operating Context block header",
            f"Expected 'Operating Context' + 'Axiom 4 v8.5' in:\n{block!r}",
        )

    if "**Now**:" in block and "**Operator timezone**:" in block:
        _ok("Operating Context block contains Now + timezone fields")
    else:
        _bad("Operating Context fields", f"Missing required fields in:\n{block!r}")


# ---------------------------------------------------------------------------
# 3. Reviewer persona frame includes cadence-authoring discipline section
# ---------------------------------------------------------------------------

def test_reviewer_persona_includes_cadence_authoring() -> None:
    """Post-ADR-306 collapse: cadence-authoring discipline is substrate
    pedagogy (ablation §3 row 7 — cadence-trifecta) and relocates from the
    persona frame to `_workspace_guide.md` (ADR-281's home, Phase C). The
    Reviewer reads the guide every wake; the discipline is preserved, only
    its home moved from system prose to bundle substrate.

    Trigger-authoring authority (Axiom 4 amendment + ADR-274) is the
    canonical provenance and is cited in the guide's cadence section.
    """
    import re
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent.parent
    needles = [
        "cadence is yours to author",
        "FOUNDATIONS v8.5 Axiom 4",
        "Derived Principle 18",
        "ADR-274",
        "Schedule(action=",
        "scaffolds",
        "bundle-fork",
        "ListRevisions",
        "Operating Context",
    ]
    for bundle in ("alpha-trader", "alpha-author"):
        raw = (
            repo_root
            / "docs" / "programs" / bundle / "reference-workspace"
            / "_workspace_guide.md"
        ).read_text(encoding="utf-8")
        # Prose is line-wrapped; collapse whitespace so multi-word needles
        # match across line breaks (content-presence test, not layout test).
        guide = re.sub(r"\s+", " ", raw)
        missing = [n for n in needles if n not in guide]
        assert not missing, (
            f"{bundle} _workspace_guide.md cadence section missing markers "
            f"(relocated from persona frame per ADR-306 D3): {missing!r}"
        )


# ---------------------------------------------------------------------------
# 4. FreddieContext TypedDict carries operating_context_block
# ---------------------------------------------------------------------------

def test_reviewer_context_has_operating_context_field() -> None:
    from agents.freddie_agent import FreddieContext

    annotations = getattr(FreddieContext, "__annotations__", {})
    if "operating_context_block" in annotations:
        _ok("FreddieContext.operating_context_block field declared")
    else:
        _bad(
            "FreddieContext field",
            f"operating_context_block missing from annotations: "
            f"{list(annotations.keys())}",
        )


# ---------------------------------------------------------------------------
# 5. _build_user_message injects the operating context block
# ---------------------------------------------------------------------------

def test_build_user_message_injects_operating_context() -> None:
    import agents.freddie_agent as mod
    src = inspect.getsource(mod._build_user_message)
    if 'ctx.get("operating_context_block")' in src:
        _ok("_build_user_message reads ctx['operating_context_block']")
    else:
        _bad(
            "_build_user_message wiring",
            "Expected ctx.get('operating_context_block') in body",
        )


# ---------------------------------------------------------------------------
# 6. Reviewer wake builds auth with caller_identity="freddie:..."
# ---------------------------------------------------------------------------
# ADR-274 D5 invariant preserved by ADR-288 D1: Schedule writes from the
# Reviewer wake are attributed to the Reviewer Identity. Pre-ADR-288 the
# dispatch loop injected per-call; post-ADR-288 the auth namespace carries
# caller_identity at construction time and the Schedule primitive defaults
# authored_by from auth.caller_identity (ADR-288 D2). One declaration site.

def test_reviewer_auth_carries_reviewer_caller_identity() -> None:
    import agents.freddie_agent as mod
    src = inspect.getsource(mod)
    inj = 'caller_identity=f"freddie:{FREDDIE_MODEL_IDENTITY}"'
    if inj in src:
        _ok("Reviewer auth carries caller_identity='reviewer:...' (ADR-288 D1)")
    else:
        _bad(
            "Reviewer auth caller_identity",
            f'Expected `{inj}` in SimpleNamespace construction',
        )


# ---------------------------------------------------------------------------
# 7. YARNNN auth defaults caller_identity="operator"
# ---------------------------------------------------------------------------
# ADR-274 D5 invariant preserved by ADR-288 D1: Schedule writes from
# YARNNN-mediated chat are attributed to the operator. Pre-ADR-288 the
# tool_executor injected per-call; post-ADR-288 the AuthenticatedClient
# dataclass defaults caller_identity="operator" (the only path that
# constructs AuthenticatedClient via FastAPI dep is the operator JWT
# handler — the operator hit the API).

def test_authenticated_client_defaults_operator_caller_identity() -> None:
    src = (ROOT / "services" / "supabase.py").read_text()
    if 'caller_identity: str = "operator"' in src:
        _ok("AuthenticatedClient defaults caller_identity='operator' (ADR-288 D1)")
    else:
        _bad(
            "AuthenticatedClient caller_identity default",
            'Expected `caller_identity: str = "operator"` in AuthenticatedClient dataclass',
        )


# ---------------------------------------------------------------------------
# 8. execution_router pause/resume pass authored_by="operator"
# ---------------------------------------------------------------------------

def test_execution_router_pause_resume_authored_by() -> None:
    src = (ROOT / "services" / "execution_router.py").read_text()
    pause_ok = '"action": "pause"' in src and '"authored_by": "operator"' in src
    resume_ok = '"action": "resume"' in src
    if pause_ok and resume_ok:
        # Check both pause + resume each carry authored_by
        n = src.count('"authored_by": "operator"')
        if n >= 2:
            _ok(f"execution_router pause+resume both pass authored_by='operator' (count={n})")
        else:
            _bad(
                "execution_router authored_by",
                f"Expected ≥2 'authored_by': 'operator' occurrences, found {n}",
            )
    else:
        _bad("execution_router authored_by", "Missing pause/resume + authored_by markers")


# ---------------------------------------------------------------------------
# 9. freddie_envelope composes operating_context_block (ADR-301 D5 update)
# ---------------------------------------------------------------------------
# Pre-ADR-301: composition lived at three wake.py call sites + the helper
# in agents/freddie_agent.py.  ADR-301 D5 consolidated composition into
# services/freddie_envelope.py — Singular Implementation, one envelope
# assembly point.  The wake-source modules consume it via the
# **governance_envelope dict-spread; ADR-276 already pre-loads the rest
# of the envelope through the same helper.  These two tests now assert
# the post-ADR-301 contract: composition in the envelope helper +
# spread-consumption at every reactive + addressed call site.
#
# `services/invocation_dispatcher.py` was deleted in the ADR-261 cleanup;
# reactive dispatch lives in services/wake.py::dispatch_recurrence.  The
# test target updates accordingly — Singular Implementation discipline
# applied to the test gate same as the code.

def test_invocation_dispatcher_wires_operating_context() -> None:
    """Post-ADR-301 D5: reactive wake path consumes the envelope helper's
    operating_context_block via dict-spread, not call-site composition.
    Test target updated from the deleted invocation_dispatcher.py to the
    canonical reactive entry point in services/wake.py::dispatch_recurrence.
    """
    env_src = (ROOT / "services" / "freddie_envelope.py").read_text()
    if (
        "def build_operating_context_block" in env_src
        and 'envelope["operating_context_block"] = build_operating_context_block' in env_src
    ):
        _ok("freddie_envelope.py composes operating_context_block (ADR-301 D5)")
    else:
        _bad(
            "freddie_envelope.py composes operating_context_block",
            "Expected build_operating_context_block defined + assigned into envelope dict",
        )
    wake_src = (ROOT / "services" / "wake.py").read_text()
    # Reactive wake site (dispatch_recurrence) must consume the envelope.
    if (
        "load_freddie_governance_envelope" in wake_src
        and "**governance_envelope" in wake_src
    ):
        _ok("services/wake.py reactive path consumes envelope via **governance_envelope spread")
    else:
        _bad(
            "services/wake.py reactive envelope consumption",
            "Expected load_freddie_governance_envelope + **governance_envelope spread",
        )
    # Anti-regression: stale call-site composition pattern must be gone.
    if '"operating_context_block": operating_context' in wake_src:
        _bad(
            "stale operating_context_block call-site composition in wake.py",
            "ADR-301 D5 deleted call-site composition; re-introducing it would be a regression",
        )
    else:
        _ok("services/wake.py no longer composes operating_context_block at call sites (ADR-301 D5)")


# ---------------------------------------------------------------------------
# 10. routes/feed.py addressed-path wires operating_context_block via envelope spread (ADR-301 D5)
# ---------------------------------------------------------------------------

def test_feed_route_wires_operating_context() -> None:
    """Post-ADR-301 D5: addressed path consumes the envelope helper via
    services/wake.py::stream_addressed_wake.  The route layer
    (routes/feed.py) consumes the wake source's typed event stream and
    no longer composes operating_context_block directly.  Verify the
    addressed wake source itself consumes the envelope.
    """
    src = (ROOT / "services" / "wake.py").read_text()
    # The stream_addressed_wake function must consume the envelope.
    if "stream_addressed_wake" in src and "load_freddie_governance_envelope" in src:
        _ok("wake.py::stream_addressed_wake consumes load_freddie_governance_envelope")
    else:
        _bad(
            "wake.py addressed envelope consumption",
            "Expected stream_addressed_wake + load_freddie_governance_envelope in wake.py",
        )
    # Anti-regression: routes/feed.py no longer composes operating_context_block.
    feed_src = (ROOT / "routes" / "feed.py").read_text()
    if "build_operating_context_block" in feed_src:
        _bad(
            "stale build_operating_context_block import in routes/feed.py",
            "ADR-301 D5 moved composition into freddie_envelope.py; routes/feed.py should not import it",
        )
    else:
        _ok("routes/feed.py no longer composes operating_context_block (ADR-301 D5)")


# ---------------------------------------------------------------------------
# 11. All known Schedule callers either inject or pass authored_by
# ---------------------------------------------------------------------------

def test_all_schedule_callers_provide_authored_by() -> None:
    """Sweep grep: every call site of handle_schedule must either pass
    authored_by literally or be reached via an injecting layer. This is
    a static check against well-known files."""
    import re

    callers = {
        "services/execution_router.py": True,  # pause/resume literal
        "routes/recurrences.py": True,         # patch routes literal
        "scripts/oneshot/cleanup_orphan_recurrences.py": True,
        "agents/yarnnn.py": True,              # tool_executor injection
        "agents/freddie_agent.py": True,      # dispatch injection
    }
    fails: list[str] = []
    for rel in callers:
        p = ROOT / rel
        if not p.exists():
            fails.append(f"{rel} missing on disk")
            continue
        text = p.read_text()
        if "authored_by" not in text:
            fails.append(f"{rel} no authored_by reference")
    if not fails:
        _ok("All known Schedule callers reference authored_by")
    else:
        _bad("Schedule caller sweep", "; ".join(fails))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    print("ADR-274 / FOUNDATIONS v8.5 — Trigger authoring is Identity-layer responsibility\n")

    test_schedule_fails_fast_on_missing_authored_by()
    test_operating_context_block_helper()
    test_reviewer_persona_includes_cadence_authoring()
    test_reviewer_context_has_operating_context_field()
    test_build_user_message_injects_operating_context()
    test_reviewer_auth_carries_reviewer_caller_identity()
    test_authenticated_client_defaults_operator_caller_identity()
    test_execution_router_pause_resume_authored_by()
    test_invocation_dispatcher_wires_operating_context()
    test_feed_route_wires_operating_context()
    test_all_schedule_callers_provide_authored_by()

    total = len(_PASS) + len(_FAIL)
    print(f"\n{len(_PASS)}/{total} pass")
    if _FAIL:
        print("\nFAILURES:")
        for name, reason in _FAIL:
            print(f"  • {name}: {reason}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
