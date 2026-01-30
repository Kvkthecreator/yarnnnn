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


async def send_work_complete_email(
    to: str,
    project_name: str,
    agent_type: str,
    task: str,
    outputs: list[dict],
    project_id: str,
) -> EmailResult:
    """
    Send email notification when work completes.

    Args:
        to: User's email address
        project_name: Name of the project
        agent_type: Type of agent (research, content, reporting)
        task: The task description
        outputs: List of output dicts with title, type, and summary
        project_id: Project ID for link

    Returns:
        EmailResult
    """
    # Build output list HTML
    output_html = ""
    output_text = ""
    for i, output in enumerate(outputs, 1):
        title = output.get("title", "Untitled")
        output_type = output.get("type", "output")
        summary = output.get("summary", "")

        output_html += f"""
        <div style="margin-bottom: 16px; padding: 12px; background: #f8f9fa; border-radius: 8px;">
            <strong style="color: #333;">{title}</strong>
            <span style="color: #666; font-size: 12px; margin-left: 8px;">({output_type})</span>
            {f'<p style="color: #555; margin: 8px 0 0 0; font-size: 14px;">{summary}</p>' if summary else ''}
        </div>
        """
        output_text += f"\n{i}. {title} ({output_type})"
        if summary:
            output_text += f"\n   {summary}"

    app_url = os.environ.get("APP_URL", "https://yarnnnn.vercel.app")
    work_url = f"{app_url}/projects/{project_id}?tab=work"

    html = f"""
    <html>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #111; margin-bottom: 4px;">Work Complete</h2>
        <p style="color: #666; margin-top: 0;">Your {agent_type} agent finished working on <strong>{project_name}</strong></p>

        <div style="background: #f0f0f0; padding: 12px; border-radius: 8px; margin: 16px 0;">
            <p style="margin: 0; color: #444;"><strong>Task:</strong> {task[:200]}{'...' if len(task) > 200 else ''}</p>
        </div>

        <h3 style="color: #333; margin-bottom: 12px;">Outputs ({len(outputs)})</h3>
        {output_html}

        <div style="margin-top: 24px;">
            <a href="{work_url}" style="display: inline-block; background: #111; color: #fff; padding: 12px 24px; text-decoration: none; border-radius: 6px;">
                View Full Results
            </a>
        </div>

        <p style="color: #888; font-size: 12px; margin-top: 32px;">
            You're receiving this because you requested work in YARNNN.
        </p>
    </body>
    </html>
    """

    text = f"""Work Complete

Your {agent_type} agent finished working on {project_name}.

Task: {task[:200]}{'...' if len(task) > 200 else ''}

Outputs ({len(outputs)}):
{output_text}

View full results: {work_url}

---
You're receiving this because you requested work in YARNNN.
"""

    return await send_email(
        to=to,
        subject=f"[YARNNN] {agent_type.title()} work complete: {task[:50]}{'...' if len(task) > 50 else ''}",
        html=html,
        text=text,
    )
