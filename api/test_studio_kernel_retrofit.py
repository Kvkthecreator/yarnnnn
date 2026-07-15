#!/usr/bin/env python3
"""Gate: the kernel style element retrofits on EVERY member write.

ADR-453 D2 promises the marked kernel element "retrofits into existing artifacts
on first touch" — that is what lets a new block kind, arrangement, or token light
up in an artifact authored before it existed.

The promise was only half-kept: 5 of 21 ops in artifactOps threaded
`kernelStyleElement` through and called ensureKernelStyle; the other 16 (insert a
block, type in one, split, merge, move, delete, duplicate, apply a skin…) did
not. So an artifact upgraded only if you happened to touch it through an
arrangement/token/background op, and could otherwise sit at an old version
indefinitely. Live receipt (kvkthecreator, 2026-07-15): kernel was v4 while
prd-for-yarnnn/document.html sat at v3 and three decks carried NO kernel element
at all.

That is benign only while kernel CSS stays strictly ADDITIVE (an old artifact
lacks only rules it never invokes — verified: v3→v4 added 15 selectors, dropped
0). It becomes a real defect the first time a version CHANGES or REMOVES a rule
an old artifact depends on, and the failure is SILENT: a token renders wrong and
nothing errors.

The fix moves the retrofit to the ONE member write door (Singular Implementation:
one retrofit site, not 21 chances to forget), so every mechanical write upgrades.

Static/structural checks (no DB, no LLM — this repo has no FE test runner):
  1. retrofitKernel exists, is exported, and actually CALLS ensureKernelStyle
     between its before/after probes. (A regex sweep once stripped that call,
     leaving before==after always true — a retrofit that silently did nothing.
     This check exists to catch exactly that.)
  2. It is byte-identical when already current (never manufactures a revision).
  3. The write door applies it, reading the kernel through a REF (the write queue
     is async — a render closure could hand it a stale/unloaded vocabulary).
  4. Singular Implementation: ensureKernelStyle has exactly ONE caller; no op
     still carries a vestigial kernelStyleElement parameter.
"""

import re
import sys
from pathlib import Path

_results: list[tuple[str, bool]] = []


def _check(label: str, cond: bool) -> None:
    _results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")


def run() -> bool:
    web = Path(__file__).resolve().parent.parent / "web"
    ops = (web / "components/studio/artifactOps.ts").read_text()
    surface = (web / "components/studio/StudioSurface.tsx").read_text()

    # ── 1. the op exists and is wired to the real upsert ────────────────────
    _check(
        "retrofitKernel is exported",
        "export function retrofitKernel(html: string, kernelStyleElement: string | undefined): string" in ops,
    )
    # THE REGRESSION GUARD: a before/after probe with no ensureKernelStyle call
    # between them makes before==after always true -> a silent no-op retrofit.
    body = ops.split("export function retrofitKernel", 1)[-1].split("\n}", 1)[0]
    _check(
        "retrofitKernel CALLS ensureKernelStyle between its before/after probes",
        bool(
            re.search(
                r"const before = .*?\n\s*ensureKernelStyle\(doc, kernelStyleElement\);\n\s*const after = ",
                body,
                re.S,
            )
        ),
    )
    _check(
        "retrofitKernel is byte-identical when already current (no spurious revision)",
        "if (before === after) return html;" in body,
    )
    _check(
        "retrofitKernel no-ops without a kernel element / without a <head>",
        "if (!kernelStyleElement) return html;" in body and "if (!head) return html;" in body,
    )

    # ── 2. the write door applies it ────────────────────────────────────────
    _check(
        "the member write door retrofits every write",
        "const html = retrofitKernel(computed, kernelStyleRef.current);" in surface,
    )
    _check(
        "the door reads the kernel through a REF (the write queue is async)",
        "const kernelStyleRef = useRef<string | undefined>(undefined);" in surface
        and "kernelStyleRef.current = kernelStyle;" in surface,
    )

    # ── 3. Singular Implementation ──────────────────────────────────────────
    _check(
        "ensureKernelStyle has exactly ONE caller (the door), not 21 chances to forget",
        len(re.findall(r"^\s*ensureKernelStyle\(doc, kernelStyleElement\);", ops, re.M)) == 1,
    )
    _check(
        "no op carries a vestigial kernelStyleElement parameter",
        not re.search(r"^\s*kernelStyleElement\?: string,", ops, re.M),
    )
    _check(
        "no caller still passes kernelStyle into an op",
        not re.search(r"\w+\(html,[^)]*,\s*kernelStyle\)", surface),
    )

    # ── 4. the kernel may not depend on skin state it cannot retrofit ───────
    # The docstring above says the retrofit is "benign only while kernel CSS
    # stays strictly ADDITIVE". This is the check for the first violation
    # (found 2026-07-15): the kernel carved out `[data-arrange]:not(.slide)
    # .cols` on the reasoning that "decks keep their own .slide .cols rules" —
    # true of the deck skin as of ADR-444, false of every deck created BEFORE
    # it, because the LAYOUT SKIN is baked once at build_skeleton and is never
    # versioned or retrofitted. Those decks matched neither rule and stacked
    # their columns silently. Live receipt: yarrnnnn-decl (kvk, 2026-07-15).
    #
    # The invariant: a kernel rule may not be predicated on the presence of a
    # skin rule. The skin is frozen at creation; the kernel is not.
    from services.studio import STUDIO_KERNEL_CSS_VERSION, compose_kernel_style_element

    kernel_css = compose_kernel_style_element()
    _check(
        "the kernel owns .cols for EVERY layout (no :not(.slide) placement carve-out)",
        "[data-arrange] .cols { display: flex" in kernel_css
        and "[data-arrange]:not(.slide) .cols { display: flex" not in kernel_css,
    )
    # The ONE legitimate :not(.slide) — a difference in KIND, not an assumption
    # about CSS that may not be there. A slide is a fixed 16:9 stage with no
    # responsive obligation; a page has one.
    _check(
        "the responsive-stacking exemption SURVIVES (a slide is a fixed stage)",
        "[data-arrange]:not(.slide) .cols { flex-direction: column; }" in kernel_css,
    )
    _check(
        "the kernel CSS version was bumped past v4 (the retrofit must REACH the stranded decks)",
        STUDIO_KERNEL_CSS_VERSION >= 5,
    )

    ok = all(c for _, c in _results)
    print()
    print(f"{'PASS' if ok else 'FAIL'}: {sum(c for _, c in _results)}/{len(_results)} checks")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
