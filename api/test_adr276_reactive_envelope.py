"""Regression gate for ADR-276 — Reactive-trigger envelope governance pre-load.

The Reviewer's reactive wakes (recurrence fires + proposal arrivals) must
receive the same governance + domain substrate pre-load that addressed
wakes receive. Both trigger paths share `services/reviewer_envelope.py::
load_reviewer_governance_envelope` per Singular Implementation discipline.

Run:
    python -m api.test_adr276_reactive_envelope
"""

from __future__ import annotations

import asyncio
import inspect
import sys
from pathlib import Path


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
# 1. Helper module exists + exports the canonical function
# ---------------------------------------------------------------------------

def test_helper_module_exists() -> None:
    try:
        from services.reviewer_envelope import load_reviewer_governance_envelope
    except ImportError as e:
        _bad("services.reviewer_envelope importable", str(e))
        return

    sig = inspect.signature(load_reviewer_governance_envelope)
    params = list(sig.parameters.keys())
    if params == ["client", "user_id"]:
        _ok("load_reviewer_governance_envelope(client, user_id) signature")
    else:
        _bad(
            "load_reviewer_governance_envelope signature",
            f"expected (client, user_id), got {params}",
        )

    if asyncio.iscoroutinefunction(load_reviewer_governance_envelope):
        _ok("load_reviewer_governance_envelope is async")
    else:
        _bad(
            "load_reviewer_governance_envelope must be async",
            "expected coroutine function",
        )


# ---------------------------------------------------------------------------
# 2. Helper reads the canonical universal substrate paths via constants
# ---------------------------------------------------------------------------
#
# Post-ADR-281 D1 refactor (2026-05-15) + ADR-282 vocabulary discipline +
# ADR-296 v2 wake architecture (2026-05-20): the helper no longer hard-codes
# substrate paths. It iterates `_UNIVERSAL_ENVELOPE_DECLS` for kernel-shipped
# paths AND reads bundle-declared program-shaped paths from the active
# bundle's MANIFEST `substrate_abi.reviewer_wake_envelope`. Per-program
# substrate (trading vs author vs commerce) is the bundle's responsibility,
# not the helper's.
#
# This test verifies the helper's STRUCTURAL shape (uses path constants from
# workspace_paths; covers the universal envelope set) rather than grep'ing
# for hard-coded program-specific path strings.

def test_helper_reads_canonical_paths() -> None:
    import services.reviewer_envelope as mod

    # The helper's _UNIVERSAL_ENVELOPE_DECLS must declare the full
    # kernel-universal envelope (governance + persona + occupant +
    # standing-intent).
    if not hasattr(mod, "_UNIVERSAL_ENVELOPE_DECLS"):
        _bad(
            "_UNIVERSAL_ENVELOPE_DECLS exists",
            "helper module must export the universal envelope declaration list",
        )
        return
    decls = mod._UNIVERSAL_ENVELOPE_DECLS
    decl_keys = {k for k, _ in decls}
    expected_universal_keys = {
        "identity_md",
        "principles_md",
        "precedent_md",
        "mandate_md",
        "autonomy_md",
        "preferences_yaml",
        "occupant_md",
        "standing_intent_md",
    }
    missing = expected_universal_keys - decl_keys
    if not missing:
        _ok(f"_UNIVERSAL_ENVELOPE_DECLS covers all {len(expected_universal_keys)} kernel-universal envelope keys")
    else:
        _bad("universal envelope coverage", f"missing keys: {missing}")

    # Program-shaped substrate (operator_profile, risk, ground_truth, signal_files,
    # voice_md, editorial_md, etc.) is now bundle-declared via MANIFEST
    # `substrate_abi.reviewer_wake_envelope`. Verify the helper reads bundle
    # MANIFEST rather than hard-coding paths.
    src = inspect.getsource(mod)
    if "substrate_abi" in src and "reviewer_wake_envelope" in src:
        _ok("helper consults bundle substrate_abi for program-shaped envelope keys (ADR-281 D2)")
    else:
        _bad(
            "bundle substrate_abi consultation",
            "helper must read bundle MANIFEST substrate_abi.reviewer_wake_envelope "
            "for program-shaped envelope keys (per ADR-281 D2)",
        )


# ---------------------------------------------------------------------------
# 3. ReviewerContext TypedDict declares the full envelope key set
# ---------------------------------------------------------------------------

def test_helper_return_shape() -> None:
    """ReviewerContext declares every envelope key the helper can populate."""
    from agents.reviewer_agent import ReviewerContext

    rc_fields = set(getattr(ReviewerContext, "__annotations__", {}).keys())
    # Kernel-universal envelope keys (helper populates unconditionally)
    universal_keys = {
        "identity_md", "principles_md", "precedent_md", "mandate_md",
        "autonomy_md", "preferences_yaml",
        "occupant_md", "standing_intent_md",
    }
    # Program-shaped envelope keys (helper populates from bundle MANIFEST;
    # alpha-trader declares operator_profile_md/risk_md/ground_truth_md/
    # signal_files; alpha-author declares voice_md/editorial_md/etc.). The
    # TypedDict must declare each as Optional so callers can spread without
    # breaking type-checking.
    program_keys = {
        "operator_profile_md", "risk_md", "ground_truth_md", "signal_files",
    }
    expected = universal_keys | program_keys

    missing_on_ctx = expected - rc_fields
    if not missing_on_ctx:
        _ok(f"ReviewerContext declares all {len(expected)} envelope keys (universal + alpha-trader program-shaped)")
    else:
        _bad(
            "ReviewerContext fields",
            f"missing on TypedDict: {missing_on_ctx}",
        )


# ---------------------------------------------------------------------------
# 4. All invoke_reviewer call sites route through the shared helper
# ---------------------------------------------------------------------------
#
# Post-ADR-296-v2 wake architecture (commit 37426c5, 2026-05-20): the
# addressed-trigger Reviewer invocation moved from routes/feed.py to
# services/wake.py::stream_addressed_wake. invocation_dispatcher.py was
# renamed to services/wake.py in the same commit. The proposal-arrival
# Reviewer invocation lives in services/review_proposal_dispatch.py.
#
# Three canonical invoke_reviewer call sites today:
#   - services/wake.py::dispatch_recurrence (cron_tick + manual_fire)
#   - services/wake.py::stream_addressed_wake (addressed)
#   - services/review_proposal_dispatch.py::_run_ai_reviewer (proposal_arrival)
#
# All three must import + call the helper + dict-spread the result into the
# invoke_reviewer context bag.

def test_all_call_sites_use_shared_helper() -> None:
    sites = [
        (ROOT / "services" / "wake.py", "wake.py"),
        (ROOT / "services" / "review_proposal_dispatch.py", "review_proposal_dispatch.py"),
    ]
    missing_import: list[str] = []
    missing_spread: list[str] = []
    for path, label in sites:
        if not path.exists():
            missing_import.append(f"{label}: file not found at {path}")
            continue
        src = path.read_text()
        if "load_reviewer_governance_envelope" not in src:
            missing_import.append(f"{label}: missing import/use of load_reviewer_governance_envelope")
        if "**governance_envelope" not in src:
            missing_spread.append(f"{label}: missing '**governance_envelope' dict-spread")

    if missing_import:
        _bad("envelope helper import at all call sites", "; ".join(missing_import))
    else:
        _ok("envelope helper imported at all invoke_reviewer call sites (wake.py + review_proposal_dispatch.py)")

    if missing_spread:
        _bad("envelope helper dict-spread at all call sites", "; ".join(missing_spread))
    else:
        _ok("**governance_envelope dict-spread present at all invoke_reviewer call sites")


def test_wake_py_preserves_recurrence_context() -> None:
    """wake.py::dispatch_recurrence preserves recurrence-specific context
    keys alongside the spread governance envelope.

    ADR-301 D5 update: `operating_context_block` is no longer composed at
    the wake.py call site — it's assembled inside `load_reviewer_
    governance_envelope` and flows through the `**governance_envelope`
    spread. The recurrence-specific keys (`recurrence_prompt` +
    `recurrence_slug`) still need explicit preservation since the
    envelope helper has no recurrence context.
    """
    src = (ROOT / "services" / "wake.py").read_text()
    for key in (
        '"recurrence_prompt": prompt',
        '"recurrence_slug": recurrence.slug',
    ):
        if key not in src:
            _bad("wake.py recurrence context preservation", f"missing key: {key}")
            return
    # ADR-301: operating_context_block must be assembled by the envelope helper,
    # not at the call site. Assert the call site does NOT re-compose it (would
    # be redundant + a Singular Implementation violation).
    if '"operating_context_block": operating_context' in src:
        _bad(
            "wake.py no longer composes operating_context_block at call site",
            "stale call-site composition still present — ADR-301 D5 incomplete",
        )
        return
    _ok("wake.py preserves recurrence_prompt + recurrence_slug; operating_context_block flows via envelope spread (ADR-301 D5)")


# ---------------------------------------------------------------------------
# 6. ADR-276 doc + cross-refs in place
# ---------------------------------------------------------------------------

def test_adr276_doc_exists() -> None:
    repo_root = ROOT.parent
    path = repo_root / "docs" / "adr" / "ADR-276-reactive-trigger-envelope-governance-preload.md"
    if not path.exists():
        _bad("ADR-276 doc present", f"missing: {path}")
        return
    text = path.read_text()
    needles = ["FOUNDATIONS v8.5", "ADR-274", "ADR-275", "Derived Principle 18", "Singular Implementation"]
    missing = [n for n in needles if n not in text]
    if not missing:
        _ok("ADR-276 doc cites all required ancestors + discipline")
    else:
        _bad("ADR-276 doc cross-refs", f"missing: {missing}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    print("ADR-276 — Reactive-trigger envelope governance pre-load\n")

    test_helper_module_exists()
    test_helper_reads_canonical_paths()
    test_helper_return_shape()
    test_all_call_sites_use_shared_helper()
    test_wake_py_preserves_recurrence_context()
    test_adr276_doc_exists()

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
