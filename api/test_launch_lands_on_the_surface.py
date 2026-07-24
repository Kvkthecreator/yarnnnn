"""
The dock icon opens the SURFACE, not the object you drilled into (2026-07-24).

Operator-observed (KVK): clicking the Studio dock icon reopened an artifact
from an arbitrary earlier session instead of Studio's landing. `studio.file`
is a `useSurfaceParam`, so it lived in `WindowState.params` — the remembered
set that `reconcileUrl` replays into the URL on EVERY foreground. `remembered`
outranks `incoming` in that merge and nothing ever CLEARED it (only opening a
different file overwrote it), so one artifact became the permanent landing
target across refreshes, sessions, and — via the ADR-407 server write-through —
devices. Any remembered value with no clearing path has this shape.

The carve is DRILL-INS, not all params — the question is whether replaying it
answers something the member is asking NOW:

  RESTORE       `settings.pane` (a resting posture), `chat.lane` (a place you
                live in — Slack/Messages/Mail resume the last thread, and the
                lane list sits beside it).
  DON'T RESTORE `studio.file` / `images.file` / `.system` (the artifact you
                were authoring — the app is not that document) and
                `agents.agent` (a drill-in on a roster whose POINT is the list).

Both stay OWNED, so an incoming deep-link, a shared URL, and a delivered
navigateToSurface param still land — those carry PRESENT intent.

This gate EXECUTES the merge rather than grepping for it. A source-text check
would pass on a `stripEphemeralParams` that was defined and never called, or
called with the arguments transposed — the precise failures worth catching.
The TS merge body is transliterated below and kept honest by assertion 0, which
fails if reconcileUrl's real merge stops matching the shape modelled here.

Run directly: `python test_launch_lands_on_the_surface.py`.
"""

import os
import re
import sys

_HERE = os.path.dirname(__file__)
_WEB = os.path.join(_HERE, "..", "web")

PREFS = "lib/shell/surface-preferences.ts"
HOOK = "lib/shell/useSurfacePreferences.tsx"
TOPBAR = "components/shell/chrome/TopBarSurface.tsx"


def _read(rel: str) -> str:
    p = os.path.join(_WEB, rel)
    return open(p, encoding="utf-8").read() if os.path.exists(p) else ""


def _check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}")
    return bool(ok)


# ---------------------------------------------------------------------------
# The two tables, parsed FROM the TypeScript source. Parsing (rather than
# duplicating) means the gate tracks the real allowlists: add `pane` to Studio's
# owned keys and this gate re-derives it, so the executable assertions below run
# against what actually ships.
# ---------------------------------------------------------------------------
def _parse_key_table(src: str, const_name: str) -> dict:
    m = re.search(
        rf"const {const_name}: Record<string, readonly string\[\]> = \{{(.*?)\n\}};",
        src,
        re.DOTALL,
    )
    if not m:
        return {}
    table = {}
    for slug, keys in re.findall(r"^\s*(\w+): \[([^\]]*)\],", m.group(1), re.M):
        table[slug] = re.findall(r"'([^']+)'", keys)
    return table


def _normalize_window_params(owned, slug, params):
    """Transliteration of normalizeWindowParams."""
    allowed = owned.get(slug)
    if allowed is None:
        return dict(params)
    return {k: v for k, v in params.items() if k in allowed}


def _strip_ephemeral(ephemeral, slug, params):
    """Transliteration of stripEphemeralParams."""
    keys = ephemeral.get(slug)
    if keys is None:
        return dict(params)
    return {k: v for k, v in params.items() if k not in keys}


def _reconcile(owned, ephemeral, slug, incoming, remembered, delivered):
    """The reconcileUrl merge: incoming < stripEphemeral(remembered) < delivered."""
    merged = dict(incoming)
    merged.update(_strip_ephemeral(ephemeral, slug, remembered))
    merged.update(delivered)
    return _normalize_window_params(owned, slug, merged)


def run() -> int:
    passed = True
    prefs = _read(PREFS)
    hook = _read(HOOK)
    topbar = _read(TOPBAR)

    owned = _parse_key_table(prefs, "SURFACE_PARAM_KEYS")
    ephemeral = _parse_key_table(prefs, "SURFACE_EPHEMERAL_PARAM_KEYS")

    passed &= _check(
        "both param tables parse out of surface-preferences",
        bool(owned) and bool(ephemeral),
        f"owned={sorted(owned)} ephemeral={sorted(ephemeral)}",
    )
    if not owned or not ephemeral:
        return 1  # nothing below is meaningful without the tables

    # ── 0. the model matches the real merge ───────────────────────────────
    # If reconcileUrl's precedence or its strip call changes, the executable
    # assertions below stop describing shipped behaviour. Pin the three facts
    # the transliteration depends on.
    merge = re.search(
        r"const remembered =\s*stripEphemeralParams\(\s*(.*?)\s*\)\s*\?\?\s*\{\};"
        r"\s*const merged.*?normalizeWindowParams\(foregroundSlug,\s*\{(.*?)\}\)",
        hook,
        re.DOTALL,
    )
    order_ok = False
    if merge:
        spread = merge.group(2)
        order_ok = (
            spread.index("...incoming")
            < spread.index("...remembered")
            < spread.index("...(deliverParams")
        )
    passed &= _check(
        "reconcileUrl strips the remembered source, precedence incoming<remembered<delivered",
        bool(merge) and order_ok,
        "" if merge else "merge shape not found — the model below may be stale",
    )
    passed &= _check(
        "stripEphemeralParams is applied to remembered, NOT to incoming/delivered",
        bool(merge) and "windowStatesRef" in merge.group(1),
        "" if merge else "call site not found",
    )

    # ── 1. THE BUG: a bare launch no longer resumes the artifact ──────────
    for slug in ("studio", "images"):
        stale = {"file": "artifacts/march-deck.html"}
        out = _reconcile(owned, ephemeral, slug, {}, stale, {})
        passed &= _check(
            f"{slug}: bare dock click drops the remembered artifact → landing",
            out == {},
            f"got {out}",
        )
        stale_sys = {"system": "systems/brand.yaml"}
        out = _reconcile(owned, ephemeral, slug, {}, stale_sys, {})
        passed &= _check(
            f"{slug}: bare dock click drops the remembered design system",
            out == {},
            f"got {out}",
        )

    # ── 2. present intent STILL lands (the regression this must not cause) ─
    # Stripping too broadly would break deep-links, "open in Studio" from
    # Files, and in-session opens — the whole reason `file` stays OWNED.
    out = _reconcile(
        owned, ephemeral, "studio", {"file": "artifacts/shared.html"}, {}, {}
    )
    passed &= _check(
        "an incoming URL deep-link still opens the artifact",
        out == {"file": "artifacts/shared.html"},
        f"got {out}",
    )
    out = _reconcile(
        owned, ephemeral, "studio", {}, {}, {"file": "artifacts/opened.html"}
    )
    passed &= _check(
        "a delivered param (navigateToSurface from Files) still opens the artifact",
        out == {"file": "artifacts/opened.html"},
        f"got {out}",
    )
    out = _reconcile(
        owned,
        ephemeral,
        "studio",
        {"file": "artifacts/stale-link.html"},
        {"file": "artifacts/remembered.html"},
        {"file": "artifacts/clicked.html"},
    )
    passed &= _check(
        "delivered outranks incoming and remembered",
        out == {"file": "artifacts/clicked.html"},
        f"got {out}",
    )

    # ── 3. the roster's front door is the roster ──────────────────────────
    # Weaker than the authoring case (nothing is authored in a profile), but a
    # launch landing on one colleague answers a question asked days ago.
    out = _reconcile(owned, ephemeral, "agents", {}, {"agent": "freddie"}, {})
    passed &= _check(
        "agents: bare dock click drops the remembered profile → roster",
        out == {},
        f"got {out}",
    )
    out = _reconcile(owned, ephemeral, "agents", {}, {}, {"agent": "freddie"})
    passed &= _check(
        "agents: a delivered profile param still opens the detail",
        out == {"agent": "freddie"},
        f"got {out}",
    )

    # ── 4. what a launch SHOULD restore is untouched ──────────────────────
    # The carve is drill-ins, not all params. A conversation is a place you
    # live in (Slack/Messages/Mail resume the last thread, and the lane list
    # sits beside it); a settings pane is a resting posture.
    out = _reconcile(owned, ephemeral, "chat", {}, {"lane": "lane-42"}, {})
    passed &= _check(
        "chat: the remembered lane STILL replays (a conversation is not a drill-in)",
        out == {"lane": "lane-42"},
        f"got {out}",
    )
    out = _reconcile(
        owned, ephemeral, "workspace-settings", {}, {"pane": "access"}, {}
    )
    passed &= _check(
        "an unconstrained surface's remembered pane still replays",
        out == {"pane": "access"},
        f"got {out}",
    )

    # ── 5. every ephemeral key is also an owned key ───────────────────────
    # A key stripped from remembered but absent from the owned allowlist would
    # be silently eaten on the incoming path too — the deep-link would die.
    for slug, keys in ephemeral.items():
        missing = [k for k in keys if k not in owned.get(slug, [])]
        passed &= _check(
            f"{slug}: every ephemeral key is owned (deep-links survive)",
            not missing,
            f"unowned: {missing}" if missing else "",
        )

    # ── 6. canvas dock-click-on-active is a no-op ─────────────────────────
    # Minimize is a windowed gesture; in canvas one chromeless surface fills
    # the column, so minimizing drops to an empty desktop with no visible
    # change to the icon. Structural check — the handler is React-bound.
    handler = re.search(
        r"} else if \(isForegrounded\) \{(.*?)\n      \} else \{", topbar, re.DOTALL
    )
    body = handler.group(1) if handler else ""
    guard_ok = (
        bool(handler)
        and "if (canvasMode) return;" in body
        and "minimizeWindow" in body
        and body.index("if (canvasMode) return;") < body.index("minimizeWindow")
    )
    passed &= _check(
        "dock click on the foregrounded icon returns early in canvas mode",
        guard_ok,
        "" if guard_ok else "branch not found, guard missing, or guard after minimizeWindow",
    )
    passed &= _check(
        "canvasMode is derived from the shell's layoutMode",
        "layoutMode } = useShellChrome()" in topbar
        and "const canvasMode = layoutMode === 'canvas';" in topbar,
    )

    print()
    print("RESULT:", "PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(run())
