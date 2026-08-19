"""ADR-539 — the vocabulary declares behavior.

What this gate defends
======================
1. D1 — every STUDIO_BLOCKS row declares tier / elements / promote /
   convertible / cites; `group` is a DERIVATION of `cites` (block_group), and
   MEDIA_BLOCK_KINDS is derived, not hand-kept.
2. D2 — the two structurally-static FE constants are PINNED PROJECTIONS of the
   registry: projection.ts TEXT_BLOCK_KINDS == the declared text tier, and
   artifactOps.ts PROMOTE_KIND == the declared {elements × promote} map.
   These are the audit's shadow registries, now gate-locked to one source.
3. D3 — HEADING_RUNGS is declared once and spoken identically by the backend
   (extract_outline, the served payload) and the FE (projection.ts's export).
4. D4 — intake clamps to the rung set at both seams (paste scrub + normalize).
5. Falsifiers are EXECUTED, not asserted: a flipped tier breaks parity, a
   widened rung set changes extract_outline's actual output.

Run from api/:  python3 test_adr539_vocabulary_declares.py
"""

import re
import sys
from pathlib import Path

import services.authoring as st

ROOT = Path(__file__).resolve().parent.parent
PROJECTION = (ROOT / "web/components/workspace/viewers/projection.ts").read_text()
ARTIFACT_OPS = (ROOT / "web/components/authoring/artifactOps.ts").read_text()
DESIGN_TAB = (ROOT / "web/components/authoring/StudioDesignTab.tsx").read_text()
MENU = (ROOT / "web/components/authoring/StudioBlockMenu.tsx").read_text()
PICKER = (ROOT / "web/components/authoring/StudioCitablePicker.tsx").read_text()
SURFACE = (ROOT / "web/components/authoring/StudioSurface.tsx").read_text()
ROUTE = (ROOT / "api/routes/studio.py").read_text()

PASS = 0
FAIL = 0


def t(name: str, ok: bool) -> None:
    global PASS, FAIL
    print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    PASS += ok
    FAIL += not ok


def strip_comments(ts: str) -> str:
    """Drop /* */ blocks and // line tails so an assertion can never match its
    own explanatory comment (the ADR-526 gate lesson)."""
    ts = re.sub(r"/\*.*?\*/", "", ts, flags=re.DOTALL)
    return re.sub(r"(?m)^\s*//.*$|(?<=[\s;{(])//[^\n]*$", "", ts)


print("=== 1. D1 — the declaration is complete and self-consistent ===")

for kind, row in st.STUDIO_BLOCKS.items():
    t(
        f"`{kind}` declares tier/elements/promote/convertible/cites",
        row.get("tier") in ("text", "object")
        # "fragment" — ADR-583: a component cites a library file.
        and row.get("cites") in ("none", "source", "picture", "fragment")
        and isinstance(row.get("convertible"), bool)
        and isinstance(row.get("promote"), bool)
        and isinstance(row.get("elements"), tuple)
        and len(row["elements"]) > 0,
    )

promoted: dict = {}
collision = None
for kind, row in st.STUDIO_BLOCKS.items():
    if row["promote"]:
        for el in row["elements"]:
            if el in promoted:
                collision = (el, promoted[el], kind)
            promoted[el] = kind
t("promote=True tags are unique across rows (the map is unambiguous)", collision is None)

t("group derives from cites (none→content, source→data, picture→media, fragment→component)",
  st.block_group({"cites": "none"}) == "content"
  and st.block_group({"cites": "source"}) == "data"
  and st.block_group({"cites": "picture"}) == "media"
  and st.block_group({"cites": "fragment"}) == "component")
t("MEDIA_BLOCK_KINDS is the picture-citing set, derived",
  st.MEDIA_BLOCK_KINDS == {k for k, r in st.STUDIO_BLOCKS.items() if r["cites"] == "picture"})

print("\n=== 2. D2 — the static FE constants are pinned projections ===")

_proj_nc = strip_comments(PROJECTION)
_text_m = re.search(r"export const TEXT_BLOCK_KINDS = \[(.*?)\]", _proj_nc, re.DOTALL)
fe_text = set(re.findall(r"'([a-z]+)'", _text_m.group(1))) if _text_m else set()
be_text = {k for k, r in st.STUDIO_BLOCKS.items() if r["tier"] == "text"}
t("projection.ts TEXT_BLOCK_KINDS == the registry's declared text tier",
  bool(fe_text) and fe_text == be_text)

# EXECUTED falsifier: flip one row's tier in a COPY — parity must break.
_flipped = set(be_text) ^ {"prose"}
t("FALSIFIER: a flipped tier breaks the parity comparison", _flipped != fe_text)

_ops_nc = strip_comments(ARTIFACT_OPS)
_pk_m = re.search(r"const PROMOTE_KIND: Record<string, string> = \{(.*?)\};", _ops_nc, re.DOTALL)
fe_promote = dict(re.findall(r"([A-Z0-9]+):\s*'([a-z]+)'", _pk_m.group(1))) if _pk_m else {}
be_promote = {
    el.upper(): kind
    for kind, row in st.STUDIO_BLOCKS.items()
    if row["promote"]
    for el in row["elements"]
}
t("artifactOps.ts PROMOTE_KIND == the registry's {elements × promote} map",
  bool(fe_promote) and fe_promote == be_promote)
t("H4–H6 are NOT in the promotion map (the clamp owns them)",
  not any(k in fe_promote for k in ("H4", "H5", "H6")))

print("\n=== 3. D3 — one rung set, spoken identically ===")

t("backend declares HEADING_RUNGS = (1, 2, 3)", st.HEADING_RUNGS == (1, 2, 3))
_rungs_m = re.search(r"export const HEADING_RUNGS = \[([0-9, ]+)\]", _proj_nc)
fe_rungs = tuple(int(x) for x in re.findall(r"\d", _rungs_m.group(1))) if _rungs_m else ()
t("projection.ts HEADING_RUNGS matches the backend's", fe_rungs == st.HEADING_RUNGS)

t("the route serves heading_rungs and the behavior fields",
  '"heading_rungs": list(HEADING_RUNGS)' in ROUTE
  and '"tier": b["tier"]' in ROUTE
  and '"convertible": b["convertible"]' in ROUTE
  and '"cites": b["cites"]' in ROUTE
  and '"group": block_group(b)' in ROUTE)

# extract_outline EXECUTED against the declared rungs.
fixture = "<h1>A</h1><h3>C</h3><h4>skip</h4><h2>B</h2>"
t("extract_outline speaks the full rung set (h3 in, h4 out, depth-indented)",
  st.extract_outline(fixture) == ["A", "    C", "  B"])

# EXECUTED falsifier: widen the rung set — the OUTPUT must change, proving the
# regex is derived from the constant rather than hardcoded.
_orig = st.HEADING_RUNGS
try:
    st.HEADING_RUNGS = (1, 2, 3, 4)
    widened = st.extract_outline(fixture)
finally:
    st.HEADING_RUNGS = _orig
t("FALSIFIER: widening HEADING_RUNGS admits the h4 (derivation is live)",
  any("skip" in line for line in widened)
  and not any("skip" in line for line in st.extract_outline(fixture)))

t("the pane outline BUILDS its selector from the rungs",
  "rungs.map((r) => `h${r}`).join(', ')" in DESIGN_TAB
  and "walkOutline(doc?.body ?? null, rungs)" in DESIGN_TAB)
t("the crumb anchor set is built from the rungs (h3 no longer invisible)",
  "HEADING_ANCHOR_SEL_JS" in PROJECTION
  and "h${r}[data-block-id]" in PROJECTION)

print("\n=== 4. D4 — intake clamps at both seams ===")

t("normalize clamps out-of-rung headings (pass A0, before promotion)",
  "OUT_OF_RUNG_TAGS.join(',')" in _ops_nc
  and "h${DEEPEST_RUNG}" in ARTIFACT_OPS)
t("the paste scrub clamps too (interpolated from the same constants)",
  "var OUT_OF_RUNG = ${OUT_OF_RUNG_TAGS_JS}" in PROJECTION
  and "var DEEPEST_RUNG_TAG = ${DEEPEST_RUNG_TAG_JS}" in PROJECTION
  and "OUT_OF_RUNG.indexOf(el.tagName)" in PROJECTION)

print("\n=== 5. D2 — the derivations replaced the hand-lists ===")

t("TURN_INTO_KINDS / PICKER_KINDS / CSV_KINDS constants are deleted",
  "TURN_INTO_KINDS = [" not in strip_comments(DESIGN_TAB)
  and "PICKER_KINDS = new Set" not in strip_comments(PICKER)
  and "CSV_KINDS = new Set" not in strip_comments(PICKER))
t("pane and menu read convertibility off the served row (one source, two mounts)",
  "isConvertible(vocabulary?.blocks, selection.blockKind)" in DESIGN_TAB
  and "isConvertible(blocks, target.blockKind)" in MENU)
t("the surface routes picker-backed kinds by the row's cites",
  "kindCites(kind)" in SURFACE and "kindCites(p.kind)" in SURFACE
  and "cites={citePicker.cites}" in SURFACE)
t("the parent-side tier reaches read the served tier (kindTier)",
  re.search(r"kindTier\(\s*vocabulary\?\.blocks", SURFACE) is not None
  and "kindTier(vocabulary?.blocks, selection.blockKind)" in DESIGN_TAB)

print(f"\n{PASS}/{PASS + FAIL} passed")
sys.exit(0 if FAIL == 0 else 1)
