# Analysis — Phase 2: Internal Agents (Freddie, and User-Created Persona Agents)

**Date**: 2026-06-26
**Hat**: B (external-developer discourse — forward vision. Conceptual; recommends Hat-A ADRs, makes no canon change.)
**Status**: Proposed framing for operator (KVK) ratification. **Conceptual / non-binding.** This doc is the *vision* the Phase-2 ADRs will cite; it does not decide implementation, schema, or vocabulary at canon strength.
**Trigger**: [ADR-375 rewrite](../adr/ADR-375-phase-1-substrate-for-humans-and-external-agents.md) (2026-06-26) drew the Phase-1/Phase-2 line and *named* two Phase-2 cuts (the Reviewer→Freddie rename; user-created agent seats) without building them. KVK asked to record the Phase-2 vision separately so the downstream ADRs inherit a coherent picture rather than re-deriving it — and so Phase-1 work can proceed with focus.
**Relationship to canon**: Phase 1 is the ratified direction (ADR-373 substrate + ADR-375 product definition + ADR-374 IA). This doc is **strictly downstream** — nothing here gates or blocks Phase-1 launch. It exists so that when Phase 2 begins, the framing is already settled.

---

## 0. Why this doc exists (and what it deliberately does NOT do)

[ADR-375](../adr/ADR-375-phase-1-substrate-for-humans-and-external-agents.md) made one cut cleanly: **the agent in the Phase-1 wedge is the EXTERNAL operator** (a principal — human-equivalent caller — using YARNNN via the interop face), **not** any YARNNN-internal component. That cut left two *internal*-agent concepts named but unbuilt, deliberately walled off so they could not re-blur Phase 1:

- **Cut 1 — Freddie**: the internal steward (today "the Reviewer"), renamed and hardened into the de-facto YARNNN system agent.
- **Cut 2 — user-created persona agents**: agents *the user authors inside YARNNN* to hold standing intent on their behalf.

This doc records the **vision** for both, plus the **third actor already settled in Phase 1** (the external agent), so all three sit in one frame. It is intentionally **conceptual**: it does not pick table names, primitive signatures, or final labels. Those are the Phase-2 ADRs' job. The value here is the *taxonomy and the boundaries* — getting the actor model right so the downstream work has a spine.

**What this does NOT do:**
- Does not rename anything in code. "Freddie" is a *proposed* label; the internal slug stays `reviewer` until a Phase-2 ADR says otherwise.
- Does not block, gate, or alter Phase-1 launch. Phase 1 ships with the internal steward dormant-behind-a-flag (ADR-375 §6); none of this is a prerequisite.
- Does not decide Cut-2's mechanics (lifecycle, creation surface, trust model). It frames the *concept* and flags the open questions.

---

## 1. The three agent-actors, held apart

The persistent confusion in the canon has been **one word, "agent," for three different things.** Naming them as three distinct actors — by *where they sit* relative to the workspace and *who authors them* — dissolves it.

| Actor | Where it sits | Who authors it | Phase | Analogy |
|---|---|---|---|---|
| **External agent operator** | OUTSIDE — a caller reaching in over the interop face | a third party (the agent's own builder/operator) | **Phase 1 (ratified)** | a customer's coding agent hitting the GitHub API |
| **Freddie** — the system agent | INSIDE — the single workspace-level steward seat | YARNNN (platform-authored, operator-tuned) | **Phase 2, Cut 1** | a bank's fiduciary who acts on your mandate in your absence |
| **User persona agents** | INSIDE — N user-authored seats | the operator (via YARNNN) | **Phase 2, Cut 2** | staff you hire and brief, each with a job and a voice |

The decisive axes:

- **External vs internal.** The external agent is a *principal* (ADR-373) — it authenticates, gets a grant, attributes as itself, and is **authorized**, never *trusted by default*. Freddie and user persona agents are *internal* — they are components/seats the workspace runs, with standing intent and substrate homes.
- **Platform-authored vs user-authored.** Freddie is one, systemic, platform-shipped (the operator tunes its persona but does not *create* it). User persona agents are zero-to-many, **created by the operator**, each a distinct authored entity.
- **One vs many.** Exactly one Freddie per workspace (the seat is singular — ADR-194). User persona agents are an open set.

The prior canon (ADR-216) actually anticipated this split — "Reviewer (sole systemic Agent)" vs "user-authored domain Agents." What the ADR-260→345 arc did was let *Reviewer* quietly absorb the role of "the actor / the judgment," at which point "Reviewer" (a *seat* name) and "the system agent" (a *thing* name) needed to separate. **Freddie is that separation made explicit.**

---

## 2. Cut 1 — Freddie: naming and hardening the internal system agent

### 2.1 The problem Freddie solves

"Reviewer" was always a **seat** name (ADR-194: one judgment seat per workspace, occupant-agnostic — human, AI, or impersonation could fill it). Through ADR-260→345 the *AI occupant* of that seat became *the* actor: it holds the mandate as the same principal across wakes (ADR-319 stewardship), reasons capital-EV over ground-truth, takes accountable action, self-amends its own rules over tenure. It is no longer "a reviewer of proposals" — it is **the fiduciary that runs the operation in the operator's absence.**

Calling that fiduciary "the Reviewer" now *under-describes* it (it does far more than review) and *conflates seat with occupant* (ADR-315 already carved seat≠occupant — Freddie is the occupant's name). The rename is the honest move: **the seat stays "the steward seat"; its hardened occupant gets a proper name — Freddie.**

### 2.2 Why "Freddie"

Frankenstein. Freddie is **the creature we deliberately built and are hardening** — assembled from parts (the wake architecture, the persona-frame, the principles, the ground-truth loop), brought to life, and *accountable*. The name carries the right connotation: not a stateless assistant bolted on, but a constructed, named, standing entity we are responsible for. It also gives the system agent a **brand-able identity** the operator can relate to ("Freddie flagged this", "Freddie's track record"), which "the Reviewer" never afforded.

*(Open: whether "Freddie" is the literal shipped label or a working name for a later operator-facing brand. Conceptual at this stage. The internal slug `reviewer` is preserved regardless — a rename of the user-facing label, not a schema migration, exactly like ADR-251's "System Agent" relabel kept the `thinking_partner` slug.)*

### 2.3 What "hardening" means (the substance, not the name)

The rename is the *surface*; the substance is that Freddie's role has already converged and should be *named as converged and made first-class*:

- **Accountable standing intent** (ADR-319 stewardship; ground-truth moves intent, operator pressure never does).
- **Self-improvement over tenure** (the proven moat headline — judgment improves, causation-controlled; tenure-rule-revision closed CONCERN-3).
- **The aperture/floor discipline** (ADR-342/343 — Freddie may widen what the operation engages but never lower the per-act integrity floor).
- **The standing obligation** (ADR-344 — Freddie is accountable for the mandate's *reachability*, not just its rules).
- **Workspace-level, not per-user** (already designed this way — `mcp_composition.py` foreign-write wake "fires for the WORKSPACE that owns this substrate"; the multi-principal arbiter role is latent, ADR-373).

In the **multi-principal** world (ADR-373), Freddie's role *clicks into full strength*: it is **the accountable arbiter across principals** — it places and judges what *any* principal (human, external agent, platform, foreign LLM) wrote to the commons, and none of them individually owns the truth. Single-principal Freddie judges *my* writes against *my* ground-truth (thin); multi-principal Freddie reconciles a heterogeneous swarm's contributions into its own `reviewer:` (→ `freddie:`?) revisions. **Freddie is the steward rung at full strength — and it only matters once the workspace is multi-principal.** This is *why* Freddie is Phase 2: it needs the Phase-1 substrate (multi-principal, populated, attributed) as its fuel and its subject.

### 2.4 The Freddie ADR (downstream)

A future Hat-A ADR owns this. Its likely shape:
- **Rename the user-facing label** Reviewer/System-Agent → Freddie (occupant, not seat); preserve internal slugs (`reviewer`) and the seat canon (ADR-194/315).
- **Promote the converged role to canon** — name Freddie as the accountable fiduciary + multi-principal arbiter (fold the ADR-319/342/343/344 stance into one "this is what Freddie IS" statement).
- **Decide the attribution prefix** — does `reviewer:` become `freddie:`, or stay `reviewer:` with Freddie as the display name? (Lean: keep the slug, rename the label — Singular-Implementation + GLOSSARY enum-exception precedent.)
- Touch `reviewer-occupant.md` + `occupant_contract.py` (the published ABI) + GLOSSARY.

---

## 3. Cut 2 — user-created persona agents

### 3.1 The concept

A **second** kind of internal agent: an agent **the operator authors inside YARNNN** to hold standing intent on a *bounded domain* on their behalf. This is the original ADR-216 "user-authored domain Agents" — zero-to-many per workspace, each with its own `IDENTITY.md` + persona, each a distinct authored judgment entity. Where Freddie is the *one systemic fiduciary over the whole operation*, user persona agents are *the operator's authored staff* — each briefed for a slice.

The mental model: **Freddie is the management; user persona agents are specialized labor the operator hires and briefs.** (Maps onto the ESSENCE v14.1 substrate=asset / agents=labor / Reviewer=management framing in project memory — Freddie is the management seat; user persona agents are author-able labor with standing voice.)

### 3.2 Why it is a SEPARATE cut from Freddie (and from external agents)

It must not be conflated with either neighbor:

- **Not Freddie.** Freddie is singular, systemic, platform-authored, accountable for the whole mandate. A user persona agent is one-of-many, user-authored, scoped to a domain. Different lifecycle, different authority, different creation path.
- **Not an external agent.** An external agent operator is a *principal on the outside* (a caller with a grant). A user persona agent is an *internal seat the operator created* — it lives in the workspace, has a substrate home, and reasons from operator-authored persona + the workspace's substrate. (Though note the interesting convergence in §4: a user persona agent *might be realized as* an internal principal that attributes as itself — the two models could meet at the attribution layer.)

### 3.3 The open questions (flagged, not answered — this is the deferred discourse)

This cut is genuinely under-specified and should *stay* under-specified until its own discourse:

1. **Lifecycle & creation surface.** How does the operator author one? Through YARNNN chat (ADR-216's original "authored through chat")? A dedicated surface? What is the minimum viable "create an agent" act?
2. **Trust & authority model.** Does a user persona agent take *accountable action* (like Freddie) or only *propose* (gated through Freddie / the operator)? Lean: **propose, not act** — Freddie remains the sole accountable-action seat; user agents are labor that *drafts*, Freddie/operator decides. This keeps one accountable fiduciary, not N.
3. **Relationship to Freddie.** Does Freddie *judge* user-persona-agent output (arbiter over internal labor too)? Almost certainly yes — it is the same arbiter role, now over internal contributors as well as external principals.
4. **Persona authoring.** Each gets an `IDENTITY.md` + persona — the same persona machinery as Freddie's seat, but user-authored per agent. How much of the seat substrate (ADR-315) generalizes?
5. **Does it even need building before demand?** Possibly the *last* Phase-2 surface. Freddie (Cut 1) is a rename of something that already works; user persona agents (Cut 2) are net-new authored entities. Build-when-demanded.

---

## 4. The unifying frame — attribution is the common spine

The three actors look different but share one substrate property that makes the whole model coherent: **every one of them attributes as itself into the authored substrate** (ADR-209/373).

- External agent → `agent:<name>` / `foreign-llm:<client>` / `a2a:<id>`
- Freddie → `reviewer:<identity>` (today) / `freddie:<identity>` (maybe)
- User persona agent → `agent:<user-slug>` (an internal authored agent)

`trace` therefore renders **a heterogeneous swarm of contributors — external agents, internal Freddie, user-authored persona agents, humans, platforms — each signed, parent-pointered, single-head**, with Freddie as the one seat that *reconciles* across them. That is the moat at full strength, and it is the same picture whether a contributor is inside or outside, platform- or user-authored. **The actor taxonomy (§1) is about authority and lifecycle; the attribution layer is what makes them all citizens of one ledger.**

This is also why the cuts can be sequenced safely: each new actor is *additive at the attribution layer* (a new prefix / a new principal class), not a restructure. Phase 1 ships the external agent. Cut 1 renames the steward. Cut 2 adds authored internal labor. None invalidates the prior; each is a citizen joining the same commons.

---

## 5. Sequencing & relationship to Phase 1

```
Phase 1 (ratified, in progress)
  └─ substrate operated by humans + EXTERNAL agents as principals
     (ADR-373 re-key + ADR-375 product def + ADR-374 IA)
     internal steward DORMANT behind AGENT_ENABLED (default ON; off for interop-first launch)

Phase 2 (named here, built later — downstream ADRs)
  ├─ Cut 1: Freddie — rename + harden the internal steward
  │         (a rename of something that already works; needs multi-principal
  │          substrate as its fuel → after Phase 1 populates)
  └─ Cut 2: user-created persona agents — authored internal labor
            (net-new; propose-not-act lean; build-when-demanded; the deferred discourse)
```

**The discipline this preserves:** Phase-1 work proceeds with focus *because* Phase 2 is recorded and out of the way. When a session is doing Phase-1 substrate / interop / gate work, "what about Freddie / user agents?" has a settled answer: *named, downstream, not now — see this doc.* That is the entire point of writing it down.

---

## 6. Recommended follow-on (the Phase-2 ADRs this doc feeds)

Not now — recorded so the sequence is legible:

1. **The Freddie ADR** (Cut 1). Rename the user-facing label, promote the converged fiduciary + multi-principal-arbiter role to canon, decide the attribution prefix. Cites this doc + ADR-315/319/342/343/344/373. *After* Phase-1 substrate is populated enough that Freddie has fuel.
2. **The user-persona-agent ADR** (Cut 2). Owns the open questions in §3.3 (lifecycle, trust, Freddie-relationship, persona authoring). The *last* surface; build-when-demanded. Cites ADR-216 (the original concept) + this doc.

This doc makes no canon change. It is the vision the two ADRs inherit, so the actor model is settled once, conceptually, and not re-litigated when each cut is built.
