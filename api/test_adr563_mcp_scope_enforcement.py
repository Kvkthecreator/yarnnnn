"""ADR-563 — the MCP scope field authorizes, it does not decorate.

Before this ADR `valid_scopes=["read"]` was the ONLY scope the connector
registered, and nothing checked it: a token LABELLED read could `delete` a file
and `share` a member grant. This gate asserts the scope set exists, that the
containment holds, that every bound verb is classified, and — the part that
actually defends the boundary — that the check is reached from the ONE
chokepoint rather than nine remembered call sites.

Run with `python3 test_adr563_mcp_scope_enforcement.py` (NOT pytest — the
check() gates print ✗ but a pytest run reports PASS; see MEMORY.md).
"""

import ast
import re
import sys
import types
import logging
import os

FAILURES: list[str] = []


def _check(label: str, cond: bool) -> bool:
    if cond:
        logging.info("✓ %s", label)
    else:
        logging.error("✗ %s", label)
        FAILURES.append(label)
    return cond


def _load_scope_tables():
    """Load auth.py's pure-data scope tables without the app runtime.

    The module imports services.supabase (and transitively the supabase SDK),
    which is not importable under the baseline interpreter. The scope tables and
    assert_scope are pure data + stdlib, so compile just those nodes. This keeps
    the gate runnable in CI without a live environment.
    """
    src = open("mcp_server/auth.py").read()
    tree = ast.parse(src)
    keep = [
        n
        for n in tree.body
        if isinstance(n, (ast.Assign, ast.AnnAssign, ast.ClassDef))
        or (isinstance(n, ast.FunctionDef) and n.name in ("assert_scope", "token_scopes"))
    ]
    mod = types.ModuleType("scopes")
    mod.__dict__.update(logging=logging, os=os)
    exec(compile(ast.Module(body=keep, type_ignores=[]), "scopes", "exec"), mod.__dict__)
    return mod


def run() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    ok = True

    a = _load_scope_tables()
    server_src = open("mcp_server/server.py").read()
    auth_src = open("mcp_server/auth.py").read()

    # ── D1. The scope set exists and is tiered ──────────────────────────────
    ok &= _check(
        "D1. three narrow scopes are declared",
        {a.SCOPE_READ, a.SCOPE_WRITE, a.SCOPE_SHARE} == {
            "files:read", "files:write", "files:share"
        },
    )
    ok &= _check(
        "D1. the legacy full-access scope is retained (pre-563 tokens keep working)",
        a.SCOPE_LEGACY_FULL == "read" and "read" in a.VALID_SCOPES,
    )
    ok &= _check(
        "D1. a fresh registration defaults to the READ-ONLY floor, not full access",
        a.DEFAULT_SCOPES == ["files:read"],
    )

    # ── D2. Every bound verb is classified ──────────────────────────────────
    # Derived from the roster, so a NEW verb that lands without a scope fails
    # here rather than silently defaulting to reachable.
    roster = set(re.findall(r'^\s{4}\(\s*\n\s{8}"([a-z]+)",', server_src, re.M))
    ok &= _check(
        f"D2. roster parsed from _INTEROP_VERBS ({len(roster)} verbs)",
        len(roster) == 9,
    )
    ok &= _check(
        "D2. every bound verb carries a scope classification",
        roster == set(a.VERB_SCOPES),
    )

    # ── D2. Containment: the tiers actually nest ────────────────────────────
    def allows(held: list[str], verb: str) -> bool:
        return any(s in a._SATISFIES[a.VERB_SCOPES[verb]] for s in held)

    ok &= _check(
        "D2. files:read reaches the four reads and NOTHING else",
        all(allows(["files:read"], v) for v in ("open", "list", "search", "history"))
        and not any(
            allows(["files:read"], v)
            for v in ("save", "edit", "delete", "move", "share")
        ),
    )
    ok &= _check(
        "D2. files:write reaches reads + mutations but NOT share",
        allows(["files:write"], "save")
        and allows(["files:write"], "delete")
        and allows(["files:write"], "open")
        and not allows(["files:write"], "share"),
    )
    ok &= _check(
        "D2. files:share is the top tier",
        all(allows(["files:share"], v) for v in a.VERB_SCOPES),
    )
    ok &= _check(
        "D2. the legacy 'read' token still reaches every verb (no live connector breaks)",
        all(allows(["read"], v) for v in a.VERB_SCOPES),
    )

    # ── D2. The scope classification agrees with the tool annotations ───────
    # The @mcp.tool blocks already declare readOnlyHint. A verb cannot be
    # annotated read-only and classified as needing write, or vice versa —
    # that divergence is how a surface starts lying about itself.
    read_only_tools = set()
    for m in re.finditer(
        r'@mcp\.tool\((.*?)\)\s*\nasync def (\w+)', server_src, re.S
    ):
        block, fn = m.group(1), m.group(2)
        named = re.search(r'name="([a-z]+)"', block)
        verb = named.group(1) if named else ("open" if fn == "open_file" else fn)
        if re.search(r"readOnlyHint\s*=\s*True", block):
            read_only_tools.add(verb)
    ok &= _check(
        "D2. readOnlyHint tools are exactly the files:read verbs",
        read_only_tools == {v for v, s in a.VERB_SCOPES.items() if s == a.SCOPE_READ},
    )

    # ── D3. The guard is at the CHOKEPOINT, not per call site ───────────────
    # Strip comments: the rationale for the chokepoint is written in prose right
    # beside the code, and a bare-name assertion matches its own explanation.
    auth_code = "\n".join(l.split("#", 1)[0] for l in auth_src.splitlines())
    ok &= _check(
        "D3. resolve_request_client takes a verb",
        re.search(r"def resolve_request_client\(\s*verb", auth_code) is not None,
    )
    ok &= _check(
        "D3. it calls assert_scope",
        re.search(r"assert_scope\(verb\)", auth_code) is not None,
    )
    ok &= _check(
        "D3. an unclassified verb is REFUSED, not allowed (fail closed)",
        re.search(r"if required is None:\s*\n\s*raise ScopeDenied", auth_code)
        is not None,
    )

    # Every handler passes its verb — the enforcement is only real if reached.
    server_code = "\n".join(l.split("#", 1)[0] for l in server_src.splitlines())
    calls = re.findall(r"resolve_request_client\(verb=\"([a-z]+)\"\)", server_code)
    ok &= _check(
        f"D3. all nine handlers pass a verb ({len(calls)} found)",
        len(calls) == 9 and set(calls) == set(a.VERB_SCOPES),
    )
    ok &= _check(
        "D3. no handler calls resolve_request_client() bare (would skip the check)",
        re.search(r"resolve_request_client\(\s*\)", server_code) is None,
    )

    # ── D4. The transport does not pre-reject legacy tokens ─────────────────
    # required_scopes at the door would 401 every pre-563 token before the
    # containment rule could keep it working.
    ok &= _check(
        "D4. required_scopes is empty (authorization is per-verb, not at the door)",
        re.search(r"required_scopes\s*=\s*\[\s*\]", server_code) is not None,
    )
    ok &= _check(
        "D4. the SDK registers the real scope list, not a hardcoded ['read']",
        re.search(r"valid_scopes\s*=\s*mcp_auth\.VALID_SCOPES", server_code)
        is not None,
    )

    print()
    print(
        f"ADR-563 MCP scope-enforcement gate: "
        f"{16 - len(FAILURES)}/16 passed, {len(FAILURES)} failed"
    )
    if FAILURES:
        for f in FAILURES:
            print(f"  ✗ {f}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(run())
