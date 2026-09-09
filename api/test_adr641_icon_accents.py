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
API = REPO / "api"

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


def test_the_face_fallback_carries_the_class_accent() -> None:
    """§7 — the FACE fallback (ADR-641 amendment, 2026-09-08).

    THE DEFECT THIS PINS. ADR-641 shipped green at 23/23 while Designer
    rendered a grey "D" in the Slides chat pane and violet two surfaces away
    on Agents. The gate could not see it: it asserted the REGISTRIES agree,
    and nothing asserted that the chat surfaces consult them at all. ⭐ A
    green gate is not a look — and the checks below are the structural half
    of that lesson, because the visual half cannot be automated.

    WHY THE CHECK IS ON THE PROP, NOT THE COLOUR. The cause was never CSS:
    `AgentFace` took `name` + `avatarUrl` (both display STRINGS), so all five
    call sites threw away a `member_kind` they already held, and no styling
    inside the component could have coloured the fallback correctly because
    the information never arrived. The fix is that `kind` is REQUIRED — a new
    chat surface cannot compile without answering "who is this?". So this
    asserts the CONTRACT (required prop, every call site passes it), which is
    what actually prevents the drift; asserting the hue would pin a spelling
    and still let a sixth silent call site appear.

    ⭐ ASSERT BOTH DIRECTIONS (ADR-636 §9). The negative — "no call site omits
    kind" — cannot catch a NEW component that hand-rolls its own initial disc,
    which is exactly the second home found and deleted in ConversationDetail's
    invite list. So the second check sweeps the chat surfaces for a rounded
    initial rendered OUTSIDE AgentFace.
    """
    print("\n[7] the face fallback carries the class accent")

    face = _read(WEB / "components/agents/AgentFace.tsx")

    # REQUIRED, no `?`, no default — the ADR-633 rule. An optional kind with
    # an `?? 'human'` fallback restores the exact silence this deletes.
    _assert(
        re.search(r"^\s*kind:\s*PrincipalKind;", face, re.M) is not None,
        "AgentFace REQUIRES a `kind` (no `?`, no default — an optional class "
        "would let a new call site silently render grey again)",
    )
    _assert(
        not re.search(r"kind\s*\?\s*:", face)
        and not re.search(r"kind\s*=\s*['\"]", face),
        "AgentFace declares no default for `kind` (a declaration nothing "
        "declares is not a declaration — ADR-592's inert `stage`)",
    )
    # The picture stays unaccented: the 2026-07-16 operator ruling that a face
    # is an uploaded IMAGE, not a colour swatch, survives this amendment.
    _assert(
        "faceAccent(kind)" in face,
        "The fallback resolves its accent through the shared `faceAccent` "
        "(one vocabulary with authorAccent, not a second palette)",
    )

    attribution = _read(WEB / "lib/workspace/attribution.ts")
    _assert(
        "export function faceAccent" in attribution
        and "export type PrincipalKind" in attribution,
        "`faceAccent` + `PrincipalKind` live BESIDE authorAccent (the dots, "
        "the glyph and the face cannot disagree about an agent)",
    )
    # Returns bg AND text together — a caller that must remember to pair them
    # is a caller that can forget, and violet-on-violet is how that reads.
    body = attribution.split("export function faceAccent", 1)[1]
    agent_row = re.search(r"case 'agent':\s*\n\s*return '([^']+)'", body)
    _assert(
        agent_row is not None
        and "bg-" in agent_row.group(1)
        and "text-" in agent_row.group(1),
        "faceAccent returns ground AND ink as one string (never a bare hue a "
        "caller has to pair correctly)",
    )

    # EVERY call site passes it. tsc enforces this too, but a gate that states
    # the rule survives a `any`-cast or a loosened prop type.
    chat_dir = WEB / "components/chat-surface"
    sites = 0
    for f in sorted(chat_dir.glob("*.tsx")):
        src = _read(f)
        for m in re.finditer(r"<AgentFace\b[^>]*?/>", src, re.S):
            sites += 1
            _assert(
                "kind=" in m.group(0),
                f"{f.name}: every <AgentFace> names the principal's kind",
            )
    _assert(sites >= 5, f"the sweep actually found the call sites ({sites} >= 5)")

    # THE ADDITION DIRECTION — a hand-rolled initial disc beside AgentFace is
    # a second home for the same rule. One was found and deleted in
    # ConversationDetail's invite list; this stops the next one.
    for f in sorted(chat_dir.glob("*.tsx")):
        src = _read(f)
        stripped = re.sub(r"<AgentFace\b.*?/>", "", src, flags=re.S)
        _assert(
            not re.search(
                r"rounded-full[^\"']*"
                r"(?=[^\"']*\bbg-muted\b)",
                stripped,
            )
            or "slice(0, 1).toUpperCase()" not in stripped,
            f"{f.name}: no hand-rolled initial disc outside AgentFace "
            "(a second home is how the first one drifted)",
        )



def test_an_agent_has_a_real_face() -> None:
    """§8 — the faces are REAL (ADR-641 amendment, 2026-09-08).

    THE DEFECT THIS PINS. `AgentFace.tsx` was built for the 2026-07-16 ruling
    (a face is an uploaded PICTURE) with the whole URL chain wired — and
    NOTHING EVER SUPPLIED ONE. `avatar_url` did not exist anywhere in the
    backend: not in the registry, not in a route, not in a payload. So every
    agent fell to its initial forever and the ruling was true on paper and
    dead in practice. The operator saw letters and asked why.

    ⭐ ASSERT THE SUPPLY, NOT THE PIXELS. A gate cannot say whether a face is
    a GOOD picture — that is what looking is for. What it can hold is that a
    face EXISTS for every kernel agent, that something SERVES it, and that the
    member's own upload outranks ours. Those are the three ways this silently
    reverts to letters.
    """
    print("\n[8] an agent has a real face")

    faces_dir = API / "services" / "agent_faces"
    _assert(faces_dir.is_dir(), "the kernel faces ship as code (services/agent_faces/)")

    # EVERY kernel agent has one. The ADDITION direction (ADR-636 §9): a new
    # agent with no face is the regression, and only a both-ways check sees it.
    reg = _read(API / "services" / "agents_registry.py")
    slugs = set(re.findall(r'^    "([a-z0-9-]+)": \{$', reg, re.M))
    shipped = {p.stem for p in faces_dir.glob("*.png")}
    _assert(len(slugs) >= 3, f"the registry sweep found the agents ({len(slugs)})")
    _assert(
        slugs <= shipped,
        f"every registered agent ships a face (missing: {sorted(slugs - shipped)})",
    )
    _assert(
        shipped <= slugs,
        f"no orphan face for a retired agent (extra: {sorted(shipped - slugs)})",
    )

    # The generator stays beside its output — an asset nobody can reproduce is
    # an asset that ossifies at the first palette change.
    _assert(
        (faces_dir / "_generate.py").exists(),
        "the generator ships beside the PNGs (a face is reproducible, not hand-drawn)",
    )

    mod = _read(faces_dir / "__init__.py")

    # ⭐ THE MEMBER'S FACE WINS — the ruling's whole point ("a face you CHOSE").
    # Asserted on the RANK, which is the mechanism, not on a comment saying so.
    _assert(
        "member_face_path" in mod and "kernel_face_path" in mod,
        "both a member path and a kernel path exist (the choice is representable)",
    )
    resolver = mod.split("def resolve_face_urls", 1)[-1].split("\ndef ")[0]
    _assert(
        "member_face_path" in resolver and "kernel_face_path" in resolver,
        "the resolver considers BOTH paths",
    )
    m_rank = re.search(r"member_face_path\(slug\)[^\n]*=\s*\(slug,\s*(\d+)\)", resolver)
    k_rank = re.search(r"kernel_face_path\(slug\)[^\n]*=\s*\(slug,\s*(\d+)\)", resolver)
    _assert(
        m_rank is not None and k_rank is not None
        and int(m_rank.group(1)) > int(k_rank.group(1)),
        "the MEMBER's face outranks the kernel's (an agent you hired has a face you chose)",
    )
    # A trashed face is not a face — `delete` archives by design, and two index
    # readers already shipped this bug once (2026-09-07).
    _assert(
        "lifecycle" in resolver,
        "the resolver skips trashed rows (delete ARCHIVES; a trashed face must not serve)",
    )

    # ⭐ THE MIRROR IS IDEMPOTENT, and its manifest read must match the path
    # form actually STORED. The first cut read the workspace-RELATIVE path
    # while rows are stored ABSOLUTE, so the version check never fired and
    # every tick rewrote all three faces forever — invisible, because the
    # faces were present and correct the whole time.
    reader = mod.split("def _read_manifest", 1)[-1].split("\ndef ")[0]
    _assert(
        '"/workspace/{KERNEL_MANIFEST_PATH}"' in reader.replace("f'", '"').replace("'", '"')
        or "/workspace/" in reader,
        "the manifest read uses the ABSOLUTE stored path (a relative one matches nothing)",
    )
    _assert(
        "substrate_scope_filter" in reader,
        "the manifest read uses the shared scope filter (the same one skills use)",
    )

    # SOMETHING SERVES IT. A face nobody puts on a payload is a file, not a face.
    lanes = _read(API / "routes" / "lanes.py")
    _assert('"avatar_url"' in lanes, "the agent roster SERVES avatar_url")
    _assert(
        "resolve_face_urls" in lanes,
        "the roster resolves faces through the ONE resolver (never a second lookup)",
    )
    # BATCHED: a per-row lookup is an N+1 on every capability read.
    payload = lanes.split("def _agents_payload", 1)[-1].split("\ndef ")[0]
    _assert(
        "resolve_face_urls" not in payload,
        "[FALSIFIER] the per-row builder does NOT query (faces resolve once, batched)",
    )

    # The scheduler carries it, or no existing workspace ever gets a new face.
    sched = _read(API / "jobs" / "unified_scheduler.py")
    _assert(
        "mirror_kernel_faces_for_all_workspaces" in sched,
        "the scheduler mirrors faces (a face changes in CODE; genesis-seeding would freeze it)",
    )

    # The FE renders a picture when there is one, in ONE place.
    mark = _read(WEB / "components" / "agents" / "AgentIcon.tsx")
    _assert("export function AgentMark" in mark, "ONE component answers how an agent appears")
    # The sweep looks for an AGENT disc specifically — a disc wrapping
    # `<AgentIcon/>`. An ENGINE brand disc in the same file is a different
    # mark and stays neutral by ADR-431; a check that banned every
    # `rounded-full bg-muted` would red-flag correct code (and did).
    for f in ("components/agents/AgentsSurface.tsx", "components/chat-surface/NewChatModal.tsx"):
        src = _read(WEB / f)
        _assert("AgentMark" in src, f"{Path(f).name}: renders agents through AgentMark")
        _assert(
            not re.search(r"rounded-full[^>]*>\s*<AgentIcon", src, re.S),
            f"{Path(f).name}: no hand-rolled agent disc wrapping AgentIcon",
        )



if __name__ == "__main__":
    test_resolvers_exist_and_degrade()
    test_surface_accents_match_declared_surfaces()
    test_root_accents_match_declared_roots()
    test_accent_never_speaks_state_or_alarm()
    test_the_path_string_ladder_stays_deleted()
    test_agent_accent_is_class_wide()
    test_the_face_fallback_carries_the_class_accent()
    test_an_agent_has_a_real_face()

    print(f"\n{'='*60}")
    print(f"ADR-641 icon accent gate: {_passed} passed, {_failed} failed")
    print(f"{'='*60}")
    sys.exit(0 if _failed == 0 else 1)
