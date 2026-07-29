# The ICP & One-Liner Discourse — Agenda

**Date**: 2026-07-29
**Status**: Discourse agenda. Nothing here is ratified; §8 lists the points that need to be.
**Premise under test** (operator, 2026-07-29): *ICP and consumer-targeting discourse should happen first, centred on re-confirming the agreed one-liner canon for yarnnn now.*
**Companion**: `GTM-RECUT-PROPOSAL-2026-07-29.md` (the drift ledger this unblocks).

---

## 0. The premise, checked

**Agreed, with one amendment.**

Right, because: the one-liner is the densest possible statement of who the product is for. Every ICP argument you could have — solo vs pair, prosumer vs team, ownership vs capability — is already encoded in the choice of subject noun and verb. Arguing the ICP without fixing the sentence means arguing about the sentence's implications while the sentence itself keeps moving.

**The amendment**: the discourse cannot *re-confirm* the one-liner, because there is no one-liner to re-confirm. There are **fifteen live ones across live documents — seven of them inside `ESSENCE.md` alone** — and they imply at least four different buyers. The task is not confirmation. It is **selection, and then slotting**.

---

## 1. The census — what is actually live

Every sentence below is in a document that is current or is cited as current. None is marked retired.

### Inside `ESSENCE.md` v16 (seven, no statement of which is for whom)

| # | § | The sentence | Buyer it implies |
|---|---|---|---|
| 1 | Core Thesis L18 | *"YARNNN is the workspace where work is cumulative."* | A person accumulating over time. Solo. |
| 2 | Product promise L42 | *"Author your context once. Carry it into every AI — and, when you're ready, let it run under a judgment you control."* | A solo operator heading toward delegation. **Contains the judgment claim ADR-380 §5 scoped out of the vision.** |
| 3 | Short form L44 | *"Your context, attributed and portable."* | An AI power user with a portability grievance. |
| 4 | §The Desk L94 | *"A desk with two verbs — Think and Make — over a commons that remembers."* | A working individual. Neutral on solo/pair. |
| 5 | §The Moat L161 | *"YARNNN is the system of record where human and AI work settles."* | Institutional / infrastructural. Plural actors. |
| 6 | §Canonical Positioning L188 | *"The workspace where work is cumulative — authored, attributed, and yours, reachable from every AI you use."* | Solo, portability-led. |
| 7 | §Canonical Positioning L191 | *"Your context, authored and portable — with a provenance chain no memory feature can show."* | Solo, competing against memory features. |

### Elsewhere

| # | Source | The sentence | Buyer it implies |
|---|---|---|---|
| 8 | SERVICE-MODEL v2.0 L16 | *"the system of record where human and AI work settles. A workspace is a **multi-principal commons** — the operator, invited members, their AI hands, and external LLMs…"* | Plural, explicitly. |
| 9 | ADR-486 D6 | *"Chat thinks, Studio and Images make, Radar watches — two hands and a watchman over a commons that remembers."* | A working individual. **Names an app hidden four days later (ADR-488).** |
| 10 | GTM v4 §1 | *"The workspace where work is cumulative — run by agents you own, under a judgment you control."* | Solo supervisor. Both halves superseded. |
| 11 | GTM v4 hero | *"The work you run shouldn't reset."* | Solo operator. |
| 12 | `README.md` | *"an AI Work Platform where deep context understanding enables superior agent supervision."* | Supervision-era. Very stale, still in the repo root. |
| 13 | IR deck ch.1 (07-22) | *"Companies keep their own private copy, you don't — so it never really becomes yours."* + *"Owned, not rented · Human + AI together · Model-agnostic."* | An AI user with an ownership grievance. |
| 14 | Live site (per SITE-COPY-SPEC note) | *"Shared memory for AI + human work"* | Plural, memory-category. |
| 15 | **Your claude.ai project description, written today** | *"co workspace with AI and humans. shared files, chat, documents under dedicated operating system"* | **Plural, co-work-led, OS-framed.** |

**#15 deserves attention.** It is the only sentence in the census written with nothing at stake — no canon to conform to, no audience to persuade, no ADR to cite. When you describe yarnnn casually, you say **co-work with AI and humans**. That is not in any of the fourteen documents above. It may be the most honest datapoint in the set, and it should be treated as evidence rather than as a stray field.

---

## 2. What the census reveals

Three things, in order of consequence.

**2.1 — The drift is not GTM's fault; it is a slotting failure in ESSENCE.**
ESSENCE holds seven one-liners in four sections with **no statement of which is for whom**. A GTM writer reading it in good faith can leave with any of seven leads and be defensible. That is the mechanism by which GTM v4, the site spec, and the IR deck each ended up carrying a different lead — they were each correctly quoting ESSENCE.

**2.2 — ESSENCE v16's own ruling says one sentence cannot do the job.**
> *"the record is the moat; the desk is the product."*

That is a statement that these are **two layers with two audiences**. It follows structurally that **you need three labelled sentences, not one**. The reason ESSENCE has seven is that it keeps trying to make one sentence carry the moat, the product, and the promise at once — and each attempt is right about a different layer.

**2.3 — The one-liner and the ICP are the same decision, and both reduce to the same question: what is the unit?**
A *workspace* implies one person. A *commons* implies plural principals. Every other fork downstream — pricing motion, activation loop, vertical chips, the site hero — is determined by that answer. This is why the operator's premise is correct: fix the sentence, and the ICP falls out rather than needing its own argument.

---

## 3. The proposed frame — three slots, not one sentence

**Position 1 (proposed for ratification):** yarnnn maintains **three** canonical sentences, each explicitly labelled with its audience and its surface. They do not compete; they stack.

| Slot | Audience | Job | Status |
|---|---|---|---|
| **The moat sentence** | Investors; internal discipline | Why this doesn't commoditize | ✅ **Ratified, leave alone.** *"The system of record where human and AI work settles"* (ADR-414 D1). |
| **The product sentence** | The buyer; the site hero; the desk | What you do here all day | ⛔ **Unresolved. This is what the discourse is for.** |
| **The recognition sentence** | The buyer, about themselves | The self-identification hook | ⛔ **Unresolved.** GTM v4 answered it for a solo (*"I run a ___"*). There is no pair version. |

Adopting this frame dissolves an argument that would otherwise burn a session — *"is it the record or the desk?"* — into a slotting question with an obvious answer. It also gives ESSENCE a maintenance rule it currently lacks: **one sentence per slot; a new candidate replaces, never accumulates.**

---

## 4. The four axes — the actual forks

### Axis 1 — The unit: a workspace, or a commons?

**The evidence that the unit is a commons:**
> ADR-465: *"The moat only turns on with a second principal. … Attribution across a single principal is trivial: **a one-member commons is a diary.** `trace`, correction-compounding, 'diverge privately, settle publicly' are all **latent until someone else is in the room.**"*

> ADR-490: *"the product's proof moment IS inviting someone into the commons, and a paywall on the first invite taxed exactly that moment."*

**The evidence that the unit is still one person:** ADR-445 accepts *"solo = low-revenue by design"* — which means solo users are expected, served, and numerous. ADR-465 makes a user own **zero-or-one** workspace. ADR-378's ceiling holds: no org layer, the workspace is the outermost unit.

**The honest reading**: the unit of *value* is a commons; the unit of *arrival* is a person. Both are true, and the one-liner has to pick which one it names.

---

### Axis 2 — The register: what it IS, what you DO, or what you GET

- **What it IS** — *"the system of record where human and AI work settles."* Infrastructure register. ADR-414 D1 frames it deliberately as *position over feature*, rhyming with git and double-entry. Powerful, and **ADR-457 §1 already ruled on its limit**: *"a settlement layer generates trust, not sessions."* Correct as a moat sentence; wrong as a product sentence.
- **What you DO** — *"think, make, keep."* Experience register, survives app churn (see §6.2), and is where ADR-457 says the felt product lives. Risk: no layman says "desk", and *keep/settle* sits behind an armed falsifier (§7).
- **What you GET** — *"work that is cumulative", "nothing resets."* Outcome register. Most emotionally direct. Risk: ESSENCE itself flags *cumulative* as jargon, and every incumbent now markets the same outcome — which is precisely why the mechanism discipline exists.

---

### Axis 3 — Ownership or capability as the lead claim

The July deck leads **ownership** (*"companies keep their own private copy, you don't"*), and it is the one claim incumbents structurally cannot make. Ownership also carries its mechanism for free — attribution *is* the proof of ownership — so it satisfies the discipline without effort.

**The risk, and it is specific.** ADR-486 D5 already named this failure mode in a different context:
> *"**Consumption guard**: accumulation is never the demo. The app leads with briefs (derived, cited, readable), never folder listings or counts. **Era-1's failure was accumulation nobody felt.**"*

Ownership has the same shape. Nobody wakes up wanting ownership; they want it retroactively, after they have lost something. **Ownership is a moat claim sitting in a product-sentence slot** — which may be exactly why the deck's chapter 1 is strong and its ICP slide is weak. Worth testing rather than assuming.

---

### Axis 4 — Is "you" a human alone, or human + AI together?

This is the newest claim, the least tested, and the one the operator reached for unprompted in #15.

It looks like it resolves Axis 1 for free: if AI colleagues count as principals, a solo workspace has a second principal on day one, attribution is non-trivial immediately, and the diary problem dissolves **without needing a human invite**. The machinery ships: ADR-492's person-first door, ADR-460's out-of-the-box Agents (*"nobody routes. You talk to someone"*), ADR-493's species-blind work units, and ADR-445's rule that AI principals are free and unlimited.

**It does not resolve it for free, and the reason is a live ruling.** ADR-460:
> *"A named preset that runs as the member's hands **does not become a principal by acquiring a name.** The face is an Agent; the fact is your hands. The room shows `Scout · Gemini` as a participant chip; **the ledger says `member:kvk via gemini/gemini-2.5-pro`.**"*

By the ledger's own testimony, a kernel Agent is **not** a second principal. So the seductive shortcut fails as stated — and the discourse has a precise question instead of a vague one:

> **Q4.** Does the "human + AI together" claim survive the ledger? Three possible answers, and they are genuinely different products:
> - **(a) No** — it is marketing the ledger contradicts, and the second principal must be human. Axis 1 resolves to *commons*, and the invite is the whole game.
> - **(b) Yes, for a subset** — ADR-445 lists AI principal roles `foreign-llm · a2a · own-agent · platform`. An **external LLM reaching in over the interop face genuinely is a distinct principal**, with its own grant row and its own attribution. That is a real second principal, arrived at with no invite and no seat — and it is the *interop* door, the one ADR-457 D5 demoted in investment priority. If (b) holds, the demotion may have been priced wrong.
> - **(c) Yes, and the ledger should change** — if "you and your AI colleagues" is the product claim, kernel Agents should attribute as principals. That is a kernel discourse (ADR-460 D3.a), not a copy decision, and it should not be smuggled in through a marketing sentence.

**This is the single highest-value question in the agenda.** It decides whether the solo user is a diary owner (a), an already-multi-principal commons (b), or a pending kernel change (c) — and each answer produces a different ICP, a different activation loop, and a different revenue model.

---

## 5. Candidates — each tagged with what it commits you to

None of these is a recommendation. They are positioned to make the axes visible, so the discourse argues about the commitment rather than the wording.

**A. "The workspace you own, where you and your AI work together."**
*Axes: commons-ish · IS/DO hybrid · ownership-led · human+AI.*
Commits to: the broadest ICP — anyone with ongoing work and at least one AI. Makes the solo user legitimate without an invite. **Depends entirely on Q4 resolving to (b) or (c).** Risk: "workspace" is Notion and Slack's word; reads generic without the second clause doing real work.

**B. "Every AI keeps its own copy of your work. This one is yours."**
*Axes: neutral on unit · IS · ownership-led · human-centric.*
Commits to: AI power users with a felt fragmentation grievance. Deck-native, and the strongest differentiator in the set — no incumbent can say it. Risk: it sells *against*, not *for*; it never says what you do all day; and per Axis 3, ownership may be a moat claim in a product slot.

**C. "Think, make, and keep — one place where your work with AI adds up."**
*Axes: neutral on unit · DO · outcome-led · human+AI implied.*
Commits to: the working individual, solo or not. Survives app churn (§6.2). Closest to ADR-457's ratified internal canon. Risk: *keep* is the settle verb, and ADR-457 D8.2 says do not lead with it until it is proven used.

**D. "A shared workspace for you, your people, and your AI — where nothing resets and everyone signs their name."**
*Axes: commons · IS/GET · attribution as mechanism · human+AI.*
Commits to: the pair. The most honest rendering of ADR-465 + ADR-490 + ADR-492. *"Everyone signs their name"* is the mechanism, in layman words, and it is what deck slide 9 already shows. Risk: longest; "your people" flirts with an org promise ADR-378 forbids; and it markets a state most new users are not in on day one.

**E. "Co-work with AI and humans — shared files, chat, and documents, in a place that's yours."**
*Axes: commons · DO · co-work-led · human+AI.*
Commits to: the operator's own unprompted framing (#15), rendered as copy. Note what it does: it names the **surfaces** (files, chat, documents) rather than the verbs or the apps, which is a third option §6.2 does not anticipate and may be more durable than either. Risk: "co-work" collides with Anthropic's Cowork product name — a real and immediate collision worth deciding on before it ships anywhere.

---

## 6. The rubric — what any candidate must survive

1. **Names the unit correctly.** Pricing keys on it (ADR-490 counts human heads), so a sentence that implies solo while the price counts heads will mis-sell on the pricing page.
2. **Survives an app moving in or out of the Dock.** On 2026-07-28 Radar was unveiled and Images was hidden (ADR-488). ADR-486's canonical desk sentence names Images. **Any sentence pinned to the app roster has a fortnight's shelf life.** Name verbs, surfaces, or the commons — not the roster.
3. **Carries a mechanism, not a bare adjective.** ESSENCE's own rule; the most durable thing in the GTM set. *Persistent / compounds / autonomous* are incumbent words now.
4. **Does not lead with an armed falsifier.** See §7.
5. **Is true of a free two-person workspace on day one.** ADR-490 made that the entry product; a sentence that only becomes true at Day 90 fails NARRATIVE v5's still-valid *demo-that-requires-tenure* anti-pattern.
6. **Is sayable by a layman about themselves.** The recognition slot. *"I run a ___"* worked for a solo; the pair version does not exist yet.
7. **Separates from both camps the deck names** — model makers and agent-memory startups — without requiring the listener to know either exists.

---

## 7. Fixed inputs — what the discourse may not re-open

Naming these is load-bearing. Without it, a one-liner discourse re-opens the whole architecture.

- **ADR-380 §5** — Rung-2 autonomous judgment is scoped out of the **vision**, not just the build. *"Under a judgment you control"* (ESSENCE L42, GTM v4 §1) may **not** return to the one-liner.
- **ADR-414 D1** — the moat sentence is ratified. Only its *slot* is in play, never its wording.
- **ADR-490** — the price shape. The one-liner must be true of a free two-person workspace with no subscription.
- **ADR-378** — no org-above-workspace layer. No "for your company", no "for your org", no team-account implication.
- **ADR-457 D5** — two doors, one commons. The interop face is demoted in *investment priority*, not deleted. A one-liner that erases it forecloses Q4(b).
- **The mechanism discipline** — carried verbatim from GTM v4 §1 and SITE-COPY-SPEC §0.

**And two armed falsifiers**, which are constraints on the *lead*, not on the roadmap:
- **ADR-457 D8.2 / ADR-460 §8** — if settle goes unused after honest staging, *"GTM must not lead with it."* Candidate **C** is exposed.
- **ADR-486 D8.2** — if briefs go unopened, *"do not GTM-lead with Radar."*

Read together, these fence off settle and Radar — the two most differentiated things in the product — until instrumented. **What is left unfenced is the shared commons and attribution**, which is, not coincidentally, what the July deck already leads with. That is worth noticing before the discourse starts: the deck may have already found the answer by necessity.

---

## 8. Ratification points

In the order they must be decided; each unblocks the next.

1. **The three-slot frame** (§3) — three labelled sentences, one per slot, replace-never-accumulate, with the slot labels written into ESSENCE.
2. **Q4 — does "human + AI together" survive the ledger?** (a) human-only principals, (b) external LLMs over the interop face count, or (c) kernel Agents should attribute as principals. *This is the fork; everything downstream reads from it.*
3. **Axis 1 — the unit named in the product sentence**: workspace, or commons. Follows mechanically from (2) in most branches.
4. **Axis 3 — the lead claim**: ownership, or the doing. With the §Axis-3 risk (ownership as a moat claim in a product slot) explicitly weighed rather than assumed away.
5. **The product sentence itself** — one candidate from §5, or a synthesis, against the §6 rubric.
6. **The recognition sentence** — the pair-or-solo self-identification hook. *"I run a ___"* survives, gets a companion, or retires.
7. **The "co-work" naming collision** — if E or anything like it advances, decide on the Cowork clash before it reaches a surface.
8. **Then, and only then**: `ICP.md` → NARRATIVE v6 → GTM v5 → GROWTH-LOOP → ESSENCE v17 → deck slides 17–18 → SITE-COPY-SPEC v2.

---

## 9. Two things to bring to the session that no document contains

Both ICP Deep-Dives (v2 Feb, v3 Apr) end with unanswered founder-validation questions. That is the actual reason they went stale — not the architecture drift, which merely finished them off. The same fate is available to whatever comes out of this discourse.

So, two inputs worth having ready:

1. **Three real pairs.** Not archetypes — three actual instances of someone using yarnnn with a second principal, human or otherwise, and what the second principal is doing. If none exist, that is itself the answer to Q4 and it changes the whole agenda.
2. **The honest read on the acquisition wedge.** ADR-457 D6 already requires this and it has never been written down: *"The acquisition wedge is an open question, named honestly … grounding and settling are retention features. Candidate wedges — multi-engine/BYOK economics, the shared team commons, MCP-side capture funneling into the desk — are plausible and unproven. **GTM must not pretend otherwise.**"*

A one-liner chosen without those two inputs will be internally coherent and externally untested — which is precisely the shape of every document this pass just bannered.
