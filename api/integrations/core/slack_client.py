"""
Slack API Client.

ADR-076: Direct API client for Slack operations.
Replaces MCP Gateway (ADR-050) with direct REST calls,
matching the GoogleAPIClient and NotionAPIClient patterns.

Slack bot tokens (xoxb-...) don't expire, so no token refresh needed.
"""

import asyncio
import logging
from typing import Optional, Any

import httpx

logger = logging.getLogger(__name__)

SLACK_API_BASE = "https://slack.com/api"
_SLACK_API_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
_MAX_RETRIES = 3
_RETRY_BACKOFF_SECONDS = [1, 2, 4]


class SlackAPIClient:
    """
    Direct API client for Slack operations.

    Uses Slack's Web API directly with bot tokens (xoxb-...).

    Usage:
        client = SlackAPIClient()
        channels = await client.list_channels(bot_token="xoxb-...")
        messages = await client.get_channel_history(
            bot_token="xoxb-...", channel_id="C123..."
        )
    """

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        bot_token: str,
        **kwargs,
    ) -> dict:
        """
        Make Slack API request with retry on transient failures.

        Handles rate limiting (429 + Retry-After header) and timeouts.
        Slack returns HTTP 200 with ok=false for API-level errors.
        """
        headers = {
            "Authorization": f"Bearer {bot_token}",
            "Content-Type": "application/json",
        }
        last_error = None

        for attempt in range(_MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=_SLACK_API_TIMEOUT) as client:
                    response = await getattr(client, method)(
                        url, headers=headers, **kwargs
                    )
                data = response.json()

                if not data.get("ok"):
                    error = data.get("error", "unknown")
                    if error == "ratelimited":
                        retry_after = int(
                            response.headers.get(
                                "Retry-After",
                                _RETRY_BACKOFF_SECONDS[min(attempt, len(_RETRY_BACKOFF_SECONDS) - 1)],
                            )
                        )
                        logger.warning(f"[SLACK_API] Rate limited, retrying in {retry_after}s")
                        await asyncio.sleep(retry_after)
                        continue
                    return data

                return data

            except httpx.TimeoutException as e:
                last_error = e
                wait = _RETRY_BACKOFF_SECONDS[min(attempt, len(_RETRY_BACKOFF_SECONDS) - 1)]
                logger.warning(f"[SLACK_API] Timeout, retrying in {wait}s (attempt {attempt + 1})")
                await asyncio.sleep(wait)

        if last_error:
            raise RuntimeError(f"Slack API request failed after {_MAX_RETRIES} retries: {last_error}")
        return {"ok": False, "error": "max_retries_exceeded"}

    # =========================================================================
    # Channel Operations
    # =========================================================================

    async def list_channels(
        self,
        bot_token: str,
        limit: int = 200,
        types: str = "public_channel,private_channel",
    ) -> list[dict[str, Any]]:
        """
        List channels in the workspace (conversations.list).

        Returns normalized list of channel dicts.
        """
        data = await self._request_with_retry(
            "get",
            f"{SLACK_API_BASE}/conversations.list",
            bot_token=bot_token,
            params={"limit": limit, "types": types, "exclude_archived": "true"},
        )
        if not data.get("ok"):
            logger.error(f"[SLACK_API] list_channels error: {data.get('error')}")
            return []

        return [
            {
                "id": ch.get("id"),
                "name": ch.get("name") or ch.get("name_normalized"),
                "is_private": ch.get("is_private", False),
                "is_archived": ch.get("is_archived", False),
            }
            for ch in data.get("channels", [])
            if isinstance(ch, dict) and ch.get("id")
        ]

    async def get_channel_info(
        self,
        bot_token: str,
        channel_id: str,
    ) -> dict[str, Any]:
        """
        Get channel info (conversations.info).

        Used for destination verification.
        """
        return await self._request_with_retry(
            "get",
            f"{SLACK_API_BASE}/conversations.info",
            bot_token=bot_token,
            params={"channel": channel_id},
        )

    async def join_channel(
        self,
        bot_token: str,
        channel_id: str,
    ) -> bool:
        """
        Join a public channel (conversations.join).

        Returns True if successful or already in channel.
        """
        data = await self._request_with_retry(
            "post",
            f"{SLACK_API_BASE}/conversations.join",
            bot_token=bot_token,
            json={"channel": channel_id},
        )
        if data.get("ok"):
            logger.info(f"[SLACK_API] Bot joined channel {channel_id}")
            return True

        error = data.get("error", "")
        if error == "already_in_channel":
            return True
        if error in ("method_not_supported_for_channel_type", "channel_not_found"):
            logger.warning(f"[SLACK_API] Cannot join channel {channel_id}: {error}")
            return False

        logger.warning(f"[SLACK_API] join_channel error: {error}")
        return False

    # =========================================================================
    # Message Operations
    # =========================================================================

    async def get_channel_history(
        self,
        bot_token: str,
        channel_id: str,
        limit: int = 100,
        oldest: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Get channel message history (conversations.history).

        Returns list of message dicts.
        """
        messages, _ = await self.get_channel_history_with_error(
            bot_token=bot_token,
            channel_id=channel_id,
            limit=limit,
            oldest=oldest,
        )
        return messages

    async def get_channel_history_with_error(
        self,
        bot_token: str,
        channel_id: str,
        limit: int = 100,
        oldest: Optional[str] = None,
    ) -> tuple[list[dict[str, Any]], Optional[str]]:
        """
        Get channel history, returning (messages, error_code).

        Used by sync paths that need to handle not_in_channel for auto-join.
        """
        params: dict[str, Any] = {"channel": channel_id, "limit": limit}
        if oldest:
            params["oldest"] = oldest

        data = await self._request_with_retry(
            "get",
            f"{SLACK_API_BASE}/conversations.history",
            bot_token=bot_token,
            params=params,
        )
        if not data.get("ok"):
            error = data.get("error", "unknown")
            logger.error(f"[SLACK_API] get_channel_history error: {error}")
            return [], error

        return data.get("messages", []), None

    async def post_message(
        self,
        bot_token: str,
        channel_id: str,
        text: str,
        blocks: Optional[str] = None,
        thread_ts: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Send a message to a channel (chat.postMessage).

        Returns full Slack API response dict.
        """
        payload: dict[str, Any] = {"channel": channel_id, "text": text}
        if blocks:
            payload["blocks"] = blocks
        if thread_ts:
            payload["thread_ts"] = thread_ts

        return await self._request_with_retry(
            "post",
            f"{SLACK_API_BASE}/chat.postMessage",
            bot_token=bot_token,
            json=payload,
        )


# Singleton
_slack_client: Optional[SlackAPIClient] = None


def get_slack_client() -> SlackAPIClient:
    """Get or create the Slack API client singleton."""
    global _slack_client
    if _slack_client is None:
        _slack_client = SlackAPIClient()
    return _slack_client
