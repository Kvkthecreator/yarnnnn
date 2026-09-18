"""ADR-635 — the connector directory is consumed, not authored; reach
attaches under the member's grant; a foreign write is the first proposal
producer. Script-style gate; falsified where it counts.

Run: cd api && python3 test_adr635_attached_connectors.py
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys

API = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(API)
sys.path.insert(0, API)

# The envelope is encrypted with the same Fernet key the hand-authored
# connectors use; a throwaway key makes the attach flow runnable offline.
from integrations.core.tokens import TokenManager  # noqa: E402

os.environ.setdefault("INTEGRATION_ENCRYPTION_KEY", TokenManager.generate_key())
os.environ.setdefault("OAUTH_STATE_SECRET", "test-secret")

_p = _f = 0


def _check(label, ok, detail=""):
    global _p, _f
    if ok:
        _p += 1; print(f"  ok   {label}")
    else:
        _f += 1; print(f"  FAIL {label}{(' — ' + detail) if detail else ''}")


def _read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# A chainable in-memory stand-in for the one table this seam touches.
# ---------------------------------------------------------------------------


class _Res:
    def __init__(self, data):
        self.data = data


class _Q:
    def __init__(self, store, op="select"):
        self.store, self.op, self.filters, self.payload, self._like = store, op, [], None, None

    def select(self, *_a, **_k):
        return self

    def eq(self, col, val):
        self.filters.append((col, val)); return self

    def like(self, col, pat):
        self._like = (col, pat.rstrip("%")); return self

    def order(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def insert(self, payload):
        self.op, self.payload = "insert", payload; return self

    def update(self, payload):
        self.op, self.payload = "update", payload; return self

    def _match(self, row):
        for col, val in self.filters:
            if row.get(col) != val:
                return False
        if self._like and not str(row.get(self._like[0], "")).startswith(self._like[1]):
            return False
        return True

    # The live table's NOT NULL set (migration 244 for connected_by, whose own
    # comment says the constraint exists "so a connect door that forgets the
    # stamp fails loudly instead of writing silent unattributable reach").
    # A fake that accepts any payload cannot see that class of defect: the
    # first driven attach 502'd on exactly this while the suite was 78/78
    # green. The fake now refuses what Postgres refuses.
    _NOT_NULL = ("user_id", "platform", "connected_by")

    def execute(self):
        if self.op == "insert":
            row = dict(self.payload); row.setdefault("id", f"row-{len(self.store) + 1}")
            row.setdefault("created_at", "2026-09-03T00:00:00+00:00")
            for col in self._NOT_NULL:
                if row.get(col) is None:
                    raise AssertionError(
                        f'null value in column "{col}" of relation '
                        f'"platform_connections" violates not-null constraint')
            self.store.append(row); return _Res([row])
        if self.op == "update":
            hit = [r for r in self.store if self._match(r)]
            for r in hit:
                r.update(self.payload)
            return _Res(hit)
        return _Res([dict(r) for r in self.store if self._match(r)])


class _Client:
    def __init__(self):
        self.rows: list[dict] = []

    def table(self, name):
        assert name == "platform_connections", name
        return _Q(self.rows)


class _Auth:
    def __init__(self, client, user_id="u1", caller_identity="member:u1 via claude-sonnet-5"):
        self.client, self.user_id, self.caller_identity = client, user_id, caller_identity
        self.workspace_id = "ws1"
        self.freddie_caller = False


from services import attached_connectors as ac  # noqa: E402

# ═══════════════════════════════════════════════════════════════════════════
print("§1 names are the ecosystem's, provider-legal, and round-trip by LOOKUP")
# ═══════════════════════════════════════════════════════════════════════════
_check("slug from the directory's short name", ac.slug_for("https://mcp.notion.com/mcp", "notion") == "notion")
_check("slug from a pasted URL is the host, sans mcp./www./tld",
       ac.slug_for("https://mcp.context7.com/mcp") == "context7", ac.slug_for("https://mcp.context7.com/mcp"))
_check("platform key is prefixed", ac.platform_key("notion") == "mcp:notion" and ac.is_attached_platform("mcp:notion"))
n = ac.lane_tool_name("notion", "notion-create-pages")
_check("lane name is mcp__{slug}__{tool}", n == "mcp__notion__notion-create-pages", n)
_check("lane name is provider-legal", re.fullmatch(r"[A-Za-z0-9_-]{1,64}", n) is not None)
long = ac.lane_tool_name("atlassian", "get_confluence_page_ancestors_with_full_body_and_history_expanded")
_check("a long tool name is cut + hashed under 64", len(long) <= 64 and long.startswith("mcp__atlassian__"), long)
_check("two long names stay distinct",
       ac.lane_tool_name("a", "x" * 80 + "1") != ac.lane_tool_name("a", "x" * 80 + "2"))
_check("the slug half parses; a foreign name does not",
       ac.slug_of_tool_name(n) == "notion" and ac.slug_of_tool_name("platform_slack_x") is None)

# ═══════════════════════════════════════════════════════════════════════════
print("§2 the attach flow, offline: discovery → registration → pending → active → empty aperture")
# ═══════════════════════════════════════════════════════════════════════════


class _Resp:
    def __init__(self, status, json_=None, headers=None, text=""):
        self.status_code, self._json, self.headers, self.text = status, json_, headers or {}, text

    def json(self):
        if self._json is None:
            raise ValueError("no json")
        return self._json


class _FakeHTTP:
    """The Notion shape, verbatim from the 2026-09-03 live probe."""
    calls: list = []

    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, **k):
        _FakeHTTP.calls.append(("post", url))
        if url == "https://mcp.notion.com/mcp":
            return _Resp(401, headers={"www-authenticate": 'Bearer realm="OAuth", resource_metadata="https://mcp.notion.com/.well-known/oauth-protected-resource/mcp"'})
        if url == "https://mcp.notion.com/register":
            return _Resp(201, {"client_id": "cid-1", "token_endpoint_auth_method": "none"})
        if url == "https://mcp.notion.com/token":
            return _Resp(200, {"access_token": "at-1", "refresh_token": "rt-1", "expires_in": 3600, "token_type": "Bearer"})
        if url == "https://anon.example/mcp":
            return _Resp(200, {"result": {}})
        return _Resp(404)

    async def get(self, url, **k):
        _FakeHTTP.calls.append(("get", url))
        if url == "https://mcp.notion.com/.well-known/oauth-protected-resource/mcp":
            return _Resp(200, {"resource": "https://mcp.notion.com/mcp", "authorization_servers": ["https://mcp.notion.com"], "scopes_supported": ["default"]})
        if url == "https://mcp.notion.com/.well-known/oauth-authorization-server":
            return _Resp(200, {"issuer": "https://mcp.notion.com", "authorization_endpoint": "https://mcp.notion.com/authorize", "token_endpoint": "https://mcp.notion.com/token", "registration_endpoint": "https://mcp.notion.com/register", "code_challenge_methods_supported": ["S256"]})
        return _Resp(404)


ac.httpx.AsyncClient = _FakeHTTP  # type: ignore[attr-defined]

found = _run(ac.discover("https://mcp.notion.com/mcp"))
_check("2a discovery follows WWW-Authenticate → PRM → AS metadata", found.get("auth") == "oauth" and found.get("registration_endpoint") == "https://mcp.notion.com/register", str(found))
anon = _run(ac.discover("https://anon.example/mcp"))
_check("2b an anonymous server is recognised as needing no sign-in", anon.get("auth") == "none")

client = _Client(); auth = _Auth(client)
os.environ["API_BASE_URL"] = "https://api.test"
started = _run(ac.begin_attach(auth, "https://mcp.notion.com/mcp", title="Notion", slug="notion", category="Knowledge base", redirect_to="/settings?settings.pane=connectors"))
_check("2c begin_attach registers a client and returns an authorize URL", started["attached"] is False and started["authorization_url"].startswith("https://mcp.notion.com/authorize?"), str(started)[:200])
_check("2d the authorize URL carries PKCE S256 + resource + our callback",
       all(k in started["authorization_url"] for k in ("code_challenge_method=S256", "resource=https", "api.test%2Fapi%2Fconnectors%2Fattach%2Fcallback", "state=")))
row = ac.load_row(client, "u1", "notion")
_check("2e the row is PENDING with an empty aperture and no token", row["status"] == "pending" and (row["metadata"]["aperture"] == {}) and ac._decrypt(row["credentials_encrypted"]).get("code_verifier"))

state = re.search(r"state=([^&]+)", started["authorization_url"]).group(1)
from urllib.parse import unquote
state = unquote(state)


async def _fake_list(server_url, envelope):
    return [
        {"name": "notion-search", "description": "search", "input_schema": {"type": "object"}, "annotations": {"readOnlyHint": True}},
        {"name": "notion-create-pages", "description": "create", "input_schema": {"type": "object", "properties": {"title": {"type": "string"}}}, "annotations": {}},
    ]


_REAL_LIST_SERVER_TOOLS = ac._list_server_tools
ac._list_server_tools = _fake_list  # type: ignore[assignment]
done = _run(ac.complete_attach(client, "code-1", state))
row = ac.load_row(client, "u1", "notion")
env = ac._decrypt(row["credentials_encrypted"])
_check("2f the callback lands the row ACTIVE with the token envelope + refresh",
       done["slug"] == "notion" and row["status"] == "active" and env.get("access_token") == "at-1" and row.get("refresh_token_encrypted"))
_check("2g the server's tools are listed on the row, with the hint carried",
       [t["name"] for t in row["metadata"]["tools"]] == ["notion-search", "notion-create-pages"] and row["metadata"]["tools"][0]["annotations"].get("readOnlyHint") is True)
_check("2h a fresh attach exposes NO tool (selection is consent, ADR-582)", row["metadata"]["aperture"] == {} and ac.attached_surface(client, "u1") == [])
_check("2i the callback redirect targets the connection's own page", done["redirect_to"] == "/settings?settings.pane=connectors")

# a stale state cannot re-complete
try:
    _run(ac.complete_attach(client, "code-2", state)); ok = False
except ValueError:
    ok = True
_check("2j a second callback on a landed row is refused", ok)

agent = _Auth(client, user_id="u1", caller_identity="specialist:researcher")
agent.headless = True
try:
    _run(ac.begin_attach(agent, "https://mcp.notion.com/mcp")); ok = False
except PermissionError:
    ok = True
_check("2k an AGENT cannot attach (ADR-577 composes)", ok)

# ═══════════════════════════════════════════════════════════════════════════
print("§3 the aperture: member-chosen, validated, and the ONLY thing that exposes a tool")
# ═══════════════════════════════════════════════════════════════════════════
for bad, why in (({"nope": "direct"}, "unknown tool"), ({"notion-search": "always"}, "unknown mode")):
    try:
        ac.set_aperture(auth, "notion", bad); ok = False
    except ValueError:
        ok = True
    _check(f"3a refuses {why} rather than storing it", ok)
ac.set_aperture(auth, "notion", {"notion-search": "direct", "notion-create-pages": "propose"})
surface = ac.attached_surface(client, "u1")
_check("3b the surface carries exactly the exposed tools with their modes",
       [(t["lane_name"], t["mode"]) for t in surface[0]["tools"]] == [("mcp__notion__notion-search", "direct"), ("mcp__notion__notion-create-pages", "propose")])
_check("3c the hint rides the surface for the member, never as a decision",
       surface[0]["tools"][0]["read_only_hint"] is True and surface[0]["tools"][1]["read_only_hint"] is False)
_check("3d categories derive from the surface", ac.reach_categories(surface) == {"Knowledge base"})
_check("3e aperture_mode: direct / propose / None for unlisted / None for foreign",
       ac.aperture_mode(client, "u1", "mcp__notion__notion-search") == "direct"
       and ac.aperture_mode(client, "u1", "mcp__notion__notion-create-pages") == "propose"
       and ac.aperture_mode(client, "u1", "mcp__notion__notion-delete") is None
       and ac.aperture_mode(client, "u1", "mcp__linear__anything") is None)
try:
    ac.set_aperture(agent, "notion", {}); ok = False
except PermissionError:
    ok = True
_check("3f an AGENT cannot set an aperture", ok)

# ═══════════════════════════════════════════════════════════════════════════
print("§4 the gate: three verdicts + the replay, at the ONE chokepoint")
# ═══════════════════════════════════════════════════════════════════════════
from services.primitives.permission import resolve_permission, PermissionDecision  # noqa: E402

d, r = _run(resolve_permission(auth, "mcp__notion__notion-search", {}))
_check("4a direct → APPLY", d == PermissionDecision.APPLY and r == "attached_direct", f"{d} {r}")
d, r = _run(resolve_permission(auth, "mcp__notion__notion-create-pages", {"title": "x"}))
_check("4b propose → QUEUE", d == PermissionDecision.QUEUE and r == "attached_propose", f"{d} {r}")
d, r = _run(resolve_permission(auth, "mcp__notion__notion-delete", {}))
_check("4c unlisted → DENY (fail closed)", d == PermissionDecision.DENY and r == "attached_tool_outside_aperture", f"{d} {r}")
d, r = _run(resolve_permission(auth, "mcp__notion__notion-create-pages", {"_proposal_id": "p1"}))
_check("4d an approved replay APPLIES without re-gating", d == PermissionDecision.APPLY and r == "approved_proposal_replay")
src = _read("api/services/primitives/permission.py")
_check("4e the branch sits BEFORE the non-Reviewer free-pass (a member's foreign write must not inherit it)",
       src.index("is_attached_tool(name)") < src.index('return PermissionDecision.APPLY, "non_freddie_caller"'))

# ═══════════════════════════════════════════════════════════════════════════
print("§5 dispatch: DENY is readable, QUEUE is the external-write proposal, APPLY reaches the server")
# ═══════════════════════════════════════════════════════════════════════════
from services.primitives import registry as reg  # noqa: E402

queued = {}


async def _fake_enqueue(auth_, name, input_, reason):
    queued.update({"name": name, "reason": reason, "preview": reg._write_effect_preview(auth_, name, input_)})
    return {"success": True, "queued": True, "proposal_id": "p-1", "family": "external-write"}


ran = {}


async def _fake_run(auth_, name, input_):
    ran.update({"name": name, "input": input_})
    return {"success": True, "text": "ok"}


reg._enqueue_platform_write_proposal = _fake_enqueue  # type: ignore[assignment]
_REAL_RUN_ATTACHED_TOOL = ac.run_attached_tool
ac.run_attached_tool = _fake_run  # type: ignore[assignment]
res = _run(reg.execute_primitive(auth, "mcp__notion__notion-delete", {}))
_check("5a DENY returns a refusal the model can read", res.get("error") == "attached_tool_denied" and "Settings" in res.get("message", ""))
res = _run(reg.execute_primitive(auth, "mcp__notion__notion-create-pages", {"title": "Q3"}))
_check("5b propose → the existing external-write enqueue", res.get("queued") is True and queued["name"] == "mcp__notion__notion-create-pages")
_check("5c the proposal preview names server + tool + arguments",
       queued["preview"]["server"] == "notion" and queued["preview"]["tool"] == "notion-create-pages" and "Q3" in queued["preview"]["preview"], str(queued["preview"]))
res = _run(reg.execute_primitive(auth, "mcp__notion__notion-search", {"q": "roadmap"}))
_check("5d direct → the server, under the member's turn", res.get("success") and ran["name"] == "mcp__notion__notion-search")
_check("5e the queue is not a second gate: QUEUE came from resolve_permission", queued["reason"] == "attached_propose")

# ═══════════════════════════════════════════════════════════════════════════
print("§6 the lane: payload, allowlist and prose from ONE surface (ADR-467 D4 holds)")
# ═══════════════════════════════════════════════════════════════════════════
from services.lane_runner import lane_tool_names, lane_tools_openai  # noqa: E402

base = lane_tool_names()
with_attached = lane_tool_names(False, None, surface)
_check("6a attached names append after the base, none without a surface",
       with_attached == base + ("mcp__notion__notion-search", "mcp__notion__notion-create-pages") and lane_tool_names(False, None, []) == base)
payload = [t["function"]["name"] for t in lane_tools_openai(False, None, surface)]
_check("6b the payload matches the allowlist exactly", payload == list(with_attached))
defs = {t["name"]: t for t in ac.attached_tool_defs(surface)}
_check("6c definitions carry the server's own schema and the mode",
       defs["mcp__notion__notion-create-pages"]["input_schema"]["properties"]["title"]["type"] == "string"
       and "queued as a proposal" in defs["mcp__notion__notion-create-pages"]["description"]
       and "Runs directly" in defs["mcp__notion__notion-search"]["description"])
sec = ac.frame_section(surface, "the member")
_check("6d the frame names the server, DIRECT and PROPOSE, and says a PROPOSE call does not run",
       "Notion" in sec and "DIRECT: mcp__notion__notion-search" in sec and "PROPOSE: mcp__notion__notion-create-pages" in sec and "does not run" in sec)
_check("6e no surface → no section (silence is honest here: the trio's section already says the edge)", ac.frame_section([], "m") == "")
lr = _read("api/services/lane_runner.py")
_check("6f both loop sites read the surface ONCE and hand it to payload + allowlist + frame",
       lr.count("_attached = attached_surface(auth.client, auth.user_id) if _reach else []") == 2
       and lr.count("attached=_attached,") == 2 and "frame_section(attached, member)" in lr)
_check("6g the skills index receives the reach categories from the same surface", "reach=set(reach_categories(attached or []))" in lr)

# ═══════════════════════════════════════════════════════════════════════════
print("§7 the directory is CONSUMED: provenance-stamped seed + live registry, never a hand list")
# ═══════════════════════════════════════════════════════════════════════════
from services import connector_directory as cd  # noqa: E402

seed = cd.load_seed()
_check("7a the seed names its upstream repo + commit + derivation", seed["source_repo"].startswith("https://github.com/anthropics/") and re.fullmatch(r"[0-9a-f]{40}", seed["source_commit"]) and seed["derived_by"].endswith("refresh_connector_directory.py"))
_check("7b every seed server is a remote https endpoint with a key", all(s["url"].startswith("https://") and s["key"] for s in seed["servers"]))
_check("7c the seed is non-trivial (the 2026-09-03 derivation carried 55)", len(seed["servers"]) >= 40, str(len(seed["servers"])))
_check("7d the refresh script exists and is the only writer", os.path.exists(os.path.join(API, "scripts/refresh_connector_directory.py")) and "DERIVED" in seed.get("note", ""))
hits = cd.search("linear", include_registry=False)
_check("7e search matches the seed by title/key/category", any(e["key"] == "linear" for e in hits))
cd.registry_search = lambda q, limit=20: [  # type: ignore[assignment]
    {"name": "x/linear-clone", "key": None, "title": "Linear clone", "description": "", "url": "https://mcp.linear.app/mcp", "category": None, "source": "registry"},
    {"name": "y/other", "key": None, "title": "Other", "description": "", "url": "https://mcp.other.example/mcp", "category": None, "source": "registry"},
]
merged = cd.search("linear")
_check("7f a registry hit on a seed host is deduped; a new host is appended after the seed",
       sum(1 for e in merged if "linear.app" in e["url"]) == 1 and merged[-1]["url"] == "https://mcp.other.example/mcp")
_check("7g the seed entry is found by URL so a pasted official URL keeps its key + category",
       (cd.seed_entry_for_url("https://mcp.linear.app/mcp") or {}).get("key") == "linear")
_check("7h categories are the seed's own vocabulary", "Project tracker" in cd.categories())

# ═══════════════════════════════════════════════════════════════════════════
print("§8 skills: `needs` scopes presentation; the strip is NAMED")
# ═══════════════════════════════════════════════════════════════════════════
from services import skills as sk  # noqa: E402

pub = """---
name: roadmap-update
description: Update the roadmap. Use when reprioritizing.
allowed-tools: [Read, Write]
model: claude-sonnet-5
argument-hint: "<initiative>"
compatibility: Requires a project tracker.
metadata:
  needs: [Project tracker]
---
# Roadmap update
body
"""
s = sk.parse_skill(pub)
_check("8a host-specific fields are stripped and NAMED", s["stripped"] == ["allowed-tools", "argument-hint", "model"], str(s["stripped"]))
_check("8b portable fields survive in metadata", s["metadata"].get("compatibility", "").startswith("Requires"))
_check("8c needs parsed as a category tuple", s["needs"] == ("Project tracker",))
_check("8d a kernel skill strips nothing", all(k["stripped"] == [] for k in sk._load_kernel().values()))
m = {"path": "skills/roadmap-update/SKILL.md", "description": s["description"], "title": "Roadmap", "apps": (), "needs": s["needs"]}
_check("8e reach None → offered (presentation never fails closed)", sk._applies_to(m, None, None))
_check("8f reach empty → withheld", not sk._applies_to(m, None, set()))
_check("8g reach matches → offered", sk._applies_to(m, None, {"Project tracker"}))
idx_off = sk.skills_index_section([m], app=None, reach=set())
idx_on = sk.skills_index_section([m], app=None, reach={"Project tracker"})
_check("8h the index withholds a needs-skill without reach and lists it with", "roadmap-update" not in idx_off and "roadmap-update" in idx_on)
_check("8i creating-skills teaches `needs`", "metadata.needs" in _read("api/services/skills/creating-skills/SKILL.md"))

# ═══════════════════════════════════════════════════════════════════════════
print("§9 the dead binding is gone; the client accepts header or no auth")
# ═══════════════════════════════════════════════════════════════════════════
_check("9a TrackForeign + foreign_read are deleted",
       not os.path.exists(os.path.join(API, "services/primitives/track_foreign.py")) and not os.path.exists(os.path.join(API, "services/foreign_read.py")))
_check("9b the registry no longer names it", "TrackForeign" not in _read("api/services/primitives/registry.py"))
try:
    from integrations.core.mcp_client import MCPClient  # noqa: E402

    _check("9c an empty token sends NO Authorization header; explicit headers win",
           MCPClient._auth_headers(None) == {} and MCPClient._auth_headers("", {"X-API-Key": "k"}) == {"X-API-Key": "k"} and MCPClient._auth_headers("t") == {"Authorization": "Bearer t"})
except ModuleNotFoundError:
    # The MCP SDK is py3.10+; under the 3.9 api venv the module cannot import
    # (the test_adr386 `_requires_mcp` precedent). Hold the rule statically.
    _mc = _read("api/integrations/core/mcp_client.py")
    _check("9c (static, SDK absent) an empty token sends NO Authorization header; explicit headers win",
           "if headers:\n            return dict(headers)" in _mc and "if access_token:" in _mc and "return {}" in _mc)
_check("9d the credential read goes through the ONE path (ADR-577)", "resolve_platform_credential(auth, platform_key(slug))" in _read("api/services/attached_connectors.py"))

# ═══════════════════════════════════════════════════════════════════════════
print("§10 yarnnn is a connector in the same directory; the card names no retired verb")
# ═══════════════════════════════════════════════════════════════════════════
card = _read("web/app/.well-known/mcp.json/route.ts")
_check("10a the discovery card enumerates no tools (the server's list is the truth)",
       "tools: [" not in card and not re.search(r'name:\s*"(remember|recall|trace)"', card))
plug = json.loads(_read("plugin/yarnnn/.mcp.json"))
_check("10b the plugin's server is the MCP URL", plug["mcpServers"]["yarnnn"]["url"] == "https://mcp.yarnnn.com" and plug["mcpServers"]["yarnnn"]["type"] == "http")
mp = json.loads(_read(".claude-plugin/marketplace.json"))
_check("10c the root marketplace points at the plugin dir that exists",
       mp["plugins"][0]["source"] == "./plugin/yarnnn" and os.path.exists(os.path.join(ROOT, "plugin/yarnnn/.claude-plugin/plugin.json")))
sj = json.loads(_read("docs/features/mcp/server.json"))
_check("10d server.json is registry-shaped with the same remote", sj["remotes"][0]["url"] == "https://mcp.yarnnn.com" and sj["$schema"].endswith("server.schema.json"))
_check("10e the plugin ships no skills (two verb vocabularies would be two copies)", not os.path.exists(os.path.join(ROOT, "plugin/yarnnn/skills")))

# ═══════════════════════════════════════════════════════════════════════════
print("§11 canon")
# ═══════════════════════════════════════════════════════════════════════════
adr = [f for f in os.listdir(os.path.join(ROOT, "docs/adr")) if f.startswith("ADR-635")]
_check("11a ADR-635 exists and declares its disposition in the first paragraph", bool(adr) and "TURN REACH" in _read(f"docs/adr/{adr[0]}").split("## 1.")[0])
for f, needle in (
    ("docs/adr/ADR-420-engine-breadth-vs-connector-breadth.md", "ADR-635"),
    ("docs/adr/ADR-585-turn-reach-the-members-own-connections.md", "ADR-635"),
    ("docs/adr/ADR-293-governance-operational-substrate-taxonomy.md", "ADR-635"),
    ("docs/adr/ADR-630-skills-are-files.md", "ADR-635"),
    ("docs/architecture/connectors.md", "Attached connectors"),
    ("docs/architecture/GLOSSARY.md", "Attached connector"),
    ("docs/architecture/ADR-LEDGER.md", "ADR-635"),
    ("docs/database/SCHEMA-NOTES.md", "mcp:{slug}"),
):
    path = os.path.join(ROOT, f)
    if not os.path.exists(path):
        cands = [x for x in os.listdir(os.path.join(ROOT, os.path.dirname(f))) if x.startswith(os.path.basename(f).split("-")[0] + "-" + os.path.basename(f).split("-")[1])]
        path = os.path.join(ROOT, os.path.dirname(f), cands[0]) if cands else path
    _check(f"11b {os.path.basename(path)} carries the amendment", os.path.exists(path) and needle in open(path, encoding="utf-8").read())

# ═══════════════════════════════════════════════════════════════════════════
print("§12 no dynamic registration is not a dead end (ADR-635, 2026-09-04)")
# ═══════════════════════════════════════════════════════════════════════════
# Eleven directory servers publish working authorize + token endpoints but NO
# registration_endpoint. begin_attach used to raise ("a pre-registered client
# is not supported yet") — a guess about what the provider would say, made on
# the member's behalf and always in the negative. Driven against those servers,
# most serve their authorize page to an unregistered client and defer client
# validation to sign-in. So: attempt it, and let the provider answer.


class _NoDCRHTTP(_FakeHTTP):
    async def get(self, url, **k):
        _FakeHTTP.calls.append(("get", url))
        if url == "https://mcp.notion.com/.well-known/oauth-protected-resource/mcp":
            return _Resp(200, {"resource": "https://mcp.notion.com/mcp",
                               "authorization_servers": ["https://mcp.notion.com"],
                               "scopes_supported": ["default"]})
        if url == "https://mcp.notion.com/.well-known/oauth-authorization-server":
            # Same server, minus the registration endpoint — the NO_DCR shape.
            return _Resp(200, {"issuer": "https://mcp.notion.com",
                               "authorization_endpoint": "https://mcp.notion.com/authorize",
                               "token_endpoint": "https://mcp.notion.com/token",
                               "code_challenge_methods_supported": ["S256"]})
        return _Resp(404)


ac.httpx.AsyncClient = _NoDCRHTTP  # type: ignore[attr-defined]

_c12 = _Client(); _a12 = _Auth(_c12)
# Caught, not propagated: the behaviour under test is precisely a REFUSAL, and
# an uncaught one aborts the run — every later check silently skipped, which
# reads as "not failing" rather than "never ran".
try:
    nodcr = _run(ac.begin_attach(_a12, "https://mcp.notion.com/mcp", title="Notion", slug="notion"))
except Exception as _exc:  # noqa: BLE001
    nodcr = {"attached": None, "authorization_url": "", "_refused": repr(_exc)}
_check("12a a server with no DCR still yields an authorize URL (no refusal)",
       nodcr["attached"] is False and nodcr["authorization_url"].startswith("https://mcp.notion.com/authorize?"),
       str(nodcr)[:200])
_check("12b it carries PKCE S256 like any other attach",
       "code_challenge_method=S256" in nodcr["authorization_url"])
_check("12c the unregistered client names US, it does not impersonate an app",
       f"client_id={ac._UNREGISTERED_CLIENT_ID}" in nodcr["authorization_url"],
       nodcr["authorization_url"][:160])
_row12 = ac.load_row(_c12, "u1", "notion")
_check("12d the row records that the client was unregistered",
       _row12["metadata"].get("unregistered_client") is True)

_c12b = _Client(); _a12b = _Auth(_c12b)
byo = _run(ac.begin_attach(_a12b, "https://mcp.notion.com/mcp", slug="notion",
                           client_id="member-own-id", client_secret="shh"))
_check("12e a member-supplied client id is used verbatim",
       "client_id=member-own-id" in byo["authorization_url"], byo["authorization_url"][:160])
_check("12f and the secret rides the pending envelope, never the URL",
       "shh" not in byo["authorization_url"]
       and ac._decrypt(ac.load_row(_c12b, "u1", "notion")["credentials_encrypted"]).get("client_secret") == "shh")

# The opt-out: a refusal NO member can resolve (partner agreement, domain
# allowlist, approved-vendor list) is the one case where listing manufactures a
# dead end. Everything else stays listed and is attempted.
from services import connector_directory as _cd  # noqa: E402

_listed = {e["url"] for e in _cd.search("", limit=300)}
for _hostname in ("mcp.squareup.com", "mcp.zoominfo.com", "mcp.figma.com"):
    _check(f"12g {_hostname} is opted out of the directory",
           not any(_hostname in u for u in _listed))
_check("12h a server that merely needs sign-in is still listed (slack, gong)",
       any("slack" in u for u in _listed) and any("gong" in u for u in _listed))
_check("12i the opt-out is keyed by HOST, so a renamed seed key cannot re-list it",
       _cd._opted_out("https://mcp.figma.com/anything") and not _cd._opted_out("https://mcp.linear.app/mcp"))

# ═══════════════════════════════════════════════════════════════════════════
print("§13 a 31-tool write-heavy server, driven end to end (ADR-635 am.1, 2026-09-18)")
# ═══════════════════════════════════════════════════════════════════════════
# The generic path was only ever exercised against Notion's handful. A commerce
# server (Shopify's shape) advertises ~31 tools, most of them WRITES, and
# attaches by header rather than OAuth. Driven here — attach, list, aperture,
# gate, dispatch — because reading it cannot prove it.
#
# The operator ruling this gate holds: THE APERTURE IS SOVEREIGN. An
# irreversible foreign write the member marked `direct` APPLIES. yarnnn does
# not classify tools it does not author, so there is no irreversible-write
# floor here and §13g asserts its ABSENCE, not its presence.

_READS_31 = ["get_shop", "list_products", "get_product", "list_orders", "get_order",
             "list_customers", "get_customer", "list_collections", "get_collection",
             "list_inventory_levels", "get_inventory_item", "list_fulfillments",
             "get_fulfillment", "list_discounts", "get_discount", "list_draft_orders",
             "get_draft_order", "search_products"]
_WRITES_31 = ["create_product", "update_product", "delete_product", "create_order",
              "cancel_order", "create_refund", "adjust_inventory", "create_discount",
              "delete_discount", "create_draft_order", "complete_draft_order",
              "create_fulfillment", "update_customer"]
_TOOLS_31 = (
    [{"name": n, "description": f"{n} on the shop.",
      "input_schema": {"type": "object", "properties": {"id": {"type": "string"}}},
      "annotations": {"readOnlyHint": True}} for n in _READS_31]
    + [{"name": n, "description": f"{n} on the shop.",
        "input_schema": {"type": "object", "properties": {"id": {"type": "string"}}},
        "annotations": {"readOnlyHint": False}} for n in _WRITES_31]
)
_check("13a the fixture is a real 31-tool write-heavy server", len(_TOOLS_31) == 31)

_SEEN_HEADERS: list = []
_TOOL_CALLS: list = []


class _MCPResult:
    def __init__(self, text, is_error=False):
        self.text, self.structured, self.is_error = text, None, is_error

    def source_ref(self):
        return "mcp://shop"


class _FakeMCPClient:
    def __init__(self):
        self.tools = list(_TOOLS_31)

    async def list_tools(self, url, headers=None):
        _SEEN_HEADERS.append(dict(headers or {}))
        return list(self.tools)

    async def call_tool(self, url, headers=None, tool_name=None, arguments=None):
        _TOOL_CALLS.append((tool_name, dict(arguments or {}), dict(headers or {})))
        return _MCPResult(f"{tool_name} ok")


_FAKE_MCP = _FakeMCPClient()
# The MCP SDK is py3.10+ and absent under the 3.9 api venv (the §9c precedent).
# Standing the module in is what lets `refresh_tools` / `run_attached_tool` —
# which import `get_mcp_client` at call time — be DRIVEN rather than read.
import types as _types  # noqa: E402

_mcp_mod = _types.ModuleType("integrations.core.mcp_client")
_mcp_mod.get_mcp_client = lambda: _FAKE_MCP
sys.modules["integrations.core.mcp_client"] = _mcp_mod
# §2 swapped `_list_server_tools` wholesale for the Notion pair; from here on
# the REAL one runs, so the auth headers it builds are driven, not assumed.
ac._list_server_tools = _REAL_LIST_SERVER_TOOLS  # type: ignore[assignment]
# Likewise §5 swapped `run_attached_tool` for a recorder; §13 DRIVES the real
# dispatch, so a green here cannot be a fake answering its own question.
ac.run_attached_tool = _REAL_RUN_ATTACHED_TOOL  # type: ignore[assignment]


class _ShopHTTP(_FakeHTTP):
    """A header-authenticated server (401 bare, 200 with the key) and an
    anonymous one. Neither publishes OAuth metadata."""

    async def post(self, url, **k):
        hdrs = k.get("headers") or {}
        if url == "https://shopify.example/mcp":
            return _Resp(200, {"result": {}}) if hdrs.get("X-Shopify-Access-Token") else _Resp(401, headers={})
        if url == "https://anon-shop.example/mcp":
            return _Resp(200, {"result": {}})
        return await super().post(url, **k)

    async def get(self, url, **k):
        if "shopify.example" in url or "anon-shop.example" in url:
            return _Resp(404)
        return await super().get(url, **k)


ac.httpx.AsyncClient = _ShopHTTP  # type: ignore[attr-defined]

_c13 = _Client()
_a13 = _Auth(_c13)
_att = _run(ac.begin_attach(_a13, "https://shopify.example/mcp", title="Shopify",
                            category="Commerce", header_name="X-Shopify-Access-Token",
                            header_value="shpat_secret"))
_check("13b a header-authenticated server attaches with NO redirect",
       _att["attached"] is True and _att["authorization_url"] is None and _att["slug"] == "shopify", str(_att))
_pv13 = ac.public_view(ac.load_row(_c13, "u1", "shopify"))
_check("13c all 31 tools land on the row", len(_pv13["tools"]) == 31, str(len(_pv13["tools"])))
_check("13d a fresh attach at 31 tools still exposes NOTHING",
       _pv13["exposed"] == 0 and _pv13["aperture"] == {}, str(_pv13["aperture"]))
_check("13e the member's header rode the tools/list call, and never reaches a surface",
       _SEEN_HEADERS[-1].get("X-Shopify-Access-Token") == "shpat_secret" and "shpat_secret" not in str(_pv13))
_check("13f 31 distinct provider-legal lane names",
       len({t["lane_name"] for t in _pv13["tools"]}) == 31
       and all(re.fullmatch(r"[A-Za-z0-9_-]{1,64}", t["lane_name"]) for t in _pv13["tools"]))
_check("13g the read-only HINT round-trips per tool and groups nothing else",
       sum(1 for t in _pv13["tools"] if t["read_only_hint"]) == 18)

from services.primitives.permission import (  # noqa: E402
    resolve_permission as _rp, PermissionDecision as _PD,
)

ac.set_aperture(_a13, "shopify", {"create_refund": "direct", "get_order": "direct",
                                  "cancel_order": "propose"})
_d, _r = _run(_rp(_a13, "mcp__shopify__create_refund", {"id": "o1"}))
_check("13h OPERATOR RULING — an IRREVERSIBLE foreign write marked `direct` APPLIES; "
       "there is no irreversible-write floor for an attached connector",
       _d == _PD.APPLY and _r == "attached_direct", f"{_d} {_r}")
_d, _r = _run(_rp(_a13, "mcp__shopify__cancel_order", {"id": "o1"}))
_check("13i `propose` QUEUES", _d == _PD.QUEUE and _r == "attached_propose", f"{_d} {_r}")
_d, _r = _run(_rp(_a13, "mcp__shopify__delete_product", {"id": "p1"}))
_check("13j one of the other 28 — unlisted — DENIES",
       _d == _PD.DENY and _r == "attached_tool_outside_aperture", f"{_d} {_r}")
_check("13k the surface carries ONLY the 3 chosen of 31",
       len(ac.attached_surface(_c13, "u1")[0]["tools"]) == 3)
_out13 = _run(ac.run_attached_tool(_a13, "mcp__shopify__create_refund", {"id": "o1", "_proposal_id": "p"}))
_check("13l dispatch reaches the server under the member's header, `_`-args stripped",
       _out13["success"] and _TOOL_CALLS[-1][0] == "create_refund"
       and _TOOL_CALLS[-1][1] == {"id": "o1"}
       and _TOOL_CALLS[-1][2].get("X-Shopify-Access-Token") == "shpat_secret", str(_TOOL_CALLS[-1:]))

# The anonymous arm of the same server shape.
_c13b = _Client()
_a13b = _Auth(_c13b)
_att2 = _run(ac.begin_attach(_a13b, "https://anon-shop.example/mcp", title="AnonShop"))
_check("13m an anonymous 31-tool server attaches the same way",
       _att2["attached"] is True and _att2["auth"] == "none", str(_att2))
_check("13n and its tools/list carried NO auth header at all", _SEEN_HEADERS[-1] == {}, str(_SEEN_HEADERS[-1]))
ac.set_aperture(_a13b, "anon-shop", {"list_products": "direct"})
_check("13o anonymous dispatch works",
       _run(ac.run_attached_tool(_a13b, ac.lane_tool_name("anon-shop", "list_products"), {}))["success"])

# ═══════════════════════════════════════════════════════════════════════════
print("§14 the aperture drifts when the server renames a tool — and SAYS SO (am.1)")
# ═══════════════════════════════════════════════════════════════════════════
# `metadata.tools` is a snapshot and the aperture is keyed on tool NAMES. When
# a server renames or withdraws a tool the member's consent for it evaporates
# and the tool starts refusing. Failing closed is right; failing closed in
# SILENCE is the defect — the member reads a working connection while an agent
# is refused a tool they believe they granted.
_FAKE_MCP.tools = [t for t in _TOOLS_31 if t["name"] != "create_refund"] + [
    {"name": "refund_create", "description": "renamed", "input_schema": {"type": "object"},
     "annotations": {"readOnlyHint": False}}]
_run(ac.refresh_tools(_a13, "shopify"))
_pv14 = ac.public_view(ac.load_row(_c13, "u1", "shopify"))
_check("14a the withdrawn tool is still PRUNED from the aperture (fail closed, unchanged)",
       "create_refund" not in _pv14["aperture"])
_d, _r = _run(_rp(_a13, "mcp__shopify__create_refund", {"id": "o1"}))
_check("14b ...and it now DENIES where it used to apply", _d == _PD.DENY, f"{_d} {_r}")
_check("14c the drop is NAMED, not silent: drift.withdrawn",
       (_pv14["drift"] or {}).get("withdrawn") == ["create_refund"], str(_pv14["drift"]))
_check("14d the new name is reported as appeared and is NOT allowed by it",
       "refund_create" in (_pv14["drift"] or {}).get("appeared", [])
       and _pv14["aperture"].get("refund_create") is None)
_check("14e the fact is DERIVED onto the row, not an event and not a notification",
       "drift" in (ac.load_row(_c13, "u1", "shopify")["metadata"] or {}))
# `"drift" in src` is true from a type import, a comment, or a dead binding
# (the class this repo keeps re-finding). Anchor on the CONDITION each surface
# renders under, in comment-stripped source, and require it once.
def _strip_ts(src):
    src = re.sub(r"/\*[\s\S]*?\*/", "", src)
    return re.sub(r"^\s*//.*$", "", src, flags=re.M)


_sub_src = _strip_ts(_read("web/components/settings/AttachedConnectorSubsurface.tsx"))
_reach_src = _strip_ts(_read("web/components/reach/ReachConnected.tsx"))
_check("14f the connection's own page RENDERS the withdrawal under a live condition "
       "(the whole JSX guard, so a `{false &&` short-circuit reds)",
       _sub_src.count("{row.drift && (row.drift.withdrawn.length > 0") == 1
       and "row.drift.withdrawn.join" in _sub_src)
_check("14f-2 and Reach → Connected names it on the row the member already reads",
       _reach_src.count("{attached && (i.drift?.withdrawn.length || i.drift?.appeared.length) ? (") == 1
       and "i.drift.withdrawn.join" in _reach_src)
_check("14g the LIST route serves it on attached rows only",
       'drift=(metadata.get("drift") or None) if attached else None' in _read("api/routes/integrations.py"))
ac.set_aperture(_a13, "shopify", {"get_order": "direct"})
_check("14h the member's SAVE is the acknowledgement — nothing to dismiss",
       ac.public_view(ac.load_row(_c13, "u1", "shopify"))["drift"] is None)
# 14i must not be vacuous: PLANT a drift record, then refresh against a server
# that moved nothing, and require the stale record GONE. Refreshing over an
# already-clear row would pass whether or not the clearing branch exists.
# json round-trip, not dict(): the in-memory client hands back a LIVE reference
# and a shallow copy would plant the record by aliasing rather than by the
# write — a fixture artifact that would make 14i-pre unfalsifiable.
_md14 = json.loads(json.dumps(ac.load_row(_c13, "u1", "shopify")["metadata"] or {}))
_md14["drift"] = {"withdrawn": ["stale"], "appeared": [], "at": "2026-01-01T00:00:00+00:00"}
ac._upsert_row(_c13, "u1", "shopify", {"metadata": _md14})
_check("14i-pre the stale record is planted", ac.public_view(ac.load_row(_c13, "u1", "shopify"))["drift"] is not None)
_run(ac.refresh_tools(_a13, "shopify"))
_check("14i a refresh that finds nothing moved CLEARS a stale record",
       ac.public_view(ac.load_row(_c13, "u1", "shopify"))["drift"] is None)

# ═══════════════════════════════════════════════════════════════════════════
print("§15 the aperture editor is tolerable at 31 tools WITHOUT weakening consent")
# ═══════════════════════════════════════════════════════════════════════════
_ed_raw = _read("web/components/settings/AttachedConnectorSubsurface.tsx")
# Strip comments before any substring check: the file's own doc block NAMES
# the shortcuts it refuses ("no 'allow all writes'"), and a check that reads
# the prose passes on the documentation rather than on the code (the recurring
# class this repo has been bitten by). Comments out, JSX text kept — the copy
# a member reads IS shipped behavior.
_ed = re.sub(r"/\*[\s\S]*?\*/", "", _ed_raw)
_ed = re.sub(r"^\s*//.*$", "", _ed, flags=re.M)
_check("15z the comment strip actually removed the doc block (else 15d is vacuous)",
       'allow all writes' in _ed_raw and 'allow all writes' not in _ed)
_check("15a a filter exists for finding one tool among many", 'type="search"' in _ed and "setFilter" in _ed)
# Counted at the DECIDING site: a mention of `read_only_hint` is also true of
# the per-row badge, and `groups` is also true of an unused binding. The split
# is the two complementary filters plus the render that walks them.
_check("15b the list is SPLIT by the server's read-only hint, and the split is RENDERED",
       "shown.filter((t) => t.read_only_hint)" in _ed
       and "shown.filter((t) => !t.read_only_hint)" in _ed
       and re.search(r"groups\.map\(\(g\)", _ed) is not None)
_check("15c a bulk set exists and is scoped to what is on screen", "setGroup(names" in _ed)
_check("15d ...and it is a member GESTURE per mode, never a 'select all writes' shortcut",
       "Select all" not in _ed and "allow all" not in _ed.lower())
# The three deciding rules, each falsifiable by a single edit:
_check("15e NO mode is preselected: the draft still reads the SERVED mode, defaulting off",
       'next[t.name] = (t.mode ?? "off") as Mode' in _ed)
_check("15f the row default in the list is likewise off", 'draft[t.name] ?? "off"' in _ed)
_check("15g the hint is shown BESIDE the choice and decides nothing — no branch reads it "
       "to pick a mode (ADR-635 D4: readOnlyHint is a hint)",
       not re.search(r'read_only_hint\s*\?\s*"(direct|propose)"', _ed)
       and not re.search(r'read_only_hint\s*&&\s*set(Draft|Group)', _ed))
_check("15y the refresh toast says WHAT it found, from the same drift record — "
       "'Tool list updated' was true whether or not a tool the member allowed vanished",
       _ed.count("success: (res) => {") == 1
       and "const d = res?.connector?.drift;" in _ed
       and "Tool list updated" not in _ed
       and "Nothing changed on this server" in _ed)
_check("15h a bulk gesture is still a DRAFT — only Save writes",
       "api.connectors.setAperture" in _ed and _ed.count("api.connectors.setAperture") == 1)

print(f"\n{_p} passed, {_f} failed")
sys.exit(1 if _f else 0)
