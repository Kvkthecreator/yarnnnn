"""Programs routes — composition surface resolution + activation.

ADR-225: GET /api/programs/surfaces returns the resolved composition tree
for the operator's workspace. The FE compositor consumes the response and
renders via universal components from web/components/library/.

ADR-226: GET /api/programs/activatable returns the list of bundles the
operator may select at signup or activation time. POST /api/programs/activate
runs the reference-workspace fork against an existing workspace.

Routes are operator-scoped + stateless. Read paths consult bundle YAML
(cached via bundle_reader.lru_cache) and platform_connections. The
activation route writes substrate via the standard authored-substrate path
(ADR-209).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.supabase import UserClient

logger = logging.getLogger(__name__)

router = APIRouter()


class ActivateRequest(BaseModel):
    program_slug: str


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


@router.get("/activatable")
async def list_activatable_programs(auth: UserClient) -> dict:
    """ADR-226: list bundles the operator may activate.

    Returns bundles with `status` in {`active`, `deferred`} from the
    program registry. The UI renders these as a selection card list at
    signup or in a later "activate a program" flow.

    Deferred bundles are listed but with a `deferred: true` flag so the
    UI can disable selection (their activation_preconditions in MANIFEST
    aren't met). Today: alpha-trader is `active` (selectable),
    alpha-commerce is `deferred` (visible but not selectable),
    alpha-prediction + alpha-defi are `reference` (not listed).

    Auth-scoped only as a permission boundary — bundle availability is
    not user-specific (every authenticated operator sees the same list).
    """
    from services.bundle_reader import _all_slugs, _load_manifest

    items = []
    for slug in _all_slugs():
        manifest = _load_manifest(slug)
        if not manifest:
            continue
        status = manifest.get("status")
        if status not in ("active", "deferred"):
            continue
        items.append({
            "slug": manifest.get("slug"),
            "title": manifest.get("title"),
            "tagline": manifest.get("tagline"),
            "status": status,
            "deferred": status == "deferred",
            "oracle": manifest.get("oracle") or {},
            "current_phase": manifest.get("current_phase"),
        })
    return {"schema_version": 1, "programs": items}


@router.post("/activate")
async def activate_program(req: ActivateRequest, auth: UserClient) -> dict:
    """ADR-226: activate a program for the operator's workspace.

    Runs the reference-workspace fork against the operator's workspace,
    forking the bundle's `reference-workspace/` files into `/workspace/`
    honoring three-tier file categorization (canon/authored/placeholder).

    Idempotent — re-running re-applies canon, preserves operator-authored.
    Same primitive whether called at signup or later (ADR-226 §6).

    Returns:
      {
        "schema_version": 1,
        "activated_program": "alpha-trader",
        "files_written": ["context/_shared/MANDATE.md", ...],
        "files_skipped": ["..."]
      }
    """
    from services.workspace_init import _fork_reference_workspace

    try:
        summary = await _fork_reference_workspace(
            auth.client, auth.user_id, req.program_slug
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception(f"[ACTIVATE] Fork failed for {auth.user_id[:8]}, program={req.program_slug}")
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "schema_version": 1,
        "activated_program": req.program_slug,
        "files_written": summary.get("files_written", []),
        "files_skipped": summary.get("files_skipped", []),
    }
