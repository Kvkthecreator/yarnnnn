# Direction — Freddie as the Workspace Agent, and the Two-Order Agent Model

**Date**: 2026-06-27
**Hat**: A-direction (system canon direction; ratified by the operator. Records the *direction + rationale*; the file-by-file canon migration is a **separate audit session**, scoped in §7.)
**Status**: **Ratified direction** (KVK, 2026-06-27). Supersedes the Freddie *framing* in [phase-2-internal-agents-freddie-and-user-personas-2026-06-26.md](phase-2-internal-agents-freddie-and-user-personas-2026-06-26.md) (which held "Picture A" — Freddie = the judgment fiduciary). This doc holds **"Picture B"** — Freddie = the workspace agent / management; judgment pushed *outward* to 2nd-order persona agents. **No canon file is migrated here**; this is the spine the audit session inherits.
**Participants**: KVK (operator) + Claude (collaborator).
**Substrate-receipts**: ledger `authored_by` classes in use today (kvk, 2026-06-27) = `system`/`reviewer`/`operator`/`operator-proxy`/`yarnnn`/`agent`/`dispatcher` — confirming the current Reviewer is a single fused entity, and there is no first-class "workspace agent" identity distinct from judgment yet.

---

## 0. Why this doc exists (and the one correction that produced it)

The [Phase-2 doc](phase-2-internal-agents-freddie-and-user-personas-2026-06-26.md)
named "Freddie" as a **rename of the Reviewer** — i.e. Freddie = the judgment
fiduciary ("the bank's fiduciary who acts on your mandate," §1; "the accountable
fiduciary + multi-principal arbiter," §2.3). Call that **Picture A**.

The 2026-06-27 discourse re-cut it. The operator's correction: **Freddie owns the
workspace *operationally* — it IS the workspace agent / system agent — and the
judgment (persona, money-making) is pushed *outward* to user-directed 2nd-order
persona agents that Freddie creates and manages.** Call that **Picture B**.

A collaborator framing-error en route is worth recording because correcting it
*is* the insight: it was said that "Freddie does not own the workspace." That
conflated two senses of *own*:

- **Own = the principal whose substrate this is** (accountability/property sense) →
  this is the **operator** (the human). Always. No agent owns it this way.
- **Own = the agent responsible for the substrate; manages, mutates, locates,
  relocates, and answers for its state** (operational sense) → this is **Freddie,
  unambiguously.** Managing the substrate at large *is* owning it operationally.

The kernel does not "own" the user's files in the property sense, but it is the
one and only thing that manages and answers for them — **that is the strongest
ownership a system agent can have, not a weaker one.** Freddie is the
kernel-agent, personified (ADR-222 OS framing). "Freddie doesn't own the
workspace" was wrong; **"Freddie owns the workspace operationally; the operator
owns it as principal"** is the correct statement, and Picture B is built on it.

---

## 1. The two-order agent model (ratified)

| | **1st order — Freddie** | **2nd order — persona agents** |
|---|---|---|
| **What it is** | The workspace agent / system agent. One per workspace, **systemic** (exists from signup). The agent-OS, personified. | Operator's judgment labor. Zero-to-many. The trader (e.g. "Jim Rohn"), the author, the domain characters. |
| **Domain** | The substrate + the system. | Judgment within a bounded mandate. |
| **Owns** | The workspace **operationally** (manages, not as principal). | Its own bounded judgment + (when set) the authority to act. |
| **Responsibilities** | Files, context, attributions, locations/relocations, reading file contents, the derive-and-cite intake step, platform-connection setup, **CRUD + governance over the 2nd-order persona agents**, multi-principal arbitration (keeping the commons coherent). | The operator-authored persona, the standing intent, the capital/domain judgment, the back-and-forth judgment discourse, accountability against ground truth. |
| **Reasoning** | A capable **base-LLM about the substrate and the system**. Does NOT embody an operator-authored judgment character. | Reasons from an **operator-authored persona** + principles + the mandate. The persona is the axis it self-improves on. |
| **Created by** | Platform (scaffolded at signup). | **Freddie** — Freddie creates and manages them. (The operator's only creation path is the YARNNN front-end via **existing pre-sets**; the operator does not author an arbitrary agent from scratch — §3.) |
| **Accountability** | The **system**: that the commons is coherent, attributed, legible; that the agents it administers are well-formed; that it correctly governs their authority. | The **judgment**: each persona agent answers for its own mandate against ground truth (DP24/DP30 relocate here — §5). |

**The keystone move** (what Picture A could not do): *Freddie creates the trader
agent (e.g. "Jim Rohn"), then sets it as "act on the user's behalf," and the
operator has a genuine judgment discourse with that agent.* The system agent
**instantiates and governs** the judgment agents but is **not itself** one. **That
is the true separation of judgment from the system** — impossible while judgment
and substrate-management are fused in one Reviewer.

---

## 2. Two ratified hinges (the questions the discourse settled)

**H1 — Freddie is the sole creator/manager of persona agents.** Freddie creates
and manages them. **The operator's only creation path is the YARNNN front-end, via
existing pre-sets** — the operator does not hand-author an arbitrary agent from
scratch; they select a pre-set and Freddie instantiates + governs it. Freddie is
therefore a **gateway *and* a governor**, not merely a governor. (This makes the
agent population a Freddie-administered set — clean lifecycle, one CRUD authority,
no orphan agents.)

**H2 — Freddie is systemic; always exactly one, even in a bare Layer-1
workspace.** Freddie exists from signup to manage the substrate *before any
judgment agent exists*. This is what makes the **judgment layer genuinely additive
at the entity level**: a bare workspace has Freddie + substrate (ESSENCE Layer 1,
valuable alone); judgment is opt-in (the operator picks a pre-set → Freddie
creates a persona agent → ESSENCE Layer 2). "Every workspace has Freddie; judgment
is opt-in" is the clean product shape.

---

## 3. Why this aligns with canon (and *fixes a drift*, not contradicts the deep model)

**ADR-216 (orchestration vs judgment) — Picture B RE-ASSERTS it.** ADR-216 D1:
*"No hybrid classification. An entity is in one layer; if it does work in both, it
is split into two entities."* Two layers: **orchestration** (mechanical,
opinion-less, substrate-writing, performance-fungible) and **judgment**
(persona-bearing, standing intent, not performance-fungible). ADR-216 put them in
two entities: YARNNN (orchestration) + Reviewer (judgment). **The ADR-260→345 arc
let the Reviewer absorb execution authority, recurrence-firing, substrate
management, the standing obligation — becoming exactly the hybrid ADR-216
forbade** (the Phase-2 doc §1 admits this: *"Reviewer quietly absorbed the role of
'the actor / the judgment.'"*). **Picture B is the ADR-216 cut, restored**: Freddie
← the orchestration/OS half (now first-class + named, not "ambient activity" the
way ADR-272 demoted the System Agent); persona agents ← the judgment half (now N
user-directed seats, not one fused systemic seat).

**ESSENCE (asset/labor/management/dividends) — survives, made MORE literal.**
ESSENCE line 16: *"substrate=asset, agents=labor, Reviewer=management."* Picture B
renames management Reviewer→**Freddie** and makes the labor (agents) the
judgment-bearers — which is what *"labor does the work, management governs"
already implies.* Management, literally, is "the one who owns the operation
operationally, hires and governs the labor, and answers for the whole without
personally doing each unit of judgment-work." **That is Freddie exactly.** The
metaphor gets *more* literal, not strained.

**ADR-222 (OS framing) — Freddie is the kernel-agent personified.** The kernel
owns the filesystem operationally; programs (applications) run in userspace.
Freddie = the kernel-agent (substrate, files, the syscall surface, the agent
population); persona agents = applications running under operator-authored
judgment. The operator = the principal whose userspace it is.

**ADR-373 (multi-principal) — Freddie is the arbiter, *as system manager*.** When
a persona agent writes judgment-work and an external principal writes a conflicting
view, Freddie reconciles into a coherent commons — but it reconciles *as system
manager* (keeping the commons coherent), **not** by overriding the persona's
judgment (it doesn't second-guess the trade). This is the multi-principal arbiter
role (Phase-2 §2.3) correctly housed in *management*, not *judgment*.

**ADR-378 (workspace = outermost unit) — composes.** One Freddie per workspace is
exactly why the ceiling lands at the workspace (one management seat per commons;
"one Freddie across many workspaces" *is* the undefined federation case). Picture B
strengthens the ADR-378 rationale.

---

## 4. Why this is a RE-CUT, not a rename (correcting the Phase-2 doc's scope)

The Phase-2 doc (§5) assumed *"Freddie is a rename of something that already
works."* Under Picture B that is **false** — it is a **structural re-cut along the
ADR-216 seam**:

- The judgment **relocates** from one systemic seat (the Reviewer) to N
  user-directed 2nd-order agents.
- A first-class **workspace-agent identity (Freddie)** is created where today there
  is a fused Reviewer + an "ambient" System Agent (ADR-272 demoted it).
- The moat headline **relocates**: ESSENCE's "authored substrate under a
  persona-bearing judgment seat" — the *persona-bearing judgment seat* is no longer
  the systemic thing every workspace has; it is the *2nd-order persona agent the
  operator opts into.* The systemic thing is Freddie (management). This makes the
  judgment layer additive **at the entity level**, which is *more* honest to
  ESSENCE's "substrate floor valuable alone" than the current always-a-Reviewer
  shape.

So the audit session inherits a **re-cut**, sized accordingly (§7) — not a label
swap.

---

## 5. Accountability — where DP24/DP30 land (resolved)

- **Judgment accountability → the persona agent.** ADR-319 (DP24, stewardship of
  intent against ground-truth) and ADR-344 (DP30, the standing obligation) move to
  the **2nd-order persona agent** — that is where the mandate, the standing intent,
  and the "act on the user's behalf" authority live. The trader agent answers for
  its trades against ground truth.
- **System accountability → Freddie.** Freddie answers for the *system*: the
  commons being coherent/attributed/legible, the agents it administers being
  well-formed, and the correct governance of their authority. **Management answers
  for the desk and for who was hired; not for any single trade.**

This is sharper than the Picture-A "Freddie keeps thin arbiter accountability vs.
Freddie is pure plumbing" framing — judgment-accountability and
system-accountability split cleanly along the two orders.

---

## 6. The autonomy/authority dial lives at Freddie's management layer

"Act on the user's behalf" is a flag **Freddie sets on a persona agent** at the
operator's direction. So the AUTONOMY governance (ADR-366 grant/contract; ADR-334
pricing axis) is **Freddie's to administer, per persona agent** — a clean home for
per-agent authority. Freddie is not just "an OS agent that manages files"; it is
**the agent that administers the entire agent-population of the workspace,
including each agent's authority to act.** A bigger, more central role than the
current Reviewer — not a smaller one.

---

## 7. What the SEPARATE audit session inherits (scope — do NOT do here)

This doc is the spine; the file-by-file canon migration is its own session. The
likely surface (sized as a re-cut, not a rename):

1. **The Freddie ADR** (the Cut-1 ADR the Phase-2 doc §6 named) — now owns Picture
   B: Freddie = workspace agent/management/arbiter + sole creator-governor of
   persona agents (H1) + systemic (H2). Decide the attribution prefix
   (`reviewer:`→`freddie:`? or keep slug, rename label — lean: keep slug, GLOSSARY
   enum-exception precedent per ADR-251).
2. **ESSENCE** — relocate the moat sentence (judgment seat = the 2nd-order persona
   agent, not the systemic Reviewer); name Freddie as management/OS-manager. Lines
   16, 55–61, 89–93.
3. **The Phase-2 doc** — amend §1 actor table + §2.3 from Picture A (Freddie = the
   fiduciary) to Picture B (Freddie = management/arbiter; persona agents = the
   fiduciaries). Add the banner pointing here.
4. **ADR-216 / LAYER-MAPPING** — reaffirm the orchestration/judgment split;
   re-map the entities (orchestration grows "ambient YARNNN" → first-class Freddie;
   judgment moves one-systemic-Reviewer → N user-directed persona agents).
5. **ADR-319 / ADR-344 (DP24/DP30)** — relocate judgment-accountability to the
   persona agent; name system-accountability as Freddie's (§5).
6. **The seat canon** (`reviewer-seat-substrate.md` + occupant docs, ADR-194/315) —
   "one judgment seat per workspace" generalizes to "one management seat (Freddie)
   + N judgment seats (persona agents)." The seat-vs-occupant model (ADR-315)
   extends cleanly.
7. **The creation surface** — the YARNNN front-end pre-set picker (H1) → Freddie
   instantiates + governs. (Implementation; downstream of the ADR.)

**Sequencing note**: Picture B touches the moat sentence and the accountability
principles — so the audit session should treat it as a **canon re-cut requiring
operator sign-off per file**, not a mechanical sweep.

---

## 8. The one-line statement (for the audit session to carry)

> **Freddie is the workspace agent — the systemic agent-OS that operationally owns
> the substrate (files, context, attributions, intake, connections) and creates +
> governs the workspace's 2nd-order persona agents, including their authority to
> act. The operator owns the workspace as principal; Freddie owns it operationally
> as its manager; the persona agents are the labor that bears judgment. The system
> agent instantiates and governs the judgment agents but is not itself one.**
