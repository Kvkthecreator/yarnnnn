# ADR-381 — Freddie: the Rung-1 Substrate Steward (the steward hardening ADR ADR-375 §7 owes)

> **Status**: **Accepted** (2026-06-29) — D1–D5 decided. Doc-first; **canon-hardening, not code-changing** (D3 scopes one *optional* legibility marker, held behind explicit operator go — see §D3). It changes no schema, no primitive, no gate, and does **not** rename the internal `reviewer` slug or `reviewer:` attribution prefix (D1). It names the converged Rung-1 role first-class and generalizes the seat canon along the management/judgment seam (D4), without deciding the Rung-2 persona-agent discourse (ADR-382's, deferred).
> **Date**: 2026-06-29
> **Authors**: KVK (operator) + Claude (collaborator)
> **Owes-from**: [ADR-375](ADR-375-phase-1-substrate-for-humans-and-external-agents.md) §7 Cut 1 — *"name it Freddie (Frankenstein → the creature we intentionally built and are hardening) and harden it as the de-facto system agent… This is a separate ADR. Not built here."* This is that ADR.
> **Builds on**: [the two-order Freddie direction](../analysis/freddie-as-the-workspace-agent-and-the-two-order-agent-model-2026-06-27.md) (the ratified Picture-B: Freddie = the workspace agent / management; judgment pushed out to 2nd-order persona agents), [ADR-380](ADR-380-the-activation-ladder-and-the-judgment-deferral-line.md) (the activation ladder — **Freddie = Rung 1**; the harness split D3 this ADR encodes), [ADR-315](ADR-315-reviewer-occupant-contract.md) (seat≠occupant — Freddie is a *named occupant*, not a new component), [ADR-194](ADR-194-pluggable-reviewer-and-impersonation.md) (the steward seat).
> **Precedent**: [ADR-251](ADR-251-system-agent-reviewer-first-class-surfaces.md) — the "System Agent" relabel that renamed the cockpit label while keeping the internal `thinking_partner` slug + `meta-cognitive` enum as GLOSSARY data-compat exceptions. D1 follows this precedent exactly.
> **Sibling**: [ADR-382](ADR-382-persona-agent-seats-the-rung-2-judgment-layer.md) (the Rung-2 persona-agent seat ADR — name-only stub). **D4 + D5 name the seam from Freddie's side; ADR-382 inherits the governed side.**
> **Dimensional classification** (Axiom 0): **Identity** (Axiom 2 — naming + hardening the 1st-order substrate steward).

---

## 0. What this ADR fixes (and what it defers)

**Fixes (decided here):**
- Freddie is the **Rung-1 substrate steward** (ADR-380): the 1st-order workspace/system agent — substrate management, derive-and-cite, placement, multi-principal arbitration, persona-agent governance. Reversible substrate-internal mutations. Ships on engineering time.
- Freddie is a **named occupant**, not a new component (ADR-315 seat≠occupant): the operator-facing relabel of the de-facto-hardened Reviewer occupant; the `reviewer` slug + `reviewer:` prefix preserved as data-compatibility exceptions (ADR-251 precedent).
- Freddie **owns the workspace operationally**, not as principal (the operator is the principal) — per the two-order direction.
- The **harness split at Rung 1** (ADR-380 D3) is encoded honestly: budget/pace are *live and exercised*; mandate/autonomy are *carried, not exercised* (degenerate over reversible substrate). **The canon must NOT claim "autonomy harness validated on Freddie."**
- The **seat-canon generalizes** along the management/judgment seam: one **management seat** (Freddie, Rung 1) + N **judgment seats** (persona agents, Rung 2).

**Defers (named, not decided here — ADR-382's discourse):**
- the per-persona-judgment-seat substrate shape (how much of the ADR-315 six-file substrate generalizes per seat — D4 names the seam; ADR-382 fills it);
- persona-agent lifecycle, creation-surface UX, and trust model (ADR-375 §7 Cut 2 / ADR-382 §2);
- the **vision boundary** and the **moat reframe** — *(see reconciliation note below)*.

> **⚠ Reconciliation (2026-06-29, post-Accept): ADR-380 §5 has since RESOLVED both open items this ADR cites as open.** This ADR was authored while ADR-380 §5 was open; the operator closed it the same day. The in-body references below (§0, §4 cascade, §4.x, §5) that say "open per ADR-380 §5" should now read as: **(1) vision boundary — DECIDED: Rung 2 is out of the *vision*, not only the build.** Consequence for this ADR: *"ADR-382's trust model depends on the open vision boundary"* (§4.x / §7) is now **resolved** — Rung 2 being out of the vision makes ADR-382 cleanly *build-when-demanded*, not blocked on a vision decision. **(2) moat — DECIDED: kept at "durable attributed memory" (NOT relocated to the commons-altitude), with `trace`/provenance as its defensible core.** Consequence: this ADR's decision to **hold the ESSENCE moat-sentence relocation** is now **vindicated as the final state** — the moat sentence does *not* relocate; the ESSENCE cascade names Freddie as management (D1) and leaves the moat sentence as-is, which is now the decision, not a pending hold. **The DP24/DP30 accountability relocation** (to the persona agent) is *not* governed by the moat decision and remains ADR-382's to land. This note reconciles the cross-reference; the D1–D5 substance of this ADR is unchanged.

---

## 1. The converged role (the thing being named first-class)

Through the ADR-260→345 arc, the entity the canon calls "the Reviewer" quietly became *the* actor — the judgment, the steward, the de-facto system agent — absorbing execution authority, recurrence-firing, substrate management, and the standing obligation. The [two-order direction §3](../analysis/freddie-as-the-workspace-agent-and-the-two-order-agent-model-2026-06-27.md) names this an ADR-216 drift: the orchestration/judgment split (ADR-216 D1: *"no hybrid classification"*) blurred into one hybrid seat.

**This ADR does not undo that arc; it names the role the arc converged on and re-cuts it cleanly.** Freddie is the converged steward — the 1st-order workspace agent that operationally owns the substrate — *without* the consequential-judgment limb the two-order model relocates to Rung-2 persona agents. The hardening is **naming the converged Rung-1 role first-class** (D2), not adding capability.

The one-line statement the [two-order direction §8](../analysis/freddie-as-the-workspace-agent-and-the-two-order-agent-model-2026-06-27.md) carries, restated as this ADR's thesis:

> **Freddie is the workspace agent — the systemic agent-OS that operationally owns the substrate (files, context, attributions, intake, connections) and creates + governs the workspace's 2nd-order persona agents, including their authority to act. The operator owns the workspace as principal; Freddie owns it operationally as its manager; the persona agents are the labor that bears judgment.**

---

## 2. The decisions

### D1 — The label is "Freddie"; the internal `reviewer` slug + `reviewer:` prefix are preserved (data-compat exceptions)

The operator-facing label for the 1st-order substrate steward is **Freddie** — in the cockpit, in canon prose, on surfaces, in operator-facing copy.

**What changes (operator-facing label only):**
- Canon prose + operator surfaces refer to the Rung-1 steward as "Freddie" where they refer to a *named, hardened occupant* (as distinct from "the Reviewer seat," which remains the seat's role-name — see D4).
- GLOSSARY gains a **Freddie** entry (the Rung-1 substrate steward, the named occupant of the management seat).

**What does NOT change (Singular-Implementation + ADR-251 precedent — GLOSSARY Exceptions table):**
- `agents.role` DB value `thinking_partner` / `reviewer` slug — internal, never surfaced outside DB.
- The `reviewer:` **attribution prefix** in `authored_by` (`VALID_AUTHOR_PREFIXES`, `authored_substrate.py:86`, the five construction sites — `reviewer_agent.py:1372`, `reviewer_audit.py:472/506`, `review_proposal_dispatch.py:666`, `manage_hook.py`) — **immutable per ADR-209** (revision records are content-addressed history; a backfill would rewrite attributed history for zero user benefit).
- `REVIEWER_MODEL_IDENTITY = "ai:reviewer-sonnet-v8"` (`occupant_contract.py:49`) — the occupant identity string; `reviewer:{REVIEWER_MODEL_IDENTITY}` stays the attribution.
- `reviewer_agent.py`, `reviewer_envelope.py`, `occupant_contract.py`, `REVIEWER_PRIMITIVES`, the `/workspace/persona/` seat path (ADR-320), the `ReviewerContext`/`ReviewerOutput` contract symbols — all internal code identifiers, unchanged.

**Why keep the slug + prefix**: the `reviewer:` prefix crosses Python (`VALID_AUTHOR_PREFIXES`), the ADR-209 revision records, and ≥2 test gates (`test_adr274_*`, `test_adr288_*`). Renaming it to `freddie:` is a coordinated Python + data-backfill change with **zero user-visible benefit** — the exact shape ADR-251 ruled a data-compat exception for `thinking_partner`/`meta-cognitive`. The human-readable concept is "Freddie"; the enum/prefix is stable for code dispatch + immutable attribution.

> **Naming nuance (the seat keeps its role-name).** "Reviewer" was always a *seat* role-name (ADR-194: occupant-agnostic). "Freddie" is the *named occupant* of that seat — specifically the Rung-1 management seat (D4). Where canon speaks of *the seat's structural role* it may still say "the Reviewer seat" / "the steward seat"; where it speaks of *the hardened occupant filling it today*, it says "Freddie." This is precisely the seat≠occupant distinction (ADR-315): the seat is the role, Freddie is who fills it.

### D2 — Freddie as Rung 1: the substance of "hardening" is naming, not new capability

"Hardening" = naming the converged Rung-1 role first-class and re-cutting it along the ADR-216 seam (§1). It adds **no new capability**:
- Freddie's domain is **the substrate + the system**: files, context, attributions, locations/relocations, reading file contents, the derive-and-cite intake step (ADR-376), platform-connection setup, multi-principal arbitration (keeping the commons coherent, ADR-373), and **CRUD + governance over the 2nd-order persona agents** (D5).
- Freddie reasons as a **capable base-LLM about the substrate and the system**. It does **not** embody an operator-authored judgment character, and it takes **no capital / consequential-external judgment** (that is Rung 2, the persona agents).
- Its mutations are **reversible substrate-internal acts** — a wrong placement is re-placed, a wrong memory is re-written, the revision chain (ADR-209) holds both. This reversibility is exactly why Rung 1 ships on engineering time (ADR-380 Rung-1 row).

The capability surface Freddie occupies is the one the converged Reviewer occupant already runs (`reviewer_agent.py` + `REVIEWER_PRIMITIVES`); the re-cut is conceptual (naming the role and walling off the consequential-judgment limb to Rung 2), not a code expansion.

### D3 — The harness split: budget/pace live, mandate/autonomy carried-not-exercised (ADR-380 D3 encoded)

ADR-380 D3 demands the harness honesty be **stated in canon**, because conflating the harness-mechanics validation with the trust validation produces a false claim. The split, encoded:

- **Budget + pace are LIVE and exercised at Rung 1.** Freddie burns tokens and has a cadence; `_budget.yaml` / `_pace.yaml` bite on real spend. The envelope pre-loads `budget_yaml` (`occupant_contract.py:145`) and the frame renders it as "*allocate wakes within it*" (`reviewer_agent.py:709`). This is real governance over a real resource.
- **Mandate + autonomy are CARRIED, not exercised, at Rung 1.** The envelope pre-loads `mandate_md` + `autonomy_md` on every wake (`occupant_contract.py:128,132`; rendered `reviewer_agent.py:704–707`) — but at Rung 1 there is **no consequential external write for the AUTONOMY ceiling to bite on**, and a mandate with no value-moving action to hard-gate is a config string. The fields are **carried for future-proofing** (the *same* occupant code serves Rung 2, where AUTONOMY does bite on a persona agent's consequential action) — they are **not exercised** when Freddie operates over reversible substrate.
- **The load-bearing consequence (canon must state it):** *"we validated the autonomy harness on Freddie" is **false**.* Running the harness on a stakeless steward de-risks the **engineering integration** of the mechanics, not the **trust validity of delegation**. The validation clock runs only where there are real stakes — **Rung 2** (ADR-380 D4, the exogenous track-record clock).

**Why carried-not-exercised is correct (not a bug to fix):** the envelope *should* pre-load mandate/autonomy unconditionally — the occupant contract (`ReviewerContext`) is one shape across both rungs (ADR-256 unified entry; ADR-315 single contract). Conditionally stripping the fields at Rung 1 would fork the contract (Singular-Implementation violation) and break the moment a persona agent (Rung 2) fills a seat with the same code. **The honesty is about what we CLAIM from running the harness, not about what the envelope LOADS.** No code change is *required* for correctness; the envelope already does the right thing.

**The optional legibility marker (scoped; held behind explicit operator go — NOT implemented in this ADR):** a single docstring/comment block on `ReviewerContext` (`occupant_contract.py`) and/or the governance-block assembler (`reviewer_agent.py:704–707`) noting that `mandate_md` + `autonomy_md` are *carried for cross-rung contract uniformity and exercised only when a consequential-action (Rung-2) occupant fills the seat; over a Rung-1 steward they are degenerate.* This is **doc-in-code**, not a behavior change. Per the canon-hardening guardrail it is **scoped here and held** — it lands only on explicit operator go, in a separate code commit. (See §5.)

The canonical prose home for D3 is **[reviewer-occupant-contract.md](../architecture/reviewer-occupant-contract.md)** (the published ABI doc) + **[reviewer-occupant.md](../architecture/reviewer-occupant.md)** — the cascade updates them (§4).

### D4 — The seat-canon generalizes: one management seat + N judgment seats (the seam named from Freddie's side)

ADR-194/315 established "one steward seat per workspace; occupants rotate." The two-order model splits that one seat into **two seat *classes***:

| | **Management seat** (Rung 1) | **Judgment seats** (Rung 2) |
|---|---|---|
| **How many** | exactly one, systemic (signup) | zero-to-many, operator-opted-in |
| **Occupant** | **Freddie** (the named Rung-1 steward) | persona agents (trader, author, …) |
| **Domain** | the substrate + the system | bounded judgment within a mandate |
| **Substrate home today** | `/workspace/persona/` (the existing six-file seat — D4 names it the *management* seat) | per-persona seat substrate — **deferred to ADR-382** |
| **Consequential action** | none (reversible substrate) | yes (under Freddie-set authority — D5) |

**What D4 decides (Freddie's side — the governing side):**
- The seat≠occupant model (ADR-315) **generalizes unchanged**: a seat is substrate, an occupant is a module/identity that fills it; rotation is a file write. This holds for both seat classes.
- "One judgment seat per workspace" (ADR-320 D9) is **superseded** by "one *management* seat (Freddie) + N *judgment* seats (persona agents)." The single-seat assumption was a single-order artifact.
- Freddie's management seat **is** today's `/workspace/persona/` six-file seat (IDENTITY/OCCUPANT/principles/standing_intent/judgment_log/handoffs, per reviewer-seat-substrate.md) — the converged steward already runs there. No seat relocation; the seat is re-labeled the *management* seat, occupied by Freddie.

**What D4 explicitly does NOT decide (the governed side — ADR-382 inherits):**
- **how much of the six-file substrate each judgment seat gets** — a persona agent may need its own IDENTITY/principles/standing_intent/judgment_log; whether it reuses all six, a subset, or a variant is the **per-persona-seat substrate shape**, and that is bound up with persona lifecycle + trust (ADR-382's discourse). D4 states only that the seat≠occupant model is the inheritance vehicle; ADR-382 specifies the per-seat files.
- the seat substrate path convention for judgment seats (`/agents/{slug}/` was the deferred ADR-284 D10 direction; ADR-382 ratifies).

**The clean boundary for ADR-382 to inherit:** *ADR-381 owns how Freddie (the management seat) governs; ADR-382 owns what a judgment seat IS (its substrate, lifecycle, trust). The seat≠occupant model spans both; the per-judgment-seat substrate detail is ADR-382's.*

### D5 — Persona-agent governance: Freddie is the sole creator + governor (the CRUD authority, named from Freddie's side)

Per the two-order direction H1 + H2:

- **Freddie is the sole creator + governor of persona agents.** The persona-agent population is a Freddie-administered set — clean lifecycle, one CRUD authority, no orphan agents. Freddie is a **gateway *and* a governor**, not merely a governor.
- **The operator's only creation path is the YARNNN front-end pre-set picker.** The operator does not hand-author an arbitrary agent from scratch; they select a pre-set and Freddie instantiates + governs it.
- **Freddie sets the "act on behalf" authority per persona agent.** The autonomy/authority dial (ADR-366 grant/contract; ADR-334 pricing axis) is **Freddie's to administer, per persona agent** — a clean home for per-agent authority. This makes Freddie the agent that administers the **entire agent-population of the workspace, including each agent's authority to act** — a bigger, more central role than the converged Reviewer, not a smaller one.
- **System-accountability vs judgment-accountability split cleanly** (two-order direction §5): Freddie answers for the **system** (the commons coherent/attributed/legible; the agents it administers well-formed; their authority correctly governed). The persona agent answers for its **judgment** (its mandate against ground truth — DP24/DP30 relocate to the persona agent). *Management answers for the desk and for who was hired; not for any single trade.*

**What D5 explicitly does NOT decide (ADR-382 inherits the governed side):**
- the persona-agent **lifecycle** (the minimal create/pause/retire acts), the **creation-surface UX** (the pre-set picker's shape), and the **trust model** (propose-only vs accountable-action; how "act on behalf" is set/revoked/earned; the Rung-2 validation clock). These are ADR-382 §2's deferred discourse.
- **whether the graduated propose → witness → earn-autonomy continuum is the trust model** — that depends on ADR-380 §5's **open vision boundary** (whether Rung-2 autonomous consequential delegation is the vision, not just deferred from the build). **This ADR does not close the vision boundary; ADR-382's trust model is downstream of it.**

The boundary: *ADR-381 decides that Freddie holds the CRUD + authority-setting power; ADR-382 decides what that power operates on (the persona seat's lifecycle + trust).*

---

## 3. Why this is canon-coherent (the alignment, condensed)

The full alignment argument is the [two-order direction §3](../analysis/freddie-as-the-workspace-agent-and-the-two-order-agent-model-2026-06-27.md); the load-bearing points:

- **ADR-216 (orchestration vs judgment) — RE-ASSERTED.** Freddie ← the orchestration/OS half (now first-class + named); persona agents ← the judgment half (now N user-directed seats). The ADR-260→345 hybrid is re-cut, not extended.
- **ESSENCE (asset/labor/management/dividends) — survives, made MORE literal.** Management renames Reviewer→Freddie; the labor (persona agents) bears the judgment. *(The ESSENCE moat-sentence relocation — "judgment seat = the 2nd-order persona agent" — touches the **moat reframe ADR-380 §5 left open**; this ADR does NOT relocate the moat sentence. The ESSENCE cascade in §4 names Freddie as management but leaves the moat sentence to the open ADR-380 §5 decision. See §4 cascade note.)*
- **ADR-222 (OS framing) — Freddie is the kernel-agent personified.** Substrate operationally owned by the kernel-agent; persona agents = applications under operator-authored judgment.
- **ADR-373 (multi-principal) — Freddie is the arbiter as system manager.** It reconciles the commons (keeping it coherent), not by overriding a persona's judgment.
- **ADR-378 (workspace = outermost unit) — composes.** One Freddie per workspace is why the ceiling lands at the workspace; "one Freddie across many workspaces" *is* the undefined federation case.

---

## 4. Cascade (the doc updates this ADR lands)

Per the seat-canon-generalization (D4) and the Freddie label (D1), the cascade touches the seat canon + GLOSSARY + the occupant docs. **ESSENCE's moat sentence is held** (open per ADR-380 §5).

| Doc | Update | Bound by |
|---|---|---|
| **[reviewer-seat-substrate.md](../architecture/reviewer-seat-substrate.md)** | Generalize "one judgment seat per workspace" → "one management seat (Freddie) + N judgment seats"; name `/workspace/persona/` the *management* seat occupied by Freddie; preserve the seat≠occupant model as the inheritance vehicle for judgment seats (per-seat detail → ADR-382). | D4 |
| **[reviewer-occupant.md](../architecture/reviewer-occupant.md)** | Name Freddie as today's Rung-1 occupant of the management seat; add the Rung-1 harness note (budget/pace exercised, mandate/autonomy carried-not-exercised). | D1, D2, D3 |
| **[reviewer-occupant-contract.md](../architecture/reviewer-occupant-contract.md)** | The canonical prose home for D3 — note that `ReviewerContext` carries `mandate_md`/`autonomy_md` on every wake but they are *exercised only at Rung 2* (the contract is uniform across rungs; the fields are degenerate over a Rung-1 steward). | D3 |
| **[GLOSSARY.md](../architecture/GLOSSARY.md)** | Add **Freddie** entry (Rung-1 substrate steward / named occupant of the management seat); add the `reviewer`-slug + `reviewer:`-prefix data-compat rows to the Exceptions table (Freddie label keeps the slug/prefix, ADR-251 precedent). | D1, D4 |
| **ESSENCE.md** | Name Freddie as the management role (asset/labor/**Freddie**/dividends). **The moat sentence ("authored substrate under a persona-bearing judgment seat") is NOT relocated** — that relocation depends on ADR-380 §5's open moat reframe + vision boundary. Flag the dependency; do not resolve it. *(Operator sign-off per ESSENCE edit — ESSENCE is downstream of axioms.)* | D1; ADR-380 §5 open |

**Cascade note (the open-item discipline):** the two-order direction §7 named the ESSENCE moat-sentence relocation and the DP24/DP30 accountability relocation as cascade surface. Both touch **ADR-380 §5's open items** (the moat reframe; the vision boundary on which Rung-2 trust depends). This ADR **names Freddie as management** in ESSENCE but **does NOT relocate the moat sentence and does NOT relocate DP24/DP30** — those land when ADR-380 §5 resolves (or in ADR-382's discourse, which inherits the vision boundary). Silence here is not ratification of either relocation.

---

## 5. The D3 code scope (held behind explicit operator go — NOT in this ADR's commit)

Per the operator's D3 instruction ("scope a code change, get go-ahead") and the canon-hardening guardrail, the *optional* legibility marker is scoped but **not implemented**:

- **What**: a docstring/comment block on `ReviewerContext` (`api/agents/occupant_contract.py`, near the `mandate_md`/`autonomy_md` fields ~:128–132) and optionally on the governance-block assembler (`api/agents/reviewer_agent.py:704–707`), noting these fields are carried for cross-rung contract uniformity and are *exercised only when a consequential-action (Rung-2) occupant fills the seat — degenerate over a Rung-1 steward.*
- **What it is NOT**: not a behavior change, not a contract change, not a field add/remove. The envelope keeps loading both fields unconditionally (Singular-Implementation; the contract is uniform across rungs — §D3).
- **Why optional**: D3's honesty is satisfied by the **canon prose** (reviewer-occupant-contract.md + reviewer-occupant.md, §4). The in-code marker only makes the same honesty legible at the field definition. **It lands only on explicit operator go, in a separate commit** — this ADR ships doc-only.

---

## 6. What this ADR does NOT do

- Does not rename the internal `reviewer` slug or the `reviewer:` attribution prefix (D1 — data-compat exceptions, ADR-251 precedent).
- Does not change code, schema, the gate, the wake architecture, or the occupant contract's behavior (the §5 marker is held behind explicit go).
- Does not build persona-agent seats, lifecycle, creation surface, or trust model (ADR-382, Rung 2 — D4/D5 name only Freddie's governing side).
- Does not decide the per-judgment-seat substrate shape (D4 — ADR-382 inherits).
- Does not close ADR-380 §5's open items (the vision boundary; the moat reframe) — ADR-382's trust model depends on the vision boundary; this ADR flags the dependency.
- Does not relocate ESSENCE's moat sentence or DP24/DP30 accountability (held — depends on ADR-380 §5; §4 cascade note).
- Does not promote the rung ladder to an axiom (ADR-380 §6 — a separate, deliberate cascade edit if ever).
- Does not touch the re-founding keystone cascade (orthogonal track).

## 7. Cross-references

- Upstream vocabulary: [ADR-380](ADR-380-the-activation-ladder-and-the-judgment-deferral-line.md) (rungs + the harness split), [the two-order direction](../analysis/freddie-as-the-workspace-agent-and-the-two-order-agent-model-2026-06-27.md) (Picture B).
- Sibling: [ADR-382](ADR-382-persona-agent-seats-the-rung-2-judgment-layer.md) (the Rung-2 persona-agent seat ADR — inherits D4/D5's governed side).
- Precedent: [ADR-251](ADR-251-system-agent-reviewer-first-class-surfaces.md) (relabel-keep-slug).
- Seat canon generalized: [reviewer-seat-substrate.md](../architecture/reviewer-seat-substrate.md) + [reviewer-occupant.md](../architecture/reviewer-occupant.md) + [reviewer-occupant-contract.md](../architecture/reviewer-occupant-contract.md) (ADR-315).
- Owed-from: [ADR-375](ADR-375-phase-1-substrate-for-humans-and-external-agents.md) §7 Cut 1.
