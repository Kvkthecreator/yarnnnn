"""ADR-563 (consent half) — the connect screen names WHO, WHERE and WHAT.

ADR-563 made the MCP scope tiers real: `assert_scope` refuses a verb the token
does not carry. But the operator approving the connection was never shown them.
The screen printed a FIXED sentence — "read and write your memory" — which was
wrong twice over: 'memory' is pre-ADR-512 vocabulary (the unit of interop is the
FILE), and a legacy `read` token can also DELETE files and mint share links that
grant MEMBER access. The label was decorative at the consent surface even after
the enforcement became real.

It also never said which ACCOUNT the bind would use (it comes from the JWT — on
a shared browser that is the difference between approving as yourself and as
someone else), nor which WORKSPACE the connector would reach (ADR-373 D6).

This gate asserts the disclosure exists and is DERIVED from the same table the
gate enforces — not that any particular sentence is spelled a particular way.
Pinning copy would test prettier, not the affordance (the ADR-572 lesson).

Run with `python3 test_adr563_consent_discloses.py` (NOT pytest — check() gates
print ✗ but a pytest run reports PASS; see MEMORY.md).
"""

import ast
import re
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


def run() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

    # The vocabulary module is pure data + stdlib — import it for REAL and call
    # it, rather than asserting over its source. A gate that greps cannot tell a
    # live branch from a comment.
    sys.path.insert(0, ".")
    from services.mcp_scopes import (
        SCOPE_READ,
        SCOPE_WRITE,
        SCOPE_SHARE,
        SCOPE_LEGACY_FULL,
        normalize_scopes,
        describe_scopes,
        is_legacy_full,
    )

    route_src = open("routes/mcp.py").read()
    fe_src = open("../web/app/mcp/authorize/page.tsx").read()
    client_src = open("../web/lib/api/client.ts").read()

    # ── D1. One definition, two services ────────────────────────────────────
    # The API cannot import mcp_server.auth (py3.9 venv + py3.11-only mcp SDK),
    # so a copy in the route is the obvious wrong turn. Assert the SHARED home
    # is the one both read.
    auth_src = open("mcp_server/auth.py").read()
    _check(
        "D1. mcp_server.auth imports the tiers (does not redefine them)",
        "from services.mcp_scopes import" in auth_src
        and 'SCOPE_READ = "files:read"' not in auth_src,
    )
    _check(
        "D1. the consent route reads the SAME shared vocabulary",
        "services.mcp_scopes" in route_src,
    )

    # ── D2. The sentences are DERIVED from the tiers, and nest ──────────────
    read_only = describe_scopes([SCOPE_READ])
    write = describe_scopes([SCOPE_WRITE])
    share = describe_scopes([SCOPE_SHARE])
    legacy = describe_scopes([SCOPE_LEGACY_FULL])

    _check(
        "D2. a read-only token discloses strictly less than a write token",
        len(read_only) < len(write) < len(share),
    )
    _check(
        "D2. the tiers are additive in the COPY too (write implies the read line)",
        all(s in write for s in read_only) and all(s in share for s in write),
    )
    _check(
        "D2. the LEGACY grant discloses the full set (it authorizes everything)",
        set(legacy) == set(share) and len(legacy) == 3,
    )
    _check(
        "D2. legacy full access is FLAGGED as such, narrow scopes are not",
        is_legacy_full([SCOPE_LEGACY_FULL])
        and not is_legacy_full([SCOPE_READ])
        and not is_legacy_full([SCOPE_WRITE]),
    )

    # The two capabilities the old copy hid entirely. Asserted by MEANING (the
    # sentence set must mention deletion and share-links somewhere), never by
    # pinning an exact string.
    blob = " ".join(legacy).lower()
    _check(
        "D2. deletion is disclosed (the old copy never mentioned it)",
        "delete" in blob,
    )
    _check(
        "D2. share-links and the member access they grant are disclosed",
        "share" in blob and "member" in blob,
    )

    # ── D3. An absent/empty scope string is the LEGACY grant, not the floor ──
    # The column default is 'read'. Displaying the safe floor for a token that
    # will actually carry full access would be the same lie in a new place.
    _check(
        "D3. an empty scope string describes LEGACY full access, not the floor",
        normalize_scopes(None) == [SCOPE_LEGACY_FULL]
        and normalize_scopes("") == [SCOPE_LEGACY_FULL],
    )

    # An unknown scope must not invent a permission sentence.
    _check(
        "D3. an unrecognized scope yields NO invented sentence",
        describe_scopes(["files:teleport"]) == [],
    )

    # ── D4. The route actually returns the three answers ────────────────────
    tree = ast.parse(route_src)
    fields = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "MCPConsentInfo":
            for stmt in node.body:
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                    fields.add(stmt.target.id)
    _check(
        "D4. MCPConsentInfo carries who / where / what",
        {"account_email", "workspace_name", "grants", "legacy_full_access"} <= fields,
    )

    # The workspace shown must be resolved by the SAME function the connector's
    # own auth uses — else the screen can promise one workspace while the token
    # reaches another (the ADR-501 D1 display/gate divergence).
    _check(
        "D4. the workspace is resolved via resolve_workspace_for_principal",
        "resolve_workspace_for_principal" in route_src,
    )
    _check(
        "D4. the mint-default workspace name is not leaked raw",
        "display_workspace_name" in route_src,
    )

    # ── D5. The FE renders them, and the false copy is GONE ─────────────────
    _check(
        "D5. the wrong 'read and write your memory' copy is deleted",
        "your memory" not in fe_src,
    )
    # Asserts the ITERATION IS OVER THE PAYLOAD, not that the two tokens
    # "grants" and ".map(" both appear somewhere in the file. The first spelling
    # of this check did the latter and PASSED its own falsification: replacing
    # `info.grants.map(...)` with `[].map(...)` left both tokens present (the
    # type declaration still says `grants`), so a screen rendering NOTHING read
    # as green. A counting/co-occurrence check cannot defend a specific site.
    _check(
        "D5. the screen iterates the grants FROM the payload",
        re.search(r"info\s*\.\s*grants\s*\.\s*map\s*\(", fe_src) is not None,
    )
    _check(
        "D5. the screen names the account being connected as",
        "account_email" in fe_src,
    )
    _check(
        "D5. the screen names the workspace",
        "workspace_name" in fe_src,
    )
    _check(
        "D5. legacy full access gets its own visible warning branch",
        "legacy_full_access" in fe_src,
    )
    _check(
        "D5. the API client type carries the new fields (no silent undefined)",
        all(k in client_src for k in ("account_email", "workspace_name", "grants")),
    )

    # ── D6. The members pane shows the tier, as its OWN axis ────────────────
    # ADR-563 made the tiers enforced; the pane still showed only PATH regions
    # (ADR-532 read_scopes/write_scopes), so an operator could not tell a
    # legacy full-access connector from a read-only one. The two axes must stay
    # distinguishable: merging the tier into the write-zone chip row would imply
    # one narrows the other.
    ws_route = open("routes/workspace.py").read()
    pane = open("../web/components/workspace-concepts/WorkspaceMembersCard.tsx").read()

    _check(
        "D6. the members route resolves the connection's token scopes",
        "connection_scopes" in ws_route and "mcp_oauth_access_tokens" in ws_route,
    )
    # Grants key on the PROVIDER host-id, tokens on the churning client_id.
    # Reuse the existing bridge rather than inventing a second mapping.
    _check(
        "D6. it bridges provider host-id → client_ids (not a second mapping)",
        "client_ids_for_provider" in ws_route,
    )
    _check(
        "D6. legacy full access is computed by the SHARED helper, not re-derived",
        "from services.mcp_scopes import is_legacy_full" in ws_route,
    )
    _check(
        "D6. the pane renders the tier from the payload",
        re.search(r"m\s*\.\s*connection_scopes", pane) is not None,
    )
    _check(
        "D6. the tier is a SEPARATE line from the write-zone chips (two axes)",
        "connectionTier" in pane and "describeConnectionTier" in pane,
    )

    total = len(FAILURES)
    print(
        f"\nADR-563 consent-disclosure gate: "
        f"{_RUN - total}/{_RUN} passed, {total} failed"
    )
    for f in FAILURES:
        print(f"  ✗ {f}")
    return 1 if FAILURES else 0


_RUN = 23

if __name__ == "__main__":
    sys.exit(run())
