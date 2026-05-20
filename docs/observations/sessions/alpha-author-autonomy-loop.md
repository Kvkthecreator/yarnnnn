# Session Start — alpha-author Autonomy Loop

> **Persistent developer-side orientation for the alpha-author autonomy demonstration.**
> Re-enter this thread cold by reading this file first; act per its protocol. The hat you wear here is **External Developer of the System** (see CLAUDE.md §"The Two Hats" + FOUNDATIONS §Scope). The Reviewer does not read this file; the system does not depend on it. You do.

## What this thread is

The alpha-author autonomy demonstration is the **primary, lower-time-cost vehicle** for validating YARNNN's autonomous Agent OS thesis. It runs against the alpha-author bundle (`docs/programs/alpha-author/`) on persona workspaces, in operator-absent mode — meaning the developer (you/Claude) does NOT engage with the workspace between snapshots. No operator-proxy turns, no chat messages, no nudges. The system runs on its own clock; the developer captures and interprets.

Companion thread: `alpha-trader-autonomy-loop.md` — same shape, capital-lane archetype, longer time horizons.

## North star

A real operator, on a freshly activated alpha-author workspace, has:
- Reviewer that wakes naturally (reactive on `ready_for_review` drafts; scheduled on bundle recurrences)
- Reviewer that reads operator-canon substrate (MANDATE, IDENTITY, _voice.md, _editorial.md, principles.md, _entities.md) and audits drafts against it
- Reviewer that under `delegation: autonomous` produces verdicts that bind (no operator click required)
- Reviewer that meta-aware-edits operator-canon when accumulated evidence warrants (per ADR-295 D1 thresholds)
- All of the above with proper ADR-209 attribution + revision-chain message discipline

Demonstrating these as natural emergent behavior — not as scenario-driven probe responses — is the success criterion.

## Active persona(s)

| Persona | user_id | workspace_id | Status | Active demo |
|---|---|---|---|---|
| yarnnn-author | `0b7a852d-4a67-447d-91d9-2ba1145a60d7` | `0b7a852d-4a67-447d-91d9-2ba1145a60d7` | activated, autonomous, first piece seeded | T0 captured 2026-05-20T03:43Z |
| netflix-script-author | `23cc7951-b6c7-471c-ac38-657d931db6f7` | `23cc7951-b6c7-471c-ac38-657d931db6f7` | activated 2026-05-18 (Phase 0 manual), not yet in active demo | reserved for future demo |
| korea-thriller-shorts | `ca478643-cee9-4f2b-b641-9a5c536aa668` | `ca478643-cee9-4f2b-b641-9a5c536aa668` | activated 2026-05-18 (Phase 0 manual), not yet in active demo | reserved for future demo |

Update this table when a new demo window opens on any persona.

## Current state (update inline as the demo evolves)

**Persona under active observation**: `yarnnn-author`
**Demo window**: 2026-05-20T03:43Z (T0) onwards
**Next scheduled capture**: T+24h ≈ 2026-05-21T03:43Z
**AUTONOMY mode**: `autonomous`
**First seeded piece**: `/workspace/context/authored/governance-as-trust/` (status: `ready_for_review`)
**Latest observation folder**: `docs/observations/2026-05-20-034317-yarnnn-author-autonomy-demonstration-T0/`

## Cold-start checklist (when you open a new Claude session for this thread)

Read these in order before doing anything else:
1. **This file** — orientation
2. **`docs/observations/README.md`** — observation discipline + Edit Checklist for evaluating Reviewer self-amendment behavior
3. **The latest observation folder for this thread** (see "Current state" above) — `PLAYBOOK.md` + `findings.md` from prior captures
4. **ADR-294** — observation discipline canon
5. **ADR-295** — Reviewer self-amendment discipline (what the demo is testing)
6. **ADR-283** — alpha-author bundle scope (what this program is)
7. **FOUNDATIONS v8.6 §Scope** — system-vs-developer-surface boundary (the hat you wear here)

Optional / on-demand:
- `docs/programs/alpha-author/reference-workspace/_recurrences.yaml` — what the system will fire on its own
- `docs/programs/alpha-author/reference-workspace/review/principles.md` — what discipline the Reviewer reads
- `docs/programs/alpha-author/MANIFEST.yaml` — bundle metadata

## What you are allowed to do in this thread (Hat B — External Developer)

- **Capture** the current state of the active-demo workspace by running a snapshot harness. The canonical capture machinery is `services.operator_proxy.capture.CaptureSession`. A snapshot script lives at `/tmp/capture_t0.py` from the initial setup — adapt or rewrite as needed for T+N captures.
- **Read** any substrate file directly via psql or Supabase (read-only is always safe).
- **Compare** state across captures (substrate-diff, revision chain, judgment_log slices, action_proposals).
- **Write findings.md** in observation folders — your qualitative interpretation.
- **Surface system-canon recommendations** to the operator — these turn into Hat-A work (ADRs, persona-frame edits, bundle principles edits).
- **Author NEW session-start guides** if a new demo type emerges that doesn't fit the existing two.

## What you must NOT do in this thread

- **Do not send operator-proxy chat messages** to the active-demo workspace. No `send_message` to `/api/feed`. No REPL turns. The discipline of operator-absent observation requires it.
- **Do not write to the workspace's substrate** unless you are setting up a new demo window from a clean state. Setup writes are documented; ongoing-demo writes corrupt the observation.
- **Do not approve / reject pending proposals** from the developer side. Those are operator actions; we observe what the Reviewer does, not what we'd do if we were the operator.
- **Do not fire recurrences manually** during an active demo window. The whole point is whether the scheduler fires them on its own cadence.
- **Do not edit observation folders' machine-produced artifacts** (transcript.md, substrate-diff.md, etc.). Those are records. Add interpretation to `findings.md`.

If you find yourself wanting to do any of the above, the right move is usually: capture state now, surface what you would have done as a system-canon recommendation, and let the next natural Reviewer wake play out.

## Capture cadence protocol

For an active demo window:
- **T0**: baseline snapshot at demo start. Document setup state in `PLAYBOOK.md`. Findings stub.
- **T+24h**: mid-window snapshot. Diff against T0. Findings drafted with what the system did on its own.
- **T+48h**: end-of-window snapshot. Final diff. Findings finalized.
- **T+7d** (optional): extended observation if the 48h window was inconclusive.

Snapshot folder naming: `docs/observations/{YYYY-MM-DD-HHMMSS}-{persona-slug}-autonomy-demonstration-{T0|T+24h|T+48h|T+7d}/`.

After T+48h findings are finalized, the demo window closes. To start a new window:
1. Cleanup or freshly re-activate the persona (operator decision: same workspace continuing accumulation, or reset for clean baseline?)
2. Possibly seed new substrate (new draft piece, new entities)
3. New T0 in a new observation folder

## How to interpret findings against canon

When reading the captured artifacts at T+24h / T+48h:

**Did the Reviewer fire?**
- Any new revisions with `authored_by: reviewer:*` since T0? If yes, system is alive.
- Which paths? `review/judgment_log.md` + `review/standing_intent.md` are the canonical Reviewer-authored signals.

**What did the Reviewer do on the seeded `ready_for_review` piece?**
- Approve / defer / reject verdict in `judgment_log.md`
- Updated `standing_intent.md` per ADR-284 + alpha-author IDENTITY.md "every judgment-mode cycle updates standing_intent.md"
- For deferred: specific defect cited (e.g., "para 3 hedge stack") + draft's `profile.md` updated with `pre_ship_audit_state: deferred`

**Did scheduled recurrences fire?**
- `corpus-coherence-check` (Mon + Thu 12:00 UTC)
- `revision-audit` (Fri 22:00 UTC)
- `outcome-reconciliation` (daily 05:00 UTC)
- For each fired: check `execution_events` table + corresponding substrate writes

**Did the Reviewer attempt any operator-canon edits?**
- If yes: apply the **Edit Checklist** from `docs/observations/README.md` §"Evaluation Checklist". All four boxes (A: evidence pattern, B: message format, C: anti-patterns avoided, D: design-time deference) should tick clean.
- If yes and ANY box fails: surface as system-canon recommendation. Hat-A fix needed.
- If no: most likely outcome at low-tenure workspaces. Acceptable; **decline = principled refusal** per the cold-start observation pattern.

**Were there any system errors?**
- Reviewer round-budget exhaustion (`no ReturnVerdict after N rounds`)
- Substrate-pathing confusion (writes to non-canonical paths)
- Within-wake state-inconsistency (read-after-write returning stale values)
- All of these are real findings; surface to system canon.

## Cross-references to active discipline

- **Edit Checklist (Reviewer self-amendment evaluation)**: `docs/observations/README.md` §"Evaluation Checklist"
- **Decline Checklist (principled refusal evaluation)**: `docs/observations/README.md` §"Decline Checklist"
- **ADR-295 D1 thresholds (per-program numeric)**: alpha-author = 20 published pieces with audience-response data, 8 distinct audits / 2 weeks persistence
- **ADR-295 D3 anti-pattern ledger**: six anti-patterns that Reviewer must NOT do even when capability permits
- **ADR-294 D2 caller-identity discipline**: `operator-proxy:{caller}:acting-as-{persona-slug}` — used during setup-time substrate seeds only; should NOT appear in ongoing-demo revisions

## When a finding warrants system-canon work

You surface it; you do NOT make the change in this thread. The flow is:
1. Capture surfaces drift (e.g., Reviewer hit an anti-pattern, scheduler missed a fire, attribution leaked)
2. Findings.md records the observation + recommends Hat-A amendments
3. Operator (you, but wearing Hat A) decides whether to draft ADR-XXX, edit persona frame, edit bundle principles, etc.
4. Hat-A work commits to system canon (`api/`, `docs/adr/`, `docs/programs/`)
5. Re-test in a new demo window with hardened canon

Do not blur 2 and 4 within the same commit. The discipline is what makes the boundary load-bearing.

## Cleanup discipline

When closing a demo window or pivoting to a new persona:
- Probe-corrupted state (orphan files at non-canonical paths from prior experiments) gets cleaned via psql DELETE on workspace_files + workspace_file_versions rows
- Don't carry experimental substrate forward into a new demo window — pollutes the baseline
- Don't reset/purge a workspace mid-demo — it kills the observation

## Quick commands

```bash
# Check workspace file count + recent activity
psql "<conn-string-from-docs/database/ACCESS.md>" -c "SELECT count(*) FROM workspace_files WHERE user_id = '<user-id>';"
psql "<conn-string>" -c "SELECT path, authored_by, created_at FROM workspace_file_versions WHERE user_id = '<user-id>' ORDER BY created_at DESC LIMIT 20;"

# Confirm AUTONOMY mode
psql "<conn-string>" -c "SELECT substring(content from 'delegation: [a-z]*') FROM workspace_files WHERE user_id = '<user-id>' AND path = '/workspace/context/_shared/_autonomy.yaml';"

# Capture T+N snapshot — adapt /tmp/capture_t0.py from the original setup
.venv/bin/python /path/to/capture_tN.py
```

## Glossary discipline reminders

When you write findings or reference state, use the system-side vocabulary that lives in canon:
- **Reviewer** (the persona-bearing judgment seat, per ADR-194 v2 + FOUNDATIONS Axiom 2)
- **System Agent** (the execution arm) — NOT "YARNNN" or "the bot"
- **Substrate** (the filesystem-versioned state) — NOT "the database" or "the workspace data"
- **Recurrence** (a scheduled or reactive wake of an agent) — NOT "task" (task abstraction was sunset per ADR-231)
- **Operator** (the human at the cockpit OR the operator-as-Reviewer two-embodiments principal)
- **Operator-canon** (the substrate files the operator authors — MANDATE, IDENTITY, _voice.md, etc.)
- **Governance files** (the three locked files: AUTONOMY.md, _autonomy.yaml, _token_budget.yaml)

For developer-side writing in this thread: scenarios, captures, findings, observations, hypotheses, drift. These are tooling vocabulary, NOT system vocabulary.

## Last updated

2026-05-20 — initial draft alongside the T0 baseline capture for yarnnn-author. Maintain this file as the demo evolves: update "Active persona(s)" table + "Current state" block on each demo-window transition.
