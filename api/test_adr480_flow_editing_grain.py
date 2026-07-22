#!/usr/bin/env python3
"""Gate: ADR-480 — the editing grain is per-mode.

The axiom: **attribution binds to the FILE, addressing binds to sub-file
STRUCTURE, editing binds to neither — it binds to what the MEDIUM is.** The
three were fused because the block was believed constitutionally required at
all three; the substrate says otherwise (see the SUBSTRATE FACTS block below,
which this gate re-verifies on every run — they are the ADR's whole premise,
and if one ever stops being true the carve needs re-deriving).

So the grain splits by mode:
  paged (deck/page/canvas) — the block is an ENCLOSURE. One block editable at
    a time; the runtime owns the caret; Enter splits, Backspace merges, an
    empty block closes itself (ADR-477 §1a). UNTOUCHED by this ADR.
  flow (document/article) — the block is an ANNOTATION. contenteditable sits
    on the flow root, so the BROWSER supplies cross-block selection, Cmd-A,
    multi-paragraph copy and native undo instead of a simulation of them.

The LOGIC of normalize-on-write (D3) is validated EXECUTING against a real
DOM (jsdom + esbuild): 28/28, covering native-split id duplication, minting,
citation-island immunity, cross-region collision, sanitization, and the
<article> root. It was FALSIFIED twice (breaking rule 2 → 6 failures;
breaking rule 5 → 1 failure) to prove the assertions bite. This committed
gate is the STATIC regression guard on the source's shape — it cannot import
TypeScript, so it checks the markers that, if regressed, break that logic.
"""

import re
import sys
from pathlib import Path

_results: list[tuple[str, bool]] = []


def _check(label: str, cond: bool) -> None:
    _results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")


def _fn(src: str, name: str) -> str:
    """The body of `export function <name>(` up to the next top-level close."""
    i = src.find(f"export function {name}(")
    return src[i : src.find("\n}", i)] if i >= 0 else ""


def run() -> bool:
    root = Path(__file__).resolve().parent.parent
    web = root / "web"
    ops = (web / "components/studio/artifactOps.ts").read_text()
    proj = (web / "components/workspace/viewers/projection.ts").read_text()
    canvas = (web / "components/studio/StudioCanvas.tsx").read_text()
    surface = (web / "components/studio/StudioSurface.tsx").read_text()
    substrate = (root / "api/services/authored_substrate.py").read_text()
    studio_py = (root / "api/services/studio.py").read_text()

    # ── SUBSTRATE FACTS — the ADR's premise, re-verified every run ─────────
    # If any of these four ever fails, blocks have become load-bearing in the
    # substrate and ADR-480's carve must be re-derived rather than patched.
    _check(
        "F1 write_revision binds to a PATH, not a block (no block param)",
        "def write_revision(" in substrate
        and "path: str" in substrate
        and "block" not in substrate.split("def write_revision(")[1].split(")")[0],
    )
    _check(
        "F2 the moat's write door has never heard of data-block",
        "data-block" not in substrate,
    )
    # F3 is the load-bearing one: blocks live entirely in the APP layer (the
    # Studio registry/routes + the IMAGES app, which shares the block grammar
    # per ADR-472). NOT in the substrate, the primitives, the permission gate,
    # the MCP face, or the revision layer. The assertion is a CONTAINMENT
    # boundary, not a file count — a new Studio/IMAGES module may legitimately
    # speak blocks; `authored_substrate.py` or `primitives/` doing so would
    # mean the premise has changed.
    APP_LAYER = ("services/studio.py", "routes/studio.py", "services/images/")
    leaks = sorted(
        str(p.relative_to(root / "api"))
        for p in (root / "api").rglob("*.py")
        if not p.name.startswith(("test_", "probe_"))
        and "data-block" in p.read_text()
        and not str(p.relative_to(root / "api")).startswith(APP_LAYER)
    )
    _check(
        f"F3 data-block is contained in the APP layer, never the substrate "
        f"(leaks: {leaks or 'none'})",
        not leaks,
    )
    _check(
        "F4 the ADR-448 reference edge lifts from data-ref, never data-block",
        '_DATA_REF_RX = re.compile(r\'data-ref="([^"]+)"\')' in substrate,
    )

    # ── D1 — the flow editing root ────────────────────────────────────────
    _check(
        "D1 the runtime reads its MODE from the stamped attribute (never a slug)",
        "data-yarnnn-mode" in proj and "FLOW_MODE" in proj,
    )
    _check(
        "D1 the runtime never learns a layout slug (ADR-222)",
        not re.search(r"FLOW_MODE\s*=.*['\"](document|article)['\"]", proj),
    )
    _check(
        "D1 the flow root is resolved by SHAPE (main/article), entered once",
        "FLOW_ROOT_SEL = 'main, article'" in proj and "function enterFlow(" in proj,
    )
    _check(
        "D1 the mode is stamped at PROJECTION time, gated on pointer",
        "opts?.pointer && opts?.mode" in proj
        and "setAttribute('data-yarnnn-mode'" in proj,
    )
    _check(
        "D1 mode is a projection INPUT (re-projects when the registry lands)",
        "[content, artifactPath, mode]" in canvas,
    )
    _check(
        "D1 the canvas passes mode into the projection",
        "pointer: true, edit: true, mode }" in canvas,
    )
    # The safety property that makes the default honest: a deck must never be
    # served the flow runtime while the vocabulary is still loading.
    _check(
        "D1 the surface passes the RESOLVED mode only (no 'flow' default leak)",
        "const resolvedMode: 'flow' | 'paged' | undefined =" in surface
        and "mode={resolvedMode}" in surface,
    )

    # ── D2/D3 — blocks stay as annotations; ids are reconstructed ──────────
    norm = _fn(ops, "normalizeBlockIds")
    _check("D3 normalizeBlockIds exists", bool(norm))
    _check(
        "D3 rule 5 — a citation island is never re-minted (checked FIRST)",
        "el.hasAttribute('data-ref')" in norm
        and norm.find("data-ref") < norm.find("freshBlockId"),
    )
    _check(
        "D3 rules 2/3/4 — absent OR already-claimed ids are re-minted",
        "if (!id || seen.has(id))" in norm,
    )
    _check(
        "D3 collision domain includes blocks OUTSIDE the region",
        "!region.contains(el)" in norm,
    )
    _check(
        "D3 document order is what makes 'the FIRST keeps it' true",
        "querySelectorAll('[data-block]')" in norm,
    )
    flow_edit = _fn(ops, "editFlowRegion")
    _check("D1 editFlowRegion exists", bool(flow_edit))
    _check(
        "D1 a byte-identical region lands NO revision",
        "region.innerHTML === sanitized" in flow_edit and "return null" in flow_edit,
    )
    _check(
        "ADR-446 preserved — the flow write still SANITIZES",
        "sanitizeInner(doc, newInner)" in flow_edit,
    )
    _check(
        "D3 the normalize pass runs on every flow write",
        "normalizeBlockIds(doc, region)" in flow_edit,
    )

    # ── D4 — the retired simulation is gated OFF on flow, ALIVE on paged ───
    for label, marker in (
        ("Enter/split", "ADR-480 D4 — the browser splits on flow"),
        ("Backspace/merge", "ADR-480 D4 — the browser merges (and empties) on flow"),
        ("arrow traversal", "ADR-480 D4 — the caret already traverses natively on flow"),
    ):
        _check(f"D4 {label} returns early on flow", marker in proj)
    # The paged grammar must SURVIVE — this ADR scopes it, never deletes it.
    for label, marker in (
        ("split op", "export function splitBlock("),
        ("merge op", "export function mergeBlock("),
    ):
        _check(f"D4 the {label} still exists (paged keeps it)", marker in ops)
    _check(
        "D4 ADR-477's empty-block rule survives for paged",
        "EMPTY block → REMOVE it" in proj,
    )
    _check(
        "ADR-466 preserved — the paged object grammar is untouched",
        "yarnnn-selbox" in proj and "yarnnn-geometry" in proj,
    )

    # ── The one write door (falsifier 2) ───────────────────────────────────
    _check(
        "falsifier 2 — the flow edit lands through the SAME door, no reload",
        "editFlowRegion(liveHtml, selector, newInner)?.html ?? null" in surface
        and "'Studio: edit document'" in surface,
    )
    # Falsifier 1/2: every flow gesture is ONE attributed revision through the
    # existing door. The flow path must reach writeAndAdvance and must NOT
    # introduce a fetch/POST of its own.
    flow_handler = surface[surface.find("const onFlowEdit = useCallback(") :][:900]
    _check(
        "falsifier 2 — the flow handler adds no second write path",
        "writeAndAdvance" in flow_handler
        and "fetch(" not in flow_handler
        and "apiPost" not in flow_handler,
    )

    # ── The registry still declares both modes (the seam this rides on) ────
    _check(
        "the mode seam is kernel-declared",
        'STUDIO_LAYOUT_MODES = ("flow", "paged")' in studio_py,
    )

    print()
    ok = sum(1 for _, c in _results if c)
    print(f"{ok}/{len(_results)} checks passed")
    return ok == len(_results)


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
