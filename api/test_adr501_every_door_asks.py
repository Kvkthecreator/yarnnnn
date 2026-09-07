"""ADR-501 S1 completion — EVERY door asks the grant, and the roster is DISCOVERED.

⭐⭐⭐ THE POINT OF THIS GATE IS THAT IT DOES NOT NAME THE DOORS.

ADR-501 wrote its own lesson down: *"a permission fix must enumerate the doors,
not the deciders."* It then enumerated TWO doors (`edit_workspace_file`,
`write_artifact`) and shipped, and `test_adr570_member_prose_door.py` ratchets
exactly those two BY NAME. Eight doors existed. Five of the six missed ones were
the destructive organize verbs, and they stayed unguarded for as long as the
ratchet has been green — because a hand-named roster cannot go red for a door
nobody added to it.

So this gate DISCOVERS the roster by walking the AST for handlers that mutate
the substrate, and asserts each one asks. Add a ninth mutating route without a
consult and this fails on a function it has never heard of. That is the whole
design; if you find yourself adding a name to a literal list here, the gate has
been defeated.

⚠️ `operator_can_organize` IS NOT AN AUTHORIZATION CHECK and never satisfies
this gate. It is a filesystem-INTEGRITY rule about path SHAPE, identical for
every principal, carving only `system/` + raw `inbound/` + `_*.yaml` leaves.
`constitution/` `persona/` `governance/` `contract/` all PASS it (ADR-320: those
are the operator's own to reorganize). The per-principal question has its own
decider — `_is_path_locked_for_principal`. A door owes BOTH.

A door satisfies this gate three ways:
  1. it calls `_is_path_locked_for_principal` itself, or
  2. it delegates to `execute_primitive` (the primitive path consults it for
     every verb in `_PATH_ADDRESSED_QUEUEABLE`), or
  3. it is named in `READ_ONLY_OR_DELEGATED` below WITH a reason — the only
     hand-maintained part, and each entry is an argued exemption, not a skip.

Run: cd api && python3 -m pytest test_adr501_every_door_asks.py -q
"""

import ast
from pathlib import Path

API = Path(__file__).parent

#: Modules serving HTTP routes that can mutate workspace substrate.
ROUTE_MODULES = ("routes/documents.py", "routes/workspace.py", "routes/studio.py")

#: Calls that MUTATE the substrate. A handler reaching any of these is a door.
MUTATING_CALLS = frozenset({
    "write_revision", "archive_live_file", "restore_live_file",
    "permanently_delete_file", "trash_folder", "restore_group",
    "move_folder", "_upsert_workspace_file",
})

#: The grant consult, and the two indirections that perform it on the caller's
#: behalf. `_assert_principal_may_organize` is documents.py's thin wrapper —
#: named here rather than inlined at seven call sites, so the 403 body is
#: written once. A gate that only accepted the raw call would push doors to
#: copy-paste the consult, which is the drift this whole file exists to stop.
CONSULT = "_is_path_locked_for_principal"
CONSULT_WRAPPERS = frozenset({"_assert_principal_may_organize"})
DELEGATE = "execute_primitive"

#: ARGUED exemptions. Each needs a reason a reviewer can check — never a skip
#: to make the gate pass. Keep this SHORT; an entry here is a claim that the
#: handler cannot mutate on behalf of a principal who might be locked.
READ_ONLY_OR_DELEGATED: dict[str, str] = {}


def _handlers(mod: str):
    """Every decorated route handler in `mod`, as (name, node)."""
    tree = ast.parse((API / mod).read_text())
    for n in ast.walk(tree):
        if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for d in n.decorator_list:
            f = d.func if isinstance(d, ast.Call) else d
            # @router.post / .delete / .patch / .put / .get
            if isinstance(f, ast.Attribute) and f.attr in {
                "post", "delete", "patch", "put", "get"
            }:
                yield n.name, n
                break


def _called_names(node) -> set[str]:
    out = set()
    for c in ast.walk(node):
        if isinstance(c, ast.Call):
            f = c.func
            if isinstance(f, ast.Name):
                out.add(f.id)
            elif isinstance(f, ast.Attribute):
                out.add(f.attr)
    return out


def _discover_doors() -> list[tuple[str, str, set[str]]]:
    doors = []
    for mod in ROUTE_MODULES:
        for name, node in _handlers(mod):
            calls = _called_names(node)
            if calls & MUTATING_CALLS:
                doors.append((mod, name, calls))
    return doors


def test_the_roster_is_not_empty():
    """A discovery gate that discovers nothing passes vacuously.

    (The ADR-641 lesson: a parity check is vacuous until the registry is
    loaded. Here the failure mode is a refactor that renames every mutating
    call, leaving this gate green over zero doors.)"""
    doors = _discover_doors()
    assert len(doors) >= 6, (
        f"only {len(doors)} mutating door(s) discovered — MUTATING_CALLS has "
        "probably drifted from the substrate's real write verbs, and this gate "
        "is now vacuous"
    )


def test_every_discovered_door_asks_the_grant():
    """THE RATCHET. Every mutating handler consults the principal, itself or by
    delegation. Nothing here is named in advance."""
    failures = []
    for mod, name, calls in _discover_doors():
        if CONSULT in calls or DELEGATE in calls or (calls & CONSULT_WRAPPERS):
            continue
        if name in READ_ONLY_OR_DELEGATED:
            continue
        mutators = sorted(calls & MUTATING_CALLS)
        failures.append(f"  {mod}::{name} mutates via {mutators} without {CONSULT}")
    assert not failures, (
        "these doors mutate substrate without asking the caller's grant:\n"
        + "\n".join(failures)
        + "\n\n`operator_can_organize` does NOT count: it is a path-shape rule "
        "identical for every principal, and constitution/ persona/ governance/ "
        "contract/ all pass it. Add `_assert_principal_may_organize(auth, path)` "
        "(routes/documents.py) or delegate to execute_primitive."
    )


def test_carve_law_is_not_mistaken_for_authorization():
    """The two questions are different, and the difference is the whole bug.

    Executed, not grepped: a principal whose grant resolves to the `agent`
    class is locked from writing these roots, while the carve law admits every
    one of them."""
    from types import SimpleNamespace
    from unittest.mock import patch

    from services.primitives import workspace as wsp
    from services.workspace_paths import operator_can_organize

    auth = SimpleNamespace(
        user_id="u1", principal_id="u1", workspace_id="w1",
        caller_identity="operator", freddie_caller=False, client=None,
    )
    roots = (
        "/workspace/constitution/MANDATE.md",
        "/workspace/persona/IDENTITY.md",
        "/workspace/governance/AUTONOMY.md",
    )
    with patch.object(
        wsp, "_lookup_grant_axes",
        lambda a: {"read": None, "write": None, "role": "member"},
    ):
        for p in roots:
            assert operator_can_organize(p), (
                f"{p} newly fails the carve law — if that is deliberate this "
                "test's premise moved, but check ADR-320 first: these are the "
                "operator's own to reorganize"
            )
            assert wsp._is_path_locked_for_principal(auth, p), (
                f"a member is no longer locked from {p} — CALLER_WRITE_POLICY "
                "or the role table changed"
            )


def test_the_destructive_verbs_specifically():
    """The five that were live-unguarded, pinned by NAME as well.

    The discovery test above is the durable half; this one names them so a
    revert reads as a revert of THIS work rather than as a generic roster
    drift. It is the only place in this file where a door is named."""
    tree = ast.parse((API / "routes" / "documents.py").read_text())
    want = {
        "delete_document", "restore_document", "permanent_delete_document",
        "empty_trash", "trash_folder_route",
    }
    seen = {}
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in want:
            calls = _called_names(n)
            seen[n.name] = (
                CONSULT in calls or "_assert_principal_may_organize" in calls
            )
    missing = sorted(want - set(seen))
    assert not missing, f"handler(s) vanished or renamed: {missing}"
    ungated = sorted(k for k, v in seen.items() if not v)
    assert not ungated, (
        f"{ungated} no longer consult the principal — this is the ADR-501 S1 "
        "hole reopening: a principal who may not WRITE a file could DESTROY it"
    )
