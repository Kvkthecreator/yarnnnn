"""ADR-577 regression gate — the agent-credential claim is withdrawn.

Replaces `test_adr566_workspace_credential.py`. ADR-566's gate passed while
production did the exact thing ADR-566 forbade, because every assertion tested
the resolver's SHAPE and none DROVE an agent through it. This gate drives.

Asserts:
  1. A human auth resolves the account store (keyed user_id).
  2. An AGENT auth is REFUSED — driven through the real resolver.
  2b. A real `HeadlessAuth` (not a stand-in) is refused.
  2c. A member's LANE is NOT refused — it is the member's hands.
  3. The withdrawn two-store symbols are absent.
  4. No route serves /integrations/workspace-credentials.
  5. The FE card + client method are gone.
  6. D4 — every platform_connections read outside the chokepoint is allowlisted,
     matching ANY auth-carrying read (not just `credentials_encrypted`).
"""

import re
import sys
from pathlib import Path

API = Path(__file__).resolve().parent
WEB = API.parent / "web"
CHOKEPOINT = "services/platform_credentials.py"


def _check(label, ok, detail=""):
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {label}" + (f" — {detail}" if detail and not ok else ""))
    return bool(ok)


def _code_only(path: Path) -> str:
    """Source with comments and docstrings stripped.

    A gate must never match its own explanatory prose — this file's comments
    name `platform_connections` repeatedly.
    """
    import ast

    src = path.read_text()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return src
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                body[0].value.value = ""
    return ast.unparse(tree)


# ---------------------------------------------------------------------------
# Driven fakes
# ---------------------------------------------------------------------------

class _Res:
    def __init__(self, data):
        self.data = data


class _Q:
    def __init__(self, sink):
        self.sink = sink

    def select(self, *a, **k):
        return self

    def eq(self, col, val):
        self.sink.setdefault("filters", []).append((col, val))
        return self

    def limit(self, n):
        return self

    def execute(self):
        return _Res([{"credentials_encrypted": "enc", "metadata": {}, "status": "active"}])


class _Client:
    def __init__(self, sink):
        self.sink = sink

    def table(self, name):
        self.sink["table"] = name
        return _Q(self.sink)


class _Auth:
    """A minimal auth stand-in; caller_identity decides classification."""

    def __init__(self, user_id="u1", caller_identity=None, headless=False):
        self.sink = {}
        self.client = _Client(self.sink)
        self.user_id = user_id
        self.headless = headless
        if caller_identity is not None:
            self.caller_identity = caller_identity


def _test_resolution():
    from services.platform_credentials import resolve_platform_credential

    out = []

    # 1 — a human resolves the account store.
    human = _Auth(user_id="u1", caller_identity="member:u1")
    row = resolve_platform_credential(human, "slack")
    out.append(_check(
        "1 a human auth resolves a credential from the account store",
        row is not None and ("user_id", "u1") in human.sink.get("filters", []),
        f"filters={human.sink.get('filters')}"))

    # 2 — an AGENT is refused. THE assertion this gate exists for: pre-577 this
    #     returned the workspace OWNER's personal token.
    agent = _Auth(user_id="owner-uuid", caller_identity="specialist:researcher", headless=True)
    row = resolve_platform_credential(agent, "slack")
    out.append(_check(
        "2 an AGENT auth is REFUSED a credential (no owner-token fallthrough)",
        row is None, f"got={row}"))
    out.append(_check(
        "2a the refusal never touched the table (no read, not a filtered read)",
        "table" not in agent.sink, f"sink={agent.sink}"))

    return out


def _test_real_headless_auth():
    """2b — drive the REAL HeadlessAuth, not a stand-in.

    The pre-577 defect lived precisely in the gap between what a test's fake
    auth carried and what `HeadlessAuth` actually carries.
    """
    from services.primitives.registry import HeadlessAuth
    from services.platform_credentials import resolve_platform_credential, is_agent_caller

    out = []
    sink = {}
    auth = HeadlessAuth(_Client(sink), "owner-uuid", agent={"role": "researcher"})

    out.append(_check(
        "2b the real HeadlessAuth classifies as an agent caller",
        is_agent_caller(auth), f"caller_identity={getattr(auth,'caller_identity',None)}"))
    out.append(_check(
        "2b2 the real HeadlessAuth is REFUSED a credential",
        resolve_platform_credential(auth, "slack") is None))

    # A HeadlessAuth with no agent role still must not reach a human's token.
    bare = HeadlessAuth(_Client({}), "owner-uuid")
    out.append(_check(
        "2b3 a role-less HeadlessAuth is also refused (fails toward refusal)",
        resolve_platform_credential(bare, "slack") is None,
        f"caller_identity={getattr(bare,'caller_identity',None)}"))

    return out


def _test_lane_is_not_an_agent():
    """2c — a member's LANE is the member's hands and MUST still resolve.

    The over-correction to guard against: refusing every AI-driven caller would
    break a member's own chat lane reaching their own connector.
    """
    from services.platform_credentials import resolve_platform_credential, is_agent_caller

    out = []
    lane = _Auth(user_id="u1", caller_identity="member:u1 via claude-sonnet-4-6")
    out.append(_check(
        "2c a member's lane is NOT classified as an agent",
        not is_agent_caller(lane)))
    row = resolve_platform_credential(lane, "slack")
    out.append(_check(
        "2c2 a member's lane still resolves that member's own credential",
        row is not None and ("user_id", "u1") in lane.sink.get("filters", []),
        f"filters={lane.sink.get('filters')}"))
    return out


def _test_symbols_withdrawn():
    import services.platform_credentials as pc

    out = []
    gone = ["is_agent_principal", "workspace_credential_filter", "_WORKSPACE_CREDENTIAL_ROLES"]
    present = [n for n in gone if hasattr(pc, n)]
    out.append(_check(
        "3 the withdrawn two-store symbols are absent",
        not present, f"still present={present}"))
    return out


def _test_route_and_fe_deleted():
    out = []

    routes_src = (API / "routes" / "integrations.py").read_text()
    # Match the ROUTE DECORATOR, not the string — the deletion note names the
    # path in a comment, and a gate must not be satisfiable by its own epitaph.
    has_route = bool(re.search(
        r'@router\.(get|post|put|delete|patch)\(\s*["\'][^"\']*workspace-credentials',
        routes_src))
    out.append(_check("4 no route serves /integrations/workspace-credentials", not has_route))

    card = WEB / "components" / "workspace-concepts" / "WorkspaceCredentialsCard.tsx"
    out.append(_check("5 the WorkspaceCredentialsCard component is deleted", not card.exists()))

    client_src = (WEB / "lib" / "api" / "client.ts").read_text()
    out.append(_check(
        "5b the workspaceCredentials client method is deleted",
        "workspaceCredentials" not in client_src))

    page = WEB / "app" / "(authenticated)" / "workspace-settings" / "page.tsx"
    out.append(_check(
        "5c the Agent Credentials pane is unmounted",
        "WorkspaceCredentialsCard" not in page.read_text()))

    return out


#: Files that read `platform_connections` WITHOUT an acting principal in scope
#: (service-role/scheduler paths, or the member's own settings routes that
#: manage their connections by definition). Every entry must EARN itself below.
PRINCIPAL_LESS_CREDENTIAL_READS = {
    # -- the member's own connector management + discovery (by definition) --
    "routes/integrations.py",
    "routes/workspace.py",              # workspace summary: platform names only
    "integrations/validation.py",       # the health probe (ADR-576 D3)
    # -- ENUMERATION only (platform/status/created_at; never the token) --
    "services/bundle_reader.py",
    "services/freddie_envelope.py",     # the one-line peripheral field
    "services/primitives/registry.py",  # list_integrations (ADR-535: see != reach)
    "services/primitives/system_state.py",
    "services/primitives/track_universe.py",
    "routes/system.py",
    "services/capture/lane.py",         # capability gate: existence, not token
    # -- capability probe: a HUMAN's availability question (ADR-577 §1e) --
    "services/orchestration.py",
    # -- ADR-582: the connector lane (service-role; reads selection/settings/
    #    connected_by ONLY — held by the ENUMERATION_ONLY check below, not by
    #    this comment; a capture's tool call goes through handle_platform_tool
    #    → the chokepoint). ADR-591 deleted the walkers: connector_derive.py
    #    no longer reads the connection row at all, so its entry is gone --
    "services/connectors.py",
    # -- service-role / scheduler paths with no acting principal --
    "services/risk_gate.py",
    "services/outcomes/commerce.py",
    "services/outcomes/reconciler.py",
    "services/outcomes/trading.py",
    "services/primitives/track_foreign.py",
    "services/primitives/track_regime.py",
}

#: Allowlisted readers whose justification is "enumeration only — never the
#: token". Found 2026-08-19: the allowlist was EXISTENCE-based, so an
#: allowlisted file could silently GROW a credential read (a falsifier adding
#: `credentials_encrypted` to connectors.py stayed green). These entries now
#: earn their comment mechanically. Files legitimately touching credentials
#: (the chokepoint, routes/integrations OAuth management, validation probe,
#: track_universe, outcomes providers) are deliberately NOT here.
ENUMERATION_ONLY = {
    "services/connectors.py",
    "services/bundle_reader.py",
    "services/freddie_envelope.py",
    "services/primitives/registry.py",
    "services/primitives/system_state.py",
    "services/capture/lane.py",
    "routes/system.py",
    "routes/workspace.py",
}


def _test_chokepoint_breadth():
    """6 — D4: the gate sees ANY platform_connections read, not only ones
    selecting `credentials_encrypted`.

    The ADR-566 gate matched `credentials_encrypted` + `user_id` in a 400-char
    window, so `capability_available`'s `attestation_grade` read was invisible.
    A gate that cannot see the violation is not a gate.
    """
    out = []
    offenders = []
    for py in sorted((API / "services").rglob("*.py")) + sorted((API / "routes").rglob("*.py")):
        rel = str(py.relative_to(API))
        if rel == CHOKEPOINT or rel in PRINCIPAL_LESS_CREDENTIAL_READS:
            continue
        code = _code_only(py)
        if re.search(r'table\(\s*["\']platform_connections["\']\s*\)', code):
            offenders.append(rel)

    out.append(_check(
        "6 every platform_connections read outside the chokepoint is allowlisted",
        not offenders, f"unlisted readers: {sorted(set(offenders))}"))

    # THE ALLOWLIST MUST EARN ITSELF — an unchecked exemption list is a mute
    # button. Every entry must still exist and still read the table.
    stale = []
    for rel in sorted(PRINCIPAL_LESS_CREDENTIAL_READS):
        f = API / rel
        if not f.exists():
            stale.append(f"{rel} (missing)")
            continue
        if not re.search(r'table\(\s*["\']platform_connections["\']\s*\)', _code_only(f)):
            stale.append(f"{rel} (no longer reads)")
    out.append(_check(
        "6b no stale allowlist entries", not stale, f"stale={stale}"))

    # 6c — an "enumeration only" entry must STAY enumeration-only: the
    # allowlist was existence-based, so an entry could silently grow a
    # credential read behind its own justifying comment (found by falsifier
    # 2026-08-19). Code-only, so a comment mentioning the column is fine.
    grew = [rel for rel in sorted(ENUMERATION_ONLY)
            if (API / rel).exists()
            and "credentials_encrypted" in _code_only(API / rel)]
    out.append(_check(
        "6c enumeration-only readers never touch credentials_encrypted",
        not grew, f"grew a credential read: {grew}"))

    return out


def main():
    results = []
    results += _test_resolution()
    results += _test_real_headless_auth()
    results += _test_lane_is_not_an_agent()
    results += _test_symbols_withdrawn()
    results += _test_route_and_fe_deleted()
    results += _test_chokepoint_breadth()

    passed = sum(1 for r in results if r)
    print(f"\n{passed}/{len(results)} ADR-577 assertions pass")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
