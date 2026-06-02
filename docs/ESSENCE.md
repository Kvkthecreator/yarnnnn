# YARNNN Essence

**Purpose**: Canonical product narrative. What YARNNN is, what users are buying, and what must remain true as the implementation evolves.
**Status**: Active
**Date**: 2026-01-28
**Updated**: 2026-06-02 (v13.0 — substrate-first rewrite. The product is re-centered on **authored, attributed, portable context** as the floor (the Phase-1 wedge), with **declared intent + a judgment seat + ground-truth evaluation** as the additive judgment layer on top (Phase 2). Supersedes the v12.x "team you build by chatting / money-truth cockpit" framing. Grounded in THESIS (four commitments), the sequenced-moat-strategy analysis (substrate as floor, judgment as rider), ADR-310/311 (one moat, two faces — cockpit + interop), ADR-222 (kernel/program OS framing), ADR-216 (orchestration vs judgment), ADR-231 (task abstraction sunset). Money-truth demoted from a universal product element to a program-specific flavor of ground truth.)

---

## Core Thesis

YARNNN is the **authored context layer that travels with you** — and, when you're ready, an operation that runs on it under a judgment you control.

There are two layers, and the lower one stands on its own:

- **The substrate layer (the floor).** You author your work — notes, documents, decisions, accumulated domain context — and every piece of it is **attributed, retained, and yours**. It's a context commons in a format every LLM speaks, reachable from any model you already use. This is valuable the moment you author anything; it needs no program, no mandate, no autonomous agent.
- **The judgment layer (additive, on top).** Activate a program and that same substrate gets a **declared mandate**, a **Reviewer** (an independent judgment seat), and an **operation that runs in your absence** — evaluated against ground truth. This deepens the substrate from *portable* to *judged and operated*. It never replaces the floor.

**The product promise in one sentence:**
> Author your context once. Carry it into every AI — and, when you're ready, let it run under a judgment you control.

Short form: *Your context, attributed and portable.*

The relationship is **authorship, not delegation**. The substrate is the user's — legible, correctable, and sovereign — and switching cost accumulates from the first thing they author.

## What Stays Constant

The product essence has five stable elements. They are ordered floor-first: the earlier ones are true with the lightest possible substrate; the later ones are what a program adds.

1. **Authored context, not inferred context**
   Every file has a declared author (operator, YARNNN, a named agent, the Reviewer, a system actor). Every mutation produces a parent-pointered revision with required attribution and a message. The operator can read, correct, and carry their context. Inferred context (what every incumbent builds — memory scraped from activity) commoditizes as retrieval saturates; authored context does not, because it is owned and inspectable (THESIS Commitment 4, FOUNDATIONS Axiom 1 + Authored Substrate / ADR-209).

2. **Portable across every AI, not locked to one model**
   Authored context is reachable from any LLM the operator already uses, via the interop face (MCP today; protocol-agnostic by design). No model provider offers your context *across* the others — they are each present-bound silos. Portability is structurally something only a neutral substrate layer can offer, and it is the wedge that stands alone before any judgment exists (ADR-310, ADR-311).

3. **Declared intent, not inferred purpose**
   When an operator activates a program, purpose is **authored** as a mandate, not discovered by inference. Everything downstream — context domains, recurrences, proposed actions — exists in service of the declared mandate. Inferred intent is undetectably wrong; declared intent is correctable because it is legible (THESIS Commitment 1, FOUNDATIONS Axiom 3).

4. **A judgment seat, not a safety filter**
   The role that decides whether a proposed action is fit to execute is the most important durable role in the system, and it is architecturally independent of the producers whose work it judges. The Reviewer reads the mandate, the accumulated context, the track record, and the proposed action, and renders a verdict. The seat persists; the occupant is interchangeable (human today, AI as it becomes credible). This is supervised autonomy: the operator is never structurally absent (THESIS Commitment 2, FOUNDATIONS Axiom 2, ADR-194).

5. **Ground-truth evaluation, not vibe-truth**
   In the domains where it applies, the Reviewer's judgment and the accumulated context are validated against a real outcome signal, not against internal agreement or user thumbs. The *flavor* of ground truth is program-specific — money-truth for a trading operation, publication/coherence for an authoring operation, revenue for commerce. Ground truth is structural, not universal; it is the spine of the judgment layer, not a claim about every workspace (THESIS Commitment 3, FOUNDATIONS Axiom 8).

These five compose. Take the substrate floor (1–2) alone and you have portable, sovereign context — already differentiated. Add the judgment layer (3–5) and the substrate becomes judged and operated. Remove any one of the five and what remains degrades into an existing inferior form (a wiki, a memory feature, a chatbot, a safety wrapper, a dashboard).

## The Two Layers, Concretely

### Layer 1 — Authored substrate, served everywhere (the floor)

A workspace is a filesystem of authored, attributed, retained context. The operator authors it through conversation with YARNNN, through uploads, and through accumulated work. Every revision is content-addressed and parent-pointered; nothing is silently lost; everything carries an author.

That substrate is reachable from any LLM via the interop face. What you author in YARNNN follows you into ChatGPT, Claude, or any model — attributed and portable. This layer requires no program, no Reviewer, no mandate. It is the entry value: *your context is yours, and it follows you.*

### Layer 2 — The judgment layer (what a program adds)

A **program** (alpha-trader, alpha-author, and future programs) is an application that activates on top of the bare substrate. It supplies:

- a **mandate** the operator declares,
- a **Reviewer persona** and principles the operator authors,
- **recurrences** that fire the operation on cadence,
- a **cockpit** — the supervisory surface where the operator consults performance, sees pending decisions, and audits the judgment trail,
- a **ground-truth signal** appropriate to the domain.

This is where the operation runs in the operator's absence and improves through supervision. It is additive: a Layer-1 operator has portable context; a Layer-2 operator has *judged* portable context plus an operation that runs without them.

## The System Shape

1. **Substrate** — the authored, attributed filesystem. The floor everything stands on. State lives in files; computation is stateless over them (FOUNDATIONS Axiom 1).

2. **The interop face** — the substrate reachable from any LLM. The distribution channel of the one moat: file + revision operations over the operator's context commons, attributed on every read (ADR-310/311).

3. **YARNNN (the orchestration surface)** — the chat surface the operator addresses. It keeps the workspace legible, drafts work, and routes mutations. It is orchestration, not a judgment persona — it is *how the operator drives the system*, not a seat that renders verdicts (ADR-216).

4. **The Reviewer** — the judgment seat (one per workspace). Reads proposed actions, renders approve/reject/defer, accumulates calibration over tenure. The seat where trust is earned (ADR-194).

5. **Programs** — applications that activate the judgment layer on bare substrate. They ship a mandate template, a Reviewer persona, recurrences, and a cockpit composition. Workspaces don't have *types*; they *run programs* (ADR-222).

6. **User-authored Agents** — persistent domain experts the operator creates through conversation. They hold domain intent and accumulate domain context. Optional; many-per-workspace.

## The User Experience Loop

There are two loops. The first is the floor; the second is what a program adds.

**Loop 1 — author and reach (every workspace):**
1. Author context — through conversation, uploads, or accumulated work.
2. It is attributed and retained — a revision chain you can inspect.
3. Reach it from any AI you use — your context follows you.

**Loop 2 — declare, judge, operate (programs):**
1. Declare a mandate — what the operation is for.
2. The operation runs on cadence — proposing actions against accumulated context.
3. The Reviewer judges proposals against the mandate and ground truth.
4. The operator supervises — approves, redirects, refines — and the judgment trail accumulates.
5. Calibration, context, and preferences compound; future supervision gets lighter.

Loop 1 is the product's floor. Loop 2 is the deepening.

## Why This Is Different

Most AI systems fail recurring, high-context work for one of two reasons: they are **session-based** (forget context between runs) or **persistent but inferred** (the context is scraped, shallow, and the operator can't see or carry it).

Every major platform is building an inferred-context layer (OpenAI Memory, Microsoft Copilot + Graph, Google Workspace Intelligence, Anthropic Projects). All infer context from activity. Inferred context commoditizes as model capability saturates.

YARNNN's position is the opposite stance: **context is authored, attributed, retained, and portable.** It does not commoditize — it gets richer per operator per month of use, and it travels across any model, any agent layer, any future incumbent. On top of that authored floor, an independent judgment seat makes the operation trustworthy in a way a self-critiquing producer never can.

## The Moat

There is **one moat: authored substrate under a persona-bearing judgment seat.** It is served two ways — a **cockpit face** (the operator, in-app) and an **interop face** (any LLM, via MCP). The two are faces of the same moat, not two moats (ADR-310).

- The substrate is the differentiator that exists *before* any judgment: attributed, retained, LLM-native, portable. No competitor's agent-filesystem exposes an attributed, walkable revision chain across the boundary.
- The judgment seat is where accumulation compounds and trust is earned: the longer the Reviewer runs against ground truth, the harder its calibrated judgment is to replicate elsewhere.

Inferred-context layers commoditize. Authored substrate, judged over tenure, compounds.

## What YARNNN Is Not

YARNNN is not:

- **an inferred-memory feature** — context is authored and attributed, not scraped from activity.
- **locked to one model** — the substrate is portable across every LLM; that is the point.
- **a chat UI** — YARNNN the chat surface is how the operator drives a running system, not the whole product.
- **a safety-filter wrapper** — the Reviewer is an independent judgment seat that compounds in value, not a post-hoc guardrail bolted onto a producer.
- **uncontrolled autonomous action** — the model is supervised autonomy: declared mandate, gated actions, a legible cockpit, and an operator who is never structurally absent.
- **a money-making claim for every workspace** — money-truth is one program's flavor of ground truth (trading), not a universal product element. The universal is *authored, portable substrate*.

## Canonical Positioning

External framing is Path B (YARNNN as a platform for operators), per the communication discipline in THESIS + ADR-210.

**Primary:**
> Author your context once. Carry it into every AI.

**Short form:**
> Your context, attributed and portable.

**Expanded:**
> YARNNN is the authored context layer that travels with you. You author your work — attributed, retained, sovereign — and reach it from any LLM you already use. Activate a program and that same substrate gets a declared mandate, an independent Reviewer, and an operation that runs in your absence under a judgment you control. The substrate is the floor; judgment is what you add on top.

Short forms that remain valid in voice-variation contexts:

- **Your context, everywhere you think.**
- **Authored, not inferred.**
- **The substrate that follows you — judged when you're ready.**

## Source Of Truth Hierarchy

For product narrative and architecture, use this order:

1. `docs/ESSENCE.md` — product essence and stable value proposition (this doc)
2. `docs/architecture/THESIS.md` — the philosophical claim and the four commitments
3. `docs/architecture/FOUNDATIONS.md` — first-principles cognitive architecture (six dimensions, eight axioms)
4. `docs/adr/ADR-310-judged-substrate-interop-face.md` + `ADR-311-primitive-interop-surface.md` — one moat, two faces; the interop surface
5. `docs/adr/ADR-222-agent-native-operating-system-framing.md` — kernel / program OS framing
6. `docs/adr/ADR-209-authored-substrate.md` — authored, attributed, retained substrate
7. `docs/adr/ADR-194-pluggable-reviewer-and-impersonation.md` — the judgment seat

If lower-level docs contradict this essence without justification, the lower-level docs should be revised.
