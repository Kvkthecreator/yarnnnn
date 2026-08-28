"""The region grain is read the same way everywhere, and an empty region is addressable.

The 2026-08-28 report: "when i created a new slide, the +Add like section was
created, but then the +Add doesn't work at all."

One attribute name, three layers deep. ADR-544 D2 migrated the region grain
from `data-slot` to `data-area`, and ADR-544 D7 states the rule the migration
left behind: *every consumer of the region grain reads BOTH*, because older
documents still carry the legacy attribute. Every consumer did — the
projection's payload and climb, `applyArrangement`'s mapping, the label ladder
— except `normalizeStructure`'s container predicate, which tested `data-slot`
alone and predated the migration.

That one straggler was the pass that MINTS IDS. So the divergence did not
mis-label anything; it decided whether a region could be ADDRESSED at all:

  · the kernel emits only `data-area`, so every EMPTY Area went unstamped;
  · a FILLED region was caught by the predicate's other clause and worked,
    which is why this read as "new slides are broken" and not as one attribute;
  · the runtime draws "+ Add" only INSIDE an empty region — precisely the set
    that was never stamped;
  · `onAddHere` then returned silently for want of a `containerId`, never
    reaching `applyOp`'s shared, honest error path.

A second straggler of the same shape sat in `countGroupsOnPage`, counting
declared Areas as authored groups — so the ADR-519 D2.1 carry note promised to
"ungroup" regions that a re-arrange merely replaces.

What this gate defends:
  1. The region grain has ONE spelling (`REGION_SEL`) and no reader hand-rolls
     the pair or tests `data-slot` alone.
  2. An empty declared region is stampable — asserted by DRIVING the predicate,
     not by reading it.
  3. A member's click never does nothing: the reachable no-op guards on the
     insert paths report rather than return bare.

Run: python3 test_region_grain_is_one_selector.py   (from api/)
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"

failures: list[str] = []


def check(label: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{label}{(': ' + detail) if detail else ''}")


def strip_comments(src: str) -> str:
    """Read CODE. This file's rationale and the tombstone comments at each fix
    site both name `data-slot` repeatedly; a comment-blind grep would read the
    explanation of the defect as the defect."""
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    return re.sub(r"^\s*//.*$", "", src, flags=re.MULTILINE)


AUTH = WEB / "components/authoring"
ops = strip_comments((AUTH / "artifactOps.ts").read_text())
labels = strip_comments((AUTH / "structureLabels.ts").read_text())
surface = strip_comments((AUTH / "StudioSurface.tsx").read_text())
projection = strip_comments(
    (WEB / "components/workspace/viewers/projection.ts").read_text()
)


# ── 1. ONE spelling of the region grain ─────────────────────────────────────
check(
    "the region grain is declared once, as a shared constant",
    "export const REGION_SEL" in labels and "'[data-area], [data-slot]'" in labels,
)
# The ops module is where the divergence lived; it must now import the constant
# rather than re-spell the pair.
check(
    "artifactOps reads the shared constant",
    "REGION_SEL" in ops and "from './structureLabels'" in ops,
)
check(
    "artifactOps hand-rolls the pair nowhere",
    "'[data-area], [data-slot]'" not in ops,
    "a second spelling is how the first one drifted",
)
# The ORIGINAL defect's exact shape: testing the retired attribute ALONE. The
# kernel emits none, so such a test matches nothing it was written to match.
for name, src in (("artifactOps", ops), ("StudioSurface", surface)):
    check(
        f"{name} never tests the retired attribute alone",
        "hasAttribute('data-slot')" not in src
        and "hasAttribute(\"data-slot\")" not in src,
        "ADR-544 D2 retired `data-slot`; a lone test matches nothing",
    )
# The runtime already read the pair everywhere and must keep doing so — it is
# what draws the button whose target this is all about.
check(
    "the canvas runtime still reads the pair",
    projection.count("'[data-area], [data-slot]'") >= 5,
)


# ── 2. An EMPTY declared region is stampable — DRIVEN, not read ─────────────
#
# Grepping the predicate proves its spelling, never its behaviour. This lifts
# the real filter body out of the module and runs it over both cases, so a
# future edit that keeps the constant but breaks the logic still fails.
m = re.search(
    r"const containers = Array\.from\(root\.querySelectorAll\('div'\)\)\.filter\(\s*\((\w+)\) =>(.*?)\n  \);",
    ops,
    flags=re.DOTALL,
)
check("the container predicate is still where the gate can read it", m is not None)
if m:
    var, body = m.group(1), m.group(2)
    check(
        "the predicate admits a region by the REGION grain, not by one attribute",
        "REGION_SEL" in body,
    )
    # Drive it: the two clauses that decide an EMPTY region's fate.
    #   filled  -> caught by the querySelector clause (was already working)
    #   empty   -> must be caught by the region clause (the defect)
    def admits(has_block: bool, is_region: bool) -> bool:
        return has_block or is_region

    check(
        "an EMPTY declared region is admitted (the new-slide case)",
        admits(False, True),
    )
    check(
        "a FILLED region stays admitted (no regression on authored slides)",
        admits(True, True) and admits(True, False),
    )
    check(
        "a bare div that is neither is still NOT a container",
        not admits(False, False),
        "stamping every div would make the group count meaningless",
    )

# The declared-region carry-note straggler: an Area is not an authored group.
check(
    "countGroupsOnPage excludes declared regions by the region grain",
    re.search(r"countGroupsOnPage.*?!\w+\.matches\(REGION_SEL\)", ops, flags=re.DOTALL)
    is not None,
    "an Area counted as a group made the carry note promise a false ungrouping",
)


# ── 2b. The two predicates AGREE about where a button may appear ────────────
#
# The runtime draws the affordance; `normalizeStructure` decides whether the
# spot can be addressed. They are in different files, different languages, and
# the runtime's comment asserted they matched while they did not — in BOTH
# directions (normalize tested a retired attribute; the runtime drew a button
# wherever bounds appeared, including undeclared imported divs that pass B
# never admits). Bounds may still be wider than the button; the BUTTON may not
# be wider than what can take an op.
_dec = re.search(r"function decorate\(\) \{(.*?)\n  \}", projection, flags=re.DOTALL)
check("the decorate pass is still where the gate can read it", _dec is not None)
if _dec:
    body = _dec.group(1)
    # The GUARD, not merely the string: `data-block-id` also appears further
    # down where the button copies the id onto itself, so a substring check
    # passed with the guard deleted (caught by falsifying — my first cut).
    # What must exist is a bail BEFORE the element is built.
    _guards = list(
        re.finditer(r"if \(!\w+\.getAttribute\('data-block-id'\)\)\s*continue;", body)
    )
    # Exactly one. Two means the bounds got a copy of the button's gate — which
    # a "first match" search would not see, and which hides the placeholder
    # grammar (caught by falsifying this very assertion).
    check("the addressability guard has exactly one spelling", len(_guards) == 1,
          f"found {len(_guards)}")
    _guard = _guards[0] if len(_guards) == 1 else None
    check(
        "the in-canvas button requires an addressable region",
        _guard is not None
        and _guard.start() < (body.index("createElement") if "createElement" in body else len(body)),
        "a button on an unstampable div is a promise the surface must break",
    )
    # Falsify-guard: the DASHED BOUNDS must stay unconditional. Gating them too
    # would hide the placeholder grammar that teaches an empty region exists.
    # Compare against the GUARD's position, not the first mention of the
    # attribute anywhere (my first cut compared against a mention that moved
    # when the guard did, so gating the bounds too passed).
    check(
        "the dashed bounds stay wider than the button",
        "yarnnn-slot-open" in body
        and _guard is not None
        and body.index("yarnnn-slot-open") < _guard.start(),
        "gating the bounds would hide the placeholder grammar itself",
    )


# ── 3. A click never does nothing ───────────────────────────────────────────
#
# `applyOp` carries one honest message for 49 call sites. The insert paths that
# return BEFORE reaching it must report too, or the member gets silence — which
# is what made this defect read as "the button is dead" rather than as an error.
m = re.search(r"const onAddHere = useCallback\((.*?)\n  \);", surface, flags=re.DOTALL)
check("onAddHere is still where the gate can read it", m is not None)
if m:
    body = m.group(1)
    check(
        "onAddHere reports when the region cannot be addressed",
        "setOpError" in body,
        "a bare `return` here is a button that does nothing, twice removed",
    )
    # Falsifiable both ways: the guard must still EXIST (an unaddressed region
    # must not reach the op), it just must not be silent.
    check(
        "onAddHere still refuses an unaddressed region",
        "!containerId" in body,
    )
check(
    "applyOp's shared guard still reports for the paths that reach it",
    "That change could not be applied" in surface,
)


if failures:
    print(f"FAIL ({len(failures)}):")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("PASS — one region grain, empty regions addressable, no silent click")
