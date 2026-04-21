# 2026-04-21 — alpha-trader — Phase-1 seeding bypassed architecture for 3 of 5 identity-domain files

## Classification
- **Objective:** A-system
- **Within-A scope:** systematic-workflow
- **FOUNDATIONS dimension:** Substrate
- **Severity:** cognitive-load
- **Resolution path:** ADR-candidate
- **Money impact:** decision-impact

## Context
I (Claude, Mode 1 per CLAUDE-OPERATOR-ACCESS.md) was tasked to run the
full Phase-1 scaffolding of the `alpha-trader` workspace on behalf of
KVK. The playbook §3A.1–3A.5 declares five identity-domain files +
six tasks as the seed state.

I audited what paths the existing architecture offers for each file
before writing the scaffold driver (`api/scripts/alpha_ops/scaffold_trader.py`).

## What happened

Two files land through clean architectural paths:

1. `/workspace/IDENTITY.md` → `POST /api/memory/user/identity` (ADR-144)
2. `/workspace/BRAND.md` → `POST /api/memory/user/brand` (ADR-144)

Three files have **no sanctioned write path** and had to be written
via direct Postgres `INSERT … ON CONFLICT` against `workspace_files`:

3. `/workspace/review/principles.md` — ADR-194 v2 scaffolds default content
   at signup and the AI Reviewer reads it at proposal-time
   (`services/review_principles.py`), but there is no primitive,
   route, or UI affordance to **rewrite it** to a persona-specific
   framework (here: the Simons 6-check capital-EV reasoning). The
   `/workspace/file` PATCH endpoint explicitly lists `/workspace/review/*`
   as not-editable (routes/workspace.py:478-488).
4. `/workspace/context/trading/_operator_profile.md` — no primitive. This is
   operator-declared domain policy (declared universe + 5 signal specs). It
   is structurally **not** any of: workspace IDENTITY (different level),
   memory (different lifetime — declared, not inferred), accumulated agent
   context (different writer — operator, not agent), task output, or
   uploaded document. It falls through the cracks of ADR-106 / ADR-142
   / ADR-144 / ADR-151.
5. `workspace/context/trading/_risk.md` (no leading slash per
   risk_gate.py:48 `RISK_MD_PATH`) — same gap as `_operator_profile.md`.
   Separately, the path is inconsistent with ADR-119 — already flagged
   in `personas.yaml`.

The six Phase-1 tasks were created via `POST /api/tasks` and paused via
`PUT /api/tasks/{slug}` — that path works. But tasks for `produces_deliverable`
kinds (pre-market-brief, weekly-performance-review, quarterly-signal-audit)
are created with `TASK.md` only — **no `DELIVERABLE.md`**. ADR-149 / ADR-178
expect a deliverable spec; inference is supposed to populate it, but
there is no "scaffold DELIVERABLE.md now" hook on task creation.

## Friction

1. **No `_operator_profile.md` architectural primitive.** This is a
   load-bearing persona-substrate file (the Reviewer's Check 2 reads
   signal rules from it). That no primitive writes it is a real gap.
   Right now it only exists because an operator, a harness script, or
   YARNNN-as-typist put it there. If KVK's first-session IDENTITY dump
   mentioned signals, would YARNNN write this file today via
   `WriteFile`? Possibly, but arbitrarily — there is no declared
   convention that "operator declarations go here in this shape."

2. **`review/principles.md` rewrite path missing.** The Reviewer's
   reasoning framework is tuned per persona (Simons Option B is very
   different from a commerce operator's refund-approval framework) but
   the tuning surface is DB-only. Operators cannot rewrite it via cockpit
   today — they can only accept the default.

3. **Path drift on `_risk.md` leaks into harness.** Because
   `risk_gate.py:48` reads from `workspace/…` (no leading slash) while
   every other file uses `/workspace/…`, the scaffold script had to
   encode the exception. Any future operator-profile primitive that
   follows ADR-119 conventions will land at a different path from
   `risk_gate.py`'s read target and silently break. Low blast radius
   (caught by `verify.py`) but a latent footgun.

4. **`DELIVERABLE.md` not scaffolded at task-create.** Three of the
   six persona tasks are `produces_deliverable` and should have a
   quality contract per ADR-149 / ADR-178. They don't. The task will
   run and produce *something*, but the contract lens
   (`_parse_deliverable_md`) will return null and the cockpit Quality
   Contract panel will be empty. This is probably "inference will fill
   it in after first-run feedback" — but the seed state between
   task-create and first-feedback is unacceptably empty.

## Hypothesis

Three separate ADR candidates, in priority order:

- **ADR-candidate P1: Operator-declared domain policy files.** Introduce
  a concept + primitive for operator-authored, domain-scoped declarations
  (e.g., `_operator_profile.md`, `_risk.md`, future `_universe.md`).
  Pattern: like IDENTITY.md but scoped under `/workspace/context/{domain}/`,
  writable by the operator via a sanctioned primitive (extend `UpdateContext`
  with `target="domain_policy"` + `domain=...` + `file=...` params?).
  Directory registry v5 declares which files are domain-policy vs
  accumulated.

- **ADR-candidate P2: Reviewer principles as first-class editable
  surface.** Either a dedicated `UpdatePrinciples` primitive or extend
  the `/workspace/file` PATCH allow-list with `/workspace/review/principles.md`
  and a schema validator that confirms the parse-ability that
  `review_principles.py` depends on.

- **ADR-candidate P3: Auto-scaffold DELIVERABLE.md at task-create for
  `produces_deliverable` task kinds.** Registry-driven starter content
  (already present in task_types.py) materialized into DELIVERABLE.md
  at task-create time, then refined by inference. Closes the "empty
  contract between create and first-feedback" window.

Separately, and already known: fix `RISK_MD_PATH` in `risk_gate.py:48`
to use the leading-slash convention. This is a 1-line fix + one-time
data migration (UPDATE workspace_files SET path = '/workspace/...'
WHERE path = 'workspace/...'). Do it alongside P1.

## Counterfactual (Objective B)

If the operator (real or Claude-as-operator) can't rewrite `principles.md`
to encode the 6-check Simons framework, the AI Reviewer evaluates
trade proposals against a generic default — which will reject trades
on the wrong grounds, approve trades that violate signal-discipline,
or both. Both are real-money decision failures. P2 is a
decision-impact gap even before any money moves.

## Links

- Driver: `api/scripts/alpha_ops/scaffold_trader.py` (new, this session)
- Gated write path: `api/routes/workspace.py:463-517` (PATCH allow-list)
- Write-free read: `api/services/risk_gate.py:48` (the path drift)
- Review reader: `api/services/review_principles.py` (the read target that P2 unblocks)
- Related ADRs: ADR-106, ADR-119, ADR-142, ADR-144, ADR-149, ADR-151,
  ADR-178, ADR-194 v2
- Related observation:
  `2026-04-21-alpha-trader-cockpit-first-run-semantically-empty.md`
  (prior session — the cockpit-side counterpart; together they bracket
  "what alpha-trader looks like at t=0 when cold-started through
  system vs hand-scaffolded")
