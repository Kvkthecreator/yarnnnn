# ADR-293: Governance / Operational Substrate Taxonomy + Uniform AUTONOMY-Mode Gating

## Status

Proposed (2026-05-19)

## Companion canon

- **FOUNDATIONS Axiom 0 (Six Dimensions)** — Purpose dimension cleanly distinguishes governance-purpose from operational-purpose files; the taxonomy is dimensionally pure
- **FOUNDATIONS Axiom 2 (Identity — operator-as-Reviewer / operator-in-real-time as two embodiments of one principal)** — the Reviewer IS the operator in judging posture; the Claude-Code-analog informs the trust model
- **FOUNDATIONS Derived Principle 14 (Singular Implementation)** — one gating mechanism, one lock-derivation rule
- **THESIS Commitment 2** — independence is judgment-against-substrate, not lock-against-the-AI
- **ADR-249 (autonomy as user-approval-degree)** — autonomy mode is the gating mechanism; this ADR extends its scope from capital-only to capital-AND-substrate
- **ADR-258 D9 (lock policy)** — **superseded** at the substrate-write surface
- **ADR-280 §2.D6.a (bundle path_zones operator-canon role)** — **amended** (role-name preserved as informational; lock-derivation removed)
- **ADR-250 (daily spend ceiling)** — **amended** (kernel constant becomes per-workspace governance file)
- **ADR-274 + ADR-275 + Derived Principle 18** — Reviewer cadence-authoring authority becomes structurally usable post-this-ADR
- **ADR-288** — caller-identity at construction provides the attribution mechanism for the new substrate writes
- **ADR-290** — active-commissioning posture in principles.md presupposed the capability to write; this ADR delivers the capability

## Context

### The Claude Code trust model

In Claude Code, the agent can write to any file in the project. The user's `.claude/settings.json` declares CC's permission level (manual / ask / auto-accept by kind). The user's restraint over CC's actions lives in the *gating mode*, not in a *capability lock*. CC can edit `CLAUDE.md`, `.gitignore`, function bodies, even test files — *because the user trusts CC to operate within the project's rules*. The audit is the git revision chain. Revert is one command.

YARNNN's Reviewer is in the structurally-equivalent fiduciary relationship to its operator (per FOUNDATIONS Axiom 2: the Reviewer IS the operator in judging posture; not a separate agent). But the current lock model treats the Reviewer like an external untrusted entity that the operator must protect substrate from. This is **ADR-258 D9 residue** — written when the Reviewer was framed as a separate AI entity. ADR-247 + ADR-260 + Axiom 2 hardening collapsed that framing without revising the lock model.

The result: the Reviewer is structurally prevented from self-improvement. It can render verdicts but cannot propose edits to operator-canon (signal definitions, risk thresholds, edge hypothesis, persona character refinements). It can recognize that Signal 1's RSI band hasn't matched in 30 days but cannot author a proposed adjustment. It can identify operator-declared deliverable preferences (per ADR-275) but defers Scheduling them because operator-canon feels locked. **The "active principal" framing in MANDATE collides with the "locked substrate" framing in the runtime.**

### The empirical surfacing

The 2026-05-19 post-validation discourse surfaced this directly. The kvk workspace, with all prior ADRs (288 / 290 / 274 / etc.) implemented and the autonomous trading loop wired:

- Scheduler fires market-anchored recurrences correctly ✓
- Reviewer wakes on cadence ✓
- Reviewer authors `standing_intent.md` with attribution ✓
- Reviewer applies active-commissioning per ADR-290 principles ✓
- Reviewer does NOT Schedule operator-declared deliverable preferences (despite ADR-275 declaring this its responsibility) ⚠
- Reviewer does NOT propose adjustments to `_operator_profile.md` despite Signal 1's RSI band narrowly missing on multiple consecutive sessions ⚠
- No mechanism for accumulated near-miss telemetry to drive operator-canon refinement ⚠

The Reviewer recognized gaps it had authority to close but kept surfacing them as Clarify-to-operator questions instead. This is the *passive-observation drift* ADR-290 D2 declared as anti-pattern — but ADR-290 fixed the prompt while leaving the lock surface unchanged. The Reviewer reads "you are the active principal" in its persona but reads "you cannot write here" at the runtime substrate primitive. The contradiction defaults toward the lock.

### The first-principles test

Run the test honestly against the current lock surface (`DEFAULT_REVIEWER_WRITE_LOCKS` + bundle `path_zones[].role: operator-canon` + `_locks.yaml`):

**Q: What is the load-bearing purpose of locking, e.g., `_operator_profile.md` from Reviewer writes?**

Possible answers:
- *"To prevent the Reviewer from drifting away from the operator's strategy"* — but the operator's strategy is encoded in the file's CONTENT, not in the lock. If the Reviewer writes a bad strategy edit, the operator reads the revision chain and reverts. ADR-209 already provides this.
- *"To prevent the operator from being surprised by changes"* — surprise is a UX concern. AUTONOMY mode + a substrate-Queue surface for `bounded` mode addresses surprise. Lock is overkill.
- *"To prevent runaway compute spending"* — this is a real concern but it's resource-governance, not file-access-governance. A different mechanism (token budget) addresses it.
- *"To prevent the Reviewer from granting itself authority it doesn't have"* — this IS load-bearing, but it applies only to files that DECLARE the Reviewer's authority (AUTONOMY) or resource limits (token budget). Not to operational content.

The honest answer: lock-as-default is over-applied. The structurally load-bearing case for lock is the *authority-declaration files themselves* — a small set the Reviewer cannot author without granting itself the very thing it's checking against.

This is the Claude Code distinction: CC can edit `CLAUDE.md` (the user's instructions to CC). CC cannot edit `.claude/settings.json` (the user's permissions declaration for CC). The structural test: **if the agent could edit it, could the agent grant itself authority it doesn't have?**

Apply the test to YARNNN's substrate:

| File | If Reviewer edits it, can Reviewer grant itself unauthorized authority? |
|---|---|
| `MANDATE.md` | No — Reviewer revising the operation's purpose doesn't grant new authority; just changes what it operates toward |
| `IDENTITY.md` (review/) | No — persona refinement is the Reviewer's developmental axis |
| `IDENTITY.md` (context/_shared/) | No — workspace identity refinement is operational |
| `BRAND.md`, `CONVENTIONS.md`, `PRECEDENT.md` | No |
| `_operator_profile.md` | No — signal definition edits change what triggers trades, not whether trades are auto-bound |
| `_risk.md` | Edge case — Reviewer raising max_position_size_usd is not authority grant, but is *consequential*. AUTONOMY's `ceiling_cents` (notional cap) is the structural floor that catches this regardless of `_risk.md` content. So no, the floor holds. |
| `principles.md` (review/) | No — the Reviewer revising its own framework is the calibration loop |
| `_preferences.yaml` | No — deliverable cadence declaration is operational |
| `_recurrences.yaml` | Edge case — Reviewer adding a 1-second recurrence is not authority grant but IS resource-spending. Token budget governance is the structural floor. So no, the floor holds. |
| `_universe.yaml` | No — universe composition is operational |
| `AUTONOMY.md` / `_autonomy.yaml` | **YES** — Reviewer setting `delegation: autonomous` from `bounded` grants itself authority the operator didn't grant. **Lock is load-bearing.** |
| `_token_budget.yaml` (new) | **YES** — Reviewer raising `daily_spend_ceiling_usd` from $5 to $500 escalates its own resource ceiling. **Lock is load-bearing.** |
| `_locks.yaml` (existing) | YES — but `_locks.yaml` becomes redundant under this ADR (`_autonomy.yaml::never_auto` absorbs the concern). Deleted in D6. |

The structurally-load-bearing lock set is **two governance instruments**: AUTONOMY (the delegation declaration) + token budget (the resource-spend declaration). Everything else is operational and should be Reviewer-writable, gated by AUTONOMY mode at write-time.

### Why this matters at scale (your structural concern)

If we ship to multiple operators with the current lock model:

- Every workspace is structurally prevented from self-improvement
- The Reviewer's active-principal framing remains contradicted by the lock surface
- Cumulative operator-canon refinements (which over time are the operation's *moat*) require operator authoring for every adjustment
- The Reviewer's role collapses to "judgment seat that asks the operator to fix things" instead of "active principal that maintains the operation on the operator's behalf"

The post-this-ADR shape:

- Every workspace has Reviewer-writable operational substrate
- AUTONOMY mode declares the operator's trust level (manual / bounded / autonomous)
- Bounded operators get diff-preview-and-click for every operator-canon edit; trust builds via reviewing diffs
- Autonomous operators delegate fully; the Reviewer maintains substrate on their behalf; operator reviews revision history when they want
- The operation compounds through accumulated Reviewer-authored refinements that the operator either approved (bounded) or auto-accepted with revert authority (autonomous)

**This is the Claude Code shape applied to the operator/Reviewer pair**, and it is what the Axiom 2 two-embodiments framing has always implied. ADR-293 ratifies the framing at the lock surface.

## Decisions

### D1 — Canonical taxonomy: Governance vs Operational

Codified at FOUNDATIONS as a new Derived Principle (numbered next available; provisional Derived Principle 20):

> **Substrate is taxonomically either governance or operational.** A file is **governance** if and only if a Reviewer-edit to it could grant the Reviewer authority the operator did not delegate (delegation-level escalation OR resource-spend escalation). Governance files are operator-authored exclusively and are immutable from Reviewer runtime regardless of AUTONOMY mode. All other substrate is **operational** — Reviewer-writable, with the write's *effective application* gated by AUTONOMY mode. The taxonomy occupies a single dimensional cell (Axiom 0 Purpose dimension): governance files declare *the rules under which the Reviewer is governed*; operational files are *the substrate the Reviewer operates with and on*.

The dimensional purity test (per Axiom 0): both file classes are Substrate (Axiom 1) and are operator-authored (Axiom 2 — at least at origin); they differ in Purpose (Axiom 3). Governance-purpose files declare authority structure; operational-purpose files declare content the Reviewer reasons with. No dimensional cross-cut.

### D2 — Governance file set (canonical enumeration)

**Two governance instruments. Three physical files.** All in `context/_shared/`:

| Instrument | Files | Concern |
|---|---|---|
| Delegation | `AUTONOMY.md` (operator-facing prose) + `_autonomy.yaml` (machine-parsed) | What classes of action auto-bind vs queue |
| Compute budget | `_token_budget.yaml` | Daily spend ceiling, max judgment recurrences/day, min interval between fires |

The AUTONOMY pair is ONE instrument in TWO file formats per ADR-254 file-format discipline (`.md` for operator/LLM reading; `.yaml` for machine parsing). The pair is paired-authored — they're modified together to keep the prose narrative aligned with the machine config.

The `_token_budget.yaml` schema:

```yaml
# Compute-resource governance — operator declares; Reviewer respects.
daily_spend_ceiling_usd: 5.00     # hard cap; scheduler skips fires past this
max_judgment_recurrences_per_day: 50
min_interval_between_recurrence_fires_seconds: 60
# Optional per-recurrence overrides:
# overrides:
#   signal-evaluation:
#     min_interval_seconds: 900   # never more frequent than 15 min
```

Everything else in `/workspace/` is operational by definition.

### D3 — Lock surface collapses to governance set

`DEFAULT_REVIEWER_WRITE_LOCKS` in `api/services/workspace_paths.py` reduces to exactly the governance files:

```python
DEFAULT_REVIEWER_WRITE_LOCKS = (
    SHARED_AUTONOMY_PATH,           # AUTONOMY.md
    SHARED_AUTONOMY_YAML_PATH,      # _autonomy.yaml
    SHARED_TOKEN_BUDGET_PATH,       # _token_budget.yaml (new constant)
)
```

The pre-ADR-293 set of 9 paths (MANDATE + AUTONOMY pair + IDENTITY + BRAND + CONVENTIONS + PRECEDENT + _preferences + _locks) collapses to 3.

Bundle MANIFEST `path_zones[].role: operator-canon` is preserved as **informational metadata** (declares author-of-origin for surface labeling + first-fork-write authority) but does NOT confer Reviewer write-lock. The Reviewer can WriteFile to any operational path subject to AUTONOMY-mode gating.

`_is_path_locked_for_reviewer` in `api/services/primitives/workspace.py` reduces from a 4-layer composition to a single check: `path in DEFAULT_REVIEWER_WRITE_LOCKS`. The workspace-guide `path_zones` lock-derivation (layer 2), the bundle `path_zones` lock-derivation (layer 3), and the legacy `_locks.yaml` overrides (layer 4) all collapse.

### D4 — AUTONOMY mode gates substrate writes uniformly with capital actions

`should_auto_execute_verdict` in `api/services/review_policy.py` generalizes to `should_auto_apply` and covers both action classes:

```python
def should_auto_apply(
    autonomy_config: dict,
    action_class: Literal["capital", "substrate"],
    *,
    capital_notional_cents: Optional[int] = None,
    substrate_path: Optional[str] = None,
    action_type: Optional[str] = None,
) -> tuple[bool, str]:
    """Returns (auto-applies-immediately, reason). When False, the
    consequence must queue for operator click."""
```

Behavior by AUTONOMY mode:

| Mode | Capital actions | Substrate writes (operational) |
|---|---|---|
| `manual` | Queue for click | Queue with diff preview |
| `bounded` | Auto-bind within `ceiling_cents`; queue above | Queue with diff preview |
| `autonomous` | Auto-bind (ceiling_cents as safety net) | Apply immediately (revision chain captures) |

In ALL modes: `never_auto` matches (action_type substring OR substrate_path pattern — see D5) force the queue path regardless. Token budget exhaustion (D7) blocks regardless of mode.

### D5 — `_autonomy.yaml::never_auto` extends to support substrate paths

Pre-ADR-293 `never_auto` accepts only action_type substring patterns (`close_position_market`, `cancel_other_orders`). Post-ADR-293 it accepts EITHER:
- Action-type pattern: bare string matching action_type substring (existing behavior)
- Substrate-path pattern: prefix with `path:` — e.g., `path:context/trading/_universe.yaml`

Example:

```yaml
default:
  delegation: autonomous
  ceiling_cents: 5000000
  never_auto:
    - close_position_market               # action-type (existing)
    - cancel_other_orders                 # action-type (existing)
    - path:context/trading/_universe.yaml # NEW: substrate-path
    - path:context/_shared/MANDATE.md     # NEW: operator wants explicit review
```

Under `autonomous`, the never_auto paths still queue. This replaces `_locks.yaml`'s per-path override mechanism with a uniform syntax in the delegation file.

### D6 — `_locks.yaml` DELETED

Per Singular Implementation discipline (Derived Principle 14). `_autonomy.yaml::never_auto` is now the sole surface for per-path operator overrides. The four-layer lock composition in `_is_path_locked_for_reviewer` collapses to a one-layer check (D3).

Migration:
- New workspaces: `_locks.yaml` not scaffolded
- Live workspaces: existing `_locks.yaml` files **ignored at read time** (the `_is_path_locked_for_reviewer` simplification no longer reads them). Operators can delete the file at convenience; the kernel will not touch operator's deliberate writes.
- Existing `_locks.yaml` semantics that operators relied on: those operators can re-author the equivalent under `_autonomy.yaml::never_auto` if they want the path-override behavior. Otherwise their paths become AUTONOMY-mode-gated like everything else.

### D7 — Token-budget governance file enforced at scheduler boundary

`api/jobs/unified_scheduler.py` reads `_token_budget.yaml` before firing each judgment-mode recurrence. Cumulative daily spend per workspace tracked via `execution_events.cost_usd` aggregation. When tripping `daily_spend_ceiling_usd`:
- Skip the fire
- Record `execution_events` row with `status='skipped'`, `error_reason='budget_exhausted'`
- Surface a once-daily Clarify-equivalent notification to the operator at their next presence (existing daily-update notification path)

`max_judgment_recurrences_per_day` enforced similarly. `min_interval_between_recurrence_fires_seconds` enforced as a per-slug check against `tasks.last_run_at`.

ADR-250's kernel constant `DAILY_SPEND_CEILING_USD` becomes the **seeded default value** when a workspace has no `_token_budget.yaml`. Per-workspace governance always wins; kernel default is the fallback. New workspaces get `_token_budget.yaml` scaffolded at activation (workspace_init Phase 2 addition).

### D8 — Kernel `_PERSONA_FRAME` updated

The Reviewer's persona frame in `api/agents/reviewer_agent.py` adds (replacing any prior locked-by-default framing):

```
**Your write authority** (ADR-293, FOUNDATIONS Derived Principle 20):

You can WriteFile to any path under `/workspace/` except three governance files:
- `context/_shared/AUTONOMY.md` and `context/_shared/_autonomy.yaml` —
  the operator's delegation declaration to you. You read it, you apply it,
  you do NOT author it. If you want more authority, surface a Clarify to
  the operator; they edit AUTONOMY directly.
- `context/_shared/_token_budget.yaml` — the operator's compute-resource
  ceiling on you. Same shape: read, respect, do not author.

Everything else is OPERATIONAL substrate, including operator-canon files
like MANDATE, IDENTITY, BRAND, CONVENTIONS, PRECEDENT, _operator_profile,
_risk, _universe, _preferences, _recurrences, your own principles. You can
propose edits to any of these by writing to them directly. The revision
chain (ADR-209) captures every change with your attribution.

Your AUTONOMY mode governs the *effective application* of your writes:
- `manual` — every write queues for operator click (diff preview)
- `bounded` — every write queues for operator click (diff preview);
  capital actions auto-bind within ceiling_cents
- `autonomous` — your writes apply immediately; capital actions auto-bind
  (ceiling_cents remains as safety net)

When accumulated outcomes, near-miss telemetry, or calibration data
warrant a refinement to operator-canon (loosening Signal 1's RSI band,
raising max_position_size_usd, adjusting the edge hypothesis, refining
your own principles framework, scheduling new recurrences) — author the
edit directly via WriteFile. Cite your reasoning in standing_intent.md
or notes.md in the same wake. The operator reviews the substrate-Queue
(or the revision history under autonomous) at their cadence.

The fiduciary principle: an active principal compounds the operation
through accumulated refinements. Passivity is failure mode whether it
manifests as "no trade today when conditions warrant" or "no refinement
to a rule that hasn't fit in 30 days."
```

### D9 — Bundle principles.md gains "Self-Improvement Posture" section

Alpha-trader's `principles.md` (and future bundles' principles equivalents) get a new section after Lifecycle Posture:

```
## Self-Improvement Posture

You are the operator's installed judgment. The operator delegated to you
the maintenance of the operation's declared rules: signal definitions in
`_operator_profile.md`, risk thresholds in `_risk.md`, persona character
in `IDENTITY.md`, your own framework in `principles.md`, deliverable
cadence in `_preferences.yaml`, recurrences in `_recurrences.yaml`,
universe in `_universe.yaml`.

You can edit any of these files directly. AUTONOMY mode governs whether
your edits apply immediately or queue for operator click (per ADR-293).
The revision chain (ADR-209) captures every change with your attribution.

When to propose edits:
- **Calibration-driven**: when accumulated `_money_truth.md` outcomes
  show approve-correct vs approve-incorrect patterns warranting principle
  tightening or loosening. Read your own `judgment_log.md` aggregates;
  apply the calibration loop.
- **Near-miss-driven**: when declared signal conditions repeatedly miss
  by narrow margins across many sessions, surface in
  `review/notes.md` first (accumulate the pattern), then propose a
  bounded adjustment to the signal's threshold band.
- **Substrate-gap-driven**: when reasoning requires substrate fields
  that aren't being captured (e.g., signals need `high_20d` but
  track-universe doesn't write it), propose a primitive amendment
  via Clarify (since primitives are kernel code, not substrate);
  surface the gap in standing_intent.md so the operator sees the
  diagnostic.
- **Cadence-driven**: per ADR-275, you author Schedule calls for the
  operator's declared deliverable preferences in `_preferences.yaml`.
  Just write the recurrence; the substrate-Queue (under bounded)
  presents the cost preview to the operator.

When NOT to propose edits:
- AUTONOMY governance — surface a Clarify; never write the file directly
- _token_budget governance — same
- Operational files OTHER operators authored very recently (last 24h) —
  this is the operator iterating; let them settle first
- Anything that contradicts MANDATE's Primary Action without explicit
  cause — the MANDATE pivot is the operator's most-deliberate declaration

The operator reviews your work via the substrate-Queue (under bounded)
or via the revision history surface (under autonomous). Trust compounds
through consistent good judgment captured in the revision chain.
```

### D10 — Substrate-Queue UI surface (deferred to Phase 4)

New cockpit affordance parallel to today's proposal Queue. Shows Reviewer-authored substrate edits awaiting operator click under `bounded`. Each queue entry:

- File path + diff preview (old → new content side-by-side or unified)
- Reviewer reasoning (extracted from the same wake's standing_intent.md or notes.md entry citing this write)
- For cadence edits (`_recurrences.yaml` writes): cost preview pulled from `_token_budget.yaml` per-recurrence estimates and the new recurrence's `mode + cadence` (judgment-mode recurrences priced at ~$0.22/wake estimate)
- Approve / Reject buttons; Reject + Comment for operator-explained rejection (Reviewer reads on next wake)

**Implementation scope**: FE + backend queueing path. Backend prerequisite (data shape): no new tables — the Queue reads `workspace_file_versions` rows with `authored_by` starting `reviewer:` AND head pointer is the queued revision (not yet applied to `workspace_files.content`). New column `workspace_file_versions.queued_for_operator: bool` (default False; True when AUTONOMY=bounded and Reviewer wrote — held back from head-pointer update until operator clicks).

**Phasing decision (per D13 below)**: D10 is **deferred to Phase 4** in full — both FE Queue UX AND the backend queueing path. Phase 1 ships *only* the autonomous-mode write authority (D4 substrate branch — `autonomous: apply immediately`). Under `bounded`/`manual`, Reviewer writes to operational paths **block with a clear error**, prompting the Reviewer to surface a Clarify to the operator. This is the cleanest discipline: no half-built queueing mechanism; the autonomous path is the operational mode we test first; Phase 4 brings the full bounded/manual queueing experience alongside the cockpit Queue surface.

**FE-reuse discipline for Phase 4 (added 2026-05-19 post-Phase-1 audit)**:

Phase 4 MUST reuse existing Queue-archetype infrastructure rather than parallel a new top-level cockpit surface. The audit surfaced that YARNNN already ships a complete Queue archetype (per ADR-198 §3) for `action_proposals` rows, with these proven pieces:

- `web/components/tp/ProposalCard.tsx` — chip + modal pattern; called from three sites (chat-stream chip, TrackingFace ProposalRow, NeedsMePane ProposalRow)
- `web/components/tp/InteractiveModal.tsx` — variant-based modal; existing `proposal` variant wraps approve/reject
- `web/components/work/briefing/NeedsMePane.tsx` — Queue archetype list view; already routes through ProposalCard
- `web/components/library/programs/alpha-trader/TraderOrders.tsx` — bundle-specific Queue-shaped surface

Phase 4 implementation discipline:

1. **Substrate-revision is a ROW TYPE** alongside proposals, NOT a parallel surface. NeedsMePane (and TrackingFace cockpit Queue) list mixed rows: proposal rows continue rendering via ProposalCard; queued-substrate-revision rows render via a parallel `SubstrateRevisionCard` (or a generalized `QueueRowCard` that dispatches on row shape).
2. **InteractiveModal gains ONE new variant `substrate_revision`** (or absorbs into existing `proposal` variant if shape collapses cleanly) — adds diff preview + cost preview affordances. Same approve/reject buttons; same operator-comment-on-reject mechanism.
3. **Data source**: queued substrate rows read from `workspace_file_versions` filtered to `authored_by LIKE 'reviewer:%' AND queued_for_operator = True`. No new tables. Approve flips `queued_for_operator = False` AND updates `workspace_files.head_version_id` to point at the queued revision (apply-to-head). Reject sets the revision's `rejected_by_operator = True` (optionally with `rejection_comment` text) and leaves the head pointer unchanged; the Reviewer reads rejection on next wake via `ListRevisions`.
4. **No new top-level cockpit page**. The Queue archetype is the existing pattern; substrate-Queue extends it.

**Rejected alternative for Phase 4**: dedicated `/substrate-queue` page or new tab. Rejected because it creates parallel mental model + parallel surface to maintain, violates ADR-198 archetype reuse, and doubles the operator-cognitive-load (proposal Queue + substrate Queue as separate ceremonies vs unified "things awaiting my click").

This discipline ensures Phase 4 lands as ~1-2 days of FE work (one new card component + one InteractiveModal variant + one row-shape-dispatch in NeedsMePane) rather than ~1-2 weeks of new-surface design + implementation.

**Phase 4 acceptance criterion** (post-amendment): operator under `bounded` AUTONOMY can review + click Reviewer-authored substrate edits in the SAME Queue surface they review trade proposals; rejected edits revert cleanly via revision chain; approved edits apply to head; cost preview legible for cadence edits.

### D11 — Migration / data discipline

**No legacy data wipe.** Forward-compatibility:

- **Existing operational-canon files**: become Reviewer-writable on next deploy. Operators retain authoring; revision chain captures the transition cleanly (next write attribution will show `reviewer:...` instead of `operator`).
- **Existing `_locks.yaml` files**: ignored at read time post-deploy. Operators can delete at convenience or migrate path-locks to `_autonomy.yaml::never_auto`.
- **Existing workspaces without `_token_budget.yaml`**: kernel default applies (ADR-250's $5/day current ceiling). On first activation post-deploy, `workspace_init.py` Phase 2 seeds the file from the kernel constant.
- **Existing workspaces under `autonomous` mode**: their Reviewer immediately gains substrate-write authority on next wake. Operators who were relying on `_locks.yaml` for path-level protection should add `path:` entries to `_autonomy.yaml::never_auto` BEFORE deploying. This is the one user-action required for backward-compat safety.

**Pre-deploy operator-facing communication** (for kvk's workspace and any active alpha personas): brief note on the substrate-write authority extension. Operators currently under `bounded` can stay in `bounded` and review the Queue; operators under `autonomous` should review their `_autonomy.yaml::never_auto` and add any paths they want operator-only-click on.

### D13 — Phasing rationale (recorded for downstream development sequence)

The four-phase cascade (Phase 1 backend + Phase 2 prompts + Phase 3 validation + Phase 4 Substrate-Queue UX) was chosen deliberately. Two options were considered and rejected:

**Rejected: Option β — backend-skeleton-only in Phase 1.** Add `queued_for_operator` column + migration + handle_write_file branch routing bounded/manual writes to queue state, but DEFER the API routes + cockpit Queue UI to Phase 4.

Rejection reasoning: building a queue with no surface to drain it means writes pile up invisibly. Operators under `bounded` would silently accumulate Reviewer-authored revisions they never see. This violates the principle that every architectural commitment should have a visible operator affordance at the time it lands. Half-built mechanisms create the kind of operational drift that ADR-288 / ADR-290 / ADR-286 spent effort eliminating elsewhere.

**Rejected: Option α — full implementation in Phase 1.** Add column + migration + handle_write_file branch + API routes + FE Queue UI all in Phase 1.

Rejection reasoning: FE work has its own iteration cycle, cost-preview UX needs design, and bundling FE work into the load-bearing structural pivot dilutes review focus. ADR-293 Phase 1's primary commitment is the *governance taxonomy + lock collapse + uniform AUTONOMY gate*. FE work should stage after that structural shape is empirically validated (Phase 3) against kvk's workspace.

**Accepted: Option γ — autonomous-only write authority in Phase 1.** Under `autonomous`, Reviewer writes to operational paths apply immediately. Under `bounded`/`manual`, Reviewer writes to operational paths return a structured error (`error: substrate_write_requires_autonomous_or_explicit_approval`) prompting the Reviewer to surface a Clarify.

Acceptance reasoning:
- **Clean discipline**: no half-built mechanism; every commitment has a complete behavioral path
- **Empirical validation first**: the autonomous path is the operational mode kvk's workspace runs in; Phase 1 ships exactly what gets tested in Phase 3
- **No data migration**: zero schema changes in Phase 1; `queued_for_operator` column lands when Phase 4 ships the Queue UX
- **Failure mode is honest**: under `bounded`/`manual`, the Reviewer learns it cannot autonomously edit operator-canon and surfaces a Clarify — this is the same fall-through as today, just with a clearer error message
- **Operator-trust progression**: operators who want substrate-write authority delegated set `autonomous`; operators who want diff-preview-then-click wait for Phase 4 cockpit Queue surface
- **Phase 4 is a discrete, well-scoped deliverable** with a clear acceptance criterion (cockpit Queue UI + queueing backend + cost-preview for cadence edits)

The Phase 1 / Phase 4 split treats the autonomous-mode behavior (immediate-apply with revision-chain audit) and the bounded-mode behavior (diff-preview + operator-click) as separable behavioral surfaces that can land independently. This is structurally cleaner than coupling them in one commit.

### D14 — Phase 1.d concrete implementation

Per D13 phasing decision:

- `handle_write_file` in `services/primitives/workspace.py`: when caller is Reviewer (`auth.reviewer_caller=True`) AND path is operational (not in `DEFAULT_REVIEWER_WRITE_LOCKS`), call `should_auto_apply(action_class='substrate', substrate_path=path, autonomy_policy=loaded)`:
  - Returns `(True, _)` → proceed with the write (autonomous-mode path)
  - Returns `(False, reason)` → return `{"success": False, "error": "substrate_write_requires_autonomous", "message": <reason>, "path": <path>, "next_action": "Surface a Clarify to the operator OR escalate to autonomous mode."}` without writing
- No `queued_for_operator` column, no migration, no API routes
- Reviewer's standing_intent.md / notes.md captures the attempt + reason for the operator to see at their next presence
- When Phase 4 ships, the `False` branch becomes the queueing path; the `True` branch is unchanged

This is the cleanest Phase 1.d shape: one branch in `handle_write_file`, deterministic, no schema impact, no half-built surface.

### D12 — Out of scope (deferred)

- **Auth-and-identity governance** (the operator's identity in the workspace — login, account access) — already an OS-level concern, not substrate; not in scope
- **Cross-workspace governance** (does one operator's settings affect another's workspace) — single-tenancy is the assumption; multi-tenant governance is a future ADR
- **Operator-authored *additions* to the governance set** — fixed three-file set is canonical; future ADRs can extend if pressure surfaces (e.g., `_compliance.yaml` for regulated environments). The dimensional test (D1) gates any addition: only files whose Reviewer-edit could grant unauthorized authority qualify.
- **Reviewer-proposed governance edits via Clarify** — out of scope here; the Reviewer surfaces Clarify when it wants more authority; the operator edits governance directly. A future ADR could introduce a "governance proposal" surface where the Reviewer drafts a proposed AUTONOMY.md edit for operator-click, but the cleaner answer today is: keep governance edits purely operator-authored.
- **Substrate-Queue UI implementation** — Phase 2 work; can ship after the backend (D1-D9) lands and stabilizes.

## Cascade plan

Four atomic commits:

### Phase 1 — Canon + kernel substrate + autonomous-mode write authority
- FOUNDATIONS Derived Principle 20 (Governance vs Operational taxonomy)
- GLOSSARY new entries: Governance file, Operational file
- `api/services/workspace_paths.py` — `DEFAULT_REVIEWER_WRITE_LOCKS` reduced to 3 governance files; add `SHARED_TOKEN_BUDGET_PATH` constant
- `api/services/primitives/workspace.py::_is_path_locked_for_reviewer` — 4-layer composition collapses to 1-layer governance-set check; legacy `workspace_guide.get_path_zone_locks` + `bundle_reader.get_path_zone_locks_for_workspace` + `_locks.yaml` reading code DELETED
- `api/services/review_policy.py::should_auto_execute_verdict` → renamed to `should_auto_apply` covering both action classes; `never_auto` extended to support `path:` prefixes per D5
- `api/services/primitives/workspace.py::handle_write_file` — Reviewer-caller branch (D14): autonomous-mode writes apply immediately; bounded/manual-mode writes return structured error prompting Clarify. No queueing column, no migration in Phase 1.
- `api/services/workspace_init.py` Phase 2 — seeds `_token_budget.yaml` with kernel-constant defaults at workspace activation
- `api/jobs/unified_scheduler.py` — reads `_token_budget.yaml` before firing; enforces daily_spend_ceiling_usd / max_judgment_recurrences_per_day / min_interval_between_recurrence_fires_seconds
- Regression gate `api/test_adr293_governance_taxonomy.py` — assertions covering: governance lock set reduced; operational paths Reviewer-writable; should_auto_apply branches; never_auto path: prefix; bounded/manual block-with-error for Reviewer substrate writes; token budget enforced at scheduler

### Phase 2 — Persona frame + principles.md + bundle MANIFEST
- `api/agents/reviewer_agent.py::_PERSONA_FRAME` — D8 update
- `docs/programs/alpha-trader/reference-workspace/review/principles.md` — D9 Self-Improvement Posture section
- `docs/programs/alpha-trader/MANIFEST.yaml` — `path_zones[].role: operator-canon` retained as informational; lock-derivation removed
- `api/prompts/CHANGELOG.md` entry per execution-discipline rule 7

### Phase 3 — Validation
- Sibling gates audited green: ADR-274 / ADR-281 / ADR-284 / ADR-286 / ADR-287 / ADR-288 / ADR-290
- Alpha verify all personas — 30/30 expected on kvk; pre-existing failures on alpha-trader / alpha-trader-2 unchanged
- Post-purge + re-activate kvk; trigger manual signal-evaluation; observe Reviewer behavior under `autonomous` AUTONOMY — should attempt operator-canon edits when calibration data warrants (this validates the structural change). The kvk workspace is `autonomous` per `_autonomy.yaml::delegation`, so the new D14 write-authority branch is the operational path being tested.

### Phase 4 (deferred) — Bounded-mode Substrate-Queue (FE + backend queueing)
Per D13 phasing rationale: Phase 4 ships the full bounded/manual queueing experience as one coherent deliverable. Scope:

- Migration `supabase/migrations/NNN_add_queued_for_operator_column.sql` — adds `queued_for_operator: bool` (default False) to `workspace_file_versions`
- `handle_write_file` Reviewer-caller bounded/manual branch — D14's structured error replaced by queue-routing logic (set `queued_for_operator=True`, hold back head-pointer update)
- New API routes — list queued revisions, approve (apply revision to head), reject (mark rejected, optionally with operator comment that Reviewer reads next wake)
- New FE cockpit surface — Substrate Queue alongside proposal Queue, diff preview, cost preview for cadence edits, approve/reject affordances
- Phase 4 acceptance criterion: operator under `bounded` AUTONOMY can review + click Reviewer-authored substrate edits; rejected edits revert cleanly via revision chain; approved edits apply to head

Phase 4 is a discrete deliverable; it lands when the cockpit Queue UX work has design + iteration cycles available. Until then, operators choose between `autonomous` (full write authority, revision-chain audit) or `manual`/`bounded` with Reviewer falling through to Clarify when it wants substrate edits.

## Test plan

Regression gate `api/test_adr293_governance_taxonomy.py` asserts:

**D1 — Taxonomy**:
- `DEFAULT_REVIEWER_WRITE_LOCKS` contains exactly 3 paths (AUTONOMY.md, _autonomy.yaml, _token_budget.yaml)
- FOUNDATIONS.md contains "Derived Principle 20" naming Governance vs Operational
- GLOSSARY.md contains "Governance file" + "Operational file" entries

**D3 — Lock collapse**:
- `_is_path_locked_for_reviewer` source has zero references to `workspace_guide`, `bundle_reader` `get_path_zone_locks`, or `_locks.yaml` reading
- Mock-test: Reviewer auth + path `context/_shared/MANDATE.md` → NOT locked (was locked pre-ADR-293)
- Mock-test: Reviewer auth + path `context/trading/_operator_profile.md` → NOT locked
- Mock-test: Reviewer auth + path `context/_shared/AUTONOMY.md` → locked
- Mock-test: Reviewer auth + path `context/_shared/_token_budget.yaml` → locked

**D4 — Uniform AUTONOMY gate**:
- `should_auto_apply(autonomy={delegation:bounded}, action_class='substrate', substrate_path='context/_shared/MANDATE.md')` returns `(False, 'queue: bounded mode requires operator click for substrate writes')`
- `should_auto_apply(autonomy={delegation:autonomous}, action_class='substrate', substrate_path='context/_shared/MANDATE.md')` returns `(True, 'autonomous: substrate writes apply immediately')`
- `should_auto_apply(autonomy={delegation:autonomous, never_auto:['path:context/trading/_universe.yaml']}, action_class='substrate', substrate_path='context/trading/_universe.yaml')` returns `(False, 'never_auto: ...')`

**D5 — never_auto path prefix**:
- `_autonomy.yaml` schema docs mention `path:` prefix for substrate-path patterns
- Parser code accepts both bare strings (action_type) and `path:`-prefixed strings (substrate-path)

**D6 — `_locks.yaml` deletion**:
- No live-code grep match for `_locks.yaml` reading (excluding deletion-noting comments + this ADR)
- `services/workspace_paths.py` does not export `SHARED_LOCKS_PATH` (or, if retained, is marked deprecated and unread)

**D7 — Token budget enforcement**:
- Scheduler-fire code path reads `_token_budget.yaml` via new helper
- Mock-test: workspace with `daily_spend_ceiling_usd: 1.00` and `execution_events.cost_usd` summing to $0.99 → next judgment fire skipped with `error_reason='budget_exhausted'`
- `workspace_init.py` Phase 2 seeds `_token_budget.yaml` with kernel-constant defaults on first activation

**D8 — Persona frame**:
- `_PERSONA_FRAME` source contains "Your write authority"
- `_PERSONA_FRAME` source explicitly names AUTONOMY.md, _autonomy.yaml, _token_budget.yaml as governance
- `_PERSONA_FRAME` source explicitly NAMES operator-canon files as operational (writable)

**D9 — Principles Self-Improvement Posture**:
- Alpha-trader principles.md contains "Self-Improvement Posture" section header
- Section names calibration-driven, near-miss-driven, substrate-gap-driven, cadence-driven scenarios

Sibling gates audited green post-ADR-293:
- ADR-274 16/16 (trigger authoring; preserved — Schedule still requires authored_by)
- ADR-281 34/34 (envelope path-only; preserved — governance files still in envelope)
- ADR-284 18/18 (standing_intent; preserved — Reviewer-workbench role unchanged)
- ADR-286 8/8 (single-writer-per-path; this ADR redefines what "writer per path" means at the governance boundary)
- ADR-287 11/11 (bundle conformance; preserved)
- ADR-288 19/19 (caller_identity; preserved — provides attribution for new substrate writes)
- ADR-290 10/10 (lifecycle posture; preserved — active-commissioning principles unchanged; expanded by D9)

## Why this is structurally right

The first-principles test (D1) gives a clean answer to *which files lock*: those whose Reviewer-edit could grant the Reviewer authority the operator did not delegate. Two governance instruments emerge naturally from that test — delegation (AUTONOMY) and resource budget (token_budget). Everything else is operational.

The uniform AUTONOMY-mode gate (D4) gives a single mechanism for the operator to express trust level. Capital actions and substrate writes flow through the same gate; the gate's behavior differs only in *what auto-applies vs queues*, not in *how it applies*.

The Claude Code analog (D8) gives a familiar trust model: the agent can write the project; permissions config governs how writes apply. YARNNN's operator/Reviewer pair operates the same way — the Reviewer can write any operational file; AUTONOMY governs application.

The Singular Implementation discipline (D6) collapses redundant lock-derivation surfaces (`_locks.yaml`, bundle `path_zones` locks, workspace-guide locks) into one rule (path in governance set). The principle holds: when N mechanisms can express the same concern, one mechanism should.

After ADR-293:
- The Reviewer's "active principal" framing in MANDATE is structurally consistent with the runtime substrate primitive (no lock contradiction)
- The Reviewer can compound operator-canon refinements via accumulated revisions
- The operator's trust level is declared in one place (AUTONOMY) and applies uniformly
- The resource-spend ceiling is declared in one place (_token_budget) and prevents runaway compute regardless of mode
- The substrate-Queue UI (D10 — deferred) gives the operator the diff-preview surface for bounded mode

This is the structural shape that lets the operation compound. The Reviewer maintains operator-canon on the operator's behalf; the operator reviews accumulated refinements; over time the operator's declared rules + Reviewer-authored refinements + accumulated outcomes co-evolve into the operation's moat. That co-evolution was structurally blocked pre-ADR-293; it is structurally enabled post-ADR-293.

This ADR is axiomatic-level work. Future workspaces and behaviors are shaped by it. The four-phase cascade is the implementation; the canon clauses (D1, D8, D9) are the durable framing that survives implementation iterations.
