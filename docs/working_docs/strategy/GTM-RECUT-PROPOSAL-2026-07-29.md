# The Persona/ICP and GTM/Activation Re-cut — Drift Ledger and Proposal

**Date**: 2026-07-29
**Status**: Proposal for operator ratification. No document rewritten yet.
**Scope**: `NARRATIVE.md` · the persona/ICP document family · `GTM_POSITIONING.md` · the activation document family.
**Trigger**: [ADR-457](#) §10.3 deferred item — *"NARRATIVE/GTM lead re-cut — external copy shifts from substrate-portability-led to desk-led-with-mechanism; its own pass, operator eyes on wording (ESSENCE v16 lands the internal canon now; the external story follows)."*

**Evidence read**: ESSENCE v16 · SERVICE-MODEL v2.0 · FOUNDATIONS (2026-07-18) · NARRATIVE v5 · GTM_POSITIONING v4 · SITE-COPY-SPEC-v1 · ICP_ANALYSIS_APRIL_2026 · ICP Deep-Dive v2 · ACTIVATION_100USERS v3 · monetization/STRATEGY.md · ADRs 334, 366, 380, 382, 396, 404, 413, 416, 435, 437, 445, 454, 457, 460, 465, 472, 486, 488, 490, 491, 492, 493 · IR Deck (2026-07-22, 19pp) · git history of `docs/` since 2026-06-10.

All quoted lines were re-verified against the repo before this draft. Where a claim rests on paraphrase rather than a quotable line, it is marked.

---

## 0. The one-line answer

ADR-457 named the re-cut as **substrate-led → desk-led**. That is true, and it is the smaller half.

In the fifteen days since ADR-457, five more ADRs (465, 486, 490, 491, 492/493) moved the ground again, and what they collectively did is bigger than a lead change:

> **The ICP inverted.** Every GTM and persona document you hold describes a **solo operator of a bounded operation**. Every ADR since 445 describes a **workspace owner who invites people**. No GTM document records this.

ADR-465 states it without hedging:

> *"The moat only turns on with a second principal. … Attribution across a **single** principal is trivial: **a one-member commons is a diary.** `trace`, correction-compounding, 'diverge privately, settle publicly' (ESSENCE v16) are all **latent until someone else is in the room.** Therefore: **The act that creates the second principal is the act that switches the moat on. It is not a peripheral convenience; it is a constitutive act of the product.**"*

And ADR-490 prices against that reading:

> *"the product's proof moment IS inviting someone into the commons, and a paywall on the *first* invite taxed exactly that moment."*

Your live GTM doc (v4 §2) says the buyer is *"someone with **something that's theirs to run**, that they **can't be continuously present for** — and who **refuses to let it reset**."* That person, taken literally, is a diary owner. The three qualifiers were built to filter *for* solitude — *theirs to run*, *can't be present*, *refuses to reset* — and the product's moat now requires the opposite entry condition.

That is the sentence the whole re-cut turns on. Everything below is the accounting.

---

## 1. Document inventory — what is current and what is not

| Document | Version / date | Eras behind | Verdict |
|---|---|---|---|
| `docs/ESSENCE.md` | v16 · 2026-07-14 | current | **Keep.** One deliberate hole — §Canonical Positioning still carries the ADR-380 §5 *substrate-led* lead, parked by ADR-457 §10.3 for this pass. Closing it is this proposal's job. |
| `docs/architecture/SERVICE-MODEL.md` | v2.0 head · v1.6 body · 2026-07-14 | head current | **Head keep, body stale.** Revision history stops at v1.6 (2026-04-20); ~85% of the body is cockpit/five-destinations/operator-era. Not a GTM doc, but it is a source people quote from. |
| `docs/architecture/FOUNDATIONS.md` | 2026-07-18 (DP29 v9.18) | current | Keep. |
| `docs/NARRATIVE.md` | **v5 · 2026-06-10** | 4 | **Full re-cut → v6.** Beat 1 = self-audit/ratings-agency; Beat 3 = standing delegate; Beat 6 = high-ACV per-operation. All three now false. |
| `docs/working_docs/strategy/GTM_POSITIONING.md` | **v4 · 2026-06-10** | 4 | **Full re-cut → v5.** §1 lead, §2 ICP, §5 pricing, §6 activation all superseded. §3 act-shape map is the only salvageable section, and it needs re-cutting too. |
| `docs/working_docs/go-to-market/SITE-COPY-SPEC-v1` | v1 2026-06-10, patched 2026-07-04 | 3 | **Supersede with v2.** Its own staleness banner already asks for this. Prices $149/$299/$499 per *operation*; "the workspace itself is never paid" is now exactly backwards. |
| `docs/working_docs/strategy/ICP_ANALYSIS_APRIL_2026.md` | 2026-04-01 | 6+ | **Archive.** Diagnoses an "automation paradox" for a product ("five domain experts", roster, deliverables) that no longer exists. |
| `docs/working_docs/strategy/YARNNN - ICP Deep-Dive v2.docx` | **v2 · February 2026** | 8+ | **Archive.** Primary profile = "The Multi-Client Consultant, 3–8 clients, $19/mo, Hook B: Reports that write themselves." Never founder-validated (every table still says "Not yet"). |
| `docs/working_docs/go-to-market/ACTIVATION_100USERS.md` | v3 · 2026-04-01 | 6+ | **Archive.** Assumes `/setup`, a five-expert roster, "TP", tasks-as-unit. All deleted (ADR-437 A, ADR-460, ADR-231). Every tracking table is empty — v3 was never run, same failure it diagnoses in v2. |
| `docs/monetization/STRATEGY.md` | 2026-07-01 | 2 pricing regimes | **Supersede.** Predates ADR-445 (seats) and ADR-490 (PAYG). Still says 2× markup and $0/$15/$45 allowances. No seat, member, or principal concept appears in it. |
| **IR Deck (2026-07-22, 19pp)** | current-ish | mixed | **Product chapters are right; ICP and Pricing slides are dead.** Detail in §3.5. |

**The pattern, and the structural cause.** Your architecture canon (ESSENCE, FOUNDATIONS, ADRs) is updated within days of every decision. `docs/working_docs/strategy/` has had **zero commits since 2026-06-10**. In that same window — 2026-06-10 to today — **168 ADRs were added** (ADR-330 through ADR-501), including three that re-cut the product's identity and five that re-cut its price.

Only two paths under `docs/working_docs/` changed at all since June 11: the site-copy spec (2026-07-04, an ADR-404 commons re-centre) and an IR deck binary. Everything else migrated: the live GTM thinking now lives in `docs/adr/` (404 commons-first launch · 437 activation · 457 service model · 465 share · 486 Radar · 490 pricing) and `docs/monetization/` (`PRICING-CONSOLIDATION` · `UNIT-ECONOMICS` · `METERING-CARVE`, all 2026-07-01), plus two June design docs (`marketing-interop-pivot-rewrite-2026-06-26`, `marketing-interaction-design-2026-06-29`).

That is the real failure mode, and it is worth naming before any rewrite: **strategy stopped being written in the strategy folder.** It kept being *decided* — in ADRs, at ADR velocity, with ADR rigour — but the documents whose job is to hold the external story stopped receiving it. A v-next GTM doc that does not solve for this will be stale again by September.

---

## 2. The four shifts that force the re-cut

### Shift 1 — The felt product: substrate-that-follows-you → a desk you work at

**Was** (ESSENCE v14.2 / ADR-380 §5, still the live external lead): *"the authored, attributed, portable substrate + `trace`."* Your context follows you into other AIs. The user is largely absent; Freddie tends the record.

**Now** (ADR-457, ESSENCE v16): *"the backdrop hum did not disappear — it was demoted from product identity to product floor."* The record is the moat; the desk is the product.

> ADR-457 §1: *"a settlement layer generates trust, not sessions."*

**And the desk sentence has already moved past ADR-457 — twice, in opposite directions, within four days.** ADR-486 (2026-07-24) amends it:

> *"Desk sentence, **once the app is real**: Chat thinks, Studio and Images make, Radar watches — two hands and a watchman over a commons that remembers."*

Then 2026-07-28: Radar unveiled (`launcher_tier: primary`, `default_pinned: True`), and Images went the *other* way — ADR-488 re-tiered it `primary → search-only` and out of the default Dock, *"the app went INTERNAL pre-beta."*

So the shipped desk today is **Chat · Studio · Files · Radar**, with Images built but hidden. Not two verbs, not ADR-486's sentence either. **This is a live problem for any copy pass**: the desk's own composition changed three times in fourteen days, and ADR-486's amended sentence — the most recent canonical phrasing — names an app the operator has since hidden. GTM v5 needs a formulation that survives an app moving in or out of the Dock, which argues for naming **the verbs and the commons**, not the app roster.

**What this kills**: NARRATIVE Beat 3 ("the workspace + the standing delegate experience"), GTM v4 §1 ("A standing delegate for the operation you can't be present for"), and every piece of copy where the user is described as *supervising* rather than *working*.

**What survives**: the mechanism vocabulary. *Owned, attributed, judged against what actually happened* is still the right discipline — ESSENCE v16 preserves it, and the incumbents still can't say it.

---

### Shift 2 — The ICP: the solo operator → the second principal

This is the shift with no GTM record at all. The chain:

| ADR | Date | What it did to the buyer |
|---|---|---|
| **404** | 07-05 | The commons-first launch — the workspace is re-centred as something a team joins, not a single operator's console. |
| **445** | 07-12 | Seat = a human head. Two named buyers: *"Solo (N=1) … Team (N≥2) … the OpenAI/Anthropic Team shape a team already understands."* Explicitly *"accepts solo = low-revenue by design and bets revenue on teams (seats) + heavy usage."* |
| **465** | 07-18 | *"a one-member commons is a diary"* — the second principal is **constitutive**, not a convenience. A user now owns **zero-or-one** workspace; a member-only principal is a first-class user. |
| **490** | 07-28 | Two humans free per workspace; the free→paid boundary is the **3rd human**, because *"the product's proof moment IS inviting someone into the commons."* |
| **491** | 07-28 | *"the deciding variable: **members are real now** (seats live, invites shipping)"* — Billing/Usage moved behind a **workspace** (org-settings) door on the ChatGPT/Claude Team convention. |
| **492** | 07-28 | *"chat's first-class capability is the **multi-human × multi-LLM conversation** over the commons."* The new-chat door is **person-first**. `private|shared` retired as *"species law in substrate costume."* |
| **493** | 07-28 | Projects as the **co-work state desk**; the work-unit is *"a declaration with an owner"*, species-blind across humans and agents; My-Work as a per-viewer derivation. |

**What this kills**:

- GTM v4 §2's three qualifiers (*theirs to run · can't be present · refuses to reset*) as the **whole** ICP. They still describe a real willingness-to-pay filter — they no longer describe the unit of the product.
- The "range proof" list (A&R · PM · solo founder · trader · partnerships lead) as a list of *individuals*. Under ADR-465 each of those is now the **first seat of a two-seat commons**, and the second seat is where the product turns on.
- SITE-COPY-SPEC's vertical chips (*a newsletter · a portfolio · a shop · a pipeline · a book of business*) as the identity claim. Every one of those nouns names something one person runs alone.
- The IR deck's ICP slide (17), verbatim: *"THE FELT PAIN · SAME PERSON, LOTS OF DIFFERENT JOBS · theirs to run · can't be present · refuses to reset."* That is GTM v4 §2 rendered as a slide — and slide 13 of the same deck says *"Multi-principal is built today … Write from any principal — it lands in one owned workspace, each author signed."* **The deck contradicts itself four slides apart.**

**The honest new frame** is not "teams instead of solos." It is a **two-stage ICP**, which no current document has:

- **Stage 1 — the founding principal.** Still recognizably the v4 psychographic: a person with work that's theirs, that they refuse to let reset. They arrive alone. Their first value is real but latent (a diary that remembers).
- **Stage 2 — the second principal.** A human colleague, or an AI colleague reaching in through the interop face, or a shared artifact recipient. This is where `trace`, correction-compounding, and *diverge privately / settle publicly* become **felt** rather than **claimed** — and it is where the pricing model says the business is.

The GTM job is no longer "find the operator." It is **"find the operator, then find the act that makes them add a second principal within the first session."**

---

### Shift 3 — The pricing axis inverted, and the motion statement inverted with it

| Regime | Doc | Unit | Price |
|---|---|---|---|
| ADR-334 (2026-06-10) | GTM v4 §5, SITE-COPY-SPEC | a **running operation**, tiered by delegation | $149 / $299 / $499 per operation/mo |
| ADR-396 (2026-07-01) | monetization/STRATEGY.md | balance + allowance | Free / $19 / $49, allowances $0/$15/$45, 2× markup |
| ADR-445 (2026-07-12) | — | seat (human head) × pooled meter | owner free, $20/additional human |
| **ADR-490 (2026-07-28)** | **live** | **human head + PAYG** | **2 humans free · $20/head beyond · usage at cost × 1.30 · allowance retired · no solo plan to buy** |

Three consequences your GTM docs have not absorbed:

1. **"Seat" is overloaded three ways in live documents**: a human head (445/490 — authoritative), a running program at $149–$499 (SITE-COPY-SPEC — dead), an AI persona entity (ADR-382 — retired as an entity class by ADR-460). External copy must use exactly one.
2. **"The workspace itself is never paid"** (SITE-COPY-SPEC) is now backwards. ADR-416 §58: *"**The billing unit is the workspace, not the user. Human seats scale the tier.**"*
3. **The motion statement is inverted.** GTM v4 §5 and SITE-COPY-SPEC both say: *"premium, high-ACV, low-velocity, expansion-led … Hundreds of operators paying real money is a real business — never a volume play."* Under ADR-490 the pricing axis is **headcount**, the margin on usage is **30%**, the first two humans are **free**, and there is **nothing for a solo user to buy**. That is a volume-and-expansion shape — closer to Slack/Figma than to a $500/mo vertical seat. ADR-445 states the bet plainly: *"a solo power-user with a rich, valuable workspace pays little."*

This is the single largest unforced contradiction in the doc set: **the strategy docs describe a high-ACV business the pricing model can no longer produce.**

---

### Shift 4 — Activation stopped being onboarding and became a share link

**Was** (ACTIVATION_100USERS v3, SITE-COPY-SPEC `/how-it-works`): ad → landing → signup → meet your roster → connect Slack/Notion → assign first task → first output → upgrade. Five-step ceremony.

**Now**:

- **ADR-437** (07-10) deleted `/setup` in full — *"delete, not repair"* — and reframed the question from *"what does onboarding look like"* to *"**how does a stranger become an activated principal in a commons**."* Two channels only: **cold discovery** (needs a deliberate empty state that teaches the moat on contact) and **invited/shared** (needs a robust accept surface).
- **ADR-465** (07-18) then re-classified Share out of activation entirely: *"Share is **re-cut from 'Phase D of an activation ADR' to a system primitive**."* It gives the loop end-to-end:

  > stranger clicks `/s/{token}` → signup (no workspace auto-minted) → `/s/{token}` → broad member grant → lands **inside someone else's populated commons, on the shared artifact, with `trace` visible** — *"the moat on contact."*

  And names the interop leg: *"An external LLM working in a member's session can `recall` an artifact and then `share` it to a colleague, who lands on `/s/{token}` and becomes a principal — **the viral loop running through the interop door**."*
- **ADR-492** (07-28) made the chat door **person-first**: *"'New chat' = pick *whom* you are talking to."*
- **ADR-486** (07-24/28) set the demo discipline: *"**Consumption guard**: accumulation is never the demo. The app leads with briefs (derived, cited, readable), never folder listings or counts. **Era-1's failure was accumulation nobody felt.**"*

**What this kills**: both of GTM v4 §6's first-session assets.
- *"Correction compounds"* (fix one file → watch artifacts improve) is now fenced by ESSENCE v16 as a **staged ledger moment**, explicitly *"never the ambient experience."*
- *"The retrospective audit"* (ingest an existing track record, reconcile past decisions) has no substrate to run on: ADR-414/437 made genesis **empty**, and a new workspace has zero recurrences until someone authors one.

**What replaces it** is not a demo — it is a **loop**: the share link is both the activation act and the growth act, and the accept surface is the landing page.

---

## 3. Drift ledger — what is now false, line by line

### 3.1 `NARRATIVE.md` v5

| § | Claim | Status |
|---|---|---|
| Macro | *"Platforms build delegates. They will not build the layer that holds delegates accountable"* — the ratings-agency thesis | **Demoted.** ADR-380 §5 scoped Rung-2 judgment out of the vision; ADR-382 is a name-only placeholder; ADR-460 retired the entity class. The thesis is defensibility ammunition, not the spine. |
| Beat 1 | *"Every platform now sells you a delegate … the same vendor that builds the delegate grades the delegate"* | **Wrong problem statement for the current product.** The deck (07-22) already replaced it: *"companies keep their own private copy, you don't — so it never really becomes yours."* |
| Beat 3 | *"the experience is the standing delegate … **And you work inside YARNNN.** The cockpit shows what's running…"* | **Dead.** Home/cockpit deleted (ADR-435). The experience is Think · Make · Watch. |
| Beat 3 | *"You set the delegation dial — manual, bounded, autonomous"* … and GTM v4 §5's *"the trust dial **is** the pricing axis"* | **Orphaned.** ADR-334 + ADR-366 deliberately fused the safety dial and the pricing dial — ADR-366:74: *"breadth=mode means the product's pricing dial and its safety dial are the same dial."* Then ADR-396 → 445 → 490 replaced that pricing model entirely. The dial survives as governance (ADR-491 relabels the pane **"System agent"** — *"copy that says whose dial it is"*); it no longer prices anything. Any copy selling delegation levels is selling a dead SKU. |
| Beat 5 | *"Per-workspace sovereignty — your asset is yours; **no cross-workspace learning**; blast radius is one operator"* | **Now reads as a limitation.** Under a multi-principal commons the interesting property is that N principals share one attributed ledger. |
| Beat 6 | *"premium, high-ACV, expansion-led … never a $19/mo volume play"* | **Contradicted by ADR-490.** |
| Vocab | *"Standing delegate"*, *"the judgment seat"*, *"delegation dial"*, *"Create an Agent"* | Retired or re-meant. ADR-460: *"'Cast' is retired … The live words are the conventional ones: a **room**, its **members**, and you **invite** them."* ADR-492: *"the act vocabulary is **invite · keep · share**."* |
| Surface guide | *"IR deck (~16 slides): all six beats"* | The live deck is 19 slides in four chapters and does not follow the six beats. The rubric has already been abandoned in practice. |

**Only thing in v5 that fully survives**: the mechanism-discipline rule — *"capability adjectives never appear without their mechanism."* Keep it verbatim into v6.

### 3.2 `GTM_POSITIONING.md` v4

| § | Status |
|---|---|
| §1 Core positioning | **Replace.** Lead, frame, USP, contrast hook, umbrella hero all built on standing-delegate + judgment-seat. |
| §2 The ICP | **Replace with a two-stage ICP.** The psychographic survives as the *founding principal's* profile; it is no longer the whole model. §2's own resolved open item ("the noun varies by vertical; the verb is universal — *I run a ___*") is a **solo** self-identification and needs a companion for the invite moment. |
| §3 Act-shape map | **Re-cut, partly salvageable.** The Artifact/Transaction/Message taxonomy still describes real work shapes. But: Transaction (trader/store-operator) depends on the Rung-2 layer ADR-380 §5 put out of the vision; and the map has no row for the act the product now leads with — **think → settle**. Its competitive caveat on the artifact class (*"the least differentiated terrain … artifact ground truth is the slow kind"*) is still correct and now more urgent, since Studio is the deep-investment app. |
| §4 Competitive landscape | **Mostly holds, needs a fifth row.** The four competitor classes still map. Missing: the *shared-workspace* class the deck's slide 16 already names (Notion · Slack) — which is where a multi-principal commons actually competes now. |
| §5 Motion & pricing | **Delete and rewrite.** Superseded twice. |
| §6 Activation | **Delete and rewrite.** Both first-session assets superseded. |
| §7 Open items | Items 1–3 marked RESOLVED are all re-opened by the shifts above. Item 4 (lead-vertical call) is still open and is now the wrong question — the question is lead *use-case for a pair*, not lead vertical for a solo. |

### 3.3 The persona/ICP family

There is no live persona/ICP document. There are three dead ones (Feb, Apr, Apr) and one live *section* (GTM v4 §2–§3). That is the actual finding: **the ICP has no owning document**, which is why it drifted invisibly while ADRs re-cut the buyer four times.

`ICP Deep-Dive v2` (Feb) is worth reading once before archiving, for one reason: it is the only document in the set that contains **demographics, tool stacks, current AI spend, switch triggers, and decision-influence channels**. Every later ICP artifact is psychographic-only. The v-next ICP doc should recover that concreteness — for the *pair*, not the individual.

### 3.4 The activation family

`ACTIVATION_100USERS` v3 assumes: `/setup` (deleted in full, ADR-437 Phase A), a pre-scaffolded five-expert roster (ADR-460 retired the framing), "TP" as orchestrator (renamed then dissolved), tasks-as-the-activation-unit (ADR-231 sunset the task abstraction; the DB scheduling index survives, the user-facing unit does not), $19/mo Pro with unlimited tasks (ADR-490), 90 days free (gone). Nothing is recoverable except the **discipline**: budget-boxed channel tests with a read-the-results matrix and an empty tracking table that someone must actually fill.

Its most useful line is its own confession — *"Neither was executed — the tracking tables are empty"* — which repeated in v3. **Any v-next activation doc should be shorter and instrumented, or it will be the third unexecuted plan.**

### 3.5 The IR deck (2026-07-22)

The deck is **ahead** of the GTM docs and **behind** the ADRs. Precisely:

**Right, and already desk-led** — chapters 01–02 lead with ownership (*"companies keep their own private copy, you don't"*), the two-camp market read (model makers vs agent-memory startups, *"what neither builds"*), and a four-part product tour: **Think `/chat` · Make `/studio` · Remember `/files` · Intelligence `/agents`**. Slide 9's *"composed from — open any source / you · Aug 2 / your agent · Aug 5 / Claude · Aug 6"* is the single best moat rendering in any yarnnn artifact: it shows multi-principal attribution as a picture rather than a claim.

**Already dead, six days after the deck was made** — slide 18 pricing: *FREE $0 · STARTER $19 · PRO $49 · each plan includes monthly usage · Enterprise: seats + pooled meter*. ADR-490 (07-28) retired the allowance, retired the solo plan, made two humans free, made every workspace PAYG at 1.30×, and moved seats out of "Enterprise" into the base model. **The pricing slide must be rebuilt before the deck goes out again.**

**Self-contradicting** — slide 13 (*"multi-principal is built today … each author signed"*) vs slide 17 (*"same person, lots of different jobs · theirs to run · can't be present · refuses to reset"*). Slide 17 is GTM v4 §2 rendered as art. Under ADR-465 it undercuts slide 13 and slide 9 — the two strongest slides in the deck.

**Drifting from canon** — slide 7's *"personas, ready out of the box"* is the right layman instinct (ADR-460: *"LLM-routing is simply NOT a laymen intuitive concept. Pre-configured Agents IS. … nobody routes. You talk to someone."*), but "persona" is precisely the word ADR-460/382 retired as an entity class. Use ADR-460's live vocabulary: **a room, its members, and you invite them.** Also: the deck's product quad (Think · Make · Remember · Intelligence) predates the 07-28 desk reshuffle — Radar unveiled, Images hidden. The next version needs either a fifth chapter for Radar or a re-cut that names verbs rather than surfaces.

---

## 4. Proposal — what each document becomes

### 4.1 `NARRATIVE.md` → **v6, "the desk over a shared commons"**

Six beats, re-cut. The change is not cosmetic: **the problem statement, the product beat, and the motion beat all change**, and the moat beat gets stronger rather than weaker.

- **Beat 1 — The problem.** Retire the ratings-agency opener; promote the deck's ownership read. *Every AI you use keeps its own private copy of your work. None of them is yours, none of them talks to the others, and none of them can show you who wrote what.* Concede incumbent capability fully (unchanged discipline from v5). The self-audit argument moves to Beat 5 as defensibility ammunition, where ADR-380 §5's conservatism actually permits it.
- **Beat 2 — Proof of demand.** Keep the two-stream structure. Stream 1 becomes the funded memory-layer category (Mem0/Zep/Cognee — deck slide 3 already carries this: *"Demand is proven — Mem0, Zep and Cognee are funded on it. What's missing isn't more memory; it's the shared layer."*). Stream 2 becomes the co-work signal rather than the governance-anxiety signal.
- **Beat 3 — Meet the product: the desk.** Think · Make · Watch over a commons that remembers, plus **settle** as the verb that makes thinking land. Name the verbs, not the app roster — the roster changed three times in the last fortnight (§2, Shift 1) and a beat pinned to it will need rewriting every sprint. The Day-1 proof is **not** "fix a file, watch artifacts improve" — it is *keep this → it lands attributed → open any source*.
- **Beat 4 — The insight.** Recut. v5's *"execution commoditizes; context and judgment compound"* narrows to the surviving half: **execution commoditizes; the shared, attributed record compounds.** Judgment is the deferred deepening (ADR-380 §5), not the revelation.
- **Beat 5 — The moat.** Strongest beat, mostly intact, plus the new load-bearing sentence: *the moat turns on with the second principal.* This is where the ratings-agency argument, total attribution, the invocation contract (ADR-413), and anti-fragility to model churn all live. Deck slide 9 is the visual.
- **Beat 6 — The opportunity.** **Rewritten against ADR-490.** Two free seats, $20/head, thin metered margin, invite-driven expansion — a land-and-expand shape, not a high-ACV vertical-seat shape. Say so plainly; the current copy claims a business the price list cannot produce.

**Add a new section v5 does not have: "The honest open question."** ADR-457 D6 requires it — *"The acquisition wedge is an open question, named honestly … grounding and settling are retention features. GTM must not pretend otherwise."* A narrative doc that hides this will produce copy the product cannot cash.

### 4.2 The persona/ICP family → **one new doc: `ICP.md` (a two-stage model)**

Archive `ICP_ANALYSIS_APRIL_2026.md` and `ICP Deep-Dive v2.docx`. Lift the live ICP out of GTM §2–§3 into a doc that owns it, so it can drift visibly next time.

Proposed structure:

1. **The unit of the product is a commons, not a person.** State ADR-465's line as the doc's premise.
2. **Stage 1 — the founding principal.** The v4 psychographic survives here, sharpened: *theirs to run · can't be present · refuses to reset*, plus the willingness-to-pay wince. Recover the ICP-Deep-Dive-v2 concreteness for this person (demographics, current AI spend, tool stack, switch trigger, decision-influence channels) — but validated this time, not hypothesised.
3. **Stage 2 — the second principal, and its three species.** This is the new material and the doc's reason to exist:
   - **a human colleague** (co-founder, contractor, client, collaborator) — the seat model's buyer;
   - **an AI colleague** in a room (ADR-492's multi-human × multi-LLM conversation) — free, unlimited, and the fastest path to a two-principal ledger;
   - **an artifact recipient** who arrives via `/s/{token}` (ADR-465) — the viral leg.
   For each: what makes it happen, how fast, and what it costs.
4. **The pair archetypes.** Replace the solo range-proof list with pairs, because the pair is what the product now serves. Candidates to pressure-test: *founder + contractor* · *consultant + client* · *analyst + their own AI colleagues* · *two co-founders* · *creator + editor*. This is the section that needs real conversations, not deduction.
5. **The anti-ICP, named.** The person for whom yarnnn is a diary: works genuinely alone, shares nothing, invites no one. Under ADR-465 they are a real user with a latent moat and near-zero revenue. Deciding whether to *serve* them, *convert* them, or *not target* them is a top-level strategy call this doc should force. ADR-445 has already implicitly answered ("solo = low-revenue by design") — GTM should say it out loud or overrule it.
6. **Vocabulary.** One "seat." The layman words are ADR-460/492's: **room · members · invite · keep · share**; **hub · sweep · brief** (ADR-486); **Projects** (ADR-493 D7).

### 4.3 `GTM_POSITIONING.md` → **v5**

Same skeleton, four sections replaced:

- **§1 Core positioning** — desk-led with mechanism. Lead candidates to test (all need operator eyes; none are final):
  - *"The workspace where you and your AI work together — and it's yours."*
  - *"Every AI keeps its own copy of your work. This one is yours, and everyone in it signs their name."*
  - *"Think, make, and remember in one place — with everyone you work with, human or not."*
  The mechanism discipline from v4 is preserved verbatim: never a capability adjective without *owned, attributed, traceable*.
- **§2 ICP** — becomes a pointer to `ICP.md` plus the messaging cut per stage.
- **§3 Act-shape map** — re-cut with a fourth row for **think → settle**, and Transaction demoted to reflect ADR-380 §5.
- **§4 Competitive** — add the shared-workspace row (Notion/Slack). Keep the posture rule; it is the best line in the doc.
- **§5 Motion & pricing** — rewritten against ADR-490. Include the seat-price ladder honestly: nothing to buy at 1–2 humans; $20/head at 3+; usage PAYG at 1.30×; the upgrade moment **is** the third invite.
- **§6 Activation** — becomes the **growth-loop** section (below).
- **§7 Open items** — reset, seeded from §5 of this memo.

### 4.4 The activation family → **`GROWTH-LOOP.md` replaces `ACTIVATION_100USERS.md`**

The reframe: ADR-437 asked *"how does a stranger become an activated principal in a commons"*; ADR-465 answered it with a primitive. The doc should be built around the loop, not around a channel plan.

**The loop, as canon already defines it:**

```
someone's artifact  →  /s/{token}  →  signup  →  broad member grant
      ↑                                                    ↓
   they share  ←  they keep something  ←  they work in a populated commons
```

Four things it must specify:

1. **Cold channel (ADR-437 D3)** — the empty state is the onboarding. Its job, quoted: *"A cold user who does nothing has learned nothing; a cold user who drops a file or states a fact and **watches it placed, attributed, and recallable** has seen the moat on contact."* The Phase-C empty-state design pass is still open.
2. **Warm channel (ADR-465 D2/D3)** — the accept surface is the landing page, and the artifact is the pitch. Two grant shapes at share time; view-only exists specifically for the *"I just want them to see this deck"* case.
3. **The activation metric.** Not signups, not tasks. **Time-to-second-principal**, and the share→accept conversion rate. Everything ADR-490 prices runs off this number.
4. **The instrumented falsifiers, carried in rather than around.** Three are already armed and two are GTM-blocking:
   - ADR-457 D8.2 / ADR-460 §8: *settle goes unused after honest staging → **"GTM must not lead with it."***
   - ADR-486 D8.2: *briefs go unopened → **"do not GTM-lead with Radar."***
   - ADR-457 D8.3: *MCP traffic dwarfs desk traffic → the hum is the true wedge; investment priority flips back.*
   A GTM doc written today that leads with settle or Radar is writing a cheque against an unresolved falsifier. Name the dependency in the doc.

Keep from v3 only: the budget-boxed test discipline, the read-the-results matrices, and the empty tracking tables — with a commitment to fill them, since two consecutive versions were written and never run.

### 4.5 Two dependent artifacts

- **`SITE-COPY-SPEC-v2`** — its own staleness banner already nominates a v2. It cannot be written before GTM v5 lands.
- **The IR deck** — rebuild slide 18 (pricing, per ADR-490) and slide 17 (ICP, per §4.2) before it goes out again. Slides 9 and 13 are the deck's strongest assets and slide 17 currently argues against both.

### 4.6 One small canon correction that belongs to this pass

`ESSENCE.md` §Canonical Positioning still reads *"The authored, portable substrate leads — defended by `trace`; the judgment layer is the future deepening"* (the ADR-380 §5 lead), while §The Desk two sections above says the felt product is the desk. ADR-457 §10.3 parked this deliberately, waiting on this pass. When GTM v5 ratifies, §Canonical Positioning should be re-cut to the desk-led-with-mechanism form and stamped v17. Otherwise ESSENCE will keep handing external writers the retired lead.

---

## 5. What you have to decide before anyone writes copy

These are genuine forks, not drafting details. Each one changes what the documents say.

1. **Solo or pair as the marketed entry?** ADR-465 says the moat turns on with the second principal; ADR-445 says solo is low-revenue by design. Do we (a) market to the pair from the first impression, (b) market to the solo and engineer the invite as the activation event, or (c) market to the solo whose *second principal is an AI colleague* — which needs no invite, no seat, and no other human? **(c) is the cheapest loop and the least explored**, and ADR-492's person-first door plus ADR-460's out-of-the-box Agents already ship the machinery for it.

2. **Does the high-ACV motion survive?** It cannot survive unamended. Either the price model changes (seats are launch-test values in one config file, per ADR-490 §5) or the motion statement changes. Right now the docs claim one and the code does the other.

3. **What do we lead with, given two armed falsifiers?** Settle is the most differentiated act in the product and the one ADR-457 D8.2 says not to lead with until it's proven used. Radar is the most demo-able and carries the same conditional. That leaves the **shared commons + attribution** as the only unfenced lead — which is, not coincidentally, what the July deck already leads with.

4. **Radar's packaging.** ADR-486 §5 deferred it to R3; R3 shipped 2026-07-28 unveiled. Standing sweeps now draw the PAYG meter unattended with no packaging story. This is a live pricing debt, and *"30 briefs this month"* is the most subscription-legible thing in the product.

5. **The word "seat."** Three live meanings across live documents. Pick one for external use (recommend: a human head, per ADR-445/490) and purge the other two from all GTM surfaces.

6. **Is the vertical-chip strategy dead?** *A newsletter · a portfolio · a shop · a pipeline · a book of business* — every one names solo work. If (1) resolves toward the pair, these chips need replacing wholesale, and SEO strategy changes with them.

7. **Who owns the ICP document?** The proximate cause of this drift is that the ICP lived as §2 of a positioning doc rather than as a doc with its own version banner and maintenance trigger. Recommend `ICP.md` gets an ADR-style "update when" clause naming the specific ADR dimensions (Identity/Axiom 2, Purpose/Axiom 3) that force a re-read.

8. **How does GTM stop drifting?** The deeper cause is §1's finding: strategy is decided at ADR velocity and recorded nowhere the external story lives. Two options, and this needs a call rather than good intentions:
   - **(a) A GTM dimension on the ADR template.** Any ADR touching Identity (Axiom 2), Purpose (Axiom 3), or Channel (Axiom 6) must state its external-copy consequence in one line, the way ADRs already state their `Amends:` line. ADR-445 already does this voluntarily (its Phase 3 is a marketing-surface commit with a gate); ADR-490 does it by delegation (*"FE/marketing coherence rides ADR-491's commit"*). Making it structural costs one line per ADR.
   - **(b) A standing review.** A recurring pass over GTM docs against the ADR log. Cheaper to adopt, easier to skip — and the two unexecuted activation plans are the evidence for how that goes here.
   (a) is the recommendation. It puts the obligation at the moment of decision, where the context is, rather than at a later moment when someone has to reconstruct it — which is exactly the argument the product itself makes.

---

## 6. Sequencing

The docs form a cascade, and writing them out of order produces the drift again.

1. **Decide §5.1 and §5.2** (the ICP fork and the motion fork). Nothing else can be written honestly first.
2. **`ICP.md` v1** — the two-stage model. It is the input to everything downstream and the doc that does not currently exist.
3. **`NARRATIVE.md` v6** — beats, sequencing, thesis-timing rules, and the honest-open-question section.
4. **`GTM_POSITIONING.md` v5** — the language toolkit against v6's structure.
5. **`GROWTH-LOOP.md`** — the loop, the metric, and the falsifier dependencies.
6. **`ESSENCE.md` v17** — the one-paragraph §Canonical Positioning correction, closing ADR-457 §10.3.
7. **Deck slides 17–18, then `SITE-COPY-SPEC-v2`** — the external surfaces, last.
8. **Archive** with a redirect banner (not delete): `ICP_ANALYSIS_APRIL_2026`, `ICP Deep-Dive v2`, `ACTIVATION_100USERS`. Add a supersession banner to `monetization/STRATEGY.md` pointing at ADR-445 + ADR-490 + ADR-491 — it is the doc a pricing page would naturally be built from, and it is two regimes wrong.

Steps 2–5 are one working session's worth of drafting once step 1 is decided. Step 1 is a founder call and this memo does not make it.

---

## Appendix — the primary contradictions, one line each

| # | Live document says | Live canon says | Source |
|---|---|---|---|
| 1 | ICP = a solo operator of a bounded operation | *"a one-member commons is a diary"* — the second principal is constitutive | ADR-465 |
| 2 | $149/$299/$499 per running operation, tiered by delegation | 2 humans free, $20/additional head, usage PAYG at ×1.30, allowance retired | ADR-490 |
| 3 | *"The workspace itself is never paid"* | *"The billing unit is the workspace, not the user"* | ADR-416 §58 |
| 4 | Motion is high-ACV, low-velocity, never a volume play | *"solo = low-revenue by design … bets revenue on teams (seats) + heavy usage"* | ADR-445 |
| 5 | Lead = the judgment seat / standing delegate | Judgment is *"the deepening a workspace grows into, not the entry experience"* | ADR-380 §5, SERVICE-MODEL v2.0 |
| 6 | The user supervises from a cockpit | Home/cockpit deleted; the user works at a desk | ADR-435, ADR-457 |
| 7 | Onboarding = pick a program → write a constitution → connect | `/setup` deleted in full; entry is a flow, not a ceremony | ADR-437, ADR-465 |
| 8 | First-session asset = correction-compounds demo | The ledger is felt at *staged* moments, *"never as the ambient experience"* | ESSENCE v16 |
| 9 | First-session asset = retrospective audit of a track record | Genesis is empty; a new workspace has no track record to audit | ADR-414, ADR-437 |
| 10 | Deck: *"same person, lots of different jobs"* | Deck, four slides earlier: *"multi-principal is built today … each author signed"* | IR Deck 07-22, slides 13 & 17 |
| 11 | The desk has two verbs | Three, and the roster moved twice on 07-28 (Radar unveiled, Images hidden) | ADR-486, ADR-488 |
| 12 | "Personas, ready out of the box" | Persona retired as an entity class; the words are *room · members · invite* | ADR-460, ADR-382 |
| 13 | *"The trust dial **is** the pricing axis"* | The dial is governance only; the pricing model it belonged to is dead | ADR-366 §74 → ADR-396/445/490, ADR-491 |
| 14 | Strategy lives in `docs/working_docs/strategy/` | Zero commits there since 06-10; 168 ADRs added in the same window | git log |
