"""ADR-566 — the workspace allocates the agent's credential.

Script-style (the authoring/py convention in this repo — run `python3
test_adr566_workspace_credential.py` from `api/`).

WHAT THIS DEFENDS
1. D4 — ONE chokepoint. No `platform_connections` credential read may key on a
   raw `user_id` outside `services/platform_credentials.py`. Eight inline reads
   is what this ADR removed; the ratchet is that they cannot come back.
2. D4 — FAIL CLOSED. An unresolvable principal gets no credential, never a
   plausible one.
3. D3/D4 — NO CROSS-STORE FALLBACK. An agent with no workspace credential gets
   None; it must never fall through to a human's. That fallback IS the retired
   owner-reuse branch arriving through an error path.
4. D2 — the probe and the resolver read the SAME store (a capability that lies
   is the ADR-467 §1 Scout-bug shape).
5. ADR-460 D3.a — the cliff, asserted from THIS side: nothing here added a
   field to an agent row, a posture row, or a member manifest.
6. §7 — the lane surface is unchanged (no new reach for a member's lane).
"""

from __future__ import annotations

import ast
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

API = Path(__file__).parent
CHECKS = 0
FAILURES: list[str] = []


def check(label: str, cond: bool, detail: str = "") -> None:
    global CHECKS
    CHECKS += 1
    if cond:
        print(f"  ok   {label}")
    else:
        FAILURES.append(f"{label}{(' — ' + detail) if detail else ''}")
        print(f"  FAIL {label}{(' — ' + detail) if detail else ''}")


# ---------------------------------------------------------------------------
print("\n1. D4 — one chokepoint: no raw user_id credential read outside it")
# ---------------------------------------------------------------------------
# Strip comments/docstrings via `ast` rather than grepping text — a prose
# mention of `platform_connections` in a docstring is not a read, and a gate
# that cannot tell them apart pins a SPELLING instead of a BEHAVIOUR.

CHOKEPOINT = "services/platform_credentials.py"


def _code_only(path: Path) -> str:
    """Source with docstrings removed — comments are already absent from ast."""
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError:
        return ""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            if (node.body and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)):
                node.body.pop(0)
    return ast.unparse(tree)


#: Paths that read a credential WITHOUT an acting principal to classify — they
#: take a bare `(client, user_id)`, not an `auth`. There is no principal to ask,
#: so routing them through the resolver would mean INVENTING one, and a fabricated
#: principal is worse than an honest human-scoped read.
#:
#: Two families, both genuinely principal-less:
#:  - the alpha-trader dogfood path (outcomes/, primitives/track_*, risk_gate) —
#:    service-client mechanical recurrences under the ADR-380 D4 exogenous-clock
#:    track, keyed by the workspace owner;
#:  - `delivery.py` — no live importer outside tests (CLAUDE.md flags it a
#:    deletion candidate);
#:  - `routes/integrations.py` — the ACCOUNT DOOR itself (ADR-425 D1): a human
#:    managing their own connectors. Asserted separately below to stay account-scoped.
#:
#: ⚠️ This list may only SHRINK. An entry earns its place by having no principal
#: in scope — never by being inconvenient to convert. Adding a NEW file here is
#: the regression this gate exists to catch: a handler that HAS an `auth` and
#: reads around the chokepoint anyway.
PRINCIPAL_LESS_CREDENTIAL_READS = {
    # `routes/alpha_trader.py` was here for one draft and REMOVED: this gate's
    # own self-check proved it carries an `auth`, so it uses the chokepoint.
    # That is the list working as designed — an exemption must be earned.
    "routes/integrations.py",
    "services/delivery.py",
    "services/outcomes/commerce.py",
    "services/outcomes/trading.py",
    "services/primitives/track_foreign.py",
    "services/primitives/track_regime.py",
    "services/primitives/track_universe.py",
    "services/risk_gate.py",
}

offenders: list[str] = []
for py in sorted((API / "services").rglob("*.py")) + sorted((API / "routes").rglob("*.py")):
    rel = str(py.relative_to(API))
    if rel == CHOKEPOINT or rel in PRINCIPAL_LESS_CREDENTIAL_READS:
        continue
    code = _code_only(py)
    if "platform_connections" not in code:
        continue
    # A credential read is a `platform_connections` table access that also
    # selects the encrypted blob. Enumeration-only reads (status/platform) are
    # handled by `connected_platforms` and checked separately below.
    for m in re.finditer(r'table\(\s*["\']platform_connections["\']\s*\)', code):
        window = code[m.start(): m.start() + 400]
        if "credentials_encrypted" in window and "user_id" in window:
            offenders.append(rel)
            break

check(
    "no credential read keys on a raw user_id outside the chokepoint",
    not offenders,
    f"offenders: {sorted(set(offenders))}",
)

# THE ALLOWLIST MUST EARN ITSELF. An exemption list that is never checked is a
# mute button. Every entry must (a) still exist and (b) still be principal-less
# — i.e. its credential reads must not have an `auth` object in scope. A file
# that grows an `auth`-carrying credential read must leave the list.
stale = {p for p in PRINCIPAL_LESS_CREDENTIAL_READS if not (API / p).exists()}
check("no stale entry in the principal-less allowlist", not stale, str(sorted(stale)))

leaked: list[str] = []
for rel in sorted(PRINCIPAL_LESS_CREDENTIAL_READS):
    if rel == "routes/integrations.py":
        continue  # the account door: asserted by the account_scope_filter check below
    code = _code_only(API / rel)
    for m in re.finditer(r'table\(\s*["\']platform_connections["\']\s*\)', code):
        head = code[max(0, m.start() - 600): m.start() + 200]
        # `auth.client.table(...)` / `auth.user_id` means a principal WAS in
        # scope and the read went around the chokepoint anyway.
        if "auth.client" in head or "auth.user_id" in head:
            leaked.append(rel)
            break
check(
    "every allowlisted file is genuinely principal-less (no auth in scope)",
    not leaked,
    f"these have an auth and must use the chokepoint: {sorted(set(leaked))}",
)

# The routes layer legitimately manages a HUMAN's own connectors (ADR-425 D1 —
# connect/disconnect/list in the account door). Those are account-store CRUD,
# not agent credential resolution, and they use `account_scope_filter`. Assert
# that helper is still the spelling there, so a future edit cannot quietly
# widen an account-door route to the workspace store.
integrations = (API / "routes" / "integrations.py").read_text()
check(
    "the account door still scopes through account_scope_filter (ADR-425 D1 intact)",
    "account_scope_filter" in integrations,
)

# ---------------------------------------------------------------------------
print("\n2. D4 — the resolver fails closed")
# ---------------------------------------------------------------------------
from services.platform_credentials import (  # noqa: E402
    connected_platforms,
    credential_missing_error,
    is_agent_principal,
    resolve_platform_credential,
    workspace_credential_filter,
)


class _FakeTable:
    def __init__(self, rows, log):
        self._rows, self._log = rows, log

    def select(self, *_a, **_k):
        return self

    def eq(self, col, val):
        self._log.append((col, val))
        return self

    def limit(self, *_a):
        return self

    def execute(self):
        return type("R", (), {"data": self._rows})()


class _FakeClient:
    def __init__(self, rows=None):
        self.rows = rows if rows is not None else []
        self.filters: list = []

    def table(self, _name):
        return _FakeTable(self.rows, self.filters)


class _Auth:
    def __init__(self, user_id="u1", workspace_id="ws1", rows=None):
        self.user_id = user_id
        self.workspace_id = workspace_id
        self.client = _FakeClient(rows)
        self.caller_identity = "operator"
        self.principal_id = user_id


check(
    "no platform name → None",
    resolve_platform_credential(_Auth(), "") is None,
)
check(
    "no acting user and not an agent → None (fail closed)",
    resolve_platform_credential(_Auth(user_id=""), "slack") is None,
)

# ---------------------------------------------------------------------------
print("\n3. D3/D4 — the two stores never cross-fall-back")
# ---------------------------------------------------------------------------
# A HUMAN principal reads the account store, keyed user_id — never workspace_id.
human = _Auth(rows=[{"credentials_encrypted": "x", "metadata": {}, "status": "active"}])
resolve_platform_credential(human, "slack")
cols = [c for c, _ in human.client.filters]
check("a human principal keys on user_id", "user_id" in cols, f"filters={human.client.filters}")
check("a human principal does NOT key on workspace_id", "workspace_id" not in cols)

# An AGENT principal reads the workspace store — and when it has no workspace,
# it gets NOTHING rather than someone's account row.
import services.platform_credentials as _pc  # noqa: E402

_real_is_agent = _pc.is_agent_principal
try:
    _pc.is_agent_principal = lambda _auth: True
    agent = _Auth(rows=[{"credentials_encrypted": "x", "metadata": {}, "status": "active"}])
    resolve_platform_credential(agent, "slack")
    acols = [c for c, _ in agent.client.filters]
    check("an agent principal keys on workspace_id", "workspace_id" in acols, f"filters={agent.client.filters}")
    check("an agent principal does NOT key on user_id", "user_id" not in acols)

    # THE LOAD-BEARING ONE: no workspace → None, never the human's store.
    orphan = _Auth(workspace_id="", rows=[{"credentials_encrypted": "leak", "metadata": {}, "status": "active"}])
    got = resolve_platform_credential(orphan, "slack")
    check(
        "an agent with no workspace gets None (the retired owner-reuse branch stays retired)",
        got is None,
        f"got={got}",
    )
    check(
        "…and issued no query at all",
        not orphan.client.filters,
        f"filters={orphan.client.filters}",
    )

    # The error text must send the reader to the door that can actually fix it.
    err = credential_missing_error(agent, "slack")
    check(
        "an agent's missing-credential error names Workspace Settings",
        "Workspace Settings" in err.get("error", ""),
        err.get("error", ""),
    )
finally:
    _pc.is_agent_principal = _real_is_agent

human_err = credential_missing_error(_Auth(), "slack")
check(
    "a human's missing-credential error still names Settings",
    "Connect it in Settings" in human_err.get("error", ""),
    human_err.get("error", ""),
)

# ---------------------------------------------------------------------------
print("\n4. D2 — the probe reads the same store as the resolver")
# ---------------------------------------------------------------------------
tools_src = (API / "services" / "platform_tools.py").read_text()
check(
    "the capability probe goes through connected_platforms",
    "connected_platforms" in tools_src,
)
check(
    "…and no longer enumerates platform_connections inline",
    'table("platform_connections")' not in _code_only(API / "services" / "platform_tools.py"),
)
check(
    "workspace_credential_filter keys on workspace_id",
    workspace_credential_filter("ws9") == ("workspace_id", "ws9"),
)

# ---------------------------------------------------------------------------
print("\n5. ADR-460 D3.a — the cliff, asserted from this side")
# ---------------------------------------------------------------------------
from services.agents_registry import (  # noqa: E402
    AGENT_MANIFEST_KEYS,
    AGENT_ROW_KEYS,
    POSTURE_ROW_KEYS,
)

check(
    "AGENT_ROW_KEYS unchanged (no credential/authority field)",
    AGENT_ROW_KEYS == frozenset(
        {"slug", "name", "blurb", "icon", "model", "token_profile", "posture"}
    ),
    str(sorted(AGENT_ROW_KEYS)),
)
check(
    "POSTURE_ROW_KEYS unchanged",
    POSTURE_ROW_KEYS == frozenset(
        {"slug", "name", "based_on", "blurb", "icon", "model", "token_profile", "posture"}
    ),
    str(sorted(POSTURE_ROW_KEYS)),
)
check(
    "AGENT_MANIFEST_KEYS unchanged",
    AGENT_MANIFEST_KEYS == frozenset({"based_on", "name", "tone", "model", "color", "avatar"}),
    str(sorted(AGENT_MANIFEST_KEYS)),
)
_cred_words = {"credential", "connector", "platform", "authority", "reach"}
for label, keys in (
    ("agent row", AGENT_ROW_KEYS),
    ("posture row", POSTURE_ROW_KEYS),
    ("member manifest", AGENT_MANIFEST_KEYS),
):
    check(
        f"no credential-shaped key on the {label}",
        not any(any(w in k.lower() for w in _cred_words) for k in keys),
    )

# ---------------------------------------------------------------------------
print("\n6. §7 — the lane surface gained no reach")
# ---------------------------------------------------------------------------
from services.lane_runner import LANE_SURFACE_EXTRA, LANE_TOOL_NAMES  # noqa: E402

check(
    "LANE_TOOL_NAMES unchanged (the five file verbs)",
    LANE_TOOL_NAMES == ("ReadFile", "WriteFile", "EditFile", "SearchFiles", "ListFiles"),
    str(LANE_TOOL_NAMES),
)
# ⚠️ A tuple-pin on LANE_SURFACE_EXTRA stood here and was RETIRED by ADR-568.
# It read `== ("QueryKnowledge", "WebSearch", "list_integrations")` — ADR-566
# §7's POINT-IN-TIME claim that no new lane reach rode in with the credential
# work. That was true when written and is not a standing law, so it went red on
# the first ratified addition (`GenerateImage`, ADR-568 D3) — the recorded
# pinned-spelling failure shape, where a gate reads a legitimate addition as a
# violation. Re-spelling it with four names would only defer the same red.
#
# The STANDING laws it was standing in for are both asserted elsewhere and stay
# green: the ADR-467 D4.a ceiling (every extra is read-only OR an artifact verb
# — test_agent_registry.py + test_adr535_connector_visibility.py, restated by
# ADR-568 D3), and the no-platform-reach invariant, which is the check directly
# below and is the one ADR-566 actually cares about.
check(
    "no platform_* tool reached the lane surface",
    not any(n.startswith("platform_") for n in LANE_TOOL_NAMES + LANE_SURFACE_EXTRA),
)

# ---------------------------------------------------------------------------
print("\n6b. D5 — the two panes stay two (no re-merge of the ADR-425 pane)")
# ---------------------------------------------------------------------------
WEB = API.parent / "web"
ws_page = (WEB / "app/(authenticated)/workspace-settings/page.tsx").read_text()
acct_page = (WEB / "app/(authenticated)/settings/page.tsx").read_text()

check(
    "the workspace door mounts the workspace-credential card",
    "WorkspaceCredentialsCard" in ws_page,
)
# ⚠️ Strip comments before asserting absence. The first draft of this check
# failed on the workspace page's own ADR-425 note explaining WHERE that section
# went — an assertion matching its own explanatory comment, the exact trap
# CLAUDE.md's gate-craft rule names. Assert on CODE, never on prose.
_ws_code = re.sub(r"//.*$", "", ws_page, flags=re.M)
_ws_code = re.sub(r"/\*.*?\*/", "", _ws_code, flags=re.S)
check(
    "…and does NOT re-mount the account door's human-connector section",
    "ConnectedIntegrationsSection" not in _ws_code,
    "ADR-425 D1 — a human's connectors stay in the account door",
)
check(
    "the account door still mounts the human-connector section",
    "ConnectedIntegrationsSection" in acct_page,
)
check(
    "…and does NOT mount the workspace-credential card",
    "WorkspaceCredentialsCard" not in acct_page,
)

card = (WEB / "components/workspace-concepts/WorkspaceCredentialsCard.tsx").read_text()
check(
    "the workspace card reads the workspace-credential endpoint, not /integrations",
    "workspaceCredentials" in card and "api.integrations.list" not in card,
)
# Normalize JSX whitespace before matching prose: the copy is line-wrapped by
# the formatter, so pinning an exact phrase would break on a re-wrap that
# changed nothing. Match the two CLAIMS the ceiling has to make, not a spelling.
_card_text = " ".join(card.split())
check(
    "the workspace card states the ceiling affirmatively (ADR-535 D3 discipline)",
    "does not let them act on their own" in _card_text
    and "waits for someone to approve it" in _card_text,
)

# The route must precede `/{provider}` or FastAPI resolves it as a provider
# named "workspace-credentials" — the collision this file warns about twice.
import routes.integrations as _ri  # noqa: E402

_paths = [r.path for r in _ri.router.routes if hasattr(r, "path")]
check(
    "the workspace-credential route is registered",
    "/integrations/workspace-credentials" in _paths,
)
check(
    "…and precedes /integrations/{provider} (path-collision trap)",
    _paths.index("/integrations/workspace-credentials") < _paths.index("/integrations/{provider}"),
)

# ---------------------------------------------------------------------------
print("\n7. own-agent is the live role, not an invention")
# ---------------------------------------------------------------------------
from services.programs import HIRE_GRANT_ROLE  # noqa: E402
from services.principals import role_class  # noqa: E402

check(
    "the resolver's role matches the one programs mint",
    HIRE_GRANT_ROLE in _pc._WORKSPACE_CREDENTIAL_ROLES,
    f"{HIRE_GRANT_ROLE} vs {_pc._WORKSPACE_CREDENTIAL_ROLES}",
)
check(
    "own-agent still inherits the member (agent) write ceiling, not the operator's",
    role_class("own-agent") == "agent",
    str(role_class("own-agent")),
)

# ---------------------------------------------------------------------------
print()
if FAILURES:
    print(f"ADR-566 gate RED — {len(FAILURES)}/{CHECKS} failed:")
    for f in FAILURES:
        print(f"  - {f}")
    sys.exit(1)
print(f"{CHECKS}/{CHECKS} checks passed")
print("ADR-566 gate GREEN")
