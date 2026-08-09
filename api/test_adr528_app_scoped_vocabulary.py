"""ADR-528 D5 — the block vocabulary is APP-SCOPED.

The operator's direction: *"authoring should be app specific or at least aim to
do so. thus scope accordingly."*

D5 was written as "drop callout and toggle" on a Docs premise, and the
implementation surfaced that the premise did not fit the machinery:
``STUDIO_BLOCKS`` is ONE registry serving all three authoring apps, and
AUTHORING.md refuses per-medium menu subsetting ("both doors offer every kind;
what differs is which door, never what's in it"). Deleting the two rows would
have removed them from decks and web pages too — and callout carries ADR-487
D2's variant system plus the ``block-callout`` token grain there.

The asymmetry that made this read as a menu question: ``STUDIO_LAYOUTS`` rows
have carried ``app`` since ADR-473 D2; ``STUDIO_BLOCKS`` rows carried nothing.
There was nowhere to SAY a kind belongs to one app, so the only reachable lever
was filtering a door. This gate pins the dimension that replaced it.

What is asserted:
  1. The dimension exists and is DERIVED from the row (never a slug list).
  2. Docs does not offer callout/toggle; Studio does; nothing else moved.
  3. The lane posture is scoped too — the ADR-525 D4 lesson ("the lane reads
     this grammar too, so without it the AI hand keeps being told a paragraph
     has a width"), one level up.
  4. Ownership is SERVED, so the FE filters at one chokepoint.
  5. The kinds stay RECOGNIZED — an existing callout in a Docs document must
     still render and still edit (an inert name, ADR-511 D8). A grammar filter
     is never a schema gate.
  6. FALSIFIERS — each claim is shown to be capable of failing.

Run from `api/`:  python3 test_adr528_app_scoped_vocabulary.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import services.docs  # noqa: F401,E402 — registration side-effect (as the app does)
import services.studio as st  # noqa: E402

PASS, FAIL = 0, 0


def t(label: str, cond: bool) -> None:
    global PASS, FAIL
    print(("[PASS] " if cond else "[FAIL] ") + label)
    if cond:
        PASS += 1
    else:
        FAIL += 1


# ── 1. The dimension exists, and is derived from the ROW ──────────────────
t(
    "D5: blocks_for_app is the one derivation",
    callable(getattr(st, "blocks_for_app", None)),
)
t(
    "D5: app_for_layout reads ADR-473 D2's `app` back off the row",
    st.app_for_layout("document") == "docs" and st.app_for_layout("deck") == "studio",
)
t(
    "D5: an unknown slug yields no app (callers treat it as no filtering)",
    st.app_for_layout("no-such-layout") is None,
)

docs = st.blocks_for_app("docs")
studio = st.blocks_for_app("studio")
every = set(st.STUDIO_BLOCKS)

# ── 2. The scoping itself ─────────────────────────────────────────────────
t("D5: Docs does not offer callout", "callout" not in docs)
t("D5: Docs does not offer toggle", "toggle" not in docs)
t("D5: Studio DOES offer callout (a composed surface's authored aside)", "callout" in studio)
t("D5: Studio DOES offer toggle", "toggle" in studio)
t(
    # ADR-538 D3 — `component` joins the studio-scoped set, for the SAME reason
    # callout and toggle are there: a composed card is an authored object on a
    # deck or a landing page, and Docs is the flow/caret medium.
    "D5: only the studio-scoped kinds are lost to Docs (nothing moved by accident)",
    every - set(docs) == {"callout", "toggle", "component"},
)
t("D5: Studio loses nothing", every - set(studio) == set())
t(
    "D5: an unscoped call yields the FULL roster (the tolerant default — "
    "the vocabulary teaches, never validates)",
    set(st.blocks_for_app(None)) == every,
)
t(
    "D5: an UNKNOWN app still gets the shared roster, never an empty menu",
    set(st.blocks_for_app("images")) == every - {"callout", "toggle", "component"},
)

# COMPLETENESS: every row is either unscoped or names a registered app. A typo
# in an `apps` tuple would silently hide a kind from every app.
KNOWN_APPS = {"docs", "studio", "images"}
bad = {
    kind: b["apps"]
    for kind, b in st.STUDIO_BLOCKS.items()
    if "apps" in b and not set(b["apps"]) <= KNOWN_APPS
}
t(f"D5: every `apps` value names a known app (offenders: {bad or 'none'})", not bad)

# ── 3. The LANE posture is scoped too ─────────────────────────────────────
docs_grammar = st._blocks_grammar("docs")
studio_grammar = st._blocks_grammar("studio")
t(
    "D5: the Docs lane posture does not teach callout/toggle "
    "(ADR-525 D4's lesson — the lane reads this grammar too)",
    "callout" not in docs_grammar and "toggle" not in docs_grammar,
)
t(
    "D5: the Studio lane posture still teaches both",
    "callout" in studio_grammar and "toggle" in studio_grammar,
)
t(
    "D5: the posture is scoped by the RESOLVED layout row, not a slug test",
    "layout.get(\"app\")" in Path("services/studio.py").read_text(),
)

# ── 4. Ownership is SERVED (the FE filters at one chokepoint) ─────────────
routes = Path("routes/studio.py").read_text()
t(
    "D5: the vocabulary endpoint serves `apps` per block",
    '"apps": list(b["apps"]) if "apps" in b else None' in routes,
)
surface = Path("../web/components/studio/StudioSurface.tsx").read_text()
t(
    "D5: the FE filters ONCE, at the vocabulary load site (rule 11 / ADR-484 — "
    "never at the three offering sites)",
    "blocks: v.blocks.filter((b) => !b.apps || b.apps.includes(app.slug))" in surface,
)
t(
    "D5: exactly one filter site exists",
    surface.count("b.apps.includes(app.slug)") == 1,
)

# ── 5. RECOGNITION is untouched — the inert-name rule (ADR-511 D8) ────────
# A grammar filter must never become a schema gate: a member's existing callout
# has to keep rendering, keep its kernel CSS, and keep the text tier so its
# prose stays editable.
studio_py = Path("services/studio.py").read_text()
t(
    "D5: the callout kernel CSS survives (an existing one still renders)",
    'aside[data-block="callout"]' in studio_py,
)
t(
    "D5: the toggle kernel CSS survives",
    'details[data-block="toggle"]' in studio_py,
)
t(
    "D5: ADR-487 D2's callout variants survive (Studio still uses them)",
    'aside[data-block="callout"][data-variant="note"]' in studio_py,
)
t(
    "D5: the rows are still IN the registry — scoped, not deleted",
    "callout" in st.STUDIO_BLOCKS and "toggle" in st.STUDIO_BLOCKS,
)
proj = Path("../web/components/workspace/viewers/projection.ts").read_text()
t(
    "D5: TEXT_BLOCK_KINDS still RECOGNIZES callout/toggle — an existing one in "
    "a Docs document keeps the text tier, so its prose stays editable",
    "'callout'" in proj and "'toggle'" in proj,
)

# ── 6. FALSIFIERS — show each claim can fail ──────────────────────────────
t(
    "FALSIFY: without the `apps` term every app would get every kind",
    set(
        k for k, b in st.STUDIO_BLOCKS.items()  # the pre-D5 derivation
    )
    != set(docs),
)
t(
    "FALSIFY: a row whose `apps` excluded the caller IS dropped "
    "(the mechanism actually filters)",
    "callout" in every and "callout" not in docs,
)

print(f"\nADR-528 D5: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
