---
schema_version: 1

# Path zones: kernel-universal first (every workspace has these), then
# alpha-commerce-specific (this bundle's substrate_abi declarations).
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
    purpose: current Reviewer seat occupant
  - path: review/handoffs.md
    role: system-ledger
    purpose: append-only seat-occupant rotation log
  - path: review/calibration.md
    role: system-ledger
    purpose: per-occupant judgment-vs-outcome rolling windows
  - path: review/judgment_log.md
    role: system-ledger
    purpose: Reviewer's judgment lineage
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
    purpose: YARNNN orchestration accumulation
  - path: agents
    role: running-narrative
    purpose: per-agent substrate
  - path: reports
    role: running-narrative
    purpose: per-recurrence deliverable outputs
  - path: operations
    role: running-narrative
    purpose: per-recurrence action state
  - path: research
    role: running-narrative
    purpose: investigation working space
  - path: _recurrences.yaml
    role: kernel-index
    purpose: scheduling-index source of truth

  # --- alpha-commerce program-specific zones ---
  - path: context/customers
    role: operator-canon
    bundle: alpha-commerce
    purpose: per-customer entities; lifecycle, LTV, segment
  - path: context/revenue
    role: operator-canon
    bundle: alpha-commerce
    purpose: account-level revenue, MRR, churn, cohort retention

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

  # --- alpha-commerce program-specific envelope ---
  - key: operator_profile_md
    path: context/customers/_operator_profile.md
    optional: false
  - key: revenue_money_truth_md
    path: context/revenue/_money_truth.md
    optional: true

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

Substrate is the persistence layer (FOUNDATIONS Axiom 1). Every piece of
state that survives between invocations lives in `/workspace/` files.
Computation is stateless: read substrate, act, write substrate, terminate.
Substrate is the bus over which the runtime operates.

Every write is **attributed and retained** (Authored Substrate, ADR-209)
— `authored_by` identity + short message; revisions accumulate
non-destructively; history inspectable via `ListRevisions` / `ReadRevision`
/ `DiffRevisions`.

The path zones declared in this guide's frontmatter are guaranteed to be
the substrate topology — readers do not need to `ListFiles` defensively
before writing within them.

**Six roles classify every path zone**:

- **`operator-canon`** — operator-authored library (locked from Reviewer).
- **`reviewer-workbench`** — Reviewer's working substrate (unlocked).
- **`system-ledger`** — infrastructure-rendered append-only (locked from LLM).
- **`world-mirror`** — external state mirrored by mechanical primitives.
- **`running-narrative`** — append-shape, mechanical or judgment-fed.
- **`kernel-index`** — kernel-managed regenerable indexes.

## What this workspace contains

This workspace runs the **alpha-commerce** program — commerce-platform
operator workflow with platform-settled outcome oracle (Lemon Squeezy +
platform webhooks). Self-funding by design.

The kernel-universal substrate is here from signup. The alpha-commerce
program adds two operator-canon domains:

- **`context/customers/`** — per-customer entities. Subscribers and
  buyers. Lifecycle, LTV, segment.

- **`context/revenue/`** — account-level revenue. MRR, churn, cohort
  retention. `_money_truth.md` accumulates reconciled revenue per
  ADR-195.

Operational substrate emerges through Reviewer judgment + work over
tenure: customer-research surfaces the `research/` directory as needed;
patterns land in `review/notes.md`; operation-shaping decisions
accumulate in `review/judgment_log.md`.

## When things diverge

The guide describes the substrate topology; it does not enforce it.
Surface unclassified substrate via `Clarify`; treat it as
`running-narrative` for reading purposes; never silently classify or
relocate substrate to enforce the guide.

## What NOT to write to operator-canon

Even when the Reviewer has insights about operator intent or framework,
do NOT write to `operator-canon` paths directly. Surface insight via
`Clarify` / `ProposeAction` so the operator authors changes with their
own attribution. The right home for the Reviewer's evolving understanding
is `review/notes.md` (reviewer-workbench).
