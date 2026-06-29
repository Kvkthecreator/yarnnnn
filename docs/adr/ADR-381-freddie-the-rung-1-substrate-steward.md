# ADR-381 — Freddie: the Rung-1 Substrate Steward (the steward hardening ADR ADR-375 §7 owes)

> **Status**: **Accepted** (2026-06-29) — D1–D5 decided.
>
> **⚠ D1 AMENDED (2026-06-29, the full-rename reversal).** D1 originally kept the internal `reviewer` slug + `reviewer:` attribution prefix as a data-compat exception (ADR-251 relabel-keep-slug precedent — preserved below for lineage). **That is reversed: the occupant entity is now FULLY renamed reviewer→freddie in code AND data** — `freddie_agent.py`, `invoke_freddie`, `FREDDIE_PRIMITIVES`, the `freddie:` attribution prefix, `ai:freddie-sonnet-v8`, the `freddie` caller-class + message-role + synthesized agent, the FE `?agent=freddie` route + components. The seat≠occupant boundary (ADR-315) still holds — the *review action/seat* machinery (`review_proposal_dispatch.py`, `review_rotation.py`, the "review" verb, `/workspace/persona/`, `ReturnVerdict`) is NOT renamed. **Why the reversal**: the operator confirmed (a) the 735 `reviewer:`-attributed live rows are disposable test data on the *old fused-reviewer service model* — the exact architecture the two-order cut retires — so a clean-slate (Phase 6) discards them and new workspaces are born `freddie:` (no ADR-209 history rewrite); and (b) keeping a `reviewer`/`freddie` split is itself the dual-state the Singular-Implementation discipline forbids. Commits `947b25b` (backend files+symbols+prefix), `177ab97` (caller-class+role/route+FE). The keep-slug paragraphs below are **historical** — read them through this banner.
>
> Canon-hardening; D3's only code change was one inert comment block (the legibility marker, §5). It names the converged Rung-1 role first-class and generalizes the seat canon along the management/judgment seam (D4), without deciding the Rung-2 persona-agent discourse (ADR-382's, deferred).
> **Date**: 2026-06-29
> **Authors**: KVK (operator) + Claude (collaborator)
> **Owes-from**: [ADR-375](ADR-375-phase-1-substrate-for-humans-and-external-agents.md) §7 Cut 1 — *"name it Freddie (Frankenstein → the creature we intentionally built and are hardening) and harden it as the de-facto system agent… This is a separate ADR. Not built here."* This is that ADR.
> **Builds on**: [the two-order Freddie direction](../analysis/freddie-as-the-workspace-agent-and-the-two-order-agent-model-2026-06-27.md) (the ratified Picture-B: Freddie = the workspace agent / management; judgment pushed out to 2nd-order persona agents), [ADR-380](ADR-380-the-activation-ladder-and-the-judgment-deferral-line.md) (the activation ladder — **Freddie = Rung 1**; the harness split D3 this ADR encodes), [ADR-315](ADR-315-reviewer-occupant-contract.md) (seat≠occupant — Freddie is a *named occupant*, not a new component), [ADR-194](ADR-194-pluggable-reviewer-and-impersonation.md) (the steward seat).
> **Precedent**: [ADR-251](ADR-251-system-agent-reviewer-first-class-surfaces.md) — the "System Agent" relabel that renamed the cockpit label while keeping the internal `thinking_partner` slug + `meta-cognitive` enum as GLOSSARY data-compat exceptions. D1 follows this precedent exactly.
> **Sibling**: [ADR-382](ADR-382-persona-agent-seats-the-rung-2-judgment-layer.md) (the Rung-2 persona-agent seat ADR — concept framed + the accountability axis decided; lifecycle/trust/per-seat-substrate deferred). **D4 + D5 name the seam from Freddie's side; ADR-382 §3 decides where DP24/DP30 land (the persona agent), and inherits the rest of the governed side.**
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
- the **vision boundary** and the **moat reframe** — *resolved by ADR-380 §5 the same day (see reconciliation note below); ADR-382's persona-agent trust model is now build-when-demanded, not blocked.*

> **⚠ Reconciliation (2026-06-29, post-Accept): ADR-380 §5 RESOLVED both open items, and the ESSENCE cascade was taken to full reconciliation accordingly.** This ADR's skeleton-fill was authored while ADR-380 §5 was briefly open; the operator closed it the same day, and the ESSENCE edit (§4) was then taken further than this ADR's first draft of §4 anticipated. The resolved state, which the in-body references below now reflect:
> - **(1) Vision boundary — DECIDED (ADR-380 §5): Rung 2 is scoped out of the *vision*, not only the build.** The vision is the **multi-principal substrate commons + Freddie (the context-management OS)**; the Rung-2 judgment layer is an optional future capability the launch + vision narrative does not pre-sell. Consequence: ADR-382's trust model is now **cleanly *build-when-demanded*, not blocked on a vision decision** (ADR-380 §5 names this relief explicitly).
> - **(2) Moat — DECIDED (ADR-380 §5): kept at "durable attributed memory," led by the substrate + `trace`/provenance (the walkable revision chain), NOT relocated to the commons-altitude and NOT led by the judgment seat.** Consequence: the **ESSENCE external lead was re-cut** from v14.0's "the judgment seat leads" to the substrate-led, `trace`-defended framing (ESSENCE v14.2; per operator decision "full ESSENCE reconciliation"). The management role is renamed Reviewer→Freddie (D1); the judgment seat is named the *future deepening*, not the systemic moat.
> - **(3) DP24/DP30 accountability relocation** (judgment-accountability to the persona agent) is *not* governed by the moat decision and **remains ADR-382's to land** — NOT done here.
>
> The D1–D5 substance of this ADR is unchanged; this note + the §4 cascade reflect the resolved vision/moat state and the full ESSENCE re-cut.

---

## 1. The converged role (the thing being named first-class)

Through the ADR-260→345 arc, the entity the canon calls "the Reviewer" quietly became *the* actor — the judgment, the steward, the de-facto system agent — absorbing execution authority, recurrence-firing, substrate management, and the standing obligation. The [two-order direction §3](../analysis/freddie-as-the-workspace-agent-and-the-two-order-agent-model-2026-06-27.md) names this an ADR-216 drift: the orchestration/judgment split (ADR-216 D1: *"no hybrid classification"*) blurred into one hybrid seat.

**This ADR does not undo that arc; it names the role the arc converged on and re-cuts it cleanly.** Freddie is the converged steward — the 1st-order workspace agent that operationally owns the substrate — *without* the consequential-judgment limb the two-order model relocates to Rung-2 persona agents. The hardening is **naming the converged Rung-1 role first-class** (D2), not adding capability.

The one-line statement the [two-order direction §8](../analysis/freddie-as-the-workspace-agent-and-the-two-order-agent-model-2026-06-27.md) carries, restated as this ADR's thesis:

> **Freddie is the workspace agent — the systemic agent-OS that operationally owns the substrate (files, context, attributions, intake, connections) and creates + governs the workspace's 2nd-order persona agents, including their authority to act. The operator owns the workspace as principal; Freddie owns it operationally as its manager; the persona agents are the labor that bears judgment.**

---

## 2. The decisions

### D1 — The label is "Freddie"; the internal `reviewer` slug + `reviewer:` prefix are preserved (data-compat exceptions)

The operator-facing label for the 1st-order substrate steward is **"Freddie, the system agent"** — a proper *name* (Freddie) carried with a descriptive *role-anchor* (the system agent). The cockpit shows "Freddie"; canon prose + the role anchor say "the system agent (Freddie)." This is deliberate: "Freddie" alone is a proper noun with zero code/role semantics (a reader hops reviewer→Freddie→"the system agent"); pairing it with the descriptive anchor gives code-readers + canon the role meaning in one hop while operators get a name they talk *to*. It is exactly how ADR-251 worked (cockpit label + descriptive concept), and it **explicitly refills the System-Agent-shaped role ADR-272 left** when it dissolved "System Agent" as a cockpit entity — Freddie *is* the system agent, now first-class and substrate-backed (not the "ambient activity" label ADR-272 demoted).

**What changes (operator-facing label only):**
- The cockpit + operator surfaces show **"Freddie"**; canon prose anchors it as **"the system agent (Freddie)"** / "the Rung-1 substrate steward (Freddie)" where the *role* is what's referenced (as distinct from "the Reviewer seat" / "the management seat," which remain the seat's role-names — see D4).
- GLOSSARY gains a **Freddie** entry (the system agent — the Rung-1 substrate steward, the named occupant of the management seat).
- The frame (the model-facing system prompt) describes the *role* — "this workspace's installed steward / the system agent" — not the proper noun (the model should anchor on the role, not over-index on a name). The proper noun is the operator-facing label; the role is what the model reasons as. *(This is a note for the downstream persona-frame re-carve — [ADR-383](ADR-383-the-consistent-agent-framework-and-mandate-as-purpose.md) §7 item 1 — not a change in this ADR.)*

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

**The legibility marker (LANDED on explicit operator go — the one code change in this ADR):** a comment block on `ReviewerContext` (`api/agents/occupant_contract.py`, above the `mandate_md`/`autonomy_md` fields) noting that they are *carried for cross-rung contract uniformity and exercised only when a consequential-action (Rung-2) occupant fills the seat; over a Rung-1 steward they are degenerate.* This is **doc-in-code** — an inert comment, no field add/remove, no behavior change (`occupant_contract.py` stays pure-data; it imports clean). The operator approved landing it this session (see §5).

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
- **whether the graduated propose → witness → earn-autonomy continuum is the trust model** — ADR-380 §5 **resolved** the vision boundary (Rung-2 autonomous consequential delegation is scoped *out* of the vision, an optional future capability). The consequence ADR-380 §5 names: ADR-382's trust model is now **cleanly build-when-demanded, not blocked on a vision decision.** **This ADR still does not *decide* that trust model — it is ADR-382's discourse — but it is no longer gated on an open vision question.**

The boundary: *ADR-381 decides that Freddie holds the CRUD + authority-setting power; ADR-382 decides what that power operates on (the persona seat's lifecycle + trust).*

---

## 3. Why this is canon-coherent (the alignment, condensed)

The full alignment argument is the [two-order direction §3](../analysis/freddie-as-the-workspace-agent-and-the-two-order-agent-model-2026-06-27.md); the load-bearing points:

- **ADR-216 (orchestration vs judgment) — RE-ASSERTED.** Freddie ← the orchestration/OS half (now first-class + named); persona agents ← the judgment half (now N user-directed seats). The ADR-260→345 hybrid is re-cut, not extended.
- **ESSENCE (asset/labor/management/dividends) — survives, made MORE literal.** Management renames Reviewer→Freddie; the labor (persona agents) bears the judgment. *(With ADR-380 §5 resolved, the ESSENCE external lead was re-cut to v14.2: the moat is led by the **substrate + `trace`/provenance**, not the judgment seat; the vision is the **substrate commons + Freddie**; the judgment layer is the future deepening. The moat sentence was NOT escalated to the commons-altitude — it stays at "durable attributed memory" with `trace` as its defensible core. See §4.)*
- **ADR-222 (OS framing) — Freddie is the kernel-agent personified.** Substrate operationally owned by the kernel-agent; persona agents = applications under operator-authored judgment.
- **ADR-373 (multi-principal) — Freddie is the arbiter as system manager.** It reconciles the commons (keeping it coherent), not by overriding a persona's judgment.
- **ADR-378 (workspace = outermost unit) — composes.** One Freddie per workspace is why the ceiling lands at the workspace; "one Freddie across many workspaces" *is* the undefined federation case.

---

## 4. Cascade (the doc updates this ADR lands)

Per the seat-canon-generalization (D4) and the Freddie label (D1), the cascade touches the seat canon + GLOSSARY + the occupant docs + ESSENCE. **With ADR-380 §5 resolved, ESSENCE was taken to full reconciliation (v14.2): management renamed Reviewer→Freddie AND the external lead re-cut to substrate-led + `trace`-defended, with the judgment seat named the future deepening** (per operator decision, this session).

| Doc | Update | Bound by |
|---|---|---|
| **[reviewer-seat-substrate.md](../architecture/reviewer-seat-substrate.md)** | Generalize "one judgment seat per workspace" → "one management seat (Freddie) + N judgment seats"; name `/workspace/persona/` the *management* seat occupied by Freddie; preserve the seat≠occupant model as the inheritance vehicle for judgment seats (per-seat detail → ADR-382). | D4 |
| **[reviewer-occupant.md](../architecture/reviewer-occupant.md)** | Name Freddie as today's Rung-1 occupant of the management seat; add the Rung-1 harness note (budget/pace exercised, mandate/autonomy carried-not-exercised). | D1, D2, D3 |
| **[reviewer-occupant-contract.md](../architecture/reviewer-occupant-contract.md)** | The canonical prose home for D3 — note that `ReviewerContext` carries `mandate_md`/`autonomy_md` on every wake but they are *exercised only at Rung 2* (the contract is uniform across rungs; the fields are degenerate over a Rung-1 steward). | D3 |
| **[GLOSSARY.md](../architecture/GLOSSARY.md)** | Add **Freddie** entry (Rung-1 substrate steward / named occupant of the management seat). *(The reviewer-slug/prefix Exceptions rows added here were DELETED by the full-rename reversal — no exception remains; only the `persona/` seat-path row stays.)* | D1, D4 |
| **ESSENCE.md** (DONE — v14.2) | (1) Name Freddie as the management role (asset/labor/**Freddie**/dividends). (2) **Re-cut the external lead** per the resolved ADR-380 §5: the moat leads with the **substrate + `trace`/provenance** (NOT the judgment seat — reverses v14.0's "judgment seat leads"); the vision is the **substrate commons + Freddie**; the judgment seat is named the future Rung-2 deepening. (3) Retire the judgment-led positioning seeds (preserved for lineage). The moat sentence stays at "durable attributed memory" with `trace` as its defensible core — NOT escalated to the commons-altitude. *(Operator decision this session: "full ESSENCE reconciliation.")* | D1; ADR-380 §5 (resolved) |

**Cascade note (the open-item discipline):** the two-order direction §7 named the ESSENCE moat-sentence relocation and the DP24/DP30 accountability relocation as cascade surface, both gated on ADR-380 §5's then-open items. **ADR-380 §5 is now resolved** (same day): the moat is **NOT** escalated to the commons-altitude (it stays "durable attributed memory," led by `trace`), and Rung-2 judgment is out of the vision. So the ESSENCE re-cut here (v14.2) renames management→Freddie and re-leads with the substrate + `trace` — it does **not** relocate the moat *sentence* to "judgment seat = the 2nd-order persona agent" (that escalation was the rejected option). **The DP24/DP30 accountability relocation** (judgment-accountability → the persona agent) is **NOT done here** — it is ADR-382's, not governed by the moat decision. That is the one cascade item this ADR still leaves to ADR-382.

---

## 5. The D3 code marker (LANDED on explicit operator go)

Per the operator's D3 instruction ("scope a code change, get go-ahead") the marker was scoped, presented, and — on explicit go this session — **landed**:

- **What landed**: a comment block on `ReviewerContext` (`api/agents/occupant_contract.py`, above the `mandate_md`/`autonomy_md` fields) noting these fields are carried for cross-rung contract uniformity and are *exercised only when a consequential-action (Rung-2) occupant fills the seat — degenerate over a Rung-1 steward*; with the explicit contrast that `budget_yaml`/pace ARE exercised at Rung 1; and the load-bearing consequence ("autonomy harness validated on Freddie" is false).
- **What it is NOT**: not a behavior change, not a contract change, not a field add/remove. The envelope keeps loading both fields unconditionally (Singular-Implementation; the contract is uniform across rungs — §D3). `occupant_contract.py` stays pure-data — it parses + imports clean (verified this session).
- **Render parity (CLAUDE.md §5)**: none required — `occupant_contract.py` is a pure-data module with no env-var/secret/schema surface; the comment is inert across all four services.
- **Why a comment, not prose-only**: D3's honesty is *also* carried by canon prose (reviewer-occupant-contract.md §"The Rung-1 harness split" + reviewer-occupant.md, §4); the in-code marker makes the same honesty legible at the field definition a future engineer reads. The two are redundant by design (the prose is the canonical home; the comment points back to it).

---

## 6. What this ADR does NOT do

- **DID** rename the occupant entity fully (reviewer→freddie in code + data; the 2026-06-29 reversal of D1's original keep-slug — see the D1 amendment banner). The seat *path* `/workspace/persona/` is NOT renamed (seat≠occupant).
- Does not change schema, the gate, the wake architecture, or the occupant contract's *behavior*. The only code change is the §5 legibility comment (inert; landed on explicit operator go).
- Does not build persona-agent seats, lifecycle, creation surface, or trust model (ADR-382, Rung 2 — D4/D5 name only Freddie's governing side).
- Does not decide the per-judgment-seat substrate shape (D4 — ADR-382 inherits).
- Does not *itself* close ADR-380 §5's items (the operator closed them the same day — vision: Rung 2 out of the vision; moat: kept at "durable attributed memory" led by `trace`). This ADR *consumes* the resolution in its ESSENCE re-cut; it does not re-decide it.
- Does not escalate ESSENCE's moat sentence to the commons-altitude (the rejected option) — the v14.2 re-cut keeps "durable attributed memory" and re-leads with the substrate + `trace`. Does not relocate DP24/DP30 accountability (that is ADR-382's — §4 cascade note).
- Does not promote the rung ladder to an axiom (ADR-380 §6 — a separate, deliberate cascade edit if ever).
- Does not touch the re-founding keystone cascade (orthogonal track).

## 7. Cross-references

- Upstream vocabulary: [ADR-380](ADR-380-the-activation-ladder-and-the-judgment-deferral-line.md) (rungs + the harness split), [the two-order direction](../analysis/freddie-as-the-workspace-agent-and-the-two-order-agent-model-2026-06-27.md) (Picture B).
- Sibling: [ADR-382](ADR-382-persona-agent-seats-the-rung-2-judgment-layer.md) (the Rung-2 persona-agent seat ADR — inherits D4/D5's governed side).
- Precedent: [ADR-251](ADR-251-system-agent-reviewer-first-class-surfaces.md) (relabel-keep-slug).
- Seat canon generalized: [reviewer-seat-substrate.md](../architecture/reviewer-seat-substrate.md) + [reviewer-occupant.md](../architecture/reviewer-occupant.md) + [reviewer-occupant-contract.md](../architecture/reviewer-occupant-contract.md) (ADR-315).
- File-structure beneath Freddie: [ADR-383](ADR-383-the-consistent-agent-framework-and-mandate-as-purpose.md) (the consistent agent framework — one file-structure; MANDATE = every agent's purpose, Freddie's is the steward-mandate; the persona-frame re-carve scope). Surfaced *from* this ADR's frame-re-carve discourse.
- Owed-from: [ADR-375](ADR-375-phase-1-substrate-for-humans-and-external-agents.md) §7 Cut 1.
