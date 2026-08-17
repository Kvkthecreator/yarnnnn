"""ADR-573 — the connector is bound to a workspace at consent.

ADR-373 D6 made the connector resolve the SAME workspace the member's own
default resolves to. It explicitly left SELECTION open: a connector could not
NAME a workspace, so a principal who reaches more than one took their default
and could not reach the others AT ALL.

That was live. A production principal owns "My Workspace" and holds an active
member grant into the shared "yarnnn workspace"; all three of their connector
writes landed in the owner workspace, and the commons — the workspace the
membership exists for — was unreachable from the connector.

This gate runs the REAL resolver against a stubbed reach oracle. The rules it
defends:

  1. A token's bound workspace is honored (the selection actually works).
  2. Reach is RE-CHECKED per request — a stamped workspace narrows, never
     grants. A member revoked after the token was minted loses it immediately.
  3. NULL binding → the principal's default, byte-identical to ADR-373 D6.
     This is what every one of the 421 live pre-573 tokens carries, and why
     this ships with no backfill.
  4. The binding survives refresh ROTATION — the path that keeps live
     connectors alive, and so the path where silently dropping it would
     un-bind every connector without anyone acting.

Run with `/tmp/mcpenv/bin/python3.11 test_adr573_connector_workspace_binding.py`
(the mcp_server package needs py3.11; NOT pytest — check() gates print ✗ but a
pytest run reports PASS. See MEMORY.md).
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


OWNER_WS = "11111111-1111-1111-1111-111111111111"
COMMONS_WS = "22222222-2222-2222-2222-222222222222"
STRANGER_WS = "33333333-3333-3333-3333-333333333333"
USER = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


def run() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    sys.path.insert(0, ".")

    import services.supabase as sb
    import mcp_server.auth as auth

    # Stub the reach oracle: this principal OWNS OWNER_WS and holds a grant
    # into COMMONS_WS. STRANGER_WS is reachable by neither. Mirrors the real
    # `resolve_workspace_for_principal` contract exactly (ADR-373): a requested
    # id is returned iff reachable, else None; no request → the default.
    reachable = {OWNER_WS, COMMONS_WS}
    calls = {"n": 0}

    def fake_resolve(user_id, requested_workspace_id=None):
        calls["n"] += 1
        if requested_workspace_id:
            return requested_workspace_id if requested_workspace_id in reachable else None
        return OWNER_WS

    original = sb.resolve_workspace_for_principal
    sb.resolve_workspace_for_principal = fake_resolve
    try:
        # ── D1. Selection works ─────────────────────────────────────────────
        _check(
            "D1. a token bound to the COMMONS resolves the commons, not the default",
            auth.resolve_mcp_workspace(USER, COMMONS_WS) == COMMONS_WS,
        )
        _check(
            "D1. this is the case that was previously IMPOSSIBLE (default != commons)",
            auth.resolve_mcp_workspace(USER, None) == OWNER_WS
            and OWNER_WS != COMMONS_WS,
        )

        # ── D2. Reach is re-checked; a stamp narrows, never grants ──────────
        _check(
            "D2. an UNREACHABLE bound workspace is never returned",
            auth.resolve_mcp_workspace(USER, STRANGER_WS) != STRANGER_WS,
        )
        _check(
            "D2. it degrades to the principal's default, not an error",
            auth.resolve_mcp_workspace(USER, STRANGER_WS) == OWNER_WS,
        )
        # The revocation case: the token was minted while the grant was live.
        reachable.discard(COMMONS_WS)
        _check(
            "D2. a grant revoked AFTER the token was minted loses reach at once",
            auth.resolve_mcp_workspace(USER, COMMONS_WS) == OWNER_WS,
        )
        reachable.add(COMMONS_WS)

        # ── D3. NULL binding is exactly ADR-373 D6 ──────────────────────────
        _check(
            "D3. no binding → the principal's default (every pre-573 token)",
            auth.resolve_mcp_workspace(USER, None) == OWNER_WS,
        )
        _check(
            "D3. the parameter is OPTIONAL — the D6 call shape still works",
            auth.resolve_mcp_workspace(USER) == OWNER_WS,
        )

        # ── D4. Resolution never raises ─────────────────────────────────────
        def boom(*a, **k):
            raise RuntimeError("db down")

        sb.resolve_workspace_for_principal = boom
        _check(
            "D4. a resolution failure degrades to None, never raises",
            auth.resolve_mcp_workspace(USER, COMMONS_WS) is None,
        )
    finally:
        sb.resolve_workspace_for_principal = original

    # ── D5. The binding is PERSISTED at every hop ───────────────────────────
    # A token that resolves correctly but is never stored is a connection that
    # forgets its workspace on the next refresh.
    prov = open("mcp_server/oauth_provider.py").read()
    tree = ast.parse(prov)

    def _writes_workspace(fn_name: str) -> bool:
        """Whether `fn_name` puts workspace_id into a dict it builds.

        Parsed, not grepped: the file mentions workspace_id in prose, and a
        comment must never satisfy a check about behaviour.
        """
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == fn_name:
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Dict):
                        for k in sub.keys:
                            if isinstance(k, ast.Constant) and k.value == "workspace_id":
                                return True
        return False

    _check(
        "D5. exchange_authorization_code persists the binding onto the tokens",
        _writes_workspace("exchange_authorization_code"),
    )
    _check(
        "D5. exchange_refresh_token PRESERVES it across rotation (the live path)",
        _writes_workspace("exchange_refresh_token"),
    )

    def _reads_workspace(fn_name: str) -> bool:
        """Whether `fn_name` passes workspace_id as a keyword to a call."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == fn_name:
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Call):
                        for kw in sub.keywords:
                            if kw.arg == "workspace_id":
                                return True
        return False

    _check(
        "D5. load_access_token surfaces it so the runtime can read it",
        _reads_workspace("load_access_token"),
    )
    _check(
        "D5. load_refresh_token surfaces it so rotation can carry it",
        _reads_workspace("load_refresh_token"),
    )

    # ── D6. The request path actually READS the token's binding ─────────────
    auth_src = open("mcp_server/auth.py").read()
    atree = ast.parse(auth_src)
    passes_binding = False
    inits_before_try = False
    for node in ast.walk(atree):
        if isinstance(node, ast.FunctionDef) and node.name == "resolve_request_client":
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call):
                    for kw in sub.keywords:
                        if kw.arg == "bound_workspace_id":
                            passes_binding = True
            # The stdio/static-bearer path takes the EXCEPT branch, so a name
            # bound only inside the try raises UnboundLocalError instead of
            # degrading. Assert it is initialized at function-body level.
            for stmt in node.body:
                if isinstance(stmt, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == "bound_workspace_id"
                    for t in stmt.targets
                ):
                    inits_before_try = True
    _check("D6. resolve_request_client passes the token's binding through", passes_binding)
    _check(
        "D6. bound_workspace_id is initialized OUTSIDE the try (stdio path)",
        inits_before_try,
    )

    # ── D7. The consent door validates reach, fail-closed ───────────────────
    route = open("routes/mcp.py").read()
    _check(
        "D7. the bind door checks reach before stamping",
        "principal_reaches_workspace" in route,
    )
    _check(
        "D7. an unreachable workspace is REFUSED (403), not silently defaulted",
        "status_code=403" in route,
    )

    # ── D8. Migration is additive + nullable (no live connector repointed) ──
    mig = open("../supabase/migrations/238_adr573_connector_names_its_workspace.sql").read()
    _check(
        "D8. all three oauth tables gain the column",
        all(
            f"ALTER TABLE {t}" in mig
            for t in ("mcp_oauth_codes", "mcp_oauth_access_tokens", "mcp_oauth_refresh_tokens")
        ),
    )
    _check(
        "D8. the migration adds NO NOT NULL and NO backfill (pre-573 stays default)",
        "NOT NULL" not in mig.upper().replace("IS NOT NULL", "") and "UPDATE " not in mig.upper(),
    )

    total = len(FAILURES)
    print(f"\nADR-573 connector workspace-binding gate: {_RUN - total}/{_RUN} passed, {total} failed")
    for f in FAILURES:
        print(f"  ✗ {f}")
    return 1 if FAILURES else 0


_RUN = 18

if __name__ == "__main__":
    sys.exit(run())
