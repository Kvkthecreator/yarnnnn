"""
Publish routes — the member-clicked outbound door (ADR-628 phase (a)).

Two tenants, two endpoints each: WordPress (ADR-628 amendment 1) and Slack
(amendment 3). Every one is a MEMBER act on the member's own JWT: the
credential resolves through `platform_credentials` (which refuses agent
callers, ADR-577), and the actual platform write happens in
`services/publish.py` — the ONE outbound seam.

There is deliberately no GET-the-receipt endpoint: the receipt is a
`_publish.yaml` sidecar in the workspace, read like any other file (and
surfaced on Reach's Crossed pane through the timeline's boundary lens,
ADR-642 D2).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.supabase import UserClient

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# WordPress
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Slack (ADR-628 amendment 3)
# ---------------------------------------------------------------------------

@router.get("/publish/slack/channels")
async def get_slack_channels(auth: UserClient) -> dict:
    """The member's channels — the picker behind the Send door.

      connected=False              → connect Slack first
      connected=True, channels=[]  → the connection sees no channel
      connected=True, channels=[…] → pick one at the act; `is_member` false
                                     on a private channel means the app
                                     needs the invite first
    """
    from services.publish import list_slack_channels

    try:
        channels = await list_slack_channels(auth)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[PUBLISH] slack channel listing failed: %s", exc)
        raise HTTPException(status_code=502, detail="Slack did not answer — try again.")
    if channels is None:
        return {"connected": False, "channels": []}
    return {"connected": True, "channels": channels}


class SlackSendRequest(BaseModel):
    model_config = {"extra": "forbid"}

    path: str = Field(..., description="Workspace path of the prose file")
    channel_id: str = Field(..., description="Slack channel id (chosen at the act)")


@router.post("/publish/slack")
async def publish_to_slack(body: SlackSendRequest, auth: UserClient) -> dict:
    """The send act (ADR-628 D2, Slack edition): one file, one channel, the
    member's click, receipted — and read back (D8)."""
    from services.publish import PublishError, publish_file_to_slack

    try:
        receipt = await publish_file_to_slack(
            auth, path=body.path, channel_id=body.channel_id
        )
    except PublishError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:  # noqa: BLE001
        logger.exception("[PUBLISH] slack send failed for %s", body.path)
        raise HTTPException(status_code=502, detail="Slack refused the message — try again.")
    return {"success": True, **receipt}
