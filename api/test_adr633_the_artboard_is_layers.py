"""ADR-633 — the artboard is a stack of layers, gated.

IMAGES takes its own chrome: the rail is DECLARED by the app (D2), an artboard
is called an Artboard (D3), the tree is two levels ordered z-descending (D4),
the layer essentials are `artboard`-grained tokens (D5), and nothing is
dual-run (D6).

This file gates the falsifiers in ADR-633 §5. Both halves are here — the
substrate rows in `services/authoring.py` AND the frontend's declarations —
because the defect this ADR fixes was ENTIRELY frontend (a noun and an organ)
while the capability it exposes is entirely substrate. A gate that watched only
one half would have passed at HEAD, before any of this shipped.

⭐ The lesson this file is built against (ADR-592, 2026-08-26): a derivation
gate is VACUOUS when nothing declares. `_implied_stage` back-derived the field
from the very pair it replaced, so the identity check passed for five days over
zero real declarations. Every assertion below that concerns `objectModel`
therefore asserts the POPULATION — that all three apps declare, and that the
values are distinct where the ADR says they are — never merely the shape.

Run from `api/`:  python3 test_adr633_the_artboard_is_layers.py
"""

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

from services.authoring import (
    STUDIO_KERNEL_CSS,
    STUDIO_MEASURES,
    STUDIO_TOKENS,
    TOKEN_GRAINS,
)
from services.apps.images.stage import IMAGES_ARRANGEMENTS

WEB = REPO / "web" / "components" / "authoring"
SURFACE = (WEB / "StudioSurface.tsx").read_text()
LABELS = (WEB / "structureLabels.ts").read_text()
TREE_PATH = WEB / "LayerTree.tsx"
NAV = (WEB / "PagedNavigator.tsx").read_text()

def _strip_comments(src: str) -> str:
    """Source with `//` and `/* */` comments removed.

    Every "spelled once" assertion below counts CODE, never prose. A gate that
    counts comment text punishes the docstring that explains the rule it is
    enforcing — which is precisely backwards, and is how this file first failed
    against a correct implementation.
    """
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", src)


failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        failures.append(msg)


# ── D5 — the layer essentials are artboard-grained TOKENS ──────────────────
#
# Four properties a LAYER has and a paragraph does not. All four take the
# NARROW grain (F4): a deck block must not acquire opacity by grain widening.
LAYER_TOKENS = ("opacity", "blend", "lock", "hide")

for key in LAYER_TOKENS:
    row = STUDIO_TOKENS.get(key)
    check(row is not None, f"D5: layer token '{key}' is missing from the registry")
    if not row:
        continue
    check(
        tuple(row["grains"]) == ("artboard",),
        f"F4: token '{key}' grains are {row['grains']} — must be ('artboard',) "
        f"so a deck block cannot acquire a layer property by grain widening",
    )
    check(
        tuple(row["scope"]) == ("block",),
        f"D5: token '{key}' scope is {row['scope']} — a layer property is a "
        f"BLOCK-scope row (the layer is the block)",
    )
    check(
        bool(row.get("values")),
        f"D5: token '{key}' declares no values — a token's values must be "
        f"enumerable (ADR-461), which is why these are tokens and not measures",
    )
    check(
        "absence =" in row.get("description", ""),
        f"D5: token '{key}' does not state its absence-default — every sibling "
        f"expresses its default by OMISSION (the ADR-461 B1 lesson)",
    )

# `normal` must NOT be a declared blend value: it is the absence-default, and a
# declared-but-unstyled value writes an attribute that renders nothing (exactly
# the ADR-461 B1 defect, where `align: start` produced two UI states with one
# visual result).
blend = STUDIO_TOKENS.get("blend")
if blend:
    check(
        "normal" not in [v["value"] for v in blend["values"]],
        "D5: `blend` declares a `normal` value — that is the absence-default "
        "and declaring it re-creates the ADR-461 B1 two-states-one-result bug",
    )

# Every declared value needs a kernel rule, or picking it renders nothing.
for key in LAYER_TOKENS:
    row = STUDIO_TOKENS.get(key)
    if not row:
        continue
    for v in row["values"]:
        sel = f'[data-{key}="{v["value"]}"]'
        check(
            sel in STUDIO_KERNEL_CSS,
            f"D5: no kernel rule for {sel} — the token would write an "
            f"attribute that renders nothing",
        )

# `hide` must vacate the coordinate space, or a member hiding a background to
# reach what is under it is still blocked by its box.
check(
    re.search(r'\[data-hide="on"\]\s*\{\s*display:\s*none', STUDIO_KERNEL_CSS) is not None,
    "D5: `hide` does not render `display: none` — `visibility: hidden` leaves "
    "the layer occupying the coordinate space",
)
# A locked layer stays VISIBLE and in flow; it is only unreachable by pointer.
check(
    re.search(r'\[data-lock="on"\]\s*\{\s*pointer-events:\s*none', STUDIO_KERNEL_CSS) is not None,
    "D5: `lock` does not render `pointer-events: none`",
)

# ── F3 — the position measures stay on the artboard grain ──────────────────
#
# Carried forward from ADR-544 §4.3. A sweep that deletes or re-grains these
# breaks IMAGES, and this ADR makes the tree depend on `z` as well.
check("artboard" in TOKEN_GRAINS, "F3: `artboard` is not a declared grain")
for key in ("x", "y", "z"):
    row = STUDIO_MEASURES.get(key)
    check(row is not None, f"F3: measure '{key}' was deleted — IMAGES breaks")
    if row:
        check(
            tuple(row["grains"]) == ("artboard",),
            f"F3: measure '{key}' grains are {row['grains']} — must be "
            f"('artboard',)",
        )

# F7 — the stacking rule the tree reads and `nudgeZ`/`setMeasure` write.
check(
    "[data-z] { z-index: var(--yz, auto); }" in STUDIO_KERNEL_CSS,
    "F7: the kernel lost its `.slide [data-block][data-z]` stacking rule — the "
    "layer tree renders an order the canvas does not honour",
)

# ── F6 — a stage stays a free composition surface ──────────────────────────
for slug, rows in IMAGES_ARRANGEMENTS.items():
    for name, a in rows.items():
        check(
            a.get("areas") == [],
            f"F6: images/{slug}/{name} declares Areas — a stage is a free "
            f"composition surface (ADR-544 §4.3)",
        )
        check(
            "data-x" in a["fragment"],
            f"F6: images/{slug}/{name} lost its seeded free position",
        )

# ── D2 / F1 — the rail is DECLARED, and every app declares it ──────────────
check(
    "objectModel: 'flow' | 'pages' | 'layers';" in SURFACE,
    "D2: `AuthoringApp` does not declare the `objectModel` field",
)
check(
    "objectModel?:" not in SURFACE,
    "F1: `objectModel` is OPTIONAL — a declaration with a default is a "
    "derivation wearing a declaration's clothes (the ADR-592 tautology)",
)

# THE POPULATION ASSERTION. Not the shape — the ADR-592 lesson is that a field
# nothing declares is inert, and an identity check over zero declarations is
# vacuous. Each app row must carry an explicit value.
#
# ADR-636 D1 re-anchor: the rows moved to `web/lib/apps/registry.ts` (the one
# client mirror of `register_app`), so this reads them THERE. The assertion is
# unchanged and still the point — what moved is where an app declares itself,
# not whether it must.
APP_MODELS = {
    "slides": "pages",
    "images": "layers",
    "blogger": "flow",
}
REGISTRY = (REPO / "web" / "lib" / "apps" / "registry.ts").read_text()
for app, expected in APP_MODELS.items():
    m = re.search(rf"^  {app}: \{{(.*?)^  \}},", REGISTRY, re.DOTALL | re.M)
    check(m is not None, f"F1: cannot read the {app} descriptor row")
    if not m:
        continue
    body = m.group(1)
    check(
        re.search(rf"objectModel:\s*'{expected}'", body) is not None,
        f"F1: {app} does not declare objectModel: '{expected}' — every app "
        f"declares explicitly; there is no implied value",
    )
# And the field must stay REQUIRED at its new home (the shape check above
# guards `AuthoringApp`; this guards the descriptor the rows now live on).
check(
    "objectModel?:" not in REGISTRY,
    "F1: `objectModel` is OPTIONAL on AppDescriptor — a declaration with a "
    "default is a derivation wearing a declaration's clothes",
)

# F1's second half: the value must never be back-derived from what it replaces.
check(
    re.search(r"objectModel\s*[:=].*\?\?", SURFACE) is None,
    "F1: `objectModel` has a `??` fallback — a declaration with a fallback is "
    "the ADR-592 tautology (the field back-derived from the pair it replaces)",
)
check(
    re.search(r"objectModel\s*=\s*.*layout\s*===", SURFACE) is None
    and re.search(r"objectModel\s*=\s*.*slug\s*===", SURFACE) is None,
    "F1: `objectModel` is derived from `layout`/`slug` — it must be declared",
)

# ── F5 — one rail per app, and the tree is the one images gets ─────────────
check(TREE_PATH.exists(), "D4: LayerTree.tsx does not exist")
TREE = TREE_PATH.read_text() if TREE_PATH.exists() else ""

check(
    "app.objectModel === 'layers' ? (" in SURFACE,
    "F5: the rail is not switched on the DECLARATION — the mount must read "
    "`app.objectModel`, never `layout === 'deck'`",
)
# The two rails are mutually exclusive: a rail plus a tree is two answers to
# "where am I" (the ADR-595 lesson — the desk is one surface).
mount = re.search(
    r"app\.objectModel === 'layers' \? \((.*?)\) : \((.*?)\)\}", SURFACE, re.DOTALL
)
check(mount is not None, "F5: cannot read the rail mount")
if mount:
    layers_arm, pages_arm = mount.group(1), mount.group(2)
    check(
        "<LayerTree" in layers_arm and "<PagedNavigator" not in layers_arm,
        "F5: the `layers` arm does not mount LayerTree alone",
    )
    check(
        "<PagedNavigator" in pages_arm and "<LayerTree" not in pages_arm,
        "F5: the `pages` arm does not mount PagedNavigator alone",
    )

# D6 — PagedNavigator keeps its SINGLE job. A layers mode inside it would be
# the dual approach wearing one filename.
check(
    "objectModel" not in NAV and "LayerTree" not in NAV,
    "D6: PagedNavigator learned about layers — it keeps one job; a second mode "
    "inside it is the dual approach wearing one filename",
)

# ── D3 / F2 — an artboard is an Artboard ───────────────────────────────────
check(
    "Artboard" in LABELS,
    "F2: `structureLabels.ts` has no 'Artboard' noun — an IMAGES artboard is "
    "still labelled 'Slide' in the crumb, the Esc-walk and the edit runtime",
)
# The noun must be CHOSEN by the app's model, not by the frame class. A bare
# `.slide → 'Slide'` with no model in scope is the defect ADR-633 §1.1 names.
check(
    re.search(r"objectModel|ObjectModel", LABELS) is not None,
    "F2: the label ladder does not read the app's object model — the noun is "
    "still derived from the frame class, which is how one object came to wear "
    "two wrong names",
)
# D6 — ONE source for the noun. An 'Artboard' alias sitting beside 'Slide' in a
# lookup is exactly the drift this ADR refuses.
#
# Counted over CODE ONLY: a comment explaining the rule is not a second
# implementation of it, and a gate that counts prose punishes the docstring
# that makes the rule legible. (The first draft of this check did exactly
# that, and failed against a correct implementation.)
LABELS_CODE = _strip_comments(LABELS)
check(
    LABELS_CODE.count("'Artboard'") + LABELS_CODE.count('"Artboard"') == 1,
    f"D6: 'Artboard' is spelled {LABELS_CODE.count(chr(39) + 'Artboard' + chr(39))} times in "
    f"the label ladder's CODE — one source for the noun, never an alias table",
)

# ── D4 — the tree's shape: two levels, z-descending ────────────────────────
if TREE:
    check(
        "STRUCTURAL_PAGE_SEL" in TREE,
        "D4: LayerTree does not use STRUCTURAL_PAGE_SEL — it must resolve "
        "artboards through the ONE page selector so indices agree with the "
        "canvas and the ops (ADR-633 D1: the kernel stays shared)",
    )
    check(
        "(b.z ?? -1) - (a.z ?? -1)" in TREE,
        "D4: the layer sort is not z-DESCENDING with an absence-default — top "
        "of stack must come first, and an unstamped layer sorts beneath every "
        "stamped one (the ADR-461 fallback rule)",
    )
    # The tree is CHROME (D1): it may not own a write path. Restacking and the
    # presence-tokens go out as callbacks to the surface's shared ops.
    for banned in ("write_revision", "setMeasure(", "setToken(", "fetch("):
        check(
            banned not in TREE,
            f"D1: LayerTree calls `{banned}` — the tree is chrome; every write "
            f"composes the surface's shared ops through a callback",
        )

    # ── D4, BEHAVIOURALLY ──────────────────────────────────────────────────
    # ⭐ Every check above is a COMPOSITION check: it proves the rail is built
    # from the right parts. They all passed at HEAD over an implementation that
    # put dragged layers in the WRONG SLOT on every real artboard — because a
    # drag was never executed, only grepped for. So the rules that decide
    # whether reordering actually works are asserted by RUNNING them.
    #
    # The stack below is the one production artboard's real z distribution
    # (`operation/untitled-image/image.html`): ten layers, five distinct z
    # values, seven of them tied with another. An agent authors z by INTENT
    # (background 1, scrim 2, type 5), so ties and gaps are the normal case,
    # and drag math assuming a dense unique permutation is wrong against every
    # file a member actually has.
    PROD_STACK = [
        ("bg-mascot", 1), ("scrim-grad", 2), ("top-stripe", 3), ("kicker-top", 4),
        ("headline-main", 5), ("body-copy", 5), ("url-pill", 5),
        ("kicker-right", 4), ("yarn-thread", 4), ("sub-right", 5),
    ]

    def displayed(stack):
        # `readLayerTree`'s order: z-descending, STABLE, absence sorts last.
        return sorted(
            range(len(stack)),
            key=lambda i: (-(stack[i][1] if stack[i][1] is not None else -1), i),
        )

    def dropped_order(stack, name, gap):
        # `commitDrop`, ported: the rail hands the parent an ORDER, never a depth.
        ids = [stack[i][0] for i in displayed(stack)]
        frm = ids.index(name)
        if gap in (frm, frm + 1):
            return ids  # the component returns early — a no-op drag
        moved = ids.pop(frm)
        ids.insert(gap - 1 if gap > frm else gap, moved)
        return ids

    def shown_after(stack, ids):
        # `handleRestack` writes a DENSE z, top of stack first; the rail then
        # re-derives from those bytes. This round-trip is what the first cut
        # failed: it is the only check that can see a wrong landing.
        top = len(ids) - 1
        written = {bid: max(0, top - i) for i, bid in enumerate(ids)}
        after = [(n, written.get(n, z)) for n, z in stack]
        return [after[i][0] for i in displayed(after)]

    for _name, _gap in (
        ("yarn-thread", 1), ("sub-right", 0), ("scrim-grad", 4),
        ("headline-main", 10), ("bg-mascot", 0), ("url-pill", 7),
    ):
        _want = dropped_order(PROD_STACK, _name, _gap)
        _got = shown_after(PROD_STACK, _want)
        check(
            _got == _want,
            f"D4: dragging `{_name}` to slot {_gap} on the PRODUCTION stack lands a "
            f"different order than the member dropped.\n      dropped: {_want}\n"
            f"      shows:   {_got}",
        )

    # A dense renumber from the top can never exceed the registry ceiling. The
    # per-layer arithmetic it replaced walked z upward on every drag until the
    # writes clamped and the rail silently stopped moving anything at all.
    _ceiling = STUDIO_MEASURES["z"]["max"]
    check(
        len(PROD_STACK) - 1 <= _ceiling,
        f"D4: a dense renumber of {len(PROD_STACK)} layers needs z up to "
        f"{len(PROD_STACK) - 1}, past the registry ceiling of {_ceiling}",
    )

    # The rail hands over an ORDER, never a depth. A `toZ`-shaped callback is
    # the defect's signature: one layer's new depth cannot express a move on a
    # stack that has ties.
    check(
        "orderedIds" in TREE and "toZ" not in TREE,
        "D4: LayerTree still computes a per-layer `toZ` — a drop index cannot be "
        "turned into one layer's z on a stack with ties or gaps; the rail hands "
        "over the artboard's ORDER and the surface writes it densely",
    )
    check(
        "setGeometryMany(" in SURFACE and "restack layers" in SURFACE,
        "D4: `handleRestack` does not write the order through `setGeometryMany` — "
        "a whole-artboard renumber is ONE revision through the shared op",
    )

    # ── ONE measure reader ─────────────────────────────────────────────────
    # `setMeasure` writes `data-<key>=""` as a bare PRESENCE MARKER and puts the
    # number in the CSS var. A consumer parsing the ATTRIBUTE therefore reads a
    # shape our own writer never produces: it works on AI-authored markup and
    # returns null the instant any op touches the block. That split stranded
    # every restacked layer at the bottom of the rail.
    OPS = (WEB / "artifactOps.ts").read_text()
    check(
        "export function readMeasure" in OPS,
        "F3: no `readMeasure` in artifactOps — `setMeasure`'s inverse must exist "
        "as ONE reader, or every consumer re-derives the marker/var split",
    )
    check(
        "getAttribute('data-z')" not in TREE,
        "F3: LayerTree parses `data-z` directly — that attribute is a PRESENCE "
        "MARKER (`setMeasure` writes it empty); read z through `readMeasure`",
    )
    # Narrowly: no second PARSE of the var. `GEOMETRY_VARS` names the same
    # strings for `returnToFlow`, which CLEARS them — a different act, and not
    # a reader, so it is not the drift this guards.
    check(
        "match(/--yz" not in _strip_comments(OPS),
        "F3: a raw `--yz` regex parse survives in artifactOps' CODE — "
        "`readMeasure` is the one reader (it composes the served `cssVar`) and "
        "`nudgeZ` calls it",
    )

    # ── The rail's click always lands (F2) ────────────────────────────────
    # `selection` starts null and resets to null on every file switch, so a
    # `sel ? … : sel` update swallowed the FIRST click on a freshly-opened file
    # while the scroll and pane-switch still fired — which read as a decorative
    # rail. The null branch must anchor the artboard.
    check(
        "sel ? { ...sel, blockId } : sel" not in SURFACE,
        "F2: `selectLayerFromTree` still no-ops when nothing is selected — "
        "`selection` starts null, so the first click on a layer is swallowed",
    )

# ── D5 — Turn into is withdrawn on an artboard ─────────────────────────────
TAB = (WEB / "StudioDesignTab.tsx").read_text()
check(
    "!isArtboardSel &&" in TAB,
    "D5: `Turn into` is not withdrawn on an artboard — the pane still offers "
    "to convert a composed layer into a bulleted list",
)
# One derivation, two readers — the predicate must not be spelled twice.
# Counted over CODE ONLY, for the same reason as the noun above.
TAB_CODE = _strip_comments(TAB)
check(
    TAB_CODE.count("layout === 'image'") == 1,
    f"D6: `layout === 'image'` appears {TAB_CODE.count(chr(39).join(['layout === ', 'image', '']))} "
    f"times in StudioDesignTab's CODE — the artboard predicate is derived ONCE "
    f"and read by both the token gate and Turn into",
)

# ── Report ─────────────────────────────────────────────────────────────────
total = 60
if failures:
    print(f"ADR-633 — {len(failures)} FAILURE(S):\n")
    for f in failures:
        print(f"  ✗ {f}")
    sys.exit(1)

print(f"ADR-633 — the artboard is a stack of layers: all checks pass")
print("  D1 kernel shared · D2 rail declared · D3 the artboard noun")
print("  D4 two levels, z-descending · D5 layer essentials · D6 nothing dual-run")
