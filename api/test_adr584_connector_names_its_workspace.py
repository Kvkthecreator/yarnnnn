#!/usr/bin/env python3.11
"""ADR-584 gate — the connector can NAME where it is standing.

Run with py3.11: anything importing `mcp_server/*` needs `/tmp/mcpenv` (the API
venv is 3.9 and dies at import on a `str | None` default annotation).

    /tmp/mcpenv/bin/python3.11 test_adr584_connector_names_its_workspace.py

What this defends, and why each check is shaped the way it is:

D1 — `whoami` exists as a real, reachable, scope-checked verb. Not "the string
     appears in the file": the roster is parsed, the registration is parsed, and
     the scope classification is read from the SHIPPED table.

D2 — the three bindings are each produced by DRIVING `resolve_mcp_workspace_detail`
     with a stubbed reach function, never by reading the source. A source grep
     cannot tell a branch that exists from a branch that lands (the lesson this
     repo has paid for repeatedly), and `binding` is the entire observability
     claim of this ADR.

D3 — the mint-default name degrades to null. A leaked "My Workspace" is worse
     than no name: it reads as a choice the operator made.

D1-envelope — no `compose_*` builder gained a workspace key. The ADR REJECTED
     the envelope shape; a rejection recorded only in prose is one a later commit
     re-litigates by accident.

Every check here was falsified — broken deliberately, observed to fail, restored.
"""

from __future__ import annotations

import ast
import asyncio
import inspect
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

API = Path(__file__).parent
SERVER_SRC = (API / "mcp_server" / "server.py").read_text()
AUTH_SRC = (API / "mcp_server" / "auth.py").read_text()
COMPOSITION_SRC = (API / "services" / "mcp_composition.py").read_text()

_passed = 0
_failed = 0


def _check(label: str, cond: bool, detail: str = "") -> bool:
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"PASS  {label}  {detail}")
    else:
        _failed += 1
        print(f"FAIL  {label}  {detail}")
    return cond


# Comments stripped: an assertion must never be satisfiable by its own
# explanatory prose (this repo has hit that five separate times).
def _decommented(src: str) -> str:
    return "\n".join(line.split("#", 1)[0] for line in src.splitlines())


def run() -> bool:
    ok = True

    # ══ D1. The verb is rostered, registered, and scoped ═════════════════════

    roster = set(re.findall(r'^\s{4}\(\s*\n\s{8}"([a-z]+)",', SERVER_SRC, re.M))
    ok &= _check(
        "D1. whoami is in the _INTEROP_VERBS roster",
        "whoami" in roster,
        f"(roster: {len(roster)} verbs)",
    )

    # The roster is DATA and the instructions prose is DERIVED from it, so this
    # is also what makes whoami announce itself — no sentence to hand-edit.
    from mcp_server import server as srv

    instructions = srv._build_interop_instructions()
    ok &= _check(
        "D1. the derived instructions announce whoami to the host",
        "whoami" in instructions,
    )

    # ...and ANNOUNCING it is not enough. Probed 2026-08-20: asked "what
    # workspace am I connected to", a live ChatGPT connection answered from a
    # `list` — the verb table named whoami, but the proactive-trigger paragraph
    # (which is what tells a host WHEN to reach for a verb) never mentioned it,
    # so the one question whoami exists to answer was answered by enumerating
    # files. A listing shows what is IN a workspace, never WHICH one it is.
    # Anchored on the trigger paragraph specifically, not on the whole string,
    # because the derived verb table already satisfies the check above.
    trigger_para = instructions.split("Use these proactively")[-1]
    ok &= _check(
        "D1.a the PROACTIVE-TRIGGER paragraph routes a 'which workspace' question to whoami",
        "whoami" in trigger_para,
    )

    # Registered as a real tool, not merely described. Parsed from the AST so a
    # `name="whoami"` inside a docstring or comment cannot satisfy it.
    tree = ast.parse(SERVER_SRC)
    registered: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call):
                continue
            target = dec.func
            if not (isinstance(target, ast.Attribute) and target.attr == "tool"):
                continue
            named = next(
                (kw.value.value for kw in dec.keywords
                 if kw.arg == "name" and isinstance(kw.value, ast.Constant)),
                None,
            )
            registered.add(named or node.name)
    ok &= _check(
        "D1. whoami is a REGISTERED @mcp.tool (AST, not a string match)",
        "whoami" in registered,
        f"(registered: {len(registered)})",
    )

    # Scope: the WEAKEST tier. Read from the shipped table, not restated.
    from services.mcp_scopes import (
        SCOPE_READ,
        SCOPE_WRITE,
        VERB_SCOPES,
        allowed_verbs,
    )

    ok &= _check(
        "D1. whoami requires the READ tier (the weakest verb)",
        VERB_SCOPES.get("whoami") == SCOPE_READ,
        f"(got {VERB_SCOPES.get('whoami')!r})",
    )

    # It must route through the chokepoint WITH its verb — the ADR-563 rule.
    code = _decommented(SERVER_SRC)
    ok &= _check(
        "D1. the handler passes verb= to resolve_request_client",
        'resolve_request_client(verb="whoami")' in code,
    )

    # `allowed_verbs` must DERIVE from the enforcement table, so what whoami
    # tells the model it may do cannot drift from what assert_scope permits.
    # Driven, not read: a read-only token must not be told it may save.
    read_only = allowed_verbs([SCOPE_READ])
    writer = allowed_verbs([SCOPE_WRITE])
    ok &= _check(
        "D1. allowed_verbs(files:read) excludes every write verb",
        "whoami" in read_only and "open" in read_only
        and not {"save", "edit", "delete", "move", "share"} & set(read_only),
        f"({read_only})",
    )
    ok &= _check(
        "D1. allowed_verbs(files:write) includes writes, still excludes share",
        {"save", "edit"} <= set(writer) and "share" not in writer,
        f"({writer})",
    )

    # ══ D2. The three bindings are DRIVEN, not read ══════════════════════════
    # This is the ADR's observability claim, so it is proved by execution: stub
    # the reach resolver and confirm each branch reports the right reason.

    import services.supabase as sb
    from mcp_server import auth as mcp_auth

    original = sb.resolve_workspace_for_principal
    try:
        # (a) chosen — the stamped workspace is reachable.
        sb.resolve_workspace_for_principal = lambda uid, ws=None: (
            "ws-chosen" if ws == "ws-chosen" else "ws-default"
        )
        got = mcp_auth.resolve_mcp_workspace_detail("u1", "ws-chosen")
        ok &= _check(
            "D2. a reachable stamped workspace reports binding='chosen'",
            got == ("ws-chosen", mcp_auth.BINDING_CHOSEN),
            f"(got {got})",
        )

        # (b) fallback — a stamp EXISTS but is unreachable. The degrade is
        # deliberate; being unable to SAY it happened was the defect.
        sb.resolve_workspace_for_principal = lambda uid, ws=None: (
            None if ws else "ws-default"
        )
        got = mcp_auth.resolve_mcp_workspace_detail("u1", "ws-revoked")
        ok &= _check(
            "D2. an UNREACHABLE stamp degrades AND reports binding='fallback'",
            got == ("ws-default", mcp_auth.BINDING_FALLBACK),
            f"(got {got})",
        )

        # (c) default — no stamp at all (every pre-573 token).
        got = mcp_auth.resolve_mcp_workspace_detail("u1", None)
        ok &= _check(
            "D2. no stamp reports binding='default'",
            got == ("ws-default", mcp_auth.BINDING_DEFAULT),
            f"(got {got})",
        )

        # (d) the wrapper's contract is UNCHANGED for its ~90 callers: a bare id.
        sb.resolve_workspace_for_principal = lambda uid, ws=None: (
            "ws-chosen" if ws == "ws-chosen" else "ws-default"
        )
        plain = mcp_auth.resolve_mcp_workspace("u1", "ws-chosen")
        ok &= _check(
            "D2. resolve_mcp_workspace still returns a BARE id (no tuple leak)",
            plain == "ws-chosen" and isinstance(plain, str),
            f"(got {plain!r})",
        )

        # (e) a resolver failure must never fail the request.
        def _boom(uid, ws=None):
            raise RuntimeError("db down")

        sb.resolve_workspace_for_principal = _boom
        got = mcp_auth.resolve_mcp_workspace_detail("u1", "ws-x")
        ok &= _check(
            "D2. a resolution failure degrades to (None, 'unresolved'), never raises",
            got == (None, mcp_auth.BINDING_UNRESOLVED),
            f"(got {got})",
        )
    finally:
        sb.resolve_workspace_for_principal = original

    # ══ D3. compose_whoami's payload — driven end to end ═════════════════════

    from services import mcp_composition as mc

    class _Auth:
        user_id = "u1"
        workspace_id = "ws-1"
        caller_identity = "yarnnn:mcp:claude.ai"

    def _drive(rows, binding="chosen", scopes=("files:read",)):
        """Run compose_whoami against a stubbed workspaces read."""
        class _Res:
            data = rows

        class _Q:
            def table(self, *_a): return self
            def select(self, *_a): return self
            def eq(self, *_a): return self
            def limit(self, *_a): return self
            def execute(self): return _Res()

        original_client = sb.get_service_client
        sb.get_service_client = lambda: _Q()
        try:
            return asyncio.get_event_loop().run_until_complete(
                mc.compose_whoami(
                    auth=_Auth(), client_name="claude.ai",
                    binding=binding, scopes=list(scopes),
                )
            )
        finally:
            sb.get_service_client = original_client

    named = _drive([{"name": "yarnnn workspace"}])
    ok &= _check(
        "D3. a NAMED workspace is reported by name",
        named["workspace"] == "yarnnn workspace" and named["workspace_named"] is True,
        f"(got {named['workspace']!r})",
    )
    ok &= _check(
        "D3. the workspace id travels too (an address the model can quote back)",
        named["workspace_id"] == "ws-1",
    )

    # The mint default must NOT leak — "My Workspace" is not "my" to the reader.
    minted = _drive([{"name": "My Workspace"}])
    ok &= _check(
        "D3. the MINT DEFAULT degrades to null, never leaked as a chosen name",
        minted["workspace"] is None and minted["workspace_named"] is False,
        f"(got {minted['workspace']!r})",
    )
    ok &= _check(
        "D3. an unnamed workspace is described by address, not invented copy",
        "unnamed workspace" in minted["explanation"],
    )

    # The fallback must be STATED in the prose the model reads — the whole point.
    fell_back = _drive([{"name": "yarnnn workspace"}], binding="fallback")
    ok &= _check(
        "D3. binding='fallback' is reported in the payload",
        fell_back["binding"] == "fallback",
    )
    ok &= _check(
        "D3. the fallback explanation WARNS before writing (not a silent success)",
        "NOT landing in" in fell_back["explanation"]
        and "chose" in fell_back["explanation"],
    )
    ok &= _check(
        "D3. binding='chosen' does NOT carry the warning",
        "NOT landing in" not in named["explanation"],
    )

    # Attribution: the model can state who the signature will name before signing.
    ok &= _check(
        "D3. the payload names the attribution writes will carry",
        named["you"] == "yarnnn:mcp:claude.ai",
    )

    # Capabilities must reflect the TOKEN, driven both ways.
    ok &= _check(
        "D3. a read-only token is told it cannot save",
        "save" not in named["capabilities"] and "whoami" in named["capabilities"],
        f"({named['capabilities']})",
    )
    full = _drive([{"name": "w"}], scopes=("read",))
    ok &= _check(
        "D3. a LEGACY-full token is told it can share",
        "share" in full["capabilities"],
        f"({full['capabilities']})",
    )

    # A workspaces lookup failure must never fail the session.
    class _Boom:
        def table(self, *_a): raise RuntimeError("no db")

    original_client = sb.get_service_client
    sb.get_service_client = lambda: _Boom()
    try:
        degraded = asyncio.get_event_loop().run_until_complete(
            mc.compose_whoami(auth=_Auth(), client_name="c", binding="chosen", scopes=["files:read"])
        )
        ok &= _check(
            "D3. a name-lookup failure degrades, never raises",
            degraded["success"] is True and degraded["workspace"] is None,
        )
    finally:
        sb.get_service_client = original_client

    # ══ D1-envelope. The REJECTED shape stays rejected ═══════════════════════
    # ADR-584 D1 chose a verb over a `workspace` key on every response. Enforced
    # rather than remembered: a prose-only rejection gets re-litigated by accident.
    comp_tree = ast.parse(COMPOSITION_SRC)
    offenders: list[str] = []
    for node in ast.walk(comp_tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.name.startswith("compose_") or node.name == "compose_whoami":
            continue
        for sub in ast.walk(node):
            if not isinstance(sub, ast.Dict):
                continue
            for key in sub.keys:
                if isinstance(key, ast.Constant) and key.value in ("workspace", "workspace_id"):
                    offenders.append(f"{node.name}:{key.value}")
    ok &= _check(
        "D1. no compose_* file verb carries a workspace key (the rejected envelope)",
        not offenders,
        f"({offenders})" if offenders else "",
    )

    # ══ D3 (ADR-533 D6). The MANDATE still does not port ═════════════════════
    # This ADR moves the workspace's ADDRESS across the boundary and stops. If a
    # later commit reaches for the mandate here, D6's ruling is what breaks.
    ok &= _check(
        "D3. compose_whoami does not read the workspace MANDATE (ADR-533 D6 holds)",
        "MANDATE" not in inspect.getsource(mc.compose_whoami).replace(
            "the workspace MANDATE", ""
        ),
    )

    return ok


if __name__ == "__main__":
    result = run()
    print(
        f"\nADR-584 connector-names-its-workspace gate: "
        f"{_passed}/{_passed + _failed} passed, {_failed} failed"
    )
    sys.exit(0 if result else 1)
