"""
Google API Client.

ADR-050: Direct API client for Gmail and Calendar operations.

This is separate from MCP - Gmail/Calendar use direct Google APIs,
not the MCP protocol. The distinction matters:

- MCP Gateway (Node.js): Slack, Notion → uses MCP servers via subprocess
- Google API Client (Python): Gmail, Calendar → uses direct REST APIs

Why separate?
1. MCP requires Node.js runtime (npx spawns MCP servers)
2. Google APIs are straightforward REST calls
3. Keeps naming honest - "MCP" means MCP protocol
"""

import asyncio
import os
import logging
import base64
from typing import Optional, Any
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone
import time

import httpx

from .types import ExportResult, ExportStatus

logger = logging.getLogger(__name__)

# Shared timeout for all Google API calls
_GOOGLE_API_TIMEOUT = httpx.Timeout(30.0, connect=10.0)

# Max retries for transient failures (429, 5xx)
_MAX_RETRIES = 3
_RETRY_BACKOFF_SECONDS = [1, 2, 4]


class GoogleAPIClient:
    """
    Direct API client for Gmail and Calendar operations.

    NOT MCP - uses Google's REST APIs directly.

    Usage:
        client = GoogleAPIClient()

        # Create a draft
        result = await client.create_gmail_draft(
            to="user@gmail.com",
            subject="Test",
            body="Hello",
            client_id="...",
            client_secret="...",
            refresh_token="..."
        )
    """

    def __init__(self):
        # Token cache: refresh_token → (access_token, expires_at_monotonic)
        self._token_cache: dict[str, tuple[str, float]] = {}

    async def _get_access_token(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str
    ) -> str:
        """
        Exchange refresh token for access token, with caching.

        Google OAuth tokens are valid for 1 hour. We cache and reuse them,
        refreshing only when within 60 seconds of expiry.
        """
        # Check cache — reuse if >60s remaining
        cached = self._token_cache.get(refresh_token)
        if cached:
            access_token, expires_at = cached
            if time.monotonic() < expires_at - 60:
                return access_token

        async with httpx.AsyncClient(timeout=_GOOGLE_API_TIMEOUT) as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token"
                }
            )

            if response.status_code != 200:
                raise RuntimeError(f"Token refresh failed: {response.text}")

            data = response.json()
            access_token = data["access_token"]
            # Google tokens last 3600s by default
            expires_in = data.get("expires_in", 3600)
            self._token_cache[refresh_token] = (
                access_token,
                time.monotonic() + expires_in,
            )
            return access_token

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        headers: dict,
        **kwargs,
    ) -> httpx.Response:
        """
        Make an HTTP request with retry on transient failures (429, 5xx).

        Retries up to _MAX_RETRIES times with exponential backoff.
        Does NOT retry on 4xx (except 429).
        """
        last_error = None
        for attempt in range(_MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=_GOOGLE_API_TIMEOUT) as client:
                    response = await getattr(client, method)(url, headers=headers, **kwargs)

                if response.status_code == 429 or response.status_code >= 500:
                    wait = _RETRY_BACKOFF_SECONDS[attempt] if attempt < len(_RETRY_BACKOFF_SECONDS) else 4
                    logger.warning(
                        f"[GOOGLE_API] {method.upper()} {url} returned {response.status_code}, "
                        f"retrying in {wait}s (attempt {attempt + 1}/{_MAX_RETRIES})"
                    )
                    await asyncio.sleep(wait)
                    continue

                return response

            except httpx.TimeoutException as e:
                last_error = e
                wait = _RETRY_BACKOFF_SECONDS[attempt] if attempt < len(_RETRY_BACKOFF_SECONDS) else 4
                logger.warning(
                    f"[GOOGLE_API] {method.upper()} {url} timed out, "
                    f"retrying in {wait}s (attempt {attempt + 1}/{_MAX_RETRIES})"
                )
                await asyncio.sleep(wait)

        # All retries exhausted
        if last_error:
            raise RuntimeError(f"Google API request failed after {_MAX_RETRIES} retries: {last_error}")
        raise RuntimeError(f"Google API returned {response.status_code} after {_MAX_RETRIES} retries: {response.text}")

    # =========================================================================
    # Gmail Operations
    # =========================================================================

    async def list_gmail_labels(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str
    ) -> list[dict[str, Any]]:
        """
        List Gmail labels (folders).

        Returns list of label objects with id, name, type, etc.
        """
        access_token = await self._get_access_token(
            client_id, client_secret, refresh_token
        )

        response = await self._request_with_retry(
            "get",
            "https://gmail.googleapis.com/gmail/v1/users/me/labels",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        data = response.json()

        if "error" in data:
            raise RuntimeError(f"Gmail API error: {data['error'].get('message', data['error'])}")

        return data.get("labels", [])

    async def list_gmail_messages(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        query: Optional[str] = None,
        max_results: int = 20,
        label_ids: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        """
        Search/list Gmail messages.

        Args:
            query: Gmail search query (e.g., "is:unread", "from:sarah@company.com")
            max_results: Maximum messages to return
            label_ids: Optional list of label IDs to filter by (ADR-055)

        Returns list of message objects with id, threadId, snippet, etc.
        """
        access_token = await self._get_access_token(
            client_id, client_secret, refresh_token
        )

        params: dict[str, Any] = {"maxResults": max_results}
        if query:
            params["q"] = query
        if label_ids:
            # Gmail API accepts multiple labelIds parameters
            params["labelIds"] = label_ids

        response = await self._request_with_retry(
            "get",
            "https://gmail.googleapis.com/gmail/v1/users/me/messages",
            headers={"Authorization": f"Bearer {access_token}"},
            params=params,
        )
        data = response.json()

        if "error" in data:
            raise RuntimeError(f"Gmail API error: {data['error'].get('message', data['error'])}")

        return data.get("messages", [])

    async def get_gmail_message(
        self,
        message_id: str,
        client_id: str,
        client_secret: str,
        refresh_token: str
    ) -> dict[str, Any]:
        """
        Get a specific Gmail message.

        Returns full message object with headers, body, attachments info.
        """
        access_token = await self._get_access_token(
            client_id, client_secret, refresh_token
        )

        response = await self._request_with_retry(
            "get",
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"format": "full"},
        )
        data = response.json()

        if "error" in data:
            raise RuntimeError(f"Gmail API error: {data['error'].get('message', data['error'])}")

        return data

    async def get_gmail_thread(
        self,
        thread_id: str,
        client_id: str,
        client_secret: str,
        refresh_token: str
    ) -> dict[str, Any]:
        """
        Get a Gmail thread (conversation).

        Returns thread object with all messages in the conversation.
        """
        access_token = await self._get_access_token(
            client_id, client_secret, refresh_token
        )

        response = await self._request_with_retry(
            "get",
            f"https://gmail.googleapis.com/gmail/v1/users/me/threads/{thread_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"format": "full"},
        )
        data = response.json()

        if "error" in data:
            raise RuntimeError(f"Gmail API error: {data['error'].get('message', data['error'])}")

        return data

    async def send_gmail_message(
        self,
        to: str,
        subject: str,
        body: str,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        cc: Optional[str] = None,
        thread_id: Optional[str] = None,
        is_html: bool = False
    ) -> ExportResult:
        """
        Send a Gmail message.

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body (plain text or HTML)
            cc: Optional CC recipients
            thread_id: Optional thread ID for replies
            is_html: Whether body is HTML content

        Returns:
            ExportResult with message ID and status
        """
        try:
            access_token = await self._get_access_token(
                client_id, client_secret, refresh_token
            )

            # Build email message
            subtype = "html" if is_html else "plain"
            message = MIMEText(body, subtype)
            message["to"] = to
            message["subject"] = subject
            if cc:
                message["cc"] = cc

            # Encode as base64url
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

            request_body = {"raw": raw}
            if thread_id:
                request_body["threadId"] = thread_id

            response = await self._request_with_retry(
                "post",
                "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json=request_body,
            )
            data = response.json()

            if "error" in data:
                raise RuntimeError(f"Gmail API error: {data['error'].get('message', data['error'])}")

            return ExportResult(
                status=ExportStatus.SUCCESS,
                external_id=data.get("id"),
                metadata={"result": data}
            )

        except Exception as e:
            logger.error(f"[GMAIL] Send failed: {e}")
            return ExportResult(
                status=ExportStatus.FAILED,
                error_message=str(e)
            )

    async def create_gmail_draft(
        self,
        to: str,
        subject: str,
        body: str,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        cc: Optional[str] = None,
        is_html: bool = False
    ) -> ExportResult:
        """
        Create a Gmail draft for user review.

        Useful for deliverables that need review before sending.
        """
        try:
            access_token = await self._get_access_token(
                client_id, client_secret, refresh_token
            )

            # Build email message
            subtype = "html" if is_html else "plain"
            message = MIMEText(body, subtype)
            message["to"] = to
            message["subject"] = subject
            if cc:
                message["cc"] = cc

            # Encode as base64url
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

            request_body = {"message": {"raw": raw}}

            response = await self._request_with_retry(
                "post",
                "https://gmail.googleapis.com/gmail/v1/users/me/drafts",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json=request_body,
            )
            data = response.json()

            if "error" in data:
                raise RuntimeError(f"Gmail API error: {data['error'].get('message', data['error'])}")

            return ExportResult(
                status=ExportStatus.SUCCESS,
                external_id=data.get("id"),
                metadata={"result": data}
            )

        except Exception as e:
            logger.error(f"[GMAIL] Create draft failed: {e}")
            return ExportResult(
                status=ExportStatus.FAILED,
                error_message=str(e)
            )

    # =========================================================================
    # Calendar Operations
    # =========================================================================

    async def list_calendar_events(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        calendar_id: str = "primary",
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
        max_results: int = 25,
        sync_token: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        List calendar events, with optional incremental sync.

        Args:
            calendar_id: Calendar ID or 'primary'
            time_min: Start time filter (ISO format or 'now'). Ignored when sync_token is set.
            time_max: End time filter (ISO format or relative like '+7d'). Ignored when sync_token is set.
            max_results: Maximum events to return
            sync_token: If provided, performs incremental sync returning only changes since last sync.
                       When sync_token is invalid (410 Gone), returns {"invalid_sync_token": True}.

        Returns dict with:
            - "items": list of event objects
            - "next_sync_token": token for next incremental sync (if present)
            - "invalid_sync_token": True if the sync_token was rejected (caller should do full sync)
        """
        access_token = await self._get_access_token(
            client_id, client_secret, refresh_token
        )

        if sync_token:
            # Incremental sync — time filters are not allowed with syncToken
            params: dict[str, Any] = {
                "syncToken": sync_token,
                "maxResults": min(max_results, 100),
            }
        else:
            # Full sync with time window
            if not time_min or time_min == "now":
                time_min = datetime.now(timezone.utc).isoformat()
            elif time_min.startswith("+"):
                time_min = self._parse_relative_time(time_min)

            if not time_max:
                time_max = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
            elif time_max.startswith("+"):
                time_max = self._parse_relative_time(time_max)

            params = {
                "timeMin": time_min,
                "timeMax": time_max,
                "maxResults": min(max_results, 100),
                "singleEvents": "true",
                "orderBy": "startTime",
            }

        response = await self._request_with_retry(
            "get",
            f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
            headers={"Authorization": f"Bearer {access_token}"},
            params=params,
        )
        data = response.json()

        if "error" in data:
            error_code = data["error"].get("code", 0)
            # 410 Gone means sync token expired — caller should do full sync
            if error_code == 410 and sync_token:
                return {"items": [], "invalid_sync_token": True}
            raise RuntimeError(f"Calendar API error: {data['error'].get('message', data['error'])}")

        return {
            "items": data.get("items", []),
            "next_sync_token": data.get("nextSyncToken"),
        }

    async def get_calendar_event(
        self,
        event_id: str,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        calendar_id: str = "primary"
    ) -> dict[str, Any]:
        """
        Get a specific calendar event.

        Returns event object with full details.
        """
        access_token = await self._get_access_token(
            client_id, client_secret, refresh_token
        )

        response = await self._request_with_retry(
            "get",
            f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        data = response.json()

        if "error" in data:
            raise RuntimeError(f"Calendar API error: {data['error'].get('message', data['error'])}")

        return data

    async def create_calendar_event(
        self,
        summary: str,
        start_time: str,
        end_time: str,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        calendar_id: str = "primary",
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """
        Create a calendar event.

        Args:
            summary: Event title
            start_time: Start time in ISO format
            end_time: End time in ISO format
            calendar_id: Calendar ID or 'primary'
            description: Optional event description
            location: Optional location
            attendees: Optional list of attendee email addresses

        Returns created event object.
        """
        access_token = await self._get_access_token(
            client_id, client_secret, refresh_token
        )

        event_body = {
            "summary": summary,
            "start": {"dateTime": start_time, "timeZone": "UTC"},
            "end": {"dateTime": end_time, "timeZone": "UTC"},
        }

        if description:
            event_body["description"] = description
        if location:
            event_body["location"] = location
        if attendees:
            event_body["attendees"] = [{"email": e} for e in attendees]

        response = await self._request_with_retry(
            "post",
            f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json=event_body,
        )
        data = response.json()

        if "error" in data:
            raise RuntimeError(f"Calendar API error: {data['error'].get('message', data['error'])}")

        return data

    async def update_calendar_event(
        self,
        event_id: str,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        calendar_id: str = "primary",
        summary: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """
        Partially update a calendar event (PATCH semantics).

        Only provided fields are changed; omitted fields keep their current values.

        Args:
            event_id: ID of the event to update
            calendar_id: Calendar ID or 'primary'
            summary: New event title (optional)
            start_time: New start time in ISO format (optional)
            end_time: New end time in ISO format (optional)
            description: New event description (optional)
            location: New location (optional)
            attendees: New list of attendee email addresses (optional)

        Returns updated event object.
        """
        access_token = await self._get_access_token(
            client_id, client_secret, refresh_token
        )

        patch_body: dict[str, Any] = {}

        if summary is not None:
            patch_body["summary"] = summary
        if start_time is not None:
            patch_body["start"] = {"dateTime": start_time, "timeZone": "UTC"}
        if end_time is not None:
            patch_body["end"] = {"dateTime": end_time, "timeZone": "UTC"}
        if description is not None:
            patch_body["description"] = description
        if location is not None:
            patch_body["location"] = location
        if attendees is not None:
            patch_body["attendees"] = [{"email": e} for e in attendees]

        response = await self._request_with_retry(
            "patch",
            f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json=patch_body,
        )
        data = response.json()

        if "error" in data:
            raise RuntimeError(f"Calendar API error: {data['error'].get('message', data['error'])}")

        return data

    async def delete_calendar_event(
        self,
        event_id: str,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        calendar_id: str = "primary"
    ) -> None:
        """
        Delete (cancel) a calendar event.

        Args:
            event_id: ID of the event to delete
            calendar_id: Calendar ID or 'primary'

        Raises RuntimeError on API failure.
        """
        access_token = await self._get_access_token(
            client_id, client_secret, refresh_token
        )

        response = await self._request_with_retry(
            "delete",
            f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # 204 No Content = success; 410 Gone = already deleted (treat as success)
        if response.status_code not in (200, 204, 410):
            raise RuntimeError(
                f"Calendar DELETE failed ({response.status_code}): {response.text}"
            )

    async def list_calendars(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str
    ) -> list[dict[str, Any]]:
        """
        List user's calendars.

        Returns list of calendar objects with id, summary, etc.
        """
        access_token = await self._get_access_token(
            client_id, client_secret, refresh_token
        )

        response = await self._request_with_retry(
            "get",
            "https://www.googleapis.com/calendar/v3/users/me/calendarList",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        data = response.json()

        if "error" in data:
            raise RuntimeError(f"Calendar API error: {data['error'].get('message', data['error'])}")

        return data.get("items", [])

    def _parse_relative_time(self, val: str) -> str:
        """Parse relative time like '+2h' or '+7d' to ISO format."""
        val = val.lstrip("+")
        if val.endswith("h"):
            delta = timedelta(hours=int(val[:-1]))
        elif val.endswith("d"):
            delta = timedelta(days=int(val[:-1]))
        else:
            delta = timedelta(days=int(val))
        return (datetime.now(timezone.utc) + delta).isoformat()


# Singleton instance
_google_client: Optional[GoogleAPIClient] = None


def get_google_client() -> GoogleAPIClient:
    """Get or create the Google API client singleton."""
    global _google_client
    if _google_client is None:
        _google_client = GoogleAPIClient()
    return _google_client
