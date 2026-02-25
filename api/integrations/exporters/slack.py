"""
Slack Exporter - ADR-028, ADR-031, ADR-032, ADR-076

Delivers content to Slack channels via Direct API (SlackAPIClient).

ADR-076: Uses SlackAPIClient directly (replaces MCP Gateway).
ADR-031 adds support for Block Kit output when platform_variant is set.
ADR-032 adds support for DM drafts (platform-centric draft delivery).

Destination Schema:
    {
        "platform": "slack",
        "target": "#team-updates" or "C123ABC456",
        "format": "message" | "thread" | "blocks" | "dm_draft",
        "options": {
            "thread_ts": "1234.5678",  # For replies
            "user_email": "user@example.com",  # For dm_draft format
        }
    }
"""

import json
import logging
import httpx
from typing import Any, Optional

from integrations.core.types import ExportResult, ExportStatus
from integrations.core.tokens import get_token_manager
from integrations.core.slack_client import get_slack_client
from .base import DestinationExporter, ExporterContext

logger = logging.getLogger(__name__)


class SlackExporter(DestinationExporter):
    """
    Exports content to Slack via Direct API (SlackAPIClient).

    ADR-076: Uses Slack Web API directly via SlackAPIClient.

    Supports:
    - Posting to channels (public and private)
    - Threading (reply to existing messages)
    - Block Kit (structured message cards)
    - DM drafts (send draft content as a DM to the user)
    """

    @property
    def platform(self) -> str:
        return "slack"

    def get_supported_formats(self) -> list[str]:
        return ["message", "thread", "blocks", "dm_draft"]

    def validate_destination(self, destination: dict[str, Any]) -> bool:
        """Validate Slack destination config."""
        target = destination.get("target")
        if not target:
            return False

        fmt = destination.get("format", "message")
        if fmt not in self.get_supported_formats():
            return False

        if fmt == "thread":
            options = destination.get("options", {})
            if not options.get("thread_ts"):
                return False

        # ADR-032: dm_draft format requires user_email in options
        if fmt == "dm_draft":
            options = destination.get("options", {})
            if not options.get("user_email"):
                return False

        return True

    async def deliver(
        self,
        destination: dict[str, Any],
        content: str,
        title: str,
        metadata: dict[str, Any],
        context: ExporterContext
    ) -> ExportResult:
        """Deliver content to Slack via Direct API."""
        target = destination.get("target")
        fmt = destination.get("format", "message")
        options = destination.get("options", {})

        if not target:
            return ExportResult(
                status=ExportStatus.FAILED,
                error_message="No target channel specified"
            )

        # Get team_id from context metadata
        team_id = context.metadata.get("team_id")
        if not team_id:
            return ExportResult(
                status=ExportStatus.FAILED,
                error_message="Missing team_id in integration metadata"
            )

        try:
            # ADR-032: Handle DM draft format
            if fmt == "dm_draft":
                return await self._deliver_dm_draft(
                    target=target,
                    title=title,
                    content=content,
                    options=options,
                    context=context,
                    team_id=team_id,
                )

            # ADR-031: Check if we should use Block Kit
            platform_variant = metadata.get("platform_variant")
            use_blocks = fmt == "blocks" or platform_variant in ("slack_digest", "slack_update")

            # Build message arguments
            text = content
            blocks_str = None

            if use_blocks:
                from services.platform_output import generate_slack_blocks

                blocks = generate_slack_blocks(
                    content=content,
                    variant=platform_variant or "default",
                    metadata={"title": title, "channel_name": target}
                )
                blocks_str = json.dumps(blocks)
                text = f"{title} - View in Slack for full formatting"
                logger.info(f"[SLACK_EXPORT] Using Block Kit ({len(blocks)} blocks) for variant={platform_variant}")

            thread_ts = None
            if fmt == "thread" and options.get("thread_ts"):
                thread_ts = options["thread_ts"]

            slack_client = get_slack_client()
            result = await slack_client.post_message(
                bot_token=context.access_token,
                channel_id=target,
                text=text,
                blocks=blocks_str,
                thread_ts=thread_ts,
            )

            if not result.get("ok"):
                error = result.get("error", "Slack API error")
                logger.error(f"[SLACK_EXPORT] API error: {error}")
                return ExportResult(
                    status=ExportStatus.FAILED,
                    error_message=error
                )

            message_ts = result.get("ts")
            permalink = result.get("permalink")

            logger.info(
                f"[SLACK_EXPORT] Delivered to {target} for user {context.user_id}, "
                f"ts={message_ts}"
            )

            return ExportResult(
                status=ExportStatus.SUCCESS,
                external_id=message_ts,
                external_url=permalink,
                metadata={"channel": target, "format": fmt}
            )

        except Exception as e:
            logger.error(f"[SLACK_EXPORT] Failed: {e}")
            return ExportResult(
                status=ExportStatus.FAILED,
                error_message=str(e)
            )

    async def _deliver_dm_draft(
        self,
        target: str,
        title: str,
        content: str,
        options: dict[str, Any],
        context: ExporterContext,
        team_id: str,
    ) -> ExportResult:
        """
        Send a draft message as a DM to a Slack user.

        ADR-032: Uses Slack API directly (users.lookupByEmail, conversations.open,
        chat.postMessage) since these are simple REST calls that don't need MCP.
        """
        user_email = options.get("user_email")
        if not user_email:
            return ExportResult(
                status=ExportStatus.FAILED,
                error_message="dm_draft format requires user_email in options"
            )

        bot_token = context.access_token

        try:
            # 1. Look up Slack user ID by email
            slack_user_id = await self._lookup_user_by_email(user_email, bot_token)
            if not slack_user_id:
                return ExportResult(
                    status=ExportStatus.FAILED,
                    error_message=f"Could not find Slack user for email: {user_email}"
                )

            # 2. Open DM channel
            dm_channel_id = await self._open_dm(slack_user_id, bot_token)
            if not dm_channel_id:
                return ExportResult(
                    status=ExportStatus.FAILED,
                    error_message="Could not open DM channel with user"
                )

            # 3. Build Block Kit message with destination context
            from services.platform_output import generate_slack_blocks

            channel_name = target
            content_blocks = generate_slack_blocks(
                content=content,
                variant="default",
                metadata={"title": title}
            )

            channel_id = options.get("channel_id", "")
            channel_link = (
                f"<#{channel_id}|{channel_name.lstrip('#')}>" if channel_id else channel_name
            )

            blocks: list[dict] = [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": f"Draft ready for {channel_name}", "emoji": True}
                },
                {"type": "divider"},
            ]
            blocks.extend(content_blocks)
            blocks.extend([
                {"type": "divider"},
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": (
                                f"This is a draft for {channel_link}. "
                                "Copy the content above and paste it there when ready."
                            )
                        }
                    ]
                }
            ])

            # 4. Send via Slack API
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://slack.com/api/chat.postMessage",
                    headers={
                        "Authorization": f"Bearer {bot_token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "channel": dm_channel_id,
                        "blocks": blocks,
                        "text": f"Draft ready for {channel_name}"
                    }
                )
                api_result = response.json()

            if api_result.get("ok"):
                message_ts = api_result.get("ts")
                logger.info(f"[SLACK_EXPORT] Sent draft DM to {slack_user_id}, ts={message_ts}")
                return ExportResult(
                    status=ExportStatus.SUCCESS,
                    external_id=message_ts,
                    metadata={
                        "channel": dm_channel_id,
                        "format": "dm_draft",
                        "destination_channel": channel_name,
                    }
                )

            error = api_result.get("error", "unknown")
            logger.error(f"[SLACK_EXPORT] DM send failed: {error}")
            return ExportResult(
                status=ExportStatus.FAILED,
                error_message=f"Slack API error: {error}"
            )

        except Exception as e:
            logger.error(f"[SLACK_EXPORT] DM draft failed: {e}")
            return ExportResult(
                status=ExportStatus.FAILED,
                error_message=str(e)
            )

    async def _lookup_user_by_email(self, email: str, bot_token: str) -> Optional[str]:
        """Look up Slack user ID by email via direct Slack REST API."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    "https://slack.com/api/users.lookupByEmail",
                    headers={"Authorization": f"Bearer {bot_token}"},
                    params={"email": email}
                )
                result = response.json()
                if result.get("ok"):
                    return result.get("user", {}).get("id")
                logger.warning(f"[SLACK_EXPORT] User lookup failed: {result.get('error')}")
                return None
        except Exception as e:
            logger.error(f"[SLACK_EXPORT] User lookup error: {e}")
            return None

    async def _open_dm(self, slack_user_id: str, bot_token: str) -> Optional[str]:
        """Open a DM channel via direct Slack REST API."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    "https://slack.com/api/conversations.open",
                    headers={
                        "Authorization": f"Bearer {bot_token}",
                        "Content-Type": "application/json"
                    },
                    json={"users": slack_user_id}
                )
                result = response.json()
                if result.get("ok"):
                    return result.get("channel", {}).get("id")
                logger.warning(f"[SLACK_EXPORT] DM open failed: {result.get('error')}")
                return None
        except Exception as e:
            logger.error(f"[SLACK_EXPORT] DM open error: {e}")
            return None

    async def verify_destination_access(
        self,
        destination: dict[str, Any],
        context: ExporterContext
    ) -> tuple[bool, Optional[str]]:
        """Verify bot has access to the channel via Direct API."""
        target = destination.get("target")
        team_id = context.metadata.get("team_id")

        if not target or not team_id:
            return (False, "Missing target or team_id")

        try:
            slack_client = get_slack_client()
            result = await slack_client.get_channel_info(
                bot_token=context.access_token,
                channel_id=target,
            )

            if result.get("ok"):
                return (True, None)

            error_msg = result.get("error", "")
            if "channel_not_found" in error_msg:
                return (False, f"Channel '{target}' not found or bot not added")
            if "not_in_channel" in error_msg:
                return (False, f"Bot is not a member of '{target}'")
            return (False, f"Cannot access channel: {error_msg}")

        except Exception as e:
            return (False, f"Cannot access channel: {e}")

    def infer_style_context(self) -> str:
        """Slack style: casual, brief, emoji-friendly."""
        return "slack"
