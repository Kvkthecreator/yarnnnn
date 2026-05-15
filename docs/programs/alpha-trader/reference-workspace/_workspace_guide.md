---
schema_version: 1

# Path zones: kernel-universal first (every workspace has these), then
# alpha-trader-specific (this bundle's substrate_abi declarations).
# Each zone declares its role; lock policy is derived per ADR-280 §2.D2.
path_zones:
  # --- Kernel-universal zones ---
  - path: context/_shared
    role: operator-canon
    purpose: operator's standing intent — MANDATE, IDENTITY, BRAND, AUTONOMY, PRECEDENT, _preferences
  - path: context/_shared/_locks.yaml
    role: operator-canon
    purpose: operator-authored lock policy
  - path: uploads
    role: operator-canon
    purpose: operator-contributed reference material
  - path: review/IDENTITY.md
    role: operator-canon
    purpose: Reviewer seat persona declaration
  - path: review/principles.md
    role: operator-canon
    purpose: Reviewer's declared judgment framework
  - path: review/_principles.yaml
    role: operator-canon
    purpose: machine-parsed Reviewer thresholds
  - path: review/OCCUPANT.md
    role: system-ledger
    purpose: current Reviewer seat occupant (rotation primitive writes)
  - path: review/handoffs.md
    role: system-ledger
    purpose: append-only seat-occupant rotation log
  - path: review/calibration.md
    role: system-ledger
    purpose: per-occupant judgment-vs-outcome rolling windows
  - path: review/decisions.md
    role: system-ledger
    purpose: Reviewer's judgment lineage (proposal verdicts, operation-shaping decisions)
  - path: memory/recent.md
    role: system-ledger
    purpose: back-office narrative digest (24h rollup)
  - path: review/notes.md
    role: reviewer-workbench
    purpose: Reviewer's working scratch across wakes
  - path: working
    role: reviewer-workbench
    purpose: ephemeral scratch (24h TTL)
  - path: memory
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
  - path: context/trading
    role: operator-canon
    bundle: alpha-trader
    purpose: per-instrument entities, signals, watched universe
  - path: context/portfolio
    role: operator-canon
    bundle: alpha-trader
    purpose: account-level state, performance, risk

# Reviewer wake envelope: what gets pre-loaded at every wake.
# Universal entries first, then alpha-trader additions.
reviewer_wake_envelope:
  # --- Kernel-universal envelope ---
  - key: identity_md
    path: review/IDENTITY.md
    optional: false
  - key: principles_md
    path: review/principles.md
    optional: false
  - key: precedent_md
    path: context/_shared/PRECEDENT.md
    optional: true
  - key: mandate_md
    path: context/_shared/MANDATE.md
    optional: false
  - key: autonomy_md
    path: context/_shared/AUTONOMY.md
    optional: false
  - key: preferences_yaml
    path: context/_shared/_preferences.yaml
    optional: true

  # --- alpha-trader program-specific envelope ---
  - key: operator_profile_md
    path: context/trading/_operator_profile.md
    optional: false
  - key: risk_md
    path: context/trading/_risk.md
    optional: false
  - key: performance_md
    path: context/trading/_performance.md
    optional: true
  # ADR-281: signal_files is a path-only entry pointing at the compact
  # substrate file written by the mirror-signal-state mechanical recurrence.
  # Per Derived Principle 19, the kernel reads substrate; the recurrence
  # writes substrate; the envelope reads it like every other path entry.
  - key: signal_files
    path: context/trading/_signals_summary.md
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
  (decisions.md, calibration.md, handoffs.md, OCCUPANT.md, memory/recent.md).
  The Reviewer supplies the content (via its `ReturnVerdict` for
  decisions.md); infrastructure renders the entries. The Reviewer does
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
library at `context/_shared/`, Reviewer seat at `review/`, working
memory at `memory/`, agent substrate roots at `agents/`, deliverable +
action recurrence roots at `reports/` and `operations/`, ephemeral
scratch at `working/`, kernel scheduling index at `_recurrences.yaml`.

The alpha-trader program adds two operator-canon domains:

- **`context/trading/`** — per-instrument entities, signals, and the
  watched universe. The operator authors `_operator_profile.md` (the
  edge hypothesis the operator is running) and `_risk.md` (declared
  risk floors). Mechanical primitives mirror per-ticker state into
  `{TICKER}.yaml` files; the signal evaluator writes into `signals/`.
  `_money_truth.md` accumulates outcome reconciliation.

- **`context/portfolio/`** — account-level state. Mechanical primitives
  mirror positions, performance, and risk; `_money_truth.md` accumulates
  reconciled P&L per ADR-195.

Operational substrate emerges through Reviewer judgment + work over
tenure: investigation work surfaces a `research/` directory the Reviewer
populates; pattern-tracking lands in `review/notes.md`; operation-shaping
judgment moments accumulate in `review/decisions.md` (rendered by
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
`reviewer-workbench` substrate (`review/notes.md`). The right channel for
proposed changes to operator canon is the operator's approval surface
(`Clarify` or `ProposeAction`).
