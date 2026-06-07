# Assessment — The Reviewer's Prompting Configuration: Coherence, Implied Posture, and As-Applied Reality

> **Status**: ASSESSMENT (2026-06-07). Reads the agent's prompt configuration as a *composed whole* and judges coherence between the **declared** design philosophy (FOUNDATIONS Derived Principle 22 + 21) and the **as-applied** prompt the Reviewer actually receives. Companion to [primitive-surface-grounding-2026-06-07.md](primitive-surface-grounding-2026-06-07.md) — that doc maps the primitive *surface*; this maps how the prompts *wield* it and what *posture* they install.
> **Hat**: A (system canon — `api/agents/`, `docs/architecture/`). System vocabulary.
> **Authors**: KVK, Claude
> **Receipts discipline**: every measurement is from the running code (`python -c` against the live composers) or a `file:line`/canon citation.

---

## 0. The question

The operator: *"read the existing prompting configuration on our agent, to understand its coherence and implied behavior and posture — not only the mechanics but how it's applied to the agent."*

Answer in one sentence: **the declared prompt philosophy is elegant and coherent (a thin kernel frame that installs *judgment-not-assistant* + the tool grammar, with all character coming from operator/bundle substrate read at wake time); the as-applied configuration only half-implements it — ADR-306 collapsed the persona-frame to 5.3K but left a 11.2K `cockpit_awareness` block bolted on after it, unreconciled against the very principle (DP22) that the collapse established.**

---

## 1. The declared philosophy (what the prompt is *supposed* to be)

Three governing canon, all post-2026-05:

**Derived Principle 21 (Reviewer formalization).** "The Reviewer is a full-substrate-authoring persona-bearing judgment seat — filesystem-native, single-lane queue-serialized, wake-fired, paced by operator-declared pace + autonomy, driven by operator-authored mandate." Every Reviewer-framing artifact must align with this sentence.

**Derived Principle 22 (the system prompt carries only the model↔runtime interface contract).** The three things that make a YARNNN seat different from a generic assistant — *on-behalf-of*, *identity-infusion*, *self-referential governance* — are each carried by **substrate + code, NOT by system prose**. Therefore the system-authored prompt layer carries **only two irreducibly-system-authored things**:
1. **principal-shift** — "you are installed judgment acting on the operator's behalf, not an assistant awaiting instruction" (corrects the *model's trained assistant prior*).
2. **action-grammar** — the agent↔runtime interface contract (a tool call IS the action; narrate only what tool calls returned; read fresh substrate; close with a verdict/standing_intent).

**The anti-rebloat constraint (the diagnostic test):** *every proposed addition to the frame must answer "is this correcting the model's prior, or defining the runtime interface?" — if neither, it belongs in substrate or code.* Specifically: rules of judgment → `principles.md`; substrate pedagogy → `_workspace_guide.md` (ADR-281); code-enforced gates → carry no prose at all.

This is a genuinely good design. It is the Claude-Code shape: a small system prompt that sets the interaction contract, and a rich repository (`CLAUDE.md` ≈ `principles.md` + `_workspace_guide.md` + the substrate envelope) that carries everything else. ADR-306 collapsed the frame from ~36K chars / 13 `_compute_*` sections to ~3.5K toward this shape.

---

## 2. The as-applied configuration (what the Reviewer actually receives)

### 2.1 The assembly (receipt: `reviewer_agent.py::_build_system_prompt`, lines 518-550)

```
system_prompt = persona_body + "\n\n" + build_cockpit_section()
              = resolve_persona_frame_sections(_PERSONA_FRAME_SECTIONS)   # the "collapsed" frame
              + build_cockpit_section()                                    # bolted on, separate module
```

Then per wake, the **user message** envelope (`_build_user_message`) pre-loads the substrate (IDENTITY, principles, MANDATE, AUTONOMY, PRECEDENT, pace, preferences, occupant, standing_intent, schedule-index, recent-execution, specs-inventory, domain substrate) + the trigger framing (`_TRIGGER_FRAMING[reactive|addressed]`).

### 2.2 Measured sizes (live, from the running composers)

| Component | Chars | DP22 verdict |
|---|---|---|
| `_compute_minimal_frame()` | **5,290** | ✅ COMPLIANT — principal-shift + action-grammar, nothing else |
| `build_cockpit_section()` | **11,215** | ⚠️ **the seam** — 2× the "collapsed" frame, not in ADR-306 |
| ├─ `build_filesystem_block()` | 2,949 | ✗ substrate pedagogy → DP22 says `_workspace_guide.md` |
| ├─ `build_tools_block()` | 3,444 | ~ borderline — tool list is arguably interface-grammar |
| └─ `_OPERATING_POSTURE` | 4,580 | ✗ posture + substrate-missing rules + write-authority + tool-loop → DP22 says `principles.md` / `_workspace_guide.md` / code |
| **system prompt total** | **~16.5K** | the "collapse to ~3.5K" landed at ~16.5K once cockpit is counted |

### 2.3 The trigger framing (the *behavioral* posture, per wake)

`_TRIGGER_FRAMING` (`reviewer_agent.py:411-514`) is appended to the user message. Two shapes:

- **`addressed`** (operator at the cockpit) — installs an aggressively **action-first** posture: *"The default is action… Stand-down is the LAST option… DO NOT enumerate options for the operator… Pick the option your framework tells you is right and execute it."* ~2.5K chars of posture.
- **`reactive`** (proposal arrival OR judgment-recurrence fire) — installs a **verdict-first** posture: *"Call ReturnVerdict with approve|reject|defer EARLY… do NOT write standing_intent.md before the verdict on proposal wakes."* Plus a long enumeration of recurrence sub-shapes (reflection / substrate-refresh / compose-deliverable / conditions-check / pre-ship-audit).

This trigger framing IS legitimate model↔runtime interface (it tells the model *how this wake's loop should close*), so it's largely DP22-defensible. But it ALSO re-teaches substrate pedagogy ("the wake envelope already pre-loaded governance + ground-truth substrate", the recurrence sub-shape catalog) — partial leakage.

---

## 3. The seam, named precisely

**ADR-306 collapsed `_PERSONA_FRAME_SECTIONS`. It did not touch `cockpit_awareness`.** Receipt: `grep -i cockpit docs/adr/ADR-306-persona-frame-collapse.md` → **zero matches**. The collapse measured itself against `_compute_*` sections in `reviewer_agent.py` and hit 90% reduction there — while a separate module (`cockpit_awareness.py`, introduced by ADR-258 D5 for drift-resistance) carrying 11.2K chars of exactly-the-forbidden-content was concatenated to the result and never audited against the new principle.

**The dual-mention is literal, not abstract.** The `_workspace_guide.md` (the DP22-designated home for substrate pedagogy) and `cockpit_awareness` teach the *same topics in two places*:

| Topic | `cockpit_awareness` (system prose) | `_workspace_guide.md` (DP22's home) |
|---|---|---|
| Filesystem topology / what each file is for | `build_filesystem_block` (2,949 ch) | "What this workspace contains", "Path zones" (lines 4-77, 392) |
| How you operate across wakes | `_OPERATING_POSTURE` "How you operate" | "How you operate across wakes" (line 155) |
| Wake envelope contents | `_OPERATING_POSTURE` | "Your wake envelope" (line 165) |
| Missing-substrate / divergence rules | `_OPERATING_POSTURE` "When substrate is missing" | "When things diverge" (line 424) |
| Don't-write-operator-canon | `_OPERATING_POSTURE` "Write authority" | "What NOT to write to operator-canon" (line 444) |
| Tool-use loop | `_OPERATING_POSTURE` "Tool-use loop" | (the action-grammar belongs in the frame) |

Notably the `_workspace_guide.md` version is **better factored** — it says "operator-canon paths… the lock policy will reject the write, but the discipline is upstream of the lock" (generic, ADR-320-compatible), while `_OPERATING_POSTURE` enumerates specific gates and (until the 2026.06.07.x fixes) drifted on specifics. **The bundle guide is the canonical version; the system-prose copy is the redundant, drift-prone one** — which is exactly the failure mode DP22 was written to prevent.

---

## 4. Why this matters (the implied-behavior consequence)

This is not cosmetic. Three concrete consequences:

1. **Drift surface.** Every substrate fact taught in `cockpit_awareness` is a fact that can disagree with `_workspace_guide.md` or the gate. The 2026.06.07.2 finding (the `_OPERATING_POSTURE` ADR-293-vs-ADR-320 self-contradiction *within the same prompt*) was an instance of exactly this — and it was only catchable because the same fact lived in two places that drifted apart. DP22 exists to make that class structurally impossible by having one home.

2. **Cost + cache.** The system prompt is cache-marked ephemeral (good), but it's ~16.5K chars billed at cache-create on the first wake of each TTL window, across every workspace, every deploy. The "90% reduction" DP22 promised is ~67% un-delivered because cockpit wasn't in scope.

3. **Posture dilution.** DP22's thesis is that a *thin* frame produces *sharper* judgment (the ablation evidence: a 22-tool surface collapsed output 74% vs 21; tool-list and prose size are empirically corrosive to judgment quality — `docs/evaluations/2026-05-25-...adr299-always-surface-resolution/`). If tool-count is corrosive, 11.2K of bolted-on prose plausibly is too. The minimal frame's whole bet is that the model reasons better from substrate-it-reads than from prose-it's-told; cockpit_awareness re-tells what the envelope already shows.

---

## 5. What IS coherent (so the assessment is balanced)

Much of the configuration is genuinely well-built and should be preserved:

- **The minimal frame itself** (`_compute_minimal_frame`) is exemplary DP22 — principal-shift + action-grammar, index-not-assert (ADR-314), coherent in both operating + standby states. Don't touch it.
- **The envelope pre-loading** (`_build_user_message`) is correct: load-bearing substrate arrives *in the message*, not as a "remember to ReadFile X" side-quest (the ADR-275 learning). Full-path headers (post-2026.06.07.1). This is the right pattern.
- **Model-by-trigger** (Sonnet for capital proposal-arrival, Haiku for conversation/framework) + **round-budget-by-trigger** (3 for discrete capital decision, 20 for read-heavy recurrence/addressed) + **`tool_choice={"type":"any"}` on round 0** (forces a tool call, no assistant-chit-chat opening) — all coherent mechanics that express the posture well.
- **Cache-marking** the static system prompt is correct (the cost story just under-delivers because the static block is 3× bigger than DP22 intended).
- **`cockpit_awareness` being *generated* from `workspace_paths` constants + the primitive registry** (ADR-258 D5 drift-resistance) is a good instinct — it just generates content that DP22 says shouldn't be in the system prompt *at all*. The drift-resistance mechanism is sound; the thing it's applied to is misplaced.

---

## 6. The recommendation

**`cockpit_awareness` should be collapsed against DP22, the same way `_PERSONA_FRAME_SECTIONS` was by ADR-306 — finishing the collapse ADR-306 started but scoped too narrowly.** Concretely:

- **`build_filesystem_block`** (substrate pedagogy) → DELETE from the system prompt. It already lives in `_workspace_guide.md` (bundle-shipped, read at wake). The Reviewer doesn't need the kernel to re-teach paths the envelope renders with labeled headers + the guide explains.
- **`_OPERATING_POSTURE`** → SPLIT by DP22's diagnostic test:
  - "How you operate" / "When substrate is missing" / "Write authority" fiduciary posture / "When things diverge" → these are **rules of judgment + substrate pedagogy** → already in `principles.md` + `_workspace_guide.md`. DELETE from system prose.
  - "Tool-use loop" (ListFiles→ReadFile→…→ReturnVerdict last) → this is **action-grammar** → it belongs in the minimal frame (and largely already is). Merge any genuinely-missing interface detail UP into `_compute_minimal_frame`, delete the rest.
- **`build_tools_block`** → KEEP, but it's the one defensible part — the tool surface is interface. (Even this could thin: the model receives the tool *schemas* in the `tools=` API param already; the prose list partly duplicates them. Worth measuring whether the prose tool-list earns its 3.4K.)

**Net:** the system prompt collapses from ~16.5K toward the ~3.5–6K DP22 actually intended, the dual-mention with `_workspace_guide.md` is eliminated, and the drift class that produced the 2026.06.07.2 self-contradiction is closed structurally.

**This is an ADR.** It amends ADR-258 (D5 cockpit-awareness — the *generation* mechanism survives for the tool-block; the substrate/posture content dissolves) and *completes* ADR-306 (the frame collapse extends to the bolted-on module DP22 didn't originally scope). It's the behavioral-layer twin of the primitive-surface re-grounding in the companion doc — both are "the post-ADR-320 architecture wants a leaner surface than the accreted one."

---

## 7. How this composes with the primitive-surface discourse

The two assessments rhyme:

- **Primitives** (companion doc): the surface accreted across deleted eras (project/task/user_memory); post-ADR-320 it wants *one authored write, one two-rank read, a narrow /proc-style relational read*. The `context` family and parts of the `entity` layer are vestigial.
- **Prompts** (this doc): the system prose accreted across pre-DP22 eras; post-ADR-306 it wants *a minimal frame (principal-shift + action-grammar) + substrate read at wake*. The `cockpit_awareness` block is the vestigial bolt-on.

**Same root cause, same fix shape:** the architecture made a strong simplifying commitment (ADR-320 topology / ADR-306 DP22), the commitment was implemented in its *primary* site, and an *adjacent* site (the primitive `scope`/`entity` layer; the `cockpit_awareness` prompt module) was left carrying the old shape. Both are "finish the collapse the architecture already decided on." Neither is a new direction — both are *completion*.

---

## Appendix — receipt index

- System prompt assembly: `reviewer_agent.py:518-550` (`_build_system_prompt` = persona_body + `build_cockpit_section()`).
- Measured sizes (live `python -c`): minimal_frame 5290, cockpit_section 11215 (filesystem_block 2949, tools_block 3444, _OPERATING_POSTURE 4580).
- DP22: FOUNDATIONS.md:716. DP21: FOUNDATIONS.md:718. DP24 (stewardship posture → principles.md, NOT frame): FOUNDATIONS.md:712.
- ADR-306 scope (no cockpit mention): `grep -i cockpit docs/adr/ADR-306-persona-frame-collapse.md` → 0.
- Dual-mention: `_workspace_guide.md` (alpha-trader) headers — "How you operate across wakes" (155), "Your wake envelope" (165), "When things diverge" (424), "What NOT to write to operator-canon" (444) vs `cockpit_awareness._OPERATING_POSTURE`.
- Trigger framing: `reviewer_agent.py:411-514` (`_TRIGGER_FRAMING[addressed|reactive]`).
- Model + round budget by trigger: `reviewer_agent.py:39-43, 1059` (Sonnet/3 for proposal-arrival; Haiku/20 for addressed + recurrence).
- `tool_choice={"type":"any"}` round 0: `reviewer_agent.py:1095`.
- Ablation evidence (tool-count corrosive to judgment): `docs/evaluations/2026-05-25-042346-adr299-always-surface-resolution/`, `docs/evaluations/2026-05-29-persona-frame-collapse-ablation.md`.
