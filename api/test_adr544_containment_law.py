"""ADR-544 — the containment law, gated.

Every block lives in exactly one Area (D1); an Area is one substrate concept
carrying its role (D2); free position is IMAGES-only (D3); the operator-facing
vocabulary is Slide/Layout/Area/Block (D4).

These gate the SUBSTRATE half of the arc. §1's defects were all invisible to
green gates — they were found by driving the doorway — so a browser click-pass
gates the surface half, not this file (ADR-544 §7).

Run from `api/`:  python3 test_adr544_containment_law.py
"""

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

from services.authoring import (
    STUDIO_MEASURES,
    STUDIO_ARRANGEMENTS,
    STUDIO_LAYOUTS,
    TOKEN_GRAINS,
)
from services.apps.images.stage import IMAGES_ARRANGEMENTS

AREA_ROLES = {"heading", "body", "media", "aside"}

failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        failures.append(msg)


class _Tree(HTMLParser):
    """Parse a fragment into (tag, attrs, ancestors) tuples — enough to answer
    'does this block have an Area ancestor inside its page?'."""

    def __init__(self) -> None:
        super().__init__()
        self.stack: list[tuple[str, dict]] = []
        self.nodes: list[tuple[str, dict, list[tuple[str, dict]]]] = []

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        self.nodes.append((tag, a, list(self.stack)))
        if tag not in ("br", "img", "hr", "input", "meta"):
            self.stack.append((tag, a))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break


def parse(fragment: str) -> list[tuple[str, dict, list[tuple[str, dict]]]]:
    p = _Tree()
    p.feed(fragment)
    return p.nodes


# ── D1 — every block lives in exactly one Area ────────────────────────────
# The pre-544 registry disagreed with itself: `title` put its heading in a slot
# while `content`/`two-column` left a bare <h2> as a slide child. This is the
# invariant that made the hierarchy unstateable (§1.1), so it is gated, not
# reviewed.
for layout, rows in STUDIO_ARRANGEMENTS.items():
    for slug, a in rows.items():
        where = f"{layout}/{slug}"
        for tag, attrs, ancestors in parse(a["fragment"]):
            if "data-block" not in attrs:
                continue
            # A nested annotated element rides its parent block (ADR-446 D3).
            if any("data-block" in anc[1] for anc in ancestors):
                continue
            has_area = any("data-area" in anc[1] for anc in ancestors)
            check(
                has_area,
                f"D1: {where} — block '{attrs.get('data-block')}' has no Area "
                f"ancestor (a bare block under a slide/band is the §1.1 defect)",
            )

# ── D2 — an Area declares its role, from the closed set ───────────────────
for layout, rows in STUDIO_ARRANGEMENTS.items():
    for slug, a in rows.items():
        where = f"{layout}/{slug}"
        check("areas" in a, f"D2: {where} — no `areas` key (the `slots` rename)")
        declared = {s["name"] for s in a.get("areas", [])}
        for s in a.get("areas", []):
            check(
                s.get("role") in AREA_ROLES,
                f"D2: {where} — area '{s.get('name')}' role "
                f"{s.get('role')!r} is not in {sorted(AREA_ROLES)}",
            )
        # Every markup Area is declared, and carries its role inline.
        for tag, attrs, _ in parse(a["fragment"]):
            if "data-area" not in attrs:
                continue
            name = attrs["data-area"]
            check(
                name in declared,
                f"D2: {where} — markup Area '{name}' is not in the `areas` list",
            )
            check(
                attrs.get("data-area-role") in AREA_ROLES,
                f"D2: {where} — Area '{name}' markup lacks a valid "
                f"data-area-role (got {attrs.get('data-area-role')!r})",
            )
        # Same-role siblings are told apart by `place` (D2's disambiguator).
        by_role: dict[str, list[dict]] = {}
        for s in a.get("areas", []):
            by_role.setdefault(s.get("role", ""), []).append(s)
        for role, group in by_role.items():
            if len(group) > 1:
                check(
                    all(s.get("place") for s in group),
                    f"D2: {where} — {len(group)} '{role}' Areas without a "
                    f"`place` to tell them apart",
                )

# ── D2 — `.cols` is a LAYOUT, never a rung: a `.col` holding blocks is an Area
for layout, rows in STUDIO_ARRANGEMENTS.items():
    for slug, a in rows.items():
        where = f"{layout}/{slug}"
        for tag, attrs, ancestors in parse(a["fragment"]):
            classes = attrs.get("class", "").split()
            if "col" not in classes:
                continue
            check(
                "data-area" in attrs,
                f"D2: {where} — a `.col` without Area markers (a col that "
                f"holds blocks IS the Area; there is no slot-inside-col rung)",
            )

# ── D1 — the layout SCAFFOLDS obey the law too ────────────────────────────
# A scaffold is what a new artifact is born as; if it ships bare blocks, every
# new deck starts in violation.
for slug, layout in STUDIO_LAYOUTS.items():
    scaffold = layout.get("scaffold", "")
    if not scaffold:
        continue
    for tag, attrs, ancestors in parse(scaffold):
        if "data-block" not in attrs:
            continue
        if any("data-block" in anc[1] for anc in ancestors):
            continue
        check(
            any("data-area" in anc[1] for anc in ancestors),
            f"D1: {slug} scaffold — block '{attrs.get('data-block')}' has no "
            f"Area ancestor",
        )

# ── D3 — free position is IMAGES-only ─────────────────────────────────────
check("artboard" in TOKEN_GRAINS, "D3: `artboard` is not a declared grain")
for key in ("x", "y", "z"):
    row = STUDIO_MEASURES.get(key)
    check(row is not None, f"D3: measure '{key}' is missing entirely")
    if row:
        check(
            tuple(row["grains"]) == ("artboard",),
            f"D3: measure '{key}' grains are {row['grains']} — must be "
            f"('artboard',) so a deck block cannot leave its Area",
        )

# §4.3 — the measures are RE-GRAINED, never deleted: IMAGES depends on them.
for key in ("x", "y", "z"):
    check(key in STUDIO_MEASURES, f"§4.3: measure '{key}' was deleted — IMAGES breaks")
check(
    IMAGES_ARRANGEMENTS is not None,
    "§4.3: IMAGES arrangements unreadable",
)
for slug, rows in IMAGES_ARRANGEMENTS.items():
    for name, a in rows.items():
        check(
            "areas" in a,
            f"§4.3: images/{slug}/{name} — no `areas` key (one vocabulary)",
        )
        check(
            a.get("areas") == [],
            f"§4.3: images/{slug}/{name} declares Areas — a stage is a free "
            f"composition surface and must declare none",
        )
        check(
            "data-x" in a["fragment"],
            f"§4.3: images/{slug}/{name} lost its seeded free position",
        )

# ── D4 — no retired vocabulary in the arrangement substrate ───────────────
# `data-slot` was the free-form authored string that leaked to the operator as
# MAIN / SIDE (§1.2). It has no home left in the registry.
for layout, rows in STUDIO_ARRANGEMENTS.items():
    for slug, a in rows.items():
        check(
            "data-slot" not in a["fragment"],
            f"D4: {layout}/{slug} — fragment still carries `data-slot`",
        )
        check(
            "slots" not in a,
            f"D4: {layout}/{slug} — row still carries a `slots` key",
        )
for slug, layout in STUDIO_LAYOUTS.items():
    check(
        "data-slot" not in layout.get("scaffold", ""),
        f"D4: {slug} scaffold still carries `data-slot`",
    )

# The LLM-facing grammar teaches containment, or the lane keeps authoring bare
# headings — the failure D1 exists to end.
import services.authoring as _authoring  # noqa: E402

guidance = _authoring.__dict__.get("STUDIO_SUBSTRATE_GUIDE", "") or ""
if not guidance:
    src = open(_authoring.__file__, encoding="utf-8").read()
    guidance = src
check(
    "CONTAINMENT LAW" in guidance,
    "D1: the lane's guidance does not state the containment law",
)
check(
    "data-area-role" in guidance,
    "D2: the lane's guidance does not teach data-area-role",
)

# ── D7 — the heal, EXECUTED on a synthetic pre-544 deck ───────────────────
# A migration that rewrites live decks is the riskiest half of this ADR (§4.2),
# so it is not asserted by reading its source: it RUNS here, over the exact
# shape §1.1 describes (a bare heading, slot-named regions, a drifted block).
try:
    import services.apps.images  # noqa: F401 — registers the IMAGES layout
    from scripts.oneshot.adr544_heal_containment import heal_html

    PRE = (
        '<!doctype html>\n<html data-template="deck"><body>\n'
        '<section class="slide" data-arrange="two-column">\n'
        '  <h2 data-block="heading" data-block-id="t1" data-x="34" data-y="12"'
        ' style="--yx:34%;--yy:12%;color:red">Drifted</h2>\n'
        '  <div class="cols">\n'
        '    <div class="col" data-slot="main"><div data-block="prose"'
        ' data-block-id="b1"><p>Left</p></div></div>\n'
        '    <div class="col" data-slot="side"><div data-block="prose"'
        ' data-block-id="b2"><p>Right</p></div></div>\n'
        '  </div>\n</section>\n</body></html>'
    )
    healed, renamed, rehomed, cleared = heal_html(PRE)
    check(renamed == 2, f"D7: both regions named as Areas (got {renamed})")
    check(rehomed == 1, f"D7: the bare heading was re-homed (got {rehomed})")
    check(cleared == 1, f"D7: the drifted position was cleared (got {cleared})")
    check("data-slot" not in healed, "D7: no `data-slot` survives the heal")
    check(
        'data-area-role="heading"' in healed,
        "D7: the re-homed heading landed in a heading-role Area",
    )
    check("data-x=" not in healed, "D7: deck free position is gone")
    check(
        "color:red" in healed,
        "D7: a non-position style declaration survived (never stomp the "
        "artifact's own style)",
    )
    for bid in ("t1", "b1", "b2"):
        check(
            f'data-block-id="{bid}"' in healed,
            f"D7: block '{bid}' kept its id (a heal never re-mints identity)",
        )
    # §4.3 — the scope discipline, EXECUTED. An IMAGES stage and a flow document
    # must come back byte-identical: the heal is Studio-paged only.
    STAGE = (
        '<!doctype html>\n<html data-template="image"><body>\n'
        '<section class="slide" data-arrange="free">\n'
        '  <h2 data-block="heading" data-block-id="t1" data-x="8" data-y="12"'
        ' style="--yx:8%;--yy:12%">Stage</h2>\n</section>\n</body></html>'
    )
    check(
        heal_html(STAGE) == (STAGE, 0, 0, 0),
        "§4.3: the heal does NOT touch an IMAGES stage (free position is its "
        "whole point)",
    )
    DOC = (
        '<!doctype html><html data-template="document"><body><main>'
        '<h1 data-block="heading" data-block-id="t1">Doc</h1></main></body></html>'
    )
    check(
        heal_html(DOC) == (DOC, 0, 0, 0),
        "D7: the heal does NOT touch a flow document (no page grain to contain "
        "into)",
    )
except ImportError as exc:  # pragma: no cover
    check(False, f"D7: the heal script is not importable ({exc})")

# ── D7/D4 — the label ladder and its injected TWIN stay in step ───────────
# `labelForJS` inlines this ladder for the sandboxed runtime and cannot import
# it, so the two are kept in sync by a comment ("change both together"). A
# comment enforces nothing — that is the exact class of defect this arc keeps
# finding — so the parity is gated: every rung the module ladder answers, the
# injected twin must answer too.
_labels_src = (REPO / "web/components/authoring/structureLabels.ts").read_text()
for rung in ("data-area-role", "data-area-place", "data-slot", "data-block"):
    check(
        _labels_src.count(rung) >= 2,
        f"D4: rung '{rung}' is missing from one of the two label ladders "
        f"(labelForElement / labelForJS — change both together)",
    )
# The LEGACY rung specifically: an un-healed document's region must read as an
# Area, never fall through to "Group" (the `Slide 2 > Group > Group` crumb the
# operator's click-pass caught) and never leak its authored name.
check(
    "if (el.getAttribute('data-slot') !== null) return areaLabel(null);" in _labels_src,
    "D7: labelForElement has no legacy data-slot rung — a pre-heal deck's "
    "regions fall through to 'Group'",
)
check(
    "if (el.getAttribute('data-slot') !== null) return 'Area';" in _labels_src,
    "D7: labelForJS has no legacy data-slot rung — the canvas chrome and the "
    "pane would disagree on an un-healed deck",
)

# ── D2 — the kernel CSS speaks Areas, and the VERSION carries it out ──────
# The kernel stylesheet is baked into every artifact at creation and retrofits
# only when `STUDIO_KERNEL_CSS_VERSION` advances (`ensure_kernel_style_in_html`
# returns byte-identical at a same-or-newer version). ADR-544 D2 rewrote two
# region selectors in that sheet; the bump is what makes the rewrite REACH the
# decks that already exist. Without it the edit is real in the registry, real in
# every gate that greps the source, and dead in every live artifact — a change
# that ships green and never mounts.
from services.authoring import STUDIO_KERNEL_CSS, STUDIO_KERNEL_CSS_VERSION

check(
    '[data-area-role="media"]' in STUDIO_KERNEL_CSS,
    "D2: the kernel's full-bleed media rule does not address the Area ROLE",
)
check(
    ".slide [data-area]" in STUDIO_KERNEL_CSS,
    "D2: the kernel's relative-position rule does not address [data-area]",
)
check(
    '[data-slot="media"]' not in STUDIO_KERNEL_CSS,
    "D2: a retired `data-slot` selector survives in the kernel CSS",
)
check(
    STUDIO_KERNEL_CSS_VERSION >= 17,
    f"D2: STUDIO_KERNEL_CSS_VERSION is {STUDIO_KERNEL_CSS_VERSION} — the "
    f"ADR-544 selector rewrite needs >= 17 to retrofit into existing artifacts",
)

# ── D5.1 — the set is sibling-only, REFUSED AT FORMATION ──────────────────
# The operator ratified the constraint over the exception ("the cross container
# drag illegal IS correct"). What matters is WHERE it is enforced: withdrawing
# the verbs afterwards leaves the illegal set existing and the pane describing
# something it has nothing true to say about. The runtime refuses the ⇧-click
# itself, and SAYS so — a gesture that silently does nothing is the inert
# affordance this ADR keeps finding.
_proj = (REPO / "web/components/workspace/viewers/projection.ts").read_text()
check(
    "gArea !== curArea" in _proj and "cross-area-set" in _proj,
    "D5.1: the ⇧-click set is not gated on a SHARED Area — a cross-Area set can "
    "still form",
)
check(
    "yarnnn-refused" in _proj,
    "D5.1: the runtime refuses silently — it must post a reason the surface can "
    "voice",
)
_surface = (REPO / "web/components/authoring/StudioSurface.tsx").read_text()
check(
    "onRefused" in _surface and "cross-area-set" in _surface,
    "D5.1: the surface does not voice the refusal (the runtime must never carry "
    "operator-facing words)",
)

# ADR-541 D4 — the ONE withdrawal notice must MOUNT. It was exported from
# selection.ts with zero importers, so the pane named a count and never said why
# the single-subject rows had gone: computed and never mounted, the ADR-536
# defect class. Asserted by COUNT — both multi scopes (range + objects) show it.
_tab = (REPO / "web/components/authoring/StudioDesignTab.tsx").read_text()
check(
    "withdrawalNotice" in _tab,
    "ADR-541 D4: withdrawalNotice has no consumer — the one notice is computed "
    "and never mounted",
)
check(
    _tab.count("withdrawalNotice(unified)") >= 2,
    "ADR-541 D4: the withdrawal notice mounts at fewer than both multi scopes "
    "(range + objects)",
)

if failures:
    print(f"ADR-544 FAILED — {len(failures)} finding(s):\n")
    for f in failures:
        print(f"  ✗ {f}")
    sys.exit(1)

print("ADR-544 containment law: all checks green")
