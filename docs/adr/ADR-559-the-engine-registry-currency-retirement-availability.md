# ADR-559 — The engine registry: currency, retirement, availability

> **Status**: **Accepted + Implemented** (2026-08-12, operator-ratified). The Anthropic lane is current (Opus 5 added, Sonnet 5 migrated), superseded engines are retired-but-honored, and engine availability is a declared fact with three reasons. Gate `api/test_adr559_engine_registry.py` 62/62, four falsifiers verified red; the three new Anthropic engines verified live via `probe_router_transport.py`.
> **Date**: 2026-08-12
> **Authors**: KVK (operator) + Claude (collaborator)
> **Dimensional classification** (Axiom 0): **Mechanism** (Axiom 5). The roster was a list of strings with no lifecycle and no notion of whether a row could actually run.

**Amends**:
- [ADR-411](ADR-411-chat-lanes-and-the-lane-tool-surface.md) **D5** — `LANE_MODELS` gains `retired` and an `offered_lane_models()` view. The D5 rule (a model enters only WITH a `_BILLING_RATES` row) is **strengthened**: it now also applies on the way *out* — §3.
- [ADR-420](ADR-420-engine-breadth-vs-connector-breadth.md) **§10** — the seed set is refreshed. Its rule ("provide enough, not the most — one lane per reason a member would leave") is preserved; an Opus tier is such a reason and was missing.
- [ADR-558](ADR-558-chat-is-the-engine-surface-agents-are-personified.md) **D1** — the door now serves the *offered* roster with availability, not the raw dict.

**Preserves**: [ADR-439](ADR-439-byok-key-scope-and-the-enterprise-tier-gate.md) §4 (an unpriced model never routes — this ADR depends on it), [ADR-460](ADR-460-agents-one-concept-independent-facts-one-gate.md) D4 (a lane's engine is a historical fact), [ADR-396](ADR-396-the-pricing-model-type-b-subscription-over-the-metered-balance.md) (one meter).

---

## 1. Context

The operator asked two questions: *is our engine list up to date*, and *how should we handle DeepSeek being unavailable at a more fundamental level?* Checked against the code, neither had a small answer.

**The Anthropic lane was two generations stale.** The roster offered `claude-sonnet-4-6` and a date-suffixed Haiku, and **no Opus tier at all** — a member who wanted Anthropic's frontier model could not pick one, on a surface ADR-558 had just made engine-first. Meanwhile `_BILLING_RATES` carried a `claude-opus-4-6` row that appeared in no roster, no `SYSTEM_CALLS` entry, and no steward route: **priced, unroutable, and reading like an Opus tier we did not offer.**

**And DeepSeek was not a special case.** The probe found its account refusing with "Insufficient Balance" — a condition no code change fixes, that nothing could predict, and that under ADR-558 is now *directly member-visible* rather than hidden behind a persona.

## 2. D1 — Currency: the roster names models that exist, are priced, and are reachable

Added **`claude-opus-5`** ($5/$25) — the frontier tier the roster never had. Migrated **Sonnet 4.6 → Sonnet 5** (same $3/$15 list price, better model) and the dated Haiku id to its suffix-free form, across all four selection homes: `LANE_MODELS`, `SYSTEM_CALLS` (ADR-556), `DEFAULT_ROUTES` (the steward, ADR-402), and `KERNEL_AGENTS`/`KERNEL_POSTURES` (ADR-460).

Deleted the `claude-opus-4-6` rate row. **A rate row is a claim about what we run**; one nothing can route to is a false claim, and the gate now asserts every priced engine is reachable from some selection home.

**One deliberate pricing decision, recorded because the mirror will look wrong.** Anthropic is running Sonnet 5 at an introductory **$2/$10 through 2026-08-31**, and LiteLLM's cost report prices at the intro rate — so the ADR-408 D4 rate mirror reads **x1.50** on that row, the only row that does not mirror ~1.00. We price at the **standard $3/$15** anyway: this table is what we charge the pool, and pricing at a rate that expires in weeks would silently under-charge the day it lapses with nothing to notice. Over-charging by 50% for the intro window is the safer error *and* is visible. Revisit after 2026-08-31, when the mirror should return to x1.00 on its own.

## 3. D2 — Retirement: superseded engines are honored, not deleted

**`LANE_MODELS` is the turn-time whitelist, not just the chooser.** `run_lane_turn` and `run_lane_turn_stream` both refuse a model that is not a key in it. So deleting a superseded row does not tidy the roster — **it breaks every existing conversation pinned to that engine.**

The measurement that settled it: at the refresh, **all 65 live lanes pinned `claude-sonnet-4-6`, 56 of them bound Studio lanes.** Deleting the row would have orphaned the entire workspace. This was not a hypothetical — it was one query away from being the shipped behavior.

So a row carries **`retired`**: still routable for lanes already pinned to it, never offered for a new conversation. `offered_lane_models()` is the chooser's view; the loops keep gating on the full dict. **Retired engines keep their `_BILLING_RATES` row** — `unpriced_lane_model` gates every turn, so dropping the rate would refuse the very lanes the state exists to protect.

This is ADR-460 D4 applied to the roster: *a lane's engine is what actually ran*, and a registry edit must never retroactively change or invalidate that.

## 4. D3 — Availability: three reasons, two computed, one observed

An engine can be unavailable for three **structurally different** reasons:

| Reason | Knowable | Whose problem |
|---|---|---|
| `no_provider_key` | before the click (env) | ours — the key never landed |
| `unpriced` | before the click (`_BILLING_RATES`) | ours — a row without a rate |
| `upstream_refused` | **only by calling** | the provider's — billing, quota |

The third is the interesting one. **Nothing can predict it**; the only way to learn is to try. So it is *observed*: a routed call that fails with an account-shaped provider error records the engine as dark, and **a successful call heals it** — process-local and deliberately not persisted, because an upstream refusal is a transient fact about someone else's account and a funded account must recover without an operator clearing a table.

**The detection is narrow on purpose.** Only account-shaped markers count (`insufficient balance`, `quota`, `billing`, `payment required`). A timeout, a rate limit, or a bad request is *not* unavailability — marking an engine dark on any error would remove a whole lane from the picker for one transient blip. The gate falsifies this directly.

**Unavailable engines are shown, not hidden.** The envelope serves `available` + `unavailable_reason` on every row; the door greys them with a member-facing reason. Hiding is worse: a member who expects DeepSeek and sees an empty space concludes the app is broken and files a bug. The server sends a *reason code* (an operator fact); the wording is the FE's, and `no_provider_key` in particular must not read as something the member did or could fix.

**And the refusal happens at the door.** `create_lane` refuses a retired or unavailable engine before the lane row is built. A conversation created on a dead engine looks fine until the first message, then fails against an empty transcript — worse than a refusal.

## 5. The FE label map, again

`web/lib/workspace/attribution.ts` hardcoded **3** of what became **10** engines, having drifted the moment the roster last grew. Every unlisted engine fell through to a raw model id. It is now complete *and* scoped in its own comment to what it is for — historical **attribution strings**, where no envelope is in hand. Anything holding the envelope reads the served `label`. Retired engines stay listed: old revisions are attributed to what actually ran, and must keep rendering a name.

## 6. Consequences

**Good.** A member can pick Anthropic's frontier model. Existing conversations survive a roster change by construction. An unavailable engine says so at the door instead of failing on the first message, and DeepSeek's condition is handled by a mechanism rather than a special case — the next provider to run out of credit is already covered.

**Cost.** `LANE_MODELS` rows now carry lifecycle state, and the roster has two views. Justified: the alternative to `retired` was orphaning 65 lanes.

**Trade accepted.** Sonnet 5 bills at standard rates during an introductory window, which over-charges the pool by 50% on that engine until 2026-08-31 (§2).

**Not done here.** Sonnet 5's **new tokenizer produces ~30% more tokens for the same text**, and `_LANE_MAX_TOKENS = 4096` was calibrated on Sonnet 4.6 — combined with the ADR-557 reasoning-overhead finding (GPT-5 spends 63% of that budget thinking), the lane token profile needs re-measuring with a fresh `--headroom` probe run. Deferred deliberately: it is a measurement, not a guess, and it is not this ADR's decision.

---

**One line**: the roster names models that exist and are priced, superseded engines keep running the 65 lanes pinned to them while leaving the door, and an engine that cannot run says which of the three reasons applies — because deleting a stale row would have orphaned the workspace, and DeepSeek's empty account was never going to be fixed by a code change.
