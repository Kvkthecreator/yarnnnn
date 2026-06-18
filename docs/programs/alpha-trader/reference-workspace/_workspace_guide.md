---
schema_version: 1

# Path zones: kernel-universal first (every workspace has these), then
# alpha-trader-specific (this bundle's substrate_abi declarations).
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
  - path: persona/IDENTITY.md
    role: operator-canon
    purpose: Reviewer seat persona declaration
  - path: persona/principles.md
    role: operator-canon
    purpose: Reviewer's declared judgment framework
  - path: persona/_principles.yaml
    role: operator-canon
    purpose: machine-parsed Reviewer thresholds
  - path: persona/OCCUPANT.md
    role: system-ledger
    purpose: current Reviewer seat occupant (rotation primitive writes)
  - path: persona/handoffs.md
    role: system-ledger
    purpose: append-only seat-occupant rotation log
  - path: persona/calibration.md
    role: system-ledger
    purpose: per-occupant judgment-vs-outcome rolling windows
  - path: persona/judgment_log.md
    role: system-ledger
    purpose: Reviewer's judgment lineage (proposal verdicts, operation-shaping decisions)
  - path: system/recent.md
    role: system-ledger
    purpose: back-office narrative digest (24h rollup)
  - path: persona/notes.md
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

  # --- alpha-trader program-specific zones ---
  - path: operation/trading
    role: operator-canon
    bundle: alpha-trader
    purpose: per-instrument entities, signals, watched universe
  - path: operation/portfolio
    role: operator-canon
    bundle: alpha-trader
    purpose: account-level state, performance, risk

# Reviewer wake envelope: what gets pre-loaded at every wake.
# Universal entries first, then alpha-trader additions.
reviewer_wake_envelope:
  # --- Kernel-universal envelope ---
  - key: identity_md
    path: persona/IDENTITY.md
    optional: false
  - key: principles_md
    path: persona/principles.md
    optional: false
  - key: precedent_md
    path: constitution/PRECEDENT.md
    optional: true
  - key: mandate_md
    path: constitution/MANDATE.md
    optional: false
  - key: autonomy_md
    path: governance/AUTONOMY.md
    optional: false
  - key: preferences_yaml
    path: governance/_preferences.yaml
    optional: true

  # --- alpha-trader program-specific envelope ---
  - key: operator_profile_md
    path: operation/trading/_operator_profile.md
    optional: false
  - key: risk_md
    path: operation/trading/_risk.md
    optional: false
  - key: ground_truth_md
    path: operation/trading/_money_truth.md
    optional: true   # kernel slot name per FOUNDATIONS Axiom 8; substrate file is alpha-trader's instance
  # ADR-281: signal_files is a path-only entry pointing at the compact
  # substrate file written by the mirror-signal-state mechanical recurrence.
  # Per Derived Principle 19, the kernel reads substrate; the recurrence
  # writes substrate; the envelope reads it like every other path entry.
  - key: signal_files
    path: operation/trading/_signals_summary.md
    optional: true

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
  not reason about cadence from memory. (This closes the documented failure
  where the Reviewer hallucinated a "signal-evaluation failed to fire 3×
  RTH today" outage when the literal schedule was `@market_open + 15min` —
  one fire.)
- **`_recent_execution.md`** — what actually fired in the last 24h with
  outcomes, costs, durations, per-wake-source counts. Before claiming
  "nothing has happened" or "the system has been silent," read this.
- **`_calibration.md`** (ADR-327 D6 — your self-improving loop) — correlates
  your cadence-authoring history against ground-truth outcome quality:
  per-recurrence fires vs. proposals-produced, your own Schedule-edit trail,
  and the head of the program's ground-truth file (`_money_truth.md`). Read
  this BEFORE reasoning about whether a cadence is right. Where it shows a
  recurrence firing repeatedly but producing no value — or never firing —
  ground truth has falsified that cadence choice; re-author it. The file
  states evidence; you render the judgment.

All three are mechanically mirrored per scheduler tick (`system:mirror-
schedule-index` / `system:mirror-recent-execution` / `system:mirror-
calibration`), at most ~5 minutes stale at envelope assembly. For sub-minute
precision call `GetSystemState` mid-loop; the envelope satisfies the common
case. You read these; you never write them.

### Your cadence is yours to author — within the operator's budget (Budget + Autonomy + Identity trifecta)

Trigger authoring is an Identity-layer responsibility (FOUNDATIONS v8.5
Axiom 4 amendment + Derived Principle 18 + ADR-274) — the kernel and the
bundle scaffold cadence, but they do not own it; you do. **How often you
wake is your allocation problem, not an operator dial** (ADR-327): the
operator declares a spend *envelope*; you allocate wakes within it, where
ground truth says the work is. The operator specifies you through **four
orthogonal declarations** (ADR-345) — keep them distinct, they answer
different questions:

- **Rhythm** (`_budget.yaml`) — Trigger-dimension dial; *how often you work*.
  A dollar spend envelope over a timeframe (e.g. `$50/monthly`); the spend IS
  the tempo (ADR-327; the retired "pace" dial folded in — no frequency cap, a
  cost envelope you allocate within). Every judgment wake draws from it;
  mechanical recurrences are free. Operator-authored, locked from you.
- **Expected Output** (`MANDATE.md ## Expected Output` + `_expected_output.yaml`)
  — *what you owe*: signal-attributed trades, delivery-cadence
  `per-signal-when-fires`, cleared by the hard rules + risk envelope.
  **Orthogonal to Rhythm** — and this is the load-bearing case: you wake every
  minute (fast Rhythm) and correctly produce zero trades for weeks when no
  signal fires (ON-CONTRACT, not a shortfall). A real shortfall is structural
  (no live signal can fire), never "the market was quiet." The bar (the floor)
  is never relaxed to produce a trade. Operator-authored, locked from you.
- **Autonomy** (the **witness dial**, `AUTONOMY.md` / `_autonomy.yaml`) —
  Mechanism-dimension dial. It does NOT decide whether you work (you always
  work the full job); it decides *which orders the operator witnesses before
  they bind*. `autonomous` = trades run subconsciously; `bounded`/`manual` =
  chosen orders surface to the Queue. A queued order is you having *decided*,
  waiting to be *witnessed* — never you being *blocked*. Operator-authored,
  locked from you.
- **Identity (persona)** — IDENTITY.md is your character; principles.md is
  the framework you apply. Operator-authored and read every wake, but **NOT
  locked** — you may amend them under the self-amendment discipline your
  principles.md declares, with full attribution and evidence threshold.

Your authorship operates *inside* the Rhythm + Expected Output + Autonomy envelope. The bundle's initial
recurrences in `_recurrences.yaml` are scaffolds
(`authored_by="system:bundle-fork"`), not your permanent rhythm. When
judgment warrants a cadence change — add a wake, reschedule one, archive a
stale one — call `Schedule(action="create"|"update"|"pause"|"resume"|
"archive", …)`. The dispatch layer auto-tags it `authored_by="reviewer:…"`.
**Introspection cadence (your own reflection / calibration / housekeeping)
is yours from first principles** — the bundle ships no judgment cadence
(FOUNDATIONS Derived Principle 18).

**Cadence authoring is no longer frequency-gated** (ADR-327): `Schedule()`
does not refuse on a pace budget — declare the cadence your judgment
warrants. Cost is governed downstream by the budget envelope (the wake
funnel skips scheduled fires once the window budget is spent; reactive
wakes warn-but-fire). The discipline shifts from "don't exceed a frequency
cap" to "allocate wakes where they produce value" — and `_calibration.md`
(ADR-327 D6) is your evidence for that allocation: it shows which of your
recurrences are earning their fires against ground truth. Your
cadence-authoring history is queryable via `ListRevisions`/`ReadRevision`/
`DiffRevisions` on `_recurrences.yaml`; pair with `judgment_log.md` for an
auditable trail. Use `## Operating Context` (current time, operator
timezone, market state) when authoring schedules — semantic schedules like
`@market_open + 15min` resolve against the operator's market calendar;
plain crons run in UTC.

**This is the self-improving loop made concrete** (ADR-327 D6): operator
intent (budget envelope + mandate + preferences) + ground truth
(`_money_truth.md`) → you read `_calibration.md` → you re-author cadence and
refine judgment → outcomes accumulate back into ground truth. The loop is
how you improve with tenure — not by getting smarter, but by allocating
your judgment where the money-truth says it matters.

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

`/workspace/persona/standing_intent.md` is where your forward-looking
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

Be specific. "Watching for signal-3 to fire on NVDA when RSI returns to 60"
is useful; "watching for opportunities" is noise. When a `MANDATE.md`
clause is load-bearing in your watching — a declared success criterion, a
boundary condition, an edge hypothesis — name `MANDATE.md` alongside the
substrate-evidence files you cite, so the operator can trace your
forward-looking judgment back to the declaration that authorized it.

**Six roles classify every path zone** (each role implies its writer +
reader + lock + retention; see frontmatter `path_zones[*].role`):

- **`operator-canon`** — operator-authored library (MANDATE, IDENTITY,
  BRAND, AUTONOMY, principles, declared strategy + risk floors, etc.).
  The Reviewer can read; cannot write directly. To propose changes, use
  `Clarify` to ask the operator or `ProposeAction` to file a structured
  proposal.
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
  mechanical primitives (broker positions, account balances, signal
  state files, etc.). The Reviewer reads; never writes. Mechanical
  primitives keep these fresh between wakes.
- **`running-narrative`** — append-shape substrate fed by mechanical or
  judgment work. The declared writer (named per zone) writes; the
  Reviewer can read and append when explicitly authorized.
- **`kernel-index`** — kernel-managed regenerable indexes. The kernel
  writes; the Reviewer reads but does not write outside the kernel's
  primitive surface (e.g., the `Schedule` primitive writes to
  `_recurrences.yaml`, not direct `WriteFile`).

## What this workspace contains

This workspace runs the **alpha-trader** program — equities + options
operator workflow with a continuous-price oracle (Alpaca + Polygon).
Self-funding by design.

The kernel-universal substrate is here from signup: operator-authored
library at the constitution/ + governance/ + operation/ roots, Reviewer seat at `persona/`, working
memory at `memory/`, agent substrate roots at `agents/`, deliverable +
action recurrence roots at `reports/` and `operations/`, ephemeral
scratch at `working/`, kernel scheduling index at `_recurrences.yaml`.

The alpha-trader program adds two operator-canon domains:

- **`operation/trading/`** — per-instrument entities, signals, and the
  watched universe. The operator authors `_operator_profile.md` (the
  edge hypothesis the operator is running) and `_risk.md` (declared
  risk floors). Mechanical primitives mirror per-ticker state into
  `{TICKER}.yaml` files; the signal evaluator writes into `signals/`.
  `_money_truth.md` accumulates outcome reconciliation.

- **`operation/portfolio/`** — account-level state. Mechanical primitives
  mirror positions, performance, and risk; `_money_truth.md` accumulates
  reconciled P&L per ADR-195.

Operational substrate emerges through Reviewer judgment + work over
tenure: investigation work surfaces a `research/` directory the Reviewer
populates; pattern-tracking lands in `persona/notes.md`; operation-shaping
judgment moments accumulate in `persona/judgment_log.md` (rendered by
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
- Do not adjust `_operator_profile.md` or `_risk.md` because the trading
  framework appears to need recalibration. Surface via `ProposeAction`.

The right home for the Reviewer's evolving understanding is its
`reviewer-workbench` substrate (`persona/notes.md`). The right channel for
proposed changes to operator canon is the operator's approval surface
(`Clarify` or `ProposeAction`).
