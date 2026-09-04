# ADR-638 — The agent speaks the member's language, not ours

> **Status**: **Accepted + Implemented** (2026-09-04, operator-observed: *"the messages relayed by the agents are technical and not really using the apps' user facing terminology — it's referring to its own technical implementations"*). Gate: `api/test_adr638_register.py`.
> **Date**: 2026-09-04
> **Authors**: KVK (operator) + Claude (collaborator)
> **Dimensional classification** (Axiom 0): **Channel** (Axiom 6 — the cognitive consumer determines the channel's affordance, extended from syntax to diction). No Identity, Purpose or authority change.

> **Numbering provenance (2026-09-04)**: first landed as ADR-638 after a same-day collision — a concurrent session had pushed [ADR-637](ADR-637-visiting-a-conversation-is-reading-it.md) (*visiting a conversation is reading it*) while this arc was in flight, and both claimed 637. That commit landed first, so it keeps the number and this one moved. The two are unrelated; nothing in either was rewritten. Renumbered before this ADR was referenced anywhere outside its own gate + probe.

**Restores**: [ADR-365](ADR-365-register-follows-consumer.md) — *register follows consumer*, ratified 2026-06-24 and **empirically validated at +49–79% operator readability**. Its directive lived in the steward's frame and was **deleted with the steward** ([ADR-632](ADR-632-the-seat-retires.md)); the lane frame that replaced it never carried one. This ADR re-homes the validated rule onto the surface that now does the talking.

**Extends**: [ADR-533 D1](ADR-533-the-participant-contract.md) — the participant contract's singular clauses, authored once and composed per surface. The register clause is a new sibling of `PARTICIPANT_FILESYSTEM_MODEL` and `PARTICIPANT_FORMAT_DISCIPLINE`.

**Preserves**: ADR-365 **D5** (a forward-reasoning surface stays free to reason in canon), ADR-306 / DP22 (the frame is ablated, not accreted — the anti-rebloat ceiling), ADR-630 (craft belongs in a skill; this is interface grammar, not craft).

---

## 1. The finding — the discipline exists everywhere except the agent's own prose

YARNNN already refuses internal vocabulary at two of the three places it can leak:

| Surface | Internal | What the member is told | Home |
|---|---|---|---|
| Tool names | `EditFile` | *"revised a file in your workspace"* | `web/components/chat-surface/toolLabels.ts` |
| Paths | `operation/`, `inbound/` | *"Documents"*, *"Downloads"* | `PARTICIPANT_FILESYSTEM_MODEL` + `HOME_ALIASES` |
| **The agent's own sentences** | — | **nothing** | **—** |

`toolLabels.ts` names the defect in its own docstring — *"the same internal-vocabulary leak the artifact card fixed for the artifact half"* — and `PARTICIPANT_FILESYSTEM_MODEL` is a deliberate, kernel-wide translation: the substrate says `operation/`, every LLM is told **Documents**, and `parse_file_reference` resolves back at one chokepoint. Both are the same rule. Neither covers prose.

**Why the leak is structural, not a model failure.** The authoring posture must teach the agent the real grammar — `data-block-id`, `data-arrange`, `data-area-role`, tokens, measures — because it has to *author* it. ~10.5K characters of the frame are that grammar. Nothing told the agent the grammar is **private to the tool**. Immersed in one vocabulary and given no other, it reaches for the one it was handed. Exactly ADR-365 §1.2's diagnosis, one surface over.

## 2. The receipts (120 consecutive live assistant replies, 2026-09-04)

| Leak | Replies | Verbatim |
|---|---|---|
| Raw tool name | 11 | *"My ReadFile tool returns file content as text/data"* |
| `data-*` grammar | 6 | *"slide 6 is the closing slide (`data-arrange=…`)"* |
| Block ids | 3 | *"a prose block reading 'One idea per slide.' (placeholder, block `b1`)"* |
| Coordinate keys | 1 | *"**Headline (z:5)** — Moved from `y:58%` → `y:66%`"* |

The operator's screenshot is the fourth row: an IMAGES read-back rendered as a table of `y:82%` → `y:86%`, `(z:5)`, *"tier separation"*, *"opacity 72% → 62%"*.

A second, distinct defect appears in the same corpus — **narration preamble**: *"Let me read the current deck to see what's on slide 6, then I'll create the CSV data files"* immediately concatenated with *"Good — slide 6 is the closing slide…"*. The member gets a plan for work that is already finished by the time they read it.

Verbosity, for calibration: median 104 words / 7 lines; p90 310 words; 45 of 120 over 150 words. Not pathological, so **this ADR sets no length limit** — the failure measured is register and preamble, not length.

## 3. The benchmark (the operator's suggestion, run honestly)

Claude Code's **public documentation contains no rule about vocabulary, internal identifiers, or how to describe changes.** Its system prompt is not published. What is documented is **output styles** — `Concise` being *"leads with the result, skips preamble and narration, and keeps responses short by default"*.

So the benchmark supplies **one** transferable rule (lead with the result, skip narration) and **not** the vocabulary rule. The vocabulary rule comes from our own ADR-365, which quoted Claude Code's *unpublished* `getOutputEfficiencySection` in June 2026 — *"They don't know codenames, abbreviations, or shorthand you created along the way… Expand technical terms."* That quote is the origin, and it is already ratified canon here. **We are not importing a convention; we are restoring one we lost.**

⚠️ **Output styles are NOT adopted.** A per-member verbosity preset is a real feature, and a different one: it needs a preference store, a door, and a default. Named here as deliberately out of scope so a future session does not read this ADR as having declined it.

## 4. D1 — The register clause is a participant clause, composed into the lane frame

`PARTICIPANT_REGISTER` in `services/workspace_paths.py`, beside the filesystem model and format discipline it is a sibling of, composed by `lane_runner` as `## Talking to {member}`.

Three rules, each naming the concrete failure it fixes:

1. **Name the thing, not its mechanism** — *"I moved the headline down and made it bigger"*, never `y:58% → y:66%, z:5`. Attribute names, ids, tokens, measures, layouts and revision ids are ours: **use them in the file, never in the reply**.
2. **Lead with what changed, then why** — and skip the narration of what you are about to do.
3. **Their words** — slides, pages, layers, images, posts, folders: the nouns on their screen.

⭐⭐⭐ **STRUCTURE, NOT WORD-FREQUENCY — the falsified arm must not return.** ADR-365's first attempt was a vague *"write plainly"*, and a controlled A/B **falsified it** (2.72 vs 2.60 jargon per 1000 chars — within noise). What worked in 365b was naming the concrete bad→good failure per rule. A future edit that softens these into "be clear and concise" is re-running the arm that was already measured not to work.

⭐ **It governs the ADDRESS, never the WORK.** The agent still reasons in and writes the real grammar — `data-block-id` in the artifact is correct and load-bearing. This constrains only sentences aimed at the member (ADR-365 D5, preserved verbatim).

## 5. D2 — Lanes only; the connector is a different consumer

`mcp_server` composes the workspace-mechanics clauses (filesystem model, citation, attribution, format) and **not** this one. Those describe *how the commons works* and are true for any principal. Register is about **who is reading the reply**, and for a connector that reader is inside someone else's client, whose host already owns its own voice. Shipping our conversational style there would be YARNNN dictating tone to Claude Desktop.

The seam is real and stated so a future session does not "fix" the omission: if a connector surface ever renders replies *in yarnnn's own chrome*, the clause ports on the same axis the citation rule did (ADR-617 D2).

## 6. What this ADR does NOT do

- **No length limit.** Measured verbosity is unremarkable; a cap would be a rule without a receipt (ADR-306 — an instruction needs an observed failure).
- **No deterministic rewriting** of model prose. ADR-365's own lesson is that the lever for *composed* surfaces is deterministic Python (D3, retained) and the lever for *free prose* is a structural directive. This is the second kind.
- **No change to `toolLabels.ts`.** That layer already works; it is cited as the precedent, not amended.

## 7. Validated — the A/B, run (2026-09-04)

The gate proves the clause is *composed*; only an experiment proves it *works*, and ADR-365's own history is why that distinction is enforced here: its first directive was ratified, shipped, and then **falsified**. So `api/scripts/operator/probe_adr638_register_ab.py` runs the same experiment on this surface — ARM A the live clause, ARM B the identical frame with it stripped, on the operator's own task shape (an artboard pass reported back, with the internal grammar deliberately handed to the model in the tool result).

| | mean leaks/reply | clean replies | mean words |
|---|---|---|---|
| **A — clause present** | **0.00** | **9/9** | **63** |
| B — clause stripped | 2.08 | 1/9 | 177 |

Reproduced across two runs (3+6 trials/arm, Sonnet 5). Leak markers are the four measured in production, counted deterministically — no judge.

Arm A, verbatim: *"Fixed it — the headline now sits clearly above the photo instead of competing with it. I moved it down a bit and made it bigger so it reads as the anchor…"*
Arm B, verbatim: *"I made the headline bigger (96px → 108px) and pushed it further down the artboard…"*, and elsewhere block ids and `data-*` names.

⭐ **The length drop was not asked for.** §6 deliberately set no length limit, and replies still fell ~64% (177 → 63 words). "Lead with what changed, then why" removes the recap; brevity is its *consequence*, not a rule. Had a word cap been added, this effect would have been wrongly attributed to it.

⚠️ **What this does not establish**: the count is a proxy. ADR-365 D2 scored as noise on word-frequency and 365b later scored +49–79% on an LLM judge over structure — a metric can miss a real effect, and it can also flatter one. This shows the clause eliminates the *measured* leak on the *measured* task; it does not score prose quality.

## 8. Open

- **Per-member verbosity presets** (the output-styles analogue) — named in §3, unbuilt.
- **Production re-measure.** The 120-reply corpus that motivated this ADR is the pre-clause baseline. Re-running that same count over replies written after this ships is the real receipt, and it needs live traffic rather than a probe.
