"""ADR-581 — the medium regroup (deck-first vocabulary ordering).

Checks, script-style (NOT pytest):
  D2  family DERIVES from declared fields — executed against the LIVE registry,
      never a hand matrix in this gate (a gate that re-keys the rows would only
      prove it agrees with itself; this one runs the ADR's formula over the
      served rows and asserts known anchors).
  D3  the ONE grouping module orders by medium; the doors pass their medium;
      NOTHING is hidden (family partition parity — order, never a filter).

Run:  cd api && python3 test_adr581_medium_regroup.py
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

API = pathlib.Path(__file__).parent
WEB = API.parent / "web"

checks = 0
failures = []


def _check(name: str, ok: bool, detail: str = ""):
    global checks
    checks += 1
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f" — {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(name)


print("── D2: family derives from the live registry ──")

from services.authoring import STUDIO_BLOCKS, STUDIO_KERNEL_CSS  # noqa: E402


def family(row) -> str:
    # The ADR-581 D2 formula, verbatim.
    if row["cites"] != "none":
        return "cited"
    return "composed" if row["tier"] == "object" else "prose"


fams = {k: family(r) for k, r in STUDIO_BLOCKS.items()}
_check(
    # ADR-583 moved `component` composed → cited (it cites a library fragment
    # now) — the DERIVATION is unchanged, the row's declaration changed.
    "the anchors classify as ratified (metrics/divider composed · heading/toggle prose · table/figure/component cited)",
    fams.get("component") == "cited"
    and fams.get("metrics") == "composed"
    and fams.get("divider") == "composed"
    and fams.get("heading") == "prose"
    and fams.get("toggle") == "prose"
    and fams.get("table") == "cited"
    and fams.get("figure") == "cited",
    detail=str(fams),
)
_check(
    "every kind lands in exactly one family (the partition is total)",
    set(fams.values()) <= {"prose", "composed", "cited"} and len(fams) == len(STUDIO_BLOCKS),
)
_check(
    # A FLOOR, not a parity: ADR-583 re-cut `component` out of the composed
    # family (it is cited now), so the honest claim is that D4's growth landed
    # and holds — 7 composed kinds (button·metrics·divider·stat·comparison·
    # timeline·person) against the pre-D4 three.
    "D4 shipped — the composed family holds its growth (>= 7 kinds)",
    sum(1 for f in fams.values() if f == "composed") >= 7,
)
_check(
    "the D4 growth set classifies by construction (stat/comparison/timeline/person composed · logo-row cited)",
    fams.get("stat") == "composed"
    and fams.get("comparison") == "composed"
    and fams.get("timeline") == "composed"
    and fams.get("person") == "composed"
    and fams.get("logo-row") == "cited",
    detail=str(fams),
)
_check(
    "the growth set stays out of turn-into and promotion (composed structure has no content counterpart)",
    all(
        STUDIO_BLOCKS[k]["convertible"] is False and STUDIO_BLOCKS[k]["promote"] is False
        for k in ("stat", "comparison", "timeline", "person", "logo-row")
    ),
)
_check(
    "the kernel draws every growth kind (registry row + kernel CSS land together, the ADR-536 rule)",
    all(
        f'[data-block="{k}"]' in STUDIO_KERNEL_CSS
        for k in ("stat", "comparison", "timeline", "person", "logo-row")
    ),
)

rows = (WEB / "components/authoring/blockRows.tsx").read_text()
_check(
    "the FE derivation matches (tier==='object' fork over a cites guard, no kind names)",
    "export function blockFamily" in rows
    and "b.tier === 'object' ? 'composed' : 'prose'" in rows
    and "'component'" not in rows.split("export function blockFamily")[1].split("}")[0],
)

print("── D3: the medium orders; nothing hides ──")

_check(
    "the ONE module orders by medium — composed leads on paged, prose on flow",
    "medium === 'paged' ? [...composed, ...prose] : [...prose, ...composed]" in rows,
)
_check(
    "the order is a partition of the SAME items (a filter here would be subsetting — refused, ADR-506 D3)",
    "blockFamily(b) === 'prose'" in rows
    and "blockFamily(b) === 'composed'" in rows
    and "blockFamily(b) === 'cited'" in rows,
)
palette = (WEB / "components/authoring/StudioSlashPalette.tsx").read_text()
_check(
    "the slash palette declares its constant medium (flow)",
    "groupBlockRows(matched, 'flow')" in palette,
)
menu = (WEB / "components/authoring/StudioBlockMenu.tsx").read_text()
_check(
    "the right-click tiers declare their constant medium (paged)",
    "groupBlockRows(blocks ?? [], 'paged')" in menu,
)
insert_menu = (WEB / "components/authoring/StudioBlockInsertMenu.tsx").read_text()
surface = (WEB / "components/authoring/StudioSurface.tsx").read_text()
_check(
    "the verb menu takes the RESOLVED medium from the surface",
    "groupBlockRows(items, medium)" in insert_menu
    and "medium={resolvedMode ?? null}" in surface,
)
_check(
    "the discovery door teaches — family subheaders inside NEW only (Composed · Text)",
    "verb === 'new' && g.key === 'new'" in insert_menu
    and "blockFamily(b) === 'composed' ? 'Composed' : 'Text'" in insert_menu,
)

print()
if failures:
    print(f"FAIL: {checks - len(failures)}/{checks} checks")
    sys.exit(1)
print(f"ADR-581 gate GREEN — {checks}/{checks}")
