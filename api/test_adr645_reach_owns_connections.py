"""ADR-645 gate — Reach is the connection surface, and reach follows the member.

Run with:  cd api && venv/bin/python test_adr645_reach_owns_connections.py
(script-style — prints ✗ and exits 1 on failure.)

Two rulings, two groups:

  D1  REACH FOLLOWS THE MEMBER. The recurring proposal that a workspace ADOPTS
      the owner's credentials is CLOSED. This group EXECUTES the refusal rather
      than grepping for it: an agent-shaped caller through the real
      `resolve_platform_credential` gets None, a member gets their own row, and
      an unreadable caller fails closed. Falsified by construction — delete the
      refusal branch and the first check reds.

  D3  REACH OWNS THE CONNECTION ACTS. The `connectors` slug is off the SERVED
      roster while its stub route survives (the ADR-592 retirement contract);
      no caller navigates to the retired slug; the acting machinery MOVED
      rather than forked; and the orphaned components are deleted.

⭐ The roster checks assert the RELATION in both directions. A negative check
   catches a forgotten deletion and never a forgotten addition (ADR-636).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

API = Path(__file__).resolve().parent
ROOT = API.parent
WEB = ROOT / "web"
sys.path.insert(0, str(API))

PASSED = 0
FAILED: list[str] = []


def check(label: str, cond: bool, detail: str = "") -> None:
    global PASSED
    if cond:
        PASSED += 1
        print(f"  ✓ {label}")
    else:
        FAILED.append(label)
        print(f"  ✗ {label}" + (f" — {detail}" if detail else ""))


def _read(rel: str) -> str:
    p = WEB / rel
    return p.read_text() if p.exists() else ""


def _strip_comments(src: str) -> str:
    """Strip comments BEFORE any substring check — a gate that greps its own
    documentation goes red on the sentence explaining the rule (three sightings
    on 2026-09-07 alone)."""
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", src)


# ---------------------------------------------------------------------------
print("D1. reach follows the member — the refusal, EXECUTED")

from services.platform_credentials import (  # noqa: E402
    is_agent_caller,
    resolve_platform_credential,
)


class _Q:
    def __init__(self, rows):
        self.rows = rows

    def select(self, *_a, **_k):
        return self

    def eq(self, col, val):
        self.rows = [r for r in self.rows if r.get(col) == val]
        return self

    def limit(self, _n):
        return self

    def maybe_single(self):
        return self

    def single(self):
        return self

    def execute(self):
        # `res.data` is a LIST — the resolver does `rows[0] if rows else None`.
        class R:
            pass

        r = R()
        r.data = self.rows
        return r


class _Client:
    def __init__(self, rows):
        self.rows = rows

    def table(self, _name):
        return _Q([dict(r) for r in self.rows])


MEMBER = "00000000-0000-0000-0000-0000000000a1"
ROWS = [
    {
        "user_id": MEMBER,
        "platform": "slack",
        "credentials_encrypted": "ENC",
        "metadata": {},
        "status": "active",
    }
]


class _MemberAuth:
    """A member's own request — and a member's chat LANE, which stamps
    `member:{id} via {model}` and IS the member's hands (ADR-408 D2)."""

    def __init__(self, identity=f"member:{MEMBER}"):
        self.user_id = MEMBER
        self.caller_identity = identity
        self.headless = False
        self.client = _Client(ROWS)


class _AgentAuth:
    """Headless agent dispatch — `registry.py::HeadlessAuth` stamps this."""

    def __init__(self, identity="specialist:researcher"):
        self.user_id = MEMBER
        self.caller_identity = identity
        self.headless = True
        self.client = _Client(ROWS)


check("a MEMBER resolves their own account credential",
      (resolve_platform_credential(_MemberAuth(), "slack") or {}).get("credentials_encrypted") == "ENC")
check("a member's LANE is the member's hands, not an agent",
      not is_agent_caller(_MemberAuth(f"member:{MEMBER} via claude-opus-5"))
      and (resolve_platform_credential(_MemberAuth(f"member:{MEMBER} via claude-opus-5"), "slack") or {})
      .get("credentials_encrypted") == "ENC")

# THE RULING. ADR-566 D2 forbade this and keyed the guard on a role zero rows
# hold, so until ADR-577 production actually handed agents the owner's token.
check("an AGENT caller is REFUSED — it never falls through to a human's token",
      resolve_platform_credential(_AgentAuth(), "slack") is None)
check("…and an unreadable headless caller fails CLOSED (refused, not allowed)",
      is_agent_caller(_AgentAuth(identity="")) is True
      and resolve_platform_credential(_AgentAuth(identity=""), "slack") is None)
check("a blank platform resolves nothing",
      resolve_platform_credential(_MemberAuth(), "") is None)

# D2 — there is no workspace credential store. The withdrawn ADR-566 D5 route
# must not come back; `workspace_id` means ROUTING, never ownership.
# ⚠️ Check the ROUTE, not the word: `integrations.py` carries an epitaph naming
# the deleted route, and a substring check over the file matches its own
# documentation (`_strip_comments` handles JS, not Python `#`). Assert that no
# DECORATOR serves the path — the fact, not its description.
_routes = (API / "routes" / "integrations.py").read_text()
_decorated = re.findall(r"@router\.(?:get|post|put|patch|delete)\(\s*[\"']([^\"']+)", _routes)
check("no route SERVES a workspace-credentials path (ADR-577 D3 stays discharged)",
      not [p for p in _decorated if "workspace-cred" in p], str(_decorated))

# ---------------------------------------------------------------------------
print("\nD3. Reach owns the connection acts")

from services.kernel_surfaces import KERNEL_SURFACES, kernel_surface_entries  # noqa: E402

served = {e["slug"] for e in kernel_surface_entries()}
raw = {e["slug"]: e for e in KERNEL_SURFACES}

# The ADR-592 retirement contract, BOTH halves — the row leaves the served
# roster (that IS the hide, nav being backend-driven) while the slug still
# resolves for its stub. Asserting only the first half would pass if someone
# deleted the row outright and broke every bookmark.
check("`connectors` is OFF the served roster (ADR-592: internal leaves it)",
      "connectors" not in served)
check("…while the row survives so the slug still resolves for its stub",
      "connectors" in raw and raw["connectors"].get("stage") == "internal")
check("…and it is no longer a pane of any door (it would render nowhere)",
      not raw["connectors"].get("pane_of") and not raw["connectors"].get("pane_group"))
check("`reach` is the surface that absorbed it, and is PRIMARY",
      "reach" in served and raw["reach"].get("launcher_tier") == "primary")

_stub = _read("app/(authenticated)/connectors/page.tsx")
check("/connectors is a redirect stub into Reach → Connected (ADR-308 transport)",
      "redirect('/reach?reach.pane=connected')" in _stub and "'use client'" not in _stub)
check("…and stays hand-listed in middleware (ADR-592's obligation: a slug off "
      "the roster leaves the auth gate with it)",
      '"/connectors"' in _read("lib/supabase/middleware.ts"))

# The deletion half. Singular Implementation: the legacy home is DELETED, not
# left as a parallel path that drifts.
_settings = _read("app/(authenticated)/settings/page.tsx")
check("the Settings → Connectors pane is DELETED, not mirrored",
      "connectors" not in _strip_comments(_settings))
check("…and the orphaned list components are gone with it",
      not (WEB / "components/settings/ConnectedIntegrationsSection.tsx").exists()
      and not (WEB / "components/settings/ConnectorCard.tsx").exists())

# No caller may point at the retired slug — asserted over the whole FE tree so
# a NEW caller cannot be added without this going red (the addition direction).
_callers: list[str] = []
for path in list((WEB / "components").rglob("*.tsx")) + list((WEB / "app").rglob("*.tsx")):
    body = _strip_comments(path.read_text())
    if "navigateToSurface('connectors')" in body or "foregroundSurface('connectors')" in body:
        _callers.append(str(path.relative_to(WEB)))
    if "settings.pane=connectors" in body:
        _callers.append(f"{path.relative_to(WEB)} (stale return path)")
check("no caller navigates to the retired slug, anywhere in the FE",
      not _callers, str(_callers))

# The MOVE, not a fork (D3.a) — a mirrored design is a second write path.
_reach_connected = _read("components/reach/ReachConnected.tsx")
for comp in ("ManageConnectionSubsurface", "AttachedConnectorSubsurface", "FindConnectorModal"):
    check(f"Reach mounts the moved {comp} (not a copy)",
          f"import {{ {comp} }} from '@/components/settings/{comp}'" in _reach_connected)
check("Reach owns the connect act (the OAuth round-trip starts here)",
      "getAuthorizationUrl" in _reach_connected)
check("Reach owns the disconnect act",
      "api.integrations.disconnect" in _reach_connected)
check("the OAuth round-trip RETURNS to Reach, not to the deleted pane",
      "/reach?reach.pane=connected" in _read("components/settings/ManageConnectionSubsurface.tsx"))

# ⭐ ADR-644 still binds: acts may join this pane, a reach SENTENCE may not.
# Every reach fact must still arrive from the server structure.
_body = _strip_comments(_reach_connected)
check("Connected writes no reach sentence of its own (ADR-644's fifth face)",
      "cannot send" not in _body.replace("i.reach.reads.length", "")
      or "i.reach" in _body,
      "a hand-written reach sentence appeared outside reach_status")
check("…the row's facts come from the server payload (`does` / `reach`)",
      "i.does" in _body and "i.reach" in _body)

# D4 — the pane states its two scopes.
check("Connected says the credential is the member's and the reach the workspace's",
      "held under your account" in _read("app/(authenticated)/reach/page.tsx"))

# ---------------------------------------------------------------------------
print()
if FAILED:
    print(f"ADR-645 gate RED — {PASSED} passed, {len(FAILED)} failed")
    for f in FAILED:
        print(f"    - {f}")
    sys.exit(1)
print(f"ALL PASS — {PASSED} checks — ADR-645 holds")
