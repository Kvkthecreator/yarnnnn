"""Wake-envelope kernel-prose ratchet — the 2026-07-30 envelope audit.

ADR-403 collapsed the wake envelope to the thin CC-shape (cached governance
prefix + volatile suffix + bare ask) and held it with evaluation receipts
(docs/evaluations/2026-07-02-freddie-envelope-rung3-armB-v2/). The system
prompt is ceiling-gated (test_adr323 / test_adr383); the envelope was not —
an ungated cut regrows. This gate holds the KERNEL-AUTHORED bytes of the
envelope. Operator/agent-authored substrate (principles.md, standing intent,
budget yaml) is deliberately NOT gated — that is the workspace's content,
not the kernel's prose.

Measured baselines (2026-07-30, live render on 3 workspaces — see
docs/evaluations/2026-07-30-envelope-audit-FINDING.md):
  - renderer scaffold, empty ctx: governance 191 · volatile <= 343 per shape
  - commons-fact leads (ADR-390 arc, fire only when facts are non-empty): 1,191
  - steward kernel constants (bare workspaces only, cached): 7,566

Raising any ceiling requires the same evidence as adding a prompt instruction
(ADR-306 / DP22 / the ADR-390 removal-over-addition discipline): a REPEATED
observed failure, named in the raising commit. New envelope prose returns as
one snapshot head-line with a receipt, never as a section revival (ADR-403
Consequences).

Run: python -m pytest api/test_envelope_scaffold_ratchet.py -q
"""
from __future__ import annotations


# Ceilings: measured baseline + modest headroom, far below dilution territory.
GOVERNANCE_SCAFFOLD_CEILING = 400
VOLATILE_SCAFFOLD_CEILING = 700       # per trigger shape, incl. interface rules
COMMONS_LEADS_CEILING = 1_600
STEWARD_CONSTANTS_CEILING = 9_000


def test_governance_scaffold_ceiling():
    """Kernel prose in the governance prefix with NO substrate: headers +
    empty-fallback lines only."""
    from agents.freddie_agent import _governance_prefix

    scaffold = _governance_prefix({})
    assert len(scaffold) <= GOVERNANCE_SCAFFOLD_CEILING, (
        f"governance scaffold is {len(scaffold)} chars "
        f"(> {GOVERNANCE_SCAFFOLD_CEILING}). Baseline 191 (2026-07-30). "
        "Substrate files render verbatim under thin headers — new prose here "
        "is coaching, which ADR-403 deleted. Raise only for a repeated "
        "observed failure, named in the raising commit."
    )


def test_volatile_scaffold_ceiling_per_shape():
    """Kernel prose in the volatile suffix per trigger shape, empty substrate.

    Enumerated per shape (a counting gate cannot defend a per-site
    invariant): addressed / reactive-recurrence / reactive-proposal.
    """
    from agents.freddie_agent import _volatile_suffix

    shapes = {
        "addressed": ("addressed", {"user_message": "x"}),
        "reactive-recurrence": (
            "reactive", {"recurrence_slug": "s", "recurrence_prompt": "x"}),
        "reactive-proposal": (
            "reactive",
            {"proposal_row": {"action_type": "a", "reversibility": "r",
                              "inputs": {}}}),
    }
    for label, (trigger, ctx) in shapes.items():
        rendered = _volatile_suffix(trigger, ctx)
        assert len(rendered) <= VOLATILE_SCAFFOLD_CEILING, (
            f"volatile scaffold [{label}] is {len(rendered)} chars "
            f"(> {VOLATILE_SCAFFOLD_CEILING}). Baselines 124/343/339 "
            "(2026-07-30). The volatile suffix is UNCACHED — every byte here "
            "bills at full rate on every wake. Interface rules stay terse; "
            "coaching is deleted (ADR-403)."
        )


def test_commons_leads_ceiling():
    """The three ADR-390 commons-fact leads are the one retained
    instruction-prose block in the envelope (ADR-403 same-day correction).
    They render only when their fact is non-empty. Hold their size, and
    hold the set at exactly the three ratified arcs."""
    from agents.freddie_agent import _volatile_suffix

    base = {"user_message": "x"}
    facts = {"principal_commons_fact": "F", "attribution_fact": "F",
             "peripheral_field_fact": "F"}
    with_leads = _volatile_suffix("addressed", {**base, **facts})
    without = _volatile_suffix("addressed", base)
    lead_bytes = len(with_leads) - len(without) - sum(len(v) for v in facts.values())
    assert lead_bytes <= COMMONS_LEADS_CEILING, (
        f"commons leads total {lead_bytes} chars (> {COMMONS_LEADS_CEILING}). "
        "Baseline 1,191 (2026-07-30). These are the ADR-389/390 attribution-"
        "catch arc — the collapse proved the catch survives even WITHOUT "
        "them (ADR-403 Evidence); growth here is dilution, not safety."
    )
    # Empty-graceful invariant: no fact -> no lead, no section header.
    assert "The commons" not in without, (
        "commons section rendered with no facts present — the empty-graceful "
        "contract (ADR-403 correction) is broken; bare-steward wakes must "
        "match the measured Arm-B shape."
    )


def test_steward_constants_ceiling():
    """The kernel steward constitution (ADR-414 B2) rides every bare-steward
    wake in place of seeded files. It is kernel-authored prompt content and
    ratchets like one."""
    from services.orchestration import (
        DEFAULT_STEWARD_IDENTITY_MD,
        DEFAULT_STEWARD_MANDATE_MD,
        DEFAULT_STEWARD_PRINCIPLES_MD,
    )

    total = (len(DEFAULT_STEWARD_IDENTITY_MD)
             + len(DEFAULT_STEWARD_MANDATE_MD)
             + len(DEFAULT_STEWARD_PRINCIPLES_MD))
    assert total <= STEWARD_CONSTANTS_CEILING, (
        f"steward constants total {total} chars (> {STEWARD_CONSTANTS_CEILING}). "
        "Baseline 7,566 (2026-07-30: identity 1,010 + mandate 2,592 + "
        "principles 3,964). These reach every bare workspace at the next "
        "wake — the highest-leverage prose surface in the system. Growth "
        "needs the ADR-306 evidence bar."
    )
