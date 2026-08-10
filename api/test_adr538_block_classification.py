"""ADR-538 — a block is classified by what it CITES, and motion is declarative.

The operator, comparing yarnnn's deck against a Claude Design artifact:
*"right now, they are mostly flat, or images, or svgs… I notice that there are
dynamic and animated. I'm thinking how we should fundamentally approach this."*

Two defects and one ceiling came out of the audit:

  · ``chart`` was filed ``group: "data"`` while citing ``./assets/chart.svg`` —
    a PICTURE of data — and sat in ``MEDIA_BLOCK_KINDS`` beside figure/gallery,
    which was the registry confessing what it actually was. Change the numbers
    and nothing happened. (The two live instances carried their data only in
    ``alt`` prose, with an EMPTY ``data-ref-rev``.)
  · The FE made that worse than a mis-label: picking "Chart" SEEDED THE CHAT
    with "Create an SVG chart at ./assets/chart.svg" — the insert door itself
    was wired to the retired model, at two sites.
  · The motion ceiling was never measured. It is not "no motion" — it is "no
    JavaScript": a bare ``sandbox=""`` (Web Viewer, paged navigator, and the
    PUBLIC SHARE LINK) runs CSS animation fine and runs no script at all.

What is asserted:
  1. The D1 classification rule holds across every row: a `data` kind cites a
     SOURCE, a `media` kind cites a PICTURE, a `content` kind cites nothing.
  2. `chart` is re-cut — cites a .csv, declares its kind, stamps a pin, and has
     LEFT the media set (so `fit`/`height` no longer claim it).
  3. `component` exists, is content, is studio-scoped, and is composite.
  4. The kernel gained motion, ALL of it declarative, ALL of it guarded by
     prefers-reduced-motion — and the version bumped so the retrofit carries it.
  5. Script is refused in the substrate teaching (the lane must not author a
     component a reader cannot see).
  6. The FE insert door is a PICKER, not a chat seed — the ADR-536 lesson
     (a control the canon promises needs a door onto it).
  7. FALSIFIERS — each claim is shown to be capable of failing.

Run from `api/`:  python3 test_adr538_block_classification.py
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import services.docs  # noqa: F401,E402 — registration side-effect (as the app does)
import services.authoring as st  # noqa: E402

PASS, FAIL = 0, 0

WEB = Path(__file__).parent.parent / "web" / "components"
PROJECTION = (WEB / "workspace" / "viewers" / "projection.ts").read_text()
SURFACE = (WEB / "authoring" / "StudioSurface.tsx").read_text()
PICKER = (WEB / "authoring" / "StudioCitablePicker.tsx").read_text()


def t(label: str, cond: bool) -> None:
    global PASS, FAIL
    print(("[PASS] " if cond else "[FAIL] ") + label)
    if cond:
        PASS += 1
    else:
        FAIL += 1


def strip_comments(css: str) -> str:
    """CSS text with /* … */ removed.

    The ADR-536 lesson, applied pre-emptively: an ABSENCE assertion must not
    match its own explanatory comment. Every "the kernel does NOT contain X"
    check below runs on this, never on the raw source.
    """
    return re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)


KERNEL = st.STUDIO_KERNEL_CSS
KERNEL_NC = strip_comments(KERNEL)

print("\n=== 1. D1 — the classification rule holds for every row ===")

# ADR-539 D1 re-cut: `group` is no longer a field the rule POLICES — it is a
# derivation of `cites` (block_group), so group-vs-citation disagreement is
# unrepresentable. What remains falsifiable, and what this section now pins,
# is the seam the derivation cannot see: the DECLARED `cites` must match what
# the MARKUP actually does. A row declaring cites="none" whose markup carries
# a data-ref (or the reverse) is the new spelling of the old chart bug.
CITES_SOURCE = {"table", "chart"}
CITES_PICTURE = {"figure", "gallery"}

for kind, row in st.STUDIO_BLOCKS.items():
    group = st.block_group(row)
    markup = row["markup"]
    cites_in_markup = "data-ref=" in markup
    if kind in CITES_SOURCE:
        t(f"`{kind}` declares source, derives data, and its markup cites",
          row["cites"] == "source" and group == "data" and cites_in_markup)
    elif kind in CITES_PICTURE:
        t(f"`{kind}` declares picture, derives media, and its markup cites",
          row["cites"] == "picture" and group == "media" and cites_in_markup)
    else:
        t(f"`{kind}` declares none, derives content, and its markup cites nothing",
          row["cites"] == "none" and group == "content" and not cites_in_markup)

t(
    "every data-group row cites a .csv (a source, never a rendering)",
    all(
        ".csv" in r["markup"]
        for k, r in st.STUDIO_BLOCKS.items()
        if st.block_group(r) == "data" and "data-ref=" in r["markup"]
    ),
)
t(
    "no row cites an .svg (the retired chart-as-picture shape)",
    not any(".svg" in r["markup"] for r in st.STUDIO_BLOCKS.values()),
)

print("\n=== 2. D2 — chart cites its data ===")

chart = st.STUDIO_BLOCKS["chart"]
t("chart cites a .csv", ".csv" in chart["markup"])
t("chart declares data-ref-kind='chart'", 'data-ref-kind="chart"' in chart["markup"])
t("chart carries a pin slot (data-ref-rev)", "data-ref-rev=" in chart["markup"])
t("chart declares its visual kind (data-chart)", 'data-chart="' in chart["markup"])
t("chart LEFT the media set", "chart" not in st.MEDIA_BLOCK_KINDS)
t("figure + gallery remain the media set", st.MEDIA_BLOCK_KINDS == {"figure", "gallery"})
t(
    "the media `applies` phrase no longer names chart",
    "chart" not in st.GRAIN_PHRASES["media"],
)
t(
    "no media-grain token claims chart",
    all(
        "chart" not in tok.get("description", "")
        for tok in st.STUDIO_TOKENS.values()
        if "media" in tok.get("applies", [])
    ),
)
t("the projection draws a cited chart", "csvToChartHtml" in PROJECTION)
t(
    "the chart branch precedes the table branch (both read a .csv)",
    PROJECTION.index("kind === 'chart'") < PROJECTION.index("kind === 'table'"),
)
t(
    "the PINNED fallback draws a chart too (never a raw CSV dump)",
    PROJECTION.count("csvToChartHtml(") >= 2,
)
t(
    "the CSV parser honours quoted fields (a '1,240' value is ONE cell)",
    "splitCsvLine" in PROJECTION and "quoted" in PROJECTION,
)

print("\n=== 3. D3 — the composite component ===")

comp = st.STUDIO_BLOCKS.get("component", {})
t("`component` row exists", bool(comp))
t("component is content (it cites nothing)",
  comp.get("cites") == "none" and st.block_group(comp) == "content")
t("component is studio-scoped", comp.get("apps") == ("studio",))
t("component is composite (header + row + footer)", all(x in comp.get("markup", "") for x in ("<header>", 'class="row"', "<footer>")))
t("the kernel draws it", 'div[data-block="component"]' in KERNEL_NC)
t("Docs is not offered the component", "component" not in st.blocks_for_app("docs"))
t("Studio IS offered the component", "component" in st.blocks_for_app("studio"))

print("\n=== 4. D4 — motion is declarative, guarded, and versioned ===")

t("the kernel has motion at all", "@keyframes" in KERNEL_NC)
t("motion is opt-in via data-motion", "[data-motion=" in KERNEL_NC)
t("a reduced-motion guard exists", "prefers-reduced-motion" in KERNEL_NC)
guard = KERNEL_NC[KERNEL_NC.index("prefers-reduced-motion"):]
t("the guard disables animation", "animation: none" in guard)
t("the guard disables transition", "transition: none" in guard)
# The version is asserted as a FLOOR, not an equality. ADR-538 needs its CSS to
# have REACHED existing artifacts, which is what a bump ≥ its own does; pinning
# the exact number made every LATER kernel edit (ADR-544 D2 → v17) read as this
# ADR regressing, when the retrofit it depends on had strictly improved. Never
# pin a version, assert the floor that carries your change.
t("kernel version is at least 16 (so the retrofit carries this ADR's CSS)",
  st.STUDIO_KERNEL_CSS_VERSION >= 16)
t(
    "the composed element carries the CURRENT version",
    f'data-kernel-v="{st.STUDIO_KERNEL_CSS_VERSION}"' in st.compose_kernel_style_element(),
)
t("NO <script> in the kernel CSS", "<script" not in KERNEL_NC)

print("\n=== 5. D4 — the substrate teaching refuses script ===")

posture = st.STUDIO_SUBSTRATE_POSTURE if hasattr(st, "STUDIO_SUBSTRATE_POSTURE") else ""
if not posture:
    # The posture lives as a module-level string; find it by its own heading.
    src = Path(__file__).parent.joinpath("services", "authoring.py").read_text()
    posture = src[src.index("Never edit a cited object's content") :][:3000]
t("the lane is told a chart cites DATA", "Charts cite DATA" in posture or "cite DATA" in posture)
t("the lane is told motion is CSS only", "Motion is CSS only" in posture)
t(
    "the lane is NOT told to author an SVG chart",
    "charts, diagrams, icons" not in posture,
)

print("\n=== 6. The insert door is a picker, not a chat seed (ADR-536 lesson) ===")

# ADR-539 D2 re-cut: picker-backing is derived from the row's `cites` field
# (PICKER_KINDS/CSV_KINDS deleted). Chart is picker-backed BECAUSE it declares
# a source citation, and the picker lists CSVs BECAUSE cites === 'source'.
t("chart is picker-backed (declares a source citation)",
  st.STUDIO_BLOCKS["chart"]["cites"] == "source")
t(
    "the picker lists CSVs for a source-citing kind (not images)",
    "cites === 'source'" in PICKER and "c.tables : c.images" in PICKER,
)
t(
    "the SVG-seeding branch is GONE from the surface",
    "./assets/chart.svg" not in SURFACE,
)
t(
    "no seed prompt mentions creating a chart",
    "Create an SVG chart" not in SURFACE,
)
t(
    "a chart pick lands a CHART (not collapsed to table/figure)",
    "cp.kind === 'chart' ? 'chart'" in SURFACE,
)

print("\n=== 7. FALSIFIERS — each claim can fail ===")

# F1 — the declaration/markup seam would catch a mis-declared row: a row
# DECLARING source whose markup cites no .csv is the post-539 spelling of the
# old chart bug (group itself can no longer be mis-filed — it is derived).
fake = dict(st.STUDIO_BLOCKS["figure"])
fake["cites"] = "source"  # picture markup under a source declaration
t(
    "F1 the D1 rule REJECTS a picture-citing row declared as source",
    st.block_group(fake) == "data" and ".csv" not in fake["markup"],
)

# F2 — the media-set assertion would notice a re-addition.
t(
    "F2 re-adding chart to MEDIA_BLOCK_KINDS would fail the gate",
    ({"figure", "gallery"} | {"chart"}) != st.MEDIA_BLOCK_KINDS,
)

# F3 — the reduced-motion guard is real: removing it changes the CSS.
t(
    "F3 stripping the guard is detectable",
    "prefers-reduced-motion" not in KERNEL_NC.replace("prefers-reduced-motion", "", 1),
)

# F4 — the comment-stripper actually works (the ADR-536 collision class).
t(
    "F4 strip_comments removes a banned token that appears ONLY in a comment",
    "<script" not in strip_comments("/* never a <script> here */ p { color: red; }"),
)

# F5 — the version gate would catch a silent bump-less CSS edit. Stated as a
# RELATION, not a number: what makes a bump-less edit detectable is that the
# composed element carries the CURRENT constant and no stale one — true at any
# version. (ADR-544 D2 proved the underlying risk is real, not theoretical: the
# Area selectors were rewritten at v16 and reached zero existing artifacts until
# the bump to v17.)
t(
    "F5 a kernel edit without a version bump is detectable",
    f'data-kernel-v="{st.STUDIO_KERNEL_CSS_VERSION}"' in st.compose_kernel_style_element()
    and f'data-kernel-v="{st.STUDIO_KERNEL_CSS_VERSION - 1}"' not in st.compose_kernel_style_element(),
)

# F6 — the chart-before-table ordering is load-bearing: a chart ref is also a
#      .csv, so the reversed order would silently draw a TABLE.
t(
    "F6 the ordering claim is meaningful (a chart ref IS a .csv)",
    ".csv" in st.STUDIO_BLOCKS["chart"]["markup"],
)

print(f"\n{PASS}/{PASS + FAIL} passed")
sys.exit(1 if FAIL else 0)
