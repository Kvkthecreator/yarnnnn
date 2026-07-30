# yarnnn — Canon Lock v2

**Date**: 2026-07-30
**Status**: **LOCKED — as working canon.** Operator-ratified in the 2026-07-30 re-cut discourse. *Working canon* is the operator's own marking: locked in full and binding on every downstream surface, **and** explicitly subject to evolve by discourse — the hook, the recognition, and every second-order derivation are working positions, not never-changing ones. The maintenance rule is unchanged and is what makes evolution safe: **one sentence per slot; a new candidate replaces, never accumulates.**
**Authority**: This document supersedes [CANON-LOCK-2026-07-29](CANON-LOCK-2026-07-29.md) in full and is the source of truth for the one-liner, the ICP, the GTM motion, and the activation model. Where NARRATIVE, GTM_POSITIONING, ICP.md, GROWTH-LOOP, the site, or the deck disagree with this document, they are wrong and get revised.
**Derivation**: the 2026-07-30 session discourse (this repo's operator + Claude), reassessing the 07-29 lock from first principles. Three findings drove the re-cut: (1) the 07-29 lock's own §9.2 validation question — *is plural-AI fragmentation felt as a grievance?* — answered itself in the negative at the first operator re-read; (2) a production-ledger probe answered §9.1 with receipts (see §9 below); (3) the enterprise-vs-teams question resolved by naming the constraint honestly — no enterprise accommodations exist or are promised, so the plurality orientation is **room-sized**: teams, not enterprises, with ease/share/out-of-box as the qualifying psychography.
**Not in scope**: architecture. This document never overrides an ADR; where it depends on one, §7 names it.

---

## 0. The psychographic center (new in v2 — everything below derives from it)

> **The small team (2–5 heads, starting at 1) that already works with AI every day — and for whom getting that work in front of each other is still copy-paste.**

The felt Tuesday-morning state: the real work happens in a private AI chat window; the shared work lives somewhere else; the bridge between them is paste. **Ease is not a feature preference for this buyer — it is the adoption condition.** They will not sit through setup, and nobody has to approve the purchase.

What fell with the 07-29 center: plural-AI **fragmentation** as the load-bearing grievance. It was flagged un-validated by the 07-29 lock itself (§9.2) and did not survive the first operator re-read — an investor-legible grievance (platform risk, lock-in) projected onto a buyer who experiences vendor memory as convenience. Fragmentation demotes from grievance to a common *trait* of the segment (still real for targeting and analytics; absent from copy).

Why not enterprises, said plainly: a solo founding team with no enterprise privacy/compliance apparatus cannot serve procurement — and does not need to. The workspace-as-outermost-unit ceiling (ADR-378) makes the constraint the position: **a room, not an org tree.** Bottom-up, self-serve, the product does the selling.

## 1. The one-liner canon — four slots

**Maintenance rule**: one sentence per slot. A new candidate **replaces**; it never accumulates.

### Slot 1 — MOAT (investors, internal discipline) — ratified-stable

> **yarnnn is the system of record where human and AI work settles.**

Ratified ADR-414 D1. Unchanged through both locks. Never used as the product sentence (ADR-457 §1: *"a settlement layer generates trust, not sessions"*). Note post-ADR-507: "settles" here is a property of the record, not a product verb — the settle *feature* was deleted; the moat statement is unaffected.

### Slot 2 — PRODUCT (the buyer, the site, the deck cover)

**Headline — ratified-stable (the operator's original premise, confirmed):**

> # your true AI-first workspace.
> # co-work like never before.

**Subhead — working canon (re-cut in v2 around ease + share):**

> One shared workspace for you, your people, and the AI you already use.
> Nothing to set up — connect, co-work on shared files and documents, share with a link.
> And every change signed by whoever made it, human or not.

Three deliberate moves: (1) **the three model names leave the hero** — *"the AI you already use"* does the out-of-box work better and stops spending the most expensive copy real estate on three competitor brands; the names move to the connector chips directly under the CTA, where the engine rule still permits them. (2) **"Nothing to set up" enters as a claim, and it is ledger-true today** — no wizard, no constitution, no program pick, no first-task ceremony (ADR-437 D1, ADR-414 D4 pure genesis — deleted, not hidden). It is guarded by falsifier 5 (§8). (3) **The signed clause is untouched and non-optional** — it remains the one line no competitor can write truthfully, and the mechanism the *"AI-first"* capability adjective requires in the same visual field.

### Slot 3 — HOOK (the problem; opens the deck and the site) — working canon

> **Made with AI. Lost in the chat.**

Six words, parallel structure, loss-shaped, layman-parseable on a billboard. It compresses the center: the work is real (*made*), the container betrays it (*lost*), and the headline reads as the rescue. The 07-29 hook (*"Every AI keeps its own copy of your work. You don't."*) is retired from this slot and returns to where its psychology belongs — the investor deck's problem chapter, where dispossession lands (it is a moat-audience claim: true, defensible, and unfelt by a buyer who experiences vendor memory as a feature).

### Slot 4 — RECOGNITION (what the buyer says about themselves) — working canon

> **"I'm the human clipboard between my AI and my team."**

A coinage, deliberately: self-deprecating, instantly understood by anyone who has copy-pasted AI output into a doc, and reusable as campaign vocabulary (*"stop being the clipboard"* is a CTA, a testimonial prompt, and a meme-able line downstream of one sentence). Sits below the fold at the conversion point, not in the hero.

**Bench note (discipline, not accumulation)**: the 07-30 discourse produced alternates for slots 3–4 (*"Your best work is stuck in a chat window"* · *"Great work happens in your AI chats. Then it dies there"* · *"Half my job is copy-pasting AI answers into docs"* · *"Somewhere in my chats is the best version of this. I just can't find it."*). They are recorded here once as replacement candidates for future discourse and appear nowhere else. The slots carry one sentence each.

### The hero, assembled (the sequence every surface derives from)

```
Made with AI. Lost in the chat.                          ← hook

  your true AI-first workspace.                          ← headline
  co-work like never before.

One shared workspace for you, your people, and the       ← subhead
AI you already use. Nothing to set up — connect,
co-work on shared files and documents, share with
a link. And every change signed by whoever made it,
human or not.

[ Co-work with the AI you already use → ]                ← CTA (lead door)
  ChatGPT · Claude · Gemini                              ← connector chips

…below the fold, at the conversion point:
"I'm the human clipboard between my AI and my team."     ← recognition
```

The arc: **loss → rescue → how → proof → self-recognition.** Each line is answered by the next; no technical noun required anywhere.

---

## 2. The ICP

### 2.1 The qualifying triad — working canon

> **AI-first · Shared · Self-serve**

| Qualifier | Meaning | The job it carries |
|---|---|---|
| **AI-first** | They work with AI daily; the AI output *is* the work, not a garnish. | The capability register, and the usage-revenue leg — volume of AI work → PAYG (ADR-490's 30% margin needs volume). |
| **Shared** | At least one other principal touches the work — a teammate, or their own connected AI. | The moat's entry condition (ADR-465) and the seat-revenue leg. **Note the correction from the 07-29 lock**: the second principal never required *plural AIs* — one human plus their one connected ChatGPT is already a two-principal ledger. The single-AI user is readmitted to the funnel. |
| **Self-serve** | They adopt tools that work in the first session — no procurement, no pilot, no admin. | The GTM motion fit (free-to-value, bottom-up) and the implicit enterprise filter. |

**Disposition of the old triad**: *plural* demotes to a common trait (targeting/analytics, never copy). *Consequential* and *continuing* demote from qualifiers to expected traits — still true of the buyer, no longer the filter.

**Register**: prosumer duos and small teams, 2–5 heads, arriving as one person who invites. This is the ADR-490 price shape read backwards — **two free seats *is* the ICP**: the duo is the free product; the third head is the business.

### 2.2 The second principal — three species (unchanged, functions intact)

| Species | Arrives | Cost | Function |
|---|---|---|---|
| **An external AI** — `foreign-llm` / `a2a` over the interop face | Day one, no invite, no seat | Free, unlimited | **Activation** |
| **Agents at the desk** — the member's hands | Out of the box | Free | **Engagement** |
| **A human colleague** — invite or `/s/{token}` | When invited | 2 free, then $20/head | **Revenue** |

**Binding honesty rule (unchanged)**: agents at the desk are **the member's hands, not principals** (ADR-460; the ledger says `member:… via …`). Never marketed as colleagues, teammates, or a second principal. The species that make the ledger multi-principal are the external AI and the human.

This table is *more* load-bearing under v2 than under v1: the **Shared** qualifier counts a connected AI as a real principal at N=1 AIs — which is true **only while [ADR-504](../../adr/ADR-504-the-interop-principal-invariant.md) holds** (the interop principal invariant, still Proposed; ratification owed).

### 2.3 The anti-ICP — two-sided, both psychographic — working canon

1. **The procurement buyer.** Needs SSO, compliance, an admin console, an org tree. Deliberately unserved — by architecture (ADR-378), not merely by staffing. Never named in copy; the self-serve posture filters them.
2. **The AI-dabbler.** AI as occasional autocomplete; their real work is happy in Google Docs. No felt gap for the hook to press.

The 07-29 anti-ICP (*the single-AI user*) is **retired**: under this center they are a qualified buyer (see §2.1 Shared). **Posture: implicit.** No gating question, no qualification form; the copy and the motion do the filtering, and conversion data tells us who was right.

### 2.4 Owed

`ICP.md` §5 demographics stub stands (validated, not hypothesised — the three dead Deep-Dives remain the cautionary precedent), with one dimension re-cut: *which AIs and how many* demotes to a targeting datum; **the new load-bearing validation question is whether the copy-paste seam registers as a grievance** (§9.2).

---

## 3. GTM

### 3.1 Motion (unchanged from v1)

> **Free-to-value, expand by head. Two revenue legs: seats and usage.**

Seats — two humans free per workspace; $20/mo per human from the third (ADR-490). Usage — PAYG at provider cost × 1.30; thin, needs volume — which is why **AI-first** (not *plural*) now carries the volume qualifier. Shape — prosumer/small-team, land-free-and-expand; early Figma or Linear, not a vertical seat. The v1 overrule of *"never a volume play"* stands as recorded.

The ease-psychography strengthens the motion's derivation: ease → volume is the same arrow the price list needs.

### 3.2 The wedge (structure unchanged; rationale simplified)

> **The first co-work moment.**

```
MCP door        →   the desk      →   the share link
first co-work       daily co-work     co-work with a person
acquire             retain            expand
(free, day one)     (free)            (paid at head 3)
```

The MCP door remains the acquisition wedge — and under the ease center its CTA no longer needs a plurality rationale: **"Co-work with the AI you already use"** now reads as *give the work you're already doing in ChatGPT a place to land*. Rationale simplifies to three legs: the only lead unfenced by an armed falsifier; the only channel where the second principal arrives free on day one; and it demos the moat in sixty seconds with no tenure. (The v1 fourth leg — connector directories pre-qualify for *plural* — is dropped with the plural center; directories remain distribution.)

### 3.3 Competitive frame — three camps (unchanged)

| Camp | Who | What they lack | The line |
|---|---|---|---|
| **Model makers** | OpenAI · Google · Anthropic | Neutrality. One vendor, sealed. | "Your context lives in their product, not yours." |
| **Agent memory** | Mem0 · Zep · Cognee | A place to work. Memory without a workspace. | "Memory remembers. It doesn't co-work." |
| **AI-retrofitted workspaces** | Notion · Slack · Google Workspace | AI as a principal. Built for humans, AI bolted on. | "Their AI is a feature inside a human tool. Here, AI is a principal in the workspace." |

Camp three remains what **"true"** in the headline is aimed at — and hook candidate A from the discourse bench (*"AI changed how you work. Your workspace didn't notice."*) is the camp-three pressure line, available to the deck's competition chapter.

**A fourth boundary, named but not a camp**: enterprise suites on the procurement motion. We do not compete there — that is the anti-ICP's first face, filtered by posture, never argued in copy.

### 3.4 Proof asset (unchanged)

**The attribution walk** — *"Composed from — open any source · you · Aug 2 · your agent · Aug 5 · Claude · Aug 6."* Multi-principal attribution as a picture, not a claim; structurally unrenderable by a single-vendor host; the only place the moat is felt; chapter one, directly after the hook. **Receipt (new, 2026-07-30)**: this picture now exists in the production ledger — see §9.1.

### 3.5 Pricing facts (from ADR-490 — quote these, not the old ones)

Two humans free per workspace · $20/mo per human from the third · usage pay-as-you-go, funded by the $3 signup grant and top-ups · hard stop at zero · no monthly allowance · no solo plan to buy · AI principals free and unlimited · dollars shown only at purchase, consumption shown as usage-%.

---

## 4. Activation

### 4.1 Definition (unchanged)

> **Activated = the first co-work moment: two distinct principals with attributed revisions on the same file.**

Metric: **time-to-first-co-work-moment**, readable from the existing ledger with no new telemetry (the 07-30 probe ran exactly this query against production — §9.1).

### 4.2 Two channels only (unchanged)

**Channel 1 — cold discovery. LEAD DOOR: connect your AI first.** Primary CTA: **"Co-work with the AI you already use."** The second principal exists before the member has authored anything; the first thing they see at the desk is a write they didn't make, signed by something that isn't them.

**Channel 2 — invited / shared.** `/s/{token}` → member grant → land on the shared artifact with `trace` visible, inside a populated commons (shipped — ADR-437 Phase D, ADR-465).

### 4.3 What activation is not (unchanged)

No setup wizard · no workspace constitution · no program pick · no roster discovery · no first-task ceremony · no blank-canvas empty state. Entry is a flow, not a ceremony (ADR-465). **Under v2 this list is promoted from hygiene to promise**: the subhead now says *"nothing to set up"* out loud, so every item on this list is copy-load-bearing.

### 4.4 Metrics (one addition)

| | Metric |
|---|---|
| **Primary** | Time-to-first-co-work-moment — **now with a target class: minutes, not days** (falsifier 5) |
| Secondary | Connector-attach rate (cold) · share→accept rate (warm) · third-head rate (revenue) |
| Guardrail | Desk-return rate among connector-origin users (falsifier 1) |

### 4.5 Named build dependency — escalated

**ADR-437 Phase C hardens from wedge-dependency to product-sentence-dependency.** Under the v1 lock, a clunky connector attach weakened the lead door. Under v2, *"nothing to set up"* is in the hero — a clunky attach doesn't weaken the strategy, **it falsifies the copy**. The sixty-second connect (ADR-494 registry → attach → first foreign write lands signed) is the first build priority by this canon's own logic.

---

## 5. Vocabulary

**Live**: co-work (verb/adjective only, lowercase, never a product noun) · AI-first (always with mechanism) · **signed** (the layman word for attribution) · shared workspace · room · members · invite · share · **the human clipboard** (coined campaign vocabulary — *"stop being the clipboard"*) · **nothing to set up** (guarded by falsifier 5) · hub · sweep · brief · Projects · seat (a human head, one meaning only).

**Removed from the live list (ADR-507)**: *keep* as a product verb — the Keep/settle affordance was deleted; distillation is something a member asks for in conversation. ("Keep" survives in ordinary English use, never as a named product act.)

**Retired — do not use in any external surface**: everything on the 07-29 retired list (standing delegate · the judgment seat · delegation dial · persona-as-entity-class · cast · agents you own · under a judgment you control · five domain experts · the trust dial is the pricing axis · operator (external) · $19/mo · per-operation pricing · the Specialist palette · "the team you build by chatting") **plus, newly retired from buyer-facing slots**: *"Every AI keeps its own copy of your work. You don't."* (investor deck problem chapter only) · *"I use three different AIs, and I'm the only thing connecting them."* (retired outright — the felt version of plurality is repetition, and the slot now carries the clipboard).

**The mechanism discipline** (verbatim, both locks): capability adjectives — *persistent, compounds, autonomous, AI-first, runs in your absence* — **never** appear without their mechanism: *owned, attributed, signed by whoever made it.*

**The roster rule**: app names may appear in the product chapter and **never** in the hero, the subhead, or above the fold.

**The engine rule** (ADR-420 §10): model names as connector chips is positioning; a model-count comparison table is the treadmill. (v2 note: the names now live in the chips, not the subhead — the rule is easier to keep.)

---

## 6. What this supersedes

[CANON-LOCK-2026-07-29](CANON-LOCK-2026-07-29.md) in full (banner applied) · the 07-29 renderings inside ESSENCE §The Canon Sentences + §Canonical Positioning, ICP.md v1 §2/§4, NARRATIVE v6 Beats 1/3/6 + vocabulary, GTM_POSITIONING v5 §1/§2, GROWTH-LOOP v1 — all re-cut in the same commit as this lock · deck hook chapter + slide 17 (re-cut owed at next deck pass).

## 7. Fixed inputs — this canon may not contradict them

- **ADR-380 §5** — Rung-2 autonomous judgment is out of the vision. No "under a judgment you control" anywhere.
- **ADR-414 D1** — the moat sentence is ratified; only its slot was ever in play.
- **ADR-460** — an Agent at the desk is the member's hands, not a principal (§2.2's honesty rule).
- **ADR-490** — the price shape. Every claim must be true of a free two-person workspace.
- **ADR-378** — no org-above-workspace layer. No "for your company", no team accounts — and under v2 this ceiling is a *positioning asset* (§0: a room, not an org tree).
- **ADR-457 D5** — two doors, one commons. The interop face is promoted in GTM priority, never at the cost of the desk.
- **ADR-507** — the acts are open (Think · Make · Perceive); the settle verb is deleted; no copy may name settle/keep as a product act. The moat sentence's "settles" is a property of the record.
- **ADR-504 (Accepted — operator-ratified 2026-07-30)** — the interop principal invariant. The Shared qualifier and the activation species both stand on it; the ratification binds: collapsing interop attribution into member attribution now requires superseding that ADR in the open. The companion signature-grammar enforcement (write-door taxonomy validation + gate) landed the same day.

## 8. Falsifiers — armed, and evaluated against declared criteria

1. **The wedge** (unchanged). Within 60–90 days of leading with the MCP door: if connector-origin users do not open the desk — no second surface, no share — then MCP is a feature of other people's products, not a door into ours. Revert the lead to the shared team commons.
2. **Settle — RETIRED with the verb** (ADR-507). Read before removal; did not fire on its own terms (low adoption ≠ abandonment); the retirement was structural. No successor needed — nothing in this canon leads with settle.
3. **Radar/briefs** (unchanged, ADR-486 D8.2) — fenced out of the lead until proven opened.
4. **ADR-457 D8.3 — re-cut LANDED (2026-07-30, same-day amendment pass).** MCP-as-acquisition-door (expected) is distinguished from MCP-as-whole-product (the real failure, owned by falsifier 1's desk-return guardrail) in ADR-457 §D8 itself.
5. **The ease claim (new in v2).** If the median cold-signup → first-co-work-moment is not measured in **minutes** once the lead door ships, *"nothing to set up"* comes out of the subhead — the claim is aspiration, not copy. Same ledger query as the primary metric; no new telemetry.

## 9. Validation state — receipts, and what is still owed

The 07-29 lock's §9 asked two questions and answered neither. One is now answered with production receipts; the other is re-cut.

### 9.1 Multi-principal ledger instances — ANSWERED 2026-07-30, partially

Probe run against the production ledger (`workspace_file_versions` × `principal_grants`), the exact activation query:

- **Two same-file co-work instances exist** (bar was three): `d5b9029b` — `/workspace/inbound/mcp/claude/inbox.md`, operator + `yarnnn:mcp:Claude`; `aa129d3c` — `/workspace/operation/memory/q3-pricing-note.md`, operator + `yarnnn:mcp:claude-desktop` (26 revisions).
- **One workspace is genuinely rich**: `d5b9029b` holds five distinct principals across all three species — owner, a second human member, and two external AIs (ChatGPT + Claude).
- **Both instances are founder-adjacent; 10 of 11 workspaces are single-principal diaries.**

**Honest classification: demonstrated, not validated.** The ledger mechanically renders multi-principal co-work exactly as the attribution walk claims — the picture exists in production. Zero third parties have produced one. A third, non-founder instance is still owed; the falsifier-1 clock is the validation instrument.

Two defects surfaced by the same probe, owed fixes outside this canon: **(a)** malformed attribution forms in the live ledger (`kvkthecreator@gmail.com via Claude Sonnet`, `probe via Claude Sonnet` — free-text shapes the `member:{id} via {model}` taxonomy forbids); if *"signed by whoever made it"* is the subhead, the signature grammar is product surface and the write door must enforce it (ADR-504-adjacent). **(b)** The interop face has been dormant since 2026-07-09 — three weeks, including the founder's own workspace. Before the lead door ships, the cheapest §9.2 evidence is the founder walking their own door daily.

### 9.2 The felt grievance — RE-CUT

The v1 question (*does fragmentation register as a grievance?*) answered itself in the negative and is retired with the plural center. The successor question, owed founder validation before the hook ships to strangers: **does the copy-paste seam register as a grievance — do real AI-first workers feel "made with AI, lost in the chat," and do they recognize themselves as the clipboard?** Test material: the hook, the recognition sentence, and the bench alternates in §1.
