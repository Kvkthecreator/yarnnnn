"""ADR-536 — the list kinds exist, and align comes back to the Text section.

Two defects, one scope: both are a control the canon PROMISED and the pane
could not reach.

D1 — the vocabulary had no ordinary list. ``checklist`` was the only list row
and it is a CHECKBOX list (``list-style:none`` + a ``☐`` pseudo-element), so a
member wanting a bullet or a numbered list had nothing to insert and nothing to
Turn into. Meanwhile the paste allowlist has always admitted ``UL``/``OL`` and
ADR-521 D4 shipped Tab/⇧Tab nesting *"in a list"* — the runtime could nest and
render a container the vocabulary could not NAME. The recognizer said so out
loud: ``PROMOTE_KIND`` mapped ``UL``/``OL`` to ``prose``, which is why a pasted
list reported as "prose" in the properties pane.

D2 — align/indent went missing in a re-cut. ADR-527 D3 restored ``align`` on
flow and added ``indent``, placing both in *"a new Text section, not a
resurrected Layout section"*. But the only mount for a block-grain token was
the Layout section, which lives in ``object`` scope — so when ADR-528 D2 turned
flow's ``block`` scope into ``range``, the tokens had no reachable home and
silently vanished. ``applicable`` still computed them (the ADR-527 D3 amendment
put ``block-flow`` in the filter, and the comment at that site still claims a
range "reaches tone + align/indent"); nothing rendered them. A token computed
and never mounted is the GREEN-GATES-TEST-THE-ROOM shape: the grain existed,
the scope existed, and the control was unreachable.

What is asserted:
  1. Both list kinds are registry rows, offered by every app.
  2. The kernel draws them, and the version bumped so they RETROFIT.
  3. The recognizer names them: PROMOTE_KIND, TEXT_BLOCK_KINDS, TURN_INTO_KINDS.
  4. convertBlock builds <li>, not <p>, for a <ul>/<ol> shell.
  5. align/indent are MOUNTED at range scope, derived from the served grain.
  6. Over a multi-block range they SPAN (ADR-541 D3 re-cut — one revision).
  7. FALSIFIERS — each structural claim is shown capable of failing.

Run from `api/`:  python3 test_adr536_lists_and_align.py
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import services.docs  # noqa: F401,E402 — registration side-effect (as the app does)
import services.authoring as st  # noqa: E402

WEB = Path(__file__).resolve().parent.parent / "web"
DESIGN_TAB = (WEB / "components/authoring/StudioDesignTab.tsx").read_text()
PROJECTION = (WEB / "components/workspace/viewers/projection.ts").read_text()
ARTIFACT_OPS = (WEB / "components/authoring/artifactOps.ts").read_text()

PASS, FAIL = 0, 0


def t(label: str, cond: bool) -> None:
    global PASS, FAIL
    print(("[PASS] " if cond else "[FAIL] ") + label)
    if cond:
        PASS += 1
    else:
        FAIL += 1


def strip_comments(src: str) -> str:
    """Line + block comments out.

    An absence assertion that matches its own explanatory COMMENT proves
    nothing — the recorded lesson from the gate that pinned "we do NOT call
    X()" and collided with the comment saying why.
    """
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", src)


DESIGN_TAB_CODE = strip_comments(DESIGN_TAB)
PROJECTION_CODE = strip_comments(PROJECTION)
ARTIFACT_OPS_CODE = strip_comments(ARTIFACT_OPS)


# ── 1. The rows exist, and belong to every app ────────────────────────────
t("D1: `list` and `numbered` are registry rows",
  "list" in st.STUDIO_BLOCKS and "numbered" in st.STUDIO_BLOCKS)

t("D1: both are UNSCOPED — every app offers them (no `apps` key)",
  "apps" not in st.STUDIO_BLOCKS["list"] and "apps" not in st.STUDIO_BLOCKS["numbered"])

_docs = st.blocks_for_app("docs")
t("D1: Docs offers both (the app that motivated them)",
  "list" in _docs and "numbered" in _docs)

t("D1: Studio offers both too — a shared roster, not a Docs fork",
  {"list", "numbered"} <= set(st.blocks_for_app("studio")))

t("D1: the shells are <ul> and <ol> respectively",
  '<ul data-block="list"' in st.STUDIO_BLOCKS["list"]["markup"]
  and '<ol data-block="numbered"' in st.STUDIO_BLOCKS["numbered"]["markup"])

t("D1: checklist SURVIVES — the checkbox list is a distinct kind, not replaced",
  "checklist" in st.STUDIO_BLOCKS
  and "list-style: none" in st.STUDIO_KERNEL_CSS + st._SHARED_CSS)


# ── 2. The kernel draws them, and the bump makes it retrofit ──────────────
t("D1: kernel draws the bulleted list (disc)",
  'ul[data-block="list"]' in st.STUDIO_KERNEL_CSS
  and "list-style: disc" in st.STUDIO_KERNEL_CSS)

t("D1: kernel draws the numbered list (decimal)",
  'ol[data-block="numbered"]' in st.STUDIO_KERNEL_CSS
  and "list-style: decimal" in st.STUDIO_KERNEL_CSS)

t("D1: padding-inline-start is DECLARED — the shared reset zeroes it, so a "
  "bare <ul> would collapse onto its markers",
  "padding-inline-start" in st.STUDIO_KERNEL_CSS)

t("D1: nesting steps the marker down (Tab/⇧Tab has shipped since ADR-521 D4)",
  'ul[data-block="list"] ul' in st.STUDIO_KERNEL_CSS
  and 'ol[data-block="numbered"] ol' in st.STUDIO_KERNEL_CSS)

t("D1: kernel version bumped to >= 15 — CSS alone retrofits nothing without it",
  st.STUDIO_KERNEL_CSS_VERSION >= 15)


# ── 3. The recognizer NAMES them ──────────────────────────────────────────
# The registry gap surfaced here: UL/OL promoted to `prose`, so a pasted list
# reported as a paragraph and got the prose roster in the pane.
t("D1: PROMOTE_KIND maps UL -> list (not prose)",
  re.search(r"UL:\s*'list'", ARTIFACT_OPS_CODE) is not None)

t("D1: PROMOTE_KIND maps OL -> numbered (not prose)",
  re.search(r"OL:\s*'numbered'", ARTIFACT_OPS_CODE) is not None)

t("D1: UL/OL no longer promote to prose (the old mapping is GONE, not shadowed)",
  re.search(r"UL:\s*'prose'", ARTIFACT_OPS_CODE) is None
  and re.search(r"OL:\s*'prose'", ARTIFACT_OPS_CODE) is None)

t("D1: TEXT_BLOCK_KINDS carries both — a list is typed IN, never select-only",
  re.search(r"TEXT_BLOCK_KINDS\s*=\s*\[(.*?)\]", PROJECTION_CODE, re.DOTALL)
  is not None
  and {"'list'", "'numbered'"}
  <= set(re.findall(r"'[a-z]+'",
                    re.search(r"TEXT_BLOCK_KINDS\s*=\s*\[(.*?)\]",
                              PROJECTION_CODE, re.DOTALL).group(1))))

# ADR-539 D2 re-cut: membership moved to the registry's `convertible` field;
# the FE derives (TURN_INTO_KINDS deleted). Same invariant, declared home.
from services.authoring import STUDIO_BLOCKS as _blocks_539
t("D1: the two list kinds are convertible — one declaration, two mounts",
  _blocks_539["list"]["convertible"] is True
  and _blocks_539["numbered"]["convertible"] is True
  and "b.convertible" in DESIGN_TAB_CODE)


# ── 4. convertBlock builds the LEGAL shape ────────────────────────────────
# The `else` fallback builds <p> children. Inside a <ul>/<ol> shell that is
# invalid markup that renders as unmarked text — a Turn into that visibly
# does nothing.
_conv = re.search(r"if \(kind === 'checklist'.*?\{(.*?)\}", ARTIFACT_OPS_CODE, re.DOTALL)
t("D1: convertBlock routes list/numbered through the <li> branch",
  re.search(r"kind === 'checklist' \|\| kind === 'list' \|\| kind === 'numbered'",
            ARTIFACT_OPS_CODE) is not None)

t("D1: ...and that branch is the one that pushes 'li'",
  _conv is not None and "'li'" in _conv.group(1))


# ── 5. align/indent are MOUNTED at range scope ────────────────────────────
t("D2: the served grain still declares align on flow (ADR-527 D3's amendment)",
  "flow" in st.STUDIO_TOKENS["align"]["grains"]
  and "flow" in st.STUDIO_TOKENS["indent"]["grains"])

t("D2: a `flowTokens` subset is DERIVED from the grain, not a hardcoded key list",
  "flowTokens" in DESIGN_TAB_CODE
  and re.search(r"grains\.includes\('flow'\)", DESIGN_TAB_CODE) is not None)

t("D2: the subset is NOT a hardcoded ['align','indent'] pair",
  re.search(r"\[\s*'align'\s*,\s*'indent'\s*\]", DESIGN_TAB_CODE) is None)

t("D2: TextSection RECEIVES the rows (the mount ADR-527 D3 specified)",
  re.search(r"flowTokens:\s*StudioToken\[\]", DESIGN_TAB_CODE) is not None
  and re.search(r"flowTokens=\{flowTokens\}", DESIGN_TAB_CODE) is not None)

t("D2: ...and RENDERS them through the shared TokenControl (one presentation)",
  re.search(r"flowTokens\.map\(", DESIGN_TAB_CODE) is not None)

t("D2: they write at BLOCK grain — data-align is text-align, on one block",
  re.search(r"onSetToken\('block',\s*key,\s*v\)", DESIGN_TAB_CODE) is not None)


# ── 6. Over a multi-block range: SPAN, not withdrawal (re-cut by ADR-541) ──
# ADR-536 shipped align/indent single-caret-only because the op addressed one
# `selectedEl` — a withdrawal it inherited from the d878242 rule. ADR-541 D3
# reversed that rule deliberately (both benchmarks apply block-grain
# transforms across a selection): the tokens now mount over ANY range and the
# SURFACE routes a spanning write through setTokenMany — every covered block,
# one revision. The invariant this section defends is unchanged one level
# down: the pane never silently answers for one block of many — now because
# the op takes them all, not because the control hid.
t("D2/ADR-541: align+indent mount over any range (span-aware, no !multi gate)",
  re.search(r"scope === 'range' \? applicable\.filter\(\(t\) => t\.grains\.includes\('flow'\)\)",
            DESIGN_TAB_CODE) is not None
  and re.search(r"scope === 'range' && !multiBlockRange", DESIGN_TAB_CODE) is None)

t("D2/ADR-541: a spanning token write routes through setTokenMany (one revision)",
  "setTokenMany(html, rangeBlockIds, key, value)"
  in (WEB / "components/authoring/StudioSurface.tsx").read_text())


# ── 7. FALSIFIERS — every structural claim can fail ───────────────────────
# A gate that cannot fail is not a gate. Each falsifier mutates the real
# artifact and asserts the check flips.
_f_ops = ARTIFACT_OPS_CODE.replace("UL: 'list'", "UL: 'prose'")
t("FALSIFIER: reverting UL->prose fails the promotion check",
  re.search(r"UL:\s*'list'", _f_ops) is None)

_f_tab = DESIGN_TAB_CODE.replace("flowTokens={flowTokens}", "")
t("FALSIFIER: unmounting flowTokens fails the mount check",
  re.search(r"flowTokens=\{flowTokens\}", _f_tab) is None)

_f_guard = DESIGN_TAB_CODE.replace("scope === 'range' && !multiBlockRange", "scope === 'range'")
t("FALSIFIER: dropping the multi-block guard fails the withdrawal check",
  re.search(r"scope === 'range' && !multiBlockRange", _f_guard) is None)

_f_blocks = {k: v for k, v in st.STUDIO_BLOCKS.items() if k != "list"}
t("FALSIFIER: removing the `list` row fails the registry check",
  "list" not in _f_blocks)

_f_css = st.STUDIO_KERNEL_CSS.replace("padding-inline-start", "padding-nothing")
t("FALSIFIER: dropping padding-inline-start fails the reset-escape check",
  "padding-inline-start" not in _f_css)


print(f"\n{PASS}/{PASS + FAIL} checks passed")
if FAIL:
    print("FAILED — see [FAIL] lines above")
sys.exit(0 if FAIL == 0 else 1)
