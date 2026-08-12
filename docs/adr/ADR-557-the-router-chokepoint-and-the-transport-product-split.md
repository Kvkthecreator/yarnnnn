# ADR-557 — The router chokepoint, and the transport/product split

> **Status**: **Accepted + Implemented** (2026-08-12, operator-ratified). The flag is enforced in the transport, `lanes_enabled()` separates the product fact from the infra fact, radar's missing guard is closed, and ADR-556's app misclassification is corrected. Gate `api/test_adr557_router_hardening.py` 18/18 with four falsifiers verified red.
> **Date**: 2026-08-12
> **Authors**: KVK (operator) + Claude (collaborator)
> **Dimensional classification** (Axiom 0): **Mechanism** (Axiom 5). One flag was answering two questions; one guard existed only as a convention callers had to remember.

**Amends**:
- [ADR-556](ADR-556-systematic-calls-and-the-model-selection-boundary.md) **D1** — **corrects a misclassification**. ADR-556's population table implied radar and IMAGES were systematic because their engine is not member-chosen. They are **user-facing apps** (ADR-467 residency). The correct rule is §4: *an app's engine follows its RESIDENT* — which is neither machinery nor a free member choice, and is the open Phase-2 question.
- [ADR-408](ADR-408-the-coworking-contract-and-the-three-ai-altitudes.md) **D4** / [ADR-411](ADR-411-chat-lanes-and-the-lane-tool-surface.md) — `MODEL_ROUTER_ENABLED` is narrowed to the transport fact; the lane surface moves to `lanes_enabled()`.

**Preserves**: [ADR-439](ADR-439-byok-key-scope-and-the-enterprise-tier-gate.md) §4 (unpriced models never route — its ordering check is repaired, not relaxed), [ADR-396](ADR-396-the-pricing-model-type-b-subscription-over-the-metered-balance.md) (one meter), [ADR-463](ADR-463-capability-not-vendor-the-model-agnostic-carve.md) D3 (the steward never routes).

---

## 1. Context — the operator's question

After ADR-556 separated systematic from user-facing model *selection*, the operator asked:

> "the model router, isn't that related to phase 2 since system level is now tracked separately? is my understanding correct? because if so, the phase 2 can be split in full for discourse to hardening and implementation"

Checked against the code, the understanding is **right in direction and the split is not clean**: `route_completion` has six callers straddling both populations. The router is shared **transport**, not a Phase-2-only concern — which is exactly why it needed hardening *before* the product discourse, not as part of it.

## 2. D1 — The flag is enforced in the TRANSPORT, not at the call sites

`route_completion` never consulted `model_router_enabled()`. The flag was a **convention every caller had to remember**. Four of five remembered. `services/radar.py` did not.

**The consequence was measured, not reasoned.** With `MODEL_ROUTER_ENABLED` unset, a radar derive call **succeeded** — it went out to Gemini over the network on whatever key was in env. A flag meant to keep routing dark did not keep it dark; it only kept it dark where a caller had opted in.

The fix is the third instance of a recorded lesson (`feedback_guard_at_chokepoint_not_call_sites`): `_assert_router_enabled()` runs at the top of both `route_completion` and `route_completion_stream`, **before the lazy litellm import**, raising a distinct `RouterDisabled`.

**Why a distinct exception type.** Every routed caller already wraps its call in `except Exception` to degrade gracefully. A bare `RuntimeError` would be indistinguishable from a provider outage — configuration would read as weather. `RouterDisabled` lets a caller tell the difference; callers that only want to degrade catch `Exception` and are unaffected.

Callers keep their own pre-checks where the flag-off path is a **real behavior** (`session_continuity` falls back to the direct SDK; `decompose` falls back to the heuristic plan). Those are *choices*, not guards — and they now sit behind a floor instead of being the only thing holding the line. Radar gains one so a flag-off sweep reports `router_disabled` rather than `derive_raised`: configuration is not a failed derive.

## 3. D2 — Transport availability and product GA are different questions

One flag answered two:

1. *Is multi-provider transport available?* — infra
2. *Are member-facing lanes GA?* — product

Identical while lanes were the router's only caller. Four machinery callers later they are not: flipping the flag to ship lanes would **also** silently change how session summaries, Studio arrangement, IMAGES planning, and radar acquire their models.

`lanes_enabled()` is the product fact. The asymmetry is deliberate — **a product flag may never grant more than the infra it rides on**:

| `MODEL_ROUTER_ENABLED` | `LANES_ENABLED` | transport | lanes |
|---|---|---|---|
| off | anything | off | **off** |
| on | unset | on | on *(today's behavior — ships INERT)* |
| on | `0` | on | **off** ← the knob that did not exist |
| on | `1` | on | on |

`LANES_ENABLED` unset defers to transport, so this split changes nothing until someone sets it. That was the requirement: the rollout knob arrives without moving the current state.

## 4. D3 — Correcting ADR-556: an app's engine follows its RESIDENT

The operator's second correction:

> "note, radar should be also one of the apps that are user facing. images as well"

ADR-556 filed radar and IMAGES as systematic because their engine is not member-chosen. That conflated *"the member does not pick it"* with *"it is machinery"*. They are **user-facing apps** — ADR-467 residency governs them (Designer resides in Studio · Docs · IMAGES; Researcher is radar's resident).

**The corrected rule — three cases, not two:**

| | who determines the engine |
|---|---|
| **Machinery** | the call type (`SYSTEM_CALLS`, ADR-556) |
| **An app** | **its RESIDENT** (`AUTHORING_APPS` + `KERNEL_AGENTS`, ADR-467) |
| **The open surface** | the member picks the colleague (ADR-460) |

ADR-556's D3 removal of the IMAGES engine passthrough **stands, with a corrected reason**: not "machinery does not take an engine from a caller" but *an app's engine follows its resident, never a caller-supplied model id* — the same rule that made Designer exist instead of `models[0]`. Whether a member may CHOOSE an app's resident is precisely the Phase-2 question, and it is now askable in the right vocabulary.

## 5. Two gate repairs (both were gates pinning a spelling)

- **ADR-486 (radar)** stubbed `route_completion` but never set the flag, so it was implicitly testing radar's *unguarded* path. It now declares the transport it pretends to have.
- **ADR-439** asserted guard-ordering by pinning the literal `model_router_enabled`, going red on the D2 rename — a rename, not a violation. My first repair over-corrected to the bare module import and swept in an unrelated `ledger_model_name` import, staying red for a *different* reason. Fixed by matching the import that brings in the **call**. Re-falsified: it still catches a genuinely mis-ordered guard. (`feedback_never_pin_a_spelling_assert_behaviour`, twice in one change.)

## 5b. Live verification (2026-08-12) — `api/probe_router_transport.py`

Everything above is stub-verified; the gates prove SHAPE against fakes. The
operator asked for real API tests before Phase 2. The Hat-B probe drives live
providers with criteria declared before the run. **31 pass · 0 fail.**

| Verified | Result |
|---|---|
| **C1** flag-off refusal | both entry points refuse in **0.0ms** — no network, guard runs before the request |
| **C2** transport | **6 of 7** lane models return real text (deepseek INFO: upstream account "Insufficient Balance") |
| **C3** ledger shape | every model returns the Anthropic-native EXCLUSIVE token shape, ints ≥ 0, `output_tokens > 0` |
| **C4** pricing | every answering model priced > 0 by `compute_cost_usd_inclusive`; **rate mirror within 1%** of LiteLLM's independent figure (x0.91–x1.00) |
| **C5** streaming | deltas + one terminal completion, usage identical to non-streamed |
| **C6** headroom | reasoning models still speak at the real 4096 lane budget |

**The finding the probe produced — reasoning models spend `max_tokens` on hidden
reasoning before emitting text.** The first cut used `max_tokens=10` and
reported gpt-5, gemini-2.5-flash and gemini-2.5-pro as FAILING with empty text.
They were not failing: gpt-5 returned `finish_reason: length`, `content: ''`,
`reasoning_tokens=10` — the entire budget consumed thinking, none left to speak
with. **A budget too small does not error; it returns an empty reply**, which
every caller reads as "the model had nothing to say".

Measured at the real lane budget (4096), the headroom holds but is not generous:
gpt-5 spends **2560 tokens (63%)** reasoning before answering, gemini-2.5-pro
1726, gemini-2.5-flash 1450. Recorded in the probe as
`OBSERVED_REASONING_AT_4096` so any future budget change is argued against
evidence. **A session that lowers `_LANE_MAX_TOKENS` must re-run C6** — the
failure mode is silent.

**Not verified here**: production env parity. The probe runs on local keys;
whether `GEMINI_API_KEY` / `OPENAI_API_KEY` / `DEEPSEEK_API_KEY` are on **both**
Render API and Scheduler is still a dashboard check, and deepseek additionally
needs its upstream account funded before that lane can be offered.

## 6. Consequences

**Good.** A flag that could be forgotten becomes one that cannot. Lanes can now ship (or stay dark) without moving four machinery paths. Radar degrades honestly and says why. The app/machinery/open-surface trichotomy is stated, so Phase 2 can be argued in the right vocabulary.

**Cost.** One new exception type and one new env var. `LANES_ENABLED` is a second flag to reason about — justified because it *removes* a coupling rather than adding one.

**Ships inert.** With `LANES_ENABLED` unset, behavior is byte-identical to before, except that a flag-off routed call now refuses instead of reaching a provider — which is the bug.

**Still unverified**: the production value of `MODEL_ROUTER_ENABLED`. If it is off, radar sweeps have been reaching Gemini over the network on the platform key while every other surface degraded. That needs a Render dashboard check; it is the one claim in this ADR that rests on local evidence only.

---

**One line**: the transport enforces its own flag so a caller cannot forget it, the product flag stops riding on the infra flag, radar's flag-off sweep says "router off" instead of silently calling a provider — and an app's engine follows its resident, which is neither machinery nor a free member choice.
