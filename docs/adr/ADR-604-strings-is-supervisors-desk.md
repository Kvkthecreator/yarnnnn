# ADR-604: Strings is Supervisor's desk — the voice/executor split

**Status**: Ratified 2026-08-25 · **D2's executor BEING and D4's two-face pane superseded by [ADR-610](ADR-610-the-keeper-dissolves-into-the-supervisor.md) (2026-08-26)** — the voice/executor *seam* this ADR identified is correct and survives; the second being that filled it is dissolved (maintenance is the steward's seat and daemon work, never a being) (operator thesis, tested and aligned in discourse: *"couldn't we actually just make strings the dedicated app for supervisor … and thus actually push down the designation of tasks, runs to the keeper"*). Implemented same day.

**Builds on**: ADR-596 (beings; authority on grants/declarations/gates) · ADR-597 (resident derived at read time) · ADR-601 (capability at the app; many-to-one) · ADR-603 (the standing declaration; Supervisor). **Supersedes** ADR-603 D4 (the dedicated `supervisor` app — deleted here) and **amends** ADR-603 D3/D6 (the desk arrives now; the kind-machinery generalisation stays gated).

## Context

ADR-603 gave Supervisor its own app, `stage: internal`, waiting for a second declaration kind. Discourse re-tested that sequencing from first principles and found the honest blocker was never the second-instance rule (that rule binds *machinery abstraction*, not surfaces): it was that **with exactly one declaration kind, a Supervisor lens duplicates the Strings surface** — the ADR-562 second-home drift, two windows answering one question.

The operator's thesis dissolves the duplication at the root: there should be **one surface**, and it should be Supervisor's. Strings the mechanism survives untouched; strings the *desk* changes whose conversation it hosts.

Two measured facts make this the right moment:

- **Zero live string declarations in production** (counted 2026-08-24). Every binding this ADR moves is a free re-point today and a migration the day the first declaration lands.
- **Strings runs were never Keeper's authored acts.** The standing writer attributes `system:strings` while *wearing* Keeper's model + posture — the ADR-596 D1 machinery-in-costume form. Keeper is the runs' **face**, not their author. "Push runs down to Keeper" is therefore mostly a matter of declaring what is already true.

## D1 — Strings is Supervisor's desk

`register_app("strings", resident="supervisor", standing_executor="keeper")`.

The desk voice — the bound lane, the composer, the tab — is **Supervisor**: the strings pane's conversation is *about standing work* (what runs, on what cadence, to keep what true), which is Supervisor's material by ADR-603 D3. Per ADR-597 D1 the re-registration re-points every strings lane at serve and at turn in the same commit, with no data move — the derivation dividend, collected a third time.

The **job overlay is untouched**: the strings desk posture (the app layer, ~87% of the frame per ADR-601's measurement) is selected by `app == "strings"` exactly as before. Supervisor at this desk knows the declaration grammar because the *desk* teaches it — capability at the app, character at the being.

Slug and title stay `strings` / "Strings": slugs are data-compat addresses, and renaming the member-facing title is a display dial the operator can turn later without an ADR. Named open, deliberately.

## D2 — `standing_executor`: a desk has a voice; its standing work has an executor

The `resident` field was answering two questions with one value: *who speaks at the desk* and *who executes the desk's unattended runs*. They coincide for every other app and must diverge here — Supervisor authors and tends declarations; **it never does the work** (ADR-603 D3, unchanged).

`register_app` gains an optional **`standing_executor`** — the being whose model + posture the app's standing runs resolve, and whose face the run receipts wear. Undeclared → the resident executes (every other app is unchanged by construction). Today exactly one app declares it: strings → `keeper`.

- `resolve_strings_resident()` derives the **executor** (it powers the run, not the conversation).
- `resident_for_declaration()` derives the **executor** — ADR-603 D2's own words were "the being that will do this declaration's work," and that is the executor. The rule "a declaration names the APP, never an agent" is untouched; only the derivation behind it deepens by one field.
- Run attribution stays `system:strings` wearing the executor's costume — the ADR-596 D1 form, unchanged.

The cliff is untouched: `standing_executor` lives on the **app registration** (kernel code), never on a being's row, and it is capability-routing, not authority — the clock's spend stays gated by the budget machinery exactly as before (ADR-596 D2).

## D3 — The dedicated `supervisor` app is DELETED

Registration and internal surface row both. Supervisor's desk is strings; a second app whose lens shows the same declarations is the second-home drift this ADR exists to prevent. ADR-603 D4 is superseded — its `stage: internal` caution was correct *for a duplicate surface*, and the surface is no longer a duplicate. No route or middleware obligation existed (the row never had a route), so nothing to discharge.

## D4 — The pane shows who a member meets, voice or executor

`homes_for_agent` now includes desks a being serves as **standing executor**, so `/agents` shows both halves of the desk honestly:

- **Supervisor — in strings** (the voice; becomes visible because strings is `primary`, resolving the operator's "why is it not on /agents" by the front door rather than a stage flip).
- **Keeper — in strings** (the executor; a member meets Keeper's face on every run receipt, and a pane that hid it would be asserting Keeper stopped existing).

Promotion stays fully derived (ADR-602 D3 as amended): no new column, no second edit when anything moves.

## D5 — What does NOT change, said out loud

- **The kind machinery.** One kind, one parser (`parse_string_yaml`), one drain (`drain_due_string_runs`), `_string.yaml` beside its subject. The general declaration engine still waits for the **second kind** — ADR-603 D6's sequencing survives for machinery; only its *surface* half is discharged early, by this ADR, while the rename window is free.
- **The D2 rule.** Declarations name apps. No key anywhere names a being.
- **Editor and Designer's reach.** Cross-craft coordination arrives through declarations naming *their* apps (`text` → editor, `images` → designer) — the existing derivation, no new mechanism, no being commanding a being.

## Consequences

- One surface for standing work with two legible roles a human already understands: the coordinator you talk to, and the named face on who did each run.
- Supervisor and Keeper both appear on `/agents`, derived, with strings' promotion — no stage flip, no second edit.
- Strings surface copy shifts one pronoun: declaration *repair and set-up* is asked of **Supervisor** (the conversation); *keeping* remains Keeper's (the receipts).
- Gates: `test_agent_registry.py` (executor homes; both beings promoted), `test_adr603_standing_declaration.py` (executor-first derivation; the ratified pairing map recut), `test_adr597_resident_derivation.py` (strings lanes derive supervisor), `test_adr569_strings.py` (the run executor stays keeper). Every new check falsified.
