# ADR-603: The standing declaration — and the Supervisor's desk

**Status**: Ratified 2026-08-24; D1–D4 Implemented. **D5 measured and EXECUTED at the concept/surface layer 2026-08-24** (see D5 execution note below). **D4 is SUPERSEDED and D6's surface half discharged by [ADR-604](ADR-604-strings-is-supervisors-desk.md)** (2026-08-25): the dedicated supervisor app is deleted — Supervisor's desk IS strings, with Keeper as `standing_executor`; the kind-machinery generalisation in D6 remains gated on a second declaration kind.

**Builds on**: ADR-596 (a being; authority on grants/declarations/gates) · ADR-597 (the resident follows the registration) · ADR-601 (many-to-one; provenance) · ADR-602 (Editor takes the authoring desks). **Supersedes** ADR-569's framing of strings as an app-private mechanism (the mechanism survives; the framing generalises). **Sequences the retirement of** ADR-261/ADR-393's recurrence declaration.

## Context

Standing work — something happening without a member present — is currently expressed three ways, and the operator's own deliberation named the problem: *"i'm continuously confusing or deliberating just how to 'cut and display' concepts of work, maintaining files, scheduling."*

Audited at execution time rather than by name:

| | **recurrence** | **string** |
|---|---|---|
| declaration | `/workspace/_recurrences.yaml`, one flat list | `/workspace/{topic}/_string.yaml`, beside its subject |
| names | a **moment** | a **subject** |
| executor | the steward, implicitly | Keeper, via `resident_for_app("strings")` |
| output | whatever judgment produces | one designated leaf |
| *"did it work?"* | unanswerable | the CONTRACT answers it |
| no-op | does not exist | `NO_CHANGE` sentinel |
| path | `dispatch_recurrence` → `submit_wake_proposal` → the wake funnel | `drain_due_string_runs` → Keeper → `write_revision` |

**They share a clock and nothing else.** A recurrence is a scheduled interruption; a string is a maintained thing. The second is a first-class object in a substrate of record; the first is a cron entry that pages an LLM.

**A run is neither.** It is a receipt — `tasks.last_run_at/next_run_at` plus `execution_event` rows — that two unrelated clocks happen to share. It was never a concept, and it gets no home of its own here.

Placed against the current architecture (capability at the app, character at the agent, authority on declarations), **strings fits unmodified and a recurrence cannot be placed at all**: no app, no contract, no answerable outcome, and an executor that ADR-596 D3 is dissolving.

## D1 — The standing declaration

The kernel concept, promoted from strings' private mechanism to shared vocabulary:

> A **standing declaration** is a **subject** + a **contract** (what "true" means for it) + **sources** + a **schedule** + the **app** whose resident does the work — producing an attributed revision, or an honest no-op.

Every field is load-bearing, and the contract is what recurrences fundamentally lacked: **without it, "did this work?" has no answer**, which is why a recurrence could only ever be a prompt.

Storage follows the subject: a declaration lives **beside the thing it maintains** when that thing has a home (strings' `{topic}/_string.yaml`, ADR-569 D2), and the shape is unchanged. A subject with no natural home is a real case (a cadence that produces something new each run) and is **named, not solved** — it needs its second instance before its storage is designed, and generalising from one example is how the wrong axis gets abstracted.

## D2 — The declaration names the APP; the agent is derived

A declaration names `app`, never an agent. The resident follows the registration at read time — the ADR-597 D1 precedence, unchanged and reused rather than reinvented.

**This deliberately inverts ADR-596 D3's phrasing** (*"declarations name their executor"*), and the inversion is forced by ADR-601: `editor` now serves two desks, so a declaration naming the agent is ambiguous about which craft it wants, while one naming `slides` or `text` never is. Naming the app also means a re-pairing (ADR-602's `slides → editor`) re-points every declaration with no data move — the same dividend, collected twice.

`resolve_strings_resident()` already does exactly this. D2 is the rule it was an unnamed instance of.

## D3 — Supervisor: a desk whose material is declarations

A dedicated resident and app, together. The operator's two reasons, both accepted:

**Familiarity.** *"just knowing you have a personified agent you talk to dedicated for coordination and orchestration makes it easier to understand."* This is ADR-598's question restated — *"who am I talking to?"* — and it is the reason residents exist at all.

**Orchestration is continuously edited.** A declaration tweaked over months or years wants a conversation, not a form. That is precisely what a desk is for, and Supervisor's material is declarations exactly as Keeper's is a maintained file.

### ⚠️ Supervisor authors declarations; it never commands beings

**The distinction this ADR turns on, and the gate that holds it:**

- *"Supervisor hires Editor"* — authority over a **BEING**. Violates ADR-460 D3.a. Not built, not representable.
- *"Supervisor writes a declaration naming an app; the app's resident does the work"* — authority over a **DECLARATION**. This is ADR-596 D2's own sentence: *authority attaches to relations and declarations, never to beings.*

Supervisor holds **no field, and no primitive, that names another being.** It calls `Schedule` — already `CHAT_PRIMITIVES`, already available to any agent in a lane, gated by the primitive registry exactly as `WriteFile` is. Editor arrives at a declaration because the *app* derives it, never because Supervisor summoned it.

`AGENT_ROW_KEYS` is unchanged. The cliff is not weakened by one byte, and `test_agent_registry.py` asserts Supervisor's row against the identical whitelist as every other being.

### Supervisor is NOT Freddie, and Freddie still dissolves

Freddie carries standing intent, self-wake, a mandate, an autonomy dial, and an omniscient remit. **Supervisor carries none of it** — it acts when addressed, like every resident. Evolving Freddie would carry that apparatus forward and hope it stayed dormant; ADR-596 D3's dissolution proceeds unchanged.

Worth porting later, and named here so it is not lost: Freddie's **judgment log and calibration trail**. A Supervisor whose proposed cadence gets corrected should accumulate that — it is the ADR-596 D2 dossier, and it is the part of Freddie that was right. Not built here.

### The name

`supervisor`, displayed **Supervisor**. The operator offered "Supervisor or Work Manager or something fundamental" after the naming risk was raised: every other resident is named for a **craft** (Editor · Keeper · Designer) while a manager-word names a **role over others** — the exact reading D3.a forbids, taught by the name itself. Supervisor is the more fundamental noun and the shorter one in a composer, and its material (oversight of declared work) reads as a craft rather than a command relation. `work-manager` is **not** retained as an alias: slugs are data-compat and there is no data yet.

## D4 — The Supervisor app

`register_app("supervisor", resident="supervisor")`, `stage: internal` at birth.

The app is a **lens over declarations** — where a member reads what stands, what ran, and what changed. It has **no craft of its own**: each declaration's work is done by *its own app's* resident, so the ADR-601 orthogonality (capability at the app, character at the agent) holds exactly.

**`stage: internal` is not timidity, it is ADR-592's rule**: an app with a clock spends money unattended, and *an app with a clock is deleted, not staged*. Supervisor ships behind the roster until D5/D6 give it real declarations to show and the spend story is settled — and per ADR-602 D3 its resident is **withheld from the /agents pane** for exactly as long, with no second edit.

## D5 — Recurrences are RETIRED, not absorbed (direction; measurement-gated)

Every writer of `_recurrences.yaml` is `services/programs.py` (bundle fork) or `services/operator_proxy/scenarios.py` (the Hat-B harness). **There is no member-facing path that creates a recurrence**, and `/recurrence` is already `search-only`.

So this is not a live feature to migrate. Absorbing it would carry the steward's plumbing into the architecture built to replace it; the two merits worth keeping — *work happens without a member present*, and *a schedule is a declaration, and declarations are substrate* — are **already re-implemented, better, by strings**.

**Gated on a live count** (`tasks WHERE kind='recurrence'` vs `kind='string'`), which the dev environment cannot take (no `SUPABASE_DB_URL`). Retiring a mechanism whose live population is unmeasured is exactly the guess this repo's discipline forbids. The direction is ratified; the deletion is a separate commit with the count in its message.

### D5 execution note (2026-08-24)

**Measured against production** (PostgREST, service key): `tasks` holds **0
`kind='recurrence'` rows and 0 `kind='string'` rows** (3 inert `kind='radar'`
rows remain — ADR-592's owed sweep); the substrate holds exactly **one
`_recurrences.yaml`, content `[]`**, untouched since 2026-07-10, and zero
`_string.yaml` files. **Retire-clean: there is nothing to migrate.**

Executed in this pass — the recurrence CONCEPT and every member-facing
surface:

- FE: the `/recurrence` window (Schedule + Runs lenses), the notifications
  "Schedule" pane, the bell's "Coming up" limb, the chat rail's
  "from recurrence" chip and "Run this on a schedule" affordance, the
  `recurrences`/`narrative` API-client namespaces, and the whole WorkDetail
  chrome layer (its only tenant). `/recurrence`, `/activity`, `/backend`,
  `/cadence`, `/overview` are redirect stubs into `/notifications`,
  hand-listed in middleware (the ADR-592 obligation).
- API: `routes/recurrences.py` + `routes/narrative.py` deleted; the
  `recurrence` + `activity` kernel-surface rows deleted. Run receipts'
  surviving home is the notifications Activity ledger (`invocation` kind
  over `execution_events`) — this ADR's own sentence.

**Deliberately NOT deleted here** (assigned, not forgotten): the steward-side
plumbing — `services/recurrence.py`, the scheduler's recurrence dispatch,
`wake_sources/cron_tick.py`/`manual_fire.py`, the `Schedule` +
`FireInvocation` primitives, and the bundle-fork seeding in
`services/programs.py` + the two alpha bundles' `_recurrences.yaml`. That
stack is the steward's cadence authority (ADR-296), and its deletion is
**ADR-596 D3 phase (a)** work — it dies with the steward's machinery
reclassification, each phase its own ADR. With zero declarations, one empty
file, and no serving surface, it can fire nothing meanwhile.

## D6 — Strings dissolves UPWARD (direction)

Strings the *concept* becomes one instance of the standing declaration; strings the *mechanism* is what generalises. `_string.yaml` stays where it is (the subject-has-a-home case), `STRING_KIND` becomes one declaration kind among several, and the Supervisor app reads across all kinds rather than strings owning a surface.

Sequenced after D5 and after Supervisor has a second declaration kind to prove the generalisation against — **a shape inferred from one instance is a hypothesis**, and building the general mechanism before the second instance risks abstracting the wrong axis.

## Consequences

- One vocabulary for standing work, replacing three, without a new mechanism: the declaration shape is strings', the derivation is ADR-597's, the primitive is `Schedule`.
- A member gets a named colleague for coordination — the familiarity argument — with no being holding authority over another.
- Runs stop being a concept: receipts surface in notifications (*what happened*) and on the agent page (*what this agent tends*).
- **Named, not answered**: the homeless-subject declaration (D1), Freddie's dossier port (D3), and the live counts blocking D5.
- Gates: `test_agent_registry.py` extended (Supervisor's row against the same whitelist; **no primitive or field names another being**); `test_adr603_standing_declaration.py` (the concept's rule: a declaration names an app, and the resident derives). Every check falsified.
