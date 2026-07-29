# yarnnn — Canon Lock

**Date**: 2026-07-29
**Status**: **LOCKED.** Operator-ratified in the 2026-07-29 ICP/one-liner discourse.
**Authority**: This document is the source of truth for the one-liner, the ICP, the GTM motion, and the activation model. Where NARRATIVE, GTM_POSITIONING, ICP, GROWTH-LOOP, the site spec, or the deck disagree with this document, they are wrong and get revised.
**Derivation**: `ICP-ONELINER-DISCOURSE-2026-07-29.md` → `ONELINER-ICP-GTM-PROPOSAL-2026-07-29.md` → `CANON-ADOPTED-2026-07-29.md`. Drift evidence: `GTM-RECUT-PROPOSAL-2026-07-29.md`.
**Not in scope**: architecture. This document never overrides an ADR; where it depends on one, §7 names it.

---

## 1. The one-liner canon — three slots

**Maintenance rule**: one sentence per slot. A new candidate **replaces**; it never accumulates. The seven-one-liners-in-one-document failure (ESSENCE v16) is what this rule exists to prevent.

### Slot 1 — MOAT (investors, internal discipline)

> **yarnnn is the system of record where human and AI work settles.**

Ratified ADR-414 D1. Unchanged. **Never used as the product sentence** — ADR-457 §1: *"a settlement layer generates trust, not sessions."*

### Slot 2 — PRODUCT (the buyer, the site, the deck cover)

> # your true AI-first workspace.
> # co-work like never before.

**Subhead** (locked, mechanism-bearing):

> Work with ChatGPT, Gemini, and Claude together in one shared workspace.
> Dedicated apps, a shared file system, documents you build with AI —
> and every change signed by whoever made it, human or not.

The final clause is non-optional. *"AI-first"* is a capability adjective, and the mechanism discipline requires its mechanism in the same visual field. *"Human or not"* does double duty: it lands attribution and it declares co-work species-blind.

### Slot 3 — HOOK (the problem, opens the deck and the site)

> **Every AI keeps its own copy of your work. You don't.**

### Slot 4 — RECOGNITION (what the buyer says about themselves)

> **"I use three different AIs, and I'm the only thing connecting them."**

A recognition hook, not a search hook. SEO load falls on category terms; this converts on-page.

---

## 2. The ICP

### 2.1 The qualifying triad

> **Plural · Consequential · Continuing**

- **Plural** — they already use more than one AI. *The load-bearing qualifier.* It is the grievance (the hook), the moat's entry condition (a second principal exists on day one), and the usage-revenue predictor (a 30% PAYG margin needs volume).
- **Consequential** — the output goes to someone who matters. The willingness-to-pay filter.
- **Continuing** — the work repeats or accumulates. The tenure filter.

Register: **AI power user doing real work.** Prosumer and small-team, not scarce senior operator. This is deliberate — it is the register the ADR-490 price list can actually serve.

### 2.2 The second principal — three species

The moat turns on with the second principal (ADR-465). The second principal is usually **not a person**; it is usually a **second surface**.

| Species | Arrives | Cost | Function |
|---|---|---|---|
| **An external AI** — `foreign-llm` / `a2a` over the interop face | Day one, no invite, no seat | Free, unlimited | **Activation** |
| **Agents at the desk** — `Scout · Gemini` et al. | Out of the box | Free | **Engagement** |
| **A human colleague** — invite or `/s/{token}` | When invited | 2 free, then $20/head | **Revenue** |

**Binding honesty rule**: agents at the desk are **the member's hands**, not principals — ADR-460, and the ledger says so (`member:kvk via gemini/gemini-2.5-pro`). They are **never** marketed as colleagues, teammates, or a second principal. The species that makes the ledger multi-principal is the external AI and the human.

### 2.3 The anti-ICP

> **The single-AI user.**

No fragmentation grievance, no second principal, no reason to leave a vendor whose memory is already good enough. **yarnnn is a worse ChatGPT for that person.**

**Posture: implicit.** No gating question, no qualification form. Naming three LLMs in the subhead does the filtering; the funnel stays wide and conversion data tells us who was right.

### 2.4 Owed

`ICP.md` must recover concrete demographics for the plural-AI user — age, income, company size, AI spend, tool stack, switch trigger, decision channels — **plus which AIs and how many**, which no prior doc captured. Validated, not hypothesised. The three archived ICP Deep-Dives died holding unanswered validation questions; that is the failure mode to avoid.

---

## 3. GTM

### 3.1 Motion

> **Free-to-value, expand by head. Two revenue legs: seats and usage.**

- **Seats** — two humans free per workspace; $20/mo per human from the third (ADR-490). Revenue scales with the invite.
- **Usage** — PAYG at provider cost × 1.30. Thin, so it needs volume — which is why *plural* qualifies.
- **Shape** — prosumer / small-team, land-free-and-expand. Early Figma or Linear, not a vertical seat.

**RETIRED**: *"premium, high-ACV, low-velocity, expansion-led … Hundreds of operators paying real money is a real business — never a volume play."* It describes a company the price list dissolved. This is an explicit overrule of a previously-ratified sentence, not a quiet edit.

### 3.2 The wedge

> **The first co-work moment.**

```
MCP door        →   the desk      →   the share link
first co-work       daily co-work     co-work with a person
acquire             retain            expand
(free, day one)     (free)            (paid at head 3)
```

**The MCP door is the acquisition wedge.** Four reasons: it is the only lead unfenced by an armed falsifier; it is the only channel where the second principal arrives free; connector directories are distribution and pre-qualify for *plural* by construction; and it demos the moat in sixty seconds with no tenure.

This promotes ADR-457 D6's named-but-unproven candidate (*"MCP-side capture funneling into the desk"*) to the lead. It does **not** reverse ADR-457 D5 — the desk remains where the product is experienced and where retention lives. Falsifier at §8.

### 3.3 Competitive frame — three camps

| Camp | Who | What they lack | The line |
|---|---|---|---|
| **Model makers** | OpenAI · Google · Anthropic | Neutrality. One vendor, sealed. | "Your context lives in their product, not yours." |
| **Agent memory** | Mem0 · Zep · Cognee | A place to work. Memory without a workspace. | "Memory remembers. It doesn't co-work." |
| **AI-retrofitted workspaces** | Notion · Slack · Google Workspace | AI as a principal. Built for humans, AI bolted on. | "Their AI is a feature inside a human tool. Here, AI is a principal in the workspace." |

Camp three is what **"true"** in the headline is aimed at. It is new to the canon and it is the camp the deck currently under-serves.

### 3.4 Proof asset

**The attribution walk** — deck slide 9: *"Composed from — open any source · you · Aug 2 · your agent · Aug 5 · Claude · Aug 6."*

Multi-principal attribution as a picture, not a claim. No tenure required. Structurally unrenderable by a single-vendor host. Because the hero leads with capability and carries ownership only in the possessive, **this is the only place the moat is felt** — it moves to chapter one, directly after the hook.

### 3.5 Pricing facts (from ADR-490 — quote these, not the old ones)

Two humans free per workspace · $20/mo per human from the third · usage pay-as-you-go, funded by the $3 signup grant and top-ups · hard stop at zero · **no monthly allowance** · **no solo plan to buy** · AI principals free and unlimited · dollars shown only at purchase, consumption shown as usage-%.

---

## 4. Activation

### 4.1 Definition

> **Activated = the first co-work moment: two distinct principals with attributed revisions on the same file.**

Not signups. Not tasks. Not connectors attached. The metric is **time-to-first-co-work-moment**, readable from the existing ledger with no new telemetry.

### 4.2 Two channels only

Per ADR-437, a stranger becomes an activated principal through exactly two channels. There is no third, and there is no wizard.

**Channel 1 — cold discovery. LEAD DOOR: connect your AI first.**

Primary CTA: **"Co-work with the AI you already use."**

The first act is attaching yarnnn to an AI the person already has, so that the second principal exists before the member has authored anything. The first thing they see at the desk is a write **they didn't make, signed by something that isn't them** — the moat on contact, per ADR-437 D3: *"a cold user who drops a file or states a fact and watches it placed, attributed, and recallable has seen the moat on contact."*

**Channel 2 — invited / shared.** `/s/{token}` → broad member grant → land on the shared artifact with `trace` visible, inside a populated commons. Shipped (ADR-437 Phase D, ADR-465). The artifact is the landing page.

### 4.3 What activation is not

No setup wizard · no workspace constitution · no program pick · no roster discovery · no "assign your first task" · no blank-canvas empty state. All deleted or retired (ADR-437 D1, ADR-421, ADR-414 D4/D5, ADR-460, ADR-231). **Entry is a flow, not a ceremony** (ADR-465).

### 4.4 Metrics

| | Metric |
|---|---|
| **Primary** | Time-to-first-co-work-moment |
| Secondary | Connector-attach rate (cold channel) · share→accept rate (warm channel) · third-head rate (revenue) |
| Guardrail | Desk-return rate among connector-origin users — the §8 falsifier |

### 4.5 Named build dependency

**Leading with the MCP door makes the connector attach path the highest-leverage unbuilt surface.** ADR-437 Phase C (the cold empty-state design pass) is still open, and it is now on the critical path rather than beside it. The connector registry (ADR-494) is the surface this leans on. **This dependency is stated, not assumed** — if the attach path is not a sixty-second act, the lead door is aspiration rather than strategy.

---

## 5. Vocabulary

**Live**: co-work (verb/adjective only, lowercase, never a product noun) · AI-first (always with mechanism) · **signed** (the layman word for attribution) · shared workspace · room · members · invite · keep · share · hub · sweep · brief · Projects · seat (**a human head, one meaning only**).

**Retired — do not use in any external surface**: standing delegate · the judgment seat · delegation dial · persona (as an entity class) · cast · agents you own · under a judgment you control · five domain experts · the trust dial is the pricing axis · operator (external; internal only) · $19/mo · per-operation pricing · the Specialist palette · "the team you build by chatting".

**The mechanism discipline** (preserved verbatim from GTM v4 — the best rule in the retiring doc):
> Capability adjectives — *persistent, compounds, autonomous, AI-first, runs in your absence* — **never** appear without their mechanism: *owned, attributed, signed by whoever made it.*

**The roster rule**: app names (Chat · Studio · Files · Radar · Images) may appear in the product chapter and **never** in the hero, the subhead, or above the fold. The Dock changed three times in fourteen days.

**The engine rule** (ADR-420 §10): naming three models is positioning; a model-count comparison table is the treadmill. Never compete on engine count.

---

## 6. What this supersedes

`NARRATIVE.md` v5 §Macro + Beats 1/3/4/6 · `GTM_POSITIONING.md` v4 §1, §2, §5, §6 · `SITE-COPY-SPEC-v1` §0 hero + ICP + pricing + `/how-it-works` · `ICP_ANALYSIS_APRIL_2026` (archived) · `ICP Deep-Dive` v1/v2/v3 (archived) · `ACTIVATION_100USERS` v3 (archived) · deck slides 17 and 18.

---

## 7. Fixed inputs — this canon may not contradict them

- **ADR-380 §5** — Rung-2 autonomous judgment is out of the **vision**. No "under a judgment you control" anywhere.
- **ADR-414 D1** — the moat sentence is ratified; only its slot was ever in play.
- **ADR-460** — an Agent at the desk is the member's hands, not a principal. §2.2's honesty rule.
- **ADR-490** — the price shape. Every claim must be true of a free two-person workspace.
- **ADR-378** — no org-above-workspace layer. No "for your company", no team accounts.
- **ADR-457 D5** — two doors, one commons. The interop face is promoted in GTM priority, never at the cost of the desk.

**One kernel dependency, stated as an invariant request**: an external LLM over the interop face must remain a **first-class principal** in the ledger (`foreign-llm` / `a2a`, ADR-445). If a future pass collapses those into member attribution the way ADR-460 collapsed kernel Agents, then *"work with ChatGPT, Gemini, and Claude together"* becomes one principal in three faces, and §2.2's activation species disappears. This needs an ADR that says so.

---

## 8. Falsifiers — armed, and evaluated against declared criteria

1. **The wedge.** Within 60–90 days of leading with the MCP door: if connector-origin users do not open the desk — no second surface, no keep, no share — then MCP is a feature of other people's products, not a door into ours. Revert the lead to the shared team commons.
2. **ADR-457 D8.2 / ADR-460 §8** — if settle goes unused after honest staging, **do not GTM-lead with it.** Currently fenced; not in this canon's lead.
3. **ADR-486 D8.2** — if briefs go unopened, **do not GTM-lead with Radar.** Currently fenced; not in this canon's lead.
4. **Correction owed to ADR-457 D8.3.** As written — *"MCP traffic dwarfs desk traffic → the hum is the true wedge; flip priority back"* — it would **fire on success**, since MCP dominance is this canon's expected acquisition pattern. It must be re-cut to distinguish *MCP as the acquisition door* (expected, good) from *MCP as the whole product* (the real failure, which is falsifier 1 above).

---

## 9. Owed, and not yet answered

Both prior ICP documents died holding unanswered founder-validation questions. To avoid a third:

1. **Three real instances of a multi-principal ledger** — any species. If none exist, §2.2 is theory.
2. **How many AIs a real prospect actually uses, and whether the fragmentation registers as a grievance or as normal life.** The entire triad rests on *plural* being **felt**, not merely true.
