#!/usr/bin/env python3
"""Gate: ADR-521 — the flow benchmark: Notion's scope, the continuous surface's mechanics.

Three grammars were live on one surface: continuous-surface selection (ADR-480's
root contenteditable), block-era formatting (the ADR-456 W2 format bar, built
eight days before the grain flipped — a bare execCommand toggle that silently
un-bolded headings, and a surroundContents wrap that mangled cross-block
ranges), and legacy enclosure chrome. ADR-521 commits the two-axis benchmark
(scope = Notion-class; mechanics = continuous-surface class) and one law: the
text tier follows the SELECTION wherever it runs; the structure tier addresses
the BLOCKS it intersects.

Static-source gate over the EDIT_SCRIPT runtime + the canon files. Per-site
assertions, never bare counts (the counting-gate lesson). What a grep cannot
see — the caret, the rendered bar, actual paste flavors — the click-pass owns.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
DOCS = ROOT / "docs"

_pass = 0
_fail = 0


def _check(label: str, cond: bool) -> None:
    global _pass, _fail
    print(("[PASS] " if cond else "[FAIL] ") + label)
    if cond:
        _pass += 1
    else:
        _fail += 1


src = (WEB / "components/workspace/viewers/projection.ts").read_text()

# ── The EDIT_SCRIPT region (extraction must succeed or every claim below is void) ──
m = re.search(r"const EDIT_SCRIPT = `\n(.*?)\n`;", src, re.DOTALL)
_check("EDIT_SCRIPT extracted", bool(m))
if not m:
    print("FAILED: cannot extract EDIT_SCRIPT — every assertion below is void")
    sys.exit(1)
edit = m.group(1)

# ── D3: the destructive block-era mechanism is DELETED ──────────────────────
_check("D3: wrapSelection is deleted (the cross-block mangle path)",
       "wrapSelection" not in src)
_check("D3: no bare execCommand('bold') toggle outside the intent machinery",
       "document.execCommand('bold')" not in edit)

# ── D3: the segmentation + deterministic-toggle machinery exists ────────────
_check("D3: formatSegments exists and clamps with compareBoundaryPoints",
       "function formatSegments()" in edit
       and "compareBoundaryPoints(Range.START_TO_START, r)" in edit
       and "compareBoundaryPoints(Range.END_TO_END, r)" in edit)
_check("D3: segments are per-block ([data-block] intersection, top-level only)",
       "querySelectorAll('[data-block]')" in edit
       and "closest('[data-block]')" in edit)
_check("D3: citation islands are never format subjects",
       "closest('[data-ref]')" in edit)
_check("D3: two-pass deterministic toggle (intent read, then enforced)",
       "function applyToggle(cmd)" in edit
       and "if (!document.queryCommandState(cmd)) { intent = true; break; }" in edit
       and "if (document.queryCommandState(cmd) !== intent) document.execCommand(cmd);" in edit)
_check("D3: heading blocks are exempt from bold (the un-bold trap guard)",
       "function isHeadingBlock(el)" in edit
       and "cmd === 'bold' && isHeadingBlock(" in edit)
_check("D3: applyFmt routes through the new ops",
       "if (op === 'bold') applyToggle('bold');" in edit
       and "else if (op === 'code') applyCode();" in edit)
_check("D3: code wrap is per-segment (the fallback comment names the boundary)",
       "function applyCode()" in edit
       and "never crosses a" in edit)

# ── D4: keyboard entrances ──────────────────────────────────────────────────
_check("D4: cmd-B/I intercept a real selection and route to applyFmt",
       "e.key === 'b' || e.key === 'B'" in edit
       and "applyFmt(op);" in edit)
_check("D4: a collapsed caret stays browser-native (no custom caret-state pipeline)",
       "sel.isCollapsed) return; // caret: browser-native" in edit)
_check("D4: Tab in a list indents, shift-Tab outdents",
       "closest('li')" in edit
       and "document.execCommand(e.shiftKey ? 'outdent' : 'indent');" in edit)
_check("D4: the ADR-480 written refusal is withdrawn from the runtime",
       "Deliberately NOT a list-indent gesture" not in src)
_check("D4: Tab still never ends the writing session (preventDefault before branching)",
       "if (e.key !== 'Tab') return;" in edit)

# ── D5: text/html paste behind the allowlist, one handler for both grains ───
_check("D5: richPaste reads text/html with a plain-text fallback",
       "function richPaste(e)" in edit
       and "getData('text/html')" in edit
       and "getData('text/plain')" in edit)
_check("D5: the flow root and the paged block share ONE paste handler",
       "root.addEventListener('paste', richPaste);" in edit
       and "var onPaste = richPaste;" in edit)
_check("D5: the plain-text-only handlers are deleted",
       "Paste stays plain-text" not in src
       and "Sanitize paste to plain text" not in src)
_check("D5: the allowlist exists and media is dropped (IMG/VIDEO/AUDIO in DROP)",
       "var PASTE_ALLOW = {" in edit
       and "var PASTE_DROP = {" in edit
       and "IMG: 1" in edit and "VIDEO: 1" in edit and "SCRIPT: 1" in edit)
_check("D5: javascript: hrefs are rejected; every other attribute is stripped",
       "indexOf('javascript:') === 0" in edit
       and "el.removeAttribute(name);" in edit)
_check("D5: unknown wrappers unwrap (children survive, the wrapper dies)",
       "parent.insertBefore(el.firstChild, el);" in edit)

# ── The template-literal discipline (a backtick or ${ in added code kills the script) ──
# Re-cut by ADR-539 D4: the paste clamp added two interpolations (the
# out-of-rung tags + the clamp target), both module-declared like TEXT_KINDS.
# The invariant is unchanged — EVERY `${` in the runtime is a DECLARED module
# constant, never an inline expression — and the set is enumerated so a stray
# interpolation still fails. (The count==1 spelling went red the moment
# ADR-539 landed, which is this re-cut's receipt, not its motive.)
_EDIT_INTERPOLATIONS = {"${TEXT_KINDS_JS}", "${OUT_OF_RUNG_TAGS_JS}", "${DEEPEST_RUNG_TAG_JS}"}
_check("runtime hygiene: EDIT_SCRIPT's interpolations are exactly the declared constants",
       edit.count("${") == len(_EDIT_INTERPOLATIONS)
       and all(tok in edit for tok in _EDIT_INTERPOLATIONS))

# The OTHER half of the same discipline, learned the hard way 2026-08-05: a
# literal backtick inside a runtime's body closes the template early. The D6
# comment used `inBlk`/`cur` as prose quoting and webpack failed the whole
# build. `${` was already pinned; the backtick was not, on EITHER runtime.
_pm = re.search(r"const POINTER_SCRIPT = `\n(.*?)\n`;", src, re.DOTALL)
_check("runtime hygiene: POINTER_SCRIPT extracted", bool(_pm))
_check("runtime hygiene: no literal backtick inside either runtime body "
       "(it would close the template and break the build)",
       "`" not in edit and bool(_pm) and "`" not in _pm.group(1))

# ── D6: the block VERB tier is an OBJECT tier on flow (the deferred audit) ──
#
# ADR-521 §7 deferred the pointer-runtime residue because that region was under
# concurrent ADR-520 edit. Executed 2026-08-05. The finding: the verb keys
# (⌫ delete · ⌘C/⌘V/⌘D) were written for the enclosure grain and asked only
# "is a block selected and does the caret claim it" — never whether the subject
# is prose or an object. Because the flow click handler sets `cur` on EVERY
# block (withholding only the cue, ADR-484), a paragraph was a live verb
# subject, and two windows made Backspace delete a whole paragraph: an EMPTIED
# one (caretOwnsKeyIn requires non-empty text) and a CROSS-BLOCK RANGE (the
# range's startContainer sits in the first block, so `inBlk` is false for cur).
#
# Bounded to the construct — the verb handler's own source slice, brace-free
# but delimited by its two named neighbours, never a fixed character window.
_vi = src.index("function caretOwnsKeyIn")
_vj = src.index("// ── The empty-slot affordance")
verbs = src[_vi:_vj]

# Read the REAL declaration rather than restating it — a hardcoded copy here
# would keep passing after someone adds an object kind to the text set.
#
# ADR-525 D1 re-pointed this: the list is now the exported `TEXT_BLOCK_KINDS`
# (the FE's tier fallback reads the same array the runtime injects, so the two
# cannot drift), and TEXT_KINDS_JS derives from it. The assertion's INTENT is
# unchanged — source the partition, never restate it — so it follows the name.
_tk = re.search(r"export const TEXT_BLOCK_KINDS = (\[[^\]]*\])", src)
_check("D6: the TEXT_KINDS declaration is readable (the kind partition is sourced)",
       bool(_tk))
TEXT_KINDS_DECL = _tk.group(1) if _tk else ""
# The injected list must still DERIVE from that one declaration — if someone
# re-inlines a literal here, the export and the runtime can disagree silently.
_check("D6: the runtime's injected list derives from the one declaration",
       "const TEXT_KINDS_JS = JSON.stringify(TEXT_BLOCK_KINDS)" in src)

_check("D6: the flow verb-subject gate exists and asks the KIND, not the caret",
       "function verbSubjectAllowed(blk)" in verbs
       and "TEXT_KINDS.indexOf(blk.getAttribute('data-block')) === -1" in verbs)
# The ASSIGNMENT/call, not the identifier — a gate nobody calls is not a gate.
_check("D6: selectedBlock() consults it BEFORE handing any verb a subject",
       "if (!verbSubjectAllowed(sel)) return null;" in verbs
       and verbs.index("if (!verbSubjectAllowed(sel)) return null;")
           < verbs.index("return caretOwnsKeyIn(sel) ? null : sel;"))
_check("D6: paged keeps the unit verb (the gate is flow-scoped, not global)",
       "if (!flow) return true;" in verbs)
_check("D6: the verb tier still reaches OBJECT kinds on flow "
       "(TEXT_KINDS excludes figure/table/chart/gallery/divider)",
       all(k not in TEXT_KINDS_DECL for k in ("figure", "table", "chart", "gallery", "divider")))

# ── Canon: the ADR + AUTHORING.md carry the ruling ──────────────────────────
adr = DOCS / "adr" / "ADR-521-the-flow-benchmark-notions-scope-the-continuous-surfaces-mechanics.md"
_check("ADR-521 exists", adr.exists())
# Renamed from STUDIO.md 2026-08-06 — the file was named for one of its two
# consumers while being the contract for both. STUDIO.md is now a stub.
studio = (DOCS / "design" / "AUTHORING.md").read_text()
_check("AUTHORING.md: normative rule 10 (the two-axis benchmark) is present",
       "The flow benchmark is two-axis" in studio)
_check("AUTHORING.md: the Inline format matrix row exists",
       "### Inline format (the text tier follows the selection — ADR-521)" in studio)
_check("AUTHORING.md: cmd-B/I and text/html paste left the owed lists",
       "⌘B/⌘I on flow ·" not in studio
       and "`text/html` paste (a security carve" not in studio)
_check("AUTHORING.md: the block-set selection refusal is standing",
       "no block-set selection mode on flow" in studio)

print()
print(f"{_pass} passed, {_fail} failed")
sys.exit(1 if _fail else 0)
