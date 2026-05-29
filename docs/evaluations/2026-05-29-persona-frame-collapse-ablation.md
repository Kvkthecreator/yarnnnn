# Ablation audit — persona-frame collapse toward the Claude-Code shape

**Date**: 2026-05-29
**Hat**: B (developer-surface investigation; recommends + designs the Hat-A collapse, which lands in system canon)
**Status**: Proposed design. The collapse it specifies is being executed this session per operator decision ("push fully toward this direction, re-validate in full, revert if the thesis doesn't hold").

> Companion to the framing-gap finding (`2026-05-29-reviewer-action-grammar-framing-gap.md`, commit e5e8453) and the composed-coherence canon it produced (`agent-composition.md` §3.2.2, commit cc8e0ab). That finding fixed a *contradiction* inside the persona-frame. This audit asks the next question: **does the persona-frame need to be this big at all?**

---

## §1 The thesis (operator-aligned, locked)

The system-authored prompt layer (`reviewer_agent.py` persona-frame, ~36K chars, 13 `_compute_*` sections) collapses to the **Claude-Code shape**: thin, stable, carrying only the model↔runtime interface contract. The substance the frame currently narrates is **already carried by substrate + code**:

- The **wake envelope** (`_build_user_message`) already renders every governance file with a labeled header (IDENTITY "Your persona", principles "Your framework", MANDATE "primary intent", AUTONOMY "Delegation ceiling", PRECEDENT "overrides principles", preferences, `## Wake context`, `## Operating Context`). The frame re-explaining what these files *mean* duplicates headers the envelope already writes.
- The **gating code** (`review_policy.should_auto_apply`, `DEFAULT_REVIEWER_WRITE_LOCKS`, `_is_path_locked_for_reviewer`) already enforces autonomy + write-authority. The frame narrating these is describing gates that hold without the prose.
- The **runtime shape** (wake-fired, no chat affordance on reactive wakes, `ReturnVerdict` as sole exit) already enforces non-conversational behavior structurally.

**The three fundamental Claude-Code/YARNNN differences are real and axiom-worthy** — but each is carried by substrate + code, not by system prose:

| Fundamental | Carried by (substrate/code) | NOT by |
|---|---|---|
| **Δ1 on-behalf-of** (installed judgment, not a driven tool) | MANDATE.md + standing_intent.md (substrate) | persona-frame narration |
| **Δ2 identity-infusion** (a *someone*, qualitative + mechanical) | IDENTITY.md + _autonomy.yaml + _pace.yaml (substrate) | persona-frame narration |
| **Δ3 self-referential governance** (agent's own CLAUDE.md is in its repo + it can amend) | substrate-location + write-locks (code) + revision attribution (ADR-209) | persona-frame narration |

This is **ADR-281's own principle ("the kernel does not author its own pedagogy") applied at the behavioral layer.** ADR-281 ruled that substrate *organization* is bundle-shipped operator-canon, not Python-string-injected. The persona-frame violates the same principle for substrate *semantics + behavior*: it Python-injects ~36K chars teaching what the substrate files and the envelope headers already declare.

---

## §2 What the thin frame keeps (the irreducible core — 3 things)

Only content that (a) fights the model's trained assistant prior, (b) is the model↔runtime interface contract, or (c) indexes substrate as authoritative. Nothing that re-teaches a substrate file's meaning or narrates a code-enforced gate.

1. **Principal-shift posture** (Δ1, fights assistant prior). One tight statement: you are installed judgment acting on the operator's behalf in their absence, not an assistant awaiting instruction; your standing intent is in MANDATE.md + standing_intent.md (pre-loaded below); read them and act. *Irreducible because it fights the model's assistant default — cannot live in operator substrate (it's a property of installing any judgment seat over an assistant-trained model, not an operator declaration).*
2. **Action-grammar / runtime-interface contract** (the cc8e0ab fix). A tool call IS your action; you direct, the runtime executes, the substrate revision is the channel; report only what tool calls returned (anti-confabulation). *Irreducible because it's about how tool-calls relate to reality — cannot live in substrate (substrate is data the agent reasons over; this is the agent↔runtime protocol).*
3. **Substrate-authoritative index** (the anti-rebloat commitment). Your governance lives in the substrate files pre-loaded in your message (IDENTITY/principles/MANDATE/AUTONOMY/PRECEDENT/preferences/pace); they are authoritative; this prompt does not restate them — read them. The envelope already labels each; trust the labels.

Target size: ~3–5K chars (from ~36K). ~85% reduction.

---

## §3 Per-section ablation verdicts (all 13)

Each `_compute_*` section classified: **KEEP-THIN** (folds into the 3-part thin frame) / **MOVE-PRINCIPLES** (operator/bundle substrate per §3.2.1) / **MOVE-SUBSTRATE** (other substrate home) / **DELETE-REDUNDANT** (envelope/substrate already carries it) / **DELETE-CODE-ENFORCED** (gate holds without prose).

| # | Section | Verdict | Justification |
|---|---|---|---|
| 1 | `identity_and_purpose` | **KEEP-THIN** (condense) | Carries Δ1 principal-shift + assistant-prior fight — the irreducible core. But 50 lines → ~10. The capital-EV bullets are reasoning-posture → MOVE-PRINCIPLES (they're "rules of judgment"). The "what you are" Variant-F sentence stays (FOUNDATIONS DP21 anchor). |
| 2 | `judgment_discipline` | **MOVE-PRINCIPLES** | "When to Clarify vs decide" is a rule of judgment (§3.2.1 domain). The anti-enumerate-options posture is the one assistant-prior-fight bit → KEEP-THIN one line; rest to principles.md. |
| 3 | `standing_intent_contract` | **MOVE-SUBSTRATE + KEEP-THIN** | The every-cycle-write commitment is real but it's *what the workbench file is for* → belongs in the workspace guide (ADR-281 substrate pedagogy) + a one-line pointer in thin frame. The P1–P5 posture taxonomy (ADR-303) is a runtime contract between Reviewer + dispatcher → KEEP-THIN compressed, OR move to the dispatcher's own doc. ~120 lines → ~8. |
| 4 | `independence_autonomy_precedent` | **MOVE-PRINCIPLES** | Independence (THESIS C2), reason-before-autonomy-filter, precedent-hierarchy are all rules-of-judgment + already enforced by code (dispatcher applies AUTONOMY post-verdict regardless of prose). DELETE-CODE-ENFORCED for the mechanism; MOVE-PRINCIPLES for the posture. |
| 5 | `voice_and_narration` | **KEEP-THIN** (this is the good one) | First-person + narrate-your-direction IS part of the action-grammar contract (cc8e0ab reconciled the rest of the frame TO this section). Keep, condensed. The trader-specific examples → DELETE (bundle-specific leak; the principle is generic). |
| 6 | `production_default` | **DELETE-REDUNDANT / MOVE-SUBSTRATE** | "Execute inline vs dispatch designer" is dispatch mechanics already determined by REVIEWER_PRIMITIVES (the Reviewer has the inline tools; DispatchSpecialist availability is the code surface). The model uses the tools it has. If any guidance survives it's one line in the thin frame's tool-usage note. |
| 7 | `cadence_trifecta` | **DELETE-REDUNDANT** | Re-explains pace/autonomy/persona that `_pace.yaml` + `_autonomy.yaml` + IDENTITY.md *declare* and the envelope *renders with headers*. The Schedule-pace-gate is code-enforced (`pace_exceeded` returned by the primitive). Pure ADR-281 violation. The one residue (Triggers-are-yours-to-author) → one line in thin frame's index ("your cadence is yours; see _recurrences.yaml"). |
| 8 | `pulse_discipline` | **DELETE-REDUNDANT** | Re-teaches reading `_schedule_index.md` + `_recent_execution.md` that the envelope *already injects as labeled sections*. The model reads what's in its message. The anti-hallucination intent is real but the cure is the envelope carrying the data (which it does), not prose telling the model to read its own message. |
| 9 | `wake_context_discipline` | **DELETE-REDUNDANT** | Re-explains the wake_source taxonomy that the envelope's `## Wake context` block *already carries structurally*. 800 chars explaining a block the model can read. The "cite wake_source when it matters" is a one-line note at most. |
| 10 | `preferences_and_notifications` | **DELETE-REDUNDANT + MOVE-SUBSTRATE** | Re-explains `_preferences.yaml` semantics the file's own frontmatter declares + the envelope renders. The operator_notifications + email-tool-exclusion detail is real but belongs in the workspace guide (substrate pedagogy), not the system frame. |
| 11 | `write_authority` | **DELETE-CODE-ENFORCED + KEEP-THIN** | The lock-set is enforced by `DEFAULT_REVIEWER_WRITE_LOCKS` + `_is_path_locked_for_reviewer` — code, not prose. The bounded/manual current-behavior + anti-confabulation rule (cc8e0ab) is action-grammar → KEEP-THIN. The lock *enumeration* → DELETE (code is the source; a one-line "some paths are operator-locked; the tool result tells you" suffices). |
| 12 | `self_amendment_discipline` | **MOVE-PRINCIPLES** | The four evidence patterns + revision-message format are *rules of judgment for when to amend operator-canon* — textbook §3.2.1 principles.md content. Per-program numerics already live in `_principles.yaml`. Move the prose to principles.md (bundle template). |
| 13 | `anti_patterns` | **MOVE-PRINCIPLES** | The six anti-patterns are *rules of judgment* (when NOT to amend). Operator-aligned decision: this is the autonomy-safety *discipline* and it belongs in principles.md (operator/bundle substrate), not the system frame. Residue-A resolved: safety-discipline is substrate, not system. |

**Tally**: KEEP-THIN core from 1+5+11 (+ slivers of 2,3) → the 3-part thin frame. MOVE-PRINCIPLES: 2,4,12,13 (+ posture slivers of 1,3). DELETE-REDUNDANT: 6,7,8,9,10. DELETE-CODE-ENFORCED: 4(mechanism),11(locks). MOVE-SUBSTRATE (workspace guide): 3(workbench-purpose),10(notifications-detail).

---

## §4 Risk register (what could break — checked per deletion)

| Risk | Mitigation |
|---|---|
| **Autonomy-safety regresses** (anti-patterns deleted → Reviewer loosens risk under drawdown) | Anti-patterns MOVE to principles.md (still in every wake's envelope as "## principles.md — Your framework"). NOT deleted — relocated to where §3.2.1 says rules-of-judgment live. The Reviewer still reads them every wake. PLUS the hard gates (`should_auto_apply`, ceiling_cents) are code and unaffected. |
| **Capital action binds beyond ceiling** | Impossible regardless of prose — `should_auto_apply` is code. The frame never enforced this; it narrated it. |
| **Reviewer regresses to assistant-mode** (asks operator, enumerates options) | The principal-shift + anti-enumerate posture is KEEP-THIN (the one thing that genuinely fights the prior). Preserved in the thin frame. |
| **Confabulation returns** | The action-grammar (cc8e0ab) is KEEP-THIN core. Preserved + now the dominant content of a small frame (less surface to contradict). |
| **Reviewer stops reading substrate it should** | The substrate-authoritative index explicitly points at the pre-loaded files. The envelope already renders them with headers. The model reads its own message. |
| **Posture-cell (P1–P5) dispatcher contract breaks** | The dispatcher's silent-exit fallback (P4/P5) is code (`dispatcher:silent_exit_fallback`). The model-authored cells (P1/P2) compress to "close every cycle with a verdict or a standing_intent write" — one line. |
| **Thesis is wrong; behavior degrades** | Each phase is a separate commit. Revert the collapse commit → main returns to cc8e0ab (working, deployed). Re-validation gates the keep decision. |

---

## §5 Execution phases (each a separate, independently-revertible commit)

- **Phase A** — collapse `reviewer_agent.py` persona-frame to the 3-part thin shape. Delete the 5 DELETE-REDUNDANT sections + the code-enforced enumerations. Keep KEEP-THIN core. (System frame: ~36K → ~4K.)
- **Phase B** — migrate MOVE-PRINCIPLES content (judgment-discipline, independence-posture, self-amendment four-patterns, six anti-patterns, capital-EV bullets) into the bundle `principles.md` templates (alpha-trader + alpha-author). Per §3.2.1 four-field shape where they fit; prose where they're posture. This is where the autonomy-safety discipline now lives.
- **Phase C** — migrate MOVE-SUBSTRATE content (workbench purpose, notifications detail) into the bundle `_workspace_guide.md` (ADR-281 substrate pedagogy home).
- **Phase D** — FOUNDATIONS amendment: new Derived Principle — *"The fundamentals (on-behalf-of, identity, self-governance) are carried by substrate + code. The system prompt carries only the model↔runtime interface contract (principal-shift, action-grammar, substrate index). It narrates no fundamental and re-teaches no substrate file — that is the anti-rebloat constraint."* Cite this audit + §3.2.2.
- **Phase E** — update stale persona-frame tests (the dead-`_PERSONA_FRAME`-regex set + section-presence tests that assert deleted sections) to assert the thin-frame contract instead; CHANGELOG; smoke test.
- **Phase F** — commit/push/deploy/full re-validation (the eval suite + the confabulation wake against the collapsed frame). If thesis holds → keep. If not → revert Phase A.

---

## §6 The falsifiable prediction (what re-validation must show)

If the thesis holds, the collapsed frame produces **equal-or-better** behavior than the 36K frame on:
- Confabulation (the cc8e0ab target): absent (action-grammar preserved).
- Non-assistant posture: preserved (principal-shift preserved).
- Autonomy-safety: preserved (anti-patterns now in principles.md, still read every wake; gates unchanged in code).
- Mandate-coherence: equal-or-better (less system narration competing with the operator's actual MANDATE for the model's attention).

If any of these regresses, the thesis is falsified for that dimension and Phase A reverts. The re-validation is the judge, not this document.
