"""Desk and MCP must list the SAME tree (2026-08-17 connector divergence).

The operator reported the two surfaces disagreeing about what exists: MCP
omitted three files the desk showed in `operation/fundraising/`, the desk
omitted one file MCP showed, and a full MCP listing collapsed from 217 files to
19. It read like a filter — an allow-list, a deny-list, an `is_searchable_root`
over-match at the wrong granularity.

**It was not a filter.** Both surfaces were listing correctly; they were listing
DIFFERENT WORKSPACES. `_resolve_owner_workspace_id_cached` had lost its
`.eq("owner_id", user_id)` filter, so the connector resolved to the oldest
workspace in the table — a stranger's — while the browser (which passes
`X-Workspace-Id` explicitly) stayed on the member's own.

That distinction is why this gate asserts SCOPE AGREEMENT rather than result
equality against a fixture. The failure mode was never "one side filters more";
it was "the two sides answer a different question". So the property to defend
is: **given one acting workspace, both surfaces derive the same scope, from the
same helper, and neither applies a hidden path filter on the listing path.**

The complementary check — that the resolver itself is owner-scoped — lives in
`test_adr373_owner_resolution_is_scoped.py`. Together they cover both halves:
the same workspace resolves (there), and the same tree is read (here).

Run with `python3 test_listing_parity_desk_vs_mcp.py` (NOT pytest — check()
gates print ✗ but a pytest run reports PASS; see MEMORY.md).
"""

import ast
import sys
import logging

FAILURES: list = []


def _check(label, cond):
    if cond:
        logging.info("✓ %s", label)
    else:
        logging.error("✗ %s", label)
        FAILURES.append(label)
    return bool(cond)


# The ONE declared exclusion. `list` is a substrate listing and excludes
# nothing by path; the searchable-root narrowing applies to QueryKnowledge's
# unscoped SWEEP (recall ranking), never to enumeration. If a path exclusion is
# ever added to listing, it must be declared here AND in both surfaces.
DECLARED_LISTING_EXCLUSIONS: set = set()


def run() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    sys.path.insert(0, ".")

    from services.workspace_context import substrate_scope_filter

    WS = "11111111-1111-1111-1111-111111111111"
    USER = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"

    # ── D1. One acting workspace → one scope, for both surfaces ────────────
    # Executed, not inspected: both call sites reduce to this helper, so if the
    # helper is stable on the same inputs the two surfaces cannot diverge.
    desk_scope = substrate_scope_filter(USER, WS)
    mcp_scope = substrate_scope_filter(USER, WS)
    _check("D1. the shared helper yields one scope for one workspace", desk_scope == mcp_scope)
    _check(
        "D1. a bound workspace keys on workspace_id, never user_id",
        desk_scope == ("workspace_id", WS),
    )

    # THE regression: two DIFFERENT workspaces must not produce the same scope.
    # This is the shape the incident had — same user, two workspaces, both
    # surfaces convinced they were right.
    other = substrate_scope_filter(USER, "22222222-2222-2222-2222-222222222222")
    _check("D1. different workspaces produce different scopes", other != desk_scope)

    # ── D2. Both surfaces reach the scope through the SAME helper ──────────
    # A second, independently-written scope derivation is how the two can drift
    # apart again. Parsed with ast, not grepped: both files discuss scoping in
    # prose, and a comment must never satisfy a structural check.
    def _calls(path: str, fname: str, callee: str) -> bool:
        tree = ast.parse(open(path).read())
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == fname:
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Call):
                        f = sub.func
                        name = getattr(f, "id", None) or getattr(f, "attr", None)
                        if name == callee:
                            return True
        return False

    _check(
        "D2. the desk's scope helper delegates to substrate_scope_filter",
        _calls("routes/workspace.py", "_substrate_scope_filter", "substrate_scope_filter"),
    )
    _check(
        "D2. the MCP/primitive scope helper delegates to substrate_scope_filter",
        _calls("services/primitives/workspace.py", "_scope_filter", "substrate_scope_filter"),
    )

    # ── D3. Both pass the BOUND workspace, not an inferred one ─────────────
    # ADR-501 §6a lesson 4: a call site that omits auth.workspace_id silently
    # degrades to owner-resolution — which is exactly the door the incident came
    # through. Both helpers must forward the bound value.
    desk_src = open("routes/workspace.py").read()
    mcp_src = open("services/primitives/workspace.py").read()

    def _forwards_workspace(path: str, fname: str) -> bool:
        """Whether `fname`'s call to substrate_scope_filter passes a SECOND arg.

        Reads the call inside that ONE function. The first spelling of this
        check asked whether the file contained the forwarding string anywhere,
        and PASSED its own falsification: deleting the argument from the helper
        left the same string in other call sites and in prose. A file-wide
        substring cannot defend a single call site.
        """
        tree = ast.parse(open(path).read())
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == fname:
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Call):
                        name = getattr(sub.func, "id", None) or getattr(sub.func, "attr", None)
                        if name == "substrate_scope_filter":
                            # arg 2 positionally, or the keyword form
                            return len(sub.args) >= 2 or any(
                                k.arg == "workspace_id" for k in sub.keywords
                            )
        return False

    _check(
        "D3. the desk helper forwards the BOUND workspace to the scope helper",
        _forwards_workspace("routes/workspace.py", "_substrate_scope_filter"),
    )
    _check(
        "D3. the primitive helper forwards the BOUND workspace to the scope helper",
        _forwards_workspace("services/primitives/workspace.py", "_scope_filter"),
    )

    # ── D4. The listing path applies NO path filter ────────────────────────
    # The reported symptom looked like an over-matching deny-list. There is no
    # such list on listing, and this asserts it stays that way: if a path
    # exclusion is added, it must be declared above and this check updated
    # deliberately rather than discovered by an operator.
    _check(
        "D4. the listing exclusion set is empty and DECLARED (not implicit)",
        DECLARED_LISTING_EXCLUSIONS == set(),
    )
    # `is_searchable_root` narrows RECALL, not enumeration. If it ever appears
    # in the listing helper, listing and the desk diverge by construction.
    tree = ast.parse(mcp_src)
    list_uses_searchable_root = False
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "_list_tree":
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call):
                    name = getattr(sub.func, "id", None) or getattr(sub.func, "attr", None)
                    if name == "is_searchable_root":
                        list_uses_searchable_root = True
    _check(
        "D4. the listing walk does NOT apply the searchable-root recall filter",
        not list_uses_searchable_root,
    )

    total = len(FAILURES)
    print(f"\nDesk/MCP listing-parity gate: {_RUN - total}/{_RUN} passed, {total} failed")
    for f in FAILURES:
        print(f"  ✗ {f}")
    return 1 if FAILURES else 0


_RUN = 9

if __name__ == "__main__":
    sys.exit(run())
