# Observations

**Canonical home for behavioral observation records of YARNNN workspaces** (ADR-294 D8).

This directory holds version-controlled captures of operator-proxy sessions — interactive REPL runs and scripted scenario playbacks. Each observation is a folder with machine-produced artifacts (substrate diffs, transcripts, token-usage tables, decisions slices) plus a human-written `findings.md` recording qualitative interpretation.

This is the qualitative companion to `api/test_adr*.py` regression gates. Together they form the YARNNN evaluation discipline: regression gates assert structural invariants; observations capture behavioral shape across multi-turn interactions.

## Why this exists

The autonomy/observability question — *"does the Reviewer act the way we think it does?"* — cannot be answered by unit tests alone. Behavioral validation requires multi-turn interaction under realistic operator pacing, with substrate accumulation, governance gates, capital-action paths, and the back-and-forth of operator-voice nudges all in scope.

Ad-hoc observation notes (the pre-ADR-294 pattern) drift. ADR-294 commits observations as first-class artifacts:
- **Reproducible**: scenario files in `scenarios/` re-run cleanly. The machine-produced artifacts are derived from DB state, not narrative recall.
- **Interpretable**: `findings.md` is human-written. The point of observation is interpretation, not just data capture.
- **Linkable**: ADRs reference specific observations as evidence; observations reference ADRs they validate or stress.

## Folder layout

```
docs/observations/
  README.md                            # this file — discipline + index
  scenarios/                           # versioned scenario YAML files
    warm-start-auto-execute.yaml
    cold-start-governance-self-amend.yaml
    ...

  YYYY-MM-DDTHHMMSS-{slug}/            # one folder per observation run
    README.md                          # 1-line summary + metadata
    PLAYBOOK.md                        # scenario or REPL session metadata
    transcript.md                      # operator–Reviewer dialog (session_messages slice)
    substrate-diff.md                  # files touched + revision chain + authored_by
    decisions.md                       # Reviewer decisions during the window
    proposals.md                       # action_proposals created + their fate
    token-usage.md                     # execution_events grouped by caller_identity
    findings.md                        # HUMAN-WRITTEN interpretation (initially a stub)
```

## Workflow

**Scripted scenario:**
```bash
.venv/bin/python -m api.scripts.operator.run_scenario \
    --scenario docs/observations/scenarios/warm-start-auto-execute.yaml \
    --caller scenario-runner
```
Produces a timestamped observation folder with all 8 files. `findings.md` is a stub — edit it after reading the artifacts.

**Interactive REPL:**
```bash
.venv/bin/python -m api.scripts.operator.loop \
    --persona alpha-trader-2 --caller claude-sonnet-4-7
> /capture                # take baseline
> Reviewer, what's your read?
> /feed
> /capture                # snapshot
```

## Discipline rules

1. **Every >1-turn operator-proxy session produces an observation folder.** Forgetting to capture is failing to learn. Scenario runs auto-capture; REPL captures on `/capture` command.

2. **`findings.md` is human-written, not Claude-written.** Claude may draft, human signs off. Drafts are marked as such until reviewed.

3. **Machine-produced artifacts are append-only.** Don't edit `transcript.md` or `substrate-diff.md` after capture — they're records. To add interpretation, edit `findings.md`.

4. **Scenarios are versioned.** Once `cold-start-governance-self-amend.yaml` is committed, changes to it should be intentional + ADR-amend-worthy if they change observed behavior shape.

5. **Cross-link with ADRs.** When an observation contradicts an ADR's claim, the next commit is either an ADR amendment or a new ADR documenting the contradiction. Don't let observations drift away from the canon.

6. **One scenario, one folder, one finding.** Don't accumulate multiple scenario runs in one folder. Each capture gets its own timestamped folder.

## Scenario schema (v1)

```yaml
scenario_schema_version: 1      # optional, defaults to 1; runner refuses unknown
scenario: warm-start-auto-execute
description: |
  Multi-line free-form description of what this scenario validates +
  why it exists.
persona: kvk                    # persona slug from docs/alpha/personas.yaml
setup:
  - fire: track-account         # manual_fire a recurrence by slug
  - fire: track-universe
  - write_substrate:            # operator-voice seed write
      path: /workspace/context/trading/_money_truth.md
      authored_by: operator-proxy:scenario-runner:acting-as-kvk
      content: |
        ---
        rolling_30d_expectancy_R: +0.31
        ---
        # ground truth stub
turns:
  - send_message: "Reviewer, what's your current read on conditions?"
    expect:                     # interpretation hints (logged, not pass/fail)
      - reviewer_responded
      - no_substrate_writes
  - emit_proposal:
      template: signal-2-nvda   # references existing emit_test_proposal logic
    expect:
      - reviewer_verdict_in: [approve, reject]
  - approve_proposal:           # explicit approve action
      id: "{{previous_proposal_id}}"
      reasoning: "scenario-driven approval"
    expect:
      - alpaca_order_submitted
capture:
  - revision_chain
  - decisions_md
  - action_proposals
  - token_usage_by_caller
  - all_session_messages
```

### Field reference

| Field | Required | Notes |
|---|---|---|
| `scenario` | yes | Unique slug, kebab-case. Used as folder suffix + log key. |
| `description` | yes | Free-form, human-readable. Saved to PLAYBOOK.md. |
| `persona` | yes | Persona slug from `docs/alpha/personas.yaml`. Resolves to user_id + email for JWT mint. |
| `setup[]` | no | Pre-turn actions. Each item is `{fire: slug}` or `{write_substrate: {...}}`. Logged but not turn-counted. |
| `turns[]` | yes | Ordered operator-voice sequence. See Turn shapes below. |
| `capture[]` | no | Which artifact types to emit. Default: all. |
| `scenario_schema_version` | no | Defaults to 1. Bumped when schema changes incompatibly. |

### Turn shapes

| Shape | Effect |
|---|---|
| `{send_message: "..."}` | Operator-voice chat message via `/api/feed`. Reviewer wakes addressed-trigger. |
| `{emit_proposal: {template: <name>}}` | Stub — currently logs intent; wires into `emit_test_proposal.py` when needed. |
| `{approve_proposal: {id, reasoning}}` | POSTs `/api/proposals/{id}/approve`. |
| `{reject_proposal: {id, reason}}` | POSTs `/api/proposals/{id}/reject`. |

`expect:` clauses are **interpretation hints**, not pass/fail assertions. The runner logs what was expected + observed; humans interpret the diff in `findings.md`.

## Caller-identity discipline (ADR-294 D2)

Every action by the operator-proxy carries:
```
operator-proxy:{caller}:acting-as-{persona-slug}
```
in `authored_by` (for substrate writes) or in `reviewer_reasoning` (for approve/reject — the human-reviewer seat is still filled per ADR-194 v2; the proxy identity surfaces in the reasoning text).

Examples:
- `operator-proxy:claude-sonnet-4-7:acting-as-alpha-trader-2`
- `operator-proxy:scenario-runner:acting-as-kvk`
- `operator-proxy:external:chatgpt-5:acting-as-yarnnn-author` (future MCP-as-operator)

The audit trail stays honest about who *really* did what.

## Relationship to `docs/alpha/observations/`

`docs/alpha/observations/` holds historical ad-hoc observation notes (pre-ADR-294). Those stay where they are as historical artifacts. **Going forward, ADR-294-conformant observations land here at `docs/observations/`.** Singular implementation rule — one canonical home for new observations; nothing lives in two places.

## Index

(Reverse-chronological. Will populate as scenarios run.)

*(none yet — Phase 2 will produce the first entries when warm-start-auto-execute + cold-start-governance-self-amend scenarios run)*
