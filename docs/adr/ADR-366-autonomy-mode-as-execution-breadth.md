# ADR-366 — Autonomy Mode as Execution Breadth: the grant/contract split

> **Status**: **Accepted** (2026-06-25). Full-purity B adopted per operator decision — breadth is governed by AUTONOMY *mode*, not by capability lock; the lock shrinks to its irreducible core (the grant + the per-act floor + system/).
> **Date**: 2026-06-25
> **Authors**: KVK + Claude
> **Discourse base**: [`docs/analysis/autonomy-mode-as-execution-breadth-vs-the-lock-2026-06-25.md`](../analysis/autonomy-mode-as-execution-breadth-vs-the-lock-2026-06-25.md) — the axiomatic stress-test the operator's challenge produced.
> **Re-ratifies**: [ADR-293](ADR-293-governance-operational-substrate-taxonomy.md) (the load-bearing lock is the authority/spend grant only; everything else mode-governed — a conclusion ADR-320 partially walked back for prefix-elegance).
> **Amends**: [ADR-320](ADR-320-constitution-region-topological-cut.md) — the boundary placement of `_preferences`/`_expected_output` (D-level "DESIGN CHOICE, open to redesign without violating an axiom" per ADR-320 §135). The five-root cut, the pure-prefix `_is_path_locked`, and the topology-IS-policy property are PRESERVED; one root is added and `governance/`'s membership is refined.
> **Composes with**: [ADR-307](ADR-307-unified-permission-taxonomy.md) (the witness gate that now governs `contract/` writes — already built, no new mechanism), [ADR-319](ADR-319-stewardship-of-intent-against-ground-truth.md) (the installed judgment revising its own operating contract against ground truth), [ADR-345](ADR-345-expected-output.md) (autonomy = the witness dial), [ADR-334](ADR-334-per-operation-pricing.md) (the AUTONOMY dial IS the pricing axis — breadth=mode makes the safety axis and the pricing axis the same dial).
> **Dimensional classification** (Axiom 0): **Identity** (Axiom 2 — who may author what) + **Substrate** (Axiom 1 — the topology) + **Channel** (Axiom 6 — the lock is the legible permission surface). The breadth control collapses onto one axis (AUTONOMY mode), a Singular-Implementation win (Derived Principle 14).

---

## 1. The challenge that re-opened it

> *"If Claude Code can change anything in a repo including its CLAUDE.md, what prevents us? Is self-running riskier — technical or conceptual? Autonomy modes should dictate execution breadth, and if it is truly self-improving, we should have both the permission AND the mechanism for our agent to self-edit its key documents."* — the operator, 2026-06-25.

The challenge is correct and was **already half-canon**: ADR-293 reached this exact conclusion (the load-bearing lock is two governance instruments — authority + spend — everything else mode-governed) and cited the Claude Code model verbatim ("the user's restraint over CC's actions lives in the *gating mode*, not in a *capability lock*; the audit is the git revision chain; revert is one command"). ADR-320 then collapsed per-file locks into a pure `startswith("governance/")` prefix — a real simplification — but in doing so **swept four file-classes into one locked root for prefix-elegance**, over-locking past what ADR-293 justified. This ADR corrects that drift.

## 2. The answer: technical or conceptual? — conceptual, and narrower than the lock

"Self-running is riskier" is **not** the reason for the lock. The operator is protected by three mechanisms that exist independently of any file lock:
- **The witness dial** (AUTONOMY mode, ADR-345/ADR-307): consequential writes route to the operator's Queue *before* binding under `bounded`/`supervised`; auto-bind under `autonomous`. This IS the breadth control.
- **The per-act floor** (ADR-343, topology-enforced at the consequential-gate class DP23): per-act integrity + outcomes-in honesty; never moves by the agent's hand.
- **The authored-substrate audit** (ADR-209): every write attributed + parent-pointered + revertible — strictly stronger than git, which is what makes CC safe to self-edit.

Run the FOUNDATIONS Axiom-0 test (a mechanic must not span a dimension without necessity): every threat the lock claims to stop is already stopped by one of those three. Lock-as-breadth-control spans the file-access dimension redundantly with witness-routing + resource-ceiling + per-act-floor — a design-drift smell.

**The one genuine carve-out is logical, not risk:** an agent cannot author *the declaration of its own authorization*, because a gate the gated party can open is not a gate. This is the operator's own principle honored — "autonomy mode dictates breadth" is only TRUE if the agent cannot edit the autonomy mode. Two files are the agent's authorization:
- `_autonomy.yaml` (+ `AUTONOMY.md`) — the **authority grant** (how far decisions bind).
- `_budget.yaml` — the **spend grant** (how much may be spent deciding). The "should" test settles it: a fund manager decides how to *deploy* capital, never how much capital they are *given* — that is the allocator's (operator's) grant, upstream of the operation, not a judgment within it. Even a perfectly-trusted autonomous agent should not move its own spend authorization. (The balance hard-stop is a *separate* net for a *different* failure — runaway spend within an honest budget — and does not bear on whether the agent should author the grant.)

Both are the same class — **the operator's grant of the terms of engagement** — distinct from the work the agent does within those terms.

## 3. The decision — the grant/contract split

`governance/` is split by the "should the agent be able to write its own X?" test into two roots:

| Root | Contents | Lock | Rationale |
|---|---|---|---|
| **`governance/`** (the GRANT) | `_autonomy.yaml`, `AUTONOMY.md`, `_budget.yaml` | **Locked-always** (DENY, every mode, every LLM caller) | The agent's authorization. A grant the grantee can rewrite is not a grant. The irreducible lock (re-ratifies ADR-293's "two governance instruments"). |
| **`contract/`** (the operating CONTRACT) | `_preferences.yaml`, `_expected_output.yaml` | **Mode-governed** (NOT in any reviewer lock-prefix → the ADR-307 witness gate routes: QUEUE under bounded/supervised, APPLY under autonomous) | What the operator declares the agent OWES + PREFERS. Editing it grants the agent NO new power — it changes what the agent is measured *against*. So breadth = the AUTONOMY dial, not a lock. |

**Why a new root, not a per-file exception:** the grant-vs-contract distinction is a *semantic-class* difference, exactly the kind the five-root cut exists to express (ADR-320 split `context/_shared/` for the same reason). Two files of class "grant" and two of class "contract" sitting in one root is the same impurity ADR-320 fixed. A new root keeps `_is_path_locked` a pure prefix function — **no filename ever appears in the lock logic** (ADR-320's load-bearing property is preserved).

### Caller matrix for `contract/`
| Caller | `governance/` (grant) | `contract/` | Why |
|---|---|---|---|
| **reviewer** | locked | **mode-governed** | the seat revises its own operating contract against ground truth (ADR-319), witness-gated |
| **mcp** (foreign LLM) | locked | locked | lowest trust; does not revise the operator's contract |
| **agent** (specialist) | locked | locked | not its concern; writes `operation/` |
| **operator** | writable | writable | the operator's own grant + contract |
| **system** | locked | locked | deterministic actors target named paths |

### The mechanism is already built (no new gate)
ADR-307's `resolve_permission` already decides APPLY (autonomous) / QUEUE (bounded → witness) / DENY (governance-locked) and already reads `_autonomy.yaml`. Today `governance/`-prefix DENY pre-empts that for the contract files. Removing the contract files from the reviewer lock-prefix lets the **existing** witness gate govern them — a Reviewer `WriteFile` to `contract/_expected_output.yaml` QUEUEs under bounded, APPLIES under autonomous. **No new mechanism; the lock just stops shadowing the gate that was always there.**

## 4. What stays locked, always (the irreducible set)
1. `governance/` — the grant (`_autonomy` + `_budget`). The dial-that-sets-the-dial.
2. `system/` — orchestration runtime state (not the seat's; deterministic actors own it).
3. The **per-act floor** (ADR-343) — topology-enforced at the consequential-gate class (DP23); the per-act risk/quality envelope + outcomes-in attestation honesty. Never moves by the agent's hand, in any mode. (For the trader this is `operation/trading/_risk.md` — note it lives in `operation/` and is *writable by root* but is the floor by its consequential-gate class; the floor's inviolability is enforced at the gate + the principles.md §0 rule, not by the write-topology — see ADR-343 + the trader `principles.md` §0 writable-path-test floor exception.)

Everything between breadth (`governance/`) and per-act integrity (the floor) is mode-governed.

## 5. Why this is safe (the safety relocates, it does not weaken)
Under `autonomous`, a Reviewer can now write `contract/_expected_output.yaml`. The safety is not removed — it relocates from the lock to the mechanisms that were always doing the real work:
- **Witness dial**: under bounded/supervised the write QUEUEs (operator witnesses before bind). Under autonomous the operator *chose* witness-not-gate (ADR-345). The dial IS the breadth the operator asked for.
- **Audit**: every edit attributed (`reviewer:ai:...`) + revertible (ADR-209). A bad self-revision is one revert away.
- **Floor unmoved**: `_autonomy.yaml` (breadth) + the per-act floor (ADR-343) never move by the agent's hand. Breadth and per-act integrity are the two poles lock protects; everything between is mode-governed.

The asymmetry this fixes: the agent could *already* amend `constitution/MANDATE.md` (a higher-authority document) but not `contract/_preferences.yaml` (cadence config). There was no principle under that asymmetry — only prefix-drift.

## 6. The single breadth axis (the deeper payoff)
Before: two parallel breadth controls — AUTONOMY mode AND the topology lock — overlapping and occasionally contradicting (the unattended-soak's "active principal but can't write here", the contradiction ADR-293 §43 predicted). After: breadth collapses onto AUTONOMY mode alone, with the single `governance/` carve-out (the dial that sets the dial). One axis, not two (DP14). This also aligns the safety axis with ADR-334's pricing axis (Supervised/Delegated/Autonomous seats) — breadth=mode means the product's pricing dial and its safety dial are the same dial.

## 7. Implementation scope
- **Path constants** (`workspace_paths.py`): `CONTRACT_ROOT` added; `CONTRACT_PREFERENCES_PATH` + `CONTRACT_EXPECTED_OUTPUT_PATH` (the files move `governance/` → `contract/`); `GOVERNANCE_PREFERENCES_PATH`/`GOVERNANCE_EXPECTED_OUTPUT_PATH` kept as deprecated aliases during the reader migration, then removed. **Done.**
- **Gate** (`CALLER_WRITE_POLICY`): `governance/` stays in reviewer/mcp/agent/system locked sets; `contract/` added to mcp/agent/system (locked) but NOT reviewer (mode-governed). `_is_path_locked` unchanged (still pure prefix). **Done.**
- **Readers** (envelope `_UNIVERSAL_ENVELOPE_DECLS`, `review_policy`, `programs` fork/reapply, `ask_builder`, `wake`, `kernel_surfaces`, occupant_contract): point at the new `contract/` constants.
- **Frontend** (render-parity, CLAUDE.md §5): `content-shapes/expected-output.ts`, the `writeShape` path-map, route pages reading these paths.
- **Bundles** (both reference-workspaces): move `governance/_preferences.yaml` + `governance/_expected_output.yaml` → `contract/`; update `MANIFEST.yaml` substrate_abi refs + path_zones.
- **Live-workspace data migration**: for each active workspace, move the two files `governance/` → `contract/` (revision chain preserved; operator-proxy attribution), so live cockpits and the standing-obligation check read the new home.
- **Tests**: `test_adr320_permission_topology.py` (the topology assertions gain `contract/` mode-governed), + the bundle/expected-output/preferences tests repoint paths. New `test_adr366_grant_contract_split.py`: reviewer CAN write `contract/` (gated by mode), CANNOT write `governance/` (DENY any mode); mcp/agent/system locked from `contract/`.
- **Canon cascade**: FOUNDATIONS DP25 (the topology principle — five roots → six; the grant/contract refinement), agent-composition.md §3.2.1/§4.4 (the write-authority axis), GLOSSARY (contract/ root entry), ADR-320 amendment banner.

## 8. Validation
A funded unattended soak under `autonomous` on yarnnn-author: does unlocking `contract/` produce **coherent self-revision against ground truth** (the agent amends a stale `_expected_output`/`_preferences` with a reason, witness-gated visible in the revision chain) — or **drift** (churning the contract to dodge the bar)? The probe-before-canon discipline: if it self-revises coherently, B is validated; if it drifts, the floor (witness dial under bounded) is where it lands. Recorded in `docs/evaluations/`. (The soak instrument `probe_unattended_soak_local.py` + the principles.md §0 writable-path test from the prior session are the substrate.)

## 9. The honest bottom line
The operator's instinct was correct and already half-canon: the lock was over-applied; ADR-293 said so; ADR-320 drifted past it for prefix-elegance. Self-running is not riskier in a way the lock addresses — the witness dial + floor + audit carry the risk whether or not a file is locked. The one real carve-out is conceptual: an agent cannot author the declaration of its own authorization. Everything else the operator asked for — permission AND mechanism to self-edit its operating contract, breadth governed by autonomy mode — is sound, consistent with the Claude Code model the canon already cites, and consistent with the agent already being able to amend its MANDATE. Breadth becomes one axis (the AUTONOMY dial); the lock shrinks to the grant + the floor + system/.
