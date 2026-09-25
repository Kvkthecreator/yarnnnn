"""ADR-664 gate — the member's browser is reach.

    D1  the browser is stated where reach is stated (`reach_status`), and nowhere else
    D2  held, it reaches any website and nothing in the reach section denies it
    D3  absent, it is still named — with how the member gets it
    D4  the frame's tools section claims no reach of its own
    D5  `list_integrations` names websites and no longer refuses
    D6  Reach shows the browser, served from the one structure, in both branches

Script-shaped: run it and READ THE COUNT.

    cd api && python3 test_adr664_the_browser_is_reach.py

Each arm was proven RED by breaking the guarded thing in place and restoring it.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

API = Path(__file__).resolve().parent
REPO = API.parent
sys.path.insert(0, str(API))
os.environ.setdefault("SUPABASE_URL", "http://localhost")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "x")

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
    p = REPO / rel
    return p.read_text(encoding="utf-8") if p.exists() else ""


from services import lane_runner as lr  # noqa: E402
from services.reach_status import browser_does, frame_paragraph  # noqa: E402

print("\nD1–D3 the reach section carries the browser")
_held = frame_paragraph([], "M", reach_on=True, browser_held=True)
_plain = frame_paragraph([], "M", reach_on=True, browser_held=False)
check(
    "held: it reaches any website, a website task goes to it first, and nothing denies it",
    "reaches ANY website" in _held and "goes to the browser first" in _held
    and "cannot send or publish anywhere" not in _held and "Never type a password yourself" in _held,
    _held[-300:],
)
check(
    "held: a connection still never sends",
    "Through a connection you cannot send or publish yourself" in _held,
)
check(
    "absent: the browser is named, with how to get it",
    "yarnnn extension to Chrome" in _plain and "cannot send or publish anywhere" in _plain,
)
runner = read("api/services/lane_runner.py")
check(
    "the frame tells the reach section whether the turn holds the browser",
    'browser_held=any(t["name"] == "BrowserOpen" for t in client_tools)' in runner,
)

print("\nD4 the tools section claims no reach")
check(
    "no reach sentence in the frame outside the reach section",
    "write out to external platforms" not in lr._CONVENTIONS_FRAME
    and "write only to the commons" not in lr._CONVENTIONS_FRAME
    and "BROWSER_FRAME" not in runner and "tools_edge" not in runner,
)
check(
    "no browser reach sentence lives with the tool definitions",
    "BROWSER_FRAME" not in read("api/services/primitives/browser.py"),
)

print("\nD5 list_integrations names websites")
reg = read("api/services/primitives/registry.py")
check(
    "its result says a website needs no connection, and its description no longer refuses",
    '"websites": (' in reg and "Asked to send or publish somewhere, you cannot" not in reg
    and "A WEBSITE needs no connection" in reg,
)

print("\nD6 Reach shows the browser")
_does = browser_does()
check(
    "the member face has the connections' shape",
    {"name", "reads", "writes", "agents"} <= set(_does) and "never allowed" in _does["writes"],
)
route = read("api/routes/integrations.py")
check(
    "GET /integrations serves it from the one structure",
    "browser=browser_does()" in route and "browser: Optional[dict] = None" in route,
)
pane = read("web/components/reach/ReachConnected.tsx")
check(
    "Reach renders the row with connections and without any",
    pane.count("<ReachBrowser does={browserDoes} Fact={Fact} />") == 2,
)
row = read("web/components/reach/ReachBrowser.tsx")
_jsx_text = re.findall(r">\s*([A-Za-z][^<>{}]{3,})\s*<", row)
check(
    "the row writes no reach sentence of its own — served facts and catalog keys only",
    not _jsx_text and "does.reads" in row and "does.writes" in row and "does.agents" in row,
    f"literal text in the row: {_jsx_text}",
)

# ═══ Amendment 1 (2026-09-24) — the browser is not a desktop feature ═══════
print("\n── am.1 — every surface says the browser works from the web and the desktop app ──")
import json as _json  # noqa: E402
from services import reach_status  # noqa: E402

_settings = read("web/app/(authenticated)/settings/page.tsx")
check("the browser has its own Settings pane, not a row in the desktop app's",
      re.search(r'\{ key: "browser", labelKey: "panes\.browser"', _settings) is not None
      and re.search(r'pane === "browser" && \(.*?<BrowserSetting />', _settings, re.S) is not None
      and "DesktopBrowserSetting" not in _settings
      and not re.search(r'pane === "desktop" && \((?:(?!pane === ").)*<BrowserSetting', _settings, re.S))
check("the agent is sent to that pane, never to the desktop app's",
      "Settings → Your browser" in reach_status.browser_sentence("M", held=False)
      and "Settings → Desktop app" not in reach_status.browser_sentence("M", held=False))
check("'keep Chrome open' is said only inside the desktop app",
      re.search(r"isNativeShell\(\) && \(\s*<p[^>]*>\{t\(\"desktopKeepOpen\"\)\}",
                read("web/components/settings/BrowserSetting.tsx")) is not None)

# ONE install action: no surface builds its own store link.
_add = read("web/components/shared/AddToChrome.tsx")
check("AddToChrome is the one install action, switched by storeUrl",
      "if (!CHROME_EXTENSION.storeUrl)" in _add and "href={CHROME_EXTENSION.storeUrl}" in _add
      and "export const EXTENSION_PUBLISHED = CHROME_EXTENSION.storeUrl !== null" in _add)
_web = Path(API.parent / "web")
_stray = [str(p.relative_to(_web)) for d in ("components", "app", "lib") for p in (_web / d).rglob("*.tsx")
          if "storeUrl" in p.read_text(encoding="utf-8", errors="ignore") and p.name != "AddToChrome.tsx"
          and "CHROME_EXTENSION.storeUrl" in re.sub(r"(?s)/\*.*?\*/|//[^\n]*", "", p.read_text(encoding="utf-8", errors="ignore"))]
check("no other surface reads storeUrl to build a link", not _stray, str(_stray))
for rel in ("web/components/settings/BrowserSetting.tsx", "web/components/reach/ReachBrowser.tsx",
            "web/components/supervisor/BrowserGate.tsx"):
    check(f"{rel.split('/')[-1]} renders the one install action", "<AddToChrome" in read(rel))

# The public site names the browser only once a visitor can install it.
_faq = read("web/components/marketing/FaqPageBody.tsx")
check("the FAQ's browser answer appears only when the extension is published",
      re.search(r"const browserItem = EXTENSION_PUBLISHED\s*\?", _faq) is not None
      and 's.cat === "work" && browserItem' in _faq)
_how = read("web/components/marketing/HowItWorksPageBody.tsx")
check("How it works shows its browser step only when published",
      's.key !== "browser" || EXTENSION_PUBLISHED' in _how and "shown.map(" in _how)
for rel, key in (("web/components/marketing/LandingPageBody.tsx", "browserLine"),
                 ("web/components/marketing/DownloadPageBody.tsx", "browserExtension")):
    check(f"{rel.split('/')[-1]}'s browser line is gated on EXTENSION_PUBLISHED",
          re.search(r"\{EXTENSION_PUBLISHED && \((?:(?!\)\}).)*t\(\"" + key + r"\"\)", read(rel), re.S) is not None)
for lang in ("en", "ko"):
    _cat = _json.loads(read(f"web/messages/{lang}.json"))
    check(f"{lang}: the browser's words exist, and the desktop pane holds none",
          all(k in _cat["extension"] for k in ("add", "install")) and "notYet" not in _cat["extension"]
          and all(_cat["settings"]["browser"].get("manual", {}).get(k)
                  for k in ("intro", "download", "unzip", "openExtensions", "loadUnpacked", "after"))
          and "<url></url>" in _cat["settings"]["browser"]["manual"]["openExtensions"]
          and "browser" in _cat["settings"] and "browser" not in _cat["settings"]["desktop"]
          and all(_cat["marketing"]["faq"]["q"]["browser"].get(k) for k in ("q", "a")))

# Amendment 2 — ADR-662 Accepted: a member may install it before the listing.
print("\nAmendment 2 — installable by hand while the Web Store reviews it")
_adr662 = next((API.parent / "docs" / "adr").glob("ADR-662-*.md")).read_text(encoding="utf-8")[:1500]
check("ADR-662 is Accepted — a member may receive the extension",
      re.search(r"\*\*Status\*\*:\s*\*\*Accepted", _adr662) is not None)
check("without a listing, the install action leads to the manual install, never a dead end",
      re.search(r"if \(!CHROME_EXTENSION\.storeUrl\) \{\s*return \(\s*<Link href=\{INSTALL_BY_HAND\}", _add) is not None
      and 'INSTALL_BY_HAND = "/settings?settings.pane=browser"' in _add and "notYet" not in _add)
_bs = read("web/components/settings/BrowserSetting.tsx")
check("the pane offers the zip and its steps while there is no listing",
      "{!connected && !hostTooOld && !EXTENSION_PUBLISHED && <InstallByHand />}" in _bs
      and "href={EXTENSION_DOWNLOAD_PATH}" in _bs and 'window.addEventListener("focus", read)' in _bs)
check("the pane leads with its state — connected, installed but off, or not — before any sentence",
      re.search(r'<p role="status"[^>]*>\s*<span[^>]*>\s*<span className=\{`h-2 w-2 rounded-full \$\{status\.dot\}`\}', _bs) is not None
      and re.search(r'hostTooOld\s*\?\s*\{ key: "status\.update"[^}]*\}\s*:\s*!connected\s*\?\s*\{ key: isNativeShell\(\) \? "status\.notConnected" : "status\.missing"[^}]*\}\s*:\s*hands\.on\s*\?\s*\{ key: "status\.on", dot: "bg-emerald-500" \}\s*:\s*\{ key: "status\.off"', _bs) is not None
      and _bs.find('role="status"') < _bs.find("{body}"))
_dl = read("web/lib/shell/desktop-app.ts")
check("the zip has one home and our own address",
      re.search(r'EXTENSION_DOWNLOAD =\s*"https://[a-z0-9]+\.supabase\.co/storage/v1/object/public/desktop-releases/yarnnn-chrome-extension\.zip"', _dl) is not None
      and re.search(r"NextResponse\.redirect\(EXTENSION_DOWNLOAD, 302\)", read("web/app/download/chrome-extension/route.ts")) is not None)
_pkg = read("scripts/package-extension.sh")
check("the manual zip keeps the manifest's key (the id the website addresses)",
      'if mode == "store":\n    m.pop("key", None)' in _pkg and "the manual zip needs the manifest's key" in _pkg)

print(f"\n  {PASS} passed, {FAIL} failed\n")
if FAIL:
    print("✗ ADR-664 checks FAILED")
    sys.exit(1)
print("✓ all ADR-664 checks passed")
