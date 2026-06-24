# Envelope-collapse A/B probe — Arm B (stripped CC-shape) composes; the real lever is caching, not stripping

**Date**: 2026-06-24
**Hat**: B (external-developer / evaluation) — the gate for the envelope-collapse conviction doc (`docs/analysis/the-envelope-collapse-2026-06-24.md`).
**Subject**: does the agent compose/judge correctly when the wake envelope is stripped to the full CC-shape (governance-block + substrate-snapshot + ask + clock; everything else on demand), with `_TRIGGER_FRAMING` deleted?
**Verdict**: **Behavioral PASS — Arm B composed a real artifact from empty corpus AND read on demand (9 reads), on the bare imperative without the coaching scaffold.** But the headline finding is economic: **the strip is only +8% tokens because the envelope is mostly *legitimate governance* (the CLAUDE.md-analogue), not prosthetic. The real cost lever is CACHING the governance-block, not stripping it.**

---

## Method

Funded fresh-state `yarnnn-author` (U=`0b7a852d-…`, balance $58). A/B as an env toggle in `_build_user_message` (`YARNNN_ENVELOPE_ARM=B`) so A and B differ by exactly the strip — Arm A is byte-identical to production (151 insertions, 0 deletions; `git diff` confirms). Two phases:

- **Phase 1 (offline, free)**: render both envelopes for an identical context bag; measure token delta + governance survival.
- **Phase 2 (funded, live)**: fire the same producer recurrence through `_invoke_recurrence_wake` (production path; ask-builder converts the stored framing → imperative) under each arm, with the validated ADR-360 full-reset between arms (corpus content/profile/manifest deleted, persona working-memory wiped, wake_queue cleared, fresh unique slug).

Probe: `api/scripts/operator/probe_envelope_collapse_local.py`.

---

## Phase 1 — the strip is small because governance is the bulk

| | ~tokens | what it is |
|---|---|---|
| Arm A (full envelope) | ~19,400 | — |
| Arm B (stripped CC-shape) | ~17,800 | — |
| **Delta** | **~1,600 (+8%)** | `_TRIGGER_FRAMING` (~700) + mirror dumps (~900) |
| Governance-block (in BOTH) | ~16,000 | IDENTITY + principles + MANDATE + AUTONOMY + expected_output — the CLAUDE.md-analogue, correctly retained |

Governance-survival check: all governing headers present in Arm B (IDENTITY, principles, MANDATE, AUTONOMY, expected_output, the ask, substrate-snapshot). `_TRIGGER_FRAMING` coaching confirmed removed. The gitStatus-analogue snapshot rendered with real "what changed since last wake" paths (schedule_index, recent_execution, standing_intent, judgment_log).

**The premise correction**: the "20 sections → 3 items" framing implied a dramatic collapse. Measured, the envelope was never mostly prosthetic — it is mostly the **CLAUDE.md-analogue** (the authored governing files), which is exactly what CC keeps as standing context. The deletable prosthetics (`_TRIGGER_FRAMING` + mirror dumps) are real but small (~8%).

**The relocated lever**: the expensive thing is not the 8% prosthetic — it is that **~16k tokens of stable governance are rebuilt and re-sent UNCACHED on every wake.** CC caches `claudeMd`. We do not cache the governance-block. **Caching the governance-block (keyed by max governing-file `head_version_id`) is a far bigger cost win than the strip** — and it is an Anthropic prompt-cache breakpoint problem, not an envelope-shape problem.

---

## Phase 2 — Arm B composes on the bare imperative (the behavioral PASS)

Receipt-grounded from the revision stream (`workspace_file_versions`), the source of truth:

**Arm B (`probe-piece-b-…`, stripped envelope) — COMPOSED:**
- `05:08:41` — WriteFile `operation/authored/reviewer-installed-judgment-seat/content.md` + profile.md — **a real, on-thesis artifact composed from empty corpus** (slug drawn from the repo signal, the perception field).
- `05:08:53–05:09:33` — EditFile profile.md + `_signal.md` ×6 — updated signal/profile substrate.
- `05:09:13` — WriteFile standing_intent.md + judgment_log.md — **closed forward working-memory properly.**
- Loop summary: 20 actions, 11 writes, **9 reads** — on-demand reading worked; the snapshot scoped the reads (the agent fetched detail it needed rather than judging blind).

**Arm A (`probe-piece-a-…`, full envelope) — also composed, also hit the ceiling:**
- Ran a full 20-round loop, composed + attempted to ship, exhausted the 20-round budget without `ReturnVerdict`: `last_prose='Now update the prose section to reflect the successful ship:'` → returned `None` → recorded `failed` (the ADR-360 Stage-4 honest-failure path: no recovery net, runs out → `failed`, not a fabricated close).

**Both arms hit the 20-round ceiling without calling ReturnVerdict.** This is a *round-budget* property (composing a full piece + updating 4-5 substrate files in 20 rounds is tight), **NOT an envelope-shape property** — the control had it too. The strip neither caused nor worsened it.

### Probe-instrumentation bug (corrected)

The probe's summary reported `composed=False` / `write_paths=[None,…]`. This was a detection bug: the action dict keys tool args under `"input"` (path is `action["input"]["path"]`), not `"path"`. The revision stream (above) is the ground truth and shows the compose unambiguously. Arm A reported `n_actions:0` because it returned `None` (budget-exhausted), which carries no actions list — not because it did nothing. **The surface gate's `[FAIL]` was an artifact; the substrate receipts show the behavioral PASS.**

---

## The 3-part gate, re-applied against the receipts

1. **Behavioral (the ADR-360 gate)** — **PASS.** Arm B composed a real artifact from empty corpus on the bare imperative + snapshot, no `_TRIGGER_FRAMING` coaching. Never silently deferred; the ceiling-exhaustion (no ReturnVerdict) is the honest `failed` path, identical in the control.
2. **On-demand works** — **PASS.** 9 reads in Arm B; the snapshot scoped the reads correctly (the agent fetched detail it needed). The stripped envelope did not cause blind-on-partial-substrate judgment.
3. **Token delta** — **MODEST (+8%).** Real but small; the strip is not where the cost is.

---

## FOLLOW-ON (2026-06-24): the real lever IMPLEMENTED + PROVEN — governance caching

The premise correction said the cost lever is *caching* the ~16k-token governance block, not stripping it. That was implemented this session on the production path and **proven on a funded wake**.

**The change** (`api/agents/reviewer_agent.py`): the user message was a plain string (uncacheable — Anthropic prompt cache keys on rendered bytes, and a string `content` carries no `cache_control`). It now builds as **two content blocks**:
- **[0] governance prefix** (IDENTITY + principles + PRECEDENT + MANDATE + AUTONOMY + budget + expected_output + preferences + occupant + domain constants) — marked `cache_control: ephemeral`. The CLAUDE.md-analogue; stable until a governing file is revised.
- **[1] volatile suffix** (operating-context [the wake timestamp — the per-wake invalidator], wake-context, mirror heads, snapshot, standing-intent, the ask) — uncached. **Moved AFTER the governance breakpoint** so the timestamp never busts the governance cache (prefix-match invalidation).

`_partition_envelope` is the singular source; `_build_user_message_content` (blocks, production) and `_build_user_message` (string, Arm-B/fallback) both consume it. System prompt (1 breakpoint) + governance (1 breakpoint) = 2 of the 4-breakpoint budget.

**The proof** (`execution_events`, funded yarnnn-author U=`0b7a852d`):

| wake | when | `cache_create` | `cache_read` | uncached `input` |
|---|---|---|---|---|
| cron_tick (PRE-change) | 05:09 | **0** | 115,759 | **185,193** |
| substrate_event (PRE-change) | 05:10 | **0** | 99,222 | **174,378** |
| cron_tick (POST-change) | 05:23 | **48,471** | 243,799 | **110,315** |

Pre-change wakes wrote **zero** new cache (`cache_create=0`) — the governance-bearing user message was a string, re-billed at full `input` rate every round (input 174k–185k). Post-change: the governance prefix is **written to cache once** (`cache_create=48,471`, the round-1 write of system+governance) and **read on every subsequent round** (`cache_read=243,799`), and the full-rate uncached `input` dropped to **110,315 — a ~40% cut**. Cache reads cost ~0.1× base input; the ~48k cached prefix that previously cost full rate every round now costs ~10% on rounds 2..N and on subsequent wakes within the 5-min TTL.

**Verdict: the envelope-collapse arc's real win lands here.** The strip was a small correctness improvement; the caching is the cost lever, and it is implemented on the live path and proven. Probe: `api/scripts/operator/probe_governance_cache_local.py`.

**Substrate floor untouched** (ADR-209 write path byte-identical). The change is envelope-rendering only — content is identical to the pre-caching flat envelope; the sole structural move is operating-context + wake-context relocating from the message head to the volatile suffix so governance becomes a cacheable prefix.

---

## What this changes about the next move

- **Agent/system separation is MORE complete than assessed.** The wake is CC-shaped (ADR-360); the envelope, stripped, IS governance + snapshot + ask + clock — structurally the CC turn. The agent composes on it. The 8% is the only prosthetic.
- **The behavioral strip is a correctness win independent of the 8%.** Deleting `_TRIGGER_FRAMING`'s standing-state coaching (which fights the ask-shaped wake) is worth doing for coherence, not for tokens.
- **The real cost lever is governance-caching**, not stripping. Per-wake uncached re-send of ~16k stable tokens is the inefficiency. Implementing the prompt-cache breakpoint on the governance-block (cache key = max governing-file `head_version_id`) is the bigger win and the truer completion of "governance is the CLAUDE.md-analogue, cached like CC caches claudeMd."
- **A secondary finding worth noting (not this probe's subject): the 20-round ceiling is tight for compose+close.** Both arms maxed out. If compose-and-close is the expected owed-output behavior, the round budget for producer recurrences may warrant a look — separate from the envelope question.

---

## Receipts

| Claim | Receipt |
|---|---|
| Arm A byte-identical to prod | `git diff` reviewer_agent.py = 151 insertions, 0 deletions |
| Strip = +8% tokens | Phase-1 offline render: 19,422 → 17,834 tok |
| Governance is the bulk | IDENTITY (~2k) + principles (large) + MANDATE + AUTONOMY + expected_output ≈ 16k of 17.8k in Arm B |
| Arm B composed | `workspace_file_versions`: WriteFile `…/reviewer-installed-judgment-seat/content.md` @ 05:08:41, `reviewer:ai:reviewer-sonnet-v8` |
| Arm B read on demand | loop summary 9 reads; snapshot scoped reads |
| Both hit 20-round ceiling | log line 804: "no ReturnVerdict after 20 rounds … returns None → recorded failed" |
| `composed=False` was a probe bug | action dict keys path under `input.path`, probe checked `action.path` |

---

## Bottom line

The funded probe earned its dollar twice: it **confirmed the behavioral PASS** (Arm B composes on the stripped CC-shape envelope, reads on demand, no coaching needed — the ADR-360 axiom completes at the envelope) AND it **corrected the premise** (the envelope was never mostly prosthetic; governance is the legitimate bulk, and the real cost lever is *caching* the governance-block, not stripping it). The strip is worth landing as a correctness/coherence win (delete `_TRIGGER_FRAMING`, fold mirrors into the snapshot), but the bigger, separable win is the prompt-cache breakpoint on governance. Probe-before-canon held: the free Phase-1 relocated the lever before the funded run, and the funded run proved the behavior the strip was actually for.
