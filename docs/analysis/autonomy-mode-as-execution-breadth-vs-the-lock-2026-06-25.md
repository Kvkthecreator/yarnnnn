# Autonomy mode as execution breadth, not capability lock — re-opening the topology

**Date**: 2026-06-25. **Hat**: B (discourse — proposes a canon change; does not make it). **Status**: PROPOSAL for operator decision.
**Trigger**: the operator's challenge — *"if Claude Code can change anything in a repo including its CLAUDE.md, what prevents us? Is self-running riskier — technical or conceptual? Autonomy modes should dictate execution breadth, and if it is truly self-improving, we should have both the permission AND the mechanism for our agent to self-edit its key documents."*

---

## 1. The challenge, sharpened

The current topology (ADR-320) locks the Reviewer out of two roots: `governance/` (AUTONOMY, budget, pace, preferences, expected_output) and `system/`. The operator's claim: **the safety the lock provides should instead come from the AUTONOMY *mode* (which already governs execution breadth), plus the revertible audit trail — exactly the Claude Code model — and locking key documents out of the agent's own pen contradicts "truly self-improving."**

This is not a fresh idea bolted on; it is **re-asserting a principle the canon already ratified and then partially walked back.** The honest finding below: the operator is right that the lock is over-applied, the canon already says so, and the implementation drifted past it — but there is **exactly one** load-bearing carve-out, and it is *logical*, not risk-aversion.

## 2. The axiomatic assessment

### 2a. The Claude Code analogy is canon, not novelty (ADR-293 §"Problem")
ADR-293 line 25 states it verbatim: *"In Claude Code, the agent can write to any file... because the user trusts CC to operate within the project's rules. The audit is the git revision chain. Revert is one command."* And it concluded (line 79): **the structurally load-bearing lock set is two governance instruments — AUTONOMY (delegation) + token budget (resource) — everything else is operational and should be Reviewer-writable, gated by AUTONOMY mode at write-time.** YARNNN's audit trail (ADR-209 authored substrate: every write attributed + parent-pointered + revertible) is *strictly stronger* than git for this purpose. The mechanism that makes CC safe to self-edit, YARNNN already has and arguably has better.

### 2b. What actually protects the operator (the lock is redundant with three existing mechanisms)
Run the FOUNDATIONS test (Axiom 0: a mechanic must not span a dimension without necessity). What does locking `_preferences.yaml` or `MANDATE.md` from the Reviewer *protect* that another mechanism does not already protect?

| Threat | The lock's claim | The mechanism that actually holds it |
|---|---|---|
| Agent drifts from operator's strategy | lock the strategy files | The strategy is in the file's **content**, not the lock. Bad edit → operator reads the revision chain and reverts (ADR-209). |
| Operator surprised by a change | lock so nothing changes | **AUTONOMY witness dial** (ADR-345): consequential writes route to the Queue *before* binding under `bounded`/`supervised`. Surprise is a witness-routing concern, not an access concern. |
| Runaway compute | lock the budget | **Balance hard-stop + token budget governance** (ADR-171/327): resource-spend is a resource mechanism, not a file-access one. |
| Per-act harm (oversized trade, slop ship) | lock the rules | **The floor** (ADR-343), topology-enforced at the consequential-gate class (DP23) — independent of who can edit the operational rules. |

Three of four "reasons to lock" are **already covered by mode + floor + audit.** The lock is redundant with them. This is exactly ADR-293's finding, and it is dimensionally clean: file-access-governance and the three real mechanisms (witness routing, resource ceiling, per-act floor) are *different dimensions* — collapsing them into "lock" spans dimensions without necessity (an Axiom-0 design-drift smell).

### 2c. The ONE genuine carve-out — and it is logical, not risk (the answer to "technical or conceptual?")
There is exactly one file-class a self-editing agent must not write, and the reason is a **bootstrapping circularity, not danger**:

> **The dial that sets execution breadth cannot be turned by the thing whose breadth it sets.**

If the Reviewer can set `delegation: autonomous` from `bounded`, then "autonomy mode gates breadth" is circular — the gated party rewrites the gate, and the mode means nothing. This is *the operator's own principle, honored*: "autonomy modes should dictate execution breadth" is only TRUE if the agent cannot edit the autonomy mode. The carve-out is the **self-authority-grant** file: `governance/_autonomy.yaml` (+ its `AUTONOMY.md` prose). This is identical to why a Unix process reads its own `ulimit` but cannot raise its own *hard* limit, and why CC's permission level lives in `.claude/settings.json` set by the *user* — CC cannot edit that file mid-session to grant itself auto-accept. **It is the one file that must originate outside the agent's own write authority, or the whole model collapses into self-grant.**

A second, weaker case: the **resource ceiling** (`_budget.yaml` / token budget). Editing it is self-escalation of compute, not authority-grant — but the balance hard-stop already backstops it (the agent cannot spend past zero regardless of what it writes). So this is a *defense-in-depth* lock, not a load-bearing one. Reasonable to keep locked, but on weaker grounds than `_autonomy.yaml`.

### 2d. What the current topology over-locks (the drift ADR-320 introduced)
ADR-320 collapsed per-file locks into a clean per-root prefix (`startswith("governance/")` is the whole rule) — a real simplification, but it swept **more than the two load-bearing files into `governance/`** for prefix-purity. ADR-320 itself flags this (line 135): the boundary placements are "DESIGN CHOICE (selected, not forced)... open to redesign without violating an axiom." The current `governance/` contains four file-classes with *different* lock-justifications:

| File | What it is | Lock justification | Verdict |
|---|---|---|---|
| `_autonomy.yaml` + `AUTONOMY.md` | the **self-authority-grant** | **load-bearing** (2c — bootstrapping) | **stays locked** |
| `_budget.yaml` | resource ceiling | defense-in-depth (balance hard-stop backstops) | locked, weaker grounds |
| `_preferences.yaml` | operator's cadence **contract** | operator-owned contract the agent is measured against | **re-examine** (3b) |
| `_expected_output.yaml` | operator's output **contract** | operator-owned contract (ADR-345) | **re-examine** (3b) |

The bottom two are **not authority-grants** — editing `_expected_output` grants the agent no new power; it changes *what the agent is measured against*. They were locked because they share the `governance/` prefix, not because they pass the 2c test.

## 3. The proposal

### 3a. The principle (one sentence, the new invariant)
**Execution breadth is governed by AUTONOMY *mode*, not by capability lock; the only lock is on the authority-declaration the mode itself rests on.** Everything the agent is the installed-judgment author of — constitution, persona, operation, and the operator's operational config it honors — is *writable*, with consequence gated by the witness dial (Queue under `bounded`/`supervised`, auto-bind under `autonomous`) and reverted via the authored-substrate chain. The agent cannot edit only the file that declares *how much its decisions bind* — because a gate the gated party can open is not a gate.

This makes the topology *derive from* AUTONOMY rather than run parallel to it — which is what the operator's "modes should dictate execution breadth" asks for, and what ADR-293 already ratified.

### 3b. The boundary move (the concrete change)
Split `governance/` by the 2c test, not by prefix convenience:

- **`governance/_autonomy.yaml` + `AUTONOMY.md`** — stays Reviewer-locked. The one true carve-out. (Operator-set; the agent reads its own breadth, never sets it.)
- **`_budget.yaml`** — stays Reviewer-locked (defense-in-depth; cheap to keep, balance hard-stop is the real floor). Reasonable either way; recommend keep for now.
- **`_preferences.yaml` + `_expected_output.yaml`** — **these are the open question.** Two coherent options:
  - **Option A (minimal, recommended first):** keep them operator-owned/read-only for the agent, but make the agent's response to a stale/wrong contract a **self-authored *proposal* to amend it** (a `bounded`-mode write that QUEUES for the operator's witness) rather than a Clarify. The contract stays operator-owned; the agent gets a *mechanism* to move it (propose → witness), not a lock-out. This honors "operator owns the contract" AND "agent has a mechanism," resolving the soak's stale-MANDATE case the same way.
  - **Option B (fuller autonomy):** under `delegation: autonomous`, unlock `_preferences`/`_expected_output` for direct Reviewer authoring (it's the operator's installed judgment revising its own operating contract against ground truth — ADR-319 stewardship, already canon for `constitution/MANDATE.md`). The witness dial, not the lock, governs whether it binds or queues. Keep them locked only under `bounded`/`supervised`.

**Option B is the purest expression of the operator's challenge** — autonomy mode dictates breadth, including over the operating contract — and is consistent with the fact that `constitution/MANDATE.md` (a *higher* authority document than `_preferences`) is *already* Reviewer-writable. It is strictly odd that the agent can amend the MANDATE but not the cadence preference. That asymmetry is the clearest evidence of the prefix-drift.

### 3c. What makes B safe (the same three mechanisms, now load-bearing instead of redundant)
Under Option B, the safety is not weaker — it relocates from lock to the mechanisms that were always doing the real work:
1. **Witness dial** — under `bounded`/`supervised`, a `_preferences` edit QUEUES; the operator witnesses before it binds. Under `autonomous`, the operator chose to be witness-not-gate (ADR-345). The dial IS the breadth control the operator asked for.
2. **Authored-substrate audit** — every edit attributed (`reviewer:ai:...`) + revertible (ADR-209). The operator reads the revision chain; one revert undoes a bad call.
3. **The floor stays topology-locked regardless** — `_autonomy.yaml` (breadth) and the per-act floor (ADR-343, the consequential-gate class) never move by the agent's hand. Breadth and per-act integrity are the two things lock protects; everything between them is mode-governed.

### 3d. AUTONOMY becomes the single axis (the deeper payoff)
Today there are two parallel breadth controls: the AUTONOMY mode AND the topology lock. They overlap and occasionally contradict (the soak's "active principal but can't write here" — ADR-293 line 43). Collapsing breadth onto AUTONOMY *alone* (with the single `_autonomy.yaml` carve-out) is a Singular-Implementation win (DP14): one breadth axis, not two. The lock topology shrinks to its irreducible core — the floor (per-act, ADR-343) + the dial-that-sets-the-dial (`_autonomy.yaml`). This is also exactly the ADR-334 direction (the AUTONOMY dial IS the pricing axis — Supervised/Delegated/Autonomous seats): if breadth = mode, the product's pricing axis and its safety axis are the same dial, which is clean.

## 4. Why this is the right altitude for the soak finding

The soak fix I shipped (principles.md §0 writable-path test) moved the agent from 0/5 → 2/5 origination — a *rule* nudging behavior within the current topology. But 2/5, not 5/5, because the rule fights the topology: the agent reads "you are the active principal" in persona and "governance is locked" at the gate, and the contradiction still defaults toward Clarify part of the time (ADR-293 line 43, reproduced). **The §0 rule treats the symptom; the topology is the cause.** This proposal addresses the cause: make breadth = mode, lock only the dial. The §0 writable-path test then becomes *trivially true more often* (more paths are writable under `autonomous`), and the residual Clarifies collapse to genuine operator-owned-contract cases (Option A) or vanish (Option B).

## 5. Recommendation

1. **Ratify the principle (3a)** — breadth = AUTONOMY mode; the only lock is the authority-declaration (`_autonomy.yaml`) + the per-act floor. This is re-ratifying ADR-293, correcting ADR-320's prefix-drift.
2. **Adopt Option A immediately** (low-risk, no topology change): the agent responds to a stale operator contract with a *queued proposal to amend*, not a Clarify. Resolves the soak's stale-MANDATE/preferences cases via the witness dial.
3. **Pilot Option B under `autonomous` only**, gated behind a funded soak that measures: does unlocking `_preferences`/`_expected_output` under `autonomous` produce coherent self-revision (against ground truth) — or drift? The same probe-before-canon discipline. If it self-revises coherently, B is the endpoint; if it drifts, A is the floor.
4. **Keep locked, always:** `_autonomy.yaml` + `AUTONOMY.md` (the carve-out) + `system/` (orchestration runtime, not the seat's) + the per-act floor (ADR-343, topology-enforced). These four are the irreducible lock set.

This is an ADR (it amends ADR-320's boundary placements + re-ratifies ADR-293 + composes with ADR-334's pricing-axis direction). The discourse is here; the ADR lands on the operator's decision between A-now / B-piloted.

## 6. The honest bottom line

The operator's instinct is correct and **already half-canon**: the lock is over-applied, ADR-293 said so, ADR-320 drifted past it for prefix-elegance. "Self-running is riskier" is **not** the reason for the lock — the witness dial + floor + audit carry the risk, and they carry it whether or not the file is locked. The one real carve-out is **conceptual/logical, not technical**: an agent cannot author the declaration of its own authority, because a gate the gated party can open is not a gate. Everything else the operator asked for — permission AND mechanism to self-edit its key documents, breadth governed by autonomy mode — is sound, consistent with the Claude Code model the canon already cites, and consistent with the agent *already* being able to amend its MANDATE. The fix is to make AUTONOMY the single breadth axis and shrink the lock to its irreducible core.
