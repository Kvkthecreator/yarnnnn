#!/usr/bin/env python3
"""Gate: ADR-628 phase (a) — the outbound disposition, WordPress first tenant.

What must hold:
  1. ONE SEAM — every outbound platform write crosses services/publish.py.
     The exporter fossil (integrations/exporters) stays deleted; the client's
     write verb has exactly one caller (the seam); no unattended module
     (scheduler, strings) reaches the seam — phase (b) is NOT built.
  2. MEMBER-CLICKED — the credential resolves through the ADR-577 path,
     which refuses an agent caller; the route is a member surface act.
  3. HONEST TRANSPORT — the payload composer moves the h1 to the title,
     strips yarnnn's data-* editing grammar, and rewrites nothing else.
  4. BLOGGER-ONLY — a non-post artifact is refused with a reason.
  5. RECEIPTED — a publish appends a `_publish.yaml` sidecar (ADR-254
     machine format) through write_revision, as the member's own act.
  6. The connect surfaces tell the truth (registry rows both sides; the
     connector facts say publish-on-click, never-captures, agents-never).

Script-style — run `python3 test_adr628_outbound_publish.py`.
"""

import asyncio
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = ROOT / "api"
sys.path.insert(0, str(API))

PASSED = 0
FAILED: list[str] = []


def check(label: str, cond: bool, detail: str = "") -> None:
    global PASSED
    if cond:
        PASSED += 1
        print(f"  ok   {label}")
    else:
        FAILED.append(label + (f" — {detail}" if detail else ""))
        print(f"  FAIL {label}" + (f" — {detail}" if detail else ""))


print("1. one seam — and the fossil stays deleted")
check("integrations/exporters is GONE (the ADR-028 fossil)",
      not (API / "integrations" / "exporters").exists())
_callers = []
for p in API.rglob("*.py"):
    rel = str(p.relative_to(API))
    if rel.startswith(("venv", "test_")) or "__pycache__" in rel:
        continue
    src = p.read_text(errors="ignore")
    if "create_post" in src and "wordpress_client" in src and rel != "integrations/core/wordpress_client.py":
        _callers.append(rel)
check("the write verb has exactly ONE caller — the seam",
      _callers == ["services/publish.py"], f"callers={_callers}")
_sched = (API / "jobs" / "unified_scheduler.py").read_text()
_strings = (API / "services" / "standing_work.py").read_text()
check("no unattended module reaches the seam (phase (b) is NOT built)",
      "services.publish" not in _sched and "publish_post_to_wordpress" not in _sched
      and "services.publish" not in _strings and "publish_post_to_wordpress" not in _strings)
_route = (API / "routes" / "publish.py").read_text()
check("the route calls the seam, never the client",
      "services.publish" in _route and "wordpress_client" not in _route)
check("the route refuses stale fields (extra=forbid, the ADR-562 door rule)",
      'extra": "forbid"' in _route or "extra=\"forbid\"" in _route)
check("main.py mounts the door",
      "publish.router" in (API / "main.py").read_text())

print("2. member-clicked — the ADR-577 refusal is structural")
_seam = (API / "services" / "publish.py").read_text()
check("the seam resolves credentials through the ONE path",
      "resolve_platform_credential" in _seam)

from services.platform_credentials import resolve_platform_credential  # noqa: E402


class _AgentAuth:
    caller_identity = "system:standing-run"
    is_agent = True
    user_id = None
    client = None


check("an agent caller is REFUSED a wordpress credential (executed, not grepped)",
      resolve_platform_credential(_AgentAuth(), "wordpress") is None)

print("3. honest transport — the payload composer")
import services.apps  # noqa: F401,E402
from services.authoring import build_skeleton  # noqa: E402
from services.publish import PUBLISH_TARGETS, PublishError, compose_wordpress_payload  # noqa: E402

_html = build_skeleton("post", "gate-probe")
_payload = compose_wordpress_payload(_html)
# build_skeleton stamps the artifact NAME into the h1 (ADR-469 lineage), so
# the composed title IS the name — asserted as the real pipeline behaves.
check("the h1 becomes the title", _payload["title"] == "gate-probe",
      repr(_payload["title"]))
check("…and leaves the body (WordPress renders the title itself)",
      "<h1" not in _payload["content"])
check("yarnnn's editing grammar is stripped (no data-* crosses the wire)",
      "data-" not in _payload["content"], _payload["content"][:120])
check("the member's material survives (standfirst + prose intact)",
      "promise to the reader" in _payload["content"]
      and "Start writing." in _payload["content"])
check("a title-less body degrades honestly",
      compose_wordpress_payload("<main><p>x</p></main>")["title"] == "Untitled post")

# ── ADR-628 D6 — the drive's findings, as assertions ────────────────────────
# ⚠️ F5: the pre-D6 gate composed ONLY build_skeleton("post"), which always
# carries <main>, so all three real defects passed clean. A probe whose only
# input is the happy shape proves the happy shape. These use the shapes that
# actually broke on 2026-09-03.

# F1 — the LEGACY outward artifact: content in <body><article>, no <main>,
# and 98% of the file is stylesheet. The pre-D6 fallback published the raw
# document; the composer must find the real root instead.
_legacy = (
    '<!doctype html>\n<html data-template="article"><head><meta charset="utf-8">'
    "<style>:root { --ink: #1a1a1a; }\n/* a comment mentioning <article> */\n"
    'aside[data-block="callout"] { border-left: 3px solid red; }</style></head>'
    "<body><article><header>"
    '<h1 data-block="heading" data-block-id="t1">test article</h1>'
    '<p class="byline" data-block-id="t3">Byline</p></header>'
    # ⚠️ A <style> INSIDE the content root — the case root-extraction alone
    # does NOT solve. Real artifacts carry per-block style this way, and a
    # <body>-rooted legacy file puts the whole sheet inside the root. Without
    # this, the F2 assertion passes vacuously (falsified 2026-09-03).
    '<style>.byline[data-block="x"] { --ink: #1a1a1a; }</style>'
    # ⚠️ `data-block` abutting the previous attribute's quote with NO leading
    # whitespace — the shape the pre-D6 `\s+data-…` pattern could not see (F3).
    # A fixture that only ever spaces its attributes proves nothing here.
    '<div class="p"data-block="prose"><p>Opening paragraph.</p></div>'
    "</article></body></html>"
)
_leg = compose_wordpress_payload(_legacy)
check("F1: a legacy <article> artifact resolves its content root",
      _leg["title"] == "test article" and "Opening paragraph." in _leg["content"],
      repr(_leg["title"]))
check("F1: the document chrome NEVER crosses (no doctype/<html>/<head>)",
      not any(t in _leg["content"].lower() for t in ("doctype", "<html", "<head>")),
      _leg["content"][:120])
check("F2: <style> is dropped WITH ITS TEXT (the platform keeps stripped-tag text)",
      "--ink" not in _leg["content"] and ":root" not in _leg["content"],
      _leg["content"][:160])
check("F3: data-* is stripped even as a CSS attribute selector (no leading space)",
      "data-" not in _leg["content"], _leg["content"][:160])
check("F1: composition is BOUNDED by the real content, not the file",
      len(_leg["content"]) < len(_legacy) // 2,
      f"{len(_legacy)} -> {len(_leg['content'])}")

# D6 — REFUSAL replaces the fallback. There is no "publish the whole file"
# branch, and its absence is the fix: a refusal is recoverable, a published
# post is not.
for _label, _src in (
    ("an empty file", ""),
    ("a stylesheet-only file", "<html><head><style>body{color:red}</style></head><body></body></html>"),
    ("a rootless fragment", "<div><p>orphan</p></div>"),
    ("an empty content root", "<main>   </main>"),
):
    try:
        compose_wordpress_payload(_src)
        check(f"D6: {_label} is refused", False, "composed instead of refusing")
    except PublishError as _e:
        check(f"D6: {_label} is refused, with a reason", bool(str(_e)), str(_e))

_src_no_text = '<main><div data-block="prose"></div></main>'
try:
    compose_wordpress_payload(_src_no_text)
    check("D6: a markup-only body is refused", False)
except PublishError:
    check("D6: a markup-only body is refused (no text to publish)", True)

print("4. blogger-only + 5. receipted — the seam, driven with stubs")


class _Table:
    def __init__(self, store, name):
        self.store, self.name, self._path = store, name, None

    def select(self, *_a, **_k):
        return self

    def eq(self, col, val):
        if col == "path":
            self._path = val
        return self

    def limit(self, *_a):
        return self

    def execute(self):
        class R:  # noqa: N801
            data = []
        r = R()
        row = self.store.get(self._path)
        r.data = [row] if row else []
        return r


class _Client:
    def __init__(self, store):
        self.store = store

    def table(self, name):
        return _Table(self.store, name)


class _MemberAuth:
    def __init__(self, store):
        self.user_id = "00000000-0000-0000-0000-000000000001"
        self.client = _Client(store)


import services.publish as _pub  # noqa: E402

# A deck must be refused — outbound is the publish medium's alone.
_deck_store = {"/workspace/operation/d/deck.html": {"content": build_skeleton("deck", "d")}}
try:
    asyncio.run(_pub.publish_post_to_wordpress(
        _MemberAuth(_deck_store), path="operation/d/deck.html", site_id="1"))
    check("a deck is refused", False)
except PublishError as e:
    check("a deck is refused, with a reason", "Blogger post" in str(e), str(e))

# A post publishes: stub the client + capture the receipt write.
_store = {"/workspace/operation/p/post.html": {"content": _html}}
_captured: dict = {}


async def _fake_create_post(token, site_id, *, title, content, status="publish"):
    return {"post_id": "77", "url": "https://example.wordpress.com/p", "status": status}


async def _fake_list_sites(token):
    # The site published to is UNLAUNCHED — the D7 case the drive hit.
    return [{"id": "9", "name": "s", "url": "https://s.wordpress.com", "public": False}]


def _fake_write_revision(client, **kw):
    _captured.update(kw)
    return "v-receipt"


import integrations.core.wordpress_client as _wpc  # noqa: E402
import services.authored_substrate as _sub  # noqa: E402

_orig_cp, _orig_wr = _wpc.create_post, _sub.write_revision
_orig_ls = _wpc.list_sites
_orig_tok = _pub._decrypted_wordpress_token
_wpc.create_post = _fake_create_post
_wpc.list_sites = _fake_list_sites
_sub.write_revision = _fake_write_revision
_pub._decrypted_wordpress_token = lambda auth: "tok"
try:
    receipt = asyncio.run(_pub.publish_post_to_wordpress(
        _MemberAuth(_store), path="operation/p/post.html", site_id="9", status="draft"))
finally:
    _wpc.create_post = _orig_cp
    _wpc.list_sites = _orig_ls
    _sub.write_revision = _orig_wr
    _pub._decrypted_wordpress_token = _orig_tok

check("the act returns the receipt row (platform, url, status)",
      receipt.get("platform") == "wordpress"
      and receipt.get("url", "").startswith("https://")
      and receipt.get("status") == "draft", str(receipt))
check("the receipt sidecar is _publish.yaml beside the post (ADR-254)",
      _captured.get("path") == "/workspace/operation/p/_publish.yaml",
      str(_captured.get("path")))
check("…written as the member's own act",
      _captured.get("authored_by") == "operator"
      and _captured.get("author_identity_uuid") == "00000000-0000-0000-0000-000000000001")
check("…and the body is a yaml LIST that appends (history, not overwrite)",
      (_captured.get("content") or "").lstrip().startswith("- "))
# D7 — the receipt records what the READER gets, not only what the API said.
check("D7: the receipt carries public reachability when known",
      receipt.get("publicly_readable") is False, str(receipt))
check("D7: …and the sidecar body carries it too",
      "publicly_readable: false" in (_captured.get("content") or ""),
      (_captured.get("content") or "")[:200])
# D8 — the receipt CITES the post it was made from.
check("D8: the receipt is derived_from the post (the provenance edge)",
      _captured.get("derived_from") == ["/workspace/operation/p/post.html"],
      str(_captured.get("derived_from")))

print("6. the connect surfaces tell the truth")
from services.connector_registry import CONNECTOR_REGISTRY  # noqa: E402
from services.connectors import connector_does  # noqa: E402
from integrations.core.oauth import OAUTH_CONFIGS, WRITE_SCOPE_MARKERS  # noqa: E402

check("wordpress is a live connector (BE registry)",
      CONNECTOR_REGISTRY.get("wordpress") == "live")
check("…mirrored in the FE registry",
      'provider: "wordpress"' in (ROOT / "web" / "lib" / "connectors" / "registry.tsx").read_text())
check("the OAuth config exists (global scope, own callback)",
      "wordpress" in OAUTH_CONFIGS
      and OAUTH_CONFIGS["wordpress"].scopes == ["global"]
      and OAUTH_CONFIGS["wordpress"].redirect_path == "/api/integrations/wordpress/callback")
check("the write-marker ledger has a deliberate entry (not an omission)",
      "wordpress" in WRITE_SCOPE_MARKERS and WRITE_SCOPE_MARKERS["wordpress"] is None)
_does = connector_does("wordpress") or {}
check("the facts: publishes on your click · never captures · agents never",
      "publish" in _does.get("writes", "")
      and "never captures" in _does.get("reads", "")
      and "your click" in _does.get("agents", ""))
check("the seam's target roster is the one home",
      PUBLISH_TARGETS == frozenset({"wordpress"}))

print("7. the FE door (blogger-only mount, three connect states)")
_surface = (ROOT / "web" / "components" / "authoring" / "StudioSurface.tsx").read_text()
check("StudioPublish mounts on the blogger desk alone",
      "app.slug === 'blogger' && artifactPath && (" in _surface
      and _surface.count("<StudioPublish") == 1)
_pub_fe = (ROOT / "web" / "components" / "authoring" / "StudioPublish.tsx").read_text()
check("the three connect states render distinctly",
      "Connect WordPress" in _pub_fe
      and "wordpress.com/start" in _pub_fe
      and "'ready'" in _pub_fe)
check("the copy states the phase (a) bound: never on a schedule",
      "publishes on a schedule" in _pub_fe)
check("the api client carries the two verbs",
      "wordpressSites" in (ROOT / "web" / "lib" / "api" / "client.ts").read_text())

print()
if FAILED:
    print(f"ADR-628 gate RED — {PASSED} passed, {len(FAILED)} failed")
    for f in FAILED:
        print(f"    - {f}")
    sys.exit(1)
print(f"ALL PASS — {PASSED} checks — ADR-628 phase (a) holds")
