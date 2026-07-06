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
) -> RoutedCompletion:
    """One provider-blind completion call via LiteLLM (lib-mode, no proxy).

    Args:
        model:       LiteLLM model string, ``provider/model`` preferred
                     (e.g. ``anthropic/claude-haiku-4-5-20251001``,
                     ``openai/gpt-4o-mini``). Bare names rely on LiteLLM's
                     inference map — pass the prefix.
        messages:    OpenAI-shape message dicts (role/content).
        system:      Optional system prompt (prepended as a system message —
                     the OpenAI convention LiteLLM translates per provider).
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

    response = await litellm.acompletion(**kwargs)

    text = ""
    try:
        text = (response.choices[0].message.content or "").strip()
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
            logger.warning(
                "[MODEL-ROUTER] no billing rate for routed model %r — "
                "execution_events will price it at the default rate. "
                "Add a _BILLING_RATES row before routing this model in prod.",
                lm,
            )
    except ImportError:
        pass

    logger.info(
        "[MODEL-ROUTER] model=%s tokens=%d/%d cache=%d/%d router_cost=%s",
        model,
        usage["input_tokens"], usage["output_tokens"],
        usage["cache_read_tokens"], usage["cache_create_tokens"],
        f"${router_cost:.6f}" if router_cost is not None else "n/a",
    )

    return RoutedCompletion(
        text=text,
        model=model,
        ledger_model=lm,
        usage=usage,
        router_cost_usd=router_cost,
    )


__all__ = [
    "model_router_enabled",
    "route_completion",
    "ledger_model_name",
    "RoutedCompletion",
]
