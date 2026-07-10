"""Seat-level model router — ADR-408 D4 (buy-not-build, LiteLLM lib-mode).

The Altitude-2 lane: a member's chosen model working *as that member's
hands* (ADR-408 D2). This module is the ONE place non-Anthropic provider
plumbing exists — call sites stay provider-blind by passing a
``provider/model`` string and reading back a normalized completion.

Scope discipline (the altitude boundary):

- **Altitude 1 (the steward) never routes.** Freddie's model selection is
  ``services/model_routing.py`` (ADR-402, Anthropic-only) and the occupant
  contract seam (ADR-315). ``agents/freddie_agent.py`` must never import
  this module — the gate test enforces it.
- **Altitude 2 (seat-level helpers) routes here.** First call site:
  session-summary generation (``services/session_continuity.py``) — a
  non-tool-loop helper call. The SSE chat tool loop is the LANES build
  (ADR-408 D6), not this spike.
- **Altitude 3 (persona agents)** is deferred with ADR-382.

Flag: ``MODEL_ROUTER_ENABLED`` (env, default OFF, read at call time). Flag
off → ``model_router_enabled()`` is False and call sites take their legacy
provider path byte-identically. LiteLLM is imported lazily inside
``route_completion`` — the import costs ~3s cold and must never tax API
boot or any flag-off path.

Cost discipline (ADR-396 double-charge invariant — one meter, one ledger):

- The router REPORTS, the ledger RECORDS. ``route_completion`` returns
  normalized token usage in the exact shape ``record_execution_event``
  expects; the caller records tokens + ``ledger_model`` into
  ``execution_events`` and ``compute_cost_usd_inclusive`` prices them —
  the SAME single cost function as every other call (ADR-291 D2).
- LiteLLM's own cost figure (``router_cost_usd``, the provider's list
  price) is surfaced for LOG-ONLY mirror verification. It is never
  written anywhere — a second spend ledger violates ADR-396.
- ``ledger_model`` strips the provider prefix so Anthropic models hit
  their existing ``_BILLING_RATES`` rows. A routed model with no rate row
  logs a loud warning (it would silently price at the Sonnet default) —
  adding a routable model means adding its rate row in the same change.

Token-shape note: LiteLLM normalizes Anthropic usage to the OpenAI
convention where ``prompt_tokens`` INCLUDES cache read/create tokens;
our ledger expects the Anthropic-native EXCLUSIVE shape
(``input_tokens`` = fresh only). ``_normalize_usage`` subtracts the cache
components back out.

Keys: LiteLLM reads provider keys from env natively
(``ANTHROPIC_API_KEY`` / ``OPENAI_API_KEY`` / ``GEMINI_API_KEY`` / ...).
BYOK (ADR-408 D4 req 3) is a per-call ``api_key`` kwarg when that lane
builds; the call path does not change.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


def model_router_enabled() -> bool:
    """Read the flag at call time (no import-time freeze — same pattern as
    model_routing.py env overrides and CONNECTOR_CAPTURE_ENABLED)."""
    return os.environ.get("MODEL_ROUTER_ENABLED", "").strip().lower() in (
        "1", "true", "yes", "on",
    )


@dataclass
class RoutedCompletion:
    """Normalized result of one routed completion call."""

    text: str
    model: str            # the provider/model string as requested
    ledger_model: str     # provider prefix stripped — the execution_events.model value
    usage: dict = field(default_factory=dict)
    # ^ exactly the record_execution_event token kwargs:
    #   input_tokens (fresh, cache-exclusive), output_tokens,
    #   cache_read_tokens, cache_create_tokens
    router_cost_usd: Optional[float] = None
    # ^ LiteLLM's provider-list-price report. LOG-ONLY mirror check —
    #   never recorded (ADR-396: one ledger).
    tool_calls: list = field(default_factory=list)
    # ^ ADR-411: OpenAI-shape tool calls from the model, normalized to
    #   [{"id": str, "name": str, "arguments": dict}]. Empty when the
    #   model replied with text. The caller runs the tools and continues
    #   the conversation with role="tool" messages.
    finish_reason: Optional[str] = None
    # ^ "tool_calls" | "stop" | provider-specific. The loop condition.
    raw_assistant_message: Optional[dict] = None
    # ^ the assistant message dict to append verbatim when continuing a
    #   tool loop (carries the provider's tool_call ids in their exact
    #   shape — round-tripping our normalized form would drop fields).


def ledger_model_name(model: str) -> str:
    """Strip the LiteLLM provider prefix for the ledger's model column.

    ``anthropic/claude-haiku-4-5-20251001`` → ``claude-haiku-4-5-20251001``
    (hits the existing _BILLING_RATES row); bare names pass through.
    """
    return model.split("/", 1)[1] if "/" in model else model


def _usage_int(usage: Any, key: str) -> int:
    """Read an int usage field from either attribute- or dict-shaped usage."""
    if usage is None:
        return 0
    val = usage.get(key) if isinstance(usage, dict) else getattr(usage, key, None)
    try:
        return int(val or 0)
    except (TypeError, ValueError):
        return 0


def _normalize_usage(usage: Any) -> dict:
    """LiteLLM usage → the ledger's Anthropic-native exclusive token shape.

    LiteLLM reports OpenAI-convention ``prompt_tokens`` (cache-INCLUSIVE for
    Anthropic responses) plus, when the provider supplies them,
    ``cache_read_input_tokens`` / ``cache_creation_input_tokens`` top-level
    and/or ``prompt_tokens_details.cached_tokens``. The ledger's
    ``compute_cost_usd_inclusive`` expects fresh-input EXCLUSIVE of cache,
    so subtract the cache components (clamped at zero — some providers
    report details that are not part of prompt_tokens).
    """
    prompt = _usage_int(usage, "prompt_tokens")
    output = _usage_int(usage, "completion_tokens")

    cache_read = _usage_int(usage, "cache_read_input_tokens")
    if not cache_read:
        details = (
            usage.get("prompt_tokens_details") if isinstance(usage, dict)
            else getattr(usage, "prompt_tokens_details", None)
        )
        cache_read = _usage_int(details, "cached_tokens")
    cache_create = _usage_int(usage, "cache_creation_input_tokens")

    fresh_input = max(0, prompt - cache_read - cache_create)
    return {
        "input_tokens": fresh_input,
        "output_tokens": output,
        "cache_read_tokens": cache_read,
        "cache_create_tokens": cache_create,
    }


async def route_completion(
    model: str,
    messages: list[dict],
    *,
    system: Optional[str] = None,
    max_tokens: int = 1024,
    temperature: Optional[float] = None,
    timeout: float = 60.0,
    tools: Optional[list[dict]] = None,
    api_key: Optional[str] = None,
) -> RoutedCompletion:
    """One provider-blind completion call via LiteLLM (lib-mode, no proxy).

    Args:
        model:       LiteLLM model string, ``provider/model`` preferred
                     (e.g. ``anthropic/claude-haiku-4-5-20251001``,
                     ``openai/gpt-4o-mini``). Bare names rely on LiteLLM's
                     inference map — pass the prefix.
        messages:    OpenAI-shape message dicts (role/content; role="tool"
                     results when continuing a tool loop).
        system:      Optional system prompt (prepended as a system message —
                     the OpenAI convention LiteLLM translates per provider).
        tools:       ADR-411 — OpenAI-format tool definitions
                     (``{"type": "function", "function": {...}}``); LiteLLM
                     translates per provider. Omit for plain completions.
        api_key:     ADR-439 — BYOK. When provided, LiteLLM authenticates this
                     call with the customer's OWN provider key instead of the
                     platform env key. The call path is otherwise unchanged
                     (the design the module docstring anticipated). None = the
                     managed default (platform env key). The caller (lane_runner)
                     resolves it per turn from the workspace's BYOK setting.
        max_tokens / temperature / timeout: standard knobs.

    Returns:
        RoutedCompletion with ledger-shaped usage. Raises on provider error —
        the caller decides fallback (the spike call site logs + returns None,
        same failure shape as its legacy path).
    """
    import litellm  # lazy: ~3s cold import must not tax API boot

    full_messages = (
        [{"role": "system", "content": system}] + list(messages)
        if system else list(messages)
    )

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": full_messages,
        "max_tokens": max_tokens,
        "timeout": timeout,
    }
    if temperature is not None:
        kwargs["temperature"] = temperature
    if tools:
        kwargs["tools"] = tools
    if api_key:
        kwargs["api_key"] = api_key  # ADR-439 BYOK — LiteLLM takes a per-call key natively

    response = await litellm.acompletion(**kwargs)

    text = ""
    finish_reason = None
    tool_calls: list[dict] = []
    raw_assistant_message: Optional[dict] = None
    try:
        choice = response.choices[0]
        finish_reason = getattr(choice, "finish_reason", None)
        msg = choice.message
        text = (msg.content or "").strip()
        for tc in (getattr(msg, "tool_calls", None) or []):
            fn = getattr(tc, "function", None)
            args_raw = getattr(fn, "arguments", None) or "{}"
            try:
                import json
                args = json.loads(args_raw) if isinstance(args_raw, str) else dict(args_raw)
            except (ValueError, TypeError):
                args = {}
            tool_calls.append({
                "id": getattr(tc, "id", "") or "",
                "name": getattr(fn, "name", "") or "",
                "arguments": args,
            })
        if tool_calls:
            # Preserve the provider-exact assistant message for the loop
            # continuation (LiteLLM messages support .model_dump()).
            try:
                raw_assistant_message = msg.model_dump()
            except AttributeError:
                raw_assistant_message = dict(msg)
    except (AttributeError, IndexError):
        pass

    usage = _normalize_usage(getattr(response, "usage", None))

    router_cost: Optional[float] = None
    try:
        router_cost = litellm.completion_cost(completion_response=response)
    except Exception:
        pass  # cost report is best-effort; the ledger prices from tokens

    lm = ledger_model_name(model)
    try:
        from services.telemetry import has_billing_rate
        if not has_billing_rate(lm):
            # ADR-439 §4 (F1): the LANE path now hard-blocks unpriced models
            # PRE-call (lane_runner.unpriced_lane_model), so this warning fires
            # only for NON-lane routed callers (e.g. session-summary) as
            # defense-in-depth — they'd otherwise price at the Sonnet default.
            logger.warning(
                "[MODEL-ROUTER] no billing rate for routed model %r — "
                "execution_events will price it at the default rate. "
                "Add a _BILLING_RATES row before routing this model in prod.",
                lm,
            )
    except ImportError:
        pass

    logger.info(
        "[MODEL-ROUTER] model=%s tokens=%d/%d cache=%d/%d tool_calls=%d router_cost=%s",
        model,
        usage["input_tokens"], usage["output_tokens"],
        usage["cache_read_tokens"], usage["cache_create_tokens"],
        len(tool_calls),
        f"${router_cost:.6f}" if router_cost is not None else "n/a",
    )

    return RoutedCompletion(
        text=text,
        model=model,
        ledger_model=lm,
        usage=usage,
        router_cost_usd=router_cost,
        tool_calls=tool_calls,
        finish_reason=finish_reason,
        raw_assistant_message=raw_assistant_message,
    )


async def route_completion_stream(
    model: str,
    messages: list[dict],
    *,
    system: Optional[str] = None,
    max_tokens: int = 1024,
    temperature: Optional[float] = None,
    timeout: float = 60.0,
    tools: Optional[list[dict]] = None,
    api_key: Optional[str] = None,
):
    """Streaming sibling of ``route_completion`` (ADR-412 D2 lane streaming).

    ``api_key`` (ADR-439 BYOK): same contract as ``route_completion`` — when
    provided, the call authenticates with the customer's own provider key;
    None = the managed platform key. Transport-only change; the ledger write
    is unaffected.

    An async generator. Yields ``("delta", text_chunk)`` for each streamed
    text fragment as it arrives, then exactly one terminal
    ``("done", RoutedCompletion)`` carrying the SAME normalized shape the
    non-streaming path returns (accumulated text, tool_calls, usage,
    raw_assistant_message) — so ``run_lane_turn`` gets one contract whether
    a round streams or not, and the ledger write is byte-identical.

    Streaming only changes TRANSPORT: the ONE ledger record (ADR-396) still
    happens in the caller from the terminal RoutedCompletion's usage. Tool
    calls arrive as index-keyed argument fragments and are reassembled here;
    a tool-call round has no user-visible text (the deltas are empty), so
    the caller streams text only on the final (text) round.
    """
    import json
    import litellm  # lazy: same cold-import discipline as route_completion

    full_messages = (
        [{"role": "system", "content": system}] + list(messages)
        if system else list(messages)
    )

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": full_messages,
        "max_tokens": max_tokens,
        "timeout": timeout,
        "stream": True,
        # include_usage → the final chunk carries token usage (OpenAI +
        # LiteLLM-normalized providers). Without it streaming drops usage
        # and the ledger would undercount.
        "stream_options": {"include_usage": True},
    }
    if temperature is not None:
        kwargs["temperature"] = temperature
    if tools:
        kwargs["tools"] = tools
    if api_key:
        kwargs["api_key"] = api_key  # ADR-439 BYOK — LiteLLM takes a per-call key natively

    text_parts: list[str] = []
    finish_reason: Optional[str] = None
    usage_obj: Any = None
    # Tool-call fragments accumulate by index: {idx: {"id", "name", "args_str"}}
    tc_acc: dict[int, dict] = {}

    response = await litellm.acompletion(**kwargs)
    async for chunk in response:
        # Usage rides the final chunk (may have empty choices).
        if getattr(chunk, "usage", None) is not None:
            usage_obj = chunk.usage
        choices = getattr(chunk, "choices", None) or []
        if not choices:
            continue
        choice = choices[0]
        if getattr(choice, "finish_reason", None):
            finish_reason = choice.finish_reason
        delta = getattr(choice, "delta", None)
        if delta is None:
            continue
        piece = getattr(delta, "content", None)
        if piece:
            text_parts.append(piece)
            yield ("delta", piece)
        for tc in (getattr(delta, "tool_calls", None) or []):
            idx = getattr(tc, "index", 0) or 0
            slot = tc_acc.setdefault(idx, {"id": "", "name": "", "args_str": ""})
            if getattr(tc, "id", None):
                slot["id"] = tc.id
            fn = getattr(tc, "function", None)
            if fn is not None:
                if getattr(fn, "name", None):
                    slot["name"] = fn.name
                if getattr(fn, "arguments", None):
                    slot["args_str"] += fn.arguments

    # Reassemble tool calls in index order (mirror the non-streaming shape).
    tool_calls: list[dict] = []
    raw_tool_calls: list[dict] = []
    for idx in sorted(tc_acc):
        slot = tc_acc[idx]
        args_raw = slot["args_str"] or "{}"
        try:
            args = json.loads(args_raw)
        except (ValueError, TypeError):
            args = {}
        tool_calls.append({"id": slot["id"] or "", "name": slot["name"] or "", "arguments": args})
        raw_tool_calls.append({
            "id": slot["id"] or "",
            "type": "function",
            "function": {"name": slot["name"] or "", "arguments": args_raw},
        })

    text = "".join(text_parts)
    # Reconstruct the assistant message for tool-loop continuation (the
    # streaming path can't call msg.model_dump() — build the equivalent).
    raw_assistant_message: Optional[dict] = None
    if tool_calls:
        raw_assistant_message = {
            "role": "assistant",
            "content": text or None,
            "tool_calls": raw_tool_calls,
        }

    usage = _normalize_usage(usage_obj)
    lm = ledger_model_name(model)
    try:
        from services.telemetry import has_billing_rate
        if not has_billing_rate(lm):
            # ADR-439 §4 (F1): lanes hard-block unpriced models pre-call; this
            # warns only for non-lane streamed callers (defense-in-depth).
            logger.warning(
                "[MODEL-ROUTER] no billing rate for streamed model %r — "
                "execution_events will price it at the default rate.", lm,
            )
    except ImportError:
        pass

    logger.info(
        "[MODEL-ROUTER stream] model=%s tokens=%d/%d cache=%d/%d tool_calls=%d",
        model, usage["input_tokens"], usage["output_tokens"],
        usage["cache_read_tokens"], usage["cache_create_tokens"], len(tool_calls),
    )

    yield ("done", RoutedCompletion(
        text=text,
        model=model,
        ledger_model=lm,
        usage=usage,
        router_cost_usd=None,  # streaming: no aggregate completion_cost; ledger prices from tokens
        tool_calls=tool_calls,
        finish_reason=finish_reason,
        raw_assistant_message=raw_assistant_message,
    ))


__all__ = [
    "model_router_enabled",
    "route_completion",
    "route_completion_stream",
    "ledger_model_name",
    "RoutedCompletion",
]
