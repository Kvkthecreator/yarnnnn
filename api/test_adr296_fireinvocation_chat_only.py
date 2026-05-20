"""ADR-296 v2 D3 regression gate — FireInvocation is chat-only.

Asserts that the FireInvocation primitive is present in CHAT_PRIMITIVES
(operator-initiated manual fire — operator presence is itself a wake-warrant
per ADR-296 v2 D1) and ABSENT from REVIEWER_PRIMITIVES (Reviewer does not
self-invoke — its authority is over cadence preference + standing intent
per D3).

Companion sanity checks:
  - Reviewer persona-frame (reviewer_agent.py + cockpit_awareness.py)
    contains NO `FireInvocation` teaching that instructs the Reviewer to
    call it.
  - reviewer_chat_surfacing.py contains NO live `_is_mechanical_fire_invocation`
    helper (dissolved per D3 narrowing; SyncPlatformState mirror-refresh
    case survives).
  - review_proposal_dispatch._execute_reviewer_directives contains NO
    `action == "fire_invocation"` branch (Reviewer directives mechanism
    is now `write_file | clarify` only).

Run: python api/test_adr296_fireinvocation_chat_only.py
"""

from __future__ import annotations

import sys
import re
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))


def _ok(msg: str) -> None:
    print(f"  PASS  {msg}")


def _fail(label: str, detail: str = "") -> None:
    print(f"  FAIL  {label}" + (f" — {detail}" if detail else ""))
    raise SystemExit(1)


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


# ----------------------------------------------------------------------------
# 1. REVIEWER_PRIMITIVES does NOT include FireInvocation; CHAT does.
# ----------------------------------------------------------------------------

def test_fireinvocation_chat_only() -> None:
    from services.primitives.registry import (
        CHAT_PRIMITIVES,
        REVIEWER_PRIMITIVES,
        HEADLESS_PRIMITIVES,
    )

    chat_names = {t["name"] for t in CHAT_PRIMITIVES}
    reviewer_names = {t["name"] for t in REVIEWER_PRIMITIVES}
    headless_names = {t["name"] for t in HEADLESS_PRIMITIVES}

    if "FireInvocation" not in chat_names:
        _fail(
            "CHAT_PRIMITIVES missing FireInvocation",
            "operator-initiated manual fire path must remain available",
        )
    _ok("FireInvocation present in CHAT_PRIMITIVES (operator manual fire path)")

    if "FireInvocation" in reviewer_names:
        _fail(
            "FireInvocation in REVIEWER_PRIMITIVES",
            "ADR-296 v2 D3: Reviewer does not self-invoke. Remove from "
            "REVIEWER_PRIMITIVES; cadence is authored via Schedule.",
        )
    _ok("FireInvocation absent from REVIEWER_PRIMITIVES (ADR-296 v2 D3)")

    # Headless surface keeps FireInvocation for now — headless agents acting
    # as operator-proxies during scenario harnesses use it. ADR-296 v2 does
    # not narrow the headless surface; only the Reviewer surface tightens.
    if "FireInvocation" not in headless_names:
        _fail(
            "HEADLESS_PRIMITIVES unexpectedly missing FireInvocation",
            "ADR-296 v2 narrows only REVIEWER_PRIMITIVES; headless surface "
            "preserved",
        )
    _ok("FireInvocation present in HEADLESS_PRIMITIVES (per scope: only "
        "REVIEWER surface narrows)")


# ----------------------------------------------------------------------------
# 2. Reviewer persona-frame teaches cadence + standing intent, NOT FireInvocation
# ----------------------------------------------------------------------------

def test_reviewer_agent_persona_no_fireinvocation_teaching() -> None:
    """Reviewer's _PERSONA_FRAME must not instruct the model to call FireInvocation."""
    src = _read("agents/reviewer_agent.py")
    # The earlier "FireInvocation the relevant recurrence to commission fresh
    # substrate" instruction must be gone.
    if re.search(r"FireInvocation\s+the\s+relevant\s+recurrence", src):
        _fail(
            "reviewer_agent.py still teaches FireInvocation",
            "ADR-296 v2 D3 deleted that guidance; replaced by cadence + "
            "standing intent",
        )
    _ok("reviewer_agent.py persona-frame does not teach FireInvocation")

    # Remaining FireInvocation mentions must sit inside a multi-line
    # deletion-provenance comment block (`ADR-296 v2 D3` within ±3 lines)
    # or carry the marker inline. Accommodates the multi-line "input:"
    # comment block at reviewer_agent.py:1417-1422.
    lines = src.splitlines()
    for line_no, line in enumerate(lines, start=1):
        if "FireInvocation" in line or "fire_invocation" in line:
            window_start = max(0, line_no - 4)
            window_end = min(len(lines), line_no + 3)
            window = "\n".join(lines[window_start:window_end])
            if "ADR-296" not in window:
                _fail(
                    f"reviewer_agent.py:{line_no} mentions FireInvocation "
                    "without ADR-296 provenance within ±3 lines",
                    line.strip()[:120],
                )
    _ok("All FireInvocation/fire_invocation mentions in reviewer_agent.py "
        "carry ADR-296 deletion provenance (inline or within ±3 lines)")


def test_cockpit_awareness_no_fireinvocation_teaching() -> None:
    """cockpit_awareness.py must not teach FireInvocation as Reviewer authority."""
    src = _read("agents/cockpit_awareness.py")
    # Bare `FireInvocation —` or `FireInvocation on` teaching patterns must
    # be absent.
    if re.search(r"FireInvocation\s+(?:on|—)", src):
        _fail(
            "cockpit_awareness.py teaches FireInvocation as Reviewer tool",
            "ADR-296 v2 D3: Reviewer does not self-invoke",
        )
    _ok("cockpit_awareness.py does not teach FireInvocation as Reviewer authority")


# ----------------------------------------------------------------------------
# 3. reviewer_chat_surfacing dissolved _is_mechanical_fire_invocation helper
# ----------------------------------------------------------------------------

def test_chat_surfacing_dissolved_mechanical_fire_helper() -> None:
    src = _read("services/reviewer_chat_surfacing.py")
    if "def _is_mechanical_fire_invocation(" in src:
        _fail(
            "_is_mechanical_fire_invocation still defined",
            "ADR-296 v2 D3 dissolved it — Reviewer no longer calls "
            "FireInvocation, so the classifier branch is unreachable",
        )
    _ok("_is_mechanical_fire_invocation helper dissolved per ADR-296 v2 D3")

    # The narrate_reviewer_action FireInvocation case must be gone.
    if re.search(r'if\s+tool\s*==\s*"FireInvocation"\s*:', src):
        _fail(
            "narrate_reviewer_action still has FireInvocation case",
            "ADR-296 v2 D3: Reviewer does not call FireInvocation",
        )
    _ok("narrate_reviewer_action has no FireInvocation case")

    # is_mirror_refresh_action survives (SyncPlatformState case is the
    # remaining override case per ADR-264).
    if "def is_mirror_refresh_action(" not in src:
        _fail(
            "is_mirror_refresh_action classifier missing",
            "narrowed but not deleted — SyncPlatformState case remains",
        )
    _ok("is_mirror_refresh_action classifier survives (narrowed to "
        "SyncPlatformState case)")


# ----------------------------------------------------------------------------
# 4. review_proposal_dispatch directives mechanism shrunk to {write_file, clarify}
# ----------------------------------------------------------------------------

def test_directives_no_fire_invocation_action() -> None:
    """_execute_reviewer_directives must not handle action='fire_invocation'."""
    src = _read("services/review_proposal_dispatch.py")
    # The action == "fire_invocation" branch must be gone.
    if re.search(r'if\s+action\s*==\s*"fire_invocation"\s*:', src):
        _fail(
            "_execute_reviewer_directives still handles fire_invocation",
            "ADR-296 v2 D3: directives mechanism is {write_file, clarify} only",
        )
    _ok("_execute_reviewer_directives has no fire_invocation branch")


def test_compat_adapter_no_fireinvocation_extraction() -> None:
    """reviewer_agent_compat.py must not extract FireInvocation actions as directives."""
    src = _read("agents/reviewer_agent_compat.py")
    if re.search(r'tool"\s*\)\s*==\s*"FireInvocation"', src):
        _fail(
            "reviewer_agent_compat still extracts FireInvocation actions",
            "ADR-296 v2 D3 deleted the directives-extraction block",
        )
    _ok("reviewer_agent_compat.output_to_review_decision has no "
        "FireInvocation-extraction block")


# ----------------------------------------------------------------------------
# 5. orchestration.py scaffold template teaches cadence + standing-intent, not fire
# ----------------------------------------------------------------------------

def test_orchestration_scaffold_no_fire_invocation_directive() -> None:
    """The Reviewer principles.md scaffold template must not teach
    `directive: fire_invocation(...)`."""
    src = _read("services/orchestration.py")
    if re.search(r"directive:\s*fire_invocation\b", src):
        _fail(
            "orchestration.py still teaches `directive: fire_invocation`",
            "ADR-296 v2 D3 replaced with Schedule + standing intent",
        )
    _ok("orchestration.py scaffold template does not teach fire_invocation directive")


# ----------------------------------------------------------------------------
# Runner
# ----------------------------------------------------------------------------

def main() -> None:
    print("=" * 72)
    print("ADR-296 v2 D3 — FireInvocation chat-only regression gate")
    print("=" * 72)

    test_fireinvocation_chat_only()
    test_reviewer_agent_persona_no_fireinvocation_teaching()
    test_cockpit_awareness_no_fireinvocation_teaching()
    test_chat_surfacing_dissolved_mechanical_fire_helper()
    test_directives_no_fire_invocation_action()
    test_compat_adapter_no_fireinvocation_extraction()
    test_orchestration_scaffold_no_fire_invocation_directive()

    print()
    print("=" * 72)
    print("All ADR-296 v2 D3 assertions PASS")
    print("=" * 72)


if __name__ == "__main__":
    main()
