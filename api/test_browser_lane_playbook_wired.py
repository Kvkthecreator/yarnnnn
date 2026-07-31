"""The browser-lane playbook stays WIRED and stays TRUE (2026-07-31).

A playbook nobody finds is a file, not doctrine. The 2026-07-31 settings pass
produced method that is expensive to re-learn — the Chrome traps alone cost
hours — so the entry points that lead a future session to it are asserted here,
along with the few claims inside it that would silently rot if the code moved.

This is a WIRING gate, deliberately narrow. It does not police prose.
"""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
EVALS = ROOT / "docs" / "evaluations"
PLAYBOOK = EVALS / "BROWSER-CLICK-PASS-PLAYBOOK.md"
README = EVALS / "README.md"
VERIFICATION = EVALS / "VERIFICATION.md"
LOGIN = ROOT / "api" / "scripts" / "operator" / "browser_login_link.py"


def test_playbook_exists() -> None:
    assert PLAYBOOK.is_file(), (
        "BROWSER-CLICK-PASS-PLAYBOOK.md is gone. It carries the method for the "
        "surface lane; deleting it silently reverts every future browser pass "
        "to re-deriving the Chrome traps from scratch."
    )


@pytest.mark.parametrize(
    "doc,label",
    [(README, "docs/evaluations/README.md"), (VERIFICATION, "docs/evaluations/VERIFICATION.md")],
)
def test_entry_points_route_to_the_playbook(doc: Path, label: str) -> None:
    """Both doors a session enters through must point at the method.

    README is where someone writing a suite starts; VERIFICATION is where the
    radar sends someone whose `web` lane is due. A playbook reachable from
    neither is not discoverable at the moment it is needed."""
    assert "BROWSER-CLICK-PASS-PLAYBOOK.md" in doc.read_text(), (
        f"{label} no longer links the browser playbook — a session lands here "
        f"and re-derives the method (or skips it)."
    )


def test_readme_keeps_the_two_lanes_distinct() -> None:
    """The judgment lane and the surface lane are graded and fired differently.

    Collapsing them is the drift this section exists to prevent: a browser suite
    read as prose loses the per-step PASS/FAIL, and a thesis suite read as
    PASS/FAIL loses the texture that IS the finding."""
    txt = README.read_text()
    assert "suite_kind: browser" in txt and "suite_kind: thesis" in txt, (
        "README no longer names both suite kinds — the two-lane split is the "
        "first thing a suite author needs to know."
    )


def test_playbook_carries_the_load_bearing_traps() -> None:
    """The specific failures that cost this project real time.

    Each of these was a live defect in method, not theory: they are asserted by
    keyword so a well-meaning rewrite cannot quietly drop one."""
    txt = PLAYBOOK.read_text().lower()
    required = {
        "isolatedcontext": "one isolated browser context PER principal (shared cookies overwrite the session)",
        "a11y snapshot": "an a11y snapshot is not a DOM state check (it produced a wrong finding)",
        "frozen at session start": "browser tools do not hot-reload into a running session",
        "falsif": "every gate assertion must be made to fail before it is trusted",
        "receipt": "the substrate half — a DOM-only step is not run",
    }
    missing = [why for key, why in required.items() if key not in txt]
    assert not missing, "the playbook dropped load-bearing lessons: " + "; ".join(missing)


def test_login_instrument_points_at_the_method() -> None:
    """The instrument is where a session is standing when it needs the rule.

    Principal-pair choice silently narrows what a suite CAN test, and the
    narrowing is invisible in the manifest — so the guidance lives on the tool,
    not only in a doc someone may not have opened."""
    src = LOGIN.read_text()
    assert "BROWSER-CLICK-PASS-PLAYBOOK.md" in src, (
        "browser_login_link.py no longer routes to the playbook"
    )
    assert "ISOLATED BROWSER CONTEXT PER PRINCIPAL" in src, (
        "the shared-cookie trap is no longer named on the instrument — this is "
        "the failure that makes a whole pass silently measure one principal twice"
    )


def test_roster_guard_is_still_enforced_in_code() -> None:
    """Never a discipline rule. Minting a session for a real user is an account
    takeover, not an evaluation."""
    src = LOGIN.read_text()
    assert "ALLOWED_EMAILS" in src and "REFUSED" in src, (
        "the roster guard is gone from browser_login_link.py — the refusal must "
        "be enforced in code, not left to the author's care"
    )
