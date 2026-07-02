# ADR-383 — The Consistent Agent Framework: One File-Structure, and MANDATE as Every Agent's Purpose (Freddie's is the Steward-Mandate)

> **⊕ Amendment (2026-07-02) — `_autonomy.yaml` joins the steward-seed set.** The §7-item-2 steward seeds shipped three files (MANDATE + IDENTITY + principles). The **fourth agent-universal governance file, `governance/_autonomy.yaml`, was left behind** — it stayed bundle-owned-absent (ADR-286 D3) even though this ADR's own §5 table classifies `governance/AUTONOMY.md` + `_autonomy.yaml` as *"agent-universal · kernel default ceiling."* The gap surfaced as a live FE symptom: the top-bar Freddie chip GETs `/workspace/governance/_autonomy.yaml` on every page and a no-program workspace **404s** (it was purged by `adr286_purge_dual_write_kernel_defaults.py` and never re-seeded). This amendment seeds it as a **steward default** in `workspace_init`'s `if not program_slug:` branch, exactly like its three siblings, closing the classification this ADR already declared. **The dual-write objection that pulled autonomy out at ADR-269 iter-4 is resolved by this ADR's own `STEWARD_DEFAULT_MARKER` mechanism** — a marked default is overwrite-eligible, so a later program-fork replaces it cleanly. Two marker forms now exist: the HTML comment for prose defaults (`.md`), and the **YAML-comment form `# yarnnn:steward-default`** for the machine-parsed `_autonomy.yaml` (an HTML comment as line 1 would break `yaml.safe_load`; the YAML-comment marker is stripped by `load_workspace_yaml` before parse, so `delegation: manual` parses cleanly). The steward default IS `delegation: manual` — the same fail-closed posture the gate already applies on absence (`review_policy.load_autonomy` → `{}` → manual), so **behavior is unchanged**; the file just makes the posture legible as substrate and stops the FE 404. Existing no-program workspaces are backfilled by `scripts/oneshot/adr383_backfill_steward_autonomy_yaml.py` (idempotent; skips program workspaces + already-present files). **The gate is still untouched** (§4 / §8 hold). Code: `DEFAULT_AUTONOMY_YAML` + `STEWARD_DEFAULT_MARKER_YAML` (`orchestration.py`), the seed line (`workspace_init.py`), the YAML-marker branch (`workspace_utils.is_skeleton_content`), the backfill script, `test_adr286_single_writer_per_path.py` extended.

> **Status**: **Accepted** (2026-06-29) — concept ratified doc-first (committed `9c84cdf`); the **steward-seed implementation** (§7 item 2 — Freddie's kernel-default MANDATE + IDENTITY + principles.md + the `workspace_init` conditional seed + the `is_skeleton_content` marker + the ADR-286 amendment) **landed in the Unit-3 implementation commit**. The **persona-frame re-carve** (§7 item 1) is its own subsequent commit (per the operator's O3 decision). **The ADR-320 D4 / ADR-207 MANDATE hard-gate function is UNTOUCHED** — under this ADR MANDATE is never empty (it always carries at least the steward default), so the gate keeps passing for every workspace; what changed is the *content seeded* (steward defaults) + the ADR-286 D2/D3 carve (§5), not the gate logic.
> **Date**: 2026-06-29
> **Authors**: KVK (operator) + Claude (collaborator)
> **Owes-from**: [ADR-381](ADR-381-freddie-the-rung-1-substrate-steward.md) (Freddie = the Rung-1 substrate steward) — surfaced during the Freddie persona-frame re-carve discourse. The re-carve asked "what does Freddie's frame carry?" and the answer forced the deeper question this ADR settles: *does Freddie need its own governance file-structure, or is there one consistent agent framework where the only difference is the file content?*
> **Builds on**: [ADR-320](ADR-320-constitution-region-topological-cut.md) (the five semantic-class roots + the D4 required-region hard-gate — this ADR refines D4's *interpretation*, not its gate), [the two-order Freddie direction](../analysis/freddie-as-the-workspace-agent-and-the-two-order-agent-model-2026-06-27.md) (Freddie = 1st-order steward; persona agents = 2nd-order judgment — *the same kind of thing*, differing by file *content*), [ADR-315](ADR-315-reviewer-occupant-contract.md) (seat≠occupant — the seat's file-structure is the agent-universal shape), [ADR-314](ADR-314-substrate-conditional-posture.md) (index-not-assert — files are reasoned about by content, not force-filled).
> **Amends**: [ADR-207](ADR-207-primary-action-centric-workflow.md) (MANDATE *semantics* generalize: MANDATE = the agent's purpose; the value-moving **Primary Action** is the *operation-instance* of purpose, not the universal definition — see §5). **Does NOT amend the ADR-320 D4 gate mechanics** (§4).
> **Sibling**: [ADR-382](ADR-382-persona-agent-seats-the-rung-2-judgment-layer.md) (persona-agent seats — this ADR gives them their file-structure: the same one Freddie uses, with the MANDATE/principles content program-authored).
> **Dimensional classification** (Axiom 0): **Substrate** (Axiom 1 — the file-structure that constitutes an agent) over **Identity** (Axiom 2 — what makes Freddie and a persona agent the same *kind*) + **Purpose** (Axiom 3 — every agent has a why; Freddie's is stewardship).

---

## 1. The question

The Freddie persona-frame re-carve ([ADR-381](ADR-381-freddie-the-rung-1-substrate-steward.md) downstream) asked a narrow question — *what does Freddie's system prompt carry?* — and could not be answered without a wider one:

> **Does the Freddie system agent need its own governance file-structure? If yes, what is it? If no, what is the standing, consistent agent framework — and what is the only difference between Freddie and a persona agent?**

The answer this ADR ratifies: **there is ONE agent file-structure. Freddie and persona agents are the same *kind* of thing — an agent constituted by the standard files. Every agent-universal file is present and populated for every agent; the only difference is the file *content*: Freddie's files carry kernel/steward defaults, a program's files carry operation content (and a program activation overwrites the defaults). Freddie is not the agent with *empty* files — it is the agent with the *steward* content.**

This is not a new structure to build — it is a **recognition** that the structure ADR-320 already scaffolds is the universal agent shape, with a kernel-default content set for the bare-workspace steward.

---

## 2. The first-principles derivation (why the "MANDATE is conditional" first-draft was wrong)

The discourse instruction that produced this ADR: *treat the governance/persona/constitution files with the same first-principles approach the prompt envelope is getting — they are all trying to achieve the same objective (constituting an agent), so re-derive, don't force-fit.*

A first draft of this ADR made MANDATE *operation-conditional* (empty for Freddie). The operator's challenge — *"is MANDATE right to be conditional, or can the system agent's mandate simply be reframed?"* — exposed the error: that draft gave Freddie a kernel-default `principles.md` (rules) **but** left MANDATE empty (no purpose). That is asymmetric — *why would the steward get default rules but no default purpose?* The resolution is that **MANDATE is agent-universal, exactly like principles.md, and Freddie has a mandate: stewardship.**

Every file in the seat/governance set answers a fixed question about an agent. Sorting by **is this question agent-universal (every agent answers it, and the steward has a sensible default) or operation-specific (only meaningful when an operation is declared)**:

| Question the file answers | File(s) | Class | Freddie's content (kernel default) |
|---|---|---|---|
| Who am I / how do I reason? (character) | `persona/IDENTITY.md` | **Agent-universal** | the careful, independent steward |
| What are my rules of judgment? | `persona/principles.md` (+`_principles.yaml`) | **Agent-universal** | stewardship rules (§6) |
| **Why do I exist?** (purpose) | `constitution/MANDATE.md` | **Agent-universal** | **the steward-mandate** (§3 D3) |
| How far do my decisions bind? (delegation) | `governance/AUTONOMY.md` + `_autonomy.yaml` | **Agent-universal** | kernel default ceiling |
| What is my spend / attention envelope? | `governance/_budget.yaml` + `_pace.yaml` | **Agent-universal** | kernel default |
| Who fills the seat / rotation history? | `persona/OCCUPANT.md`, `persona/handoffs.md` | **Agent-universal** | the AI occupant (Freddie) |
| What have I decided / learned / am watching? | `persona/{judgment_log, reflection, standing_intent}.md` | **Agent-universal** | the trail (accumulates) |
| What am I on the hook to *deliver*? (output contract) | `contract/_expected_output.yaml` | **Operation-specific** | *(none — Freddie owes coherence, not a declared deliverable)* |
| Durable interpretations | `constitution/PRECEDENT.md` | **Operation-specific** (accumulates with operation) | *(empty until interpretations accrue)* |
| Domain rules (risk, voice, universe, …) | `operation/{domain}/*` | **Operation-specific** | *(none — no domain)* |

**The split falls out — but it is content, not presence.** The agent-universal files are *present and populated for every agent*, including Freddie — they constitute *an agent* (a character, rules, a **purpose**, a ceiling, a resource envelope, a trail). The operation-specific files (`_expected_output`, `operation/{domain}/*`) are the ones with **no sensible steward default** — they are genuinely empty for Freddie and populate only on program activation. **An agent with no operation is still a complete agent with a full universal file-set** — Freddie's universal files carry steward defaults; only the operation-specific files are empty.

**Why "MANDATE conditional" was the error**: MANDATE answers *"why do I exist?"* — a question **every** agent answers, including the steward (its why is stewardship). Treating MANDATE as empty-for-Freddie special-cased the system agent as *the agent without a why*, which is false (the system agent's why is the most stable one in the workspace) and asymmetric with the default-principles.md decision. The fix is to **reframe Freddie's MANDATE, not remove it**.

---

## 3. The decisions

### D1 — There is ONE agent file-structure; Freddie and persona agents are the same kind

The seat file-structure (ADR-315 seat≠occupant; `/workspace/persona/` + `/workspace/governance/` + `/workspace/constitution/`) **is the agent-universal shape**. It constitutes *an agent*, occupant-agnostic and program-agnostic. Freddie (1st-order steward) and persona agents (2nd-order judgment, ADR-382) are **the same kind of thing** — agents constituted by these files — differing only in **file content** (steward defaults vs operation content). No agent gets its own bespoke file-structure; the difference is *content*, never *presence in the schema*.

This is the file-structure expression of the two-order model's core claim (the [two-order direction](../analysis/freddie-as-the-workspace-agent-and-the-two-order-agent-model-2026-06-27.md)): Freddie and persona agents are not different *categories of construct* — they are the same construct with different content. The seat≠occupant model (ADR-315) already supports this; this ADR names the file-structure as its substrate.

### D2 — The agent-universal files are present and populated for EVERY agent (Freddie carries steward defaults)

Every workspace's agent is constituted by the agent-universal files **populated** — for a bare workspace, with kernel/steward defaults (scaffolded at signup, the way ADR-320 already scaffolds `persona/IDENTITY.md` + `persona/principles.md` as non-skeleton). The operation-specific files (`contract/_expected_output.yaml`, `operation/{domain}/*`) are empty for Freddie and populate on program activation. `operation/` empty remains the bare-workspace signal (ADR-320 D4 — **unchanged**).

The hard-gate (ADR-320 D4) tests the agent-universal required region — `constitution/MANDATE` + `persona/IDENTITY` + `persona/principles` non-skeleton — and **keeps passing for every workspace**, because all three carry kernel/steward defaults from signup. **The gate is untouched** (§4). What ADR-320 D4 called "is this workspace ready to dispatch work" remains true; this ADR adds only that a bare-Freddie workspace *satisfies* it (it has a constituted steward with a steward-mandate) — it is not a gate-failure state.

### D3 — MANDATE is agent-universal (every agent's purpose); Freddie's MANDATE is the kernel-default steward-mandate

`constitution/MANDATE.md` declares **the agent's purpose** — why it exists. This is agent-universal: every agent has a why. Freddie's MANDATE is the **kernel-default steward-mandate**, seeded at signup the same way its default `principles.md` is:

> *Steward this workspace's substrate — keep it coherent, attributed, placed, and legible — on the operator's behalf. Reality enters as attributed observation; place it in its meaning-home with derive-and-cite. Keep the commons coherent across principals. Keep declared connections live. You move no capital and send no irreversible external message; your work is reversible substrate stewardship.*

When a program activates, the bundle-fork (ADR-226) **overwrites** Freddie's MANDATE with the operation's intent (the Primary Action it moves) — the same overwrite-on-activation mechanism that already applies to `principles.md` and `IDENTITY.md`. So MANDATE is never empty: bare workspace → steward-mandate; program active → operation-mandate. The agent reading MANDATE always finds a populated purpose.

This makes the **agent-universal set symmetric**: `IDENTITY.md` (character) + `principles.md` (rules) + `MANDATE.md` (purpose) + `governance/*` (ceilings) are **all** present, **all** seeded with kernel/steward defaults, **all** program-overwritable. The system agent is the agent with the *steward* content, not the agent *missing* content.

### D4 — Standing-obligation is per-agent, read from that agent's own files; the frame carries only the universal pointer

The standing obligation (DP30 — an agent is accountable for what it is configured to produce) is **per-agent**, read from **that agent's own `MANDATE` + `principles.md`** (+ `_expected_output.yaml` when an operation declares one):

- **Freddie's** obligation (its steward-mandate + steward `principles.md`, §6): keep the commons coherent, place intake, fix attribution, keep connections live. A real standing obligation — substrate stewardship, not capital.
- **A persona agent's** obligation (its operation-mandate + bundle `principles.md` — already present in alpha-trader/alpha-author): produce against its mandate, widen aperture on dormancy, hold the floor. The capital/output judgment.

The **persona-frame** (the system prompt) carries only the **universal pointer**: *"apply what your `MANDATE` and `principles.md` declare about what you are on the hook to produce."* The kernel guarantees the agent *looks for* an obligation against its own purpose; each agent's files supply the *content*. This resolves the O1 question (where DP30 lives when it leaves the frame) at the file-structure level: it lives in each agent's MANDATE + principles.md; the frame points; a bare Freddie's steward-mandate carries stewardship obligations; the content is never kernel-hardcoded into the frame or program-monopolized.

### D5 — Freddie needs kernel-default MANDATE + principles.md seeds (the genuinely new authored artifacts)

Because MANDATE + principles.md are agent-universal and Freddie is an agent, the bare-workspace scaffold must **seed both with steward defaults** — the kernel-default the way a bundle ships program MANDATE + principles.md. These are the new authored artifacts the framework implies:
- **`constitution/MANDATE.md`** seeded with the steward-mandate (D3).
- **`persona/principles.md`** seeded with stewardship rules (§6), in the four-field rule shape (`agent-composition.md` §3.2.1).

A program activation overwrites both (the existing bundle-fork path — ADR-226). **Scoped in §7; authored in the implementation pass, not here.** *(This is what closes the asymmetry the operator's challenge exposed: both purpose and rules get steward defaults, symmetrically.)*

---

## 4. The gate is UNTOUCHED (the Model-B dividend)

ADR-320 D4's hard-gate (`_classify_activation_state` / `working_memory` hard-gate: `constitution/MANDATE` + `persona/IDENTITY` + `persona/principles` non-skeleton before operation dispatch) is **not changed by this ADR**. Under D3, MANDATE is never empty — every workspace carries at least the steward-mandate default — so the gate keeps passing from signup. There is **no "empty MANDATE is now legal" gate re-derivation** (that was the discarded Model-A first draft).

The only nuance worth stating for future readers: the gate, read literally ("MANDATE non-skeleton → ready to dispatch"), now passes for a bare-Freddie workspace because its steward-mandate is non-skeleton. That is correct: a bare Freddie *is* ready to do steward work (intake, placement, connections). What it cannot do without a program is *operation* work (recurrences against an operation-mandate) — but that is gated by program activation (the bundle supplies the operation-mandate + recurrences), not by an empty-MANDATE check. The distinction "is there a steward vs is there an operation" is read from **whether MANDATE is the steward-default or a program-overwritten operation-mandate** (a content read, e.g. the program marker per `programs.py::parse_active_program_slug`), not from MANDATE emptiness.

→ **No change to `workspace_utils` skeleton detection, no change to the hard-gate function, no change to `test_adr320_permission_topology.py`'s gate assertions.** The implementation surface (§7) is *seeds + frame*, not *gate*.

---

## 5. What this amends (precisely)

- **ADR-207** (Primary-Action-Centric Workflow) — MANDATE **semantics generalize**: ADR-207 framed MANDATE as declaring the **Primary Action** (the value-moving external write) and hard-gating task creation on it. This ADR generalizes: **MANDATE declares the agent's *purpose*; the Primary Action is the *operation-instance* of purpose** (what purpose looks like when the agent runs a value-moving operation). The steward's purpose (Freddie's MANDATE) names **no** Primary Action — stewardship moves no capital and sends no irreversible message. ADR-207's thesis is preserved *for operations* (every *operation* declares its Primary Action in MANDATE; the program hard-gate still applies to operation dispatch) — what changes is that "MANDATE always names a Primary Action" generalizes to "an *operation*'s MANDATE names a Primary Action; the *steward*'s MANDATE names its stewardship purpose." MANDATE stays the singular "why" file for every agent.
- **ADR-320 D4** — **interpretation refined, gate unchanged** (§4). The required region (`constitution/MANDATE` + `persona/IDENTITY` + `persona/principles`) is preserved verbatim; this ADR clarifies that all three are agent-universal files carrying kernel/steward defaults, so the gate passes for the bare-Freddie state (which is a valid constituted-steward state, not a gate failure). No gate-function change.
- **ADR-286 D2/D3** (the steward-default carve) — the three agent-universal paths (`constitution/MANDATE.md`, `persona/IDENTITY.md`, `persona/principles.md`) move from **bundle-owned-absent** to **kernel-universal-seeded** (steward defaults). **The dual-write elimination ADR-286 protects is preserved**: the kernel seeds them ONLY in `workspace_init`'s `if not program_slug:` branch (a program workspace's single writer stays the bundle-fork; a bare workspace's writer is the kernel). A `STEWARD_DEFAULT_MARKER` makes `is_skeleton_content` classify the steward defaults overwrite-eligible so a later program activation replaces them. **Consonant with the same-day [ADR-384](ADR-384-the-re-founding-meaning-folders-permission-as-metadata.md) amendment**: ADR-384 D1 keeps `persona/` a path-anchored principal-home + MANDATE a fixed-target kernel file (the residue the steward seeds occupy); ADR-383 changes the *content*, ADR-384 keeps the *path* anchored — orthogonal axes. *This part is Implemented* (`orchestration.py` steward constants, `workspace_init.py` conditional seed, `workspace_utils.py` marker, `test_adr286` conditional-discipline gate 9/9).
- **Preserves**: ADR-315 (seat≠occupant — the file-structure is the seat's universal shape), ADR-314 (index-not-assert — the frame reasons from MANDATE content, now always populated), the dual-write *elimination* of ADR-286 (preserved by the conditional seed — see the ADR-286 amendment above), the five semantic-class roots (ADR-320 §7 / DP25 — unchanged; MANDATE stays in `constitution/`), `governance/` as the operator-only ceiling (ADR-366 — unchanged), the bundle-fork overwrite path (ADR-226 — now the mechanism by which a program overwrites the steward-mandate, exactly as it already overwrites principles.md/IDENTITY.md).

---

## 6. Freddie's `principles.md` (the steward default — sketched, authored in implementation)

The kernel-default `persona/principles.md` for a bare workspace declares Freddie's stewardship rules of judgment. Sketch (four-field shape per `agent-composition.md` §3.2.1; authored fully in the implementation pass):

- **intake-placement** — substrate: a `remember`/intake dump in `operation/memory/` or `inbound/`; pass: placed in its meaning-home with derive-and-cite (ADR-376); verdict-on-fail: place it (Freddie's standing job).
- **attribution-integrity** — substrate: a revision with missing/wrong `authored_by`; pass: every revision attributes its principal; verdict-on-fail: fix/flag.
- **commons-coherence** — substrate: conflicting writes to one path (single-writer-per-path, ADR-286); pass: the commons is coherent; verdict-on-fail: reconcile as system manager (not by overriding judgment — the two-order arbiter role).
- **connection-hygiene** — substrate: a stale/broken connector; pass: declared connections are live; verdict-on-fail: surface/repair.
- **the stewardship standing-obligation** — substrate: the steward-mandate (§3 D3) × what the workspace's substrate state shows; pass: the substrate is being tended; verdict-on-fail: tend it (the D4 per-agent obligation, Freddie's instance).

This is **stewardship judgment, not capital judgment** — real rules of judgment in the four-field shape, with no consequential-external-action limb (that is the persona agent's, ADR-382).

---

## 7. Implementation scope (downstream — NOT in this commit)

Doc-first; this ADR ratifies the model. The code lands after, in its own commits (the frame re-carve is the operator's separate-commit-per-O3):

1. **The persona-frame re-carve** (`reviewer_agent.py::_compute_minimal_frame`) — the steward self-model + the universal standing-obligation pointer (D4); removes the capital-judgment residue. Its own commit + CHANGELOG + the `test_persona_frame_action_grammar_coherence` structural gate + a Hat-B behavioral dogfood eval. (Design: the scratch design doc, to be promoted to `docs/evaluations/` on implementation.)
2. **Freddie's kernel-default seeds** (D3 + D5) — `constitution/MANDATE.md` (steward-mandate) + `persona/principles.md` (stewardship rules) authored as kernel-default seeds, wired into the bare-workspace scaffold (`workspace_init`). **Amendment (2026-07-02): `governance/_autonomy.yaml` joins this set** — the fourth agent-universal governance file, seeded as `delegation: manual` (the steward delegation posture), via the YAML-comment marker form. See the amendment banner at the top. The bundle-fork overwrite path (ADR-226) is **already** the program-overwrite mechanism — no new overwrite logic, just the seeds. Its own artifacts + scaffold wiring.
3. **Doc cascade** — `agent-composition.md` (§3.2.1 + the §4 operator↔Reviewer symmetry table: MANDATE named agent-universal/every-agent's-purpose; the agent-universal vs operation-specific split named), `reviewer-seat-substrate.md` (the seat's file-structure IS the agent-universal shape; MANDATE is read alongside as the agent's purpose), `FOUNDATIONS` (Axiom 3 note if the "every agent has a purpose; the steward's is stewardship" generalization rises to an axiom touch — assessed at implementation; likely a Derived-Principle note), GLOSSARY (agent-universal vs operation-specific file classes; the steward-mandate), CLAUDE.md ADR index.

**Sequencing**: this ADR (concept) ratifies first. Then the frame re-carve (1) — the operator's immediate next step — which can read a populated steward-MANDATE (it no longer has to special-case absent MANDATE). Then the seeds (2). The doc cascade (3) accompanies whichever code commit lands the corresponding canon. **The gate is untouched, so there is no `test_adr320` change and no dispatch-gate risk** (the Model-B dividend).

---

## 8. What this ADR does NOT do

- Does not change the frame in the steward-seed commit (the persona-frame re-carve is §7 item 1, its own subsequent commit).
- **Does not change the ADR-320 D4 hard-gate *function*** — MANDATE is never empty under this ADR (§4), so the gate keeps passing. The steward-seed commit DOES add `is_skeleton_content` a steward-default marker (so a program-fork overwrites the steward defaults) — a recognition rule, not a gate-logic change.
- Does not build persona-agent seats (ADR-382 — this ADR gives them their file-structure, but lifecycle/trust is ADR-382's).
- Does not change the five semantic-class roots or the topological lock (ADR-320 §7 / DP25) — MANDATE stays in `constitution/`; this ADR re-frames its *content for the steward*, not its root or write-permission.
- Does not touch `governance/` as the operator-only ceiling (ADR-366) or single-writer-per-path (ADR-286).
- Does not decide Freddie's operator-facing naming (ADR-381 D1 — "Freddie, the system agent") or the harness split (ADR-381 D3) — those are settled; this ADR is the file-structure beneath them.
- Does not touch the re-founding keystone cascade (orthogonal track — though it is *consonant* with the keystone's "meaning, not namespace" instinct; the keystone may later subsume the universal-vs-operation-specific split into its metadata model. Flagged, not coupled.).

## 9. Rejected alternatives

- **Give Freddie its own bespoke governance file-structure.** Rejected (§2/D1) — Freddie is an agent; an agent's file-structure already exists; a bespoke structure would be a second representation of the same thing (Singular-Implementation violation) and would deny that Freddie and persona agents are the same kind.
- **Make MANDATE operation-conditional / empty-for-Freddie (the discarded first draft).** Rejected (§2, by the operator's challenge) — it special-cases the steward as *the agent without a why* (false: the steward's why is the most stable purpose in the workspace), is asymmetric with the default-principles.md decision (D5), and forces a gate re-derivation (empty-MANDATE-is-legal) that Model B avoids entirely. **MANDATE is reframed, not removed.**
- **Make the standing-obligation a kernel-hardcoded frame guarantee.** Rejected (D4) — it would re-import judgment-flavored content into the frame (the residue the re-carve removes) and monopolize in the kernel what each agent's MANDATE + principles.md should declare. The universal *pointer* in the frame + per-agent *content* in the files is the partition-clean answer (`agent-composition.md` §3.2.1).
- **Fully delete the standing-obligation pointer from the frame (per-program only).** Rejected (D4) — a program author who omits it would silently lose the DP30 behavior with no kernel signal. The universal pointer is the safety net; the content is the agent's own files.
