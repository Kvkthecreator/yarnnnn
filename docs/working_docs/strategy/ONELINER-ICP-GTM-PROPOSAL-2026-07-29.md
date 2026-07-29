# The One-Liner Canon, the ICP, and the GTM Rescope — Proposal

**Date**: 2026-07-29
**Status**: Proposal. Nothing ratified. §8 lists what needs an operator ruling and what needs a kernel ruling.
**Supersedes in intent**: GTM_POSITIONING v4 §1–§2, §5–§6 (bannered 2026-07-29).
**Reads from**: `ICP-ONELINER-DISCOURSE-2026-07-29.md` (the agenda) · `GTM-RECUT-PROPOSAL-2026-07-29.md` (the drift ledger).
**Source caveat**: the artifact *"Copy of IR deck design system update"* would not render under browser automation. This proposal is built on the **2026-07-22 IR deck (19pp)**, extracted in full. If the artifact's copy has moved, §7 is the section most likely to need revision.

---

## 1. The move that makes everything else fall out

The discourse agenda left one question open as the fork: **does "human + AI together" survive the ledger?** I'm proposing an answer, because the ICP and the GTM both hang on it and the evidence is one-sided.

### The answer: yes — but not the way it looks, and the difference is the whole strategy

ADR-460 is right and should not be softened:

> *"A named preset that runs as the member's hands **does not become a principal by acquiring a name.** The face is an Agent; the fact is your hands. … the ledger says `member:kvk via gemini/gemini-2.5-pro`."*

An Agent you address at the desk is **your hands**. It does not create a second principal. So the tempting shortcut — *"you already have AI colleagues, so you're already multi-principal"* — is false, and marketing it would be a claim the ledger contradicts.

**But ADR-445 enumerates the AI principal roles: `foreign-llm · a2a · own-agent · platform`.** An external LLM reaching into the commons over the interop face is a **genuinely distinct principal** — its own grant row, its own attribution line, its own entry in the revision chain. That is not a roadmap item. It ships. It is the MCP surface.

### The consequence

> **The second principal is not necessarily a person. It is most often a second *surface*.**

A solo founder who works at the yarnnn desk *and* pulls the same commons into Claude or ChatGPT already has a multi-principal ledger on day one. `trace` has something real to show. Correction-compounding is felt. ADR-465's *"a one-member commons is a diary"* is true — and the escape from the diary does **not** require an invite, a seat, or another human.

**The deck already drew this.** Slide 9:

> *"composed from — open any source · **you · Aug 2** · **your agent · Aug 5** · **Claude · Aug 6**"*

Three attributions, one of them an external LLM. That slide is the product, the moat, and the ICP in one picture, and it is the strongest asset in the whole corpus. The one-liner's job is to be that slide in words.

### What this costs, stated honestly

ADR-457 D5 demoted the interop face from product identity to product floor, and moved investment priority to the desk. **This proposal does not reverse that** — the desk is still where the product is experienced and where retention lives. What it says is narrower and specific: **the interop face is the acquisition channel, not merely the floor.** ADR-457 D6 already listed it among the unproven candidates (*"MCP-side capture funneling into the desk"*); this proposal promotes it from candidate to lead, and §8.3 names the falsifier that would kill it.

---

## 2. The one-liner canon — three slots, filled

Per the agenda's §3 frame: three labelled sentences, one per slot, replace-never-accumulate. Written into ESSENCE with the slot labels visible, so no future writer has to guess which of seven to quote.

### Slot 1 — The moat sentence (investors, internal discipline)

**Unchanged. Ratified by ADR-414 D1. Do not re-open.**

> **yarnnn is the system of record where human and AI work settles.**

Its job is to answer *why doesn't this commoditize*. It is correct, it is a position claim rather than a feature claim, and ADR-457 §1 already named its limit: *"a settlement layer generates trust, not sessions."* That limit is why it does not belong in slot 2.

### Slot 2 — The product sentence (the buyer, the site, the desk) — **PROPOSED**

> **yarnnn is the workspace you own — where you, your people, and every AI you use work on the same material, and every change is signed.**

**Hero form** (site, deck cover, one-line answer to *what is it*):

> ## Work with any AI. Own what comes out of it.

**Subhead** (carries the mechanism, per the discipline):

> One workspace for you, your team, and the AI you already use — every file attributed, every change traceable to whoever made it, human or not.

Why this and not the alternates:

| Rubric test (agenda §6) | How it passes |
|---|---|
| Names the unit correctly | *"you, your people, and every AI you use"* — true at N=1 (you + an external LLM), true at N=3 (a paid seat). The sentence does not have to change when the price does. |
| Survives an app leaving the Dock | Names no app. Radar in, Images out (2026-07-28) — the sentence is untouched. |
| Carries a mechanism | *"every change is signed"* / *"traceable to whoever made it"*. Ownership's mechanism is attribution, and this says it in words a layman owns. |
| Doesn't lead with an armed falsifier | No settle, no Radar, no briefs. |
| True of a free two-person workspace on day one | Yes — and true of a one-person workspace with one external LLM, which is the point of §1. |
| Layman-sayable | *"Work with any AI. Own what comes out of it."* No product noun to learn. |
| Separates from both camps | From model makers: *any* AI, not one vendor's. From memory startups: *what comes out of it* — work products, not recalled facts. |

**The alternates, and why they lose:**
- *"Every AI keeps its own copy of your work. This one is yours."* — the strongest **problem** line in the corpus (it is the deck's chapter 1). Keep it. Use it as the **hook**, not the one-liner: it sells against rather than for, and never says what you do all day.
- *"Think, make, and keep…"* — closest to ADR-457's internal canon, but *keep* is settle, and ADR-457 D8.2 fences it until instrumented.
- *"Co-work with AI and humans…"* — your own unprompted phrasing, and the most honest description of the thing. **Rejected on one ground only: the Cowork collision.** Anthropic ships a product called Cowork, in the same category, and it is one of the two camps the deck positions against. Using "co-work" as the lead noun hands them the category word. Keep the *idea* — it is what slot 2 says — and drop the *word*.

### Slot 3 — The recognition sentence (what the buyer says about themselves) — **PROPOSED**

GTM v4's *"I run a ___"* was correct for a solo operator of a bounded operation and does not survive §3's ICP. The replacement:

> **"I use three different AIs, and I'm the only thing connecting them."**

This is a recognition hook, not a search hook (same posture v4 correctly took). It does three things at once: names the fragmentation, names the person as the load-bearing element, and — critically — **self-selects for the plural-AI qualifier that predicts whether the moat can turn on at all** (§3).

---

## 3. The ICP — rescoped

### 3.1 The unit, and the three species of second principal

Replace the two-stage model in the drift ledger with **three stages mapped to three business functions**. This is the structure no existing doc has.

| Stage | Who arrives | Cost to yarnnn | Business function |
|---|---|---|---|
| **0 — The founding principal** | One human, at the desk | Free | The signup |
| **1 — An external AI** (`foreign-llm` / `a2a`, over MCP) | Day one, no invite, no seat | Free, unlimited (ADR-445) | **Activation** — the ledger becomes multi-principal; `trace` has something to show |
| **2 — Agents at the desk** (`Scout · Gemini` et al.) | Out of the box (ADR-460) | Free | **Engagement** — the daily use. *Honest caveat: these are your hands, not a principal. Never marketed as a colleague.* |
| **3 — A human colleague** (invite or `/s/{token}`) | 2 free, then $20/head | Seat price | **Revenue** — the 3rd human is the upgrade moment (ADR-490) |

Read down that column: **activation, engagement, and revenue are three different principals, and only the third one is a person.** That is the whole GTM in one table, and it dissolves the solo-vs-pair argument that was going to eat the discourse: you market to the solo, you activate on the second surface, and you monetise on the third head.

### 3.2 The qualifying triad — replacing v4's

GTM v4 filtered on *theirs to run · can't be present · refuses to reset*. Those three were built to select for solitude, and per ADR-465 solitude is the condition under which the product is a diary. Proposed replacement:

> **Plural · Consequential · Continuing**

- **Plural** — *they already use more than one AI.* **New, and the most important of the three.** It is simultaneously the fragmentation grievance (the hook), the entry condition for the moat (a second principal exists on day one), and the predictor of usage revenue (30% PAYG margin needs volume). No prior ICP doc has this qualifier.
- **Consequential** — *the output goes to someone who matters.* Survives from v4's *theirs to run* and the wince filter. This is the willingness-to-pay test.
- **Continuing** — *the work repeats or accumulates.* Survives from *refuses to reset*. This is the tenure test.

### 3.3 The anti-ICP, named

> **The single-AI user.**

If someone only uses ChatGPT, there is no fragmentation grievance, no second principal, and no reason to leave the vendor whose memory is already good enough. **yarnnn is a worse ChatGPT for that person.** This is a much sharper disqualifier than v4's implicit *hobbyist*, and it is falsifiable at the top of the funnel — one question on the landing page tells you.

Note what this does to ADR-445's accepted cost (*"a solo power-user with a rich, valuable workspace pays little"*): it stays true, but it stops being a worry. A plural, consequential, continuing solo user is a **high-usage** account under PAYG, and usage is the second revenue leg.

### 3.4 What to recover from the archived docs

The three ICP Deep-Dives (v1/v2/v3) are the only artifacts carrying concrete demographics — age, income, company size, current AI spend, tool stack, switch trigger, decision-influence channels. Every ICP artifact since is psychographic-only. **`ICP.md` should recover that concreteness for the plural-AI user**, with one addition none of them had: *which* AIs, and *how many*.

And all three ended with unanswered founder-validation questions. That is why they went stale — the architecture drift merely finished them off. §8.4 addresses this.

---

## 4. The GTM rescope

### 4.1 The motion — reconciled with the price list

GTM v4 and SITE-COPY-SPEC both claim *"premium, high-ACV, low-velocity, expansion-led … never a volume play."* ADR-490 cannot produce that business. The honest restatement:

> **Free-to-value, expand by head, with two revenue legs.**

- **Leg 1 — seats.** Two humans free; $20/head from the 3rd. Revenue scales with the invite, not with the deal.
- **Leg 2 — usage.** PAYG at cost × 1.30. Thin, so it needs volume — which is why **plural** is a qualifying criterion and not just a hook.
- **Shape.** Prosumer / small-team, land-free-and-expand. The comparable motion is early Figma or Linear, not a $500/mo vertical seat. ADR-445 already made this bet explicitly (*"accepts solo = low-revenue by design and bets revenue on teams (seats) + heavy usage"*); GTM has simply never said so out loud.

**Retire**: *"Hundreds of operators paying real money is a real business — never a volume play."* It describes a company the pricing model dissolved.

### 4.2 The acquisition wedge — proposed, and named as the open question ADR-457 required

ADR-457 D6 requires this be stated honestly rather than assumed:

> *"The acquisition wedge is an open question, named honestly … grounding and settling are retention features. Candidate wedges — multi-engine/BYOK economics, the shared team commons, MCP-side capture funneling into the desk — are plausible and unproven. GTM must not pretend otherwise."*

**Proposed wedge: the MCP door.** Four reasons, in order of strength:

1. **It is the only lead not fenced by an armed falsifier.** Settle is fenced (ADR-457 D8.2). Radar is fenced (ADR-486 D8.2). What remains unfenced is the shared commons and attribution — which is exactly what reaching yarnnn from another AI demonstrates.
2. **It is the only channel where the second principal arrives free.** No invite, no seat, no human. Per §1, that is where the moat turns on.
3. **The connector directories are distribution.** Being present where people already are — inside ChatGPT, Claude, Cursor — is a channel no GTM doc in the repo names. It is also the only channel that pre-qualifies for **plural** by construction: nobody installs a connector for an AI they don't use.
4. **The demo needs no tenure.** NARRATIVE v5's still-valid anti-pattern is *"never ask a stranger to imagine Day 90."* Reach a file from two different AIs and watch both attributions land — that is a sixty-second demo of the moat, on day one, with no accumulated history required.

**Sequenced role of each surface:**

```
MCP door  →  the desk  →  the share link
acquisition   retention    expansion
(free)        (free)       (paid at head 3)
```

### 4.3 The proof asset

**Slide 9 of the July deck, promoted from a slide to the central asset.** *"Composed from — open any source · you · Aug 2 · your agent · Aug 5 · Claude · Aug 6."* It shows multi-principal attribution as a picture rather than a claim, requires no tenure, and is the one thing a single-vendor host structurally cannot render. Everything else — site hero, demo video, first-session flow — should be a rendering of that one idea.

This also replaces GTM v4 §6's two dead first-session assets (*correction compounds*, fenced as a staged ledger moment; *retrospective audit*, which has no substrate on an empty genesis).

### 4.4 Deck consequences

| Slide | Action |
|---|---|
| Cover | Hero becomes *"Work with any AI. Own what comes out of it."* |
| Ch.1 problem | **Keep as is** — *"companies keep their own private copy, you don't"* is the best hook in the corpus. |
| **9 (Remember / trace)** | **Promote.** This is the product slide, not a chapter-two detail. |
| **13 (Across entities)** | Strengthen — *"multi-principal is built today, each author signed"* is now the ICP claim, not a vision claim. |
| **17 (ICP)** | **Rebuild.** Currently *"same person, lots of different jobs · theirs to run · can't be present · refuses to reset"* — GTM v4's solo psychographic, which argues against slides 9 and 13. Replace with **plural · consequential · continuing**, and the three-species table (§3.1). |
| **18 (Pricing)** | **Rebuild.** Free/$19/$49 with monthly allowances died six days after the deck was made. Replace with ADR-490: two humans free, $20/head from the 3rd, usage PAYG, top up from $5. |
| Product chapters | Re-cut for the 07-28 desk (Radar unveiled, Images hidden) — or better, name **verbs and surfaces**, not the app roster, so the next reshuffle doesn't invalidate a slide. |

---

## 5. The full canon, on one page

```
MOAT      (investors, internal)
          yarnnn is the system of record where human and AI work settles.

PRODUCT   (buyer, site, desk)
          yarnnn is the workspace you own — where you, your people, and every
          AI you use work on the same material, and every change is signed.

HERO      Work with any AI. Own what comes out of it.

HOOK      Every AI keeps its own copy of your work. This one is yours.

RECOGNITION
          "I use three different AIs, and I'm the only thing connecting them."

ICP       Plural · Consequential · Continuing.
          Anti-ICP: the single-AI user.

SECOND PRINCIPAL, three species:
          an external AI (activation) → agents at the desk (engagement)
          → a human colleague (revenue, head 3)

MOTION    Free-to-value, expand by head. Two legs: seats + usage.

WEDGE     The MCP door.   MCP → desk → share link
                          acquire   retain   expand

PROOF     Slide 9. Composed from — you · your agent · Claude.
```

---

## 6. Vocabulary rules

**Live words** (ADR-460/486/492/493): room · members · invite · keep · share · hub · sweep · brief · Projects · **signed** (proposed addition — the layman word for attribution).

**Retired, do not use**: standing delegate · the judgment seat · delegation dial · persona (as an entity class) · operator (external use; internal only) · cast · agents you own · under a judgment you control · five domain experts · the trust dial is the pricing axis.

**"Seat" means a human head.** One meaning only. Purge the other two (a running program; an AI persona entity) from every external surface.

**"Co-work" is not the lead noun** — see §2, the Cowork collision. The idea stays; the word goes.

**Preserved verbatim from GTM v4** — the mechanism discipline: *capability adjectives (persistent / compounds / autonomous / runs in your absence) never appear without their mechanism (owned, attributed, traceable to whoever made it).* This is the best line in the retiring doc and it gets stronger under the new lead, because ownership's mechanism is now in the one-liner itself.

---

## 7. What is weakest here

Named so it gets attacked rather than absorbed.

1. **Ownership is a moat claim in a product slot.** ADR-486's consumption guard is the warning: *"accumulation is never the demo … Era-1's failure was accumulation nobody felt."* Nobody wakes up wanting ownership; they want it retroactively, after losing something. The hero mitigates this by leading with a capability (*work with any AI*) and closing with ownership — but the risk is real and the first stranger conversations should probe it directly.
2. **The MCP wedge is unproven and this proposal promotes it anyway.** It is a reasoned bet from structure, not from data. §8.3 is how it dies.
3. **"Plural" may be too narrow.** It is a sharp qualifier, which is its value and its risk — it may filter out people who would convert. Testable cheaply: one question at the top of the funnel.
4. **The deck source.** Built on the 2026-07-22 PDF, not the artifact you linked. If the artifact's chapter 1 or ICP slide has moved, §4.4 needs revision.

---

## 8. What needs a ruling

### 8.1 — Operator rulings (this pass)
1. **The three-slot frame**, written into ESSENCE with slot labels, and the replace-never-accumulate maintenance rule.
2. **The product sentence and hero** (§2), or a counter-draft.
3. **The recognition sentence** (§2 slot 3).
4. **The ICP triad** — plural · consequential · continuing — and the single-AI anti-ICP.
5. **The motion restatement** (§4.1). This is the one that contradicts a previously-ratified sentence, so it needs an explicit overrule rather than a quiet edit.
6. **The wedge** (§4.2) as the *lead*, with §8.3's falsifier attached.

### 8.2 — One kernel ruling this proposal depends on
**Is an external LLM over the interop face a first-class principal in the ledger, permanently?** §1 rests on ADR-445's `foreign-llm`/`a2a` roles being real and durable. If a future pass collapses those into the member's attribution — the way ADR-460 collapsed kernel Agents into *the member's hands* — the activation stage in §3.1 evaporates and the ICP reverts to needing a human invite. **This should be stated as an invariant somewhere it will be honoured, not left as an implementation detail.**

### 8.3 — The falsifier, and a correction to an existing one

**New falsifier for the wedge**: within 60–90 days of leading with the MCP door, if users who arrive through a connector do not open the desk — no second surface, no settle, no share — then MCP is a feature of other people's products rather than a door into ours, and the wedge reverts to the shared team commons.

**And a correction worth making now.** ADR-457 D8.3 reads:

> *"MCP traffic dwarfs desk traffic among real users → the hum is the true wedge; investment priority flips back per D5."*

Under this proposal, MCP traffic dwarfing desk traffic is the **expected and desired** acquisition pattern, with the desk as the retention surface. As worded, D8.3 would fire on success. It should be re-cut to distinguish **MCP as the acquisition door** (good, expected) from **MCP as the whole product** (the actual failure mode — users who arrive via MCP and never reach the desk). That is the §8.3 falsifier above, and it measures the right thing.

### 8.4 — The two inputs no document can supply

Both ICP Deep-Dives died holding unanswered founder-validation questions. To avoid a third:

1. **Three real instances of a multi-principal ledger.** Any species. If none exist, §1 is theory and the whole proposal downgrades to a hypothesis to test rather than a canon to ratify.
2. **How many AIs does a real prospect actually use, and does the fragmentation register as a grievance or as normal life?** The entire ICP triad hangs on **plural** being felt rather than merely true.

---

## 9. Sequencing, if this is ratified

1. `ESSENCE.md` **v17** — the three slots with labels, and the §Canonical Positioning correction ADR-457 §10.3 parked for this pass.
2. `ICP.md` **v1** — the three-species model, the triad, the anti-ICP, the recovered demographics.
3. `NARRATIVE.md` **v6** — six beats re-cut; Beat 1 becomes the ownership read, Beat 3 the desk, Beat 6 the corrected motion.
4. `GTM_POSITIONING.md` **v5** — the language toolkit against v6.
5. `GROWTH-LOOP.md` — MCP → desk → share; metric = time-to-second-principal.
6. **IR deck** — slides 17 and 18 first (both are actively wrong); slide 9 promoted; cover hero.
7. `SITE-COPY-SPEC` **v2** — last, once 1–5 are settled.
8. **The ADR-template GTM line** (drift-ledger §5.8) — so this does not recur.
