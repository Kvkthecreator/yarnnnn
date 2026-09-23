"""ADR-663 gate — the desktop app is the website in a native window; the host
is what is versioned.

    D1  the window opens the website (the local dev server in debug); the one
        bundled page is the bootstrap; no static-export machinery survives
    D2  one version, Cargo.toml's; the current host clears the API's minimum
    D3  the page names the host on every API request; the API refuses an older
        host with 426 THROUGH CORS (driven against the real app), and the page
        turns that into a notice
    D4  the website's origin is granted an explicit roster — never a default
        set, never anything that acts on the machine
    D5  sign-in is the browser's, chosen at runtime
    §4  the retired origins are gone from CORS; the installer build freezes
        nothing, so it needs no web toolchain and no secrets

Script-shaped: run it and READ THE COUNT.

    cd api && python3 test_adr663_the_desktop_app_is_the_website.py

Each arm was proven RED by editing the shipped file in place and restoring it.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

API = Path(__file__).resolve().parent
REPO = API.parent
WEB = REPO / "web"
TAURI = REPO / "src-tauri"

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


def strip_comments(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("//"))


def rust_code(src: str) -> str:
    """Whole-line comments only. Cutting every `//…` to end-of-line eats the
    `https://` inside a string (found by this gate's first run)."""
    return "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("//"))


# --------------------------------------------------------------------- D1
print("\nD1 the desktop app loads the website")

main_rs = rust_code(read("src-tauri/src/main.rs"))
_release = re.search(r'#\[cfg\(not\(debug_assertions\)\)\]\s*const APP_URL: &str = "([^"]+)";', main_rs)
_debug = re.search(r'#\[cfg\(debug_assertions\)\]\s*const APP_URL: &str = "([^"]+)";', main_rs)
check(
    "a release build opens the website over https",
    bool(_release) and _release.group(1) == "https://www.yarnnn.com/desktop",
    f"release APP_URL is {_release.group(1) if _release else None!r}",
)
check(
    "a debug build opens the local dev server",
    bool(_debug) and _debug.group(1).startswith("http://localhost:"),
    "cargo tauri dev would open production",
)
check(
    "the window starts on the bootstrap and is told where to go",
    re.search(r'WebviewWindowBuilder::new\(\s*app,\s*"main",\s*WebviewUrl::default\(\)\s*\)', main_rs) is not None
    and "__YARNNN_APP_URL__" in main_rs and "APP_URL" in main_rs,
    "the window must open the bundled bootstrap with APP_URL injected",
)

conf = json.loads(read("src-tauri/tauri.conf.json") or "{}")
build = conf.get("build") or {}
check(
    "the installer bundles only the bootstrap",
    build == {"frontendDist": "bootstrap"},
    f"build config {build!r} — a before-command or dev URL means something is built into the installer again",
)
boot = read("src-tauri/bootstrap/index.html")
check(
    "the bootstrap opens the injected address and has an offline answer",
    "window.__YARNNN_APP_URL__" in boot and "location.replace(target)" in boot
    and 'addEventListener("online"' in boot,
    "the app would open to a blank window when offline, or never leave the bootstrap",
)
check(
    "the bootstrap is the only bundled file",
    sorted(p.name for p in (TAURI / "bootstrap").iterdir()) == ["index.html"],
    "a second bundled page is a second interface to version",
)

nc = strip_comments(read("web/next.config.js"))
check(
    "no static-export configuration survives",
    not re.search(r"output\s*:|pageExtensions|YARNNN_SHELL|distDir|next-shell", nc),
    "next.config.js still carries the shell build",
)
_web_suffix = [str(p.relative_to(WEB)) for p in (WEB / "app").rglob("*") if re.search(r"\.web\.tsx?$", p.name)]
check(
    "no `.web` route file survives",
    not _web_suffix,
    f"the two-build convention is back: {_web_suffix[:3]}",
)
_gone = [
    "web/scripts/shell-next.mjs",
    "web/components/i18n/ShellIntlScope.tsx",
    "web/i18n/resolve-client.ts",
    "web/components/shell/FallbackWait.tsx",
]
check(
    "the static export's stand-ins are deleted",
    not [g for g in _gone if (REPO / g).exists()],
    f"still present: {[g for g in _gone if (REPO / g).exists()]}",
)
_client = strip_comments(read("web/lib/supabase/client.ts"))
check(
    "the app holds the website's session — one Supabase client",
    "createClientComponentClient" in _client and "supabase-js" not in _client
    and "localStorage" not in _client and "isNativeShell" not in _client,
    "a second session store is back beside the web's cookie",
)

# --------------------------------------------------------------------- D2
print("\nD2 one version")

cargo = read("src-tauri/Cargo.toml")
_ver = re.search(r'^version\s*=\s*"(\d+)\.(\d+)\.(\d+)"', cargo, re.M)
check(
    "Cargo.toml carries the version",
    bool(_ver),
    "the host has no version",
)
check(
    "tauri.conf.json carries none",
    "version" not in conf,
    "two version sources — the one Tauri reads and the one we bump will drift",
)

sys.path.insert(0, str(API))
from services import desktop_client  # noqa: E402

_min = tuple(int(x) for x in desktop_client.DESKTOP_MIN_VERSION.split("."))
check(
    "the current host clears the API's minimum",
    bool(_ver) and tuple(int(g) for g in _ver.groups()) >= _min,
    f"the host being shipped ({_ver.groups() if _ver else None}) is below DESKTOP_MIN_VERSION {_min} — every install would be refused",
)

# --------------------------------------------------------------------- D3
print("\nD3 the host names itself; the API may refuse it")

host = strip_comments(read("web/lib/shell/host.ts"))
check(
    "the page names the host as desktop/X.Y.Z",
    "`desktop/${version}`" in host and 'CLIENT_HEADER = "X-Yarnnn-Client"' in host,
    "the header shape the API parses is not the one the page sends",
)
api_client = strip_comments(read("web/lib/api/client.ts"))
_auth = re.search(r"async function getAuthHeaders\(\)[\s\S]*?\n\}", api_client)
check(
    "every request() carries it (getAuthHeaders)",
    bool(_auth) and "await clientHeaders()" in _auth.group(0),
    "the API cannot tell an old host from a browser",
)
check(
    "the chat transport carries it too",
    "await clientHeaders()" in strip_comments(read("web/lib/api/chatTransport.ts")),
    "the one door that hand-builds headers would skip the identity",
)
check(
    "a refusal becomes an event before the error is thrown",
    re.search(r"noticeHostRefusal\(response\.status,\s*data\);\s*throw new APIError", api_client) is not None,
    "an old host would meet the 426 as a screen of failed loads",
)
layout = strip_comments(read("web/app/(authenticated)/layout.tsx"))
check(
    "the notice is mounted inside the scope",
    re.search(r"<IntlScope>\s*<DesktopUpdateNotice\s*/>", layout) is not None,
    "nobody would hear the event, or the notice would throw outside a provider",
)
for lang in ("en", "ko"):
    cat = json.loads(read(f"web/messages/{lang}.json") or "{}")
    hu = (cat.get("shell") or {}).get("hostUpdate") or {}
    check(
        f"the notice is worded in {lang}",
        bool(hu.get("message")) and bool(hu.get("action")),
        "the notice would render a raw key",
    )

main_py = read("api/main.py")
_mw = main_py.find("app.add_middleware(DesktopMinVersionMiddleware)")
_cors = main_py.find("CORSMiddleware,", _mw if _mw >= 0 else 0)
check(
    "the minimum is registered INSIDE CORS",
    0 <= _mw < _cors,
    "added after CORS it would be outermost, and its 426 would carry no CORS headers",
)

# Driven, not read: the real app, the real middleware order.
os.environ.setdefault("INTEGRATION_ENCRYPTION_KEY", "adr663-gate")
try:
    import logging

    logging.disable(logging.CRITICAL)
    from fastapi.testclient import TestClient
    import main as _main

    _tc = TestClient(_main.app)

    def _get(header: str | None, origin: str = "https://www.yarnnn.com"):
        h = {"Origin": origin}
        if header:
            h["X-Yarnnn-Client"] = header
        return _tc.get("/health", headers=h)

    _drove = True
except Exception as e:  # pragma: no cover - a crash reports nothing, so say so
    print(f"    (could not import the app: {e!r})")
    _drove = False

check("the harness drove the real app", _drove, "a gate that crashes reports nothing")
if _drove:
    _old = _get("desktop/0.1.0")
    check(
        "an old host is refused with 426 and the update code",
        _old.status_code == 426
        and (_old.json().get("error") or {}).get("code") == "desktop_update_required",
        f"got {_old.status_code}",
    )
    check(
        "the refusal carries CORS headers, so the page can read it",
        _old.headers.get("access-control-allow-origin") == "https://www.yarnnn.com",
        "the browser would report a network error and the notice would never fire",
    )
    _cur = ".".join(_ver.groups()) if _ver else "0.0.0"
    check(
        "the host being shipped is served",
        _get(f"desktop/{_cur}").status_code == 200,
        "every install of this build would be refused",
    )
    check(
        "a browser (no header) is never refused",
        _get(None).status_code == 200,
        "the website would lock itself out",
    )
    # §4 — the retired static-export origins.
    check(
        "the static-export origins are gone from CORS",
        _get(None, origin="tauri://localhost").headers.get("access-control-allow-origin") is None
        and _get(None, origin="http://tauri.localhost").headers.get("access-control-allow-origin") is None,
        "a retired host could still reach the API",
    )

# --------------------------------------------------------------------- D4
print("\nD4 the website's origin gets an explicit roster")

caps = json.loads(read("src-tauri/capabilities/default.json") or "{}")
_perms = {p if isinstance(p, str) else p.get("identifier") for p in caps.get("permissions") or []}
ALLOWED = {
    "core:event:default",            # DeepLinkBridge listens for the host's deep-link event
    "core:app:allow-version",        # hostVersion() — D3's header
    "core:window:default",           # window chrome (read-only queries, title-bar zoom)
    "core:window:allow-start-dragging",  # the top bar is the grab handle (ADR-661 §7n)
    "deep-link:default",             # the yarnnn:// return leg
    "opener:allow-open-url",         # the system-browser hand-off, URL-scoped (ADR-661 §7j)
    # ADR-662 D15 — local hands: the host RELAYS each act to the yarnnn Chrome
    # extension, which performs it and draws its own per-site consent — the
    # executor asks, never the page, so D4's rule holds. Asserted, and proven
    # RED, in api/test_adr662_local_hands.py.
    "allow-hands-status",
    "allow-browser-act",
}
check(
    "the roster names exactly what the interface needs",
    _perms == ALLOWED,
    f"granted {sorted(_perms)} — adding a permission the website may call needs ADR-663 D4's host-drawn consent",
)
check(
    "no default set is granted to a remote page",
    "core:default" not in _perms,
    "core:default grants menus, trays, paths and resources the interface never asked for",
)
_remote = (caps.get("remote") or {}).get("urls") or []
check(
    "only the website's own https origin is remote",
    sorted(_remote) == ["https://www.yarnnn.com/*", "https://yarnnn.com/*"],
    f"remote urls {_remote}",
)
check(
    "the bundled bootstrap may ask the host for nothing",
    caps.get("local") is False,
    "the local page needs no host commands",
)
check(
    "the dev server gets the SAME roster, re-pointed, only in debug",
    re.search(r'#\[cfg\(debug_assertions\)\]\s*\{[^}]*include_str!\("\.\./capabilities/default\.json"\)', main_rs, re.S) is not None
    and "add_capability" in main_rs,
    "a second hand-written roster for dev drifts from the real one",
)

# --------------------------------------------------------------------- D5
print("\nD5 sign-in is the browser's, chosen at runtime")

login = strip_comments(read("web/app/auth/login/page.tsx"))
check(
    "the sign-in page chooses the app's panel after mount",
    re.search(r"useEffect\(\(\)\s*=>\s*setInApp\(isNativeShell\(\)\)", login) is not None
    and re.search(r"if\s*\(inApp\)\s*return\s*<DesktopSignIn\s*/>", login) is not None,
    "the app would render the website's form — a flow begun in the app cannot complete",
)

# --------------------------------------------------------------------- §4
print("\n§4 the installer build freezes nothing")

wf = read(".github/workflows/shell-windows.yml")
check(
    "the Windows workflow builds the host alone",
    "npm ci" not in wf and "setup-node" not in wf and "secrets." not in wf,
    "the installer would freeze web values into itself again",
)

# ------------------------------------------------------------------- count
print(f"\n  {PASS} passed, {FAIL} failed\n")
if FAIL:
    print("✗ ADR-663 checks FAILED")
    sys.exit(1)
print("✓ all ADR-663 checks passed")
