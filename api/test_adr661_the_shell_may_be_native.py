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
impl_adrs = [
    p.name
    for p in sorted((REPO / "docs" / "adr").glob("ADR-*.md"))
    if p.name != "ADR-661-the-shell-may-be-native-the-hands-may-not.md"
    and re.search(r"computer-use|local-hands|computer_use", p.name, re.I)
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

if impl_adrs:
    check(
        "the implementation ADR exists — tripwire retired",
        True,
        "",
    )
    print(f"      (found {impl_adrs[0]}; §6.4's evidence standard now governs)")
else:
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

# D4: ONE codebase. The host must build the web tree, never carry its own copy.
before = (conf.get("build") or {}).get("beforeBuildCommand", "")
check(
    "the shell builds from web/, never its own tree",
    "cd web" in before and "YARNNN_SHELL=1" in before,
    f"beforeBuildCommand does not build the shared tree: {before!r}",
)

# The API must accept the shell's Origin, or every call fails CORS while the
# app itself loads fine — a whole-product failure that reads as a backend
# outage. Measured during the §8 click-pass.
main_py = read("api/main.py")
check(
    "the API allows the shell's origins",
    "tauri://localhost" in main_py and "http://tauri.localhost" in main_py,
    "the shell would load and then fail every API call on CORS",
)

# §5/§6: the capability roster is the audit surface for what the host exposes.
# Local hands would add a permission HERE, in their own ADR — so the roster
# staying small is what makes that addition visible.
cap_path = TAURI / "capabilities" / "default.json"
caps = json.loads(cap_path.read_text(encoding="utf-8")) if cap_path.exists() else {}
perms = set(caps.get("permissions") or [])
check(
    "the host grants only what the product needs today",
    perms and perms <= {"core:default", "opener:allow-open-url", "deep-link:default"},
    f"the capability roster grew without an ADR: {sorted(perms)}",
)

# The shell build must not ship Hat-B tooling or the marketing site.
for rel in ("web/app/admin/page.web.tsx", "web/app/page.web.tsx"):
    check(
        f"{rel.split('/', 1)[1]} is web-only",
        (REPO / rel).exists(),
        "a web-only route lost its .web suffix and would enter the shell build",
    )

# ----------------------------------------- §7g the shell's OAuth flow is PKCE
print("\n§7g the shell signs in the way a native app must")

client_src = strip_comments(read("web/lib/supabase/client.ts"))

# supabase-js defaults to flowType: 'implicit', which returns the session in a
# URL FRAGMENT. A fragment is never sent anywhere — not to a server, not
# through a custom-scheme deep link — so the app got a callback carrying
# nothing and stayed signed out. The web's auth-helpers sets pkce for us, which
# is why only the shell was affected.
#
# PKCE is also the conventional flow for a native app (RFC 8252): no client
# secret, and the verifier never leaves the device.
check(
    "the shell client uses the PKCE flow",
    '"pkce"' in client_src or "'pkce'" in client_src,
    "implicit returns the session in a fragment the deep link cannot carry",
)

# --------------------------------------- §7f the shell root is not an error
print("\n§7f the shell root is a real page")

# `redirect()` from next/navigation is a SERVER call. In a static export Next
# emits the route as an ERROR page (id="__next_error__") instead — which is
# what a member saw after signing in: a page that looks like a logged-out
# start, on an app that had just authenticated them.
#
# The check is on the SOURCE, because the export is a build artifact that may
# not exist when the gate runs.
shell_root = strip_comments(read("web/app/page.tsx"))
check(
    "the shell root redirects client-side, not with server redirect()",
    "use client" in read("web/app/page.tsx") and "router.replace" in shell_root,
    "a server redirect() exports as an error page in a static build",
)
# The web's `/` is the marketing LANDING PAGE, not a stub — the two roots are
# different pages, which is the whole reason the shell needs its own.
check(
    "the web root is still the marketing landing page",
    "LandingPageBody" in strip_comments(read("web/app/page.web.tsx")),
    "the web build lost its landing page to the shell's redirect",
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

auth_form = strip_comments(read("web/components/auth/AuthForm.tsx"))

# `signInWithOAuth` navigates the CURRENT window unless told not to. In the
# shell that renders Google's own consent page inside the app's webview, where
# it recognises no passkey and offers no password field — reported from a real
# build.
check(
    "the OAuth consent screen opens in the member's browser",
    "skipBrowserRedirect" in auth_form and "openExternal" in auth_form,
    "the provider's sign-in page would render inside the app window",
)

callback = strip_comments(read("web/app/auth/callback/page.tsx"))

# The shell's client sets detectSessionInUrl: false (its callback is a deep
# link, not a navigation it can inspect), so the PKCE code must be exchanged
# explicitly or the member returns signed-in-but-not.
check(
    "the PKCE code is exchanged explicitly",
    "exchangeCodeForSession" in callback,
    "a returning member's code would never be redeemed",
)

# A full page load in a STATIC EXPORT reboots the app from index.html, losing
# the session that was just established — the "sign in, land on the landing
# page, sign in again" loop.
for rel, src in (
    ("web/app/auth/callback/page.tsx", callback),
    ("web/app/auth/login/page.tsx", strip_comments(read("web/app/auth/login/page.tsx"))),
):
    check(
        f"{rel.rsplit('/', 2)[-2]}: post-sign-in navigation is soft in the shell",
        "isNativeShell" in src and "router.replace" in src,
        "a hard navigation reboots the static export and drops the session",
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
