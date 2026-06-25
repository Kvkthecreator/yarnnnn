"""
Navigation guard — cross-surface jumps must use the window-manager verbs.

Enforces the OS-desktop navigation model (ADR-297 D19.5/D19.6 + ADR-358 D5/D6):
the authenticated shell NEVER leaves its `/desktop` baseline. Two sanctioned
verbs do all navigation, both in web/lib/shell/useSurfacePreferences.tsx:

  • CROSS-surface (open/raise another window) → navigateToSurface(slug, params)
    or the <SurfaceLink to="slug"> wrapper (components/shell/SurfaceLink.tsx).
  • INTRA-surface (change what THIS window shows) → useSurfaceParam(slug).set(...)

The ANTI-PATTERN this guard bans is the pre-OS-shell idiom that drifted back in:
  (a) <Link href="/{surface-route}">  — Next hard-navigates → pathname flips off
      /desktop → the SPA remounts, resetting the docked chat (the "inconsistent
      redirect" operators felt: some launches foreground cleanly, others jump).
  (b) <a href="/{surface-route}">     — same hard-navigation.
  (c) router.push/replace("/{surface-route}") — same, via the router.

Why a guard: the verb sweep (2026-06-25) migrated ~40 sites to SurfaceLink /
navigateToSurface / useSurfaceParam. Without a ratchet the idiom creeps back one
PR at a time (it's the obvious thing to type). This guard is green at the
zero-baseline (every site swept) and turns RED the moment a new cross-surface
<Link>/<a>/router.push to a surface route is added.

Same PROGRESSIVE-VALIDATE-AND-EXPAND shape as
test_voice_no_kernel_nouns_in_copy.py + test_adr209_no_filename_versioning.py:
banned patterns + an ALLOWLIST baseline (empty here) that a regressing PR must
either honour or explicitly extend (forcing the reviewer to see the drift).

SCOPE — web/components/ + web/app/ TS/TSX. Excludes:
  - comment lines (// , * , /* */)
  - the SurfaceLink component itself (it legitimately builds the href)
  - redirect-stub PAGES under web/app/.../page.tsx whose whole job is a
    server `redirect(...)` (ADR-308 pure-transport stubs) — those are allowed
    to name a route; they don't hard-navigate inside the shell.

Usage:
    cd api && python test_nav_no_cross_surface_router_push.py
    (pytest-compatible: pytest api/test_nav_no_cross_surface_router_push.py)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# The kernel surface SLUGS (== their routes; web/types/desk.ts KERNEL_SURFACE_SLUGS).
# A cross-surface jump targets one of these as `/{slug}` (optionally `?query`).
SURFACE_SLUGS = [
    "feed", "home", "recurrence", "budget", "autonomy", "expected-output",
    "mandate", "principles", "identity", "files", "agents", "setup", "program",
    "queue", "notifications", "activity", "settings", "workspace-settings",
    "connectors", "sources",
    # legacy route aliases that still resolve to a surface (redirect stubs)
    "system", "team", "chat", "cadence", "operation", "context",
]
_SLUG_ALT = "|".join(re.escape(s) for s in SURFACE_SLUGS)

# (a)+(b): href="/{surface}" or href={`/{surface}…`} or href='/{surface}…'
#   matches  <Link href="/recurrence?…">  and  <a href="/connectors">
_HREF_SURFACE = re.compile(
    r"""href=\{?["'`]/(?:""" + _SLUG_ALT + r""")(?:[/?"'`]|$)""",
)

# (c): router.push("/{surface}…") / router.replace(`/{surface}…`)
_ROUTER_NAV_SURFACE = re.compile(
    r"""router\.(?:push|replace)\(\s*[`"']/(?:""" + _SLUG_ALT + r""")(?:[/?`"']|$)""",
)

BANNED = [
    (_HREF_SURFACE,
     "cross-surface <Link>/<a> href to a surface route — use <SurfaceLink to=\"slug\"> "
     "(components/shell/SurfaceLink.tsx); it keeps the OS shell on /desktop"),
    (_ROUTER_NAV_SURFACE,
     "router.push/replace to a surface route — use navigateToSurface(slug, params) "
     "(cross-surface) or useSurfaceParam(slug).set(...) (intra-surface)"),
]

_COMMENT_LINE = re.compile(r"^\s*(//|\*|/\*|\*/)")

# =============================================================================
# Files in scope
# =============================================================================

WEB_DIRS = ["components", "app"]
WEB_EXCLUDE_DIRS = {"node_modules", ".next", "dist", "build"}

# The SurfaceLink component legitimately constructs the `/{slug}` href as the
# native-affordance fallback (middle-click / new-tab); it's the sanctioned
# wrapper, not a violation.
EXEMPT_FILES = {
    "web/components/shell/SurfaceLink.tsx",
}


def _web_files():
    for d in WEB_DIRS:
        base = REPO_ROOT / "web" / d
        if not base.exists():
            continue
        for p in base.rglob("*.ts*"):
            if p.suffix not in (".ts", ".tsx"):
                continue
            if any(part in WEB_EXCLUDE_DIRS for part in p.parts):
                continue
            yield p


# =============================================================================
# ALLOWLIST — known-baseline of pre-existing violations (the progress meter).
# Each entry: "relative/path::substring-of-the-violating-line". SHRINK it as
# sites migrate; a removed-but-still-violated entry turns the guard red.
#
# Zero-baseline (2026-06-25): the verb sweep migrated every cross-surface site
# to SurfaceLink / navigateToSurface / useSurfaceParam, so the guard ships
# EMPTY — ANY new cross-surface <Link>/<a>/router.push turns CI red.
# =============================================================================

ALLOWLIST: list[str] = []


def _allowlisted(rel_path: str, line: str) -> bool:
    for entry in ALLOWLIST:
        if "::" not in entry:
            continue
        ap, frag = entry.split("::", 1)
        if rel_path.endswith(ap) and frag in line:
            return True
    return False


def find_violations() -> list[tuple[str, int, str, str]]:
    """Returns (rel_path, lineno, line, reason) for every non-allowlisted hit."""
    violations: list[tuple[str, int, str, str]] = []
    for path in _web_files():
        rel = str(path.relative_to(REPO_ROOT))
        if rel in EXEMPT_FILES:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if _COMMENT_LINE.match(line):
                continue
            for pat, reason in BANNED:
                if not pat.search(line):
                    continue
                if _allowlisted(rel, line):
                    continue
                violations.append((rel, lineno, line.strip(), reason))
    return violations


def test_no_cross_surface_router_push():
    violations = find_violations()
    if violations:
        msg = ["Cross-surface navigation bypasses the window-manager verbs "
               "(ADR-297 D19 + ADR-358):"]
        for rel, lineno, line, reason in violations:
            msg.append(f"  {rel}:{lineno} — {reason}")
            msg.append(f"      {line[:140]}")
        msg.append("")
        msg.append("Use <SurfaceLink to=\"slug\" params={{…}}> for cross-surface links,")
        msg.append("navigateToSurface(slug, params) for cross-surface button triggers,")
        msg.append("or useSurfaceParam(slug).set(...) for intra-surface deep-link state.")
        msg.append("If this is a genuine pre-existing site not yet swept, add it to ALLOWLIST.")
        raise AssertionError("\n".join(msg))


if __name__ == "__main__":
    vs = find_violations()
    if not vs:
        print("✅ nav guard: 0 cross-surface hard-navigations (clean or fully allowlisted)")
        sys.exit(0)
    print(f"⚠️  nav guard: {len(vs)} violations not yet allowlisted\n")
    print("# --- suggested ALLOWLIST seed (paste into ALLOWLIST, then sweep down) ---")
    for rel, lineno, line, reason in vs:
        frag = line[:60].replace('"', '\\"')
        print(f'    "{rel}::{frag[:40]}",  # {reason[:40]}')
    print(f"\n# total: {len(vs)}")
    sys.exit(1)
