"""Commons-leads removal probe — the 2026-07-30 envelope-audit flagged candidate.

QUESTION (docs/evaluations/2026-07-30-envelope-audit-FINDING.md §4): the three
commons-fact LEAD paragraphs (~1,191 chars of kernel prose in the volatile
suffix, freddie_agent.py::_volatile_suffix::_commons_parts) are the largest
kernel-authored prose block left in the wake envelope. ADR-403's Arm-B evidence
showed the attribution catch survives with the fact SECTIONS gone entirely;
the same-day correction retained them. This probe tests the narrower cut the
audit flagged: LEADS deleted, section header + fact BODIES retained.

MECHANISM: in-process wrapper around `_volatile_suffix` that strips the three
lead paragraphs from the rendered suffix. No production code changes — the
wake fires through the real `_invoke_recurrence_wake` path. The strip is
byte-receipted before firing (offline render, leads-absent + facts-present
asserted).

SITUATION + GATE: reuses probe_freddie_bare_steward wholesale — same seeded
stewardship situation (unplaced dump + mis-attributed AI-voiced file stamped
`operator`), same generic sweep prompt (discovery not scripted), same
three-halves heuristic read + human-read requirement. PASS for the candidate
means: HALF 1 holds INCLUDING touched_misattrib (the catch the leads exist to
coach lands without the coaching).

Usage:
  # free pre-render: prove the strip is real and surgical, no LLM
  cd /Users/macbook/yarnnn/api && python3 -m scripts.operator.probe_commons_leads_removal_local
  # funded live wake (~$0.16)
  cd /Users/macbook/yarnnn/api && python3 -m scripts.operator.probe_commons_leads_removal_local --live
  # restore seeded situation
  cd /Users/macbook/yarnnn/api && python3 -m scripts.operator.probe_commons_leads_removal_local --restore
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
_API_ROOT = _THIS_DIR.parents[1]
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(_API_ROOT / ".env.alpha-ops")
load_dotenv(_API_ROOT / ".env")

# Reuse the standing instrument: seed/restore/gate/capture machinery.
from scripts.operator import probe_freddie_bare_steward as base  # noqa: E402

# The three lead openers (must match freddie_agent.py::_commons_parts verbatim
# openers; the strip asserts it found all three that RENDERED).
LEAD_OPENERS = [
    "**Principals — who may write, the referent for every attribution.**",
    "**Recent revisions and who authored them.**",
    "**Perimeter health (peripherals).**",
]


def _strip_leads(rendered: str) -> tuple[str, int]:
    """Remove each lead paragraph (opener through its terminating blank line).
    Returns (stripped, n_removed)."""
    lines = rendered.split("\n")
    out: list[str] = []
    removed = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        if any(line.startswith(op) for op in LEAD_OPENERS):
            # skip the lead paragraph: consume until the blank line after it
            removed += 1
            while i < len(lines) and lines[i].strip():
                i += 1
            # skip the single blank separator too
            if i < len(lines) and not lines[i].strip():
                i += 1
            continue
        out.append(line)
        i += 1
    return "\n".join(out), removed


def _install_wrapper() -> dict:
    """Wrap _volatile_suffix so every render this process makes is lead-free.
    Returns a receipt dict filled on first render."""
    import agents.freddie_agent as fa

    receipt: dict = {}
    orig = fa._volatile_suffix

    def wrapped(trigger: str, ctx: dict) -> str:
        full = orig(trigger, ctx)
        stripped, n = _strip_leads(full)
        if not receipt:
            receipt.update({
                "full_chars": len(full),
                "stripped_chars": len(stripped),
                "delta": len(full) - len(stripped),
                "leads_removed": n,
                "header_retained": "## The commons" in stripped
                if "## The commons" in full else None,
            })
        return stripped

    fa._volatile_suffix = wrapped
    return receipt


async def _prerender(client) -> int:
    """FREE: render the volatile suffix for the seeded-situation workspace and
    byte-receipt the strip. Seeds + restores nothing; uses live substrate."""
    from services.freddie_envelope import load_freddie_governance_envelope
    import agents.freddie_agent as fa

    envelope, _ = await load_freddie_governance_envelope(client, base.USER_ID)
    ctx = dict(envelope)
    ctx["_snapshot_client"] = client
    ctx["_snapshot_user_id"] = base.USER_ID
    ctx["recurrence_slug"] = "prerender"
    ctx["recurrence_prompt"] = base.SWEEP_PROMPT
    ctx["recurrence_required_capabilities"] = []
    ctx["wake_source"] = "cron_tick"

    full = fa._volatile_suffix("reactive", ctx)
    stripped, n = _strip_leads(full)

    facts_present = [k for k in (
        "principal_commons_fact", "attribution_fact", "peripheral_field_fact",
    ) if (ctx.get(k) or "").strip()]
    facts_survive = all((ctx[k].strip()[:60] in stripped) for k in facts_present)
    leads_gone = not any(op in stripped for op in LEAD_OPENERS)

    print("=== FREE PRE-RENDER (strip receipt) ===")
    print(f"  full volatile: {len(full)} chars; stripped: {len(stripped)}; "
          f"delta: {len(full) - len(stripped)}; lead paragraphs removed: {n}")
    print(f"  facts rendering on this workspace now: {facts_present}")
    print(f"  [{'OK' if leads_gone else 'FAIL'}] all lead openers absent from stripped render")
    print(f"  [{'OK' if facts_survive else 'FAIL'}] fact bodies survive the strip")
    hdr = "## The commons" in full
    print(f"  [{'OK' if ('## The commons' in stripped) == hdr else 'FAIL'}] "
          f"section header retained iff it rendered (rendered={hdr})")
    ok = leads_gone and facts_survive
    print(f"\n  PRE-RENDER: {'PASS — strip is surgical; --live is safe' if ok else 'FAIL — do NOT fire'}")
    return 0 if ok else 1


async def main() -> int:
    from services.supabase import get_service_client
    client = get_service_client()

    if "--restore" in sys.argv:
        base._restore(client)
        return 0

    if "--live" not in sys.argv:
        return await _prerender(client)

    # Live: install the wrapper, then run the standing instrument's live flow
    # unchanged (seed -> fire -> gate -> capture).
    receipt = _install_wrapper()
    print("[leads-removal] wrapper installed — every envelope this process "
          "renders is lead-free (header + facts retained)")
    rc = await base._live(client)
    print(f"\n=== STRIP RECEIPT (from the fired wake's own render) ===")
    for k, v in receipt.items():
        print(f"  {k}: {v}")
    return rc


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
