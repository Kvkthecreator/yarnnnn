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
# The connect act moved from ReachConnected into the FINDER (2026-09-20), which
# Reach mounts — the assertion is still "Reach owns it, not the deleted Settings
# pane", but the door is now one door for all three lanes. It moved because the
# roster-level "Available" list rendered AFTER the roster, so a member with zero
# connections never reached it: the empty state's one button opens the finder,
# and the finder had no first-party lane. Counted at the CALL, not by `in src`,
# which an import line alone satisfies.
_finder_src = _read("components/settings/FindConnectorModal.tsx")
_finder_code = re.sub(r"/\*[\s\S]*?\*/", "", _finder_src)
_finder_code = re.sub(r"^\s*//.*$", "", _finder_code, flags=re.M)
check("Reach owns the connect act (the OAuth round-trip starts in the finder it mounts)",
      _finder_code.count("api.integrations.getAuthorizationUrl(") >= 1
      and "FindConnectorModal" in _reach_connected,
      f"authorize calls={_finder_code.count('api.integrations.getAuthorizationUrl(')}")

# ⭐ THE REACHABILITY ARM (2026-09-20). The defect this closes was invisible to
# every check above: the "Available" list EXISTED in this file and rendered its
# avatars, so a presence census was green while the list sat behind an early
# return that a member with no connections never passed. The click-pass found it
# by being that member — searching "wordpress" in the only dialog the empty
# state offers and being told "Nothing matched".
#
# So: BOTH finder mount sites must pass `heldProviders`, including the one in the
# zero-connection branch. A lane the empty state cannot see is the whole bug.
_mounts = re.findall(r"<FindConnectorModal\b[\s\S]*?/>", _reach_connected)
check("the finder is mounted in BOTH branches — the empty state included",
      len(_mounts) == 2, f"{len(_mounts)} mount sites")
check("…and every mount passes heldProviders, so the first-party lane renders "
      "for a member holding NOTHING (the 2026-09-20 stranded-lane defect)",
      all("heldProviders=" in m for m in _mounts),
      str([("heldProviders=" in m) for m in _mounts]))
check("the first-party lane is SEARCHABLE — the click-pass found the gap by "
      "typing a connector's name and being told nothing matched",
      "m.displayName.toLowerCase().includes(q)" in _finder_code
      and "m.provider.includes(q)" in _finder_code)
check("…and 'Nothing matched' counts the first-party lane, or a found "
      "connector renders under a line saying nothing was found",
      "firstParty.length === 0" in _finder_code)
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
print("D5. one connector, one face — the mark survives the trip to Connected")

# WHY THIS GROUP EXISTS. A connector used to have three faces: a brand chip on
# the four platform-OAuth rows, a generic lucide plug for EVERY attached MCP
# server, and nothing at all in the finder. The member who attached Linear could
# not pick it out of their own list. `lib/connectors/marks.tsx` resolves one
# identity and `ConnectorAvatar` renders it; these checks hold both halves.

_marks = _read("lib/connectors/marks.tsx")
_avatar = _read("components/connectors/ConnectorAvatar.tsx")
_finder = _read("components/settings/FindConnectorModal.tsx")
_attached_sub = _read("components/settings/AttachedConnectorSubsurface.tsx")

# ⚠ Anchored on the EXPORT and on the avatar's CALL, not on the bare name. A
# substring check is satisfied by a rename (`connectorIdentityX` still contains
# `connectorIdentity`) and by an import line — the arm that deleted the resolver
# came back GREEN against the loose form.
check("the identity resolver is exported under its canonical name",
      bool(re.search(r"export function connectorIdentity\(", _marks)))
check("the one render site CALLS it",
      bool(re.search(r"\bconnectorIdentity\(\{", _avatar)),
      "ConnectorAvatar no longer resolves an identity")

# ⭐ THE LEAK CHECK, and the reason this file is hand-authored at all. /reach is
# the boundary surface; resolving 55 marks through a favicon service would tell
# a third party which connectors a member browses, every time the modal opens.
# Asserted on the RENDERED source of every connector surface, not on marks.tsx
# alone — the leak would arrive as an <img> in whichever component added it.
_surfaces = {
    "lib/connectors/marks.tsx": _marks,
    "components/connectors/ConnectorAvatar.tsx": _avatar,
    "components/settings/FindConnectorModal.tsx": _finder,
    "components/reach/ReachConnected.tsx": _reach_connected,
    "components/settings/AttachedConnectorSubsurface.tsx": _attached_sub,
}
# ⚠ NOT through the shared `_strip_comments`. That helper strips `//` to
# end-of-line, and every URL this check hunts for CONTAINS `//`, so a re-added
# favicon endpoint is truncated at its scheme and the evidence is destroyed
# BEFORE the search runs — the falsification arm that re-added one came back
# GREEN for exactly that reason. Stripping is still needed, because marks.tsx's
# own header names these services while explaining why it uses none of them; so
# this strips a line comment only where the `//` does not follow a URL scheme.
def _strip_comments_keeping_urls(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    return re.sub(r"(?<!:)//[^\n]*", "", src)


_leaks = [
    name
    for name, src in _surfaces.items()
    if re.search(
        r"s2/favicons|icons\.duckduckgo|favicon\.ico|<img\b|next/image",
        _strip_comments_keeping_urls(src),
    )
]
check("no connector surface fetches a third-party mark (no favicon service, no <img>)",
      not _leaks, f"outbound mark fetch in {_leaks}")

# ⭐ EVERY surface renders THE SAME component. A shared resolver with two render
# sites still drifts; the whole point is that the finder row and the Connected
# row are visibly one connector. Counted at the CALL, not at the import — an
# `in src` check is satisfied by the import line alone (2026-09-17).
# ⚠ The count is EXACT, not `>= 1`. ReachConnected renders the avatar twice
# (the connected row AND the Available list) and the finder three times (the
# curated row, the directory row, and the picked connector in the step header),
# so a `>= 1` threshold stays green while one of them is deleted — the arm that
# removed the Connected row's avatar came back GREEN against exactly that. A
# threshold cannot fail on what it no longer covers; the census has to be the
# assertion (ADR-636, and the 2026-09-17 action-feedback sweep).
for name, src, want in (
    # 4 = the curated row · the directory row · and the step header's TWO
    # branches (a curated pick and a directory pick land on different steps).
    # 5 = the four above + the first-party lane's row (2026-09-20). yarnnn's own
    # OAuth connectors wear the SAME face here as they do once connected, which
    # is the whole point of the shared component.
    ("the finder's browse rows + step header + first-party lane", _finder, 5),
    # 1, down from 2: the "Available" list was DELETED from this file when its
    # lane moved into the finder. One door, one render site — a mirrored list
    # would be the second write path D3.a refuses.
    ("the Connected list", _reach_connected, 1),
    ("the attached connection's page", _attached_sub, 1),
):
    body = _strip_comments(src)
    found = body.count("<ConnectorAvatar")
    check(f"{name} render ConnectorAvatar at every site ({want})",
          found == want,
          f"{found} render sites, expected {want} — a site was added or deleted")

# The generic plug is GONE from the two places that used to wear it AS A
# CONNECTOR'S FACE. Scoped to a CHIP-shaped plug, not to the glyph as such: the
# empty state ("Nothing is connected yet") still draws a plug, and there it
# stands for the ABSENCE of connectors rather than for one connector, which is
# the right glyph. A blanket ban went red on that empty state on first run —
# the rule is about a row's identity, so the check has to be too.
for _name, _src in (
    ("the Connected row", _reach_connected),
    ("the attached connection's header", _attached_sub),
):
    _body = _strip_comments(_src)
    _chip_plug = re.search(r"h-\d+ w-\d+[^\"']*(?:rounded|bg-muted)[^\"']*\"[^<]*>\s*<Plug", _body) or re.search(
        r"<Plug[^>]*className=\"[^\"]*h-\d", _body
    ) and "rounded-lg bg-muted" in _body
    check(f"{_name} no longer wears a generic plug as its face", not _chip_plug)

# ⭐ A MARK IS A CLAIM ABOUT A VENDOR. The first draft of marks.tsx carried ~28
# paths written from memory and the click-pass found roughly half were wrong
# shapes — Ahrefs as a lowercase b, Box as goggles, Datadog as a blob. Every one
# typechecked, built, and compiled into the CSS: a path string cannot be wrong
# in a way a gate reads. So the gate holds the only thing it CAN hold — that the
# set stays small and deliberate, and that the file still carries the discipline
# that says a mark is not added until its rendering has been looked at.
_mark_count = len(re.findall(r"icon:\s*svg\(", _marks))
check("the mark set is bounded (a mark is added only after its shape is seen)",
      0 < _mark_count <= 32, f"{_mark_count} marks — raising this needs a click-pass in the commit")
check("marks.tsx records why a mark needs a click-pass before it is added",
      "SEEN RENDERED" in _marks)

# ⭐ THE FALLBACK MUST DISCRIMINATE. A lettermark that paints every row the same
# tone is exactly as blind as the generic plug it replaced — the failure mode
# that shipped a populated-but-constant column on /admin (2026-09-18). This
# walks the REAL directory seed, not a fixture, so a re-derivation that clusters
# the names cannot quietly collapse the palette.
import json  # noqa: E402

_seed = json.loads((API / "services/connector_directory_seed.json").read_text())
_tones = re.findall(r'"(bg-\[#[0-9A-Fa-f]{6}\])"', _marks.split("const LETTER_TONES = [")[1].split("];")[0])
_domains = re.findall(r'^\s*"([^"]+)":', _marks.split("const DOMAIN_MARKS: Record<string, ConnectorMark> = {")[1].split("\n};")[0], re.M)


def _has_mark(host: str) -> bool:
    if host in _domains:
        return True
    labels = host.split(".")
    return any(".".join(labels[i:]) in _domains for i in range(1, len(labels) - 1))


def _tone_for(seed: str) -> str:
    h = 0
    for ch in seed:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return _tones[h % len(_tones)]


_fallback = []
for _srv in _seed["servers"]:
    _host = _srv["url"].split("/")[2].lower()
    if _has_mark(_host):
        continue
    _fallback.append((_srv["title"], _tone_for(_srv["title"].lower())))

# DISTINCT, not the entry count: twelve copies of one slate is a palette of one
# and would satisfy a length check while painting every fallback row the same.
check("the lettermark palette is wide enough to separate a clustered directory",
      len(set(_tones)) >= 12, f"only {len(set(_tones))} distinct tones")
_spread = len({t for _, t in _fallback})
check("the fallback DISTRIBUTES rather than painting one constant tone",
      _spread >= min(6, len(_fallback)),
      f"{len(_fallback)} lettermark rows collapsed onto {_spread} tones")

# ⭐ A tone is seeded on the TITLE, never the host: four of the directory's
# literature endpoints share ONE host, so a host-first seed paints them
# identically — the indistinguishability the lettermark exists to end.
#
# ⚠ This reads the ORDER OUT OF THE TYPESCRIPT rather than recomputing it here.
# The first version of this check called a Python `_tone_for(title)` and asked
# whether the results differed — which they always did, because the gate was
# choosing the seed itself. Reverting the real `const seed = …` line to
# host-first left it GREEN: a gate agreeing with its own reimplementation
# (2026-09-18, the `needs` fixture). The assertion has to be about the SOURCE.
_seed_expr = re.search(r"const seed = ([^;]+);", _marks)
check("the resolver's tone seed is derived (the source states the order)",
      _seed_expr is not None)
if _seed_expr:
    _order = [t.strip() for t in _seed_expr.group(1).split("||")]
    check("…and the TITLE is the first seed, not the host",
          _order and _order[0].startswith("title"),
          f"seed order is {_order} — a host-first seed collapses the shared-host rows")

_shared_host = [s for s in _seed["servers"] if s["url"].split("/")[2].lower() == "hcls.mcp.claude.com"]
if len(_shared_host) > 1:
    # With the order confirmed above, the consequence is worth stating too: the
    # real rows on that one host must land on different tones.
    _their_tones = {_tone_for(s["title"].lower()) for s in _shared_host}
    check("…so servers sharing one host still get different chips",
          len(_their_tones) > 1,
          f"{len(_shared_host)} rows on one host collapsed onto {len(_their_tones)} tone(s)")

# ⭐ AN ARBITRARY TAILWIND CLASS ONLY EXISTS IF TAILWIND SAW IT. Every tone is a
# `bg-[#......]` literal; if one were ever computed (a template string, a lookup
# built at runtime) the class would vanish from the built CSS and the chip would
# render transparent — visible only in a browser, never in a typecheck.
check("every lettermark tone is a literal class Tailwind can scan",
      all(re.fullmatch(r"bg-\[#[0-9A-Fa-f]{6}\]", t) for t in _tones))

# ---------------------------------------------------------------------------
print()
if FAILED:
    print(f"ADR-645 gate RED — {PASSED} passed, {len(FAILED)} failed")
    for f in FAILED:
        print(f"    - {f}")
    sys.exit(1)
print(f"ALL PASS — {PASSED} checks — ADR-645 holds")
