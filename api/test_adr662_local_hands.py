"""ADR-662 gate — local hands, the browser first.

    D1   the host never takes the machine: no global input, no screen capture,
         no clipboard; the pane is named in no capability
    D3   every act reads its effect back and says so; receipts persist as words
    D4   consent is the HOST's dialog; the act refuses until the member said yes
    D6   the browser tools reach only the shell turn that asked, on a host new
         enough; only that turn's nonce and member can answer; an unanswered
         act fails closed — driven through the real loop with a fake engine
    D8   stop when stuck
    D9   the unattended derive turn stays toolless
    D13  the model never writes a script: arguments are JSON-encoded by the host

Script-shaped: run it and READ THE COUNT.

    cd api && python3 test_adr662_local_hands.py

Each arm was proven RED by breaking the guarded thing in place and restoring it.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from pathlib import Path

API = Path(__file__).resolve().parent
REPO = API.parent
sys.path.insert(0, str(API))

PASS = FAIL = 0


def check(name: str, cond, note: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name}" + (f" — {note}" if note else ""))


def read(rel: str) -> str:
    path = REPO / rel
    return path.read_text(encoding="utf-8") if path.exists() else ""


def rust_code(src: str) -> str:
    """Drop whole-line comments (`//`, `//!`, `///`) — never mid-line, which
    would eat the `https://` inside a string."""
    return "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("//"))


def fn_body(src: str, name: str) -> str:
    """The brace-matched body of `fn name` — never a fixed window (VERIFICATION.md)."""
    m = re.search(rf"\bfn {re.escape(name)}\b[^{{]*{{", src)
    if not m:
        return ""
    depth, i = 1, m.end()
    while i < len(src) and depth:
        depth += {"{": 1, "}": -1}.get(src[i], 0)
        i += 1
    return src[m.end(): i - 1]


HOST = rust_code(read("src-tauri/src/hands/mod.rs"))
MAIN = rust_code(read("src-tauri/src/main.rs"))
PAGE_JS = read("extension/page.js")
HOST_ALL = HOST + MAIN

# --------------------------------------------------------------------- D1
print("\nD1 the host never takes the machine")

_TAKEOVER = re.compile(
    r"CGEvent|CGWarpMouse|enigo|SendInput|keybd_event|mouse_event|NSPasteboard|clipboard"
    r"|CGWindowListCreateImage|ScreenCaptureKit|SCStream|screenshot|xcap",
    re.I,
)
check(
    "no global input, screen capture or clipboard in the host",
    not _TAKEOVER.search(HOST_ALL),
    f"found {(_TAKEOVER.search(HOST_ALL) or [''])[0]!r} — ADR-662 D1/D2",
)
caps = json.loads(read("src-tauri/capabilities/default.json") or "{}")
_pane = re.search(r'pub const PANE: &str = "([^"]+)";', HOST)
check(
    "the pane has a label, and no capability names it",
    bool(_pane) and caps.get("windows") == ["main"] and _pane.group(1) not in (caps.get("windows") or []),
    f"windows={caps.get('windows')} pane={_pane.group(1) if _pane else None}",
)
check(
    "the pane opens without taking the member's focus",
    ".focused(false)" in fn_body(HOST, "pane"),
    "the pane would steal focus from what the member is doing",
)
check(
    "no page value leaves a password field",
    re.search(r'if \(item\.kind !== "password field"\) item\.value', PAGE_JS) is not None,
    "BrowserRead would send a password to the model",
)

# --------------------------------------------------------------------- D4
print("\nD4 consent is the host's")

enable = fn_body(HOST, "hands_enable")
check(
    "switching on draws the host's own dialog",
    ".dialog()" in enable and ".blocking_show()" in enable,
    "hands_enable must ask the member through a host-drawn prompt (ADR-663 D4)",
)
check(
    "the answer is the dialog's, never an argument from the page",
    re.search(r"=\s*allowed;", enable) is not None and "hands_enable<R: Runtime>(app: AppHandle<R>)" in HOST,
    "the page could set consent by passing a flag",
)
_act = fn_body(HOST, "browser_act")
check(
    "an act refuses before doing anything until the member said yes",
    "require_enabled(&app)" in _act and _act.index("require_enabled(&app)") < _act.index("act(&app"),
    "browser_act must check consent first",
)
_perms = {p if isinstance(p, str) else p.get("identifier") for p in caps.get("permissions") or []}
check(
    "no dialog or file permission is granted to the website",
    not any(p.startswith(("dialog:", "fs:")) for p in _perms),
    f"granted {sorted(p for p in _perms if p.startswith(('dialog:', 'fs:')))}",
)
_manifest = re.findall(r'"(\w+)"', (re.search(r"commands\(&\[(.*?)\]\)", read("src-tauri/build.rs"), re.S) or [None, ""])[1])
check(
    "the app's commands are declared, and the roster names exactly them",
    sorted(_manifest) == ["browser_act", "hands_disable", "hands_enable", "hands_status"]
    and {f"allow-{c.replace('_', '-')}" for c in _manifest} <= _perms,
    f"manifest {_manifest}",
)

# -------------------------------------------------------------------- D13
print("\nD13 the model never writes a script")

_call = fn_body(HOST, "call")
check(
    "every argument is JSON-encoded by the host",
    "serde_json::to_string(a)" in _call and "PAGE_JS" in _call,
    "an argument reaching the page as code is arbitrary execution",
)
_evals = re.findall(r"eval_with_callback\(([^,]+),", HOST)
check(
    "the one eval site runs `call(...)` and nothing else",
    _evals == ["call(routine"],
    f"eval sites: {_evals}",
)
check(
    "only http and https are opened",
    'url.scheme() != "http" && url.scheme() != "https"' in HOST,
    "file:, javascript: or a custom scheme would reach the pane",
)

# --------------------------------------------------------------------- D3
print("\nD3 every act says what changed")

# Literal records, and the act named at each `failure(receipt, act, subject)` call.
_acts = set(re.findall(r'"act": "(\w+)"', HOST)) | set(re.findall(r'failure\([^;]*?, "(\w+)", ', HOST))
check(
    "each act kind reports a record, and the client words every one",
    _acts >= {"opened", "read", "pressed", "filled", "back", "failed", "refused"},
    f"acts {sorted(_acts)}",
)
_labels = read("web/components/chat-surface/toolLabels.ts")
_receipt_acts = set(re.findall(r"'(\w+)'", (re.search(r"RECEIPT_ACTS = new Set\(\[(.*?)\]\)", _labels) or [None, ""])[1]))
en = json.loads(read("web/messages/en.json"))
ko = json.loads(read("web/messages/ko.json"))
_needed = {a for a in _acts} | {f"{a}Unchanged" for a in _acts if a not in ("read", "opened")}
check(
    "the client knows every act the host reports, in both languages",
    _acts <= _receipt_acts
    and _needed <= set(en["chat"]["receipts"]) and _needed <= set(ko["chat"]["receipts"]),
    f"host {sorted(_acts)} · client {sorted(_receipt_acts)}",
)
check(
    "no change is a measurement: clicks compare the page before and after",
    'before.get("sig") != after.get("sig")' in HOST and "no change observed" in HOST,
    "a click would claim an effect it never read",
)
lanes_src = read("api/routes/lanes.py")
check(
    "the member's row records which client tools the turn held",
    'meta["client_tools"] = [t["name"] for t in client_tools]' in lanes_src,
    "whether a turn had the browser would be unanswerable afterwards",
)
check(
    "receipts ride the turn's one assistant row",
    'extra["receipts"] = receipts' in lanes_src and "receipts.append(payload)" in lanes_src,
    "the record of what happened in the member's browser would be lost on reload",
)

# --------------------------------------------------------------------- D6
print("\nD6 only the shell that asked holds the tools, and only it can answer")

os.environ.setdefault("SUPABASE_URL", "http://localhost")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "x")
from services import client_tools as ct  # noqa: E402
from services.desktop_client import BROWSER_MIN_VERSION  # noqa: E402

check("a browser holds no client tools", ct.offered(None, ["browser"]) == ())
check("a host older than the pane holds none", ct.offered("desktop/0.2.0", ["browser"]) == ())
check("a host that did not ask holds none", ct.offered(f"desktop/{BROWSER_MIN_VERSION}", None) == ())
check(
    "a new-enough host that asked holds the browser tools",
    [t["name"] for t in ct.offered(f"desktop/{BROWSER_MIN_VERSION}", ["browser"])]
    == ["BrowserOpen", "BrowserRead", "BrowserClick", "BrowserFill", "BrowserBack"],
)
_cargo = re.search(r'^version = "([\d.]+)"', read("src-tauri/Cargo.toml"), re.M)
check(
    "the host being cut is new enough for the pane",
    bool(_cargo) and tuple(map(int, _cargo.group(1).split("."))) >= tuple(map(int, BROWSER_MIN_VERSION.split("."))),
    f"Cargo {(_cargo.group(1) if _cargo else None)} < BROWSER_MIN_VERSION {BROWSER_MIN_VERSION}",
)
check(
    "both turn doors resolve the tools through the one resolver, with the header",
    len(re.findall(r"client_tools=_client_tools_for\(\s*x_yarnnn_client,", lanes_src)) == 2,
    "a door that skips the resolver offers tools no executor was checked for",
)
check("a page declaring the extension holds the browser tools", len(ct.offered(None, ["browser"], "extension/0.1.0")) == 5)
check("a page declaring an older or malformed extension holds none",
      ct.offered(None, ["browser"], "extension/0.0.9") == () and ct.offered(None, ["browser"], "extension/x") == ()
      and ct.offered(None, ["browser"], "desktop/9.9.9") == ())


async def _answering() -> list[str]:
    out = []
    n = ct.open_turn("member-a")
    fut = ct.expect(n, "call-1")
    out.append(ct.resolve("wrong-nonce", "call-1", "member-a", {"success": True}))
    out.append(ct.resolve(n, "call-1", "member-b", {"success": True}))
    out.append(ct.resolve(n, "call-1", "member-a", {"success": True, "receipt": "r"}))
    got = await ct.wait(n, "call-1", fut)
    out.append("delivered" if got.get("receipt") == "r" else "lost")
    ct.close_turn(n)
    out.append(ct.resolve(n, "call-1", "member-a", {"success": True}))
    return out


check(
    "a wrong nonce, another member, then the right answer, then the closed turn",
    asyncio.run(_answering()) == ["unknown", "not_yours", "ok", "delivered", "unknown"],
    f"got {asyncio.run(_answering())}",
)


async def _unanswered() -> dict:
    ct.ACT_TIMEOUT_S, saved = 0.05, ct.ACT_TIMEOUT_S
    try:
        n = ct.open_turn("member-a")
        fut = ct.expect(n, "call-x")
        got = await ct.wait(n, "call-x", fut)
        ct.close_turn(n)
        return got
    finally:
        ct.ACT_TIMEOUT_S = saved


_r = asyncio.run(_unanswered())
check("an unanswered act fails closed, in words", _r.get("success") is False and "nothing is known to have changed" in _r.get("receipt", ""))

# ---- the real loop, a fake engine: the act goes out, the answer comes back
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


async def _drive_loop(requested_tools: tuple, answer: dict | None) -> tuple[list, list]:
    seen_messages: list = []
    calls = {"n": 0}

    async def fake_stream(model, messages, **kw):
        calls["n"] += 1
        seen_messages.append([m for m in messages])
        names = [t["function"]["name"] for t in kw.get("tools") or []]
        seen_messages[-1].append({"_tools": names})
        if calls["n"] == 1:
            yield ("done", _Routed(tool_calls=[{"id": "tc1", "name": "BrowserOpen", "arguments": {"url": "https://example.com"}}]))
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
            _Auth(), model="anthropic/claude-sonnet-5", history=[], user_message="open example",
            client_tools=requested_tools,
        ):
            events.append((kind, payload))
            if kind == "client_tool" and answer is not None:
                ct.resolve(payload["nonce"], payload["call_id"], "member-a", answer)
    finally:
        (model_router.lanes_enabled, model_router.route_completion_stream, lr.resolve_turn_reach,
         lr.build_lane_conventions, lr.unpriced_lane_model, lr._resolve_byok_key) = saved
    return events, seen_messages


_ev, _msgs = asyncio.run(_drive_loop(ct.offered(f"desktop/{BROWSER_MIN_VERSION}", ["browser"]),
                                      {"success": True, "receipt": "Opened “Example Domain” (example.com).",
                                       "record": {"act": "opened", "subject": "Example Domain", "changed": True}}))
_kinds = [k for k, _ in _ev if k != "round_break"]
check(
    "the shell turn: the act goes out, its receipt comes back, the turn continues",
    _kinds[:3] == ["tool", "client_tool", "receipt"] and _kinds[-1] == "done"
    and any("Example Domain" in (m.get("content") or "") for m in _msgs[-1] if m.get("role") == "tool"),
    f"events {_kinds}",
)
check(
    "the engine was handed the browser tools on that turn",
    "BrowserOpen" in (_msgs[0][-1].get("_tools") or []),
)
_ev2, _msgs2 = asyncio.run(_drive_loop((), None))
check(
    "a turn without them never offers them, and a call to one is refused, not sent",
    "BrowserOpen" not in (_msgs2[0][-1].get("_tools") or []) and "client_tool" not in [k for k, _ in _ev2],
    f"events {[k for k, _ in _ev2]}",
)
check("no turn is left open after the loop ends", not ct._TURNS, f"{len(ct._TURNS)} open")

# ---- the frame's edge follows the turn's tools (2026-09-23: the first in-app
# test held the tools and refused to post, because the frame said it could not)
from services.primitives.browser import BROWSER_FRAME  # noqa: E402

_edge_src = re.search(r"tools_edge=(.+?),\n", read("api/services/lane_runner.py"))
check(
    "a hands turn's edge REPLACES the plain one, which says it cannot write out",
    bool(_edge_src) and _edge_src.group(1).strip() == "BROWSER_FRAME if client_tools else _TOOLS_EDGE"
    and "write out to external platforms" in lr._TOOLS_EDGE
    and "write out to external platforms" not in BROWSER_FRAME and "post, submit" in BROWSER_FRAME,
    "the model would read both 'you cannot write out' and 'you may post'",
)

# --------------------------------------------------------------------- D8
print("\nD8 stop when stuck")

w = ct.StuckWatch()
_v = [w.note("BrowserClick", {"ref": 3}, False), w.note("BrowserClick", {"ref": 3}, False),
      w.note("BrowserClick", {"ref": 4}, False), w.note("BrowserRead", {}, False)]
check("a repeated failure is named; a run of failures stops the turn", _v == [None, "warn", None, "stop"], f"{_v}")
w2 = ct.StuckWatch()
_v2 = [w2.note("BrowserClick", {"ref": 3}, False), w2.note("BrowserRead", {}, True), w2.note("BrowserClick", {"ref": 3}, False)]
check("a success resets the watch", _v2 == [None, None, None], f"{_v2}")
_runner = read("api/services/lane_runner.py")
check(
    "the loop acts on the verdict and has its own round bound",
    "client_tools_mod.STUCK_SENTENCE" in _runner and "client_tools_mod.HANDS_MAX_ROUNDS if client_tools" in _runner,
)

# --------------------------------------------------------------------- D9
print("\nD9 attended only")

derive = read("api/services/derive_turn.py")
check(
    "the derive turn holds no client tools",
    "client_tools" not in derive and "BrowserOpen" not in derive and "primitives.browser" not in derive,
    "an unattended turn could reach the member's machine",
)
_sync_turn = re.search(r"async def run_lane_turn\(.*?(?=\nasync def run_lane_turn_stream\()", _runner, re.S)
check(
    "the non-streaming turn holds none (a client act needs a stream)",
    bool(_sync_turn) and "client_tools" not in _sync_turn.group(0),
    "run_lane_turn would offer tools no client can answer",
)

# -------------------------------------------------------------------- web
print("\nweb the page's side")

client_ts = read("web/lib/api/client.ts")
hands_ts = read("web/lib/shell/hands.ts")
check(
    "a turn asks for the browser only when an executor has it on",
    "const hands = await clientToolsRequest();" in client_ts
    and "if (!hands.on) return {};" in hands_ts,
)
check(
    "the result goes back with the turn's nonce",
    "nonce: frame.nonce" in hands_ts and "/tool-results/" in hands_ts,
)
_web_calls = [
    str(p.relative_to(REPO)) for p in (REPO / "web").rglob("*.ts*")
    if "node_modules" not in p.parts and ".next" not in p.parts
    and re.search(r"""["']browser_act["']|["']hands_enable["']""", p.read_text(encoding="utf-8", errors="ignore"))
]
check("only lib/shell/hands.ts talks to the host's hands", _web_calls == ["web/lib/shell/hands.ts"], f"{_web_calls}")
_ext_calls = [
    str(p.relative_to(REPO)) for p in (REPO / "web").rglob("*.ts*")
    if "node_modules" not in p.parts and ".next" not in p.parts
    and "CHROME_EXTENSION.id" in p.read_text(encoding="utf-8", errors="ignore")
]
check("only lib/shell/hands.ts talks to the extension", _ext_calls == ["web/lib/shell/hands.ts"], f"{_ext_calls}")

# -------------------------------------------------------------------- D15
print("\nD15 the member's own Chrome, through the yarnnn extension")

import base64 as _b64  # noqa: E402
import hashlib as _hl  # noqa: E402
import subprocess as _sp  # noqa: E402

manifest = json.loads(read("extension/manifest.json") or "{}")
bg = read("extension/background.js")
policy_js = read("extension/policy.js")
_der = _b64.b64decode(manifest.get("key", ""))
_ext_id = "".join(chr(ord("a") + int(c, 16)) for c in _hl.sha256(_der).hexdigest()[:32])
_web_id = re.search(r'id: "([a-p]{32})"', hands_ts)
check(
    "the extension's id (from its manifest key) is the one the website calls",
    bool(_web_id) and _web_id.group(1) == _ext_id,
    f"manifest → {_ext_id}, web → {_web_id.group(1) if _web_id else None}",
)
_origins = re.findall(r'"(https?://[^"]+)"', (re.search(r"YARNNN_ORIGINS = \[(.*?)\]", policy_js) or [None, ""])[1])
_matches = (manifest.get("externally_connectable") or {}).get("matches") or []
check(
    "only yarnnn's origins can reach it — Chrome's list and the worker's own check agree",
    sorted(m.rstrip("/*") for m in _matches) == sorted(_origins)
    and "if (!YARNNN_ORIGINS.includes(sender.origin)) return false;" in bg,
    f"manifest {_matches} · worker {_origins}",
)
check(
    "it asks for exactly what acting in a tab needs — no clipboard, cookies, debugger, history or network",
    sorted(manifest.get("permissions") or []) == ["scripting", "storage", "tabGroups", "tabs"],
    f"permissions {manifest.get('permissions')}",
)
_open = re.search(r"async function open\(url\) \{(.*?)\n\}", bg, re.S)
_with = re.search(r"async function withTab\(fn\) \{(.*?)\n\}", bg, re.S)
check(
    "every act passes the site gate first — where the tab IS, not where it was sent",
    bool(_open) and _open.group(1).lstrip().startswith("const refused = await gate(url);")
    and bool(_with) and "const refused = await gate(tab.url);" in _with.group(1)
    and _with.group(1).index("gate(tab.url)") < _with.group(1).index("return fn(tab)"),
)
check(
    "consent is drawn by the extension, and no answer is a no",
    "consent.html" in bg and "if (pendingConsent.delete(id)) resolve(false);" in bg
    and "sender.id !== chrome.runtime.id" in bg,
)
check(
    "the agent's tab opens in the background, never over the member's",
    "active: false" in bg and "active: true" not in bg and "chrome.tabs.highlight" not in bg,
)
check(
    "the page routines are injected by file, and the one function is a fixed dispatcher",
    'files: ["page.js"]' in bg and bg.count("func:") == 1
    and "func: (r, a) => window.__yarnnnHands[r](...a)," in bg,
)
_bg_acts = set(re.findall(r'act: "(\w+)"', bg)) | set(re.findall(r'failure\([^;]*?, "(\w+)", ', bg))
check(
    "the extension reports the same kinds of act the client words",
    _bg_acts and _bg_acts <= _receipt_acts,
    f"extension {sorted(_bg_acts)} · client {sorted(_receipt_acts)}",
)
_policy_probe = _sp.run(
    ["node", "--input-type=module", "-e", """
import { verdictFor, hostOf } from './extension/policy.js';
const v = (u, s) => verdictFor(hostOf(u), s);
console.log(JSON.stringify([
  v('https://www.paypal.com/'), v('https://obank.kbstar.com/'), v('https://www.coinbase.com'),
  v('https://1password.com'), v('https://myaccount.google.com/security'), v('javascript:alert(1)'),
  v('https://x.com/home', {allowed: ['x.com']}), v('https://mobile.x.com', {allowed: ['x.com']}),
  v('https://x.com', {allowed: ['x.com'], denied: ['x.com']}), v('https://news.ycombinator.com'),
  v('https://bank.example.com', {allowed: ['bank.example.com']}),
].map(r => r.verdict + (r.category ? ':' + r.category : ''))));
"""], cwd=str(REPO), capture_output=True, text=True,
)
_verdicts = json.loads(_policy_probe.stdout or "[]")
check(
    "the site rules: categories deny whatever was allowed; allowing covers subdomains; a no wins",
    _verdicts == ["denied:banking", "denied:banking", "denied:trading", "denied:passwords",
                  "denied:accountSecurity", "denied:notAWebPage", "allowed", "allowed",
                  "denied:yours", "ask", "denied:banking"],
    f"{_verdicts} {_policy_probe.stderr[:200]}",
)
_en = json.loads(read("extension/_locales/en/messages.json") or "{}")
_ko = json.loads(read("extension/_locales/ko/messages.json") or "{}")
_used = set(re.findall(r'(?:\bt|getMessage)\("(\w+)"', read("extension/consent.js") + read("extension/popup.js")))
_used |= set(re.findall(r'"\w+:(\w+)"', read("extension/popup.js")))
check(
    "the extension speaks English and Korean, with no missing string",
    set(_en) == set(_ko) and _used <= set(_en) and manifest.get("default_locale") == "en",
    f"missing {sorted(_used - set(_en))} · en≠ko {sorted(set(_en) ^ set(_ko))}",
)
check(
    "one copy of the page routines: the host reads the extension's file",
    'include_str!("../../../extension/page.js")' in HOST and not (REPO / "src-tauri/src/hands/page.js").exists(),
)

# ------------------------------------------------------------------- count
print(f"\n  {PASS} passed, {FAIL} failed\n")
if FAIL:
    print("✗ ADR-662 checks FAILED")
    sys.exit(1)
print("✓ all ADR-662 checks passed")
