# ADR-276: Reactive-Trigger Envelope Governance Pre-Load

> **⚠ Preserved by [ADR-296 v2](ADR-296-continuous-judgment-cycle.md) (2026-05-20).** ADR-276's `load_reviewer_governance_envelope` helper — the singular canonical assembly point for operator-authored governance substrate at every Reviewer wake — is preserved and generalized. Under ADR-296 v2 D1, every Reviewer wake (regardless of which of the five wake sources proposed it) routes through `services/wake.py`, which calls `load_reviewer_governance_envelope` before invoking the Reviewer. The "one helper, many callers" Singular Implementation pattern is intact; only the caller list expands (cron_tick + addressed + proposal_arrival + substrate_event + manual_fire all route through the same envelope helper inside the wake gateway). The `envelope_load_ms` observability column (migration 175) continues to populate at every escalated wake.

**Status**: **Implemented 2026-05-14** — closes the structural gap ADR-275 §5b documented as out-of-scope. Finishes the dev sequence FOUNDATIONS v8.5 → ADR-274 → ADR-275 → ADR-275 refinement → ADR-276.

**Observability hardening (2026-05-15)**: `load_reviewer_governance_envelope` return signature widened to `(dict, int)` — the second element carries elapsed ms. Reactive callers route the elapsed value into `execution_events.envelope_load_ms` (new column, migration 175); addressed callers log it via structured logger (`[REVIEWER_ENVELOPE] addressed`). Regression gate `api/test_envelope_observability.py` (10/10 PASS) validates the contract; sibling gates (ADR-275 + ADR-274 + ADR-276) still green post-update. Rationale: the helper is the dominant DB-read pattern per Reviewer wake (9 parallel `workspace_files` reads + `signal_files` summary), and today's `duration_ms` couldn't isolate envelope cost from total wake latency. Surfaces capacity-tuning data with zero LLM cost.

**Authors**: KVK + Claude (discourse session 2026-05-14, continued from ADR-275 refinement)

**Companion canon**: FOUNDATIONS v8.5 Axiom 4 + Derived Principle 18 (already shipped via ADR-274). ADR-274 declared Trigger-authoring as an Identity-layer responsibility. ADR-275 closed the bundle-vs-Reviewer half of that for judgment cadence. ADR-275 refinement closed the addressed-trigger envelope half. ADR-276 closes the reactive-trigger envelope half — the third and final structural gap in the same axiom-implementation arc.

**Amends**: ADR-260 (Reviewer real-time loop), ADR-261 (recurrence shape), ADR-263 (mechanical vs judgment mode dispatch). All three established the reactive-trigger pathway; none of them prescribed the envelope shape the Reviewer's wake actually receives.

**Preserves**:
- FOUNDATIONS Axioms 1–8 unchanged.
- ADR-209 Authored Substrate model unchanged.
- Schema unchanged (no new tables, no new columns).
- Primitive surface unchanged (no new primitives).
- Cron scheduler unchanged.
- Mechanical-mode recurrences unchanged (they don't wake the Reviewer).

**Dimensional classification**: **Trigger** (Axiom 4) primary; **Identity** (Axiom 2) secondary; **Channel** (Axiom 6) tertiary.

---

## 1. The structural gap (audit-found during ADR-275 run-2)

Run-2 e2e on commit `af123ca` validated the addressed-trigger envelope: the Reviewer perceives full governance substrate (IDENTITY + principles + PRECEDENT + MANDATE + AUTONOMY + `_preferences.yaml` + `_operator_profile` + `_risk` + `_performance`) at every addressed wake via `routes/feed.py`'s 9-file `asyncio.gather` pre-load. Result: Reviewer authored 3× `Schedule` for active operator preferences on its first wake.

However, when the Reviewer's same loop subsequently called `FireInvocation(slug="signal-evaluation")` at the end of run-2, the resulting reactive wake (via `services/invocation_dispatcher.py::dispatch_recurrence`) received only:

```python
context = {
    "recurrence_prompt": <the recurrence's YAML prompt>,
    "recurrence_slug": <the slug>,
    "recurrence_required_capabilities": [...],
    "options": {...},
    "operating_context_block": <ADR-274 time/market state>,
}
```

**No MANDATE, no IDENTITY, no principles, no AUTONOMY, no `_preferences.yaml`, no domain substrate.** The Reviewer's reactive wake reasons only from the recurrence's own prompt + Operating Context, relying on tool calls to fetch governance substrate. This is the same prose-vs-pre-load asymmetry ADR-275 refinement closed for addressed turns — applied to reactive turns instead.

Symptom in the field (run-2 §Side observation b): the Reviewer's `signal-evaluation` reactive wake "completed but did not populate `/workspace/context/trading/signals/`." The Reviewer didn't have its principles + `_operator_profile.md` (which declares the signals) + `_universe.yaml` pre-loaded; it would have had to do tool calls to fetch them and may have hit a context-or-prompt-interaction issue along the way. Whether the empty `signals/` was strictly *caused* by the missing pre-load or downstream of some other gap is the empirical question this ADR's deployment answers.

## 2. Why this is structurally the same fix

The architectural pattern that worked for addressed turns (ADR-275 refinement) applies identically to reactive turns:

| Concern | Addressed (ADR-275 refinement) | Reactive (ADR-276) |
|---|---|---|
| Site assembling `ReviewerContext` | `routes/feed.py` | `services/invocation_dispatcher.py::dispatch_recurrence` |
| Pre-load mechanism | `asyncio.gather` of 9 file reads | Identical |
| Wake envelope shape | `_build_user_message` renders pre-loaded sections | Identical (already shared between both triggers) |
| Substrate delivered | IDENTITY + principles + PRECEDENT + MANDATE + AUTONOMY + `_preferences.yaml` + `_operator_profile` + `_risk` + `_performance` + signal_files | Identical |

The Reviewer's `ReviewerContext` TypedDict + `_build_user_message` envelope assembly + `_PERSONA_FRAME` prose are unchanged from ADR-275 refinement. Only the dispatcher's context-bag assembly site needs to mirror the feed.py pre-load.

## 3. Decisions

### D1. New helper `services/reviewer_envelope.py::load_reviewer_governance_envelope`

Extract the 9-file pre-load logic into a single shared helper so both trigger paths (addressed + reactive) call the same code. Singular Implementation: one helper, two callers.

```python
async def load_reviewer_governance_envelope(client, user_id) -> dict:
    """Returns the full governance + domain substrate the Reviewer
    perceives at every wake. Used by both addressed-trigger (routes/feed.py)
    and reactive-trigger (services/invocation_dispatcher.py) call sites.

    Returns a dict keyed by the ReviewerContext field names — drop
    directly into the context bag passed to invoke_reviewer().
    """
```

Reads in parallel: REVIEW_IDENTITY_PATH, REVIEW_PRINCIPLES_PATH, SHARED_PRECEDENT_PATH, SHARED_MANDATE_PATH, SHARED_AUTONOMY_PATH, SHARED_PREFERENCES_PATH, `context/trading/_operator_profile.md`, `context/trading/_risk.md`, `context/trading/_performance.md`. Also loads `signal_files_summary` via `read_signal_files`.

Returns keys: `identity_md`, `principles_md`, `precedent_md`, `mandate_md`, `autonomy_md`, `preferences_yaml`, `operator_profile_md`, `risk_md`, `performance_md`, `signal_files`.

### D2. `routes/feed.py` migrates to the helper

Singular Implementation: the inline `_asyncio.gather` block in `feed.py` (lines ~1186-1200) is replaced by a single `await load_reviewer_governance_envelope(auth.client, auth.user_id)` call + dict-unpack into the context bag. ~15 LOC delete + 2 LOC add.

### D3. `services/invocation_dispatcher.py` adds the helper call to reactive dispatch

Before `invoke_reviewer(trigger="reactive", context={...})` in `dispatch_recurrence`, call the helper and merge results into the context bag alongside `recurrence_prompt`, `recurrence_slug`, etc.

The reactive context bag becomes:

```python
{
    "recurrence_prompt": prompt,
    "recurrence_slug": recurrence.slug,
    "recurrence_required_capabilities": list(recurrence.required_capabilities),
    "options": dict(recurrence.options) if recurrence.options else {},
    "operating_context_block": operating_context,
    **governance_envelope,   # ADR-276: full governance substrate pre-loaded
}
```

### D4. No persona-frame changes

`_PERSONA_FRAME` is unchanged. The persona already names operator preferences as "pre-loaded above"; it now applies to reactive wakes too, with no prose modification needed. The structural delivery is what changes, not the contract.

### D5. No new ADR for the dual-writer `decisions.md` question

Side observation (a) from run-2 (Reviewer's `WriteFile` + dispatch's `append_decision` racing on `decisions.md` head pointer) is **explicitly out of scope** for ADR-276. It's a Singular Implementation question (which writer is canonical?) that deserves its own discourse, not a bundled-in fix on top of an axiom-implementation commit. Documented as the next item for separate session.

### D6. Item #3 (`signal-evaluation` empty `signals/`) re-tested post-deploy, not pre-emptively patched

If the reactive-trigger Reviewer perceives `_operator_profile.md` (which declares signals) + `_universe.yaml` (which declares tickers) + principles pre-loaded, the next `signal-evaluation` fire should populate `signals/` correctly. If it still doesn't, then the gap is in the prompt or the signal-evaluation logic itself — a separate bundle-level audit. ADR-276's deployment is the empirical test.

## 4. What this ADR does NOT do

- **No new primitives.** All work happens through the existing `ReviewerContext` shape.
- **No schema changes.** No new tables, no new columns.
- **No changes to `_build_user_message`.** The envelope renderer already handles all the fields ADR-275 refinement added.
- **No changes to the Reviewer's tool surface or persona prose.** The contract is unchanged; only the structural delivery for reactive triggers gets corrected.
- **No backwards-compatibility shim.** The pre-ADR-276 reactive context bag (without governance pre-load) is deleted in the same commit. Singular Implementation.

## 5. Implementation scope

- `api/services/reviewer_envelope.py` (new) — `load_reviewer_governance_envelope()` helper (~50 LOC)
- `api/routes/feed.py` — migrate addressed-trigger pre-load to use the helper (-15 / +2 LOC; net delete)
- `api/services/invocation_dispatcher.py::dispatch_recurrence` — call the helper, merge into context bag (~10 LOC)
- `api/test_adr276_reactive_envelope.py` — regression gate (~80 LOC, ~10 assertions)
- `docs/adr/ADR-276-reactive-trigger-envelope-governance-preload.md` — this file
- `docs/adr/ADR-275-introspection-cadence-reviewer-authored.md` — §5b status update ("ADR-276 implemented")
- `api/prompts/CHANGELOG.md` — `[2026.05.14.10]` entry
- `CLAUDE.md` — ADR-276 entry in summary

Net: ~150 LOC across 8 files. Atomic single commit. No new ADR concepts; this is the dev-sequence closer.

## 6. Empirical test plan (post-deploy)

The natural reactive-wake observation points (no manual triggering needed):

1. **13:00 UTC** — `pre-market-brief` recurrence fires (Reviewer-authored by run-2). Wakes Reviewer reactively with the brief prompt. We should see the Reviewer perceive `_preferences.yaml` + `_operator_profile.md` + `_performance.md` in its prompt (no ReadFile calls for these) and produce a brief that references operator-declared signals + current portfolio state.
2. **13:45 UTC** — `signal-evaluation` recurrence fires. Wakes Reviewer reactively with the signal-eval prompt. With governance + universe + operator profile pre-loaded, signals should be evaluable directly — no tool-call detour for substrate the prompt already cites. Item #3 either resolves (validates ADR-276 closed the downstream gap) or persists (validates the gap is in bundle prompt logic, not envelope delivery).
3. **21:00 UTC** — `outcome-reconciliation` fires post-close. Wakes Reviewer reactively with the reconciler prompt.

Capture for each fire:
- `workspace_file_versions` revisions in the next 5 minutes — should show fewer Reviewer tool-call reads on governance files
- `execution_events` row for the recurrence
- Any narrative entries or substrate writes the Reviewer produces
- Compare to the equivalent fires in run-2 (pre-ADR-276) to isolate the structural change

## 7. Status

After this commit lands, ADR-274 + ADR-275 + ADR-275 refinement + ADR-276 collectively close the dev sequence on FOUNDATIONS v8.5 Axiom 4 amendment + Derived Principle 18:

| ADR | What it shipped |
|---|---|
| ADR-274 | FOUNDATIONS v8.5 (Axiom 4 amendment + Derived Principle 18) + enabling primitives (Operating Context block + Schedule attribution + persona cadence-authoring section) |
| ADR-275 | Bundle thinning (7 judgment recurrences deleted) + `_preferences.yaml` operator-authored substrate |
| ADR-275 refinement | Addressed-trigger envelope pre-loads `_preferences.yaml` + AUTONOMY (audit-found gap) |
| **ADR-276** | **Reactive-trigger envelope pre-loads full governance + domain substrate via shared helper** |

The Reviewer perceives full governance substrate at every wake regardless of trigger shape (addressed | reactive | future trigger types). Derived Principle 18 lands operationally across the entire trigger surface.

The two remaining items from the run-2 observation (#2 `decisions.md` dual-writer race + #3 `signal-evaluation` empty signals/) are intentionally NOT bundled into this commit. #2 deserves its own discourse; #3 will be re-evaluated by the ADR-276 deployment's empirical test.
