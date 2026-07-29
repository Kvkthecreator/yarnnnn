# YARNNN Narrative Architecture

**Purpose**: Canonical reference for how the yarnnn story is structured and sequenced across all surfaces — decks, videos, applications, landing pages, conversations.
**Status**: Active (v6.0)
**Date**: 2026-07-29
**Supersedes**: v5.0 (2026-06-10) — a full re-cut, not a patch. v5 told the judgment-seat / standing-delegate story to a solo operator on a high-ACV motion; all three legs have since been re-cut by canon: judgment is out of the vision (ADR-380 §5), the ICP inverted from solo operator to plural-AI user in a multi-principal commons (ADR-465, CANON-LOCK §2), and the pricing shape dissolved the high-ACV motion (ADR-490). **One explicit overrule, recorded rather than edited quietly**: v5 Beat 6's ratified sentence — *"Hundreds of operators paying real money is a real business; this was never a $19/mo volume play"* — is overruled by CANON-LOCK §3.1. Under ADR-490 (two humans free, $20/head from the third, usage at cost × 1.30) the business is free-to-value, expand-by-head, volume-dependent — early Figma or Linear, not a vertical seat. The old sentence described a company the price list dissolved.
**Grounded in**: [CANON-LOCK-2026-07-29](working_docs/strategy/CANON-LOCK-2026-07-29.md) (operator-ratified) · [ESSENCE.md](ESSENCE.md) v17 · [ICP.md](working_docs/strategy/ICP.md) v1 · ADR-457 (the desk and the record) · ADR-465 (share; the second principal) · ADR-490 (pricing) · ADR-437 (activation channels)

**Related docs:**
- [ESSENCE.md](ESSENCE.md) — what we believe and how the product works (carries the canon sentences)
- [GTM_POSITIONING.md](working_docs/strategy/GTM_POSITIONING.md) — specific language, messaging toolkit (v5)
- [GROWTH-LOOP.md](working_docs/go-to-market/GROWTH-LOOP.md) — the activation loop and metrics

---

## The Macro Frame: Capability Forward, Ownership as the Proof

Two layers, told in order (ESSENCE v16/v17: *the record is the moat; the desk is the product*):

- **The story leads with the capability**: co-work — you, your people, and every AI you already use, on the same material. This is the hero and the promise.
- **The moat is felt, not claimed**: attribution — every change signed by whoever made it, human or not — shown as a picture (the attribution walk), never argued as a thesis in the hero.

The ratings-agency / self-audit argument that opened v5 is **demoted to defensibility ammunition** (Beat 5), where ADR-380 §5's conservatism permits it. The sequencing discipline survives from v4/v5: lead with what the product is and does today; the structural thesis lands mid-story as the "aha."

---

## The Six Narrative Beats

### Beat 1: The Problem (The Ownership Hook)

**Role**: Land the grievance the plural-AI user already feels, in one sentence.

**The hook (canon, Slot 3):**
> **Every AI keeps its own copy of your work. You don't.**

**The claim**: You use more than one AI — most working people do now. Each one keeps its own memory, its own context, its own private copy of what you told it. None of them talks to the others. None of them can show you who wrote what. And none of it is yours: it lives in their product, shaped by their retention policy, unreadable and uncarryable. The connective tissue between your AIs is *you* — the recognition sentence: *"I use three different AIs, and I'm the only thing connecting them."*

**Why this works**: It concedes incumbent capability fully (their AIs are good — that's the premise, not the threat), and the grievance grows as the incumbents succeed: every new AI you adopt is another private copy. The ratings-agency/self-audit argument v5 opened with is real but it is a *defensibility* argument, not a felt problem — it moves to Beat 5.

**What to avoid**: Don't open on accountability or judgment (deferred, ADR-380 §5). Don't open on "AI forgets" (false, and the audience knows). Don't open on ownership-as-ideology — nobody wakes up wanting ownership; they want it retroactively (CANON-ADOPTED §1.2). The hook works because it names a *loss*, not a principle.

### Beat 2: Proof of Demand (Validation)

**Role**: Establish the appetite is real and funded.

**The claim**: Two proof streams. (1) **The memory-layer category is funded**: Mem0, Zep, Cognee raised on exactly this gap — the market has already priced "AI needs a persistent, portable memory layer" as true. What's missing isn't more memory; it's the *shared place to work* — memory startups ship infrastructure, not a workspace. (2) **The co-work signal**: the platform vendors themselves are converging on multiplayer AI work — persistent project workspaces, shared AI surfaces, collaborative sessions. The category verb is becoming *work with*, not *ask*. Demand for AI-that-persists is proven; demand for a *shared, vendor-neutral* place where that work settles is forming exactly on schedule — and every single-vendor entrant validates it without being able to serve it.

**Adaptation note**: For investor audiences, the funded-category stream leads (it is a comp, not a claim). For buyers, the co-work signal leads (it names what they're already doing).

### Beat 3: Meet the Product (The Shared Workspace)

**Role**: Introduce yarnnn concretely, in the canon's own words.

**The hero (canon, Slot 2):**
> **your true AI-first workspace.**
> **co-work like never before.**
>
> Work with ChatGPT, Gemini, and Claude together in one shared workspace.
> Dedicated apps, a shared file system, documents you build with AI —
> and every change signed by whoever made it, human or not.

**The claim, expanded**: One workspace, and everything you work with meets you there. The AIs you already use reach the same files you do. You think in conversation, you make documents and pages, you keep what matters — and every change, whoever made it, lands as a signed revision in a record you own. Nothing is a session; everything settles.

**The roster rule (binding)**: name **verbs and surface categories** — *dedicated apps, a shared file system, documents you build with AI; think, make, keep, share* — **never the app roster**. The Dock changed composition three times in fourteen days; ADR-486's canonical desk sentence named Images, which ADR-488 hid four days later. App names may appear in a product chapter walkthrough, never in the beat's framing copy (CANON-LOCK §5).

**The Day-1 proof**: *keep this → it lands attributed → open any source.* A stranger drops a file or states a fact and watches it placed, signed, and recallable — the moat on contact (ADR-437 D3). Not correction-compounding (a staged tenure moment, never the ambient experience — ESSENCE v16), not a retrospective audit (genesis is empty — ADR-414/437).

**Mechanism discipline (binding, from v4/v5, unchanged)**: capability adjectives — *persistent, compounds, autonomous, AI-first* — never appear without their mechanism: *owned, attributed, signed by whoever made it.*

### Beat 4: The Insight (Thesis as Revelation)

**Role**: Reframe why this works when others don't — narrowed to the surviving half of v5's thesis.

**The claim**: Work is shifting to AI-first — that's adoption data now, not prediction. As execution gets delegated to models that improve quarterly, execution itself commoditizes; whatever model you used last quarter, a better one arrives next quarter, and it remembers nothing you did. What compounds is the other thing: **the shared, attributed record of the work** — who decided what, what was corrected, what settled. *Execution commoditizes; the shared, attributed record compounds.* The durable product isn't a better AI — better AIs are the commodity layer, arriving on schedule. It's the neutral place where every AI's work (and yours, and your colleagues') accumulates into one signed history that survives every model upgrade. Judgment — an installed seat that renders calibrated verdicts — is the *deferred deepening* of this record (ADR-380 §5), not the revelation.

**This is where "moat," "switching costs," "compounding" first appear as named concepts.**

### Beat 5: The Moat (Defensibility)

**Role**: Answer "why can't the platforms eat this?"

**The moat sentence (canon, Slot 1 — investors and internal discipline only, never the product sentence):**
> **yarnnn is the system of record where human and AI work settles.**

**The load-bearing sentence this beat gains in v6**: **the moat turns on with the second principal** (ADR-465 — *"a one-member commons is a diary"*). Attribution across one principal is trivial; the moment a second principal exists — an external AI over the interop face, or an invited human — the ledger becomes the only place that can answer *who did this, and what was it made from*, across vendors. And the second principal usually costs nothing and arrives on day one (ICP.md §3).

**The visual is the attribution walk** (deck slide 9): *"Composed from — open any source · you · Aug 2 · your agent · Aug 5 · Claude · Aug 6."* Multi-principal attribution as a picture, not a claim. No tenure required. Structurally unrenderable by a single-vendor host. Because the hero leads with capability and carries ownership only in the possessive, **this is the only place the moat is felt** — it belongs in chapter one, directly after the hook, not buried in a product tour.

**Structural defensibility arguments** (this is where the v5 material lives on):
1. **Neutrality by construction** — a model vendor auditing its own model's work is a self-audit; the ratings-agency argument, demoted from Beat 1 to here, where it is ammunition rather than spine.
2. **Total attribution enforced at the write path** — nothing mutates the substrate anonymously; every revision is authored, parent-pointered, content-addressed (ADR-209/413). No incumbent context layer exposes this.
3. **Anti-fragile to model churn** — every new frontier engine makes the vendor-neutral commons more necessary, not less (ESSENCE §The Moat).
4. **Portability is the trust wedge** — you can leave with everything, which is why you stay.

**Architecture as evidence**: 500+ ADRs; attribution enforced in code, not claimed in copy. Architecture appears here, as defensibility, never as product description.

### Beat 6: The Opportunity (Market + Motion + Timing)

**Role**: The business case, with the motion matched to the price list actually shipped.

**The buyer**: the plural-AI user doing real work — **plural · consequential · continuing** ([ICP.md](working_docs/strategy/ICP.md)). Prosumer and small-team register. The anti-ICP is the single-AI user, filtered implicitly by the hero itself.

**The motion (CANON-LOCK §3.1)**:
> **Free-to-value, expand by head. Two revenue legs: seats and usage.**

- **Seats** — two humans free per workspace; $20/mo per human from the third (ADR-490). Revenue scales with the invite — the proof moment *is* the growth moment.
- **Usage** — PAYG at provider cost × 1.30. Thin margin, needs volume — which is exactly why *plural* is the qualifying trait.
- **Shape** — prosumer / small-team, land-free-and-expand. Early Figma or Linear, not a vertical seat.

*(This beat is where the v5 "never a volume play" sentence is overruled — see the header banner.)*

**Why now**: the memory category is funded but shipped as infrastructure without a workspace; the platform vendors are converging on multiplayer AI work but each inside a sealed single-vendor commons; MCP made the external-AI second principal a day-one reality rather than a roadmap item. The composition — shared workspace + multi-vendor principals + signed record — is unoccupied, and every incumbent move validates the category while deepening their own disqualification from the neutral position.

---

## The Honest Open Question

*(New in v6 — required by ADR-457 D6, which names the acquisition wedge as an open question and forbids GTM from pretending otherwise.)*

**The acquisition wedge is a bet, not a proven channel.** CANON-LOCK §3.2 leads with the **MCP door** — *"co-work with the AI you already use"* — because it is the only lead unfenced by an armed falsifier, the only channel where the second principal arrives free on day one, and connector directories pre-qualify for *plural* by construction. But it is promoted from ADR-457 D6's *named-but-unproven candidate* list, and it carries an armed falsifier (CANON-LOCK §8.1): if within 60–90 days connector-origin users do not open the desk — no second surface, no keep, no share — then MCP is a feature of other people's products, not a door into ours, and the lead reverts to the shared team commons. Grounding and settling are retention features; the narrative must not present them as acquisition. Copy written from this document must not write cheques the wedge hasn't cashed.

---

## Vocabulary Rules (Global)

Per CANON-LOCK §5. Full discipline in GTM v5.

| Always say | Instead of | Reasoning |
|------------|-----------|-----------|
| **co-work** (verb/adjective only, lowercase) | "collaboration platform" / `yarnnn Cowork` | Never a product noun, never capitalised — the line that keeps the Anthropic-Cowork adjacency an asset instead of a collision |
| **AI-first** (always with mechanism) | bare "AI-powered" | Capability adjective; requires the signed clause in the same visual field |
| **signed** | "attributed" (in layman copy) | The layman word for attribution |
| **shared workspace · room · members · invite · keep · share** | "cast" / "roster" / "team you build by chatting" | The live layman words (ADR-460/492) |
| **hub · sweep · brief · Projects** | — | Live surface vocabulary (ADR-486, ADR-493 D7) |
| **seat = a human head, one meaning only** | seat-as-program ($149–499) / seat-as-persona | Three live meanings existed; ADR-445/490's is the only external one |
| Verbs and surface categories | the app roster | The roster rule — see Beat 3 |

**Retired — never in external copy** (CANON-LOCK §5): standing delegate · the judgment seat · delegation dial · persona (as an entity class) · cast · agents you own · under a judgment you control · five domain experts · the trust dial is the pricing axis · operator (external; internal only) · $19/mo · per-operation pricing · the Specialist palette · "the team you build by chatting".

**The engine rule** (ADR-420 §10): naming three models is positioning; a model-count comparison table is the treadmill. Never compete on engine count.

---

## Thesis-Timing Rules

| Language | First appears | Rationale |
|----------|--------------|-----------|
| The ownership hook ("its own copy") | Beat 1 | It IS the problem statement |
| The recognition sentence | Beat 1 | The buyer's self-identification, right after the hook |
| The hero + subhead | Beat 3 | The product, in canon words |
| The attribution walk (visual) | Immediately after Beat 1 in decks; Beat 5 in prose | The only place the moat is felt (CANON-LOCK §3.4) |
| "Moat" / "switching costs" / "compounding" (named) | Beat 4 | Protect the revelation |
| The moat sentence ("system of record…") | Beat 5 | Investors and internal discipline only — never the product sentence (ADR-457 §1) |
| Self-audit / ratings-agency argument | Beat 5 | Defensibility ammunition, not the spine (ADR-380 §5) |
| Pricing / motion | Beat 6 | After value is established |

---

## Surface Adaptation Guide

- **IR deck**: hook (Beat 1) → attribution walk promoted to chapter one (CANON-LOCK §3.4) → product chapter (Beat 3; app names allowed here) → market/camps (Beats 2 + 5) → motion (Beat 6). Slides 17 (ICP) and 18 (pricing) rebuild against ICP.md and ADR-490 — they are the two actively wrong slides (CANON-ADOPTED §4.9).
- **Landing page**: Beat 1 hook above the hero → Beat 3 hero + subhead → attribution walk → Beat 6 CTA (*"Co-work with the AI you already use"* — the lead door, GROWTH-LOOP.md).
- **Elevator pitch (30s)**: "Every AI you use keeps its own copy of your work — you're the only thing connecting them. yarnnn is one shared workspace where you work with ChatGPT, Gemini, and Claude together: shared files, documents you build with AI, and every change signed by whoever made it, human or not. The AIs keep getting better and keep getting swapped; the signed record of the work is yours and compounds."
- **Written VC application**: all six beats in prose; Beat 5 gets the most space; open with the hook, close with the motion; the moat sentence appears once, in Beat 5.

---

## Anti-Patterns

All v4/v5 anti-patterns hold (no "AI forgets everything"; no false certainty about incumbents; no thesis-first or architecture-first sequencing; no feature lists; no "better ChatGPT"; no pre-built roster framing). Two are preserved verbatim from v5 — both are more binding now, not less:

**Bare-capability copy**: leading with "persistent," "autonomous," "self-improving," "runs while you sleep" — these are now the *incumbents'* words. Using them without the mechanism makes YARNNN indistinguishable from the commodity it isn't. Always carry the mechanism.

**Demo that requires tenure**: selling compounding with a demo that can't show it. First sessions must show either *correction-compounding* (fix one file, watch artifacts improve) or the *retrospective audit* (reconcile an existing track record into an instant calibration trail). Never ask a stranger to imagine Day 90.
> *v6 note on the preserved text*: the two first-session assets named above are superseded (correction-compounding is a staged tenure moment, never the ambient experience — ESSENCE v16; the retrospective audit has no substrate, genesis is empty — ADR-414/437). The rule's principle is untouched and sharper than ever; the asset that satisfies it now is the **attribution walk** and the **moat-on-contact** loop: keep this → it lands signed → open any source (ADR-437 D3). Still never ask a stranger to imagine Day 90.

v6 adds:

**Counting hands as principals**: any copy that presents a desk Agent as a colleague, teammate, or second principal. The ledger contradicts it (`member:kvk via …` — ADR-460). The species that make the workspace multi-principal are the external AI and the human ([ICP.md](working_docs/strategy/ICP.md) §3).

**Leading with fenced acts**: GTM-leading with settle (fenced by ADR-457 D8.2 / ADR-460 §8 until proven used) or with Radar/briefs (fenced by ADR-486 D8.2 until proven opened). Both are product truths and neither is a lead until its falsifier is cleared.

---

## Maintenance

Update when: the CANON-LOCK §8 falsifiers fire or clear (falsifier 1 re-cuts Beat 6 and the open question; 2 and 3 unlock new leads); a CANON-LOCK §9 validation question is answered (re-verify Beat 1's grievance is *felt*); a platform ships a multi-vendor attributed commons (re-examine Beat 5 immediately); ICP.md §5 demographics land (sharpen Beat 6); the canon sentences change in ESSENCE (this doc quotes, never forks, them).

This document is the rubric for external storytelling. ESSENCE defines what we believe and carries the canon sentences. GTM_POSITIONING defines how we say it. NARRATIVE defines the order and why. GROWTH-LOOP defines how a stranger becomes a principal.
