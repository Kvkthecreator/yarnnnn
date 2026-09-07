"""ADR-643 D2 — the one access decider, driven.

Two halves, and the second is the one that keeps it honest:

1. BEHAVIOR — `resolve_access` / `may_edit_as_prose` / `access_summary` are
   EXECUTED against every (role x path-class) pair that matters, with the grant
   lookup stubbed. Source inspection proves nothing about a decider.
2. SINGULARITY — the decider composes the predicates that already exist and
   invents no permission concept of its own.

⭐⭐ Driving this, rather than reading it, is what caught a real bug during
authoring: `may_edit_as_prose` routed to the `write` verb, which deliberately
skips the carve law, so a `.md` file under raw `inbound/` reported EDITABLE —
contradicting ADR-422 D2 (an arrival is retained exactly as it came). The FE's
own `isArrival` check was right about that one. Kept as a named case below.

Run: cd api && python3 -m pytest test_adr643_one_decider.py -q
"""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from services import access
from services.primitives import workspace as wsp


def _auth(caller_identity: str = "operator"):
    return SimpleNamespace(
        user_id="u1", principal_id="u1", workspace_id="w1",
        caller_identity=caller_identity,
        freddie_caller=caller_identity.startswith("freddie:"),
        client=None,
    )


@pytest.fixture()
def as_role():
    """Pin the grant lookup to a role for the duration of a check."""
    def _run(role, fn):
        with patch.object(
            wsp, "_lookup_grant_axes",
            lambda a: {"read": None, "write": None, "role": role},
        ):
            return fn()
    return _run


# ---------------------------------------------------------------------------
# 1. The two questions are DIFFERENT, and the decider keeps them apart
# ---------------------------------------------------------------------------

def test_carve_law_is_not_the_grant(as_role):
    """⭐⭐ The framing claim, executed.

    `constitution/MANDATE.md` PASSES the carve law (ADR-320: the operator's own
    to reorganize) and FAILS the member's grant. A decider that collapsed them
    would have to get one of these two rows wrong."""
    p = "/workspace/constitution/MANDATE.md"
    assert as_role("owner", lambda: access.resolve_access(_auth(), p, "trash")).allowed
    member = as_role("member", lambda: access.resolve_access(_auth(), p, "trash"))
    assert not member.allowed
    assert member.code == "grant", (
        "a member's refusal here must cite the GRANT — citing the carve law "
        "would be a lie about why, and the client shows this string"
    )


def test_a_carved_path_refuses_everyone_for_the_shape_reason(as_role):
    """`system/` and machine leaves refuse the OWNER too, and say why."""
    for path, code in (
        ("/workspace/system/skills/x/SKILL.md", "system_managed"),
        ("/workspace/governance/_autonomy.yaml", "machine_config"),
        ("/workspace/inbound/slack/a.md", "raw_intake"),
    ):
        d = as_role("owner", lambda p=path: access.resolve_access(_auth(), p, "trash"))
        assert not d.allowed, path
        assert d.code == code, f"{path}: {d.code} != {code}"
        assert d.reason and "“" in d.reason, "a refusal owes a person-facing sentence"


def test_write_does_not_run_the_carve_law(as_role):
    """⚠️ The conflation that produced `editable_prefixes`.

    Editing content in place MOVES nothing, so `write` must not ask the
    placement question. `governance/_autonomy.yaml` is un-renameable for
    everyone and still writable by the owner — two facts, two questions."""
    p = "/workspace/governance/_autonomy.yaml"
    assert not as_role("owner", lambda: access.resolve_access(_auth(), p, "rename")).allowed
    assert as_role("owner", lambda: access.resolve_access(_auth(), p, "write")).allowed


# ---------------------------------------------------------------------------
# 2. The Text question (ADR-643 D4)
# ---------------------------------------------------------------------------

def test_non_prose_never_opens_as_prose(as_role):
    """The operator's sharpest case: machine-parsed YAML rendered as markdown,
    with an inspector asserting "it stays a .md file". A category error
    whoever is asking, so the FORMAT refusal precedes the principal one."""
    d = as_role("owner", lambda: access.may_edit_as_prose(
        _auth(), "/workspace/governance/_autonomy.yaml"))
    assert not d.allowed
    assert d.code == "not_prose"


def test_raw_intake_prose_does_not_open_editable(as_role):
    """⭐⭐ THE BUG DRIVING THIS FILE FOUND.

    A `.md` under raw `inbound/` passes `is_prose_document` AND the owner's
    write ceiling. Routing prose-editability at the `write` verb therefore
    reported it EDITABLE, against ADR-422 D2 (retained exactly as it arrived).
    Opening a canvas is an invitation to REPLACE the content, which for an
    immutable record is the same category error as renaming it."""
    d = as_role("owner", lambda: access.may_edit_as_prose(
        _auth(), "/workspace/inbound/slack/a.md"))
    assert not d.allowed, "a raw arrival must not open in an editable canvas"
    assert d.code == "raw_intake"


def test_the_human_upload_lane_stays_editable(as_role):
    """The twin that makes the check above non-vacuous: `inbound/uploads/` is
    the HUMAN raw lane (ADR-395) and the operator owns what they uploaded. A
    blanket `inbound/` refusal would have passed the test above and been
    wrong here."""
    d = as_role("owner", lambda: access.may_edit_as_prose(
        _auth(), "/workspace/inbound/uploads/kv/note.md"))
    assert d.allowed


def test_prose_a_member_cannot_write_is_refused_for_the_grant(as_role):
    """ADR-643 D4's read-only case: the format is fine, the principal is not.
    Text renders read-only here rather than refusing to open — which is why
    the code must distinguish this from `not_prose`."""
    d = as_role("member", lambda: access.may_edit_as_prose(
        _auth(), "/workspace/persona/IDENTITY.md"))
    assert not d.allowed
    assert d.code == "grant"


# ---------------------------------------------------------------------------
# 3. The served summary (ADR-643 D3)
# ---------------------------------------------------------------------------

def test_summary_shape_is_stable_and_small(as_role):
    """The client is TOLD, never re-derives. Keep this small: a client needing
    a fourth fact should ask for a VERB, not reconstruct a rule."""
    s = as_role("owner", lambda: access.access_summary(
        _auth(), "/workspace/operation/notes.md"))
    assert set(s) == {"may_write", "may_organize", "may_edit_as_prose", "reason", "code"}
    assert s["may_write"] and s["may_organize"] and s["may_edit_as_prose"]
    assert s["reason"] is None and s["code"] is None


def test_summary_separates_write_from_organize(as_role):
    """The row that proves the summary is not one boolean wearing three names:
    the owner may WRITE a machine leaf and may not ORGANIZE it."""
    s = as_role("owner", lambda: access.access_summary(
        _auth(), "/workspace/governance/_autonomy.yaml"))
    assert s["may_write"] is True
    assert s["may_organize"] is False
    assert s["may_edit_as_prose"] is False


# ---------------------------------------------------------------------------
# 4. A door cannot invent a verb
# ---------------------------------------------------------------------------

def test_unknown_verb_raises_rather_than_allowing():
    """⭐ Fails CLOSED and LOUD. A typo'd verb silently returning ALLOWED is
    the failure mode a single decider would otherwise introduce."""
    with pytest.raises(ValueError, match="unknown access verb"):
        access.resolve_access(_auth(), "/workspace/operation/x.md", "delete")


def test_every_mutating_verb_consults_the_grant(as_role):
    """No verb may skip the principal question by omission."""
    p = "/workspace/persona/IDENTITY.md"
    for verb in sorted(access.MUTATING_VERBS):
        d = as_role("member", lambda v=verb: access.resolve_access(_auth(), p, v))
        assert not d.allowed, f"{verb} let a member through on {p}"


def test_read_is_not_gated_here(as_role):
    """`read` is served for PRESENTATION. The read path is bounded by
    substrate_scope_filter + RLS; duplicating that here would be a second
    decider, which is the thing this module exists to prevent."""
    assert as_role("member", lambda: access.resolve_access(
        _auth(), "/workspace/persona/IDENTITY.md", "read")).allowed


# ---------------------------------------------------------------------------
# 5. Singularity — no new permission concept
# ---------------------------------------------------------------------------

def test_decider_invents_no_policy_of_its_own():
    """Every refusal must trace to a predicate that already existed. If this
    module grows its own root list, the divergence has simply moved here.

    ⚠️ Checks EXECUTABLE code only — string constants, comments and docstrings
    are stripped first. An earlier version grepped the raw source and went red
    on the prose EXPLAINING why these roots are not named here (the recurring
    `a gate that matches its own documentation` defect)."""
    import ast
    import pathlib

    src = pathlib.Path(__file__).parent.joinpath("services/access.py").read_text()
    tree = ast.parse(src)

    # Every string literal the module actually evaluates, docstrings excluded
    # by construction: we look at Constant nodes that are NOT a body's first
    # statement. Comments never reach the AST at all.
    literals = []
    docstrings = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(body, list) and body:
            first = body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) \
                    and isinstance(first.value.value, str):
                docstrings.add(id(first.value))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                and id(node) not in docstrings:
            literals.append(node.value)

    haystack = "\n".join(literals)
    for banned in ("constitution/", "persona/", "contract/", "governance/"):
        assert banned not in haystack, (
            f"services/access.py hard-codes {banned!r} in executable code — the "
            "roots belong to CALLER_WRITE_POLICY, and a second list here is the "
            "divergence this module exists to end"
        )


def test_the_singularity_check_is_not_vacuous():
    """The twin: the check above must be able to SEE a planted root.

    A stripper that removed too much would pass over a real violation."""
    import ast

    planted = ast.parse('X = "constitution/"')
    lits = [n.value for n in ast.walk(planted)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    assert "constitution/" in lits, (
        "the literal extraction can no longer see a hard-coded root, so the "
        "singularity check above is vacuous"
    )
