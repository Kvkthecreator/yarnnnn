"""ADR-641 — the app + agent marks carry an accent.

WHAT THIS GATE HOLDS

The shell's iconography was uniformly monotone while THREE colored-icon
registries already shipped (`studioShapes.ts`, `FileIcon.tsx`,
`attribution.ts::authorAccent`). ADR-641 closes that inconsistency by giving
the two registries that missed it — `surface-icons.tsx` (apps) and
`root-icons.tsx` (the Files spine) — an accent map beside the glyph map, in
the `studioShapes` shape: a record of Tailwind classes with a NEUTRAL
fallback, so an undeclared row renders exactly as it did before.

WHY THE CHECKS ARE SHAPED THIS WAY

⭐ ASSERT THE RELATION, IN BOTH DIRECTIONS. A negative check ("X no longer
claims docs") pins the last deletion and cannot catch a forgotten ADDITION —
the ADR-636 §9 lesson, and the reason the six hand-kept FE app lists agreed
by memory rather than by construction. So §2 asserts that every accented
surface slug is a slug some surface actually declares (no phantom rows) AND
that the four authoring apps each carry one (no forgotten additions).

⭐ ASSERT THE FACT, NEVER THE SPELLING. A gate that pins `text-violet-500`
pins the defect the moment the palette moves. These checks assert that a hue
EXISTS where identity is claimed and is ABSENT where state speaks — never
which hue it is. The one exception is the semantic-reservation check (§4),
where the specific families red/amber ARE the fact being protected.

⭐ THE UNEXERCISED HALF IS WHERE THE BUG IS. §5 covers the DELETION half of
this change (the WorkspaceTree path-string ladder) rather than only the
addition, because a re-added fallback would silently restore the inversion
ADR-641 exists to fix — and would do it without breaking any check that only
looked at the new maps.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WEB = REPO / "web"

SURFACE_ICONS = WEB / "lib/shell/surface-icons.tsx"
ROOT_ICONS = WEB / "lib/workspace/root-icons.tsx"
AGENT_ICON = WEB / "components/agents/AgentIcon.tsx"
WORKSPACE_TREE = WEB / "components/workspace/WorkspaceTree.tsx"
TOP_BAR = WEB / "components/shell/chrome/TopBarSurface.tsx"

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


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _record_keys(src: str, const_name: str) -> set[str]:
    """The keys of a `const NAME: Record<...> = { ... }` literal.

    Parsed rather than imported because these are TSX. Brace-counted from the
    opening `{` so a nested object or a comment brace cannot truncate the read.
    """
    m = re.search(rf"const {const_name}[^=]*=\s*\{{", src)
    if not m:
        return set()
    i = m.end() - 1
    depth = 0
    for j in range(i, len(src)):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                body = src[i + 1 : j]
                break
    else:
        return set()
    # Strip comments so a commented-out row is not read as live.
    body = re.sub(r"//[^\n]*", "", body)
    body = re.sub(r"/\*.*?\*/", "", body, flags=re.DOTALL)
    keys = set()
    for km in re.finditer(r"^\s*'?([A-Za-z0-9_-]+)'?\s*:", body, re.MULTILINE):
        keys.add(km.group(1))
    return keys


# =============================================================================
# Group 1 — both accent resolvers exist and fall back neutrally
# =============================================================================


def test_resolvers_exist_and_degrade() -> None:
    print("\n[1] the accent resolvers exist and degrade to neutral")

    surf = _read(SURFACE_ICONS)
    roots = _read(ROOT_ICONS)

    _assert(
        "export function resolveSurfaceAccent" in surf,
        "surface-icons.tsx exports resolveSurfaceAccent",
    )
    _assert(
        "export function resolveRootAccent" in roots,
        "root-icons.tsx exports resolveRootAccent",
    )

    # The soft fallback is the whole reason this is safe to add: an undeclared
    # surface must render exactly as it did before ADR-641. A resolver that
    # threw, or returned '', would make a missing row a visible defect.
    for name, src, fn in (
        ("surface", surf, "resolveSurfaceAccent"),
        ("root", roots, "resolveRootAccent"),
    ):
        body = src.split(f"export function {fn}")[1]
        _assert(
            body.count("text-muted-foreground") >= 2,
            f"{fn} returns the neutral tone for both the null and "
            f"the unmapped case (the {name} registry degrades, never throws)",
        )


# =============================================================================
# Group 2 — the surface accents name real surfaces, in both directions
# =============================================================================


def test_surface_accents_match_declared_surfaces() -> None:
    print("\n[2] every accented slug is a real surface; every app has an accent")

    sys.path.insert(0, str(REPO / "api"))
    from services.kernel_surfaces import KERNEL_SURFACES  # noqa: E402

    declared = {s["slug"] for s in KERNEL_SURFACES}
    accented = _record_keys(_read(SURFACE_ICONS), "SURFACE_ACCENTS")

    _assert(bool(accented), "SURFACE_ACCENTS parsed a non-empty key set")

    # Direction 1 — no PHANTOM rows. An accent for a slug no surface declares
    # is dead weight that reads as live (the orphan-mapping rule, CLAUDE.md §2).
    phantom = accented - declared
    _assert(
        not phantom,
        f"No accent names an undeclared surface (phantoms: {sorted(phantom)})",
    )

    # Direction 2 — no forgotten ADDITIONS. The four authoring apps are the
    # rows a member must tell apart at a glance; that is the whole point of
    # the change, so a new app arriving without an accent must go red.
    #
    # Derived from the backend's own app registry rather than hand-spelled —
    # a hand-listed census is the ADR-636 §9 defect (a gate that pins a
    # spelling pins the drift it was written to catch).
    # ⚠️ The `import services.apps` is LOAD-BEARING, not tidiness: apps register
    # by import side-effect (ADR-562), so without it `all_apps()` returns only
    # whatever a prior import happened to pull in. Omitting it made this very
    # check pass vacuously over ONE app while claiming to cover four — caught
    # by falsifying it (removing an app's accent stayed green).
    import services.apps  # noqa: F401,E402  (registration side-effect)
    from services.authoring import all_apps  # noqa: E402

    app_slugs = set(all_apps())
    _assert(
        len(app_slugs) >= 4,
        f"The app registry is actually loaded before the parity check "
        f"(found {len(app_slugs)}: {sorted(app_slugs)})",
    )
    missing = app_slugs - accented
    _assert(
        not missing,
        f"Every registered app carries an accent (missing: {sorted(missing)})",
    )


# =============================================================================
# Group 3 — the root accents name real roots, in both directions
# =============================================================================


def test_root_accents_match_declared_roots() -> None:
    print("\n[3] every root icon has an accent, and vice versa")

    from services.workspace_paths import WORKSPACE_ROOTS  # noqa: E402

    root_icons = {r["icon"] for r in WORKSPACE_ROOTS.values() if r.get("icon")}
    src = _read(ROOT_ICONS)
    glyphs = _record_keys(src, "ROOT_ICON_REGISTRY")
    accents = _record_keys(src, "ROOT_ACCENTS")

    _assert(bool(glyphs) and bool(accents), "both root records parsed")

    # Every kernel-named root glyph must resolve to BOTH a component and a hue.
    # `file-cog` is in the registries but not in WORKSPACE_ROOTS — it is the
    # Files page's loose-machine-file node (ADR-457 P3), so it is checked in
    # the glyph direction below rather than sourced from the roots table.
    _assert(
        not (root_icons - glyphs),
        f"Every WORKSPACE_ROOTS icon has a glyph "
        f"(missing: {sorted(root_icons - glyphs)})",
    )
    _assert(
        not (root_icons - accents),
        f"Every WORKSPACE_ROOTS icon has an accent "
        f"(missing: {sorted(root_icons - accents)})",
    )

    # The two maps must stay in lockstep. A glyph without a hue renders grey in
    # a spine that is otherwise accented (the inversion, returning); a hue
    # without a glyph is an orphan.
    _assert(
        glyphs == accents,
        f"ROOT_ICON_REGISTRY and ROOT_ACCENTS cover the same keys "
        f"(glyph-only: {sorted(glyphs - accents)}, "
        f"accent-only: {sorted(accents - glyphs)})",
    )

    # ADR-641 fixed this specifically: a loose machine FILE was drawn with the
    # generic FOLDER glyph because `file-cog` had no row.
    _assert(
        "file-cog" in glyphs,
        "'file-cog' resolves to a real glyph (a machine file is not a folder)",
    )


# =============================================================================
# Group 4 — accent is identity; state and semantics keep their own colours
# =============================================================================


def test_accent_never_speaks_state_or_alarm() -> None:
    print("\n[4] accent says WHICH, never WHAT-STATE and never ALARM")

    surf = _read(SURFACE_ICONS)
    # Strip comments FIRST. This block DOCUMENTS why amber is reserved, so a
    # raw substring check goes red on its own explanation — the exact defect in
    # `feedback_a_gate_check_that_matches_its_own_documentation`. Assert the
    # ROW (a `slug: 'text-<hue>'` value), never the prose around it.
    accents_body = surf.split("const SURFACE_ACCENTS")[1].split("};")[0]
    accents_body = re.sub(r"//[^\n]*", "", accents_body)
    declared_hues = re.findall(r":\s*'(text-[a-z]+-\d+)'", accents_body)
    _assert(bool(declared_hues), "SURFACE_ACCENTS declares at least one hue")

    # Red + amber mean "wrong / wants you" in this shell (--destructive on the
    # notification badge, the amber attention rows). A quiet app wearing one
    # would read as an alarm. This is the one place a specific hue family IS
    # the fact, so it is named.
    for family in ("red", "amber"):
        offenders = [h for h in declared_hues if h.startswith(f"text-{family}-")]
        _assert(
            not offenders,
            f"No surface accent uses the reserved family '{family}' "
            f"(red/amber are semantic: destructive + attention) "
            f"— offenders: {offenders}",
        )

    # The Dock encodes STATE with colour already (foregrounded → the inverted
    # slab; kept-not-open → /50). An accent painted unconditionally would put
    # two colour languages on one 9x9 icon — the ADR-258 fault. The call site
    # must gate on both state facts.
    bar = _read(TOP_BAR)
    _assert(
        "!isForegrounded && surfaceIsOpen && accent" in bar,
        "The Dock applies the accent ONLY to the open-and-backgrounded cell "
        "(state keeps the foregrounded + kept-not-open cells)",
    )


# =============================================================================
# Group 5 — the DELETION half: the path-string ladder does not come back
# =============================================================================


def test_the_path_string_ladder_stays_deleted() -> None:
    print("\n[5] the WorkspaceTree path-guess ladder stays deleted")

    tree = _read(WORKSPACE_TREE)
    body = tree.split("function folderIcon")[1].split("\n}")[0]
    # Strip comments — this file DOCUMENTS the deleted paths, and a substring
    # check that matches its own explanation is the gate defect recorded in
    # `feedback_a_gate_check_that_matches_its_own_documentation`.
    code = re.sub(r"//[^\n]*", "", body)

    # The inversion ADR-641 fixes: the DEAD fallback carried the spine's only
    # hues while the LIVE registry rendered grey. Re-adding any path-string
    # branch restores it, and would do so without touching the new maps.
    _assert(
        "node.path" not in code,
        "folderIcon does not read node.path (no path-string glyph guessing)",
    )
    _assert(
        "/explorer/" not in code and "/workspace/" not in code,
        "folderIcon hard-codes no substrate paths",
    )
    _assert(
        "resolveRootIcon" in code and "resolveRootAccent" in code,
        "folderIcon resolves BOTH glyph and accent from the root registry",
    )


# =============================================================================
# Group 6 — the agent mark is one hue for the class
# =============================================================================


def test_agent_accent_is_class_wide() -> None:
    print("\n[6] the agent glyph carries one accent for the class")

    src = _read(AGENT_ICON)

    _assert(
        "AGENT_ACCENT" in src,
        "AgentIcon declares an accent",
    )

    # NOT keyed per-agent and NOT keyed on the agent's app. Since ADR-601 D1 an
    # agent may serve several apps (Editor -> Slides + Text), so an app-derived
    # hue has no single answer for exactly the many-to-one case that ADR made
    # free. A Record keyed by agent or app slug here would be that regression.
    #
    # Asserted on the CONSTRUCT (one constant, not a lookup), never on the hue.
    _assert(
        not re.search(r"const AGENT_ACCENTS?\s*:\s*Record", src),
        "The agent accent is a single constant, not a per-agent/per-app map "
        "(ADR-601 many-to-one has no single app hue to derive from)",
    )

    agents_surface = _read(WEB / "components/agents/AgentsSurface.tsx")
    _assert(
        "resolveSurfaceAccent(app.slug)" in agents_surface,
        "The app CHIPS carry the per-app accent (the glyph says 'an agent', "
        "the chips say which apps)",
    )


if __name__ == "__main__":
    test_resolvers_exist_and_degrade()
    test_surface_accents_match_declared_surfaces()
    test_root_accents_match_declared_roots()
    test_accent_never_speaks_state_or_alarm()
    test_the_path_string_ladder_stays_deleted()
    test_agent_accent_is_class_wide()

    print(f"\n{'='*60}")
    print(f"ADR-641 icon accent gate: {_passed} passed, {_failed} failed")
    print(f"{'='*60}")
    sys.exit(0 if _failed == 0 else 1)
