# 2026-04-29 — Post-refactor-wave E2E observation: alpha-trader-2 steady state

> **Persona**: alpha-trader-2 (`user_id=29a74c63-0c9c-4998-b8bb-56dd0d810a4e`, `workspace_id=68c0eabc-efa4-45cb-87da-8d14e5a979c1`)
> **Posture**: Read-only API probes against live prod state; **no chat-initiated invocation, no proposal emission, no AUTONOMY change** — alpha-trader-2 was already in steady state with 9 active recurrences when this run executed.
> **Operator (this run)**: Claude (builder seat — running Pass 3 of the 4-pass alpha-doc refresh against post-ADR-227/228/230/231/233/235/237/238/239 substrate)
> **Scope**: validate that the ADRs that landed since 2026-04-26 (the last alpha-doc touch) are wired in production AND identify the highest-confidence breakage to write up before Pass 4 rewrite.

---

## Outcome: substrate is clean, surfaces are wired, two real bugs surfaced

After 2 weeks of substrate-dissolution refactors, alpha-trader-2 remains operational. All 9 declared recurrences are firing on schedule against natural-home substrate per ADR-231 D2. The cockpit four-face composition tree per ADR-228 returns 200 with active bundle metadata. Reviewer pseudo-agent synthesis per ADR-214 works. URL flip per ADR-231 P3.8 is live (`/api/recurrences` → 200, `/api/tasks` → 404).

Two real bugs identified — both write-shape contract violations. One affects 2 of 4 back-office executors silently; one is operator-facing and would block any new operator running the harness.

---

## What got exercised (read-only, no state mutation)

| Layer | Probe | Status |
|---|---|---|
| Persona invariants | `verify.py --all` post-Pass 2 re-baseline | ✅ alpha-trader 32/32 + alpha-trader-2 31/31 + alpha-commerce 4/7 (3 expected: bundle deferred) |
| URL flip (ADR-231 P3.8) | `GET /api/recurrences` | ✅ 200, full recurrence list returned |
| URL flip cleanup | `GET /api/tasks` | ✅ 404 |
| Workspace file read | `GET /api/workspace/file?path=/workspace/context/_shared/MANDATE.md` | ✅ 200, content returned |
| Workspace file read (no leading slash) | `GET /api/workspace/file?path=context/_shared/MANDATE.md` | ❌ 404 — see Bug 2 |
| Cockpit nav | `GET /api/workspace/nav` | ✅ 200 |
| Compositor (ADR-225) | `GET /api/programs/surfaces` | ✅ 200, returns `active_bundles[0]={slug:"alpha-trader", current_phase:"observation"}` with full 5-phase map |
| Cockpit money-truth face (ADR-228) | `GET /api/cockpit/money-truth/{workspace_id}` | ⚠️ 404 — expected; ADR-228 Commit 3 explicitly deferred |
| Agents listing (ADR-214) | `GET /api/agents` | ✅ 200; first row `id="reviewer"`, `agent_class="reviewer"` (synthesis works) |
| Recurrence executors (live runs) | Recent session_messages for live session | ✅ pre-market-brief-2 wrote `/workspace/reports/pre-market-brief-2/2026-04-29T0815/output.md` (165s, 5 tool rounds) ✅ track-universe-2 wrote `/workspace/context/trading/...` (165s, 5 tool rounds) ❌ reviewer_calibration + outcome_reconciliation both errored "invalid shape" — see Bug 1 |

---

## Bug 1 — back-office executor return-shape contract drift (A — system)

**Severity**: silent failure on 2 of 4 back-office executors. Affects every workspace.

**Symptom**: `system` role messages in chat session show:
```
executor services.back_office.reviewer_calibration returned invalid shape (expected dict with 'output_markdown')
executor services.back_office.outcome_reconciliation returned invalid shape (expected dict with 'output_markdown')
```

**Root cause**: `services/invocation_dispatcher.py:646-649` enforces a contract that the result dict from a back-office executor must contain `output_markdown`. Compliant executors (4 of 6):
- [agent_hygiene.py:201](api/services/back_office/agent_hygiene.py#L201) — returns `{"output_markdown": ..., "actions_taken": ...}`
- [narrative_digest.py:251](api/services/back_office/narrative_digest.py#L251) — returns `{"output_markdown": ..., "actions_taken": ...}`
- [workspace_cleanup.py:112](api/services/back_office/workspace_cleanup.py#L112) — returns `{"output_markdown": ..., "actions_taken": ...}`
- [reviewer_reflection.py:473](api/services/back_office/reviewer_reflection.py#L473) — returns `{"output_markdown": ..., "actions_taken": ...}`

Non-compliant executors (2 of 6):
- [reviewer_calibration.py:96](api/services/back_office/reviewer_calibration.py#L96) — returns `{"content": ..., "structured": ...}`
- [outcome_reconciliation.py:111](api/services/back_office/outcome_reconciliation.py#L111) — returns `{"content": ..., "structured": ...}`

The drift likely happened during ADR-231 Phase 3.7 atomic deletion — the dispatcher contract was canonized while these two executors were left on the older return shape. No CI test covers the return-shape contract.

**Impact**:
- `_performance.md` is not getting refreshed by `outcome_reconciliation` — money-truth substrate goes stale.
- `decisions.md` calibration aggregation is not running — Reviewer development trajectory data missing.
- Both failures are silent at the operator layer (the dispatcher logs but doesn't surface to UI).

**Proposed fix** (one-line per file): rename the return-dict keys to match the dispatcher contract:

```python
# reviewer_calibration.py:96
return {
    "output_markdown": _render_report(...),   # was "content"
    "actions_taken": {                         # was "structured"
        "decisions_parsed": len(decisions),
        ...
    },
}
```

```python
# outcome_reconciliation.py:111
return {
    "output_markdown": "\n".join(report_lines),   # was "content"
    "actions_taken": {                             # was "structured"
        "total_appended": total_appended,
        ...
    },
}
```

Also: add a regression test asserting all 6 back-office executor `run()` functions return a dict with `output_markdown` key. The contract belongs in `services/invocation_dispatcher.py` next to the validator (line 646), with executors importing the type alias.

**Tag**: A (system) — substrate-pipeline integration gap from ADR-231 P3.7 atomic refactor.

---

## Bug 2 — `/api/workspace/file` requires leading slash, no normalization (B — product)

**Severity**: low-frequency operator-facing surprise. Affects anyone (KVK, Claude-on-behalf, future MCP callers) calling the API directly.

**Symptom**:
- `GET /api/workspace/file?path=/workspace/context/_shared/MANDATE.md` → 200 ✅
- `GET /api/workspace/file?path=context/_shared/MANDATE.md` → 404 ❌

The substrate file is identical in both cases — `workspace_files.path` always starts with `/workspace/`. The API route does an exact-match lookup without normalizing the leading slash.

**Why this is a small but real friction**: post-ADR-235, `WriteFile(scope="workspace", path="context/_shared/MANDATE.md")` (without leading `/workspace/` prefix — that's what `scope="workspace"` adds) is the canonical write shape. So a caller reading-back-what-they-wrote gets a 404. This is the kind of asymmetry that makes a careful operator distrust the API.

**Proposed fix**: normalize the path in `routes/workspace.py::get_file` — if `path` does not start with `/`, prepend `/workspace/`. Match the same normalization the WriteFile path does. Document the canonical caller shape.

**Tag**: B (product) — API ergonomic asymmetry, not a substrate bug.

---

## What this run does NOT exercise (deferred to dynamic E2E)

- Chat-initiated invocation against alpha-trader-2 (no live YARNNN turn taken, no message posted to session).
- Mandate hard-gate verification (`ManageRecurrence(create)` pre-mandate). The persona is post-mandate; would need a fresh workspace.
- Capability-gate ADR-227 fix (`platform_trading_*` tools showing up on Tracker when recurrence declares `read_trading`). Would require reading the actual tool surface from a live agent run prompt.
- AI Reviewer reactive dispatch (ADR-194 v2 Phase 3). Would require an `action_proposals` row to fire.
- AUTONOMY chip rendering (ADR-238) — backend AUTONOMY.md exists; FE consumption is a separate FE-side test.

These belong in the **next** observation run, after Pass 4 rewrites the playbook around the dynamic E2E shape.

---

## Implication for Pass 4 (playbook rewrite)

The static substrate + URL surface is healthier than I expected. Two bugs surfaced (one substrate, one API ergonomic), neither blocking. The playbook §3A.5 task list and §6 daily-rhythm flow translate cleanly to recurrence-declaration vocabulary because the **slugs and behaviors are preserved** — only the underlying primitive names + URL paths shifted.

Pass 4 can therefore be **scoped narrower than originally planned**: vocabulary alignment in §3A.5 + §6 + a new §3A.5b documenting the natural-home substrate paths so an operator reading the playbook can find their substrate via cockpit Context surface. No structural rewrite required.

---

## Outstanding questions for KVK

1. **Bug 1 fix** — ship as a separate commit before Pass 4, or fold into a "pre-Pass 4 hardening" commit? My recommendation: separate commit, ADR-231-followup, because two of YARNNN's claimed-canonical back-office executors are silently broken.
2. **Bug 2 fix** — same question. Lower stakes but same answer: separate commit.
3. **alpha-commerce activation** — `activate_persona.py --persona alpha-commerce` has never been run against KVK's commerce workspace. The bundle is `status: deferred` per ADR-224, so this isn't urgent, but it would let the cockpit four-face Money-Truth face actually surface revenue data. Decide: defer to Phase 1 of trader, or activate now to test the "second program in same operator" path?

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-29 | v1 — Initial observation. Pass 3 of 4-pass alpha-doc refresh against post-ADR-231/235 substrate. |
