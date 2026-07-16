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

    OUR OWN PRIMITIVES   the five file verbs, QueryKnowledge
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
