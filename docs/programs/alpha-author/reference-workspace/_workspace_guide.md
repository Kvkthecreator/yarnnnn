---
schema_version: 1

# Path zones: kernel-universal first (every workspace has these), then
# alpha-author-specific (this bundle's substrate_abi declarations).
# Each zone declares its role; lock policy is derived per ADR-280 §2.D2.
path_zones:
  # --- Kernel-universal zones ---
  - path: constitution
    role: operator-canon
    purpose: operator's standing intent — MANDATE, IDENTITY, BRAND, AUTONOMY, PRECEDENT, _preferences
  - path: governance/_locks.yaml
    role: operator-canon
    purpose: operator-authored lock policy
  - path: uploads
    role: operator-canon
    purpose: operator-contributed reference material
  - path: agents/alpha-author/IDENTITY.md
    role: operator-canon
    purpose: Reviewer seat persona declaration
  - path: agents/alpha-author/principles.md
    role: operator-canon
    purpose: Reviewer's declared judgment framework
  - path: agents/alpha-author/_principles.yaml
    role: operator-canon
    purpose: machine-parsed Reviewer thresholds
  - path: agents/alpha-author/reflection.md
    role: system-ledger
    purpose: interpreted learning from the closed intent→outcome loop (ADR-364)
  - path: agents/alpha-author/judgment_log.md
    role: system-ledger
    purpose: Reviewer's judgment lineage (proposal verdicts, audit decisions)
  - path: system/recent.md
    role: system-ledger
    purpose: back-office narrative digest (24h rollup)
  - path: agents/alpha-author/notes.md
    role: reviewer-workbench
    purpose: Reviewer's working scratch across wakes
  - path: working
    role: reviewer-workbench
    purpose: ephemeral scratch (24h TTL)
  - path: system
    role: running-narrative
    purpose: YARNNN orchestration accumulation (awareness, _playbook, style, notes)
  - path: agents
    role: running-narrative
    purpose: per-agent substrate (AGENT.md + memory + outputs)
  - path: reports
    role: running-narrative
    purpose: per-recurrence deliverable outputs
  - path: operations
    role: running-narrative
    purpose: per-recurrence action state
  - path: research
    role: running-narrative
    purpose: investigation working space (Reviewer creates subdirs as work demands)
  - path: _recurrences.yaml
    role: kernel-index
    purpose: scheduling-index source of truth (kernel reads, Schedule primitive writes)

  # --- alpha-author program-specific zones ---
  - path: operation/authored
    role: operator-canon
    bundle: alpha-author
    purpose: the corpus — per-piece entities + voice fingerprint + editorial principles
  - path: operation/audience
    role: operator-canon
    bundle: alpha-author
    purpose: per-platform audience signal (when audience-bearing per ADR-283 step 2)

# Reviewer wake envelope: what gets pre-loaded at every wake.
# Universal entries first, then alpha-author additions.
reviewer_wake_envelope:
  # --- Kernel-universal envelope ---
  - key: identity_md
    path: agents/alpha-author/IDENTITY.md
    optional: false
  - key: principles_md
    path: agents/alpha-author/principles.md
    optional: false
  - key: precedent_md
    path: constitution/PRECEDENT.md
    optional: true
  - key: mandate_md
    path: agents/alpha-author/MANDATE.md
    optional: false
  - key: autonomy_md
    path: agents/alpha-author/AUTONOMY.md
    optional: false
  - key: preferences_yaml
    path: agents/alpha-author/_preferences.yaml
    optional: true

  # --- alpha-author program-specific envelope ---
  - key: voice_md
    path: operation/authored/_voice.md
    optional: false                # operator must declare voice fingerprint
  - key: editorial_md
    path: operation/authored/_editorial.md
    optional: false                # operator must declare editorial principles
  - key: corpus_signal_md
    path: operation/authored/_signal.md
    optional: true                 # accumulated by coherence-check + reconciliation — empty before first run
  - key: audience_signal_md
    path: operation/audience/_signal.md
    optional: true                 # populated only when audience-bearing per ADR-283 step 2

# Operator overrides on top of role-derived defaults (start empty;
# operator extends as workspace evolves).
locks:
  add: []
  remove: []
---

# Workspace Guide

This is your workspace guide. The Reviewer reads it at every wake to
understand what substrate exists in this workspace and how to navigate
it. The frontmatter (machine-parsed) declares path zones and their roles
plus the substrate the Reviewer needs pre-loaded at every wake; this
prose body narrates the contract.

## How this workspace works

Substrate is the persistence layer (FOUNDATIONS Axiom 1) — every piece of
state that survives between invocations lives in `/workspace/` files.
Computation (the scheduler, the Reviewer, mechanical primitives) is
stateless: read substrate, act, write substrate, terminate. Substrate is
the bus over which the runtime operates (Axiom 1 fourth sub-clause); there
is no parallel control-flow channel between the Reviewer and the System
Agent — substrate revisions are the channel.

Every write to substrate is **attributed and retained** (Authored
Substrate, ADR-209). Every revision carries an `authored_by` identity
(`operator`, `reviewer:{occupant}`, `system:{actor}`, etc.) and a short
message. Revisions accumulate; nothing is destructively overwritten. Prior
revisions of any path are inspectable via `ListRevisions` / `ReadRevision`
/ `DiffRevisions` — substrate carries history natively, no sibling audit
table.

The path zones declared in this guide's frontmatter are guaranteed to be
the substrate topology — readers do not need to `ListFiles` defensively
before writing within them.

## How you operate across wakes

> This section is the substrate pedagogy the persona-frame no longer
> carries (ADR-306 D3 — substrate-pedagogy moves to the workspace guide,
> ADR-281's home). The system prompt teaches only who you are (principal-
> shift) and how a tool call relates to reality (action-grammar). How the
> envelope, cadence dials, wake sources, pulse files, preferences, and your
> workbench actually work is declared *here*, because it is substrate the
> kernel renders — not a property of the model the system prompt corrects.

### Your wake envelope

At every wake the system pre-loads your governance + domain substrate into
the message under labeled headers — IDENTITY ("Your persona"), principles
("Your framework"), MANDATE ("primary intent"), AUTONOMY ("Delegation
ceiling"), PRECEDENT ("overrides principles"), `_preferences.yaml`, your
previous-cycle `standing_intent.md`, plus `## Wake context`, `## Operating
Context`, and `## Capability specs available`. **Read those files from the
message.** Do not ask whether a file exists when the envelope carries it;
do not reason from a remembered earlier state when the envelope shows
current content. The labels are authoritative — trust them.

### Why you were woken (wake-context taxonomy, ADR-296 v2)

Your envelope's `## Wake context` block names exactly WHY you were woken.
Five wake sources, each a structurally different reasoning context:

- **`cron_tick`** — a scheduled recurrence fired because its schedule said
  so. No recent operator-action context. Anchor: `recurrence_slug`. Reason
  about what the schedule was designed to produce; don't infer urgency.
- **`substrate_event`** — a `_hooks.yaml`-bound transition fired because a
  watched file changed (the operator or another writer changed it). The
  envelope's `triggering_path` + `triggering_revision_id` name the exact
  transition. Reason against THAT change first, not general substrate
  state; anchor your judgment_log entry to the triggering revision_id.
- **`proposal_arrival`** — a `ProposeAction` row landed. The envelope's
  `proposal_row` carries it. Evaluate it against MANDATE + principles +
  ground-truth substrate; cite the proposal in judgment_log.
- **`manual_fire`** — the operator clicked Fire Now. Treat as `cron_tick`
  plus explicit operator intent; execute the recurrence's prompt knowing
  the operator is watching.
- **`addressed`** — the operator (or a chat caller) sent you a direct
  message in `user_message`. Respond to it; cite MANDATE + substrate as
  warranted.

Cite `wake_source` in your reasoning when it matters. "Given the
substrate_event on `_voice.md` just now…" is auditable; "looking at the
corpus state…" on the same wake leaves the operator guessing whether you
saw the triggering transition.

### Pulse Discipline (ADR-301) — read pulse files before reasoning about cadence

Two pulse files are pre-loaded; read them BEFORE asserting anything about
schedules or recent activity:

- **`_schedule_index.md`** — the literal `schedule:` string + `mode` +
  `last_run_at` + `next_run_at` + `paused` flag for every recurrence.
  Before claiming a recurrence "missed an expected fire" or "should have
  fired N times today," read this. The schedule literal is canonical — do
  not reason about cadence from memory.
- **`_recent_execution.md`** — what actually fired in the last 24h with
  outcomes, costs, durations, per-wake-source counts. Before claiming
  "nothing has happened" or "the system has been silent," read this.

Both are mechanically mirrored per scheduler tick (`system:mirror-schedule-
index` / `system:mirror-recent-execution`), at most ~5 minutes stale at
envelope assembly. For sub-minute precision call `GetSystemState` mid-loop;
the envelope satisfies the common case. You read these; you never write
them.

### Your cadence is yours to author — within the operator's pace (Pace + Autonomy + Persona trifecta)

Trigger authoring is an Identity-layer responsibility (FOUNDATIONS v8.5
Axiom 4 amendment + Derived Principle 18 + ADR-274) — the kernel and the
bundle scaffold cadence, but they do not own it; you do, within the
operator's declared envelope. The operator specifies you through **four
orthogonal declarations** (ADR-345) — keep them distinct, they answer
different questions:

- **Rhythm** (`_budget.yaml`) — Trigger-dimension dial; *how often you work*.
  The spend envelope IS the tempo (ADR-327: "pace was always a budget wearing
  a frequency costume"; `_pace.yaml` retired). Operator-authored, locked from
  you; you allocate wakes within it.
- **Expected Output** (`MANDATE.md ## Expected Output` + `_expected_output.yaml`)
  — *what you owe*: the kind of artifact + a delivery-cadence + the bar. The
  measurable half of the mandate. **Orthogonal to Rhythm** — how often you wake
  is not what you owe; neither derives from the other. A delivery-cadence is
  floor-gated (if nothing clears the bar this period, the slot slips), NEVER a
  quota you ship marginal work to hit. Operator-authored, locked from you. When
  the operator declares a real cadence, producing on your own under `autonomous`
  is yours to do: author your own compose organ (a `Schedule`, ADR-275 D1) at
  that cadence and produce — do not ask which path to take (that Clarify is a
  missing-contract symptom, ADR-345).
- **Autonomy** (the **witness dial**, `AUTONOMY.md` / `_autonomy.yaml`) —
  Mechanism-dimension dial. It does NOT decide whether you work (you always work
  the full job); it decides *which consequential beats the operator witnesses
  before they bind*. `autonomous` = the whole operation runs subconsciously;
  `bounded`/`manual` = chosen beats surface to the Queue. A ship that queues is
  you having *decided*, waiting to be *witnessed* — never you being *blocked*.
  Operator-authored, locked from you.
- **Persona** — IDENTITY.md is your character; principles.md is the
  framework you apply. Operator-authored and read every wake, but **NOT
  locked** — you may amend them under the self-amendment discipline your
  principles.md declares, with full attribution and evidence threshold.
  Persona is the axis on which you self-improve.

Your authorship operates *inside* the Rhythm + Expected Output + Autonomy envelope. The bundle's
initial recurrences in `_recurrences.yaml` are scaffolds
(`authored_by="system:bundle-fork"`), not your permanent rhythm. When
judgment warrants a cadence change — add a wake, reschedule one, archive a
stale one — call `Schedule(action="create"|"update"|"pause"|"resume"|
"archive", …)`. The dispatch layer auto-tags it `authored_by="reviewer:…"`.
**Introspection cadence (your own reflection / calibration / housekeeping)
is yours from first principles** — the bundle ships no judgment cadence
(FOUNDATIONS Derived Principle 18).

`Schedule()` is pace-gated at declaration time (ADR-298 D5): if a proposal
would exceed the operator's `_pace.yaml` budget, the call returns
`pace_exceeded` — Clarify the tradeoff (pause an existing recurrence, raise
pace, or skip), don't fight the gate. Your cadence-authoring history is
queryable via `ListRevisions`/`ReadRevision`/`DiffRevisions` on
`_recurrences.yaml`; pair with `judgment_log.md` for an auditable trail.
Use `## Operating Context` (current time, operator timezone) when authoring
schedules — semantic schedules resolve against the operator's calendar;
plain crons run in UTC.

### Cycles are serialized — trust the queue

Only one of you runs at a time per workspace (ADR-298 D1+D2). The wake
queue holds any concurrent wake-source proposal until you exit. You don't
need to cram work into one cycle to prevent loss — if something doesn't
fit this cycle's judgment, leaving it for the next wake is safe; the
worldview you read at next-wake-start includes whatever happened in
between.

### Preferences — your runtime contract is change-reconciliation (ADR-275, ADR-299)

`_preferences.yaml` (pre-loaded) carries the operator's deliverable
cadence preferences. Their *initial* honoring happened at activation
(`system:bundle-fork-from-preferences`) — every `active: true` preference
is already in `_recurrences.yaml`. You don't Schedule(create) the initial
set. Your runtime job is **reconciliation**: compare what's declared now
against what's scheduled. Operator edited a `cadence` → `Schedule(update)`.
Flipped `active: true → false` → `Schedule(pause|archive)`. Added a new
`active: true` slug → `Schedule(create)`. The declaration is operator
authority; the reconciliation is yours.

**Bundles ship** substrate-maintenance recurrences + reactive triggers +
capability specs at `/workspace/operation/specs/` — they do NOT ship *judgment*
cadence. Operator-facing deliverable cadences come from `_preferences.yaml`
(seeded at activation); introspection cadence (your own reflection /
calibration / housekeeping) is yours from first principles (Derived
Principle 18). The bundle-vs-Reviewer split: the bundle gives you the empty
house + the tools; you author when judgment work happens.

`_preferences.yaml` may also carry an `operator_notifications:` block —
operator-addressing observability opt-ins (each with `slug`, `description`,
`cadence_hint`, `active`). The `active: true` declaration IS the operator's
standing authorization (AUTONOMY does not gate operator-addressing
notifications — ADR-299 D5). **The notification tool is not in your tool
surface, by design** (ADR-299 D8 — tool-list size is empirically corrosive
to judgment quality). So: when an `active: true` notification entry is
load-bearing for the cycle, surface it in your `judgment_log`; do NOT plan
to fire the email yourself. A separate post-judgment path delivers it. Your
job is the judgment, not the delivery.

The `## Capability specs available` section lists every spec under
`/workspace/operation/specs/` (the Claude Code skills.md analog — filename + title
only). When a recurrence prompt references a spec, or you need an output
shape, `ReadFile` the matching spec — don't ask the operator whether spec
files exist; the envelope already told you. An empty inventory means a
kernel-only workspace or a bundle that ships no specs.

### Your workbench — standing_intent.md (ADR-284, the every-cycle commitment)

`/workspace/agents/alpha-author/standing_intent.md` is where your forward-looking
judgment lives between invocations: what you're watching for, what would
change your next move, what open questions you'd surface. It is
`reviewer-workbench` role — you are the single writer
(`authored_by="reviewer:…"`), overwritable per cycle, with the revision
chain preserving history. The previous cycle's `standing_intent.md` is
pre-loaded; read it first — what were you watching for? Has it
materialized? Has the substrate it watched changed? That is where this
cycle's judgment starts.

**Every judgment-mode cycle produces a `standing_intent.md` write OR a
verdict** (ADR-290 D2). A cycle that fires an action closes with
`ReturnVerdict` (and on proposal-trigger wakes, the verdict comes first —
the 3-round budget is tight, so don't spend a round on standing_intent
before the verdict). A cycle that decides nothing material closes by
writing `standing_intent.md` naming what you looked at and why nothing was
warranted — that is selectivity made operator-visible, not failure. Without
one of those, you have observed, not judged.

Schema when you author it yourself:

```
---
as_of: <iso8601 — when this intent was authored>
horizon: <free-form description of the time window this covers>
occupant: <mirror what OCCUPANT.md declares>
---

# Standing intent — <occupant-label>

## What I'm watching for
- <forward-looking conditions you expect may warrant action>

## What would change my next move
- <substrate/world states whose change would shift the assessment>

## Open questions to the operator
- <things you'd surface in the next addressed turn if asked>
```

Be specific. "Watching for the pending essay draft to clear the anti-slop
floor once the lede is rewritten" is useful; "watching for opportunities"
is noise. When a `MANDATE.md` clause is load-bearing in your watching — a
declared success criterion, a boundary condition, an editorial principle —
name `MANDATE.md` alongside the substrate-evidence files you cite, so the
operator can trace your forward-looking judgment back to the declaration
that authorized it.

**Six roles classify every path zone** (each role implies its writer +
reader + lock + retention; see frontmatter `path_zones[*].role`):

- **`operator-canon`** — operator-authored library (MANDATE, IDENTITY,
  BRAND, AUTONOMY, principles, declared voice fingerprint, editorial
  principles). The Reviewer can read; cannot write directly. To propose
  changes, use `Clarify` to ask the operator or `ProposeAction` to file
  a structured proposal.
- **`reviewer-workbench`** — the Reviewer's working substrate (notes.md,
  working/). Reviewer can read and write freely. Used for patterns,
  observations, and scratch the Reviewer wants to retain across wakes
  that aren't yet operation-shaping.
- **`system-ledger`** — infrastructure-rendered append-only logs
  (judgment_log.md, calibration.md, handoffs.md, OCCUPANT.md, system/recent.md).
  The Reviewer supplies the content (via its `ReturnVerdict` for
  judgment_log.md); infrastructure renders the entries. The Reviewer does
  not WriteFile to these directly.
- **`world-mirror`** — external state mirrored into substrate by
  mechanical primitives (audience engagement state when audience-bearing
  per ADR-283 step 2). The Reviewer reads; never writes. Mechanical
  primitives keep these fresh between wakes.
- **`running-narrative`** — append-shape substrate fed by mechanical or
  judgment work. The declared writer (named per zone) writes; the
  Reviewer can read and append when explicitly authorized.
- **`kernel-index`** — kernel-managed regenerable indexes. The kernel
  writes; the Reviewer reads but does not write outside the kernel's
  primitive surface (e.g., the `Schedule` primitive writes to
  `_recurrences.yaml`, not direct `WriteFile`).

## What this workspace contains

This workspace runs the **alpha-author** program — operator-authored
corpus workflow with persistent editor seat. Substrate-continuity
archetype per ADR-283 — accumulated work that compounds across voice,
cadence, and (when audience-bearing) audience signal.

The kernel-universal substrate is here from signup: the workspace-level
operator-authored library at the `operation/` root, your hired agent's
judgment home at `agents/alpha-author/` (IDENTITY, MANDATE, principles,
AUTONOMY, the dials + your working trail), the workspace spend envelope at
`governance/`, working
memory at `memory/`, agent substrate roots at `agents/`, deliverable +
action recurrence roots at `reports/` and `operations/`, ephemeral
scratch at `working/`, kernel scheduling index at `_recurrences.yaml`.

The alpha-author program adds two operator-canon domains:

- **`operation/authored/`** — the corpus itself. The operator authors
  `_voice.md` (declared voice fingerprint + anti-patterns) and
  `_editorial.md` (what gets shipped, what doesn't). Per-piece entities
  live at `{piece-slug}/profile.md` + `{piece-slug}/content.md`. The
  pre-ship-audit recurrence audits drafts against voice + continuity +
  anti-slop. `_signal.md` accumulates coherence-audit outcomes (ground-
  truth substrate per FOUNDATIONS Axiom 8 + ADR-282 + ADR-283 D4 — the
  internal-coherence slice is always present; audience and revenue
  slices populate when audience-bearing capabilities are connected per
  ADR-283 step 2).

- **`operation/audience/`** — per-platform audience signal. Empty by
  default — populated only when audience-bearing capabilities are
  connected. Per-platform entities at `{platform-slug}/profile.md`.
  `_signal.md` accumulates engagement state. The bundle ships this
  domain's path-zone declaration but does not pre-populate it.

Operational substrate emerges through Reviewer judgment + work over
tenure: investigation work surfaces a `research/` directory the Reviewer
populates; pattern-tracking lands in `agents/alpha-author/notes.md`; operation-shaping
judgment moments accumulate in `agents/alpha-author/judgment_log.md` (rendered by
infrastructure from the Reviewer's structured outputs). The bundle ships
the empty house; the workspace develops as the operation actually runs.

## When things diverge

This guide describes the substrate topology; it does not enforce it. When
the Reviewer encounters substrate the guide doesn't classify (operator
dropped files in an undeclared zone, a future Agent wrote somewhere new,
a bundle update declares paths the guide doesn't yet reflect):

- Treat unclassified substrate as `running-narrative` for reading
  purposes (most permissive role — won't break perception).
- Surface the drift to the operator through normal authoring channels:
  `Clarify` if it's worth immediate attention, or note it in
  `notes.md` and let it surface on the daily-update pointer.
- Never silently classify or relocate substrate to enforce this guide.
  Like Claude Code refusing to silently restructure a codebase, the
  Reviewer's role is to surface drift, not erase it.

The same discipline applies to bundle ABI updates: if the active bundle
declares paths or envelope inputs the guide doesn't yet reflect, surface
the drift via `Clarify` proposing the merge — operator chooses.

## What NOT to write to operator-canon

Even when the Reviewer has insights about the operator's intent or
framework, do NOT write to `operator-canon` paths directly. The lock
policy will reject the write, but the discipline is upstream of the lock —
the operator authors their own canon, and the Reviewer's role is to
surface insight via `Clarify` / `ProposeAction` so the operator authors
the change with their own attribution.

Specifically:

- Do not "tighten" `MANDATE.md` because outcomes suggest a tighter scope.
  Instead: `Clarify` proposing the tightening; let the operator author it.
- Do not adjust `principles.md` thresholds because calibration suggests a
  shift. Instead: `ProposeAction` with the structured threshold change.
- Do not synthesize an `IDENTITY.md` revision based on observed operator
  behavior. The persona is the operator's authored character; do not
  paraphrase it.
- Do not adjust `_voice.md` or `_editorial.md` because the corpus appears
  to need voice recalibration. The voice is the operator's authored
  declaration of how they sound; surfacing voice drift via `Clarify`
  during quarterly-voice-audit is the right channel.

The right home for the Reviewer's evolving understanding is its
`reviewer-workbench` substrate (`agents/alpha-author/notes.md`). The right channel for
proposed changes to operator canon is the operator's approval surface
(`Clarify` or `ProposeAction`).
