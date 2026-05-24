# RESOLUTION — ADR-299 architectural-class-naming redundancy closed

**Hat**: External Developer of the System (Hat B). Closes the observation opened by [`findings.md`](findings.md).

**Status**: ✓ Hat-A correction landed cleanly in commit `50df8b4`.

## What Hat-A delivered

All 6 recommendations from `findings.md` §"Recommendation (Hat-A correction)" landed atomically in one commit:

| Recommendation | Delivered | Verification |
|---|---|---|
| 1. Delete `api/services/kernel_capabilities.py` | ✓ | `git show 50df8b4 --stat` shows `delete mode 100644 api/services/kernel_capabilities.py` (-169 LOC) |
| 2. Add `send_operator_email` to `CAPABILITIES` dict with `addressee_class: "operator"` field | ✓ | `services/orchestration.py:1219-1230` carries the new entry; test `test_send_operator_email_in_capabilities_dict` validates shape |
| 3. Revert parallel kernel-universal pre-check in `get_platform_tools_for_capabilities` | ✓ | Function returns to pre-Phase-1 shape; test `test_resolution_does_not_have_parallel_kernel_universal_precheck` enforces non-regression |
| 4. Keep tool definition + handler + structural pin | ✓ | All three layers preserved per Phase 1 (commit `3f0cabb`); none touched in correction |
| 5. Amend ADR-299 with Discovery note + reframe class | ✓ | ADR now opens "Operator-Addressing Capability"; Discovery note section ratifies the reframe + names the discipline lesson |
| 6. Update regression test to corrected shape | ✓ | Test rewritten with 8 assertions covering corrected shape; 8/8 PASS |

## Validation gates (both green post-correction)

```
$ python api/test_adr299_kernel_universal_capability.py
  PASS  test_send_operator_email_in_capabilities_dict
  PASS  test_kernel_capabilities_module_does_not_exist
  PASS  test_email_tools_exposes_send_to_operator_with_constrained_schema
  PASS  test_handler_refuses_llm_supplied_addressee_fields
  PASS  test_resolution_wires_send_operator_email_through_existing_path
  PASS  test_resolution_does_not_have_parallel_kernel_universal_precheck
  PASS  test_bundle_capability_resolution_not_regressed
  PASS  test_addressee_class_distinguishes_operator_from_audience

8/8 tests passed

$ python api/test_reviewer_formalization.py
  ...
8/8 tests passed
```

No regression in adjacent canon. The reviewer-formalization gate from this morning's Variant F canonization passes unchanged, confirming the correction didn't touch unrelated surfaces.

## Net diff summary

- **-169 LOC**: `api/services/kernel_capabilities.py` deleted (parallel registry)
- **+15 LOC**: `services/orchestration.py` (send_operator_email entry in CAPABILITIES dict)
- **+11 LOC / -1 LOC**: `services/platform_tools.py` (CAPABILITY_PROVIDER_MAP + PLATFORM_TOOLS_BY_CAPABILITY wiring; parallel pre-check removed)
- **~352 LOC rewritten / -302**: regression test rewritten to assert corrected shape
- **+34 LOC**: ADR-299 Discovery note + status update + cross-reference

**Net**: -168 LOC. The correction is a Singular Implementation deletion (one registry instead of two; one resolution path instead of two; one test shape instead of two layered conditions).

## What the correction did NOT touch

The genuinely-new-and-correct components from Phase 1 (commit `3f0cabb`) survive intact:

- `platform_email_send_to_operator` tool definition in `EMAIL_TOOLS` (constrained schema, no addressee fields exposed to LLM)
- `send_to_operator` branch in `_handle_email_tool` (resolves operator email via `get_user_email` at send-time, refuses LLM-supplied addressee fields with clear errors, pins `Resend.send(to=[operator_email])`)
- All four out-of-scope commitments (D7): no audience-bearing email, no SMS/push, no new email provider, no AUTONOMY routing change

These are load-bearing for the operator-addressing-capability contract and have no redundancy with existing code.

## Discipline takeaways (named for future-Claude reference)

1. **When proposing a new architectural class, the first check is whether an existing class has space for a new field that captures the genuine novelty.** If yes, prefer the new field over the new class. New classes are expensive (parallel registries, parallel resolution paths, doc churn); new fields are cheap (additive metadata on existing entries). The corrected ADR-299 captures the novelty (`addressee_class: "operator"`) as a single new field on the existing `CAPABILITIES` dict — not as a parallel `KERNEL_UNIVERSAL_CAPABILITIES` registry.

2. **Delegate research to subagents, but verify load-bearing facts before designing on top of them.** The pre-ADR-299 research agent reported "no explicit `CAPABILITIES = {} dict currently visible" — incorrect. Had I personally grepped for `^CAPABILITIES\s*=` in `orchestration.py` before drafting D5, the redundancy would have been visible up front and the parallel-registry path would never have been proposed.

3. **In-place ADR amendments via Discovery notes (per ADR-283 + Singular Implementation) are the right shape for correcting drafting errors caught within days of shipping.** The corrected text IS the ADR; no v1/v2 split. The Discovery note explains the reframe so future readers understand why the ADR's body says what it says.

4. **The three-commit cross-hat shape (Hat-B observation → Hat-A correction → Hat-B resolution) is fast for small + obvious + in-canon-precedented corrections.** Total session time for this correction: ~45 minutes. The discipline holds because the commit boundaries preserve the audit trail (operator can see findings.md surfaced the bug, Hat-A commit landed the fix, RESOLUTION.md confirms — even though all three landed in one session).

## What this confirms about the broader system

The `CAPABILITIES` dict + `_resolve_capability` + `CAPABILITY_PROVIDER_MAP` resolution path (shipped pre-ADR-299) **was already correctly designed** for capabilities that operate across all bundle archetypes. The kernel/bundle boundary (ADR-224) was the structural commitment; capabilities like `summarize`, `web_search`, `chart`, etc. have been kernel-universal-shaped since they shipped. The architectural class "operator-addressing capability" is a new *member* of an existing pattern, not a new pattern.

## Cross-references

- Hat-B finding: [`findings.md`](findings.md)
- Hat-A correction commit: `50df8b4` ("fix(adr-299): reframe class as 'operator-addressing', delete parallel registry")
- Hat-B observation commit: `aead8bc` ("docs(observations): ADR-299 architectural-class-naming redundancy")
- ADR-299 (post-Discovery-note): [`docs/adr/ADR-299-kernel-universal-operator-addressing-capability.md`](../../adr/ADR-299-kernel-universal-operator-addressing-capability.md) — note the title now reads "Operator-Addressing Capability"
- Existing CAPABILITIES dict: `api/services/orchestration.py:1129`
- Regression gate: `api/test_adr299_kernel_universal_capability.py` (8/8 PASS)
- Phase 1 commit that introduced the redundancy: `3f0cabb` (preserves genuinely-new-and-correct components: tool + handler + structural pin; the rest was redundant + corrected here)
- Companion ADR pattern (ADR-283 in-place Discovery notes): [`docs/adr/ADR-283-alpha-author-bundle.md`](../../adr/ADR-283-alpha-author-bundle.md) §"Discovery note" + §"Discovery note 2"

## Status

**Closed.** ADR-299's architectural-class framing now matches the existing pattern (one capability registry, one resolution path, one tool definition, one structural-pin enforcement). The operator-addressing capability class is correctly named, correctly housed, and correctly tested. The L6 capital-execution branch on alpha-author still has a clear path forward via Phases 2-4 of ADR-299's deferred roadmap.
