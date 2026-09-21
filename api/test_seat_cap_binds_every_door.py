"""The free→paid seat cap binds EVERY door that mints a human grant (2026-09-21).

THE DEFECT THIS GUARDS. There are two doors to a `principal_grants` row with
`role='member'` — the email invite (`workspace_invites.create_invite`) and the
share link's redemption (`workspace_shares.accept_share`). Both end in exactly the
role the seat counter bills (`HUMAN_SEAT_ROLES = ("owner","member")`), and the
share link is re-redeemable by design ("it can be used more than once", said in the
share dialog itself). The cap lived INLINE in `create_invite`, so it was a property
of one door rather than of the outcome: a Free workspace could pass its 2-seat cap
without bound through the share door, and `sync_seat_quantity` was not called there
either — invisible to billing twice over.

ADR-537's own comparison table asserts the open join link `| Bills | yes |`. It did
not. The ADR reasoned that "the seat gate lives in the service, independent of the
caller" — true of `create_invite`'s service, and never true of the share service.

WHY THIS SHAPE. A test that only asserted "create_invite refuses the 3rd human"
passed throughout the defect — it was already true. The arms below assert the rule
at the SHARED function and at EACH call site, so a door added later without the
check fails here rather than shipping green. The call-site arms read the source
(AST/text), because the alternative is a live Supabase, and a gate that needs the
network is a gate that gets skipped.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

API = Path(__file__).parent
SHARES = API / "services" / "workspace_shares.py"
INVITES = API / "services" / "workspace_invites.py"
TIERS = API / "services" / "billing_tiers.py"
SHARE_ROUTE = API / "routes" / "shares.py"

CHECK = "seat_cap_blocks_new_human"


# ---------------------------------------------------------------------------
# 1. The rule exists in ONE home, and it is the billing module
# ---------------------------------------------------------------------------

def test_the_cap_has_one_home():
    """The check is defined in billing_tiers, beside the roles it counts."""
    tree = ast.parse(TIERS.read_text())
    fns = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    assert CHECK in fns, (
        f"{CHECK}() is not defined in billing_tiers.py. The free→paid boundary "
        f"guards an OUTCOME (one more human) reached through several doors; it "
        f"cannot live inline in any one of them."
    )


def test_the_cap_counts_the_roles_that_bill():
    """It counts HUMAN_SEAT_ROLES — the same roles `billable_seats` charges for.

    A cap that counted a different set than the biller would refuse the wrong
    people, or admit people it then charges for.
    """
    src = _fn_source(TIERS, CHECK)
    assert "HUMAN_SEAT_ROLES" in src, (
        "the cap does not count HUMAN_SEAT_ROLES — it would disagree with the "
        "seat counter it exists to protect"
    )
    assert 'eq("status", "active")' in src, "the cap counts non-active grants"


def test_the_cap_fails_open():
    """A read error ADMITS. Never block a legitimate join on a DB hiccup."""
    src = _fn_source(TIERS, CHECK)
    tail = src[src.index("except"):]
    assert "return False" in tail, (
        "the cap fails CLOSED on a read error — a transient Supabase blip would "
        "refuse legitimate joins. The behaviour it replaced failed open."
    )


def test_a_paid_or_exempt_workspace_is_never_refused():
    """ADR-445 §4 — the seat axis BILLS an extra human, it never refuses one."""
    src = _fn_source(TIERS, CHECK)
    assert "billing_exempt" in src and "PAID_TIERS" in src, (
        "the cap does not exempt paid/billing-exempt workspaces; a paid team "
        "would be blocked from growing, which is not the free→paid boundary"
    )


# ---------------------------------------------------------------------------
# 2. EVERY door calls it — the per-site arms
# ---------------------------------------------------------------------------

#: Each door that mints a human `principal_grants` row, and the function that
#: must call the cap. Adding a door without adding it here fails arm 3.
HUMAN_GRANT_DOORS = {
    "create_invite": INVITES,
    "accept_share": SHARES,
}


@pytest.mark.parametrize("fn_name", sorted(HUMAN_GRANT_DOORS))
def test_every_human_grant_door_calls_the_cap(fn_name: str):
    """PER-SITE: the door consults the cap before minting.

    Falsify by deleting the `seat_cap_blocks_new_human(...)` call from either
    function — the corresponding arm goes red.
    """
    src = _fn_source(HUMAN_GRANT_DOORS[fn_name], fn_name)
    assert re.search(rf"\b{CHECK}\s*\(", src), (
        f"{fn_name}() mints a human grant without consulting {CHECK}(). A rule "
        f"enforced at one of two doors is not enforced — this is the 2026-09-21 "
        f"finding: the share door bypassed the free tier's 2-seat cap entirely."
    )


def test_no_door_reimplements_the_cap_inline():
    """The count must not be re-derived at a call site.

    `create_invite` held its own inline copy; that is precisely how the second
    door came to have none. A second inline copy would drift the same way.
    """
    offenders = []
    for fn_name, path in HUMAN_GRANT_DOORS.items():
        # CODE only — a comment naming the rule is documentation, not a second
        # implementation, and matching prose made this arm fail on its own
        # explanation. `ast` sees names; it cannot see a comment.
        names = _names_used(path, fn_name)
        if names & {"tier_included_seats", "HUMAN_SEAT_ROLES"}:
            offenders.append(fn_name)
    assert not offenders, (
        f"these doors re-derive the seat count inline instead of calling "
        f"{CHECK}(): {offenders}. One home, or they drift."
    )


def test_the_viewer_branch_is_not_capped():
    """A viewer redemption is not a billed seat, so it must not be refused.

    Guards an over-correction: capping the whole of `accept_share` would break
    read-only sharing, which ADR-517 D1 makes explicitly free.
    """
    src = _fn_source(SHARES, "accept_share")
    viewer_at = src.index('share_role == "viewer"')
    member_at = src.index('role="member"')
    check_at = src.index(CHECK)
    assert viewer_at < check_at, "the cap is applied before the viewer branch splits"
    assert check_at < member_at, "the cap does not guard the member mint"


# ---------------------------------------------------------------------------
# 3. The refusal is legible, and the accepted seat is billed
# ---------------------------------------------------------------------------

def test_both_doors_signal_upgrade_required_the_same_way():
    """One status code for one condition, so a client branches instead of parsing.

    The invite door already answered 402; the share route mapped no such code, so
    an identical refusal would have surfaced as a generic 400.
    """
    route = SHARE_ROUTE.read_text()
    accept = route[route.index("async def accept_workspace_share"):]
    accept = accept[: accept.index("\n@router") if "\n@router" in accept else len(accept)]
    assert '"upgrade_required": 402' in accept, (
        "the share-accept route does not map upgrade_required → 402; the same "
        "refusal answers 402 at the invite door and 400 here"
    )


def test_share_accept_syncs_the_seat_quantity():
    """An admitted human grows the bill. The invite door syncs; this one must too."""
    route = SHARE_ROUTE.read_text()
    accept = route[route.index("async def accept_workspace_share"):]
    accept = accept[: accept.index("\n@router") if "\n@router" in accept else len(accept)]
    assert "sync_seat_quantity" in accept, (
        "share-accept does not call sync_seat_quantity — a share join stays "
        "invisible to billing even once the cap admits it"
    )
    assert 'get("role") != "viewer"' in accept, (
        "share-accept syncs seats for a viewer redemption, which is not a seat"
    )


# ---------------------------------------------------------------------------

def _fn_source(path: Path, fn_name: str) -> str:
    """The source text of one function, so an arm cannot match a neighbour.

    (A whole-file grep is how a check in a DIFFERENT function reads as present —
    the blind-arm shape this repo has been bitten by twice.)
    """
    text = path.read_text()
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == fn_name:
            return ast.get_source_segment(text, node) or ""
    raise AssertionError(
        f"{fn_name}() not found in {path.name}. If it was renamed or moved, update "
        f"HUMAN_GRANT_DOORS — do not delete the assertion."
    )


def _names_used(path: Path, fn_name: str) -> set[str]:
    """Every identifier REFERENCED in a function body (never its comments)."""
    text = path.read_text()
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == fn_name:
            out: set[str] = set()
            for n in ast.walk(node):
                if isinstance(n, ast.Name):
                    out.add(n.id)
                elif isinstance(n, ast.Attribute):
                    out.add(n.attr)
                elif isinstance(n, ast.alias):
                    out.add(n.name.split(".")[-1])
            return out
    raise AssertionError(f"{fn_name}() not found in {path.name}")
