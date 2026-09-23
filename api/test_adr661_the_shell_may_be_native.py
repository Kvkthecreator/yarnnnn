"""ADR-661 gate — a native shell, and the local hands it may grow.

    §6.1  the unattended path stays TOOLLESS — a clock plus hands is the
          combination this forbids, the same shape as a clock plus a credential
    §5.2  the credential chokepoint still refuses an agent-shaped caller —
          local hands must never become the way around it
    §6.2  write_revision remains the single write path — a local act that
          lands durably lands as an attributed revision, never as a side
          effect visible only on the far side
    §6.4  no local-hands capability ships BEFORE its own implementation ADR —
          a tripwire on the evidence standard, not a ban on the capability
    §4.3  leaving the product goes through ONE door — a raw in-place
          navigation to an external URL strands a member in a native window
    §4.4  a share link names the canonical WEB origin, never the window's
    §7a.1 the eight export-fragile surfaces keep their Suspense boundary, and
          no hook above them re-opens the bailout on every route
    §7.5  the two dead Supabase packages stay gone
    §9.6  the vendored Claude Code source stays out of the repo

Script-shaped: run it and READ THE COUNT (`pytest` collects nothing from it).

    cd api && python3 test_adr661_the_shell_may_be_native.py

Static by necessity — the subject is a ruling, not a behaviour. What reading
cannot prove is named in the ADR: §6.4 requires a DRIVEN TRACE before local
hands may claim they act correctly, and no gate substitutes for it (ADR-577 §7
is the precedent — a passing gate read as live for four months while the path
it described was unreachable).

Arm 4 is a TRIPWIRE, not a prohibition. ADR-661 D3 scopes local attended
computer use IN. This arm fires when an implementation appears while ADR-661 is
still the only ADR on the subject — i.e. when the capability shipped without
the implementation ADR §6.4 demands. It is retired by that ADR, not by deleting
this check.

Each arm was proven RED by editing the shipped file in place and restoring it
in place.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

API = Path(__file__).resolve().parent
REPO = API.parent
WEB = REPO / "web"

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
    """Drop `#` and `//` line comments and block comments.

    A rule that survives only in a docstring is not enforced, and a docstring
    that NAMES the thing it forbids would otherwise satisfy a substring check
    (the ADR-653 finding: `"name" in src` is true from the import line).
    """
    src = re.sub(r'""".*?"""', "", src, flags=re.S)
    src = re.sub(r"'''.*?'''", "", src, flags=re.S)
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    out = []
    for line in src.splitlines():
        line = re.sub(r"(^|\s)#.*$", "", line)
        line = re.sub(r"(^|\s)//.*$", "", line)
        out.append(line)
    return "\n".join(out)


print("\nADR-661 — a native shell, and the local hands it may grow\n")

# ---------------------------------------------------------------- §6.1 toolless
print("§6.1 the unattended path stays toolless")

derive = read("api/services/derive_turn.py")
derive_code = strip_comments(derive)

check(
    "derive_turn.py exists",
    bool(derive),
    "api/services/derive_turn.py not found — the unattended path moved",
)

# The construction, not a default: ADR-615 — "deleting the toolless
# construction would open it, which is why the gate asserts that construction
# directly." Assert on CODE, so a docstring mentioning tools cannot satisfy it.
check(
    "run_bounded_derive_turn passes no tools=",
    bool(derive) and "tools=" not in derive_code,
    "a tools= argument appeared on the unattended path — §6.1 forbids a clock plus hands",
)

check(
    "the unattended path does not compose a tool roster",
    bool(derive) and "lane_tools_openai" not in derive_code,
    "the unattended path reached for the lane's tool roster",
)

# --------------------------------------------------------- §5.2 the chokepoint
print("\n§5.2 the credential chokepoint still refuses an agent-shaped caller")

creds = read("api/services/platform_credentials.py")
creds_code = strip_comments(creds)

check(
    "platform_credentials.py exists",
    bool(creds),
    "api/services/platform_credentials.py not found",
)

# Word-boundary, not substring: `def resolve_platform_credential_RENAMED`
# CONTAINS `def resolve_platform_credential`, so a substring check stays green
# through exactly the rename it exists to catch. Found by falsifying this arm.
check(
    "resolve_platform_credential is still the one resolver",
    bool(re.search(r"def\s+resolve_platform_credential\s*\(", creds_code)),
    "the chokepoint ADR-577 D1.a made reachable was renamed or removed",
)

# ADR-577 D1.a: the refusal is AFFIRMATIVE and logged, keyed on what the auth
# object carries. A silent `return None` would pass a weaker check.
check(
    "the agent refusal is affirmative",
    bool(re.search(r"is_agent_caller|agent-shaped|caller_identity", creds_code)),
    "the agent-shaped refusal lost its affirmative branch",
)

# -------------------------------------------------------- §6.2 the write path
print("\n§6.2 write_revision remains the single write path")

authored = read("api/services/authored_substrate.py")
authored_code = strip_comments(authored)

# Word-boundary for the same reason as the chokepoint arm above: a rename that
# EXTENDS the name satisfies a substring check.
check(
    "write_revision is defined in authored_substrate",
    bool(re.search(r"def\s+write_revision\s*\(", authored_code)),
    "ADR-209's single write path moved or was renamed",
)

check(
    "authored_by is still required at the boundary",
    "authored_by" in authored_code,
    "the attribution argument left the write path",
)

# A second writer is how the invariant erodes: not by deleting write_revision
# but by adding a sibling that skips it.
writers = []
for path in sorted((REPO / "api" / "services").rglob("*.py")):
    if path.name in {"authored_substrate.py"}:
        continue
    body = strip_comments(path.read_text(encoding="utf-8", errors="ignore"))
    if re.search(r"def\s+write_revision\b", body):
        writers.append(str(path.relative_to(REPO)))

check(
    "no second definition of write_revision",
    not writers,
    f"a parallel write path appeared: {writers[:3]}",
)

# ----------------------------------------------- §6.4 the local-hands tripwire
print("\n§6.4 no local-hands capability ships before its own ADR")

# ADR-661 D3 scopes this capability IN. The tripwire fires only while ADR-661
# is the ONLY ADR on the subject — the implementation ADR retires this arm.
# It must be ACCEPTED to retire it: ADR-662 landed as a Proposed draft, and a
# filename match alone would have disarmed the guard before anything was
# ratified — the draft satisfying the check it exists to earn.
def _accepted(p: Path) -> bool:
    head = p.read_text(encoding="utf-8", errors="ignore")[:1500]
    return re.search(r"\*\*Status\*\*:\s*\*\*Accepted", head) is not None

impl_adrs = [
    p.name
    for p in sorted((REPO / "docs" / "adr").glob("ADR-*.md"))
    if p.name != "ADR-661-the-shell-may-be-native-the-hands-may-not.md"
    and re.search(r"computer-use|local-hands|computer_use", p.name, re.I)
    and _accepted(p)
]

hands_tokens = re.compile(r"computer_use|computerUse|synthetic_click|screen_capture", re.I)

offenders: list[str] = []
scan_roots = [
    REPO / "api" / "services" / "primitives",
    REPO / "api" / "services" / "skills",
    WEB / "lib" / "apps",
]
for root in scan_roots:
    if not root.exists():
        continue
    for path in sorted(root.rglob("*")):
        if path.suffix not in {".py", ".ts", ".tsx", ".md"} or not path.is_file():
            continue
        body = strip_comments(path.read_text(encoding="utf-8", errors="ignore"))
        if hands_tokens.search(body):
            offenders.append(str(path.relative_to(REPO)))

# 2026-09-23 — ADR-662's browser pane is BUILT while the ADR is still Proposed:
# §7 builds it so the driven trace §6.4 demands can happen, and ratification
# follows that trace. What the tripwire must still refuse is a member RECEIVING
# it before then. The pane reaches only a host at or above BROWSER_MIN_VERSION,
# and no host reaches a member until a download is published — so while the ADR
# is not Accepted, no download may be.
_downloads = read("web/lib/shell/desktop-app.ts")
_published = re.findall(r'^\s*(mac|windows):\s*"https?://', _downloads, re.M)
# ADR-662 D15 — the Chrome extension is the other way local hands reach a
# member; its listing is held to the same rule.
if re.search(r'storeUrl:\s*"https?://', read("web/lib/shell/hands.ts")):
    _published.append("chrome-extension")

if impl_adrs:
    check(
        "the implementation ADR exists — tripwire retired",
        True,
        "",
    )
    print(f"      (found {impl_adrs[0]}; §6.4's evidence standard now governs)")
else:
    check(
        "no host carrying local hands reaches a member before the ADR is Accepted",
        not _published,
        f"a download is published ({_published}) while ADR-662 is not Accepted — drive the trace and ratify first",
    )
    check(
        "no local-hands capability ships ahead of its ADR",
        not offenders,
        f"a capability appeared with no implementation ADR: {offenders[:3]}",
    )

# --------------------------------------------------------- §7.5 dead packages
print("\n§7.5 the dead Supabase packages stay gone")

pkg_raw = read("web/package.json")
try:
    pkg = json.loads(pkg_raw) if pkg_raw else {}
except json.JSONDecodeError:
    pkg = {}
deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

for dead in ("@supabase/ssr", "@supabase/auth-helpers-react"):
    check(
        f"{dead} is not declared",
        dead not in deps,
        "re-declared with no source import — the ambiguity ADR-661 §7.5 removed",
    )

# The live one must survive: this arm fails if the cleanup went too far.
check(
    "@supabase/auth-helpers-nextjs is still declared",
    "@supabase/auth-helpers-nextjs" in deps,
    "the LIVE auth client was removed — the cleanup overshot",
)

# --------------------------------------------------- §8 step 4 the shell target
print("\n§8 step 4 the shell is a build target, not a fork")

TAURI = REPO / "src-tauri"
check(
    "the host crate exists",
    (TAURI / "Cargo.toml").exists() and (TAURI / "src" / "main.rs").exists(),
    "src-tauri/ is gone — the shell has no host",
)

conf_path = TAURI / "tauri.conf.json"
conf = json.loads(conf_path.read_text(encoding="utf-8")) if conf_path.exists() else {}

# The capability roster is read here for the §7j/§7n arms; what it may GRANT
# the website's origin is ADR-663 D4's, asserted by that ADR's gate.
cap_path = TAURI / "capabilities" / "default.json"
caps = json.loads(cap_path.read_text(encoding="utf-8")) if cap_path.exists() else {}
# A permission is either a bare string or a SCOPED object ({identifier, allow}).
# `opener:allow-open-url` needs the scoped form: the plugin's scope defaults to
# EMPTY, which refuses every URL, and the refusal is silent to the caller — the
# sign-in button opened nothing and the member watched a spinner.
_raw_perms = caps.get("permissions") or []
perms = {p if isinstance(p, str) else p.get("identifier") for p in _raw_perms}
_scoped = {p.get("identifier"): p for p in _raw_perms if isinstance(p, dict)}
# ------------------------------------ §7j the opener has a URL scope
print("\n§7j the opener is allowed to open the URLs the product uses")

opener = _scoped.get("opener:allow-open-url")
check(
    "opener:allow-open-url carries an explicit URL scope",
    bool(opener and opener.get("allow")),
    "an empty scope refuses every URL, silently — the button opens nothing",
)
allowed = " ".join(a.get("url", "") for a in (opener or {}).get("allow", []))
check(
    "the sign-in hand-off host is in scope",
    "yarnnn.com" in allowed,
    "the shell could not open its own sign-in page",
)
check(
    "the scope is not a blanket wildcard",
    "https://*/*" not in allowed and "https://*" not in allowed.replace("https://*.", ""),
    "any page the app renders could ask the OS to open anything",
)

# A fallback that navigates the APP'S OWN WINDOW reintroduces the exact trap
# this helper prevents: the external page renders inside the app, with no
# address bar and no way back.
# Slice the shell branch by its OWN closing `return false;`, not by the string
# it must not contain — splitting on that string truncates the slice before the
# code it is checking, and the arm stays green through the very edit it exists
# to catch. Found by falsifying it.
nav_src = strip_comments(read("web/lib/shell/external-navigation.ts"))
_after = nav_src.split("if (isNativeShell())", 1)
shell_branch = _after[1].split("return false;", 1)[0] if len(_after) > 1 else ""
check(
    "the shell branch never falls back to navigating its own window",
    "window.location.href" not in shell_branch,
    "a refusal would render the external page inside the app",
)

# --------------------------------- §7i the browser completes the sign-in
print("\n§7i the browser signs in, the app receives a session")

# The conventional native-app shape (Notion, Slack, Claude): the app never
# talks to a provider. It opens the WEBSITE, which signs the member in with the
# ordinary web flow and hands the session back over the custom scheme. The PKCE
# verifier therefore never crosses a process boundary — the failure that
# defeated the previous design three times.
handoff = REPO / "web" / "app" / "auth" / "desktop" / "page.tsx"
check(
    "the web has a desktop hand-off page",
    handoff.exists(),
    "the shell would have to authenticate itself again",
)

# §7p — the desktop app has NO sign-in form. `/auth/login` renders
# `DesktopSignIn` in the app (chosen at runtime, ADR-663 D5), which opens
# `/auth/desktop` in the browser. Anchor on the component, and assert it starts
# no auth flow: an email link or OAuth return can only complete in the context
# that began it.
shell_login = strip_comments(read("web/components/auth/DesktopSignIn.tsx"))
check(
    "the desktop sign-in page opens the website's hand-off",
    re.search(r"openExternal\(\s*`\$\{webOrigin\(\)\}/auth/desktop`\s*\)", shell_login) is not None,
    "the app would have no way to sign in",
)
check(
    "the desktop sign-in page starts no auth flow of its own",
    re.search(r"\bAuthForm\b|signInWith\w+\(|signUp\(|resetPasswordForEmail\(", shell_login) is None,
    "a flow begun in the app cannot complete from an email link or a browser return",
)
check(
    "the website's sign-in form carries no desktop branch",
    "isNativeShell" not in strip_comments(read("web/components/auth/AuthForm.tsx")),
    "a second sign-in path inside the shared form — the dual path §7p deleted",
)

bridge_src = strip_comments(read("web/components/shell/DeepLinkBridge.tsx"))
# `refreshSession`, NOT `setSession`. setSession requires BOTH tokens and
# throws AuthSessionMissingError on a falsy access_token BEFORE it ever looks
# at the refresh token — a hand-off carries only a refresh token, so setSession
# failed with "Auth session missing!" on every attempt (observed in a real
# hand-off, reported with a screenshot).
check(
    "the bridge mints a session from the handed-over refresh token",
    "refreshSession" in bridge_src and "refresh_token" in bridge_src,
    "setSession needs both tokens; a hand-off carries only the refresh token",
)
check(
    "the bridge does not call setSession with a half-session",
    "setSession" not in bridge_src,
    "setSession throws AuthSessionMissingError on an empty access_token",
)

# ------------------------------- §7l the hand-off page survives sign-in
print("\n§7l the return target survives the sign-in it bounces through")

# A signed-out member reaching /auth/desktop is sent through login with
# `?next=/auth/desktop`. `getSafeNextPath` refused EVERY `/auth/` target, so
# middleware, login and callback all rewrote it to HOME_ROUTE: the member
# landed on /desktop in the browser and the app never heard back (observed,
# reported with a screenshot). Run the REAL function, not a grep of it — every
# text arm in this file has been blind at least once.
def _safe_next(cases: list[str]) -> dict[str, str] | None:
    import tempfile
    web = REPO / "web" / "lib"
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "routes.ts").write_text((web / "routes.ts").read_text())
        src = (web / "auth" / "redirect.ts").read_text()
        (Path(tmp) / "redirect.ts").write_text(src.replace('"@/lib/routes"', '"./routes.ts"'))
        prog = (
            'import {getSafeNextPath as g} from "./redirect.ts";'
            f"const c={json.dumps(cases)};"
            "console.log(JSON.stringify(Object.fromEntries(c.map(n=>[n,g(n)]))));"
        )
        try:
            out = subprocess.run(
                ["node", "--input-type=module", "-e", prog],
                cwd=tmp, capture_output=True, text=True, timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        if out.returncode != 0:
            return None
        return json.loads(out.stdout.strip().splitlines()[-1])

_next = _safe_next(["/auth/desktop", "/auth/login", "/auth/callback", "/auth/desktop/x"])
check(
    "the guard ran (node strips the types; a crash reports nothing)",
    _next is not None,
    "cannot evaluate getSafeNextPath — fix the harness before trusting this section",
)
check(
    "/auth/desktop survives as a next target",
    bool(_next) and _next["/auth/desktop"] == "/auth/desktop",
    "every desktop sign-in lands on HOME_ROUTE in the browser; the app never hears back",
)
check(
    "every other /auth/ target is still refused (the exemption is exact)",
    bool(_next) and all(_next[p] != p for p in ("/auth/login", "/auth/callback", "/auth/desktop/x")),
    "a widened exemption re-opens the login loop the prefix guard exists to prevent",
)

# ---------------------------- §7m a shipped binary reaches production
# ------------------------------ §7n the app's chrome is the window's chrome
print("\n§7n the shell's top bar knows who is signed in and where the window controls are")

# The shell layout passes no email (it has no request to read one from), and
# the provider had no fallback: the avatar read `?` on every shell launch
# (observed, screenshot). The layout's docstring claimed a fallback existed.
provider = strip_comments(read("web/components/shell/ShellChromeContext.tsx"))
check(
    "the chrome provider falls back to the client session for the email",
    re.search(r"\buserEmail\s*=\s*serverEmail\s*\?\?\s*sessionEmail\b", provider) is not None
    and re.search(r"\.auth\s*\.getSession\(\)\s*\.then\([^)]*\)\s*=>\s*\{[^}]*setSessionEmail", provider, re.S) is not None,
    "the shell's avatar reads `?` — no email reaches the chrome without a request",
)

# The overlaid title bar puts the traffic lights inside the top bar. Anchor on
# the <header> ELEMENT: the drag region and the inset must be on it, not merely
# somewhere in the file.
topbar = strip_comments(read("web/components/shell/chrome/TopBarSurface.tsx"))
_header = re.search(r"<header\b[^>]*>", topbar, re.S)
_header_src = _header.group(0) if _header else ""
check(
    "the top bar is the window's drag region",
    'data-tauri-drag-region="deep"' in _header_src,
    "with an overlaid title bar the window has no grab handle and cannot be moved",
)
check(
    "the top bar reserves the host's title-bar inset",
    "var(--titlebar-inset)" in _header_src,
    "the traffic lights sit on the wordmark",
)
css = read("web/app/globals.css")
check(
    "the inset is 0 on the web and non-zero only when the host says so",
    re.search(r":root\s*\{\s*--titlebar-inset:\s*0(px)?\s*;", css) is not None
    and re.search(r':root\[data-titlebar="overlay"\]\s*\{\s*--titlebar-inset:\s*[1-9]\d*px\s*;', css) is not None,
    "the web's top bar would carry a dead gap, or the shell's none",
)
main_rs = read("src-tauri/src/main.rs")
# Slice from the macOS-only rebinding to the build call. NOT to the first
# `;` — the injected script is full of them, and a slice that stops inside it
# never sees the lines after (found by this arm going red on a correct file).
_mac = re.search(r'#\[cfg\(target_os\s*=\s*"macos"\)\]\s*let builder = builder(.*?)let win = builder\.build\(\)', main_rs, re.S)
_mac_src = _mac.group(1) if _mac else ""
check(
    "the host (macOS only) centres the lights and tells the page",
    ".traffic_light_position(" in _mac_src
    and 'setAttribute("data-titlebar", "overlay")' in _mac_src
    and ".initialization_script(" in _mac_src,
    "the page cannot know the controls are there without detecting a platform (§7.6)",
)
check(
    "the window may be dragged (the drag region needs the permission)",
    "core:window:allow-start-dragging" in perms,
    "data-tauri-drag-region is inert without it: core:default does not grant dragging",
)

# ------------------------------------- §7o the host builds for Windows too
print("\n§7o one host, macOS and Windows")

# The overlay title-bar methods do not EXIST on Windows — outside the macOS
# block the host fails to compile there (E0599, observed by cross-checking).
_code = re.sub(r"//[^\n]*", "", main_rs)
_mac_code = re.sub(r"//[^\n]*", "", _mac_src)
for method in ("title_bar_style", "hidden_title", "traffic_light_position"):
    check(
        f"`.{method}(` is called only inside the macOS block",
        _code.count(f".{method}(") == 1 and f".{method}(" in _mac_code,
        "a macOS-only builder method outside #[cfg(target_os = \"macos\")] breaks the Windows build",
    )

# Windows hands a deep link to a SECOND copy of the app; without this the copy
# that opened the browser never hears the sign-in hand-off.
cargo = read("src-tauri/Cargo.toml")
check(
    "single-instance is a dependency with its deep-link feature",
    re.search(r'^tauri-plugin-single-instance\s*=\s*\{[^}]*features\s*=\s*\[[^\]]*"deep-link"', cargo, re.M) is not None,
    "a Windows sign-in hand-off launches a second app instead of reaching the first",
)
_plugins = re.findall(r"\.plugin\(\s*(tauri_plugin_\w+)::init", _code)
check(
    "single-instance is the FIRST plugin registered",
    bool(_plugins) and _plugins[0] == "tauri_plugin_single_instance",
    f"plugin order {_plugins} — a later registration lets the duplicate launch act first",
)

bundle = conf.get("bundle") or {}
check(
    "the bundle declares the Windows installer and its icon",
    "nsis" in (bundle.get("targets") or []) and "icons/icon.ico" in (bundle.get("icon") or []),
    "the Windows build has no installer, or an installer with Tauri's default icon",
)

wf = read(".github/workflows/shell-windows.yml")
check(
    "the Windows installer is cut on a Windows runner",
    "runs-on: windows-" in wf and "--bundles nsis" in wf,
    "no reproducible way to cut the Windows installer",
)

# ------------------------------------- §7h a failed sign-in says why
print("\n§7h a failed sign-in gives the member a reason")

form = strip_comments(read("web/components/auth/AuthForm.tsx"))

# `useState(initialError)` captures the prop on the FIRST render only, and the
# login page reads `?error=` in an effect — so an error arriving with the URL
# was computed and silently discarded. A member bounced back from a failed
# callback saw a bare form with no reason, which is unreportable.
# Match the EFFECT that syncs it, not the mere presence of the two names —
#  appears elsewhere in this file, so a looser check stays green
# through exactly the deletion it exists to catch. Found by falsifying it.
check(
    "an error arriving after first render still reaches the notice",
    bool(re.search(r"useEffect\(\(\)\s*=>\s*\{[^}]*initialError", form, re.S)),
    "a late ?error= would be computed and dropped",
)

# ------------------------------------------------- §7e the app must hydrate
print("\n§7e the shell ships a LIVE app, not dead HTML")

# Tauri injects a nonce into script-src whenever a CSP is set, and a nonce makes
# the browser IGNORE 'unsafe-inline'. Next delivers React's hydration payload
# through INLINE scripts, so any CSP here ships an app that renders and does
# nothing — measured: the sign-in button was inert.
csp = ((conf.get("app") or {}).get("security") or {}).get("csp")
check(
    "no CSP is set (a nonce would block Next's inline hydration)",
    csp is None,
    f"a CSP would ship dead HTML: {str(csp)[:60]!r}",
)

# --------------------------------------- §8 step 5a the sign-in round trip
print("\n§8 step 5a sign-in leaves, comes back, and stays")

callback = strip_comments(read("web/app/auth/callback/page.tsx"))

# The shell's client sets detectSessionInUrl: false (its callback is a deep
# link, not a navigation it can inspect), so the PKCE code must be exchanged
# explicitly or the member returns signed-in-but-not.
check(
    "the PKCE code is exchanged explicitly",
    "exchangeCodeForSession" in callback,
    "a returning member's code would never be redeemed",
)

# §7p — nothing may mint the superseded `yarnnn://auth/callback`: the app
# never receives a callback; the browser completes every sign-in.
_producers = []
for _root in (WEB / "app", WEB / "components", WEB / "lib"):
    for _f in _root.rglob("*.ts*"):
        _code = strip_comments(_f.read_text(encoding="utf-8", errors="ignore"))
        if re.search(r"auth/callback", _code) and re.search(r"SHELL_SCHEME|yarnnn://", _code):
            _producers.append(str(_f.relative_to(REPO)))
check(
    "nothing mints a yarnnn://auth/callback address",
    not _producers,
    f"the superseded return address is back: {_producers[:3]}",
)

# ---------------------------------------- the desktop app is surfaced, once
print("\n§7p the desktop app is a first-class way in — one roster, no dead links")

# Operator 2026-09-23: "surface the desktop features as first class, no need to
# limit per tiers". The Settings pane lists every platform from ONE module; a
# link appears only for a signed build (an unsigned one says "damaged" — worse
# than no link), and nothing else in the client carries an installer URL.
_desk = strip_comments(read("web/lib/shell/desktop-app.ts"))
_block = re.search(r"DESKTOP_DOWNLOADS[^=]*=\s*\{(.*?)\}", _desk, re.S)
_vals = re.findall(r"\w+\s*:\s*([^,\n]+)", _block.group(1)) if _block else []
check(
    "every desktop download is null or an https link",
    bool(_vals) and all(v.strip() == "null" or re.fullmatch(r'"https://[^"]+"', v.strip()) for v in _vals),
    f"a download entry that is neither unpublished nor https: {_vals}",
)
_settings = strip_comments(read("web/app/(authenticated)/settings/page.tsx"))
check(
    "the Settings pane renders the roster from that module",
    re.search(r"DESKTOP_PLATFORMS\.map\(", _settings) is not None
    and re.search(r"DESKTOP_DOWNLOADS\[\s*platform\s*\]", _settings) is not None,
    "the desktop app is not surfaced, or the pane keeps its own list",
)
_installer = re.compile(r"https?://[^\s\"'`]+\.(dmg|msi|exe)\b|/[^\s\"'`]*\.(dmg|msi)\b")
_second = [
    str(f.relative_to(REPO))
    for root in (WEB / "app", WEB / "components", WEB / "lib")
    for f in root.rglob("*.ts*")
    if f.name != "desktop-app.ts"
    and _installer.search(strip_comments(f.read_text(encoding="utf-8", errors="ignore")))
]
check(
    "no second home for an installer link",
    not _second,
    f"a download link outside lib/shell/desktop-app.ts: {_second[:3]}",
)

# ------------------------------------------------ §8 step 5 the return leg
print("\n§8 step 5 the shell can be signed, and can be returned to")

# §4.3 sends OAuth to the system browser. Without a way BACK the handoff is
# one-way: the member signs in, the browser holds the session, the app never
# hears. The scheme must be declared in BOTH halves or the link goes nowhere.
conf_plugins = (conf.get("plugins") or {}).get("deep-link") or {}
schemes = set((conf_plugins.get("desktop") or {}).get("schemes") or [])
check(
    "the host registers the yarnnn:// scheme",
    "yarnnn" in schemes,
    f"no scheme to return to: {sorted(schemes)}",
)

bridge = strip_comments(read("web/components/shell/DeepLinkBridge.tsx"))
check(
    "the bridge listens for the host's event",
    "deep-link" in bridge and "router" in bridge,
    "the web half of the return leg is gone",
)

# The listener must sit ABOVE the auth boundary: a member completing sign-in is
# on /auth/login, OUTSIDE the authenticated group. Mounted inside it, the
# bridge does not exist at the one moment it is needed — measured, the app woke
# on the link and never navigated.
root_layout = strip_comments(read("web/app/layout.tsx"))
check(
    "the bridge is mounted at the ROOT, above the auth boundary",
    "<DeepLinkBridge" in root_layout,
    "a bridge below /auth/login cannot hear the link that completes sign-in",
)

# A downloaded build that is not notarized says "yarnnn is damaged" — which
# reads as malware. The script is what makes a publishable build reachable.
release = REPO / "scripts" / "release-shell.sh"
release_src = read("scripts/release-shell.sh")
check(
    "the release script exists and is executable",
    release.exists() and os.access(release, os.X_OK),
    "publishing would need someone to remember the steps by hand",
)
check(
    "the release script signs, notarizes AND staples",
    all(k in release_src for k in ("codesign", "notarytool", "stapler")),
    "a build missing any one of the three is unusable when downloaded",
)

# Notarization requires the hardened runtime, which denies the webview's JIT
# unless the entitlement is present — the app would launch and render nothing.
ents = read("src-tauri/entitlements.plist")
check(
    "the entitlements keep the webview working under the hardened runtime",
    "com.apple.security.cs.allow-jit" in ents
    and "com.apple.security.network.client" in ents,
    "a notarized build would launch to a blank window",
)

# ------------------------------------------ §4.3/§4.4 leaving the product
print("\n§4.3/§4.4 leaving the product goes through one door")

EXT = WEB / "lib" / "shell" / "external-navigation.ts"
check(
    "the external-navigation helper exists",
    EXT.exists(),
    "openExternal/webOrigin are gone — 11 call sites lose their one door",
)

# An OAuth consent screen or a checkout page navigated IN PLACE strands a
# member in a native window with no address bar and no back button. These are
# the seven sites; a new one must use the helper, not the raw assignment.
EXTERNAL_NAV_FILES = [
    "web/hooks/useSubscription.ts",
    "web/components/settings/FindConnectorModal.tsx",
    "web/components/settings/ManageConnectionSubsurface.tsx",
]
raw_nav = [
    rel
    for rel in EXTERNAL_NAV_FILES
    if re.search(r"window\.location\.href\s*=", strip_comments(read(rel)))
]
check(
    "no raw in-place navigation to an external URL",
    not raw_nav,
    f"would strand a member in a native window: {raw_nav}",
)

# A share link is pasted into someone ELSE's chat. Built from
# window.location.origin it names the custom scheme and is dead everywhere.
SHARE_LINK_FILES = [
    "web/components/authoring/StudioSurface.tsx",
    "web/components/text/TextEditor.tsx",
]
origin_links = [
    rel
    for rel in SHARE_LINK_FILES
    if "${window.location.origin}" in strip_comments(read(rel))
]
check(
    "share links are built from the canonical web origin",
    not origin_links,
    f"a pasted link would be dead: {origin_links} — use webOrigin()",
)

# ------------------------------------------- §7a.1 the export stays reachable
print("\n§7a.1 the surfaces keep their Suspense boundaries")

# The eight surfaces the export spike found bailing out. Their consumers are
# Suspense-wrapped for SSR; `output: export` needs the boundary at the PAGE.
# Reading could not find this and the export build could — so the gate pins the
# FIX, not the diagnosis.
SUSPENSE_PAGES = [
    "chat", "files", "settings", "supervisor",
    "text", "slides", "images", "notifications",
]
# Count the USE, not the mention: an `import { SurfaceBoundary }` line alone
# satisfies a substring check, so removing the JSX stayed GREEN on the first
# falsification of this arm (the ADR-653 trap — `"name" in src` is true from the
# import). The element must actually be rendered.
missing_boundary = [
    slug
    for slug in SUSPENSE_PAGES
    if not re.search(
        r"<SurfaceBoundary[\s>]",
        strip_comments(read(f"web/app/(authenticated)/{slug}/page.tsx")),
    )
]
check(
    "the eight export-fragile surfaces wrap in SurfaceBoundary",
    not missing_boundary,
    f"useSearchParams would bail out with no boundary: {missing_boundary}",
)

check(
    "SurfaceBoundary exists and is the one fallback",
    (WEB / "components" / "shell" / "SurfaceBoundary.tsx").exists(),
    "the shared boundary is gone — eight bespoke fallbacks will drift",
)

# A hook in a layout is a hook on EVERY route beneath it. AuthGate wraps all 41
# authenticated routes, so `useSearchParams` there took the export from 12
# failures to 40. It reads window.location.search instead.
gate_src = strip_comments(read("web/components/shell/AuthGate.tsx"))
check(
    "AuthGate does not call useSearchParams",
    "useSearchParams" not in gate_src,
    "a query-string hook above every page demands a boundary on every route",
)

# ------------------------------------------------- §7.6 the client is neutral
print("\n§7.6 the client does not design against a platform")

WEB_SRC = [WEB / d for d in ("lib", "components", "hooks", "app", "contexts")]


def web_sources():
    for root in WEB_SRC:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if path.suffix in {".ts", ".tsx"} and path.is_file():
                yield path


# A HANDLER must never branch on the platform: the house idiom is
# `e.metaKey || e.ctrlKey`, which accepts both. `lib/shell/modifier-key.ts` is
# the ONE exception — it decides a NAME to print, never a behaviour — so it is
# the single allowed reader of the platform.
MODIFIER_HELPER = WEB / "lib" / "shell" / "modifier-key.ts"
platform_readers: list[str] = []
for path in web_sources():
    if path == MODIFIER_HELPER:
        continue
    body = strip_comments(path.read_text(encoding="utf-8", errors="ignore"))
    if re.search(r"navigator\s*\.\s*(platform|userAgent|userAgentData)", body):
        platform_readers.append(str(path.relative_to(REPO)))

check(
    "no runtime platform detection outside the one helper",
    not platform_readers,
    f"a surface branched on the platform: {platform_readers[:3]} "
    "— a handler takes metaKey||ctrlKey; only a printed NAME may differ",
)

check(
    "the modifier helper exists and is the one decider",
    MODIFIER_HELPER.exists(),
    "lib/shell/modifier-key.ts is gone — the ⌘/Ctrl+ decision lost its home",
)

# Member-facing copy must not name one platform's key. The catalogs are the
# whole surface: a hardcoded glyph there reaches every member on every OS.
glyph_hits: list[str] = []
for loc in ("en", "ko"):
    cat = WEB / "messages" / f"{loc}.json"
    if not cat.exists():
        continue

    def walk(node, path=""):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{path}.{k}" if path else k)
        elif isinstance(node, str) and re.search(r"⌘|⌥|Cmd\b", node):
            glyph_hits.append(f"{loc}:{path}")

    walk(json.loads(cat.read_text(encoding="utf-8")))

check(
    "no catalog string hardcodes a mac-only modifier",
    not glyph_hits,
    f"copy names one platform's key: {glyph_hits[:3]} — pass {{mod}} instead",
)

# --------------------------------------------------- §9.6 the vendored tree
print("\n§9.6 the vendored Claude Code source stays out of the repo")

vendored = "docs/analysis/src_claudeCC"
try:
    tracked = subprocess.run(
        ["git", "ls-files", vendored],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout.strip()
except Exception:  # pragma: no cover - git absent
    tracked = ""

check(
    "src_claudeCC is not tracked",
    not tracked,
    "a vendored copy of Claude Code's source entered the repo; "
    "22 of 28 'computer use' matches under docs/ are that tree, not canon",
)

gitignore = read(".gitignore")
check(
    "src_claudeCC is gitignored",
    "src_claudeCC" in gitignore,
    "the vendored tree lost its ignore entry and will surface in git status",
)

# ------------------------------------------------------------------- the count
print(f"\n  {PASS} passed, {FAIL} failed\n")
if FAIL:
    print("✗ ADR-661 checks FAILED")
    sys.exit(1)
print("✓ all ADR-661 checks passed")
