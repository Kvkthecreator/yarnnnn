"""Deliberate workspace genesis — the create act (ADR-465 D2, 2026-08-18).

Guards the carve that makes this safe to grow:

  1. Genesis is its OWN seam (`services/workspace_genesis.py`), distinct from
     the cold-user door's `ensure_owner_workspace` — which is a FIRST-workspace
     function (returns early when an owner row exists) and must never be taught
     to mint a second.
  2. The mint carries **no signup grant**. The $3 is per-PERSON (ADR-172), and
     the column DEFAULT (migration 144) would print it on every call. This is
     the assertion most likely to be silently reverted by "simplifying" the
     insert payload, so it is EXECUTED, not grepped.
  3. The route is actually WIRED — the model is `extra="forbid"`, the handler
     calls the seam, and it does NOT owner-gate (a member-only principal
     starting their own workspace is ADR-465:129's ratified case).

Run: python3 test_workspace_genesis_deliberate.py   (from api/)
"""

import ast
import os
import re
import sys
import types
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

failures: list = []
checks = 0


def check(label: str, cond: bool) -> None:
    global checks
    checks += 1
    if cond:
        print(f"  ✓ {label}")
    else:
        print(f"  ✗ {label}")
        failures.append(label)


def _load_genesis():
    """Import the genesis module against a stubbed supabase seam.

    Executes the REAL create_workspace body — a source grep cannot tell whether
    balance_usd survives into the payload.
    """
    captured: dict = {}

    class _Ins:
        def __init__(self, payload):
            captured["payload"] = payload

        def execute(self):
            row = dict(captured["payload"])
            row["id"] = "ws-new"
            return types.SimpleNamespace(data=[row])

    class _Tbl:
        def __init__(self, name):
            captured["table"] = name

        def insert(self, payload):
            return _Ins(payload)

    class _Cli:
        def table(self, name):
            return _Tbl(name)

    fake = types.ModuleType("services.supabase")
    fake.get_service_client = lambda: _Cli()
    fake._resolve_owner_workspace_id_cached = mock.Mock(cache_clear=mock.Mock())
    sys.modules["services.supabase"] = fake
    sys.modules.pop("services.workspace_genesis", None)
    import importlib

    mod = importlib.import_module("services.workspace_genesis")
    return mod, captured, fake


print("\n[1] The seam exists and is distinct from the cold-user door")
genesis_path = os.path.join(HERE, "services", "workspace_genesis.py")
check("1a. services/workspace_genesis.py exists", os.path.exists(genesis_path))
gsrc = open(genesis_path).read() if os.path.exists(genesis_path) else ""
check(
    "1b. genesis does NOT call ensure_owner_workspace (the first-workspace fn)",
    "ensure_owner_workspace(" not in gsrc,
)
sup = open(os.path.join(HERE, "services", "supabase.py")).read()
_ensure = re.search(r"def ensure_owner_workspace\(.*?\n(?=\n\n@|\n\ndef |\n\n# )", sup, re.S)
check(
    "1c. ensure_owner_workspace still early-returns on an existing owner row "
    "(it is NOT the multi-workspace path)",
    bool(_ensure) and "if existing:" in _ensure.group(0) and "return existing" in _ensure.group(0),
)

print("\n[2] The mint prints no money — EXECUTED, not grepped")
mod, captured, fake = _load_genesis()
row = mod.create_workspace("user-1", "Acme Research")
payload = captured.get("payload", {})
check("2a. inserts into the workspaces table", captured.get("table") == "workspaces")
check("2b. balance_usd is explicitly 0 (the $3 column DEFAULT is overridden)", payload.get("balance_usd") == 0)
check(
    "2c. free_balance_granted=True (the grant is SETTLED, so no later refill re-grants it)",
    payload.get("free_balance_granted") is True,
)
check("2d. owner_id comes from the authenticated caller", payload.get("owner_id") == "user-1")
check("2e. the caller's name is what lands", payload.get("name") == "Acme Research")
check("2f. returns the new workspace id", row.get("id") == "ws-new")
check(
    "2g. the oldest-first owner resolver cache is cleared (it may hold a stale answer)",
    fake._resolve_owner_workspace_id_cached.cache_clear.called,
)

print("\n[3] Name normalization is real")
check("3a. internal whitespace collapses (no two look-alike rows)", mod.normalize_workspace_name("  Acme   Research ") == "Acme Research")
for bad, why in [("", "empty"), ("   ", "whitespace-only"), ("x" * 81, "over 80")]:
    try:
        mod.normalize_workspace_name(bad)
        check(f"3b. refuses {why}", False)
    except mod.WorkspaceGenesisError:
        check(f"3b. refuses {why}", True)
check("3c. accepts exactly 80", mod.normalize_workspace_name("x" * 80) == "x" * 80)

print("\n[4] The route is WIRED (not merely defined)")
rsrc = open(os.path.join(HERE, "routes", "workspace.py")).read()
tree = ast.parse(rsrc)
handler = next(
    (
        n
        for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        and n.name == "create_owned_workspace"
    ),
    None,
)
check("4a. the handler exists", handler is not None)
hsrc = ast.get_source_segment(rsrc, handler) if handler else ""
# Strip comments/docstring so an assertion cannot match its own explanation.
hbody = re.sub(r"#.*", "", hsrc)
if handler and handler.body and isinstance(handler.body[0], ast.Expr):
    doc = ast.get_source_segment(rsrc, handler.body[0]) or ""
    hbody = hbody.replace(doc, "")
check("4b. the handler CALLS the genesis seam", "create_workspace(" in hbody)
check(
    "4c. it passes the AUTHENTICATED user id, never a caller-supplied one",
    re.search(r"create_workspace\(\s*auth\.user_id\s*,", hbody) is not None,
)
check(
    "4d. it is POST /workspace and 201",
    any(
        isinstance(d, ast.Call)
        and getattr(d.func, "attr", "") == "post"
        and d.args
        and getattr(d.args[0], "value", "") == "/workspace"
        and any(k.arg == "status_code" and k.value.value == 201 for k in d.keywords)
        for d in (handler.decorator_list if handler else [])
    ),
)
check(
    "4e. NOT owner-gated — a member-only principal may start their own "
    "(ADR-465:129); the owner-only 403 copy belongs to PATCH, not here",
    "Only the workspace owner" not in hbody,
)
check("4f. a bad name surfaces as 400, not 500", "WorkspaceGenesisError" in hbody and "400" in hbody)

print("\n[5] The request model refuses what we have not built")
mtree = next(
    (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == "WorkspaceCreateRequest"),
    None,
)
check("5a. WorkspaceCreateRequest exists", mtree is not None)
msrc = ast.get_source_segment(rsrc, mtree) if mtree else ""
check(
    "5b. extra=forbid (a future field sent early is REFUSED, not silently dropped)",
    '"extra": "forbid"' in msrc or "'extra': 'forbid'" in msrc,
)

print("\n[6] The FE binds + hard-navigates (a rebind needs a full reload, ADR-407 D9)")
pane = os.path.join(HERE, "..", "web", "components", "workspace-concepts", "WorkspaceCreatePane.tsx")
psrc = open(pane).read() if os.path.exists(pane) else ""
check("6a. the pane exists", bool(psrc))
# Strip block comments NON-GREEDILY, then line comments WITHOUT re.S. Combining
# the two alternatives under re.S makes `//.*` run to end-of-file and swallow the
# whole component — which failed this gate against CORRECT code on first run.
pbody = re.sub(r"/\*.*?\*/", "", psrc, flags=re.S)
pbody = re.sub(r"//.*", "", pbody)
check("6b. it pins the new workspace", "setActiveWorkspace(" in pbody)
check("6c. it HARD-navigates (window.location), never a client route", "window.location.assign" in pbody)
check("6d. it calls the create verb", "api.workspace.create(" in pbody)

print("\n[7] The pane is mounted on the workspace door (not the account door)")
door = os.path.join(HERE, "..", "web", "app", "(authenticated)", "workspace-settings", "page.tsx")
dsrc = open(door).read() if os.path.exists(door) else ""
check("7a. imported by workspace-settings", "WorkspaceCreatePane" in dsrc)
check("7b. registered as a pane key", '"create"' in dsrc)
acct = os.path.join(HERE, "..", "web", "app", "(authenticated)", "settings", "page.tsx")
asrc = open(acct).read() if os.path.exists(acct) else ""
check(
    "7c. NOT on the account door — a workspace is a commons + billing unit "
    "(ADR-416/378), not a personal object (operator ruling 2026-08-18)",
    "WorkspaceCreatePane" not in asrc,
)

print("\n[8] The creator can REACH what they just created")
# THE DEFECT THIS SUITE MISSED (found by an operator click-pass, 2026-08-18).
# Genesis minted the row, the pane pinned X-Workspace-Id to it, and
# `principal_reaches_workspace` then REFUSED it: the owner branch used the
# oldest-first SINGULAR resolver, which returns the creator's OLDER workspace,
# and there is no grant row (ownership ground truth is the `owner_id` COLUMN —
# see principal_grants.has_billing_authority — so genesis correctly writes no
# owner grant). Both branches failed → 403 on every request → the member was
# locked out of a workspace they own, switcher included.
sup2 = open(os.path.join(HERE, "services", "supabase.py")).read()
check("8a. a PLURAL owned-workspace resolver exists", "def resolve_owned_workspace_ids" in sup2)
_reach = re.search(r"def principal_reaches_workspace\(.*?\n(?=\n\ndef |\n\n@)", sup2, re.S)
_rbody = re.sub(r"#.*", "", _reach.group(0)) if _reach else ""
check(
    "8b. the reach check consults EVERY owned workspace, not just home",
    "resolve_owned_workspace_ids(" in _rbody,
)
check(
    "8c. it no longer equality-compares the SINGULAR home resolver "
    "(that is what locked the owner out)",
    "resolve_owner_workspace_id(user_id) == workspace_id" not in _rbody,
)
check(
    "8d. the plural resolver keeps the ownership filter (never a cross-tenant list)",
    bool(re.search(r"def resolve_owned_workspace_ids.*?\.eq\(\s*[\"']owner_id[\"']", sup2, re.S)),
)
_memb = re.search(r"async def get_workspace_memberships\(.*?\n(?=\n\n@router)", rsrc, re.S)
_mbody = re.sub(r"#.*", "", _memb.group(0)) if _memb else ""
check(
    "8e. the switcher lists ALL owned workspaces (else the new one is hidden)",
    "resolve_owned_workspace_ids(" in _mbody,
)

print(f"\n{'='*66}")
if failures:
    print(f"FAILED {len(failures)}/{checks}")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print(f"PASSED {checks}/{checks}")
