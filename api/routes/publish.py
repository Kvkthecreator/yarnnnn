"""
Publish routes — the member-clicked outbound door (ADR-628 phase (a)).

Two endpoints, one platform (WordPress, the first tenant — ADR-628 amendment).
Both are MEMBER acts on the member's own JWT: the credential resolves through
`platform_credentials` (which refuses agent callers, ADR-577), and the actual
platform write happens in `services/publish.py` — the ONE outbound seam.

There is deliberately no GET-the-receipt endpoint: the receipt is a
`_publish.yaml` sidecar in the workspace, read like any other file.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.supabase import UserClient

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/publish/wordpress/sites")
async def get_wordpress_sites(auth: UserClient) -> dict:
    """The member's publishable sites — the picker behind the Publish door.

    Three answers, matching the ADR-628 three-state connect story:
      connected=False           → connect WordPress first (state 3)
      connected=True, sites=[]  → the login has no site yet (state 2 — the
                                  surface offers the free-site guidance)
      connected=True, sites=[…] → pick one at the act (state 1)
    """
    from services.publish import list_wordpress_sites

    try:
        sites = await list_wordpress_sites(auth)
    except Exception as exc:  # noqa: BLE001 — a platform hiccup is a readable answer
        logger.warning("[PUBLISH] wordpress sites listing failed: %s", exc)
        raise HTTPException(
            status_code=502, detail="WordPress did not answer — try again."
        )
    if sites is None:
        return {"connected": False, "sites": []}
    return {"connected": True, "sites": sites}


class PublishRequest(BaseModel):
    # `extra="forbid"` — the ADR-562 door discipline: a stale field is refused,
    # never silently dropped.
    model_config = {"extra": "forbid"}

    path: str = Field(..., description="Workspace path of the post artifact")
    site_id: str = Field(..., description="WordPress site id (chosen at the act)")
    status: str = Field("publish", description="'publish' or 'draft'")


@router.post("/publish/wordpress")
async def publish_to_wordpress(body: PublishRequest, auth: UserClient) -> dict:
    """The publish act (ADR-628 D2): one post, the member's click, receipted."""
    from services.publish import PublishError, publish_post_to_wordpress

    if body.status not in ("publish", "draft"):
        raise HTTPException(status_code=422, detail="status must be 'publish' or 'draft'")
    try:
        receipt = await publish_post_to_wordpress(
            auth, path=body.path, site_id=body.site_id, status=body.status
        )
    except PublishError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:  # noqa: BLE001
        logger.exception("[PUBLISH] wordpress publish failed for %s", body.path)
        raise HTTPException(
            status_code=502, detail="WordPress refused the post — try again."
        )
    return {"success": True, **receipt}
