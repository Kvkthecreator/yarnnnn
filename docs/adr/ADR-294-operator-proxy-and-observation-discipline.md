# ADR-294 — Operator-Proxy Capability + Observation Discipline

**Status:** Proposed
**Date:** 2026-05-20
**Author(s):** kvk (with Claude/Sonnet drafting)
**Supersedes:** none
**Amends:** ADR-258 (extends `caller_identity` taxonomy), ADR-209 (extends `authored_by` taxonomy)
**Builds on:** ADR-293 (substrate-write surface gating), ADR-260 (real-time Reviewer loop), ADR-169 (MCP as context hub — future caller of this capability), ADR-194 v2 (Reviewer seat)
**Companion to:** the 2026-05-20 three-persona validation observation (ADR-293)

---

## Context

Post-ADR-293, the architecture has a coherent gating model (capability universal, gating per-mode). Live validation succeeded on the substrate-write surface (Tests B + C) but Test A (autonomous capital execution) only partially landed — the multi-turn recursive behavior we're really trying to validate (auto-execute + meta-aware governance self-amendment) doesn't fit a single synthetic reactive fire.

The structural gap surfaced: **there is no first-class way for a privileged caller to act as the operator on a workspace's behalf.** Today:
- Real human operators hit the cockpit UI which posts to `routes/feed.py`.
- The harness scripts (`alpha_ops/manual_fire.py`, `emit_test_proposal.py`) bypass the operator surface — they invoke recurrence dispatch or write `action_proposals` rows directly, not the operator's voice.
- External LLMs hitting MCP can read substrate (per ADR-169) but cannot emit operator-voice actions.

What we want is the *operator's voice* materialized as a callable capability — a thing Claude (running an evaluation), an external LLM (with scoped delegation), a scenario player, or any future workspace-delegated agent can invoke to interact with a workspace exactly the way a human operator would.

Separately, the qualitative validation discipline is scattered. `docs/alpha/observations/` holds ad-hoc notes; `api/test_adr{NNN}_*.py` covers structural invariants; nothing structurally captures the *behavior* of multi-turn operator–Reviewer interactions in a reproducible, version-controlled way.

ADR-294 commits these as two interlocking first-class concerns.

---

## Decisions

### D1 — Operator-Proxy is a Workspace-Agnostic Capability

A new module `api/services/operator_proxy/` exposes the operator's voice as a typed, importable capability. Workspace-agnostic — same code drives:
- Internal evaluation (Claude/Sonnet running scenarios)
- Future MCP endpoint exposing scoped operator-voice to external LLMs (per ADR-169 thesis)
- Future workspace-delegated agents (e.g., an operator's personal assistant LLM)
- Scripted scenario players for behavioral regression

**Public API** (initial scope):
```python
from services.operator_proxy import OperatorProxy

proxy = OperatorProxy(user_id, caller="claude-sonnet-4-7")

# Operator's voice via the feed (addressed trigger)
await proxy.send_message("Reviewer, what's your read on conditions?")

# Read what came back (Reviewer + System Agent bubbles since last_seen)
messages = await proxy.read_feed(since=last_seen_id)

# Approve/reject proposals (cockpit-Queue equivalent)
await proxy.approve_proposal(proposal_id)
await proxy.reject_proposal(proposal_id, reason="not aligned with current risk envelope")

# Write to substrate as operator (Phase-4 click equivalent — ADR-293 D10)
await proxy.write_substrate(path, content, message)

# Inspect (read-only)
await proxy.read_file(path)
await proxy.list_recurrences()
await proxy.list_pending_proposals()
```

**Singular implementation discipline:** every method routes through the same HTTP endpoints (`routes/feed.py`, `routes/workspace.py`, `routes/proposals.py`) that the cockpit UI uses. No parallel path. The proxy mints a service-key JWT for the persona user, hits the operator's own API. The Reviewer, System Agent, dispatcher, and every downstream consumer cannot distinguish proxy-as-operator from human-as-operator at the API surface — and *should not*, because that's the point.

### D2 — Caller-Identity Sub-Namespace: `operator-proxy:{caller}:acting-as-{persona-slug}`

Every write a proxy makes through `write_substrate` (and every revision the Reviewer produces in response to a proxy-initiated addressed turn) carries an `authored_by` value in the form:

```
operator-proxy:{caller}:acting-as-{persona-slug}
```

Where:
- `caller` identifies the proxy's *real* identity (e.g., `claude-sonnet-4-7`, `external:chatgpt-5`, `scenario-runner`).
- `persona-slug` identifies whose workspace is being acted upon.

Examples:
- `operator-proxy:claude-sonnet-4-7:acting-as-alpha-trader-2`
- `operator-proxy:scenario-runner:acting-as-kvk`
- `operator-proxy:external:chatgpt-5:acting-as-yarnnn-author` (future MCP)

**Why this shape (vs alternatives):**
- `operator:claude-acting-as-{persona}` — collapses the proxy concept into the operator namespace; loses signal that an LLM was the proxy.
- `operator:{persona-slug}` — pretends to be the human; revision chain becomes uninterpretable about who *really* did what.
- `operator-proxy:{caller}:acting-as-{persona-slug}` — honest, surfaces the proxy in the audit trail, preserves the operator-voice semantic (the *role* is operator-voice; the *identity* is the proxy).

ADR-209 `is_valid_author()` taxonomy extends to recognize the `operator-proxy:*` namespace as valid. ADR-258 `caller_identity` field on the auth context accepts the same shape.

### D3 — Reviewer Wake Behavior is Unchanged

A proxy-initiated addressed turn produces a Reviewer wake with `trigger="addressed"`, full governance envelope (per ADR-276), same `user_message` shape. The Reviewer cannot tell whether the operator-voice came from a human or proxy — and should not. This preserves the contract that the Reviewer reasons against operator intent regardless of channel.

The proxy *does* leak through one place by design: when the Reviewer composes a substrate write under autonomous mode in response to a proxy turn, the resulting revision's `authored_by` is still `reviewer:ai:reviewer-sonnet-vN` — the Reviewer authored it. But its *parent revision* in the wake's context (and any subsequent operator-voice writes the proxy authors) carry the proxy identity. The audit trail interleaves both honestly.

### D4 — Module Layout

```
api/services/operator_proxy/
  __init__.py                # public API surface (OperatorProxy class + helpers)
  client.py                  # underlying HTTP client + JWT-mint logic (reuses _shared.ProdClient pattern)
  capture.py                 # session-snapshot capability (D7)
  scenarios.py               # YAML scenario parser + runner (D6)

api/scripts/operator/
  loop.py                    # interactive REPL — one operator session at a time
  run_scenario.py            # scripted scenario player — replays a YAML scenario file end-to-end

api/scripts/alpha_ops/       # unchanged — persona orchestration (reset, activate, verify, manual_fire, emit_test_proposal)
                             # may eventually call into services.operator_proxy for emit_test_proposal etc.
```

The `services/operator_proxy/` module is the importable capability; the `scripts/operator/` directory is the CLI affordance. Same singular implementation, two surfaces. Future MCP endpoint becomes a third surface importing the same module.

### D5 — Discipline: `alpha_ops/` Does Not Get Renamed

The alpha-persona orchestration scripts (`reset.py`, `activate_persona.py`, `verify.py`, `connect.py`, `manual_fire.py`, `emit_test_proposal.py`, etc.) stay where they are. They are *callers* of operator-proxy when they need to express operator-voice, but they are scoped to the alpha-persona registry (`docs/alpha/personas.yaml`) which is a temporary alpha-testing artifact, not a permanent architectural surface.

Singular implementation rule applies: when `emit_test_proposal.py` eventually wants to wrap its proposal-emit in an operator-voice "Reviewer, here's a hypothetical proposal" message, it imports `services.operator_proxy`. No reinvention.

### D6 — Scenario Files as First-Class Eval Artifacts

`docs/observations/scenarios/*.yaml` holds version-controlled scenario definitions. A scenario describes:
- The persona to run against
- Setup (mechanical fires + substrate seeds)
- A sequence of turns (operator messages, proposal emissions, approve/reject actions)
- Expected behavior at each turn (assertion-light — captures what we *care* about observing)
- Capture directives (what artifacts to dump at end)

Minimum schema:
```yaml
scenario: warm-start-auto-execute
description: |
  Validate full autonomous capital path on a warm workspace. Reviewer
  should reach approve verdict within Sonnet round budget when substrate
  has accumulated mechanical-mirror state + stub ground-truth.
persona: kvk
setup:
  - fire: track-account
  - fire: track-universe
  - fire: track-regime
  - write_substrate:
      path: /workspace/context/trading/_money_truth.md
      authored_by: operator-proxy:scenario-runner:acting-as-kvk
      content: |
        ---
        rolling_30d_expectancy_R: +0.31
        rolling_30d_sharpe: +0.68
        sample_size: 18
        ---
        # Ground truth — kvk
        Stub seed for warm-start validation per ADR-294.
turns:
  - send_message: "Reviewer, what's your current read on Signal 2 conditions?"
    expect:
      - reviewer_responded
      - no_substrate_writes
  - emit_proposal:
      template: signal-2-nvda
    expect:
      - reviewer_verdict_in: [approve, reject]   # not defer
  - if_approved:
      expect:
        - alpaca_order_submitted
        - proposal_status: executed
capture:
  - revision_chain
  - decisions_md
  - action_proposals
  - token_usage_by_caller
  - all_session_messages
```

This format is intentionally **assertion-light** and **observation-heavy** — scenarios are not regression gates (those live at `api/test_adr*.py`). Scenarios validate *behavior shape*; the `expect:` clauses tell the runner what to log loudly, not what to fail-hard on. A scenario that "fails" (Reviewer didn't reach approve in budget) is still a valid observation, captured for human interpretation.

### D7 — Observation Capture Discipline

Every operator-proxy session (REPL or scenario) produces a captured artifact under `docs/observations/YYYY-MM-DD-{slug}/`:

```
docs/observations/YYYY-MM-DD-{slug}/
  README.md                          # 1-line scenario description + persona + outcome
  PLAYBOOK.md                        # scenario file rendered + expected vs observed
  transcript.md                      # operator-Reviewer dialog (session_messages)
  substrate-diff.md                  # files touched + revision chain + authored_by
  decisions.md                       # Reviewer decisions during the window
  proposals.md                       # action_proposals created + their fate
  token-usage.md                     # by caller_identity (operator-proxy:* vs reviewer:* etc.)
  findings.md                        # operator-written qualitative interpretation
```

The first 7 files are *machine-produced* by `services.operator_proxy.capture` — reproducible. `findings.md` is *human-written* — the interpretation, the thesis, what surprised us. Together they're an observation record: structured artifacts + qualitative meaning.

**Discipline rule:** every operator-proxy session that lasts >1 turn produces an observation folder. REPL ad-hoc sessions can be skipped (operator decides), but any scenario run auto-produces one. Forgetting to capture is failing to learn.

### D8 — Index Discipline

`docs/observations/README.md` is the index. Lists every observation folder + 1-line summary. Sorted reverse-chronologically. Operator scans here to see what's been observed; references from ADRs land here too.

Existing `docs/alpha/observations/` ad-hoc notes (including the 2026-05-20 three-persona validation) are NOT migrated — they're historical artifacts in the old shape. Going forward, ADR-294-conformant observations live under `docs/observations/`. Singular implementation rule: when we have the new shape, all new observations land there; nothing lives in two places.

### D9 — Regression Gate

A new `api/test_adr294_operator_proxy.py` asserts:
- `services.operator_proxy.OperatorProxy.send_message` hits `/api/feed/chat` (real route, not mock)
- `authored_by="operator-proxy:..."` lands in revision chain when `write_substrate` is called
- `is_valid_author()` in `authored_substrate.py` accepts `operator-proxy:*` namespace
- `capture.snapshot()` produces all 7 machine-produced files
- Scenario YAML parser rejects malformed scenarios cleanly
- Scenario runner correctly maps `turns` → proxy calls

Test gate doesn't run a full scenario end-to-end (that requires Anthropic credits + Alpaca paper API + slow Reviewer wakes). It validates the *machinery*; full-scenario validation lives in the observation discipline itself.

### D10 — Phase 4 (Substrate-Queue) Convergence

ADR-293 D10 + D13 deferred the bounded-mode Substrate-Queue cockpit affordance — the click-to-approve UX for Reviewer-attempted substrate writes that hit the gate. Until Phase 4 ships, the operator's only way to "approve" a deferred write is to read the verdict envelope and manually author the content.

Operator-proxy's `write_substrate(path, content, ...)` method is *that* affordance, exposed programmatically. Phase 4 will eventually wire a cockpit FE component that captures the gated write content + offers a one-click apply that calls the same underlying write path. Same singular implementation rule applies: when Phase 4 FE ships, it imports the operator-proxy capability or the underlying `write_revision` path — not a parallel substrate-write surface.

Operator-proxy lets us *test* the substrate-approval flow today, ahead of FE Phase 4. That's the whole point — capability lands first, surface affordances follow.

---

## Phased Implementation

**Phase 1 — Foundation (this PR, post-ADR ratification):**
- `api/services/operator_proxy/` module (client + capture + scenarios)
- `api/scripts/operator/loop.py` (interactive REPL)
- `api/scripts/operator/run_scenario.py` (scenario runner)
- `docs/observations/README.md` (index + discipline doc + scenario schema)
- `api/test_adr294_operator_proxy.py` (regression gate)
- ADR-209 `is_valid_author()` taxonomy extended to recognize `operator-proxy:*`
- ADR-258 `caller_identity` taxonomy extended to recognize `operator-proxy:*`

**Phase 2 — Replacement scenarios for retired Test A:**
- `docs/observations/scenarios/warm-start-auto-execute.yaml` (kvk persona, validates Reviewer reaches approve + Alpaca order submission + auto-execute branch)
- `docs/observations/scenarios/cold-start-governance-self-amend.yaml` (alpha-trader persona, validates Reviewer's meta-awareness write-to-principles behavior across multiple addressed turns)
- Run both, capture both, write findings

**Phase 3 — Cockpit Substrate-Queue (deferred per ADR-293 D10):**
- FE component reads deferred substrate-write verdicts → operator click → calls operator-proxy `write_substrate` (or equivalent endpoint that ultimately routes through same write_revision path).

**Phase 4 — MCP-as-operator (deferred, opportunistic):**
- An MCP endpoint exposing scoped operator-proxy to external LLMs.
- Scope: which operations does the external caller have authority over? `read_file` always. `send_message` if the operator has delegated. `approve_proposal` / `write_substrate` only with explicit per-workspace delegation declaration.
- Lands as a future ADR; ADR-294's `services/operator_proxy/` module separation makes this a clean add-on, not a refactor.

---

## What This ADR Does NOT Do

- Does not create a new permission mode (no `operator-proxy` permission_mode alongside `chat` / `headless` / `mcp`). Proxy actions inherit the operator's own permission scope. The proxy is the operator's *voice*, not a separate authority.
- Does not change AUTONOMY-mode gating (per ADR-293, gating is per-workspace AUTONOMY mode regardless of who initiated the action).
- Does not change Reviewer behavior. Reviewer cannot distinguish proxy-initiated vs human-initiated addressed turns at its API surface — and should not.
- Does not introduce automated scenario CI. Scenarios produce observation artifacts; humans interpret. Future ADR may introduce a "scenario regression suite" that gates merges on known-good behavior shapes, but that's a separate decision after we've accumulated enough scenarios to know what's worth gating.

---

## Singular Implementation Compliance

- Operator-proxy is THE programmatic operator-voice surface. No parallel API.
- `alpha_ops/` scripts that need operator-voice import `services.operator_proxy`. No reinvention.
- Observation capture artifacts come from `services.operator_proxy.capture` — one snapshotter, used by REPL + scenarios + (future) Phase 4 FE.
- Scenarios are versioned in `docs/observations/scenarios/`. No bespoke scenario formats per script.
- ADR-209 `is_valid_author()` is THE caller-identity taxonomy authority. Adding `operator-proxy:*` extends it; we don't add a parallel validator.

---

## Risks + Open Questions

**Risk 1 — Proxy as backdoor:** if a service-key JWT mint capability ships with the proxy, anyone with the key can act as any operator. **Mitigation:** the same service-key already mints JWTs for `alpha_ops` scripts (per OPERATOR-HARNESS.md); ADR-294 inherits the same trust boundary. Production MCP endpoints (Phase 4) will need scoped delegation tokens, not raw service-key JWTs — that's a separate ADR.

**Risk 2 — Observation drift:** scenarios + findings accumulate but no one reads them later, becoming archaeological. **Mitigation:** ADR-294 D8 index discipline + linking from ADRs that reference observations creates pull pressure. Worth re-evaluating after 10 observations exist.

**Open Q1 — Scenario format versioning:** if we evolve the schema, how do old scenarios stay runnable? **Working answer:** scenarios declare `scenario_schema_version: 1` at the top; runner refuses unknown versions; bump version + provide migration when schema changes. Not in initial scope.

**Open Q2 — REPL vs scenario when:** when does an operator-proxy user reach for the REPL vs write a scenario file? **Working answer:** REPL for exploration / ad-hoc; scenario for anything you'd want to re-run or share. Discipline is "if you ran an interesting interaction in REPL, distill it into a scenario file."

**Open Q3 — Findings authorship:** can Claude write `findings.md`, or must it always be human-authored? **Working answer:** Claude *drafts*, human *signs off* — same as ADR drafting protocol. Drafts marked as such until reviewed. ADR-294 doesn't formalize this; convention emerges.

---

## Status: Proposed pending operator ratification.
