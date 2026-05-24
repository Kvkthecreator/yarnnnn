# RESOLUTION — ADR-299 wire redundancy correction (mostly) closed

**Hat**: External Developer of the System (Hat B). Closes the observation opened by [`findings.md`](findings.md), with one deferred follow-up.

**Status**: ✓ Hat-A wire correction landed in commit `f1f77e6` (Commit 2a). One prose follow-up (Commit 2b) deferred to avoid sweep-up with a parallel session's ADR-301 work in the same file.

## What Hat-A delivered (Commit 2a, `f1f77e6`)

Five of the six findings-recommendations from `findings.md` §"Recommendation (Hat-A correction — Path X)" landed atomically:

| Recommendation | Delivered | Verification |
|---|---|---|
| 1. `_handle_email_tool` send_to_operator branch rewired to `api/jobs/email.py::send_email` | ✓ Early-return at top of function; uses `system_send_email` alias for system Resend wire; preserves addressee resolution + structural pin discipline | `test_handler_refuses_llm_supplied_addressee_fields` (extended to require `system_send_email` import + `to=operator_email` shape) |
| 2. `CAPABILITIES["send_operator_email"]` drop wire-gate | ✓ `runtime: "kernel"`, `platform_connection_requirement: None` | `test_send_operator_email_in_capabilities_dict` (extended to assert both) |
| 3. Resolution-path rework for no-wire-gate kernel capabilities | ✓ `get_platform_tools_for_capabilities` extended with kernel CAPABILITIES dict no-wire-gate branch; `send_operator_email` removed from `CAPABILITY_PROVIDER_MAP` | `test_resolution_send_operator_email_not_in_provider_map` + `test_resolution_surfaces_send_operator_email_unconditionally` |
| 4. Phase 3 persona-frame wire-gate clause deletion | ⏳ **Deferred to Commit 2b** — sweep-up risk with parallel ADR-301 work (see "Sweep-up avoidance" below) | n/a until Commit 2b lands |
| 5. Regression test updates | ✓ 9/9 PASS post-correction (one assertion replaced, one new assertion added, runtime + wire-gate assertions corrected) | `python api/test_adr299_kernel_universal_capability.py` |
| 6. ADR-299 Discovery note 2 | ✓ In-place per Singular Implementation; documents the wire redundancy + correction + recursive discipline lesson | ADR §"Discovery note 2 — wire redundancy correction (2026-05-24)" |

Sibling reviewer-formalization gate also remained 9/9 PASS — no regression in adjacent canon.

## Sweep-up avoidance — Commit 2b deferral

The Phase 3 persona-frame wire-gate clause deletion (1 paragraph swap in `api/agents/reviewer_agent.py::_PERSONA_FRAME`) was completed in the working tree but **not included in Commit 2a** because of a detected sweep-up risk.

### What I observed

When I prepared the staged set for Commit 2a (`git diff --cached --stat`), the `reviewer_agent.py` diff showed ~180 line changes when my edit was only ~7 lines (one paragraph swap). Inspection revealed the file's working-tree state contained:
- My intended change: delete the "wire-gate handling" paragraph + replace with single-paragraph system-wire note
- **Parallel-session work**: new `ReviewerContext` TypedDict fields (`schedule_index_md`, `recent_execution_md` per ADR-301), and a substantive refactor relocating `build_operating_context_block` to `services/reviewer_envelope.py`

The parallel session is mid-stream on ADR-301 (Reviewer Pulse Envelope) work — visible in working-tree state: 9 modified files spanning `kernel_mirrors.py`, `unified_scheduler.py`, `wake.py`, `wake_drainer.py`, `pace.py`, `primitives/registry.py`, `reviewer_envelope.py`, `workspace_paths.py`, `reviewer_agent.py` + new files `kernel_mirrors.py`, `mirror_recent_execution.py`, `mirror_schedule_index.py`, `ADR-301-reviewer-pulse-envelope.md`.

If I'd included reviewer_agent.py in Commit 2a, the commit would have swept up all parallel-session ADR-301 changes to that file — same shape as the 2026-05-22 sweep-up incident documented in `docs/observations/2026-05-22-043009-reviewer-formalization-audit/RESOLUTION.md`, but in reverse (my commit sweeping up theirs instead of theirs sweeping up mine).

### Discipline applied

Per CLAUDE.md §"The Two Hats" + the verify-staged-set discipline that the morning's sweep-up incident produced:
1. **Detected the sweep-up risk pre-commit** via `git diff --cached --stat` showing unexpected scope
2. **Scoped Commit 2a to exclude `reviewer_agent.py`** — load-bearing wire correction (handler + CAPABILITIES + resolution) shipped without the orthogonal prose update
3. **Confirmed the scoping is functionally safe**: regression gate is wire-correction-focused, not persona-frame-content-focused, so 9/9 PASS without the persona-frame edit
4. **Documented the deferral in Commit 2a's message + CHANGELOG entry `[2026.05.24.3]`** so the prose-update intent is visible in the audit trail even before Commit 2b lands

### Commit 2b plan

After the parallel ADR-301 session commits its `reviewer_agent.py` changes to main, Commit 2b applies just my paragraph swap as a clean diff. Three options for executing:

- **(a) Operator-triggered**: I run Commit 2b when prompted, after observing parallel-session reviewer_agent.py changes have landed
- **(b) Self-driven follow-up**: in a future session that touches reviewer_agent.py for any reason, the paragraph swap can land alongside whatever change motivates that session
- **(c) Conditional**: if the parallel session's ADR-301 work ends up restructuring the `_PERSONA_FRAME` operator_notifications awareness block independently, the wire-gate clause deletion may happen organically without needing a dedicated commit

The deferral is **prose-only**. The wire correction is functional and shipped; the persona-frame clause currently teaches the Reviewer a wire-gate-detection discipline that won't fire (the tool is always available). No functional bug from the delay; the Reviewer would just be prepared to note a substrate-vs-wire drift that the post-correction architecture never produces.

## Validation gates (both green post-correction)

```
$ python api/test_adr299_kernel_universal_capability.py
  PASS  test_send_operator_email_in_capabilities_dict
  PASS  test_kernel_capabilities_module_does_not_exist
  PASS  test_email_tools_exposes_send_to_operator_with_constrained_schema
  PASS  test_handler_refuses_llm_supplied_addressee_fields
  PASS  test_resolution_send_operator_email_not_in_provider_map
  PASS  test_resolution_surfaces_send_operator_email_unconditionally
  PASS  test_resolution_does_not_have_parallel_kernel_universal_precheck
  PASS  test_bundle_capability_resolution_not_regressed
  PASS  test_addressee_class_distinguishes_operator_from_audience

9/9 tests passed

$ python api/test_reviewer_formalization.py
  ...
9/9 tests passed
```

## Net diff summary (Commit 2a)

- `api/services/platform_tools.py`: +135 / -95 net (handler refactor + resolution-path extension + CAPABILITY_PROVIDER_MAP removal)
- `api/services/orchestration.py`: +20 / -6 net (CAPABILITIES dict entry runtime + wire-gate changes + commentary)
- `api/test_adr299_kernel_universal_capability.py`: +88 / -31 net (assertions corrected + new resolution test)
- `docs/adr/ADR-299-...md`: +47 / -4 net (Discovery note 2 in-place)
- `api/prompts/CHANGELOG.md`: +42 net (entry `[2026.05.24.3]` documenting deferred persona-frame work)
- `api/agents/reviewer_agent.py`: **EXCLUDED from this commit** (sweep-up avoidance; persona-frame paragraph swap pending Commit 2b)

**Net Commit 2a**: +359 / -109 = +250 LOC, 5 files. Singular Implementation honored (one handler shape, one resolution function, one CAPABILITIES dict entry).

## What this confirms about the broader system

YARNNN had **two correctly-designed Resend wires** all along:
- **System-keyed** (`api/jobs/email.py` + `RESEND_API_KEY` env var) for operator-addressing (ADR-040 notifications, ADR-202 daily-update pointer emails)
- **Per-user OAuth** (`api/integrations/core/resend_client.py` + `platform_connections.platform='email'`) for audience-addressing (ADR-192 Phase 4 commerce operator-to-customer sends)

The architectural design was honest. ADR-299 Phase 1 + yesterday's class-naming correction (`50df8b4`) both pointed the operator-addressing capability at the audience-addressing wire — twice — because each correction verified the layer it was correcting but not the wire underneath. **The system itself was correct; the corrections-around-it had a structural blindspot.**

This is the third architectural-discipline lesson today's session has surfaced (Discovery note 1, this Discovery note 2, the wire-vs-class orthogonality codified in the regression gate). All three are now in the audit trail for future-Claude reference.

## Discipline takeaways

1. **When correcting a class-naming redundancy, also verify the wire each class member points at.** Class-naming and wire-pointing are orthogonal axes; correcting one doesn't guarantee the other is correct.

2. **The verify-staged-set discipline (`git diff --cached --stat` between `git add` and `git commit`) caught a second sweep-up risk this session** — same shape as the discipline this morning recorded, applied successfully in real-time. The pattern is now operational.

3. **When a parallel session is mid-stream on a file you also edited, prefer scope-narrow commits over file-aggregating ones.** My handler/CAPABILITIES/resolution/test/ADR changes were the load-bearing wire correction; the persona-frame paragraph swap is orthogonal prose cleanup. Splitting them across two commits is honest about what's actually load-bearing.

4. **In-place ADR Discovery notes can stack** — ADR-283 has two Discovery notes; ADR-299 now has two Discovery notes. Each in-place patch is a discipline marker that the canonical text was correctable rather than wholesale-superseded.

## Cross-references

- Hat-B finding: [`findings.md`](findings.md)
- Hat-A correction commit: `f1f77e6` ("fix(adr-299): rewire send_operator_email to system Resend wire")
- Hat-B observation commit: `0f80355` ("docs(observations): ADR-299 wire redundancy — second-order finding")
- Yesterday's predecessor correction: [`docs/observations/2026-05-24-042952-adr299-class-naming-redundancy/`](../2026-05-24-042952-adr299-class-naming-redundancy/) — class-naming redundancy that this finding's wire redundancy was orthogonal to
- The 2026-05-22 sweep-up incident discipline reference: [`docs/observations/2026-05-22-043009-reviewer-formalization-audit/RESOLUTION.md`](../2026-05-22-043009-reviewer-formalization-audit/RESOLUTION.md) — the original verify-staged-set lesson, applied here in real-time
- ADR-299 (post-Discovery-note-2): [`docs/adr/ADR-299-kernel-universal-operator-addressing-capability.md`](../../adr/ADR-299-kernel-universal-operator-addressing-capability.md)
- System Resend wire: `api/jobs/email.py::send_email` (uses `RESEND_API_KEY` env var)
- Per-user Resend wire: `api/integrations/core/resend_client.py` (unchanged; still serves `platform_email_send` audience-addressing surface)
- Regression gate: `api/test_adr299_kernel_universal_capability.py` (9/9 PASS, includes new test for kernel-CAPABILITIES-dict no-wire-gate branch)

## Status

**Mostly closed.** The wire correction is functional and shipped. One prose follow-up (Commit 2b: persona-frame wire-gate clause deletion) is deferred to avoid sweep-up with parallel ADR-301 work in the same file; my paragraph swap remains in working-tree state ready to commit when the parallel session's reviewer_agent.py changes land on main. No functional bug from the delay; the Reviewer's behavior post-correction is correct regardless of whether the persona-frame still teaches the (now non-firing) wire-gate-detection discipline.
