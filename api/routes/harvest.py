"""Harvest routes — "bring in your reality" (ADR-331 D3 + D4).

Two endpoints, both fired from the `/setup` "bring in reality" step:

  POST /api/harvest/dry-run
      Metadata-only estimate for the picker. NO writes, NO LLM. Reuses the
      existing platform list tools for counts; returns the estimate + the
      likely target context domains so the picker can show
      "~N items → these domains" before the operator confirms (D4).

  POST /api/harvest/run
      Fires the curated harvest invocation: a headless LLM call with the
      scoped read tools + WriteFile, attributed agent:harvest, that reads the
      picked sources, curates, and routes each piece into a context domain
      (D3). Selection scope is ephemeral — passed in the request body, never
      persisted (ADR-331 D4 no-stored-state).

No new primitive, no new permission mode, no harvest subsystem — these are
thin endpoints over the existing platform bridge + headless executor path.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from services.supabase import UserClient
from services.harvest import harvest_dry_run, harvest_run

logger = logging.getLogger(__name__)

router = APIRouter()


# Note: Pydantic evaluates field annotations at class-build time, so the
# `X | None` 3.10+ union syntax fails on the Python 3.9 runtime even with
# `from __future__ import annotations` (which only defers *function* annotations).
# Use typing.Optional / typing.List for model fields.
class HarvestSource(BaseModel):
    provider: str                        # slack | notion | github
    id: Optional[str] = None             # channel_id / page_id / owner-repo
    label: Optional[str] = None
    range_days: Optional[int] = None


class HarvestScopeRequest(BaseModel):
    sources: List[HarvestSource] = []


@router.post("/harvest/dry-run")
async def harvest_dry_run_route(auth: UserClient, request: HarvestScopeRequest):
    """Metadata-only estimate (ADR-331 D4). No writes, no LLM."""
    scope = {"sources": [s.model_dump() for s in request.sources]}
    return await harvest_dry_run(auth, scope)


@router.post("/harvest/run")
async def harvest_run_route(auth: UserClient, request: HarvestScopeRequest):
    """Fire the curated harvest invocation (ADR-331 D3). Writes agent:harvest substrate."""
    scope = {"sources": [s.model_dump() for s in request.sources]}
    return await harvest_run(auth, scope)
