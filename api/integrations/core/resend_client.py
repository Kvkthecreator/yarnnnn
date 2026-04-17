"""
Resend Email API Client — ADR-192 Phase 4: Email Send Platform Class

Thin HTTP wrapper for Resend's send API. Used by the `email` platform
class to enable autonomous customer communication for the e-commerce
domain and audience comms for future AI-influencer / international-trader
domains.

Resend is chosen for: dev-first API, no OAuth (API key only), free tier
covers alpha, fair scale pricing. See ADR-192 Phase 4 rationale.

**Authentication:** single API key per user, stored encrypted in
`platform_connections.credentials_encrypted`. User connects via
`POST /integrations/email/connect`.

**Sender identity:** Alpha accounts use Resend's shared sender
`onboarding@resend.dev` for fastest setup. Production-quality sending
requires the user verify a domain in Resend and configure
`from_email` / `from_name` on the connection's metadata.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


RESEND_BASE = "https://api.resend.com"
DEFAULT_FROM = "YARNNN <onboarding@resend.dev>"
_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
_MAX_RETRIES = 3
_RETRY_BACKOFF_SECONDS = [1, 2, 4]


class ResendClient:
    """Direct API client for Resend.

    Usage:
        client = ResendClient()
        ok = await client.validate_key(api_key="re_...")
        result = await client.send(
            api_key="re_...",
            from_email="team@example.com",
            to=["customer@example.com"],
            subject="Your brief is ready",
            html="<p>…</p>",
        )
    """

    async def _request(
        self,
        method: str,
        path: str,
        api_key: str,
        json_body: Optional[dict] = None,
    ) -> Any:
        url = f"{RESEND_BASE}{path}"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        }
        if json_body:
            headers["Content-Type"] = "application/json"

        last_error: Optional[str] = None
        for attempt in range(_MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                    response = await client.request(
                        method, url, headers=headers, json=json_body,
                    )

                if response.status_code == 401:
                    return {"error": "invalid_credentials", "status": 401}
                if response.status_code == 403:
                    return {"error": "forbidden", "status": 403}
                if response.status_code == 404:
                    return {"error": "not_found", "status": 404}
                if response.status_code == 422:
                    detail = response.text[:500]
                    return {"error": "validation_failed", "status": 422, "detail": detail}
                if response.status_code == 429:
                    last_error = "rate_limited"
                    if attempt < _MAX_RETRIES - 1:
                        import asyncio as _a
                        await _a.sleep(_RETRY_BACKOFF_SECONDS[attempt])
                        continue
                    return {"error": "rate_limited", "status": 429}

                if response.status_code >= 400:
                    detail = response.text[:500]
                    return {"error": f"http_{response.status_code}", "detail": detail}

                return response.json()

            except httpx.TimeoutException:
                last_error = "timeout"
                if attempt < _MAX_RETRIES - 1:
                    import asyncio as _a
                    await _a.sleep(_RETRY_BACKOFF_SECONDS[attempt])
                    continue
                return {"error": "timeout"}
            except httpx.HTTPError as e:
                last_error = f"http_error: {e}"
                if attempt < _MAX_RETRIES - 1:
                    import asyncio as _a
                    await _a.sleep(_RETRY_BACKOFF_SECONDS[attempt])
                    continue
                return {"error": "http_error", "detail": str(e)}

        return {"error": "exhausted_retries", "detail": last_error or ""}

    # =========================================================================
    # Validation
    # =========================================================================

    async def validate_key(self, api_key: str) -> dict:
        """Verify a Resend API key by listing domains (scoped, harmless GET).

        Resend API keys start with `re_`. This method returns metadata on
        success (including verified domains) for use at connect time.
        """
        if not api_key or not api_key.startswith("re_"):
            raise ValueError("Invalid Resend API key format (must start with 're_')")

        result = await self._request("GET", "/domains", api_key)
        if isinstance(result, dict) and result.get("error"):
            raise ValueError(f"Key validation failed: {result.get('error')} — {result.get('detail', '')}")

        # Resend returns {"data": [{"id": ..., "name": "domain.com", "status": ...}]}
        domains = []
        if isinstance(result, dict):
            domains = result.get("data") or []
        return {
            "valid": True,
            "domains": [
                {
                    "id": d.get("id"),
                    "name": d.get("name"),
                    "status": d.get("status"),
                    "region": d.get("region"),
                }
                for d in domains
            ],
            "has_verified_domain": any(d.get("status") == "verified" for d in domains),
        }

    # =========================================================================
    # Send
    # =========================================================================

    async def send(
        self,
        api_key: str,
        *,
        to: list,
        subject: str,
        html: str,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        reply_to: Optional[str] = None,
        cc: Optional[list] = None,
        bcc: Optional[list] = None,
    ) -> dict:
        """Send a single email to one or more recipients (all receive same body).

        For per-recipient personalization use `send_batch`.

        Args:
            to: list of recipient email strings.
            subject, html: email contents.
            from_email / from_name: override default sender. If both absent,
                uses Resend's shared `onboarding@resend.dev` (alpha-only).
            reply_to: Reply-To header; replies land in user's actual inbox.
            cc, bcc: optional.

        Returns {id, to, status} on success or {error, detail} on failure.
        """
        if not to:
            return {"error": "missing_to", "detail": "at least one recipient required"}
        if not subject:
            return {"error": "missing_subject"}
        if not html:
            return {"error": "missing_html"}

        from_field = self._format_sender(from_email, from_name)
        body: dict[str, Any] = {
            "from": from_field,
            "to": to,
            "subject": subject,
            "html": html,
        }
        if reply_to:
            body["reply_to"] = reply_to
        if cc:
            body["cc"] = cc
        if bcc:
            body["bcc"] = bcc

        result = await self._request("POST", "/emails", api_key, json_body=body)
        if isinstance(result, dict) and result.get("error"):
            return {"error": result["error"], "detail": result.get("detail", "")}

        return {
            "id": result.get("id", "") if isinstance(result, dict) else "",
            "to": to,
            "status": "sent",
        }

    async def send_batch(
        self,
        api_key: str,
        *,
        messages: list,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
    ) -> dict:
        """Send many personalized emails in one call.

        Args:
            messages: list of {to, subject, html, [reply_to, cc, bcc]} dicts.
                Each becomes an independent send.
            from_email / from_name: default sender for all messages (each
                message may override via its own 'from' field).

        Returns:
            {
                success_count: int,
                failure_count: int,
                results: [{index, to, outcome, id?, error?}, ...],
            }

        Resend supports a native batch endpoint (POST /emails/batch, max
        100 per call). For simplicity + error isolation, this implementation
        uses per-message sends; swap to the batch endpoint if throughput
        becomes a concern.
        """
        default_from = self._format_sender(from_email, from_name)
        results = []
        for idx, msg in enumerate(messages):
            to = msg.get("to")
            if isinstance(to, str):
                to = [to]
            if not to or not isinstance(to, list):
                results.append({
                    "index": idx,
                    "to": to,
                    "outcome": "skipped",
                    "error": "missing or invalid 'to'",
                })
                continue
            if not msg.get("subject") or not msg.get("html"):
                results.append({
                    "index": idx,
                    "to": to,
                    "outcome": "skipped",
                    "error": "missing subject or html",
                })
                continue

            body: dict[str, Any] = {
                "from": msg.get("from", default_from),
                "to": to,
                "subject": msg["subject"],
                "html": msg["html"],
            }
            if msg.get("reply_to"):
                body["reply_to"] = msg["reply_to"]
            if msg.get("cc"):
                body["cc"] = msg["cc"]
            if msg.get("bcc"):
                body["bcc"] = msg["bcc"]

            result = await self._request("POST", "/emails", api_key, json_body=body)
            if isinstance(result, dict) and result.get("error"):
                results.append({
                    "index": idx,
                    "to": to,
                    "outcome": "failed",
                    "error": result.get("error"),
                    "detail": result.get("detail", ""),
                })
            else:
                results.append({
                    "index": idx,
                    "to": to,
                    "outcome": "sent",
                    "id": result.get("id", "") if isinstance(result, dict) else "",
                })

        success_count = sum(1 for r in results if r["outcome"] == "sent")
        failure_count = len(results) - success_count
        return {
            "success_count": success_count,
            "failure_count": failure_count,
            "results": results,
        }

    # =========================================================================
    # Helpers
    # =========================================================================

    @staticmethod
    def _format_sender(from_email: Optional[str], from_name: Optional[str]) -> str:
        """Build RFC 5322 from header. Falls back to shared Resend sender."""
        if from_email:
            if from_name:
                return f"{from_name} <{from_email}>"
            return from_email
        return DEFAULT_FROM


# Singleton
_resend_client: Optional[ResendClient] = None


def get_resend_client() -> ResendClient:
    global _resend_client
    if _resend_client is None:
        _resend_client = ResendClient()
    return _resend_client
