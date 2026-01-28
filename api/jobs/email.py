"""
YARNNN v5 - Email Delivery Service

Sends transactional emails via Resend.
https://resend.com/docs/api-reference/emails/send-email
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import httpx


@dataclass
class EmailResult:
    """Result of an email send attempt."""

    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


async def send_email(
    to: str,
    subject: str,
    html: str,
    text: Optional[str] = None,
    from_email: Optional[str] = None,
    reply_to: Optional[str] = None,
) -> EmailResult:
    """
    Send an email via Resend API.

    Args:
        to: Recipient email address
        subject: Email subject line
        html: HTML email body
        text: Plain text email body (optional, recommended)
        from_email: Sender address (defaults to env var)
        reply_to: Reply-to address (optional)

    Returns:
        EmailResult with success status and message_id or error
    """
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        return EmailResult(success=False, error="RESEND_API_KEY not configured")

    from_addr = from_email or os.environ.get(
        "RESEND_FROM_EMAIL", "YARNNN <noreply@yarnnn.com>"
    )

    payload = {
        "from": from_addr,
        "to": [to],
        "subject": subject,
        "html": html,
    }

    if text:
        payload["text"] = text

    if reply_to:
        payload["reply_to"] = reply_to

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )

            if response.status_code == 200:
                data = response.json()
                return EmailResult(
                    success=True,
                    message_id=data.get("id"),
                )
            else:
                return EmailResult(
                    success=False,
                    error=f"Resend API error: {response.status_code} - {response.text}",
                )

    except httpx.TimeoutException:
        return EmailResult(success=False, error="Request timed out")
    except httpx.RequestError as e:
        return EmailResult(success=False, error=f"Request failed: {str(e)}")
    except Exception as e:
        return EmailResult(success=False, error=f"Unexpected error: {str(e)}")


async def send_test_email(to: str) -> EmailResult:
    """Send a test email to verify configuration."""
    return await send_email(
        to=to,
        subject="[YARNNN] Test Email",
        html="""
        <html>
        <body>
            <h1>Test Email</h1>
            <p>If you're seeing this, email delivery is working!</p>
            <p>- YARNNN</p>
        </body>
        </html>
        """,
        text="Test Email\n\nIf you're seeing this, email delivery is working!\n\n- YARNNN",
    )
