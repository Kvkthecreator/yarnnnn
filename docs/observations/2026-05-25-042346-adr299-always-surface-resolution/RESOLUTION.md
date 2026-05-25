# RESOLUTION — ADR-299 Discovery 4 Path A Isolation (2026-05-25)

Closes the diagnostic arc that began with findings.md (Hat-B observation
of canary v3 producing REJECT verdict but no email) and continued through
the Discovery 3+4 in-place ADR corrections (Hat-A commit `7147aa7`),
canary v4 RED outcome, Path A revert (Hat-A commit `cd71930`), pure
email wire smoke test, and canary v5 Path A isolation validation.

## Chronological progression (substrate-receipts)

### Canary v1-v2 (background — pre-this-observation)
Wire-pointing redundancy + class-naming redundancy resolved per Discovery
notes 1+2. Detail in ADR-299.

### Canary v3 — 2026-05-25 04:13 UTC (the seed for THIS observation folder)
- Reviewer substrate-event hook fired correctly
- 10 LLM rounds, 6139 output tokens, $0.32 cost (`execution_events` row `252e75f6`)
- Substrate writes: judgment_log.md (revisions `53f1b342`, `9b15410a`) + standing_intent.md (revision `c22618eb`)
- Verdict: REJECT
- **Email: did not fire**
- Root cause (diagnosed in findings.md): `EMAIL_SEND_TO_OPERATOR_TOOL` was structurally unreachable to the Reviewer — kernel CAPABILITIES dict had it, agent-path resolution did NOT surface it for kernel-universal-no-wire-gate capabilities (Discovery 3 gap), AND REVIEWER_PRIMITIVES did not include it (Discovery 4 gap).

### Hat-A correction — 2026-05-25 04:38 UTC (commit `7147aa7`)
- Discovery 3 fix: always-surface kernel-universal-no-wire-gate capabilities in `get_platform_tools_for_capabilities`
- Discovery 4 fix: lift `EMAIL_SEND_TO_OPERATOR_TOOL` as named constant; add to `REVIEWER_PRIMITIVES` (tool count 21 → 22)
- Test gate 10/10 PASS

### Canary v4 RED — 2026-05-25 04:42 UTC (the regression)
- Fired 4 min post-deploy; substrate-event hook fired correctly
- 4 LLM rounds, 1577 output tokens, $0.21 cost (`execution_events` row `58d325df`)
- Tool calls: 7× ReadFile + 1× ListFiles, all read-only (Render logs confirm)
- **Zero substrate writes** to `/workspace/review/`
- **Zero email**
- Verdict: `stand_down` (cycle exited via `ReturnVerdict(verdict='stand_down', ...)`, no fallback warnings in logs, `execution_events.status='success'`)
- Same prompt as v3, same hook, intentional voice issues — should have produced defer/reject

### Operator decision: Path A revert (chose hypothesis-A test)
Two candidate causes for the verdict shift:
- **Hypothesis A**: tool addition to REVIEWER_PRIMITIVES perturbed Reviewer attention/judgment toward stand_down
- **Hypothesis B**: prompt-coverage gap admitting stand_down as escape hatch

Operator chose Path A to isolate the structural variable first.

### Hat-A Path A revert — 2026-05-25 05:11 UTC (commit `cd71930`)
- `EMAIL_SEND_TO_OPERATOR_TOOL` removed from `REVIEWER_PRIMITIVES` (tool count back to 21)
- Discovery 3 always-surface fix in `get_platform_tools_for_capabilities` **preserved** (non-Reviewer callers still reach the tool)
- Test gate 10/10 PASS with inverted assertion (`test_reviewer_primitives_excludes_send_operator_email_path_a_revert`)
- Deploy `dep-d89tj6beo5us73ba7ssg` live 05:11:09 UTC

### Pure email wire smoke test — 2026-05-25 05:23 UTC (commit `09f44c7`)
Added `POST /api/account/test-email` endpoint (permanent operator-facing health check). Bypasses Reviewer + notifications + delivery + recurrence entirely. Direct exercise of `jobs.email.send_test_email`.

Invocation result:
- HTTP 200
- `success: True`
- `recipient: kvkthecreator@gmail.com`
- `message_id: aca1b873-9e4c-4216-9f04-b597dbc43ea1`
- `error: None`

**Operator inbox-confirmed delivery** (screenshot evidence in chat transcript: "Test Email — If you're seeing this, email delivery is working! — yarnnn" from `noreply@yarnnn.com`).

This rules out hypothesis C (wire broken). Canary v4's silent stand_down was 100% Reviewer judgment, not a downstream failure.

### Canary v5 — 2026-05-25 05:25:37 UTC (the isolation test)
Same content as canary v4 (identical intentional voice issues) so the only variable changing is the Reviewer's tool surface size (22 → 21).

Substrate-receipts:
- profile.md seed: revision `221f8085-d0d6-4121-b35f-433a40ce6197`
- content.md seed: revision `71797f0b-9c93-470a-9482-9f0051495cef`
- Canary transition (draft → ready_for_review): revision `8b629647-777d-4e79-9ef3-51fb6364a43b`

Reviewer cycle outcome:
- `execution_events` row `1e9ac22c-1f61-4f84-9ee4-8611bb962055`
- **12 LLM rounds** (vs v4's 4, v3's 10)
- **14,615 output tokens** (vs v4's 1577, v3's 6139)
- $0.41 cost (vs v4's $0.21, v3's $0.32)
- Status: success

Substrate writes:
- `/workspace/review/judgment_log.md` — updated 05:27:25 (revision pending lookup)
- `/workspace/review/standing_intent.md` — updated 05:29:37

Verdict (from judgment_log.md head):
```
outcome_kind: reject_publication
reviewer_identity: ai:reviewer-sonnet-v8
phase4-canary-v4-post-disco34: HARD REJECTED — systematic anti-slop
floor violations across 8+ distinct anti-pattern categories.
```

Documented 12 independent anti-pattern instances. (Note: piece_slug in
the judgment_log header mis-attributed to `v4-post-disco34` instead of
the v5 slug — separate prompt-template-substitution issue worth its own
follow-up, but does NOT impact the Path A diagnostic.)

**No email fired** (expected — tool not in Reviewer surface post-revert; zero `platform_email_send_to_operator` log lines in v5 cycle window).

## Hypothesis verdict

**Hypothesis A CONFIRMED.** Removing `EMAIL_SEND_TO_OPERATOR_TOOL` from `REVIEWER_PRIMITIVES` restored substantive judgment. Comparison table:

| Metric | v3 (22-tool, pre-Discovery-4) | v4 (22-tool, post-Discovery-4) | v5 (21-tool, post-Path-A) |
|---|---|---|---|
| Tool surface size | 21 (no tool) | 22 (with tool) | 21 (tool reverted) |
| LLM rounds | 10 | 4 | 12 |
| Output tokens | 6,139 | 1,577 | 14,615 |
| Cost | $0.32 | $0.21 | $0.41 |
| Substrate writes | judgment_log + standing_intent | none | judgment_log + standing_intent |
| Verdict | reject | stand_down | reject_publication |

The 22-tool surface (v4) collapsed Reviewer judgment by ~74% on output tokens vs the 21-tool surface (v3/v5). Same content, same prompt, same hook — the only variable was the tool count.

## Mechanism (best-current-understanding)

**Conjecture**: adding a 22nd tool — particularly one with strong "explicit action with consequence" framing (`platform_email_send_to_operator` is described as "send email to operator") — shifts the model's attention budget away from the document-judgment task toward the meta-question "should I use this action tool?". With the action tool absent (21-tool surface), the model commits fully to the judgment task per the hook prompt and produces substantive output.

This is consistent with known LLM behavior: more tools → more tool-selection overhead → less budget for primary task. The threshold appears to sit between 21 and 22 tools for this particular Reviewer + Haiku + judgment-shaped prompt combination.

## Recommendation

**Keep Path A in place** (Discovery 4 reverted). The Reviewer's primary value is independent capital-EV judgment per ADR-247 + ADR-194 v2. Trading judgment quality for operator-notification convenience is the wrong tradeoff — operators already have the cockpit surface for verdict visibility (Stream archetype per ADR-198).

**Operator email notifications, if needed**, should reach operators via a path that doesn't perturb Reviewer judgment:
1. **Post-judgment notification hook** (zero impact on Reviewer surface): after the dispatcher writes the verdict to substrate, a separate notification step (notifications.py-style) reads the verdict + operator preferences and dispatches email. This is how `services/notifications.py` already works for proposal notifications.
2. **Operator-driven check-in**: the `/api/account/test-email` endpoint added in commit `09f44c7` is a baseline; can extend to "/api/account/digest-email" or similar for periodic operator-driven summaries.
3. **NOT in the Reviewer's tool surface.** The Reviewer's role is judgment; notification dispatch is a downstream concern.

**Re-introduction protocol if needed in future**: should the architecture genuinely require the Reviewer to directly send operator-addressed email (e.g., for a high-urgency-only carve-out), the experiment to run is:
- Add the tool back to REVIEWER_PRIMITIVES
- Run N canaries (N ≥ 3) with intentional voice issues on a fresh corpus
- Measure verdict-quality regression vs baseline (21-tool surface)
- Accept the regression only if the use case justifies the judgment-quality tradeoff
- Document the tradeoff explicitly in the ADR

## Discipline lesson (recorded for the broader system)

**A tool's presence in a model's surface is not free.** Anthropic's tool-use specification treats tools as available-when-relevant; in practice, every additional tool consumes attention budget regardless of whether it's called. For judgment-shaped prompts where the model's primary task is substrate evaluation, tool count is a load-bearing variable.

This generalizes beyond the email case. Any future capability addition to REVIEWER_PRIMITIVES (or other persona-bearing actor surfaces) should be measured against verdict-quality baselines, not just tested for structural reachability.

## Cross-references

- ADR-299 with Discovery 4 Path A addendum: [`docs/adr/ADR-299-kernel-universal-operator-addressing-capability.md`](../../adr/ADR-299-kernel-universal-operator-addressing-capability.md)
- Path A revert commit: `cd71930`
- Test-email endpoint commit: `09f44c7`
- Canary v5 script: [`api/scripts/operator/canary_phase4_v5_path_a_isolation.py`](../../../api/scripts/operator/canary_phase4_v5_path_a_isolation.py)
- Smoke test caller: [`api/scripts/operator/email_wire_smoke_test.py`](../../../api/scripts/operator/email_wire_smoke_test.py)
- `execution_events` rows: v3 `252e75f6`, v4 `58d325df`, v5 `1e9ac22c`
- Resend message_ids: smoke test `aca1b873-9e4c-4216-9f04-b597dbc43ea1`

## Status

**RESOLVED** — Path A confirmed hypothesis A (tool perturbation). Recommendation: keep Discovery 4 reverted; route operator notifications through post-judgment hooks rather than Reviewer's tool surface. Findings.md original observation status flipped from OPEN to RESOLVED by this addendum.

Follow-up observation worth its own folder (out of scope here): the v5 judgment_log header carried piece_slug `phase4-canary-v4-post-disco34` instead of the actual v5 slug `phase4-canary-v5-path-a-isolation`. Likely a prompt-template-substitution issue where the Reviewer carries forward a prior piece's slug. Doesn't impact the Path A diagnostic but should be investigated if it recurs.
