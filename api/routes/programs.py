"""Programs routes — composition surface resolution for the cockpit.

ADR-225: GET /api/programs/surfaces returns the resolved composition tree
for the operator's workspace. The FE compositor consumes the response and
renders via universal components from web/components/library/.

Single endpoint. Stateless. Reads only:
- Bundle YAML files (cached via bundle_reader.lru_cache)
- workspace's `platform_connections` table (for active-program resolution
  per ADR-224 §3 capability-implicit activation)

No mutation. No platform API calls. No LLM calls.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter

from services.supabase import UserClient

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/surfaces")
async def get_workspace_surfaces(auth: UserClient) -> dict:
    """Resolve composition surfaces for the operator's workspace.

    Per ADR-225 §2: returns active_bundles[] metadata + composition tree
    (tabs + chat_chips) + schema_version.

    Response shape (illustrative — empty workspace):
        {
            "schema_version": 1,
            "active_bundles": [],
            "composition": {"tabs": {}, "chat_chips": []}
        }

    Response shape (alpha-trader active):
        {
            "schema_version": 1,
            "active_bundles": [{
                "slug": "alpha-trader",
                "title": "alpha-trader",
                "tagline": "...",
                "current_phase": "observation",
                "current_phase_label": "Phase 0 — Observation",
                "phases": [...]
            }],
            "composition": {
                "tabs": {
                    "chat": {"bands": [...]},
                    "work": {"list": {...}, "detail": {"middles": [...]}},
                    "agents": {"list": {...}, "detail": {"middles": [...]}},
                    "files": {"list": {...}}
                },
                "chat_chips": [...]
            }
        }
    """
    from services.composition_resolver import resolve_workspace_composition

    return resolve_workspace_composition(auth.user_id, auth.client)
