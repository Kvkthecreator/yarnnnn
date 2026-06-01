# Fix 1 design — Two-Channel Audit Verdict (A + C)

**Date**: 2026-06-01
**Hat**: A (system fix design — lands in `api/agents/reviewer_agent.py` + the alpha-author bundle spec + an ADR-303 amendment)
**Status**: DESIGN ONLY — nothing landed. Brought to operator for sign-off before implementation.
**Addresses**: `findings-silent-exit-reproduction.md` (the structural channel-shape-mismatch silent-exit).

> **Operator decision (2026-06-01)**: fix shape = **A + C (two-channel + in-loop guard)**.

---

## The cause, restated in one line

The pre-ship-audit spec directs a **long, structured, multi-rule verdict document** to `judgment_log.md` (`pre-ship-check.md` lines 32–33, 65). But the prompt/loop routes every verdict through `ReturnVerdict.reasoning`, documented as **"2-5 sentences"** (`reviewer_agent.py:267`), and `write_reviewer_message` assumes **"Short (typically 2–5 sentences)"** (`reviewer_chat_surfacing.py:56`). Facing a long audit, the model writes the full document as a **text block** (the only shape that fits), and the loop's `if not tool_uses` (`:1216`) reads that text-only round as a terminal silent-exit, synthesizing a `stand_down` that **contradicts the real verdict** and discarding the document.

**Key reconciliation**: Option A is NOT a new architecture. The spec *already* says "write the audit verdict to judgment_log.md within the same wake." The fix makes the **prompt + tool surface honor what the spec already declares** — it closes a prompt-vs-spec drift, it doesn't invent a channel.

---

## A — Two-channel verdict (the cause-fix)

**Principle**: separate the *ledger record* (long, structured, append-only) from the *verdict signal* (short, the loop-closing tool call).

- **Long audit document → `judgment_log.md` via `WriteFile`** (append mode). This is the verdict-of-record. It carries the full `## Pre-Ship Audit / ### Rule 1.../### Rule 2...` structure the spec demands and the model already wants to write. `judgment_log.md` is Reviewer-writable (NOT in `DEFAULT_REVIEWER_WRITE_LOCKS`) and is canonically "append-only judgment lineage" (`workspace_paths.py:29`, ADR-281 §5). No schema change.
- **Short verdict signal → `ReturnVerdict`** carries `verdict` (approve/defer/reject) + a 1-sentence headline + a pointer (`judgment_log` was written this wake). `ReturnVerdict.reasoning` keeps its 2-5-sentence shape — correct for proposal audits, and now correct for long audits too because the long content lives in the ledger, not the signal.

**Sequence on an audit wake**: `ReadFile`(s) → `WriteFile(judgment_log.md, <full audit>)` → `ReturnVerdict(verdict, headline, confidence)`. Two consequential calls, last is ReturnVerdict.

### Concrete touch-points (A)

1. **`pre-ship-check.md` spec** (bundle): make the two-channel contract explicit in "Output target" — *"Write the full structured audit (rule-by-rule) to `judgment_log.md` via WriteFile (append). Then call ReturnVerdict with the verdict + a one-sentence headline; ReturnVerdict.reasoning is the headline, NOT the full audit — the full audit is the judgment_log document."* (The spec already names judgment_log as the target; this sharpens "long doc = WriteFile, headline = ReturnVerdict.")
2. **Reactive trigger framing** (`reviewer_agent.py::_TRIGGER_FRAMING["reactive"]`): add a sub-bullet for audit-shaped recurrence prompts — *"For a pre-ship / corpus-coherence audit: WriteFile the full rule-by-rule audit to judgment_log.md, THEN ReturnVerdict the headline. Do not put the full audit in ReturnVerdict.reasoning — it is sized for a headline."*
3. **`RETURN_VERDICT_TOOL.reasoning` description** (`reviewer_agent.py:264`): clarify it is the **headline / verdict summary**, and that long structured audits belong in a `WriteFile(judgment_log.md)` written before ReturnVerdict. (Keeps "2-5 sentences" — now with the explicit "the long content goes to judgment_log" escape valve so the model stops trying to cram it here.)

**No change** to `ReviewerOutput.reasoning`, `write_reviewer_message`, or the Feed bubble rendering — `reasoning` stays short, the Feed bubble stays a headline, and the operator clicks through to judgment_log for the full audit (which is the right surface for a long structured document anyway).

---

## C — In-loop guard (the backstop, closes the contradicting-stand_down harm)

A's two-call sequence introduces a **second silent-exit surface**: the model could `WriteFile(judgment_log)` then emit the headline as *text* instead of `ReturnVerdict` → `if not tool_uses` fires → synthesizes a contradicting `stand_down`. C covers this (and the pre-A failure mode) by **recovering the verdict-shaped text instead of fabricating a contradicting stand_down.**

### The guard (at `reviewer_agent.py:1216`, the `if not tool_uses:` branch)

Today this branch unconditionally synthesizes `verdict="stand_down"` from the text. The harm is that the text is often a *real verdict* (approve/defer/reject), and `stand_down` contradicts it. The guard:

1. **Detect verdict-shaped text**: if the text-only response contains a recognizable verdict signal (heuristic — matches `approve|reject|defer` as a leading/structural token, or `## Pre-Ship Audit` / `### Rule` structure), it is NOT a stand-down; it is a verdict the model failed to wrap.
2. **One-shot recovery nudge** (preferred over immediate synthesis): inject a system-style text block — *"You produced a verdict as prose. Close the turn by calling ReturnVerdict(verdict=…, reasoning='[one-sentence headline]'). If the full audit isn't yet in judgment_log.md, WriteFile it first."* — and **continue one more round** (do not break). This preserves model autonomy (ADR-303's stated reason for deferring in-loop intervention) and gives the model the chance to land the verdict correctly.
3. **Fallback only if it text-exits AGAIN**: if the *next* round is also text-only, THEN fall through to the existing dispatcher silent-exit write — but with `exit_class="verdict_in_prose_unrecovered"` (a new, honest class distinct from `text_only_mid_loop`) and the synthesized verdict derived from the detected signal (e.g. if the prose clearly says "reject", synthesize `reject` not `stand_down`), so the dispatcher record stops fabricating a contradicting verdict.

**Why nudge-then-retry, not force-tool**: force-`tool_choice=any` would also strip the model's ability to emit a legitimate final-narration text block on non-audit wakes (addressed turns rely on that). The one-shot nudge is scoped to the failure (text-only when a verdict was expected) and self-limits (one retry, then honest fallback).

### Concrete touch-points (C)

- `reviewer_agent.py:1216` `if not tool_uses:` branch — replace unconditional `stand_down` synthesis with: detect-verdict-shape → nudge-and-continue (once) → on repeat, honest fallback with derived verdict + new exit_class.
- A small `_looks_like_verdict(text) -> Optional[str]` helper (returns the detected verdict token or None).
- `_dispatcher_write_silent_exit_standing_intent` — accept the new `exit_class="verdict_in_prose_unrecovered"` and the derived verdict.

---

## What this does NOT touch (scope discipline)

- **No `ReturnVerdict.reasoning` widening** (that was Option B, rejected — keeps the short-verdict semantics correct for proposal audits).
- **No new tool, no new permission mode** — `WriteFile(judgment_log)` is an existing Reviewer primitive.
- **No schema change, no migration.**
- **No persona-frame (ADR-306) change** — the minimal frame's action-grammar ("a tool call IS the action; close with a verdict or standing_intent") is preserved and reinforced (the guard makes "close with a verdict" actually hold on audit wakes).
- **No `DEFAULT_REVIEWER_WRITE_LOCKS` change.**

---

## Canon updates required (docs-alongside-code)

- **ADR-303 amendment**: add a sixth posture cell **P6 — "Verdict-in-prose (synthesized-correctly, wrong-channel)"**, distinct from P5-Confused. P5 = "genuinely unable to synthesize"; P6 = "synthesized a full correct verdict but emitted it as prose." The moat-audit receipts (8,406 tokens of correct `### Rule 1...`) are the evidence that P5 was conflating two cells. P6's contract: recover the verdict (C), don't fabricate a contradicting stand_down. This is the "future ADR revisits" ADR-303 §Open-Questions named.
- **`api/prompts/CHANGELOG.md`**: entry for the reactive-framing + ReturnVerdict-description + spec changes (prompt-change protocol).
- **Bundle spec** (`pre-ship-check.md`): the two-channel output-target sharpening.

---

## Validation plan (after landing — separate session)

1. **Re-fire the moat pre-ship-audit under `autonomous`** (restore the dial first — it's currently `bounded` from the contaminating pre-flight). Expected: the Reviewer WriteFiles a full rule-by-rule audit to `judgment_log.md` AND ReturnVerdicts a headline. Receipt = a `judgment_log.md` revision with the moat audit + an `execution_events` row with a real verdict.
2. **This re-fire also answers the parent finding's still-open citation question** (`findings.md` §2): a *completing* audit, walking its rules, against a piece with known-fabricated citations (the invented github URLs are in `moat-thesis/profile.md` right now). Whether the audit catches them is the test for the §2 `citation-grounding` rule recommendation — which is downstream of this fix (a citation rule only fires if the audit completes and lands).
3. **Regression**: confirm proposal audits (short verdicts) are unchanged — ReturnVerdict.reasoning still 2-5 sentences, Feed bubble still a headline.

---

## Sequencing note

Fix 1 (this) unblocks the citation-grounding rule (parent `findings.md` §2 recommendation #1). Land Fix 1 → re-fire → if the audit now completes, THEN evaluate whether it catches the fabricated citations → if not, land the citation-grounding rule and re-fire again. The two fixes are dependency-ordered: completion before catch.
