# ADR-323 — Finish the Persona-Frame Collapse: `cockpit_awareness` Against Derived Principle 22

> **Status**: DRAFT (2026-06-07). Proposed by Claude, pending KVK ratification. The behavioral-layer twin of the post-ADR-320 surface re-grounding — completes the collapse ADR-306 scoped too narrowly.
> **Date**: 2026-06-07
> **Authors**: KVK, Claude
> **Upstream**: [reviewer-prompting-posture-coherence assessment](../analysis/reviewer-prompting-posture-coherence-2026-06-07.md) (the measured seam) + the 2026.06.07.2 CHANGELOG fix (the ADR-293-vs-ADR-320 self-contradiction *inside one prompt* that was an instance of exactly this drift class).
> **Dimensional classification**: **Channel** (Axiom 6 — the system prompt is the legible interface the model reads) + **Mechanism** (Axiom 5 — prompts are half of Mechanism's vocabulary, FOUNDATIONS Derived Principle 9).
> **Canon backing**: FOUNDATIONS Derived Principle 22 (the system prompt carries only the model↔runtime interface contract) + Derived Principle 21 (Reviewer formalization) + ADR-281 (the kernel does not author its own pedagogy).

---

## The one-sentence thesis

**ADR-306 collapsed the Reviewer persona-frame from ~36K to ~5.3K toward Derived Principle 22 — but it measured itself against `_PERSONA_FRAME_SECTIONS` only, leaving a separate 11.2K `cockpit_awareness` block (substrate pedagogy + posture + gate-narration, exactly what DP22 forbids) bolted on after the frame and never reconciled.** This ADR finishes the collapse: dissolve `cockpit_awareness`'s DP22-violating content into its canonical substrate homes (`_workspace_guide.md`, `principles.md`, the minimal frame), keeping only the genuine interface (the tool block). The actual composed system prompt drops from ~16.5K toward the ~5–6K DP22 intended.

---

## Context — the collapse was partial

DP22 (FOUNDATIONS.md:716) is precise: the system-authored prompt carries **only** (1) principal-shift (corrects the model's trained assistant prior) + (2) action-grammar (the agent↔runtime interface contract). Everything else lives in substrate + code:
- rules of judgment → `principles.md`
- substrate pedagogy → `_workspace_guide.md` (ADR-281)
- code-enforced gates → no prose at all (the gate holds; the tool result reports it)

ADR-306 implemented this for `_PERSONA_FRAME_SECTIONS` (the `_compute_*` registry in `reviewer_agent.py`), hitting a 90% reduction there. **But the system prompt is assembled as `persona_body + build_cockpit_section()`** (`reviewer_agent.py:543`), and `cockpit_awareness` was a *separate module* (introduced by ADR-258 D5 for drift-resistance) that ADR-306 never scoped. Receipt: `grep -i cockpit docs/adr/ADR-306-*.md` → zero matches.

Measured live (assessment §2.2):

| Component | Chars | DP22 verdict |
|---|---|---|
| `_compute_minimal_frame()` | 5,290 | ✅ compliant |
| `build_cockpit_section()` | **11,215** | ⚠️ the seam |
| ├─ `build_filesystem_block()` | 2,949 | ✗ substrate pedagogy → `_workspace_guide.md` |
| ├─ `build_tools_block()` | 3,444 | ~ defensible (interface) |
| └─ `_OPERATING_POSTURE` | 4,580 | ✗ posture + missing-substrate rules + write-authority + tool-loop |

So the "collapse to ~3.5K" actually lands at **~16.5K**, with `cockpit_awareness` 2× the size of the frame it's appended to.

**The dual-mention is literal** (assessment §3): `_workspace_guide.md` (DP22's designated home, bundle-shipped, read every wake) and `cockpit_awareness` teach the *same topics* — "How you operate across wakes," "Your wake envelope," "When things diverge," "What NOT to write to operator-canon" appear in **both**. The `_workspace_guide.md` version is better-factored (generic, ADR-320-compatible: "the lock policy will reject the write, but the discipline is upstream"); the system-prose version enumerates specifics that drift. This is precisely the failure mode that produced the ADR-293-vs-ADR-320 self-contradiction *within one prompt* (fixed in CHANGELOG 2026.06.07.2) — two homes for one fact, drifted apart.

---

## Why this matters (not cosmetic)

1. **Drift surface (the proven cost).** Every substrate fact in `cockpit_awareness` can disagree with `_workspace_guide.md` or the gate. The 2026.06.07.2 self-contradiction was an instance. DP22 exists to make that class structurally impossible by enforcing one home.
2. **Posture dilution.** DP22's thesis: a *thin* frame produces *sharper* judgment. The ablation evidence is strong — adding one tool (22 vs 21) collapsed Reviewer output 74% (`docs/evaluations/2026-05-25-...adr299-always-surface-resolution/`). If tool-count is corrosive, 11.2K of bolted-on prose plausibly is too. The minimal frame's whole bet is that the model reasons better from substrate-it-reads than prose-it's-told; `cockpit_awareness` re-tells what the envelope already renders.
3. **Cost/cache.** The static system prompt is cache-marked (good), but it's ~16.5K billed at cache-create on the first wake of each TTL window, every workspace, every deploy. The promised 90% reduction is ~67% un-delivered.

---

## Decision (proposed)

Apply DP22's diagnostic test — *"is this correcting the model's prior, or defining the runtime interface? If neither, it belongs in substrate or code"* — to each `cockpit_awareness` part:

### D1 — `build_filesystem_block` is DELETED from the system prompt.
Substrate pedagogy. It already lives in `_workspace_guide.md` (the path-zone declarations + "What this workspace contains"), and the per-wake envelope (`_build_user_message`) already renders each governance/persona/domain file under a *labeled header with full path*. The Reviewer does not need the kernel to re-teach paths the envelope shows and the guide explains. **Verify-before-delete:** confirm every path fact in `build_filesystem_block` has a home in `_workspace_guide.md`; migrate any genuinely-missing fact into the guide (the bundle's home), not back into system prose.

### D2 — `_OPERATING_POSTURE` is SPLIT by the diagnostic, then deleted.
- "How you operate" / "When substrate is missing" / "Write authority" fiduciary posture / "When things diverge" → **rules of judgment + substrate pedagogy** → already in `principles.md` (the fiduciary/stewardship posture per Derived Principle 24) + `_workspace_guide.md` ("When things diverge," "What NOT to write to operator-canon"). DELETE from system prose; migrate any unique fact to its substrate home.
- "Tool-use loop" (ListFiles→ReadFile→…→ReturnVerdict last) → **action-grammar** → merge any genuinely-missing interface detail UP into `_compute_minimal_frame` (most is already there — "close every cycle with a verdict or a standing_intent write"). DELETE the redundant copy.

### D3 — `build_tools_block` is KEPT (the one defensible part), but audited for redundancy with the `tools=` API param.
The tool surface is interface. But the model already receives full tool *schemas* via the Anthropic `tools=` parameter; the prose list partly duplicates them. **Audit:** measure whether the 3.4K prose tool-list earns its tokens over the schema the API already carries. If the prose adds only the "not in your surface" + "Schedule is yours" framing (which IS load-bearing posture-correction), shrink the list to that framing and let the schemas carry the per-tool descriptions. Keep what corrects the model's prior about *which* tools are its job; drop what re-states schema.

### D4 — The drift-resistance mechanism survives where it still applies.
ADR-258 D5's instinct — *generate* the cockpit section from `workspace_paths` constants + the primitive registry so it can't drift — is sound. It just got applied to content DP22 says doesn't belong in the prompt. After D1-D3, the only generated-from-constants survivor is the tool block (D3), which legitimately should track the registry. The filesystem-block generation moves to a different consumer if needed: `_workspace_guide.md` is bundle-authored prose, not generated — but if we want path-drift-resistance there, that's a *separate* mechanism (a bundle-lint that checks guide paths against `workspace_paths`), not system prose. Named, not built here.

### D5 — Net target and the regression gate.
System prompt: ~16.5K → ~5–6K (minimal frame ~5.3K + audited tool block). Gate `api/test_adr323_frame_collapse_finished.py`: (a) `build_filesystem_block` deleted (no caller); (b) `_OPERATING_POSTURE` deleted; (c) the composed system prompt (frame + surviving tool block) is under a char ceiling (~7K, headroom over the 5–6K target); (d) no substrate-pedagogy term ("When substrate is missing," "What NOT to write," path enumerations) appears in the system prompt — they live in `_workspace_guide.md` / `principles.md`; (e) the action-grammar invariants (tool-call-IS-action, anti-confabulation, close-with-verdict) survive in the minimal frame.

---

## What this is NOT

- **NOT touching the minimal frame's content.** `_compute_minimal_frame` is DP22-exemplary; it only *gains* any genuine action-grammar detail migrated up from the tool-loop section (D2). Its principal-shift + index-not-assert (ADR-314) are untouched.
- **NOT touching the envelope.** `_build_user_message`'s per-wake substrate pre-loading (labeled headers, full paths, ADR-275 pattern) is correct and stays.
- **NOT touching trigger framing.** `_TRIGGER_FRAMING[addressed|reactive]` is largely action-grammar (how this wake's loop closes) — DP22-defensible. A light audit for substrate-pedagogy leakage (the recurrence sub-shape catalog) is in scope but the framing stays.
- **NOT a new principle.** This *applies* DP22 to a site ADR-306 missed. No FOUNDATIONS change.
- **NOT moving content into a new home.** Everything deleted already has a canonical home (`_workspace_guide.md` / `principles.md` / the frame). The discipline is *delete the dup*, not *relocate* (the dup's content already exists in the right place — verify, then delete).

---

## Claim tiering

- **FORCED (by DP22 — ratified canon):** substrate pedagogy + rules of judgment + gate-narration do not belong in system prose. D1/D2 are *applying ratified canon* to a site that escaped it, not new direction.
- **DESIGN CHOICE (selected):** D3 (how aggressively to thin the tool block against the API schema); the exact char ceiling in D5.
- **PRESERVED:** the minimal frame, the envelope, trigger framing, the generate-from-constants drift-resistance (re-homed to the tool block).

---

## Scope / blast radius

Small, behavioral, well-gated. Single PR (independent of ADR-321/322 — this is the reviewer prompt, not the file primitives):
1. `cockpit_awareness.py`: delete `build_filesystem_block` + `_OPERATING_POSTURE`; audit + shrink `build_tools_block`; `build_cockpit_section` reduces to the tool block (+ the load-bearing "not in your surface" / "Schedule is yours" framing).
2. `reviewer_agent.py`: `_compute_minimal_frame` gains any migrated action-grammar detail; `_build_system_prompt` composition unchanged in shape (frame + slimmer cockpit).
3. Verify-before-delete: confirm `_workspace_guide.md` + `principles.md` cover every deleted fact; migrate gaps to those homes (bundle/operator substrate), NOT back to prose.
4. `api/prompts/CHANGELOG.md` (this is a prompt change — protocol).
5. Canon: amend ADR-258 (D5 cockpit-awareness — the *generation* mechanism survives for the tool block; substrate/posture content dissolves) + note in ADR-306 that the collapse is *completed* here.
6. Regression gate (D5).

**Behavioral-validation note:** because DP22's thesis is *thinner frame → sharper judgment*, this change should be **canary-validated** the way ADR-299/ADR-306 were — run N≥3 Reviewer wakes against the slimmed prompt and compare verdict quality (output substance, action-taking, no regression to stand-down-with-no-writes) vs the current ~16.5K prompt. The hypothesis is *improvement or neutral*; confirm it's not a regression before merge. (Hat-B evaluation; the fix lands in Hat-A.)

---

## Relationship to other ADRs

- **Completes** ADR-306 (the persona-frame collapse — extends it to the `cockpit_awareness` module DP22 didn't originally scope).
- **Amends** ADR-258 (D5 cockpit-awareness — generation mechanism survives for the tool block; substrate/posture content dissolves into substrate homes).
- **Applies** Derived Principle 22 (the governing canon) + Derived Principle 21 (the seat's framing) + ADR-281 (kernel does not author its own pedagogy — the filesystem-block deletion is the behavioral-layer instance).
- **Preserves** the minimal frame (ADR-306/ADR-314), the envelope pre-loading (ADR-275/ADR-276), trigger framing, model+round-budget-by-trigger (ADR-260/263).
- **Twins** the primitive-surface re-grounding (ADR-321/322): same root cause (a strong simplifying commitment implemented at the primary site, an adjacent site left carrying the old shape), same fix shape (*finish the collapse the architecture already decided*).

---

## Open questions (deferred to ratification)

1. **Trigger-framing leakage** — `_TRIGGER_FRAMING` carries a recurrence sub-shape catalog (reflection / substrate-refresh / compose / conditions-check / pre-ship-audit) that is partly substrate-pedagogy. Audit whether it belongs in `_workspace_guide.md`'s wake-context taxonomy instead. Light scope; deferred to avoid over-reaching this PR.
2. **Tool-block vs API-schema redundancy (D3)** — exact aggressiveness. Measure first.
3. **Drift-resistance for `_workspace_guide.md` paths (D4)** — if we want the bundle guide's paths checked against `workspace_paths`, that's a bundle-lint, a separate small ADR. Named, not built.
