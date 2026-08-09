"""ADR-542 — a token declares WHERE and WHEN (`applies` → scope × grains).

What this gate defends
======================
1. D1 — every token/measure row declares `scope` + `grains` from the two
   CLOSED enums; the compound `applies` field is gone from rows and wire.
2. D2 — one admitting function per side: the FE's `admits()` (executed here)
   and the lane's `_where_phrase` (executed here).
3. D3 — the completeness invariant, the ADR-536 defect ("computed and never
   mounted") as a standing gate: every served grain has a RESOLVED predicate
   in the pane's admits contexts, and every scope has a pane mount. A grain
   added to the registry without its FE predicate fails HERE, not in prod.
4. D5 — the dead chrome is gone: flow ships no mobile nav tab; the PAGE_SEL
   climb short-circuits on flow.

Run from api/:  python3 test_adr542_token_axes.py
"""

import re
import sys
from pathlib import Path

import services.authoring as st

ROOT = Path(__file__).resolve().parent.parent
PANE = (ROOT / "web/components/authoring/StudioDesignTab.tsx").read_text()
GRAMMAR = (ROOT / "web/components/authoring/tokenGrammar.ts").read_text()
SURFACE = (ROOT / "web/components/authoring/StudioSurface.tsx").read_text()
ROUTE = (ROOT / "api/routes/studio.py").read_text()

PASS = 0
FAIL = 0


def t(name: str, ok: bool) -> None:
    global PASS, FAIL
    print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    PASS += ok
    FAIL += not ok


print("=== 1. D1 — two closed axes, declared on every row ===")

ALL_ROWS = list(st.STUDIO_TOKENS.items()) + list(st.STUDIO_MEASURES.items())
for key, row in ALL_ROWS:
    t(
        f"`{key}` declares scope+grains from the closed enums (no applies)",
        "applies" not in row
        and isinstance(row.get("scope"), tuple)
        and set(row["scope"]) <= set(st.TOKEN_SCOPES)
        and len(row["scope"]) > 0
        and isinstance(row.get("grains"), tuple)
        and set(row["grains"]) <= set(st.TOKEN_GRAINS)
        and len(row["grains"]) > 0,
    )

t("the axes themselves are the declared enums (block/page/document × 8 grains)",
  st.TOKEN_SCOPES == ("block", "page", "document") and len(st.TOKEN_GRAINS) == 8)
t("`tone` is the two-scope witness (the row the compound encoding couldn't say)",
  st.STUDIO_TOKENS["tone"]["scope"] == ("block", "page")
  and st.STUDIO_TOKENS["tone"]["grains"] == ("any",))
t("the wire serves the axes and not the compound",
  '"scope": list(t["scope"])' in ROUTE
  and '"grains": list(t["grains"])' in ROUTE
  and '"applies"' not in ROUTE)

print("\n=== 2. D2 — the two admitting functions, EXECUTED ===")

# The lane's phrase composer.
t("_where_phrase composes scope × grains",
  st._where_phrase(("block",), ("staged", "media")).startswith("a block on a staged frame")
  and st._where_phrase(("block", "page"), ("any",)) == "a block / a page/slide element")
t("every declared value has a phrase (no silent axis value)",
  all(s in st.SCOPE_PHRASES for _, r in ALL_ROWS for s in r["scope"])
  and all(g in st.GRAIN_PHRASES for _, r in ALL_ROWS for g in r["grains"]))

# The FE's admits(), executed from its real body.
_m = re.search(r"export function admits\([\s\S]*?\{\n([\s\S]*?)\n\}", GRAMMAR)
t("admits() is extractable", _m is not None)
admits_body = _m.group(1) if _m else ""
import subprocess

_probe = subprocess.run(
    ["node", "-e", f"""
const admits = (row, scope, ctx) => {{ {admits_body} }};
const r = [];
r.push(admits({{scope:['block'],grains:['staged','media']}}, 'page', {{staged:true}}) === false);   // wrong scope
r.push(admits({{scope:['block'],grains:['any']}}, 'block', {{}}) === true);                          // unconditional
r.push(admits({{scope:['block'],grains:['staged','media']}}, 'block', {{staged:false,media:true}}) === true);  // ANY grain
r.push(admits({{scope:['block'],grains:['flow']}}, 'block', {{}}) === false);                        // unresolved predicate = false
console.log(r.every(Boolean) ? 'OK' : 'BAD:' + r.join(','));
"""],
    capture_output=True, text=True,
)
t("admits() behaves: scope gates, 'any' passes, ANY grain suffices, "
  "an unresolved predicate refuses (never renders on a guess)",
  _probe.stdout.strip() == "OK")

print("\n=== 3. D3 — the completeness invariant (ADR-536 as a standing gate) ===")

# Every scope has a pane mount consulting admits().
for scope in st.TOKEN_SCOPES:
    t(f"the pane mounts scope '{scope}' through admits()", f"admits(t, '{scope}'" in PANE
      or (scope == "block" and "admits(m, 'block'" in PANE))
# Every non-any grain is RESOLVED as a predicate somewhere in the pane's ctxs.
_ctx_src = PANE + SURFACE
GRAIN_RESOLUTIONS = {
    "staged": r"staged:",
    "flow": r"flow:",
    "media": r"media:",
    "callout": r"callout:",
    "deck": r"deck:",
    "multicol": r"multicol",
    "bg": r"bg:",
}
for g in st.TOKEN_GRAINS:
    if g == "any":
        continue
    t(f"grain '{g}' has a resolved predicate in a consumer context",
      re.search(GRAIN_RESOLUTIONS[g], _ctx_src) is not None)

# FALSIFIER, executed: a grain served WITHOUT a resolved predicate never
# admits — the control cannot silently render; and this gate's resolution
# table is itself pinned to the enum, so adding a grain without extending
# the table fails the loop above.
t("FALSIFIER: the resolution table covers exactly the non-any grains",
  set(GRAIN_RESOLUTIONS) == set(st.TOKEN_GRAINS) - {"any"})

print("\n=== 4. D5 — the dead chrome is gone ===")

t("flow ships NO mobile nav tab (the dead 'Outline' doorway)",
  "resolvedMode === 'paged'" in SURFACE
  and re.search(r"\.\.\.\(resolvedMode === 'paged'[\s\S]{0,120}'nav'", SURFACE) is not None)
t("the PAGE_SEL climb short-circuits on flow (always-empty rows not computed)",
  "mode === 'paged' && selectedEl" in PANE)

print(f"\n{PASS}/{PASS + FAIL} passed")
sys.exit(0 if FAIL == 0 else 1)
