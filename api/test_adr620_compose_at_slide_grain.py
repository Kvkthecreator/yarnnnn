"""ADR-620 — Compose is Rewrite at slide grain.

`+ Add` stamps registry fragments whose bytes are literal (`42%`, `label`), so
a member gets a shape and fills every hole by hand. Rewrite is judged, seeded
and receipted — and stops at the block. Compose closes that gap at slide grain,
and the whole safety argument is that it closes it **through the machinery that
already exists** rather than beside it.

What this gate defends, in the order the design can fail:

  1. ONE WRITE PATH. A first cut built a `/studio/compose/plan` endpoint, a
     validator and an `applyComposePlan` op — a faithful mirror of ADR-479's
     re-arrange planner, and a second way to author the same substrate. All
     three were deleted before shipping. Their absence is the invariant: the
     lane already has EditFile-with-anchor, the block grammar and one
     attributed write.

  2. ONE PRODUCER. Rewrite and Compose seed the same composer through the same
     `seedRewrite`/`seedComposer` site. Two producers would be two acts under
     one vocabulary, and nothing at build time would say so.

  3. THE PERMISSION IS THE MEMBER'S. `remove` destroys their own words. The
     choice rides the seed and is stated in the frame in BOTH directions — an
     absent instruction is not a prohibition, and a colleague told nothing
     about removal will infer its own license from the word "compose".

  4. THE GRAIN READS RIGHT. `_seed_line` resolved the page grain as "no block
     id", true only because pre-620 nothing at page grain carried one. A
     composed slide carries the PAGE's id (stamped since ADR-519), so the proxy
     would have said "the slide block". Both the frame and the chip now read
     the LABEL — and must agree, because the same gesture is rendered before
     Send (the chip) and after (the transcript).

Run: python3 test_adr620_compose_at_slide_grain.py   (from api/)
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from services.lane_runner import _seed_line  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
API = ROOT / "api"

failures: list[str] = []


def check(label: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{label}{(': ' + detail) if detail else ''}")


def strip_ts_comments(src: str) -> str:
    """Read CODE. Every site here carries a comment naming what was deleted
    ("no plan endpoint", "applyComposePlan"), so a comment-blind grep would
    read the tombstone as the thing it buried."""
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    return re.sub(r"^\s*//.*$", "", src, flags=re.MULTILINE)


AUTH = WEB / "components/authoring"
surface = strip_ts_comments((AUTH / "StudioSurface.tsx").read_text())
pane = strip_ts_comments((AUTH / "StudioDesignTab.tsx").read_text())
ops = strip_ts_comments((AUTH / "artifactOps.ts").read_text())
client = strip_ts_comments((WEB / "lib/api/client.ts").read_text())
lane_panel = (WEB / "components/chat-surface/LanePanel.tsx").read_text()
insert_menu = strip_ts_comments((AUTH / "StudioBlockInsertMenu.tsx").read_text())
studio_routes = (API / "routes/studio.py").read_text()
lanes_routes = (API / "routes/lanes.py").read_text()


# ── 1. ONE write path: the deleted stack stays deleted ──────────────────────
check(
    "no compose PLAN endpoint",
    "compose/plan" not in studio_routes
    and "ComposePlanRequest" not in studio_routes
    and not (API / "services/studio_compose_plan.py").exists(),
    "the lane already has EditFile + the block grammar (ADR-462 D1)",
)
check("no compose plan client method", "composePlan" not in client)
check("no compose-specific applier op", "applyComposePlan" not in ops)
# The arrangement planner is a DIFFERENT act and must survive untouched — this
# ADR explicitly does not re-frame it (§2).
check(
    "the arrangement planner is untouched",
    "arrangement/plan" in studio_routes
    and (API / "services/studio_arrangement_plan.py").exists(),
)
# The billing block was extracted when the second planner was contemplated;
# the extraction is a genuine dedup and stays, with its one caller.
check(
    "the plan meter is named once and still used",
    "def _meter_plan(" in studio_routes
    and studio_routes.count("_meter_plan(auth,") >= 1,
)


# ── 2. ONE producer, two verbs ──────────────────────────────────────────────
check(
    "the surface composes a seed at exactly ONE site",
    surface.count("seedComposer('', {") == 1,
    "two producers is two acts under one vocabulary",
)
for door in ("rewriteSelection", "menuRewrite", "composeSlide"):
    check(f"{door} exists", f"const {door} = useCallback(" in surface)
_c = re.search(r"const composeSlide = useCallback\((.*?)\n  \);", surface, flags=re.DOTALL)
check("composeSlide is readable by the gate", _c is not None)
if _c:
    body = _c.group(1)
    # Through the PRODUCER, never composing a seed itself. My first cut of
    # composeSlide called seedComposer directly and this gate caught it — a
    # second producer that would have drifted from Rewrite's the first time
    # either changed.
    check(
        "compose routes through the one producer",
        "seedRewrite(" in body and "seedComposer(" not in body,
    )
    check("compose declares its verb", "verb: 'compose'" in body)
    check(
        "compose carries the page index — the grain's address",
        "pageIndex" in body and "slideIndex" in body,
    )
    check(
        "compose defaults to ADDITIVE (D3 — the destructive reading is chosen)",
        "replace: false" in body,
    )


# ── 3. The door is the PANE, and Add gained no AI row ───────────────────────
check(
    "the pane offers Compose at page scope",
    "onCompose" in pane and "Compose this {pageNoun}" in pane,
)
check("the surface wires it", "onCompose={composeSlide}" in surface)
# D5 — the catalog stays a catalog. A second Add door differing by a modifier
# is the shape ADR-616 and ADR-619 each deleted.
# A ROW, not the word: the door's empty-state copy legitimately says "ask the
# chat to compose one", which a bare substring search reads as a violation.
# What must not exist is a compose HANDLER or a judged pick.
check(
    "the insert door gained no AI/compose row",
    "onCompose" not in insert_menu
    and "verb: 'compose'" not in insert_menu
    and "seedComposer" not in insert_menu,
    "+ Add is the catalog of things that EXIST",
)
# D4 — a chip that grew a body, never a modal.
check(
    "the housing is the composer chip, not a modal",
    "pendingSeed.verb === 'compose'" in lane_panel
    and "role=\"dialog\"" not in lane_panel,
)


# ── 4. The permission reaches the colleague, in BOTH directions ─────────────
check("LaneSeed carries the choice", "compose_replace" in lanes_routes)
check("the wire carries it", "compose_replace" in lane_panel)

_base = {"verb": "compose", "block_id": "pg7", "label": "slide", "page_index": 6}
_additive = _seed_line({**_base, "compose_replace": False})
_replace = _seed_line({**_base, "compose_replace": True})

check("a compose renders a gesture line at all", bool(_additive))
check(
    "the ADDITIVE case is an INSTRUCTION, not a silence",
    "FILL IN" in _additive and "do not delete" in _additive,
    "an absent instruction is not a prohibition",
)
check(
    "the REPLACE case states the permission",
    "REMOVE" in _replace,
)
check(
    "the two readings differ",
    _additive != _replace and "do not delete" not in _replace,
)
check(
    "compose teaches what to write, not just what it may touch",
    "actual words" in _additive and "placeholder" in _additive.lower(),
)


# ── 5. The page grain reads "slide N", in BOTH renderings ───────────────────
#
# Driven, not grepped: the defect was a PROXY that happened to be true, so only
# exercising the case it fails on can catch it.
check(
    "the frame calls a composed slide `slide 7`, never `the slide block`",
    "slide 7" in _additive and "slide block" not in _additive,
    "the noun must read the LABEL, not the absence of a block id",
)
# A block-grain gesture must be unaffected by that fix.
_block = _seed_line(
    {"verb": "rewrite", "block_id": "b3", "label": "heading", "excerpt": "Hi"}
)
check(
    "a block gesture still reads `the heading block`",
    "the heading block" in _block,
)
# The chip mirrors it — the same gesture is rendered before Send (chip) and
# after (transcript), and reading differently is the drift.
_noun = re.search(r"function seedTargetNoun\(t: SeedTarget\): string \{(.*?)\n\}", lane_panel, flags=re.DOTALL)
check("seedTargetNoun is readable by the gate", _noun is not None)
if _noun:
    check(
        "the chip reads the LABEL for the page grain, like the frame",
        "t.label === 'slide'" in _noun.group(1),
        "`!t.blockId` alone would call a composed slide a block",
    )


# ── 6. The verb is admitted end to end ──────────────────────────────────────
check("the FE union admits compose", "'check' | 'compose'" in lane_panel)
check(
    "the wire reader admits compose",
    "verb !== 'compose'" in lane_panel,
    "a stamp it rejects renders a composed turn as a plain one",
)


if failures:
    print(f"FAIL ({len(failures)}):")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("PASS — compose is Rewrite's sibling: one producer, one write path, the member's permission")
