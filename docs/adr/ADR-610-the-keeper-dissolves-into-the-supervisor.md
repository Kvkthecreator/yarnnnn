# ADR-610: Keeper dissolves into Supervisor — maintenance is a seat and a daemon, never a being

**Status**: Ratified 2026-08-26 (operator thesis, tested in discourse and aligned in full). Implemented same day.

**Builds on**: ADR-596 (a being is identity ⊕ character ⊕ engine; authority/clock/judgment live on grants, declarations and gates — never on the being) · ADR-600 (one register; hireability is a field) · ADR-601 (capability lives at the APP) · ADR-603 (the standing declaration; Supervisor authors declarations, never commands beings).

**Supersedes** ADR-604 D2's *executor being* and ADR-604 D4's two-face pane; **amends** ADR-569's naming (the app's runs are no longer "Keeper's"). The `standing_executor` **mechanism survives untouched** — see D2.

## Context

ADR-604 correctly diagnosed that `resident` was answering two questions with one value: *who speaks at a desk* and *who executes its unattended runs*. It fixed that with a new field, `standing_executor`, and filled the new slot with a second being: Keeper.

The field was right. The second being does not follow from it.

The operator re-opened the question at the conceptual altitude — *what should Keeper's role actually be?* — with the thesis that Keeper's remit was **time-based maintenance, folder and file health, substrate management**. Testing that thesis against the substrate is what settles this ADR, and it settles it against Keeper twice over.

### The role the thesis describes EXISTS — and it is already assigned

Substrate health is not an unclaimed job. It is written down, in four-field rule shape, in `DEFAULT_STEWARD_PRINCIPLES_MD` (`services/orchestration.py`) — and it belongs to the **steward**:

- `intake-placement` — an observation landed raw; place it in its meaning-home, citing its source.
- `attribution-integrity` — a revision with missing or wrong `authored_by`; fix where the steward authored it, flag where another principal did.
- `commons-coherence` — two principals' revisions to one meaning-path that genuinely contradict; reconcile as system manager.

That *is* "folder and file health," with pass conditions and verdicts. It is **judgment about the commons**, which is why it needs a mandate, an autonomy dial, and a calibration trail — the apparatus of a SEAT (ADR-315), not the contents of a character row.

### The mechanical half is daemon work, correctly characterless

The rest of maintenance is already running and already has no face: `wake_queue.reclaim_stale_locks`, `connector_retention`, `_cap_history`, the wake drain, outcome-reconciliation. Per the OS framing (ADR-222), daemons are **kernel**. A being is something a member *meets*. Putting a face on work nobody watches yields a persona whose entire existence is a label on a cron job.

So the maintenance concept splits cleanly, and **neither half wants a being**: the judgment half is the steward's seat, the mechanical half is a daemon.

### Keeper as BUILT was never that role

ADR-604 says so in its own words: Keeper *"is the runs' face, not their author,"* and pushing runs down to it is *"mostly a matter of declaring what is already true."* What the `keeper` row actually holds is a `model` and a `posture` consumed by one call — `run_bounded_derive_turn` — for one app's unattended write, under a fixed output contract (return the file's markdown, or `NO_CHANGE`). No tools, no conversation, no judgment about what to do next. Attribution stays `system:strings`; the character is a costume (ADR-596 D1).

**The name promises the operator's concept; the row delivers one app's executor slot.** That gap is the defect. It is the kind that worsens with tenure, because the name keeps recruiting responsibilities the row was never built to hold — the same class as a property modelled as its container's identity (ADR-600 Context).

### Keeper's character was mostly a job overlay in the character slot

Read the posture against the run frame it composes with. Keeper's six lines are either **already stated in `_KEEPER_RUN_POSTURE`** ("never invent facts, numbers, or sources" appears verbatim in both) or are **rules of judgment** — which `agent-composition.md` §3.2.1 places in the contract or the job layer, explicitly NOT in a persona frame. Only two lines were doing non-duplicative work, and both are job instruction: *preserve the member's corrections*, and *when a source and the contract disagree, say so plainly*.

### The split manufactured the discontinuity it meant to prevent

ADR-604 D4 kept Keeper on `/agents` reasoning that "a member meets the executor's face on every run receipt." But the member declares a contract in conversation with **Supervisor**, and then receives a receipt signed by **someone they have never spoken to**. One desk, one contract, two names. Supervisor's remit — *"standing work: the things that should keep happening without them having to ask again"* — is already the member-facing half of the operator's thesis, at the right altitude, with the contract as its load-bearing part. Keeper does not extend it; it sits underneath doing the write and gives that write a second name.

## Decision

### D1 — The `keeper` being is DELETED

Its row leaves `agents_registry.AGENTS`. There is no successor being: the maintenance role it was named for belongs to the steward's seat (judgment) and to daemons (mechanics), and putting it on a being's row would be authority on a being — the ADR-460 D3.a cliff, which ADR-596 D1 restated and this ADR does not reopen.

The strings desk has **one colleague, Supervisor**: the being a member declares contracts with, and the face on the receipts for those contracts. One desk, one contract, one name.

### D2 — `standing_executor` SURVIVES, pointing at the resident

ADR-604 D2's diagnosis stands: a desk's conversation and its unattended runs are different contexts, and collapsing them into `resident` was answering two questions with one value. **The seam is real and stays.**

What changes is only its value: `register_app("strings", resident="supervisor")` — with `standing_executor` undeclared, so it derives the resident, exactly as every other app already does. `standing_executor_for_app()` and `resolve_strings_resident()` keep their signatures and their fail-closed behaviour (no plausible default; an unregistered executor raises — the ADR-548 lesson).

Deleting the field instead would be the mistake symmetric to ADR-604's: **a mechanism is not wrong because its first filling was**. Keeping it inert-but-honest costs one field and preserves the ability to diverge a desk's voice from its executor the day a desk genuinely needs it.

### D3 — Keeper's two live lines move to the job layer

`_KEEPER_RUN_POSTURE` gains what was non-duplicative in the character: preserve the member's own corrections (they compound), and name a source/contract disagreement plainly rather than papering over it. These are **job instruction for a standing run**, not identity — §3.2.1's partition, applied.

The posture constant and its builder are **renamed off the deleted being** (`_STANDING_RUN_POSTURE` / `build_standing_run_posture`). A symbol named for a being that no longer exists is precisely the future ambiguity this ADR exists to remove.

### D4 — The receipt and the surface say Supervisor

- Run receipt: `"Supervisor kept 'x.md' current (standing pull, N sources)"`. `authored_by` stays `system:strings` — ADR-460 D2 unchanged: the face is a display concern, the fact is the ledger.
- The strings attribution label (`StringsSurface.tsx`) reads `Supervisor` for `system:strings`.
- Surface summary, Files door, landing copy: one colleague at this desk, named once.

### D5 — `/agents` shows one being per desk again

`homes_for_agent` still counts a desk served as voice OR standing executor (ADR-604 D4's mechanism is correct and untouched) — it simply resolves to one being for strings now, because one being holds both roles. No new column; promotion stays derived (ADR-602 D3).

## Consequences

- **"Agent" keeps exactly one meaning, and so does each desk.** A member who asks "who keeps this file?" gets one answer, and it is the same one they declared the contract with.
- The maintenance concept is not lost — it is **located**: judgment on the steward's seat (`attribution-integrity`, `commons-coherence`, `intake-placement`), mechanics in daemons. Both already exist and neither needed a being.
- ADR-604 D6's kind-machinery generalisation remains gated on a **second declaration kind**, unaffected: that gate never depended on Keeper.
- Landing copy loses "a keeper for the files you want kept current." Supervisor's version is a stronger claim, because "kept current" is a *contract* claim and the contract is Supervisor's material.
- Historical ADRs (569, 597–604) keep their Keeper prose. **A ratified ADR is a record of what was decided, not a live claim** — rewriting them would falsify the trail. This ADR is the pointer that supersedes them.

**The rule this ADR leaves behind**: a being is someone a member MEETS. Work nobody watches is a daemon; judgment about the commons is a seat. Neither earns a character row, and naming one after a role it does not hold is how the ambiguity starts.
