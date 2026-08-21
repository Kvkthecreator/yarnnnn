"""Capability servers — WHO serves a capability the kernel offers (ADR-463 D2).

THE CUT THIS MODULE EXISTS TO MAKE

Three classes of thing get called "the model layer", and conflating them is what
locked the system to one vendor while a provider-blind router sat unused:

    TRANSPORT            "complete this with tools"      → services/model_router.py
                         genuinely fungible: LiteLLM speaks every provider.

    CAPABILITY SERVER    "search the web"                → THIS MODULE
                         a job some vendor performs with machinery we do not
                         own. INHERENTLY vendor-bound at the point of service —
                         Anthropic's server-side web_search has no LiteLLM
                         equivalent, because it is not a completion, it is a
                         service that happens to arrive through one.

    OUR OWN PRIMITIVES   the seven file verbs, QueryKnowledge
                         provider-irrelevant. We are the server.

**Model-agnostic does not mean vendor-capability-free.** It means: the agent asks
for a CAPABILITY; the kernel decides WHO serves it. Before ADR-463, `WebSearch`
*was* "Anthropic's web_search tool" — the vendor was welded into the primitive's
identity, so "give Scout web search" silently meant "make Gemini call Claude".
That conflation was the bug. The Anthropic dependency was never the bug: today
Anthropic serves search, and that is a fine answer to a question that must at
least be ASKED.

WHAT THIS BUYS, CONCRETELY
- Swapping in Gemini grounding, Brave, or Tavily is an edit HERE. No primitive
  changes, no agent changes, no prompt changes — the caller never knew.
- The vendor becomes a COST decision (a search served by Haiku-plus-server-tool
  has a price; a search served by Brave has a different one) rather than an
  architectural fact.
- `SEARCH_SERVER` is a name a session can grep. The old shape — `client =
  get_anthropic_client()` buried 260 lines into a primitive — was not.

WHY A REGISTRY AND NOT AN ABSTRACT BASE CLASS
Same reason as `LANE_MODELS`, `DERIVE_RECIPES`, `KERNEL_AGENTS` (ADR-450's rule,
fifth instance): servers are DATA. A second search server is a row and a
function, not a subclass. There is exactly one row today, and one row is the
honest state — this module does not pretend to a plurality it does not have. It
makes the question askable; evidence answers it.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

#: Who serves `WebSearch`'s search mode. Env-overridable at call time (the
#: `model_selection` pattern — a deployment flips a cell without a redeploy).
#:
#: `anthropic` — Anthropic's server-side `web_search_20250305` tool, driven by a
#: minimal Haiku call whose only job is to make the tool fire. This is the sole
#: server today and it is the honest default: it works, it is metered, and it is
#: the one we have evidence for.
#:
#: ⚠️ A SEARCH SERVER IS NOT THE AGENT'S ENGINE. Scout runs Gemini and can hold a
#: search capability served by Anthropic — the agent asks for search and never
#: learns who answered. That is the entire point of the seam; if a future reader
#: finds that odd, the oddity is the vendor-hosted capability, not this
#: indirection (§ADR-463 D2).
_SEARCH_SERVER_DEFAULT = "anthropic"


def search_server() -> str:
    """Which server performs a web search. Read at call time."""
    return (os.environ.get("YARNNN_SEARCH_SERVER", "").strip().lower()
            or _SEARCH_SERVER_DEFAULT)


async def serve_search(
    query: str,
    *,
    context: Optional[str] = None,
    max_results: int = 5,
) -> Any:
    """Perform a web search using whichever server the kernel names.

    Returns the server's raw `WebSearchResult` — the shape `WebSearch` already
    speaks. A second server must return the same shape; that is the contract,
    and it is enforced by the caller being blind to which server ran.
    """
    server = search_server()
    if server == "anthropic":
        from services.primitives.web_search import _execute_web_search
        return await _execute_web_search(query, context, max_results)

    # An unknown server is a CONFIG error, and it must be loud: silently falling
    # back to the default would let a deployment believe it had switched vendors
    # while every search still went to Anthropic — and the bill would say so
    # long after the belief set.
    raise ValueError(
        f"Unknown search server {server!r} (YARNNN_SEARCH_SERVER). "
        f"Known: anthropic. Adding one is a branch here + its function."
    )


# ---------------------------------------------------------------------------
# Image generation (ADR-568 D1)
# ---------------------------------------------------------------------------
#
# The SECOND capability through this door, and the reason the door exists.
# Generation is vendor-bound at the point of service exactly as search is: an
# image model is not a completion the router can carry, so no amount of
# LiteLLM makes it fungible. The agent asks for an IMAGE; the kernel picks who
# renders it.
#
# ⚠️ THE SERVER IS NOT THE LANE'S ENGINE, and here that is the whole product
# point rather than an oddity to excuse. A member chatting on Grok, Claude or
# DeepSeek gets an image served by Gemini, and their engine never learns it
# happened. Cross-vendor composition is the DESIGN (ADR-568 §1), not a
# fallback — the same shape `serve_search` already ships, where Scout runs
# Gemini and holds an Anthropic-served search.
#
# Why no registry: ADR-450 — servers are data, and a second one is a row and a
# function. There is one image server. A table with one occupant would also
# invite the ADR-558 error of surfacing it at a door where a member cannot
# chat with it.

#: Who renders an image. Reuses the EXISTING `IMAGES_GENERATION_ENGINE` rather
#: than minting a parallel name: ADR-475's gate already pins its stub-forcing
#: behaviour, and two env vars for one fact is the drift this canon keeps
#: paying to undo.
_GENERATION_SERVER_DEFAULT = "gemini"


class GenerationUnavailable(RuntimeError):
    """Image generation cannot be served, with the ADR-559 D3 reason attached.

    A DISTINCT type so a caller can tell "this deployment cannot generate"
    (fix the config) from "the vendor call failed" (weather) — the same
    reasoning that made `RouterDisabled` its own class.
    """

    def __init__(self, message: str, *, reason: str) -> None:
        super().__init__(message)
        self.reason = reason


def generation_server() -> str:
    """Which server renders an image. Read at call time."""
    return (os.environ.get("IMAGES_GENERATION_ENGINE", "").strip().lower()
            or _GENERATION_SERVER_DEFAULT)


def generation_availability() -> tuple[bool, Optional[str]]:
    """`(available, reason)` for image generation — the ADR-559 D3 shape.

    Deliberately the SAME three reasons a text engine can be dark, because a
    member cannot be expected to learn a second vocabulary for the same fact:

        no_provider_key  — the key never landed on this deployment.
        unpriced         — no `_IMAGE_RATES` row; we cannot meter it.
        upstream_refused — reserved; observed refusals darken here once the
                           driver reports them, mirroring `note_upstream_refusal`.

    `reason` is None when available. The `stub` server is always available: it
    is offline, free, and deterministic — that is what makes it a test double
    rather than a production fallback (D2.b).
    """
    server = generation_server()
    if server == "stub":
        return True, None
    if server == "gemini":
        if not (os.environ.get("GEMINI_API_KEY") or "").strip():
            return False, "no_provider_key"
        from services.telemetry import image_generation_cost_usd
        model = os.environ.get("IMAGES_GENERATION_MODEL") or "gemini-2.5-flash-image"
        if image_generation_cost_usd(model) is None:
            return False, "unpriced"
        return True, None
    # An unknown server is dark, not defaulted — see serve_generation.
    return False, "no_provider_key"


def serve_generation():
    """The generation driver the kernel names, or raise.

    Returns a `GenerationBackend` (the driver contract — per-leaf, `cutout`);
    the caller is blind to which vendor is behind it, exactly as `serve_search`
    callers are blind to who searched.

    ⚠️ RAISES rather than substituting a placeholder. Before ADR-568 D2.b a
    missing key silently produced a stub PNG and the call reported SUCCESS —
    the defect only became visible at the glass, which is the recorded
    `feedback_gate_pinned_spelling_hides_dead_call` shape. A refusal a member
    can read beats an image that lies.
    """
    server = generation_server()
    if server == "stub":
        from services.apps.images.generate import StubBackend
        return StubBackend()

    if server == "gemini":
        ok, why = generation_availability()
        if not ok:
            raise GenerationUnavailable(
                f"image generation unavailable ({why}) — server={server!r}", reason=why or "unknown",
            )
        from services.apps.images.generate import GeminiBackend
        return GeminiBackend(api_key=(os.environ.get("GEMINI_API_KEY") or "").strip())

    # Same discipline as the search resolver: an unknown server is a CONFIG
    # error and must be loud. Silently stubbing would let a deployment believe
    # it had switched vendors while every image came back a placeholder.
    raise ValueError(
        f"Unknown generation server {server!r} (IMAGES_GENERATION_ENGINE). "
        f"Known: gemini, stub. Adding one is a branch here + its function."
    )
