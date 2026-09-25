"""ADR-668 — a website is a platform; the browser is its transport.

Run: cd api && python3 test_adr668_a_website_is_a_platform.py

Script-shaped (the house form): prints each check, a count, exits 1 on any
failure. The lane arms are DRIVEN — the real lane loop with a fake engine —
and the scope grammar is driven in node against `extension/policy.js`; the
rest reads source. §8's arms read the ADR's Status line and hold the state
that matches it: while Proposed, nothing of §8 is built ahead of the ruling;
on Accepted, each item is asserted.
"""

from __future__ import annotations

import asyncio
import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("SUPABASE_URL", "http://localhost")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "x")

ROOT = Path(__file__).resolve().parent.parent
PASS = 0
FAIL = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name} {('— ' + detail) if detail else ''}")


def read(rel: str) -> str:
    return (ROOT / rel).read_text()


ADR = read("docs/adr/ADR-668-a-website-is-a-platform-the-browser-is-its-transport.md")
STATUS = (re.search(r"\*\*Status\*\*: \*\*(Proposed|Accepted)", ADR) or [None, ""])[1]
BG = read("extension/background.js")
POLICY = read("extension/policy.js")
HANDS = read("web/lib/shell/hands.ts")
LANE = read("api/services/lane_runner.py")
CT = read("api/services/client_tools.py")
RUNS = read("api/services/runs.py")
E2E = read("extension/e2e/run.mjs")
SERVER = read("api/mcp_server/server.py")
COMPOSE = read("api/services/mcp_composition.py")

from services import client_tools as ct  # noqa: E402
from services import runs as runs_mod  # noqa: E402

print(f"ADR-668 status: {STATUS or 'UNREADABLE'}")
check("the ADR names its gate", "api/test_adr668_a_website_is_a_platform.py" in ADR and STATUS in ("Proposed", "Accepted"))

# ═════════════════════════════════════════════════════════════════════════════
print("\nF9 the timeout receipt names the executor that exists")
# ═════════════════════════════════════════════════════════════════════════════
_no_answer = re.search(r'"error": "no_answer",\s*"receipt": "([^"]+)"', CT)
check("the no_answer receipt says the browser did not answer, not the desktop app",
      bool(_no_answer) and "desktop app" not in _no_answer.group(1)
      and _no_answer.group(1).startswith("The browser did not answer in time"),
      _no_answer.group(1) if _no_answer else "no receipt found")

# ═════════════════════════════════════════════════════════════════════════════
print("\nD4/D8 driven through the real lane loop — the frame carries the scope, the receipt the address")
# ═════════════════════════════════════════════════════════════════════════════
from services import lane_runner as lr  # noqa: E402
from services import model_router  # noqa: E402


class _Routed:
    def __init__(self, text="", tool_calls=None):
        self.text = text
        self.tool_calls = tool_calls or []
        self.usage = {"input_tokens": 1, "output_tokens": 1}
        self.ledger_model = "fake"
        self.finish_reason = "stop"
        self.raw_assistant_message = {"role": "assistant", "content": text, "tool_calls": []}


async def _drive(url: str, *, sites: tuple, answer: dict):
    calls = {"n": 0}

    async def fake_stream(model, messages, **kw):
        calls["n"] += 1
        if calls["n"] == 1:
            yield ("done", _Routed(tool_calls=[{"id": "tc1", "name": "BrowserOpen", "arguments": {"url": url}}]))
        else:
            yield ("delta", "done.")
            yield ("done", _Routed(text="done."))

    saved = (model_router.lanes_enabled, model_router.route_completion_stream, lr.resolve_turn_reach,
             lr.build_lane_conventions, lr.unpriced_lane_model, lr._resolve_byok_key)
    model_router.lanes_enabled = lambda: True
    model_router.route_completion_stream = fake_stream
    lr.resolve_turn_reach = lambda *a, **k: (False, ())
    lr.build_lane_conventions = lambda *a, **k: "system"
    lr.unpriced_lane_model = lambda m: False
    lr._resolve_byok_key = lambda a, m: None

    class _Auth:
        user_id = "member-a"
        client = None
        workspace_id = None

    events = []
    try:
        async for kind, payload in lr.run_lane_turn_stream(
            _Auth(), model="anthropic/claude-sonnet-5", history=[], user_message="run it",
            client_tools=ct.offered(None, ["browser"], "extension/0.1.2"), browser_sites=sites,
        ):
            events.append((kind, payload))
            if kind == "client_tool":
                ct.resolve(payload["nonce"], payload["call_id"], "member-a", dict(answer))
    finally:
        (model_router.lanes_enabled, model_router.route_completion_stream, lr.resolve_turn_reach,
         lr.build_lane_conventions, lr.unpriced_lane_model, lr._resolve_byok_key) = saved
    return events


_answer = {"success": True, "receipt": "Opened “Shop” (shop.example.com).", "url": "https://shop.example.com/x",
           "record": {"act": "opened", "subject": "Shop", "changed": True}}
_ev = asyncio.run(_drive("https://shop.example.com/x", sites=("example.com",), answer=_answer))
_frame = next((p for k, p in _ev if k == "client_tool"), {})
_rcpt = next((p for k, p in _ev if k == "receipt"), {})
check("⭐ a declared run's frame carries its sites, so the executor can refuse where the tab is",
      _frame.get("sites") == ["example.com"], str(_frame))
check("⭐ the receipt carries where the tab was when the act ended",
      _rcpt.get("url") == "https://shop.example.com/x", str(_rcpt))
_ev = asyncio.run(_drive("https://anything.org", sites=(), answer={"success": True, "receipt": "Opened."}))
_frame = next((p for k, p in _ev if k == "client_tool"), {})
_rcpt = next((p for k, p in _ev if k == "receipt"), {})
check("a chat turn's frame carries no scope", "sites" not in _frame, str(_frame))
check("…and a receipt with no address says so (`url` present, None)", "url" in _rcpt and _rcpt["url"] is None, str(_rcpt))
check("the server still refuses what BrowserOpen names off-list (two doors)",
      "_outside = _outside_scope(name, args, browser_sites)" in LANE and "site_not_in_scope" in LANE)

_tr = runs_mod.TurnRun(user_id="member-a", workspace_id=None, lane_id="lane-1")
_tr.on_receipt({"name": "BrowserOpen", "text": "Opened.", "ok": True,
                "record": {"act": "opened", "subject": "Shop", "changed": True}, "url": "https://shop.example.com/x"})
check("the run's step keeps the address", _tr.steps[0].get("url") == "https://shop.example.com/x", str(_tr.steps))
_record = runs_mod.render_record(
    {"started_at": "2026-09-25T01:00:00+00:00", "trigger": "manual", "state": "done", "outcome": "wrote",
     "revision_id": "abcdef12", "steps": [
         {"text": "Opened “Shop”.", "ok": True, "url": "https://shop.example.com/x"},
         {"text": "Read “Shop”.", "ok": True},
     ]},
    topic="prices", target="prices.csv", member_name="Kevin")
check("the record renders a step's address, and none where the executor gave none",
      "1. Opened “Shop”. — https://shop.example.com/x" in _record and "2. Read “Shop”.\n" in _record, _record)
check("RunOut says a step carries url", "`url`" in read("api/routes/runs.py") and "ADR-668 D4" in read("api/routes/runs.py"))

# ═════════════════════════════════════════════════════════════════════════════
print("\nD8 the scope holds at the executor — the page, the extension, the instrument")
# ═════════════════════════════════════════════════════════════════════════════
check("the page's frame type names the scope", "sites?: string[]" in HANDS)
check("the page forwards the scope to the extension AND to the host",
      HANDS.count("...(sites ? { sites } : {})") == 2
      and '{ type: "act", tool: frame.name, args, ...(sites ? { sites } : {}) }' in HANDS
      and '"browser_act", { tool: frame.name, args, ...(sites ? { sites } : {}) }' in HANDS)

_node = subprocess.run(
    ["node", "--input-type=module", "-e",
     "import('./extension/policy.js').then(m => process.stdout.write(JSON.stringify(["
     "m.withinScope('shop.example.com', ['example.com']),"
     "m.withinScope('example.com', ['example.com']),"
     "m.withinScope('evil-example.com', ['example.com']),"
     "m.withinScope('example.com.evil.net', ['example.com']),"
     "m.withinScope('anything.org', []),"
     "m.withinScope('anything.org', undefined)])))"],
    cwd=str(ROOT), capture_output=True, text=True,
)
_grammar = json.loads(_node.stdout or "null") if _node.returncode == 0 else None
check("⭐ `withinScope` mirrors the server's site grammar — the site and its subdomains, never a lookalike, no scope = no check",
      _grammar == [True, True, False, False, True, True], f"{_grammar} {_node.stderr[-200:]}")

_gate = re.search(r'async function gate\(url, sites = \[\], where = "open"\) \{(.*?)\n\}', BG, re.S)
check("the extension's gate takes the run's scope and refuses it BEFORE the member's lists or a consent question",
      bool(_gate) and "withinScope(host, sites)" in _gate.group(1)
      and _gate.group(1).index("withinScope(host, sites)") < _gate.group(1).index("await settings()")
      and '"outside", host, here' in _gate.group(1))
check("the refusal names the site the work may not use, on open and where the tab is",
      bool(_gate) and "this work may open only" in _gate.group(1) and "has left this work's sites" in _gate.group(1))
check("every act threads the scope — perform, both doors, each act",
      'export async function perform(tool, args = {}, sites = [])' in BG
      and BG.count("perform(msg.tool, msg.args, msg.sites)") == 2
      and "return await open(String(args.url || \"\").trim(), sites);" in BG
      and "return await read(sites);" in BG and "return await back(sites);" in BG
      and BG.count(", sites);\n}") >= 3)
check("back says where it went; a refusal carries the tab's address",
      "success: navigated, url: now.url," in BG and "...(url ? { url } : {})" in BG)
_manifest = json.loads(read("extension/manifest.json"))
check("the extension that performs it is 0.1.2 or later",
      tuple(int(x) for x in _manifest["version"].split(".")) >= (0, 1, 2), _manifest["version"])
check("the server's floor is NOT raised by this ADR — an older extension is still offered the tools, gated as before",
      ct._extension_meets("extension/0.1.1", ct.EXTENSION_MIN_VERSION) and "EXTENSION_MIN_VERSION` stays `0.1.0`" in ADR)
for _arm in (
    "each act says where the tab was when it ended",
    "an open inside the run's sites goes through",
    "an open outside them is refused as `outside`, naming the site, with no consent question",
    "an act on a tab that has left the run's sites is refused where the tab IS, with its address",
    "a chat turn carries no scope and is not scoped",
):
    check(f"the e2e instrument drives: {_arm}", _arm in E2E)
check("the e2e instrument hands the scope with the act", "...(s ? { sites: s } : {})" in E2E)

# ═════════════════════════════════════════════════════════════════════════════
print("\nD7 runs are readable outside a lane — the `runs` verb")
# ═════════════════════════════════════════════════════════════════════════════
from services import mcp_scopes as sc  # noqa: E402

_roster: set = set()
for _node_ in ast.walk(ast.parse(SERVER)):
    _targets = [_node_.target] if isinstance(_node_, ast.AnnAssign) else (list(_node_.targets) if isinstance(_node_, ast.Assign) else [])
    if any(isinstance(t, ast.Name) and t.id == "_INTEROP_VERBS" for t in _targets):
        for _elt in getattr(_node_.value, "elts", []):
            _parts = getattr(_elt, "elts", [])
            if _parts and isinstance(_parts[0], ast.Constant):
                _roster.add(_parts[0].value)
check("`runs` is on the interop roster", "runs" in _roster, str(sorted(_roster)))
check("`runs` is a files:read verb — a token that may read the files may read what the agents did",
      sc.VERB_SCOPES.get("runs") == sc.SCOPE_READ and "runs" in sc.allowed_verbs([sc.SCOPE_READ]))
_tool = re.search(r"@mcp\.tool\((.*?)\)\nasync def runs\(", SERVER, re.S)
check("the tool is registered read-only and passes its verb to the one auth door",
      bool(_tool) and "readOnlyHint=True" in _tool.group(1)
      and 'resolve_request_client(verb="runs")' in SERVER and '_present("runs", result' in SERVER)
check("the tool declares an output schema (a schema-less verb reads as a warning on ChatGPT's panel)",
      '"runs": {' in SERVER[SERVER.index("_OUTPUT_SCHEMAS = {"):])
_fn = COMPOSE[COMPOSE.index("async def compose_runs("):COMPOSE.index("def _portable_run(")]
check("compose_runs reads through the caller's client under the connection's workspace binding — never the service client",
      "list_runs(auth.client, ws" in _fn and "get_service_client" not in _fn
      and 'effective_workspace_id(auth.user_id, getattr(auth, "workspace_id", None))' in _fn)
check("the consent sentence for the read tier says so, in the server's words and the hub's",
      "runs" in sc._GRANT_SENTENCES[sc.SCOPE_READ] and sc._LEGACY_SENTENCES[0] == sc._GRANT_SENTENCES[sc.SCOPE_READ]
      and json.loads(read("web/messages/en.json"))["marketing"]["developers"]["scope"]["read"] == sc._GRANT_SENTENCES[sc.SCOPE_READ])


class _Q:
    def __init__(self, rows):
        self._rows = rows

    def __getattr__(self, _name):
        return lambda *a, **k: self

    def execute(self):
        return type("R", (), {"data": self._rows})()


class _Client:
    def __init__(self, rows):
        self._rows = rows

    def table(self, _name):
        return _Q(self._rows)


async def _compose():
    from services import mcp_composition as mc, principal_display as pd, workspace_context as wc
    saved = (pd.resolve_member_names, wc.effective_workspace_id)
    pd.resolve_member_names = lambda client, ids: {"u1": "Kevin"}
    wc.effective_workspace_id = lambda uid, explicit=None: "ws-1"

    class _Auth:
        user_id = "u1"
        workspace_id = "ws-1"
        client = _Client([{
            "id": "r1", "workspace_id": "ws-1", "user_id": "u1", "lane_id": "lane-secret", "kind": "browser",
            "trigger": "chat", "state": "done", "outcome": None, "topic": None, "revision_id": "rev1",
            "record_path": None, "cost_usd": 0.17, "started_at": "t0", "ended_at": "t1",
            "steps": [{"name": "BrowserOpen", "text": "Opened “Shop”.", "ok": True, "at": "t0",
                       "record": {"act": "opened", "subject": "Shop", "changed": True}, "url": "https://shop.example.com/"}],
        }])

    try:
        return await mc.compose_runs(auth=_Auth(), limit=5)
    finally:
        pd.resolve_member_names, wc.effective_workspace_id = saved


_res = asyncio.run(_compose())
_run = (_res.get("runs") or [{}])[0]
_step = (_run.get("steps") or [{}])[0]
check("⭐ a run crosses the boundary boundary-safe: a display name, no member id, no lane id",
      _res.get("success") and _run.get("member") == "Kevin" and "user_id" not in _run and "lane_id" not in _run
      and "lane-secret" not in json.dumps(_res), json.dumps(_run)[:300])
check("⭐ each step is the portable shape — {at, act, url, subject, changed, ok, text} (+ tool)",
      set(_step) == {"at", "act", "url", "subject", "changed", "ok", "text", "tool"}
      and _step["act"] == "opened" and _step["url"] == "https://shop.example.com/" and _step["changed"] is True,
      json.dumps(_step))
check("what a run wrote is a revision id, for `open` and `history` to follow", _run.get("wrote") == "rev1")

for _rel, _needle in (
    ("docs/features/mcp/tool-contracts.md", "## `runs`"),
    ("docs/features/mcp/README.md", "| `runs` |"),
    ("docs/features/mcp/CONNECTING.md", "history · runs · share"),
    ("docs/architecture/SERVICE-MODEL.md", "· runs ·"),
    ("docs/gitbook/api-reference/mcp-tools.md", "## `runs`"),
    ("docs/gitbook/integrations/mcp-connector.md", "| `runs` |"),
    ("web/lib/openapi.ts", 'name: "runs",'),
    ("web/components/marketing/DevelopersPageBody.tsx", '{ name: "runs", kind: "read" }'),
):
    check(f"the roster copy names it — {_rel}", _needle in read(_rel))
for _loc in ("en", "ko"):
    check(f"the developers hub words it — {_loc}",
          "runs" in json.loads(read(f"web/messages/{_loc}.json"))["marketing"]["developers"]["verb"])

# ═════════════════════════════════════════════════════════════════════════════
print("\n§5 the refusals hold")
# ═════════════════════════════════════════════════════════════════════════════
_mig = "\n".join(p.read_text() for p in (ROOT / "supabase" / "migrations").glob("*.sql"))
check("no `sites` / `browser_platforms` table — the roster is derived",
      not re.search(r"create\s+table\s+(if\s+not\s+exists\s+)?(public\.)?(sites|browser_platforms)\b", _mig, re.I))
_code = "\n".join(p.read_text() for p in (ROOT / "api" / "services").rglob("*.py"))
check("no `WORKFLOW.md` — the how is keyed by site, not by declaration", "WORKFLOW.md" not in _code)
_ext_code = re.sub(r"//[^\n]*|/\*.*?\*/", "", BG + read("extension/page.js"), flags=re.S)  # comments may name a site; code may not
check("no per-site code in the extension — five acts, whatever the site",
      not re.search(r"shopify|twitter|x\.com|linkedin|notion|instagram", _ext_code, re.I))

# ═════════════════════════════════════════════════════════════════════════════
print("\nthe canon points where it should")
# ═════════════════════════════════════════════════════════════════════════════
check("ADR-665 carries F4 at its head — the sentence was false when written",
      "ADR-668" in read("docs/adr/ADR-665-browser-workflows.md") and "false when written" in read("docs/adr/ADR-665-browser-workflows.md"))
_666 = read("docs/adr/ADR-666-the-run.md")
check("ADR-666 §3 no longer owes the extension-side check, and D2's steps carry url",
      "The extension-side check is owed with the next extension release" not in _666
      and "Closed by ADR-668 D8" in _666 and "`url` — where the tab was" in _666)
check("ADR-664 D5, ADR-630 D3 and ADR-667 D1 point at their proposed amendments",
      "ADR-668" in read("docs/adr/ADR-664-the-members-browser-is-reach.md")
      and "`metadata.sites`" in read("docs/adr/ADR-630-skills-are-files.md")
      and "ADR-668" in read("docs/adr/ADR-667-the-supervisor-is-set-up-in-conversation.md"))
check("the ledger has the row and the glossary the term",
      "- **ADR-668**:" in read("docs/architecture/ADR-LEDGER.md") and "| **Site skill**" in read("docs/architecture/GLOSSARY.md"))
check("the handoff no longer owes the extension-side site check; local-hands says the scope holds at the executor",
      "the site check inside the extension (a link followed" not in read("docs/SESSION-HANDOFF.md")
      and "withinScope" in read("docs/architecture/local-hands.md"))
check("SCHEMA-NOTES records the step's url without a migration",
      "ADR-668 D4" in read("docs/database/SCHEMA-NOTES.md"))

# ═════════════════════════════════════════════════════════════════════════════
print(f"\n§8 held against the Status line ({STATUS})")
# ═════════════════════════════════════════════════════════════════════════════
_skills = read("api/services/skills/__init__.py")
_posture = read("api/services/apps/supervisor.py")
_reach = read("api/services/reach_status.py")
_creating = read("api/services/skills/creating-skills/SKILL.md")
if STATUS == "Proposed":
    check("Proposed: the skill loader does not parse `metadata.sites` ahead of the ruling", 'metadata.get("sites")' not in _skills)
    check("Proposed: the Supervisor's posture does not yet offer a site skill", "site skill" not in _posture.lower())
    check("Proposed: the reach section does not yet derive a site roster", "site skill" not in _reach.lower())
else:
    check("Accepted: the skill loader lifts `metadata.sites`", 'metadata.get("sites")' in _skills and "def _applies_to" in _skills)
    check("Accepted: the Supervisor's posture offers to write or revise the site skill from the run's steps",
          "skills/sites/" in _posture)
    check("Accepted: creating-skills teaches the site shape", "sites" in _creating)
    check("Accepted: the reach section and list_integrations derive the workspace's sites",
          "sites" in _reach and "sites" in read("api/services/primitives/registry.py"))
    check("Accepted: the step carries `args` minus anything secret-shaped", '"args"' in LANE)

print("\n" + "=" * 70)
print(f"  {PASS} passed, {FAIL} failed")
print("=" * 70)
if FAIL:
    print("✗ ADR-668 gate RED")
    sys.exit(1)
print("✓ all ADR-668 checks passed")
