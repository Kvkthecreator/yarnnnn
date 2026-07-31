"""Every GOVERNANCE verb is owner-gated, per-site (2026-07-31).

Guards the finding at docs/evaluations/findings/2026-07-31-member-can-widen-own-grant.md:
`POST /workspace/members/{id}/narrow` and `.../revoke` resolved the caller's
workspace with the bare `_resolve_caller_workspace`, which answers "which
workspace is this caller in" and NEVER "may this caller govern it". A member
called /narrow against their OWN principal_id and added `governance/` to their
own write_scopes; production returned 200 and the grant row changed.

WHY THIS SHAPE. A counting gate ("N routes call the owner helper") cannot defend
a per-site invariant: it passes when a new route is added unguarded as long as
some other route gains a call. So this ENUMERATES the governance verbs by route
path and asserts per-site, plus a completeness assert that fails when a new
`/workspace/members/*` mutating route appears without a verdict here.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

ROUTES = Path(__file__).parent / "routes" / "workspace.py"

#: Mutating member-lifecycle routes that MUST be owner-gated. Keyed by the route
#: path suffix as written in the decorator.
GOVERNANCE_VERBS = {
    "/workspace/members/invite",
    "/workspace/members/{principal_id}/narrow",
    "/workspace/members/{principal_id}/revoke",
    "/workspace/members/{principal_id}/cap",       # per-member spend cap
    "/workspace/invites/{invite_id}/revoke",
}

#: Mutating member routes deliberately NOT owner-gated, each with a reason.
#: A route may only sit here with an explicit justification.
NON_GOVERNANCE_EXEMPT = {
    # The invitee accepts their OWN invite; requiring owner would make invites
    # unusable. Authority is the invite token + email binding, not the grant.
    "/workspace/invites/accept",
}

OWNER_HELPER = "_require_owner_workspace"
UNGUARDED_HELPER = "_resolve_caller_workspace"


def _module() -> ast.Module:
    return ast.parse(ROUTES.read_text())


def _route_functions() -> dict[str, ast.AsyncFunctionDef | ast.FunctionDef]:
    """Map decorator route-path -> the handler function node."""
    out: dict[str, ast.AsyncFunctionDef | ast.FunctionDef] = {}
    for node in ast.walk(_module()):
        if not isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
            continue
        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call):
                continue
            func = dec.func
            if not (isinstance(func, ast.Attribute) and func.attr in {"post", "put", "patch", "delete"}):
                continue
            if not dec.args or not isinstance(dec.args[0], ast.Constant):
                continue
            out[dec.args[0].value] = node
    return out


def _calls_in(fn) -> set[str]:
    names = set()
    for node in ast.walk(fn):
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name):
                names.add(f.id)
            elif isinstance(f, ast.Attribute):
                names.add(f.attr)
    return names


@pytest.mark.parametrize("route", sorted(GOVERNANCE_VERBS))
def test_governance_verb_is_owner_gated(route: str) -> None:
    """PER-SITE: each governance verb calls the owner helper, not the bare one."""
    fns = _route_functions()
    assert route in fns, (
        f"{route} is no longer a mutating route in workspace.py. If it moved or "
        f"was renamed, update GOVERNANCE_VERBS — do not delete the assertion."
    )
    called = _calls_in(fns[route])
    assert OWNER_HELPER in called, (
        f"{route} does not call {OWNER_HELPER}(). Membership is not authority: "
        f"{UNGUARDED_HELPER}() answers 'which workspace' and never 'may this "
        f"caller govern it'. This is the 2026-07-31 escalation."
    )


def test_no_governance_verb_relies_on_the_bare_resolver_alone() -> None:
    """A verb that calls BOTH is fine (the helper wraps it); calling only the
    bare resolver is the defect shape."""
    fns = _route_functions()
    offenders = []
    for route in sorted(GOVERNANCE_VERBS):
        if route not in fns:
            continue
        called = _calls_in(fns[route])
        if UNGUARDED_HELPER in called and OWNER_HELPER not in called:
            offenders.append(route)
    assert not offenders, f"governance verbs gated only by membership: {offenders}"


def test_member_mutating_routes_are_all_accounted_for() -> None:
    """COMPLETENESS: a NEW mutating /workspace/members/* route must be classified
    as governance (owner-gated) or explicitly exempted. Without this, adding an
    unguarded route beside the fixed ones would ship green."""
    fns = _route_functions()
    member_routes = {
        r for r in fns
        if re.match(r"^/workspace/(members|invites)/", r)
    }
    unclassified = member_routes - GOVERNANCE_VERBS - NON_GOVERNANCE_EXEMPT
    assert not unclassified, (
        f"unclassified mutating member routes: {sorted(unclassified)}. Add each "
        f"to GOVERNANCE_VERBS (and owner-gate it) or to NON_GOVERNANCE_EXEMPT "
        f"with a written reason."
    )


def test_narrow_cannot_widen() -> None:
    """`narrow_grant` enforces the subset invariant its name promises.

    Defense in depth behind the owner gate: an owner-only verb that can still
    widen is a footgun, and NULL polarity makes the mistake easy (NULL is the
    class DEFAULT, a non-empty reachable set — not 'nothing')."""
    src = (Path(__file__).parent / "services" / "principal_grants.py").read_text()
    assert "class ScopeEscalation" in src, "the widen-refusal exception is gone"
    assert "class_default_write_regions" in src, (
        "the subset check must resolve NULL against the CLASS DEFAULT, else a "
        "NULL -> ['governance/'] transition reads as narrowing from nothing."
    )
    tree = ast.parse(src)
    fn = next(
        (n for n in ast.walk(tree)
         if isinstance(n, ast.FunctionDef) and n.name == "narrow_grant"),
        None,
    )
    assert fn is not None, "narrow_grant not found"
    raises = {
        n.exc.func.id
        for n in ast.walk(fn)
        if isinstance(n, ast.Raise) and isinstance(n.exc, ast.Call)
        and isinstance(n.exc.func, ast.Name)
    }
    assert "ScopeEscalation" in raises, (
        "narrow_grant no longer raises ScopeEscalation — it can widen again."
    )
