# Reviewer Formalization Audit — Variant F alignment pass

**Hat**: External Developer of the System (Hat B).

**Predecessor**: [`2026-05-21-021204-reviewer-prompt-strategy-audit-stub/`](../2026-05-21-021204-reviewer-prompt-strategy-audit-stub/findings.md) — opened the open thread for the broader audit motivated by Option D + the sibling text-only-fallback symptom. This folder is the engagement.

**Trigger**: ADR-296 v2 (wake architecture) + ADR-298 (wake queue + pace + Phase 4 minimum_pace + Phase 5 cleanup) all fully Implemented across commits `42c9b13`, `9d320b5`, `2dfdb98`, `9aaddfb`, `b2c4bef`, `dc36cdf`, `f00e18a`. The architectural arc that motivated the broader audit is complete. With the wake-architecture cutover landed and stable, the Reviewer's accumulated prompt surface (~20+ ADR amendments over months) needs to be checked against the now-canonized world.

## Anchor sentence (ratified before audit)

> **The Reviewer is a full-substrate-authoring persona-bearing judgment seat — filesystem-native, single-lane queue-serialized, wake-fired, paced by operator-declared pace + autonomy, driven by operator-authored mandate.**

The audit's job is to find every place the codebase's Reviewer framing contradicts or fails to honor this sentence, and document the drift for Hat-A cleanup.

The seven structural claims (each independently auditable):

1. **Full-substrate-authoring** — `REVIEWER_PRIMITIVES` is CHAT_PRIMITIVES-class, gated only by `DEFAULT_REVIEWER_WRITE_LOCKS` (5 paths: `AUTONOMY.md`, `_autonomy.yaml`, `_token_budget.yaml`, `_preferences.yaml`, `_pace.yaml`).
2. **Persona-bearing judgment seat** — sole systemic persona-bearing Agent per ADR-216 / ADR-194 v2. Persona authored by operator (IDENTITY.md + principles.md), read at reasoning time.
3. **Filesystem-native** — Axiom 1 + Authored Substrate (ADR-209). No parallel DB-resident semantic state.
4. **Single-lane queue-serialized** — ADR-298 wake_queue enforces one Reviewer cycle at a time per workspace via CAS try_lock.
5. **Wake-fired** — ADR-296 v2 + Derived Principle 20. Five wake sources funnel into one evaluation gate; singular invocation gateway `services/wake.py::submit_wake_proposal`. Reviewer self-arranges *future* invocations via Schedule + ManageHook + standing_intent — those route THROUGH wake. It does NOT call `invoke_reviewer()` directly to spawn an inline cycle.
6. **Paced by operator-declared pace + autonomy** — Pace (`_pace.yaml`) is Trigger-dimension dial. Autonomy (`_autonomy.yaml`) is Mechanism-dimension dial. Both locked from Reviewer writes.
7. **Driven by operator-authored mandate** — MANDATE.md hard-gates task creation (ADR-207) and is pre-loaded in the wake envelope. Reviewer reasoning serves the mandate.

## Audit scope (six layers)

| Layer | Target | Method |
|---|---|---|
| L1 | `api/agents/reviewer_agent.py::_PERSONA_FRAME` + `_TRIGGER_FRAMING` | End-to-end read against Variant F |
| L2 | `api/services/reviewer_envelope.py::load_reviewer_governance_envelope` | Confirm envelope shape matches the corrected awareness picture |
| L3 | `api/services/primitives/registry.py::REVIEWER_PRIMITIVES` + `workspace_paths.py::DEFAULT_REVIEWER_WRITE_LOCKS` | Confirm primitive surface matches ADR-296 v2 + ADR-298 commitments |
| L4 | `reviewer_agent.py` tool-use loop body (nudges, text-only fallback, ReturnVerdict exit contract) | Confirm Option D nudge-deletion held; check whether structural close binding is sufficient |
| L5 | `docs/programs/alpha-{author,trader}/reference-workspace/{_hooks,_recurrences}.yaml` | For each judgment prompt, check whether verdict-emission is structurally bound to ReturnVerdict + WriteFile |
| L6 | 14 Reviewer-amending ADRs | Spot-check for pre-cutover prose; confirm supersession banners point forward |

## Findings folder structure

- `PLAYBOOK.md` (this file) — scope, anchor sentence, layer manifest
- `findings.md` — per-layer catalog with verdicts (ALIGNED / DRIFT / OPEN-QUESTION) and explicit Hat-A recommendations
- `RESOLUTION.md` (Commit 3, appended after Hat-A fix lands) — confirms the fix or names residual drift
