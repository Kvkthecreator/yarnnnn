"""Regression guard — the address bar's PATHNAME follows the foreground.

Operator-observed (KVK 2026-08-20): every browser refresh landed on User
Settings → Account, whatever surface was actually on screen.

ROOT CAUSE — two rules that cannot both hold:

  1. `reconcileUrl` (lib/shell/useSurfacePreferences.tsx) rewrote only the
     QUERY STRING and preserved `url.pathname` verbatim. That was ADR-297
     D19.2 as written: "the Dock indicator dot is the canonical
     what's-foregrounded signal, not the URL". So a bare foreground — dock
     click, launcher, clicking a window body — flipped the window while the
     address bar kept naming the surface you left.

  2. The cold-load sync (components/shell/AuthenticatedLayout.tsx, 2026-08-05)
     treats the pathname as EXPLICIT INTENT and foregrounds whatever it names,
     deliberately OUTRANKING the remembered posture.

Rule 1 leaves a stale pathname; rule 2 makes the reload trust it. The
observed URL was `/settings?provider=notion&status=connected&
workspace-settings.pane=danger` — a pathname from the last param-bearing
navigate, carrying a param namespaced to a DIFFERENT surface. D19.2 is
withdrawn: the pathname now follows the foreground.

WHY THIS GATE EXECUTES RATHER THAN GREPS: a text search cannot tell a real
pathname rewrite from a comment describing one, and the sibling lesson is on
the record (a gate assertion matching its own explanatory comment). So this
gate strips the types off the REAL `lib/shell/route-sync.ts` and RUNS
`resolveForegroundPathname` in node against the actual gestures. Falsified
against the pre-fix shape (return the current pathname unchanged): checks in
group 2 fail.

Run: cd api && python3 test_adr297_pathname_follows_foreground.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB = REPO_ROOT / "web"
ROUTE_SYNC = WEB / "lib" / "shell" / "route-sync.ts"
LAYOUT = WEB / "components" / "shell" / "AuthenticatedLayout.tsx"
PREFS = WEB / "lib" / "shell" / "useSurfacePreferences.tsx"

_passed = 0
_failed = 0


def _assert(cond: bool, msg: str) -> None:
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"  PASS  {msg}")
    else:
        _failed += 1
        print(f"  FAIL  {msg}")


def _strip_types(ts: str) -> str:
    """route-sync.ts is import-free plain TS; drop the annotations so node runs
    the REAL source (not a hand-copied JS twin that could drift from it)."""
    out = re.sub(r"^export interface [\s\S]*?^}", "", ts, flags=re.M)
    out = out.replace("export function", "function")
    # Param + return type annotations, longest-first so `: string | null` and
    # `: RouteSurfaceEntry[]` are consumed before the bare `: string`.
    out = out.replace("(s: RouteSurfaceEntry): string", "(s)")
    out = re.sub(r"(\w+):\s*RouteSurfaceEntry\[\]", r"\1", out)
    out = re.sub(r"(\w+):\s*string\b", r"\1", out)
    out = re.sub(r"\):\s*string \| null \{", ") {", out)
    out = re.sub(r"\):\s*string \{", ") {", out)
    return out


def _run_node(script: str) -> dict:
    src = _strip_types(ROUTE_SYNC.read_text())
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False) as fh:
        fh.write(src + "\n" + script)
        path = fh.name
    res = subprocess.run(["node", path], capture_output=True, text=True)
    Path(path).unlink(missing_ok=True)
    if res.returncode != 0:
        raise RuntimeError(f"node failed: {res.stderr}")
    return json.loads(res.stdout)


# The live roster shape (slug + route), as the compositor serves it.
ROSTER = [
    {"slug": "chat", "route": "/chat"},
    {"slug": "files", "route": "/files"},
    {"slug": "settings", "route": "/settings"},
    {"slug": "workspace-settings", "route": "/workspace-settings"},
    {"slug": "studio", "route": "/studio"},
    {"slug": "agents", "route": "/agents"},
]


def test_the_operator_gesture() -> None:
    """Group 2 — the reported bug, driven as the gesture that produced it."""
    print("\n[2] the pathname follows the foreground (the reported bug)")

    roster = json.dumps(ROSTER)
    out = _run_node(
        f"""
const R = {roster};
const r = (p, s) => resolveForegroundPathname(p, s, R);
console.log(JSON.stringify({{
  // THE REPORTED BUG: sitting on /settings (last param-bearing navigate),
  // then dock-clicking Files. Pre-fix this returned '/settings', so the
  // refresh re-foregrounded Settings.
  settings_to_files: r('/settings', 'files'),
  settings_to_chat: r('/settings', 'chat'),
  // Any cross-surface foreground moves the pathname.
  chat_to_studio: r('/chat', 'studio'),
  files_to_agents: r('/files', 'agents'),
  // The desktop baseline is not sticky either.
  desktop_to_files: r('/desktop', 'files'),
  // Sibling routes that share a prefix must not be confused for sub-paths.
  settings_to_workspace_settings: r('/settings', 'workspace-settings'),
  workspace_settings_to_settings: r('/workspace-settings', 'settings'),
}}));
"""
    )

    _assert(
        out["settings_to_files"] == "/files",
        "REPORTED BUG: on /settings, foregrounding files → pathname '/files' "
        f"(got {out['settings_to_files']!r}) — a refresh now reloads Files",
    )
    _assert(
        out["settings_to_chat"] == "/chat",
        f"on /settings, foregrounding chat → '/chat' (got {out['settings_to_chat']!r})",
    )
    _assert(
        out["chat_to_studio"] == "/studio",
        f"cross-surface foreground moves the pathname (got {out['chat_to_studio']!r})",
    )
    _assert(
        out["files_to_agents"] == "/agents",
        f"files → agents rewrites (got {out['files_to_agents']!r})",
    )
    _assert(
        out["desktop_to_files"] == "/files",
        f"the /desktop baseline is not sticky (got {out['desktop_to_files']!r})",
    )
    # `/settings` is a string-prefix of nothing here, but `/workspace-settings`
    # vs `/settings` is the pair most likely to be mishandled by a naive
    # startsWith — and they are the two doors in the reported URL.
    _assert(
        out["settings_to_workspace_settings"] == "/workspace-settings",
        "the two Settings doors are distinct routes, not sub-paths "
        f"(got {out['settings_to_workspace_settings']!r})",
    )
    _assert(
        out["workspace_settings_to_settings"] == "/settings",
        f"...and in reverse (got {out['workspace_settings_to_settings']!r})",
    )


def test_the_guards_hold() -> None:
    """Group 3 — the two cases that must KEEP the current pathname."""
    print("\n[3] the guards: route-less rows and deeper sub-paths keep the path")

    roster = json.dumps(ROSTER + [{"slug": "seeded", "route": ""}])
    out = _run_node(
        f"""
const R = {roster};
const r = (p, s) => resolveForegroundPathname(p, s, R);
console.log(JSON.stringify({{
  // A route-less roster row (the seeded chrome-only composition, or a
  // program row that omitted its route) must never blank the pathname.
  routeless: r('/files', 'seeded'),
  unknown_slug: r('/files', 'no-such-surface'),
  // Already AT the route — no churn.
  already_there: r('/files', 'files'),
  // A deeper sub-path is MORE specific than the bare route; keep it.
  deeper: r('/files/some/nested/path', 'files'),
  // A non-string route on the wire (the roster is best-effort at the
  // program tier — see route-sync.routeOf) must not crash or blank.
  nonstring: r('/files', 'bad'),
}}));
""".replace(
            '{"slug": "seeded", "route": ""}',
            '{"slug": "seeded", "route": ""}, {"slug": "bad", "route": 42}',
        )
    )

    _assert(
        out["routeless"] == "/files",
        f"a route-less roster row keeps the pathname (got {out['routeless']!r})",
    )
    _assert(
        out["unknown_slug"] == "/files",
        f"an unknown slug keeps the pathname (got {out['unknown_slug']!r})",
    )
    _assert(
        out["already_there"] == "/files",
        f"already at the route → unchanged (got {out['already_there']!r})",
    )
    _assert(
        out["deeper"] == "/files/some/nested/path",
        f"a deeper sub-path is kept, not flattened (got {out['deeper']!r})",
    )
    _assert(
        out["nonstring"] == "/files",
        f"a non-string route on the wire degrades safely (got {out['nonstring']!r})",
    )


def test_the_two_rules_agree() -> None:
    """Group 4 — the round-trip that WAS the bug.

    The cold-load sync resolves pathname→slug; reconcileUrl resolves
    slug→pathname. They are inverses. If they disagree, a refresh lands
    somewhere other than where you were — which is exactly what happened.
    """
    print("\n[4] round-trip: what reconcileUrl writes, the cold-load sync reads back")

    roster = json.dumps(ROSTER)
    out = _run_node(
        f"""
const R = {roster};
const slugs = R.map((s) => s.slug);
const roundTrip = {{}};
for (const slug of slugs) {{
  // Start from an unrelated pathname (the bug's shape), foreground `slug`,
  // then read the written pathname back the way a refresh would.
  const written = resolveForegroundPathname('/settings', slug, R);
  roundTrip[slug] = resolveRouteSurface(written, R);
}}
console.log(JSON.stringify(roundTrip));
"""
    )

    for slug in [s["slug"] for s in ROSTER]:
        _assert(
            out[slug] == slug,
            f"foreground '{slug}' → the pathname a refresh reads back is '{slug}' "
            f"(got {out[slug]!r})",
        )


def test_the_withdrawal_is_recorded() -> None:
    """Group 5 — D19.2's withdrawal is written down where the next reader looks.

    Not a spelling pin: this asserts the two files that ASSERTED the old rule
    no longer assert it, by checking the live claim is absent rather than that
    some new sentence is present.
    """
    print("\n[5] the withdrawn D19.2 claim is gone from the live docs")

    prefs = PREFS.read_text()
    # The pre-fix docblocks stated the pathname is preserved. Those exact
    # claims must not survive a change that makes them false.
    _assert(
        "URL stays as-is per D19.2" not in prefs,
        "the 'URL stays as-is per D19.2' claim is withdrawn from navigateToSurface",
    )
    _assert(
        "Pathname is preserved (the `/desktop` baseline, ADR-358 D5)" not in prefs,
        "the 'Pathname is preserved' claim is gone from reconcileUrl + navigateToSurface",
    )
    # reconcileUrl must actually route through the extracted decision — the
    # one place a rewrite can happen — rather than hand-rolling a second copy.
    _assert(
        "resolveForegroundPathname(" in prefs,
        "reconcileUrl calls the extracted resolveForegroundPathname",
    )
    # Count CALLS, not mentions. The docstring at the `setSurfaceParams`
    # interface describes the mechanism in prose ("Mechanism:
    # `window.history.replaceState(null, '', <current-pathname>?<params>)`"),
    # and a naive substring count read that comment as a third writer — the
    # gate matching its own explanatory text. Strip comment lines first.
    code_lines = [
        ln
        for ln in prefs.splitlines()
        if not ln.lstrip().startswith(("*", "//", "/*"))
    ]
    call_sites = sum(ln.count("window.history.replaceState") for ln in code_lines)
    _assert(
        call_sites == 2,
        "still exactly TWO replaceState CALL sites (reconcileUrl + setSurfaceParams) — "
        f"no third URL writer appeared (found {call_sites})",
    )
    # setSurfaceParams is INTRA-surface: it must keep preserving the pathname.
    # If this ever routes through resolveForegroundPathname, switching entity
    # inside a window would flip the URL — the D19.6 disruption.
    intra = prefs[prefs.index("const setSurfaceParams"):]
    intra = intra[: intra.index("// 2026-06-25 — mirror the change")]
    _assert(
        "resolveForegroundPathname" not in intra,
        "setSurfaceParams (INTRA-surface) still preserves the pathname — D19.6 intact",
    )


if __name__ == "__main__":
    print("ADR-297 D19.2 withdrawal — the pathname follows the foreground")
    test_the_operator_gesture()
    test_the_guards_hold()
    test_the_two_rules_agree()
    test_the_withdrawal_is_recorded()

    print(f"\n{'='*60}")
    print(f"pathname-follows-foreground gate: {_passed} passed, {_failed} failed")
    print(f"{'='*60}")
    sys.exit(0 if _failed == 0 else 1)
