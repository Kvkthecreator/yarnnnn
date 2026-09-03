# ADR-634 — The lane frame is cacheable, and the marker never reaches a provider that cannot use it

**Status:** Accepted · 2026-09-03
**Supersedes:** nothing. **Amends:** the ADR-557 router contract (`system` is no longer only a string).

## Context

The lane frame is the system prompt — the "prompt envelope". For a Slides lane it measures ~15,800 bytes (~4,400 tokens), of which the studio posture is 65%, the ADR-630 skills index 14%, and the kernel constants the rest.

`build_lane_conventions` runs **once per turn**, at `lane_runner.py:1447`, outside the round loop. The resulting string is then re-sent on **every round** of the tool loop, up to `_LANE_MAX_ROUNDS`. Every round after the first billed the same bytes as fresh input: ~22,700 input tokens of pure frame on a five-round turn.

`services/anthropic.py` has carried the `prompt-caching-2024-07-31` beta header since it was written, and its own docstring says *"prompt caching should pass a list with cache_control on static blocks."* **No live path in `services/` ever passed one.** The accounting was further ahead than the request: `_normalize_usage` already subtracted `cache_read_input_tokens` / `cache_creation_input_tokens` out of `prompt_tokens`, and `telemetry.compute_cost_usd_inclusive` already priced them at 0.10x read / 1.25x write. The bookkeeping for a feature nothing had requested was correct and unused.

## Decision

**D1. The system prompt is carried as a cache-marked content block when the model can use one.** `_system_payload(system, model)` in `services/model_router.py` returns `[{"type": "text", "text": …, "cache_control": {"type": "ephemeral"}}]`, or the plain string it always was.

**D2. Both router doors use it.** `route_completion` and `route_completion_stream` assemble the same message list; they are twins, and a one-door fix works half the time (the ADR-623 lesson). One helper, two call sites, asserted by the gate.

**D3. Any doubt degrades to the plain string.** Below `_CACHE_MIN_CHARS` (4,000) a marker is pointless — the provider will not cache a short prefix — so a small frame's payload stays byte-identical to before. `supports_prompt_caching` is consulted as defense in depth, and any exception returns the string. A caching miss is the failure mode; a broken call never is.

**D4. Provider safety is established by EXECUTION against the real transforms, not by reading LiteLLM's source.** Verified: the Anthropic transform preserves `cache_control` and hoists the block into the top-level `system` field; the OpenAI-compatible transform (which `openai`, `xai` and `deepseek` all ride) **strips** it; the Gemini transform strips it. In every case the frame TEXT survives intact — no provider loses content. LiteLLM doing the stripping is what makes one payload shape safe for all five providers.

**D5. The trade is stated in both directions.** A cache write costs 1.25x, so a **one-round turn costs ~25% more**. Measured on 500 real production turns (2026-09-03): 33% ran one round, 67% ran two or more, blending to a **~46% saving on frame bytes**. The gate asserts the blended arithmetic on that distribution, so if traffic ever shifted to mostly-single-round turns the change would fail loudly rather than quietly invert.

## Consequences

- No frame restructuring was needed. The frame interleaves static and per-turn slots from its first line (`You are {model_label}, … as {member}'s hands`), so it has no stable *cross-turn* prefix — but it is byte-stable *within* a turn, which is where the repetition was. A cross-turn prefix cache would need the frame reordered static-first; that is a larger change and is **not** taken here.
- Cost per turn is unchanged in the ledger's shape: the same rows, now with `cache_read_tokens` populated, priced by machinery that already existed.
- Only Anthropic models are actually cached today, because only they receive the marker. OpenAI caches automatically without markers; that is the provider's business, not ours.

## Gate

`api/test_adr634_prompt_caching.py` — 28/28, run on the py3.9 venv (it imports litellm). Falsified two ways: reverting either call site fails §3, and removing the capability guard fails §1. §2 asserts the wire payload of three real provider transforms; §5 asserts the economics on the measured round distribution.
