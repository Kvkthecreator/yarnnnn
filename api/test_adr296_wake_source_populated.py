"""ADR-296 v2 D1 + D2 regression gate — wake_source + funnel_decision
populated at every Reviewer-wake telemetry call site.

Asserts that the kernel call sites that record_execution_event for Reviewer
wakes populate the wake-source taxonomy + funnel-decision taxonomy stamped
by migration 177.

Wake sources (D1 taxonomy):
  - cron_tick          — scheduler dispatcher path (judgment + mechanical)
  - addressed          — operator addressed Reviewer via chat
  - proposal_arrival   — proposal creation woke Reviewer (NOT yet stamped —
                          review_proposal_dispatch does not write its own
                          execution_events row; Reviewer's internal cost-
                          ledger path writes it. Tracked for Checkpoint 2.)
  - substrate_event    — hooks (Checkpoint 2 — kernel doesn't write these yet)
  - manual_fire        — FireInvocation in chat (dispatcher with trigger="addressed")

Funnel decisions (D2 taxonomy):
  - skip               — Tier 1 kernel gate (balance/spend/cap/min_interval)
  - tier_2_wait        — Tier 2 Haiku said wait (Checkpoint 2 — funnel not built yet)
  - tier_2_observe     — Tier 2 Haiku said observe (Checkpoint 2)
  - escalate           — Reviewer full cycle fired
  - mechanical         — Mechanical-mode recurrence bypass (no Reviewer)

Checkpoint 1 scope: Reviewer-wake telemetry sites in wake.py
(11 record_execution_event calls) + routes/feed.py (2 calls) all carry
wake_source + funnel_decision. Non-wake LLM-cost-ledger sites (anthropic.py,
session_continuity.py, recurrence_prompt_inference.py, primitives/infer_*.py,
primitives/dispatch_specialist.py, primitives/web_search.py) are sub-LLM-call
cost rows per ADR-291; they correctly stamp neither field (NULL).

Run: python api/test_adr296_wake_source_populated.py
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
# 1. Telemetry signature accepts wake_source + funnel_decision (Session B
#    substrate). Sanity guard against regression.
# ----------------------------------------------------------------------------

def test_telemetry_signature_accepts_wake_kwargs() -> None:
    import inspect
    from services import telemetry

    sig = inspect.signature(telemetry.record_execution_event)
    for name in ("wake_source", "funnel_decision"):
        if name not in sig.parameters:
            _fail(
                f"record_execution_event missing kwarg {name!r}",
                "Session B added the kwargs — see migration 177 + telemetry.py",
            )
        if sig.parameters[name].default is not None:
            _fail(
                f"record_execution_event.{name} default not None",
                f"got {sig.parameters[name].default!r} — expected optional None",
            )
    _ok("record_execution_event accepts wake_source + funnel_decision (Optional[str]=None)")


# ----------------------------------------------------------------------------
# 2. wake.py — every record_execution_event call carries
#    wake_source. The local `wake_source` variable is computed once at entry.
# ----------------------------------------------------------------------------

def test_dispatcher_computes_wake_source_at_entry() -> None:
    """Post-Checkpoint-2: wake_source comes in as a function parameter on
    _invoke_recurrence_wake (passed by submit_wake_proposal). The legacy
    `trigger` is derived from wake_source per the kw-only signature.
    """
    src = _read("services/wake.py")
    # Verify the new signature: _invoke_recurrence_wake accepts wake_source
    m = re.search(
        r"async def _invoke_recurrence_wake\([^)]*wake_source:\s*WakeSource",
        src, re.DOTALL,
    )
    if not m:
        _fail(
            "_invoke_recurrence_wake signature missing wake_source: WakeSource",
            "Phase 1A: caller (submit_wake_proposal) passes wake_source explicitly",
        )
    # Verify trigger is derived inside the body
    if 'trigger = "addressed" if wake_source == "manual_fire" else "reactive"' not in src:
        _fail(
            "_invoke_recurrence_wake does not derive trigger from wake_source",
            "Phase 1A: trigger is internal vocabulary derived from wake_source",
        )
    _ok("wake.py: _invoke_recurrence_wake accepts wake_source param + derives trigger internally")


def test_dispatcher_all_telemetry_sites_stamp_wake_source() -> None:
    """Every record_execution_event call in wake.py carries a wake_source.
    The pattern is either `wake_source=wake_source` (param-threaded in
    recurrence + mechanical bodies) or `wake_source="<source>"` literal
    (substrate_event body — the source is known statically).
    """
    src = _read("services/wake.py")
    call_count = len(re.findall(r"record_execution_event\(", src))
    threaded = len(re.findall(r"wake_source=wake_source", src))
    literal = len(re.findall(r'wake_source="(?:cron_tick|manual_fire|substrate_event|addressed|proposal_arrival)"', src))
    total_stamped = threaded + literal
    if total_stamped < call_count:
        _fail(
            "wake.py has unstamped record_execution_event calls",
            f"found {call_count} calls, {total_stamped} carry wake_source "
            f"({threaded} threaded, {literal} literal)",
        )
    _ok(f"wake.py: all {call_count} record_execution_event calls carry "
        f"wake_source ({threaded} param-threaded, {literal} source-literal)")


def test_dispatcher_funnel_decision_taxonomy() -> None:
    """funnel_decision values at dispatcher sites match the D2 taxonomy."""
    src = _read("services/wake.py")
    # Find all funnel_decision= populations
    populations = re.findall(r'funnel_decision="([^"]+)"', src)
    allowed = {"skip", "tier_2_wait", "tier_2_observe", "escalate", "mechanical"}
    bad = [p for p in populations if p not in allowed]
    if bad:
        _fail(
            "invocation_dispatcher uses funnel_decision values outside the D2 taxonomy",
            f"bad values: {sorted(set(bad))}",
        )
    _ok(f"invocation_dispatcher funnel_decision values all within taxonomy "
        f"(found: {sorted(set(populations))})")

    # All four expected categories must appear in the dispatcher.
    expected_present = {"skip", "escalate", "mechanical"}
    missing = expected_present - set(populations)
    if missing:
        _fail(
            "invocation_dispatcher missing funnel_decision categories",
            f"expected at least {sorted(expected_present)}, missing {sorted(missing)}",
        )
    _ok(f"invocation_dispatcher carries all expected funnel_decision categories: "
        f"{sorted(expected_present)}")


def test_dispatch_mechanical_accepts_wake_source() -> None:
    """_dispatch_mechanical accepts wake_source as a keyword-only parameter."""
    src = _read("services/wake.py")
    if not re.search(r"async def _dispatch_mechanical\([^)]*wake_source:\s*str", src, re.DOTALL):
        _fail(
            "_dispatch_mechanical signature missing wake_source",
            "must accept wake_source: str as kw-only per ADR-296 v2",
        )
    _ok("_dispatch_mechanical accepts wake_source kw-only parameter")


# ----------------------------------------------------------------------------
# 3. routes/feed.py — addressed cycle stamps wake_source="addressed" +
#    funnel_decision="escalate"
# ----------------------------------------------------------------------------

def test_feed_addressed_stamps_wake_source() -> None:
    """Both record_execution_event call sites in feed.py (addressed-success +
    addressed-failure) must carry wake_source="addressed" + funnel_decision=
    "escalate".

    Approach: scan call-site lines structurally — find each
    `record_execution_event(` opening, walk until its matching `)`,
    inspect the block content. Avoids regex brittleness around nested
    `output.get(...)` parens.
    """
    src = _read("routes/feed.py")

    # Walk parenthesis-balanced blocks for each record_execution_event call.
    blocks: list[str] = []
    i = 0
    while True:
        i = src.find("record_execution_event(", i)
        if i == -1:
            break
        # Walk balanced parens from the opening `(`
        depth = 0
        j = i + len("record_execution_event")  # at the `(`
        start = j
        while j < len(src):
            c = src[j]
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    blocks.append(src[start : j + 1])
                    break
            j += 1
        i = j + 1

    if not blocks:
        _fail(
            "feed.py has no record_execution_event call sites",
            "expected at least 2 (addressed-success + addressed-failure)",
        )

    # Filter to addressed-cycle blocks.
    addressed_blocks = [b for b in blocks if 'slug="addressed"' in b]
    if len(addressed_blocks) < 2:
        _fail(
            "feed.py addressed-cycle record_execution_event call sites < 2",
            f"found {len(addressed_blocks)}",
        )

    for idx, block in enumerate(addressed_blocks):
        if 'wake_source="addressed"' not in block:
            _fail(
                f"feed.py addressed block #{idx} missing wake_source=\"addressed\"",
                block[:200],
            )
        if 'funnel_decision="escalate"' not in block:
            _fail(
                f"feed.py addressed block #{idx} missing funnel_decision=\"escalate\"",
                block[:200],
            )
    _ok(f"feed.py: all {len(addressed_blocks)} addressed-cycle "
        f"record_execution_event call sites carry wake_source + funnel_decision")


# ----------------------------------------------------------------------------
# 4. Non-wake LLM-cost-ledger sites correctly do NOT stamp wake_source.
#    These are sub-LLM-call cost rows per ADR-291.
# ----------------------------------------------------------------------------

def test_non_wake_sites_do_not_stamp_wake_source() -> None:
    """Sub-LLM-call cost ledger sites (per ADR-291) write rows that are not
    Reviewer-wake events; wake_source legitimately stays NULL for them.

    Smoke check: confirm no spurious `wake_source=` appears in files that
    write sub-LLM-call rows. If a future commit accidentally stamps a
    wake_source on a sub-call row, this gate catches it.
    """
    non_wake_files = [
        "services/session_continuity.py",
        "services/recurrence_prompt_inference.py",
        # ADR-314 D4: infer_workspace.py deleted (first-act scaffold dissolved).
        "services/primitives/infer_context.py",
        "services/primitives/dispatch_specialist.py",
        "services/primitives/web_search.py",
    ]
    for rel in non_wake_files:
        src = _read(rel)
        if re.search(r"wake_source=", src):
            _fail(
                f"{rel} stamps wake_source — but it writes sub-LLM-call rows",
                "wake_source stamps Reviewer-wake events only (ADR-296 v2 D1). "
                "Sub-LLM calls are cost-ledger rows per ADR-291.",
            )
    _ok(f"Non-wake LLM-cost-ledger sites correctly omit wake_source "
        f"({len(non_wake_files)} files audited)")


# ----------------------------------------------------------------------------
# Runner
# ----------------------------------------------------------------------------

def main() -> None:
    print("=" * 72)
    print("ADR-296 v2 D1 + D2 — wake_source + funnel_decision population gate")
    print("=" * 72)

    test_telemetry_signature_accepts_wake_kwargs()
    test_dispatcher_computes_wake_source_at_entry()
    test_dispatcher_all_telemetry_sites_stamp_wake_source()
    test_dispatcher_funnel_decision_taxonomy()
    test_dispatch_mechanical_accepts_wake_source()
    test_feed_addressed_stamps_wake_source()
    test_non_wake_sites_do_not_stamp_wake_source()

    print()
    print("=" * 72)
    print("All ADR-296 v2 D1 + D2 wake-source population assertions PASS")
    print("=" * 72)


if __name__ == "__main__":
    main()
