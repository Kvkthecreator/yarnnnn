# ADR-365 — Register Follows Consumer: the operator-facing channel has its own diction, not just its own syntax

**Status**: **Implemented (D3 only)** (2026-06-24) — D3 shipped + retained; **D2 + D4 reverted after the eval falsified them**; D1 narrowed to the eval finding. Drafted ahead of implementation per doc-first discipline, implemented, then **empirically validated the same session** — the validation is the whole point of the "an eval is owed" promise in §6 below.

**Eval disposition (the validation §6 owed — receipt: [`docs/evaluations/2026-06-24-adr365-register-ab-FALSIFICATION.md`](../evaluations/2026-06-24-adr365-register-ab-FALSIFICATION.md)).** A controlled A/B on the prompt itself (`probe_adr365_register_ab_local.py`, 4 trials/arm, D2-present vs D2-stripped, same empty-author envelope, Haiku tier) found:
- **D2 (frame directive) does NOT measurably move the model's free-prose register** — A=2.72 vs B=2.60 pure-jargon per 1000 chars, within noise. → **REVERTED.**
- **D4 (verdict-headline note) solved a non-problem** — the headline is already clean in both arms (0.0/k). → **REVERTED.**
- **D3 (narration strings) is the real lever** — deterministic Python, plain by construction. → **RETAINED.**
- The motivating jargon lives in `standing_intent`, a *forward-reasoning* surface §D5 deliberately leaves the agent free to reason in canon within — so a soft prose directive neither moves it nor should.

**Bonus, retained independently of D2/D4.** The §3.2.1 citation + pedagogy *compressions* made while landing D2 (the over-long DP31 block — the per-program sourcing rule already lives in both bundles' `principles.md`; the governing-file header enumeration the envelope already labels; the principles.md content-restatement) were correct on their own terms — enforcing the partition's "one clause" rule. **Kept.** With D2/D4 gone they bring the composed system body to **11109 chars — under the 11500 ceiling for the first time** (it was 12023 at HEAD, a pre-existing red). The voice ADR incidentally paid down a frame-ceiling debt it did not create.

**The durable lesson (revised thesis).** The operator-legibility lever is **the surfaces YARNNN renders deterministically (D3), not the model's free prose (D2/D4).** Where the model reasons freely the canon register is partly load-bearing; if raw `standing_intent` jargon reaching the operator is a real problem, the fix is a composed plain-English projection rendered FROM standing_intent (ADR-340 "compose few"), not a frame directive — a separate, larger ADR, deliberately not attempted here.
**Deciders**: KVK + Claude
**Dimensional classification** (Axiom 0): **Channel** (primary — Axiom 6: the cognitive consumer determines the channel's affordance; this ADR extends "affordance" from *syntax* to *diction/register*) + **Mechanism** (secondary — *where* the register-switch instruction is authored, and the anti-rebloat constraint on the persona frame, DP22).
**Discourse base**: a 2026-06-24 voice/style audit of the live Reviewer (this session). The operator observed that YARNNN's agent writes operator-facing prose in dense internal canon vocabulary (`substrate`, `aperture`/`floor`, `standing obligation`, `cadence-drift`, `hard-trigger from principles.md`) where Claude Code — a far more technical tool — reads as plain, layperson-legible. Ground-truth receipts below.
**Reuses (no new taxonomy)**: ADR-254 (file-format discipline — *format follows consumer*; this ADR is its register twin), Axiom 6 (Channel — consumer-determines-affordance, already canon), DP22 (the persona frame carries only the model↔runtime interface contract — the anti-rebloat constraint this ADR must obey), ADR-281 (`_workspace_guide.md` — the kernel does not author its own pedagogy; bundle teaches), agent-composition.md §3.2.1 (the frame-vs-principles partition this ADR slots into).
**Amends (the canon this completes)**: FOUNDATIONS Axiom 6 (Channel gains the register sub-clause); `docs/architecture/agent-composition.md` §3.2.1 (the partition gains a third home — the consumer-register directive); `api/prompts/CHANGELOG.md` (the frame text, if D-final lands there).

---

## 1. The finding (receipt-grounded)

The operator's instinct: *Claude Code is a deeply technical tool, yet it talks more coherently and more layperson-friendly than YARNNN's agent does.* The audit found the instinct **correct, and structurally explicable** — it is not a quality gap in the model, it is a missing instruction the codebase's own axioms predict.

### 1.1 — Claude Code spends ~400 words teaching the model how to address a human. YARNNN spends one sentence.

Claude Code's `getOutputEfficiencySection()` ([src_claudeCC/constants/prompts.ts:405-414](../analysis/src_claudeCC/constants/prompts.ts#L405-L414)) is a dedicated **"Communicating with the user"** section whose load-bearing instruction is:

> "Assume the person has stepped away and lost the thread. They don't know codenames, abbreviations, or shorthand you created along the way... use complete, grammatically correct sentences **without unexplained jargon. Expand technical terms.** Err on the side of more explanation."
> — plus: "Write user-facing text in flowing prose"; "lead with the action" (inverted pyramid); "what's most important is the reader understanding your output without mental overhead or follow-ups, not how terse you are."

YARNNN's **complete** equivalent is one sentence in the persona frame ([api/agents/reviewer_agent.py:393-395](../../api/agents/reviewer_agent.py#L393-L395)):

> "**Narrate your direction in first person**, plainly. ... Make the conversation legible."

"Plainly" and "legible" are the entire operator-facing-voice brief. There is no model of who the reader is, no jargon-expansion directive, no lead-with-the-takeaway rule. A grep of the whole Reviewer surface (`reviewer_agent.py` + `reviewer_chat_surfacing.py` + `occupant_contract.py`) for `jargon|stepped away|lost the thread|expand|non-technical|laymen|mental overhead` returns **zero** operator-reader instructions.

### 1.2 — The frame the agent reasons inside is written in internal canon vocabulary, so the agent writes back out in it.

The persona frame describes the agent to itself ([reviewer_agent.py:295-299](../../api/agents/reviewer_agent.py#L295-L299)):

> "You are a full-substrate-authoring persona-bearing judgment seat — filesystem-native, single-lane queue-serialized, wake-fired, paced by operator-declared pace + autonomy..."

and hands it the concepts to reason with: **aperture**, **floor**, **standing obligation**, **structural_gap**, **ground-truth**, **topological write boundary**, **FOUNDATIONS Derived Principle 21**. These are precise and *correct* — they are the ADR vocabulary, load-bearing for judgment quality. But the operator reading the chat panel never read the ADRs. With no instruction that this vocabulary is insider-only, the agent reaches for the only register it was immersed in. The live `standing_intent.md` (observed this session) reads:

> "Recurrences are firing and failing predictably on empty substrate... The pre-ship-audit hook is armed and waiting. No hard-trigger from principles.md fires — there is no declared corpus-authoring cadence to miss, so cadence-drift doesn't apply."

A layperson cannot parse `hard-trigger from principles.md`, `cadence-drift doesn't apply`, or `firing and failing on empty substrate`. **This is the agent writing to itself, in canon vocabulary, surfaced to a human.**

### 1.3 — The hard-coded narration strings have the same defect.

The per-action feed line the operator sees ([reviewer_chat_surfacing.py:339](../../api/services/reviewer_chat_surfacing.py#L339)):

> `Wrote to Reviewer substrate on its direction.`

"Substrate" is the filesystem-as-Postgres abstraction — an implementation detail the operator does not have. "On its direction" is stilted. These strings cost **zero prompt budget** (they are Python f-strings, not model output) and are the cheapest possible win.

## 2. The architectural defect, stated in the codebase's own axioms

This is not a style preference. Axiom 6 (Channel) **already** says the cognitive consumer determines the channel's affordance ([FOUNDATIONS.md:490-499](../architecture/FOUNDATIONS.md#L490-L499)):

> "Addressed channels inherit [Axiom 2's distinct-scope]: the **cognitive consumer determines the channel's affordance.**"
> — Operator (human user) → Surfaces + email. Another Identity within YARNNN → Substrate.

The Reviewer authors several artifacts that are read by **two different cognitive consumers**:

| Artifact | Consumer 1 (next-wake reader) | Consumer 2 (operator) |
|---|---|---|
| `standing_intent.md` | the agent next wake (envelope-rendered) | the operator reading `persona/` |
| verdict `reasoning` headline | written to `judgment_log.md` (agent-read) | surfaced to the feed (operator-read) |
| feed narration | — | operator only |

Today the agent writes all of these in **one register** — the next-wake-agent register (dense canon). That is a **register collapse across the Channel dimension**: a single artifact serves two cognitive consumers at one diction, when Axiom 6 says the consumer determines the affordance. The defect is precisely a violation of the axiom already on the books.

### 2.1 — The precedent is ADR-254, and this ADR is its missing twin.

ADR-254 (file-format discipline) already canonized **"format follows the consumer"** — `.md` UPPERCASE for operator/LLM prose, `_*.yaml` for Python, `.json` for machines. That discipline governs **syntax** (which file extension, which parser). It says nothing about **diction** (which vocabulary, which register).

> ADR-254 made *syntax* follow the consumer. Nothing made *diction* follow the consumer. ADR-365 is that twin: **register follows consumer.**

A `.md` file is the right *format* for both the next-wake agent and the operator — they both read prose. But "the right format" is not "the right register": the operator and the agent are different cognitive consumers of the same prose, and the diction must split even when the extension does not. This is the gap ADR-254 left open, named.

## 3. The first-principles question the operator flagged: *where does the directive live, future-proof?*

The operator explicitly declined to pre-commit the home, asking that it be derived correctly rather than chosen by preference. The derivation:

The thing being added is **a register-switch rule: when you address the operator, write for someone who has not read your ADRs.** Where it lives is determined by *what kind of thing it is* under the existing frame-vs-substrate partition (agent-composition.md §3.2.1):

- **It is NOT a rule of judgment** (when to Clarify, independence, evidence patterns) → so it does **not** belong in `principles.md`.
- **It is NOT substrate pedagogy** (what each file is for) → so it does **not** belong in `_workspace_guide.md` (ADR-281).
- **It IS part of the model↔runtime interface contract** — specifically the *output*-half of that contract: "how the channel you emit to is consumed." The frame already owns the output-side interface grammar: anti-confabulation ("describe only what your tool calls returned"), citation-binds-to-Source (DP31), "narrate in first person." **The consumer-register directive is the same *class* of thing as those** — it is interface grammar (how to shape what you emit), not a rule of judgment (what to decide).

**Therefore the directive's home is the persona frame**, alongside the existing output-interface grammar (anti-confabulation, citation, first-person narration). This is the kernel-universal answer: it applies to every program (trader, author, any future bundle) identically, because "write for a reader who hasn't read your internals" is consumer-shaped, not program-shaped — exactly the agnosticism test ADR-343 applied to aperture/floor.

### 3.1 — The constraint that makes "where" non-trivial: the frame is at its size ceiling.

DP22 (persona-frame collapse) holds the frame to the model↔runtime interface contract and nothing else, under an explicit **anti-rebloat constraint** ([reviewer_agent.py:255-258](../../api/agents/reviewer_agent.py#L255-L258)). The frame is **already over its declared ceiling** (the live gate `test_system_prompt_under_ceiling` is red — frame ~11841 chars vs 11500 cap, a prior-session rebloat). So "put it in the frame" cannot mean "add 400 words like Claude Code." The directive must be **the tightest possible interface-grammar line** — 2-4 sentences in the register of the existing anti-confabulation / citation lines, NOT a Claude-Code-length pedagogy block.

The detailed, example-rich version (the "stepped away, lost the thread, expand technical terms, inverted pyramid" exposition) is **not** kernel content. By the same ADR-281 logic that puts substrate pedagogy in `_workspace_guide.md`, the *worked examples* of operator-facing prose belong in bundle-authored guidance, NOT the kernel frame. The frame carries the *contract* ("address the operator in their register, not yours"); the bundle may carry *worked examples* if a program wants them. This is the frame-thin / substrate-rich split the codebase already runs.

> **Resolution of the "where" question:** the *contract* (one tight interface-grammar line) lives in the persona frame (kernel-universal); the *worked exposition* (if any) lives in bundle guidance (`_workspace_guide.md`). This mirrors DP22 (frame = contract) × ADR-281 (bundle = pedagogy), and is future-proof because it scales per-program without touching the kernel.

## 4. Decisions

### D1 — Axiom 6 gains the register sub-clause (canon)
FOUNDATIONS Axiom 6: "the cognitive consumer determines the channel's affordance" is amended to read affordance as **both syntax and register**. An artifact addressed to the operator is written for a reader who has not read the system's internals; an artifact addressed to the next-wake agent may use the full canon register. Where one artifact is read by both, the **operator register governs** (the agent can always parse plain prose; the operator cannot always parse canon). New Derived Principle (number TBD at ratification): *register follows consumer — the twin of ADR-254's format-follows-consumer.*

### D2 — One tight interface-grammar line in the persona frame (Mechanism)
Add to `_compute_minimal_frame()`, adjacent to the existing "Narrate your direction in first person, plainly" line, a 2-4 sentence directive of the form: *"When you address the operator (feed narration, standing_intent, the verdict headline they read), write for someone who has not read your governing files or this system's internals. Do not use internal vocabulary — `substrate`, `aperture`/`floor`, `cadence-drift`, `hard-trigger` — without expanding it in plain words, or better, naming the thing itself ('there's nothing to review yet' not 'firing on empty substrate'). Lead with what it means for the operator, then the mechanism. Your internal reasoning keeps the canon register; the words you address to the operator do not."* **Must fit the anti-rebloat ceiling** — this lands only alongside a move-to-principles that brings the frame back under cap (the ceiling debt is pre-existing; D2 does not get to ignore it). Update CHANGELOG.

### D3 — Rewrite the hard-coded narration strings (Mechanism, zero prompt cost)
[reviewer_chat_surfacing.py:336-345](../../api/services/reviewer_chat_surfacing.py#L336-L345) — drop "substrate" and "on its direction" from operator-facing strings. `Wrote to Reviewer substrate on its direction.` → e.g. `Saved a note to its own working files.` (or a per-path-aware line that names what was written in plain terms). `Proposal submitted on Reviewer's direction.` → `Submitted a proposal for your review.` These cost nothing and are independent of D2 — they can ship first as the cheap win.

### D4 — The verdict-headline instruction gains the consumer note (Mechanism)
The `ReturnVerdict.reasoning` description ([reviewer_agent.py:128](../../api/agents/reviewer_agent.py#L128)) — "2-5 sentences in your persona's voice" — gains one clause: *this headline is read by the operator on the feed; write it in their register.* The headline is the single most operator-visible piece of agent prose and currently gets no consumer guidance.

### D5 — What this ADR explicitly does NOT do
- It does **not** touch the agent's *internal reasoning* register — `aperture`/`floor`/`standing obligation` stay exactly as they are in the frame, principles, and the agent's private reasoning. Judgment quality depends on that vocabulary. **Only the operator-addressed channel changes.**
- It does **not** add a Claude-Code-length section to the frame (DP22 / anti-rebloat).
- It does **not** move rules of judgment or substrate pedagogy (those stay in principles.md / `_workspace_guide.md` per §3).

## 5. Consequences

**Positive.** The operator-facing channel becomes layperson-legible without diluting judgment vocabulary — the moat's "your accumulated context, legible to you" claim gets honest at the prose layer. The fix is derived from an axiom already on the books (Axiom 6), so it is future-proof: every new program inherits it, no per-program work. D3 is a same-day shippable win at zero prompt cost.

**Cost / risk.** D2 cannot land until the frame ceiling debt is paid (a move-to-principles is owed regardless). There is a residual judgment call the model must make per-wake — "is this term canon or plain?" — which the directive can only guide, not enforce; a future eval (not this ADR) would measure whether operator-facing prose actually got more legible. The register-split also means the *same concept* may be named two ways (canon in reasoning, plain to the operator); that is the intended consequence of consumer-determines-affordance, not drift.

## 6. Open (deferred, not blocking)
- The exact Derived Principle number + final frame wording are settled at ratification (paired with the ceiling-debt move-to-principles).
- Whether bundles ship *worked examples* of operator-register prose in `_workspace_guide.md` is a per-bundle authoring call, deferred to bundle maintainers.
- An eval that measures operator-facing-prose legibility (a Hat-B scenario) is owed before claiming D2 worked — not part of this ADR.
