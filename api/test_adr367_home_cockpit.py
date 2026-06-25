"""ADR-367 gate — Home as Operating Cockpit (the dashboard acts in place).

ADR-367 is FE-only — the inline decision reuses the existing ADR-307 gate +
the shared `useProposalModal` (one modal path, a new entry point). No schema,
primitive, or backend change. The web package has no JS test runner, so the
load-bearing FE invariants are guarded here by source-assertion (the same
pattern as the ADR-350 / ADR-351 FE guards), with `tsc --noEmit` as the
companion type gate run in web/.

Invariants:
  1. The Home decision-queue slot ACTS IN PLACE — it opens the shared proposal
     modal (`useProposalModal`) and renders the modal element, instead of
     deep-linking each row to /queue. (Singular Implementation: same modal as
     QueueBody / chat stream / briefing — no inline-button bypass of the gate.)
  2. The slot's deep-links target the Notifications composition's `resolve`
     pane (post-ADR-349 canonical act surface), NOT the bare /queue mirror.
  3. The ADR-350 StandingBand heads the PROGRAM cockpit (ADR-369 §D5
     relocation — the standing obligation is program-shaped). It left
     HomeRenderer; the Home front page keeps the kernel decision queue.
  4. Notifications is PRESERVED as the full act-workbench (NOT demoted) — its
     resolve pane still mounts QueueBody (deliberate tiered redundancy, §D3).
  5. The slot no longer declares itself a glance-only board (the pre-ADR-367
     "not the place you act" framing is gone).

Run: pytest test_adr367_home_cockpit.py -q
"""
from __future__ import annotations

import os

_WEB = os.path.join(os.path.dirname(__file__), "..", "web")


def _read_web(rel: str) -> str:
    with open(os.path.join(_WEB, rel), encoding="utf-8") as fh:
        return fh.read()


def test_decision_queue_acts_in_place_via_shared_modal():
    src = _read_web("components/library/kernel-home/KernelDecisionQueue.tsx")
    # reuses the shared proposal modal (Singular Implementation — one gate)
    assert "useProposalModal" in src
    assert "openProposal(toProposalData(" in src
    # the modal element is actually rendered in the tree
    assert "{modalElement}" in src


def test_decision_queue_rows_do_not_deep_link_to_bare_queue_mirror():
    src = _read_web("components/library/kernel-home/KernelDecisionQueue.tsx")
    # §D5: links go to the Notifications composition resolve pane, not /queue
    assert 'to="notifications"' in src
    assert "pane: 'resolve'" in src
    # the pre-ADR-367 row link (SurfaceLink to="queue") is gone
    assert 'to="queue"' not in src, "Home slot must target the Notifications workbench, not the bare queue mirror"


def test_no_inline_button_gate_bypass():
    """The act path must be the shared modal, never re-introduced inline
    Approve/Reject buttons that skip the reasoning + gate (the anti-pattern
    useProposalModal exists to kill)."""
    src = _read_web("components/library/kernel-home/KernelDecisionQueue.tsx")
    assert "api.proposals.approve" not in src, "no direct approve call — route through the shared modal/gate"
    assert "api.proposals.reject" not in src


def test_standing_band_heads_the_program_cockpit():
    """ADR-369 §D5 (amends ADR-367 §D4): the standing obligation is
    program-derived (budget→pace × mandate→output), so under the shape axis it
    is program-shaped and RELOCATES from Home's head to the program cockpit's
    head. ADR-367's "acts in place" principle is preserved and now spans both
    tabs (Home acts in place on the kernel decision queue; the program tab on
    its own affordances).

    The StandingBand mount left HomeRenderer; it now heads ProgramCockpit, above
    the program sections. The Home front-page body holds the kernel decision
    queue and never mounts the band."""
    cockpit = _read_web("components/library/kernel-home/ProgramCockpit.tsx")
    assert "<StandingBand />" in cockpit, (
        "ADR-369 §D5: the StandingBand relocates to the program cockpit head."
    )
    # heads the cockpit — above the program-section dispatch (compare against
    # the JSX call site, not the import, which necessarily precedes JSX)
    assert cockpit.index("<StandingBand />") < cockpit.index("dispatchComponent({ kind:")

    # the band left HomeRenderer (no longer mounted on the surface root)
    home = _read_web("components/library/HomeRenderer.tsx")
    assert "<StandingBand />" not in home, (
        "ADR-369 §D5: the StandingBand mount moved off HomeRenderer to "
        "ProgramCockpit."
    )

    # the Home front page keeps the decision queue (acts in place) and does NOT
    # mount the standing band (it's program-shaped now).
    front = _read_web("components/library/kernel-home/HomeFrontPage.tsx")
    assert "<KernelDecisionQueue" in front
    assert "StandingBand" not in front


def test_notifications_preserved_as_full_workbench():
    """§D3: Notifications is NOT demoted — its resolve pane still mounts the
    full QueueBody workbench (deliberate tiered redundancy with Home)."""
    page = _read_web("app/(authenticated)/notifications/page.tsx")
    assert "QueueBody" in page


def test_slot_no_longer_declares_itself_glance_only():
    src = _read_web("components/library/kernel-home/KernelDecisionQueue.tsx")
    # the pre-ADR-367 framing ("not the place you act on each proposal") is gone
    assert "not the place you act" not in src
    # the new framing is present
    assert "act" in src.lower() and "in place" in src.lower()


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
