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
        "RESEND_FROM_EMAIL", "yarnnn <noreply@yarnnn.com>"
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
        subject="Test email from yarnnn",
        html="""
        <html>
        <body>
            <h1>Test Email</h1>
            <p>If you're seeing this, email delivery is working!</p>
            <p>- yarnnn</p>
        </body>
        </html>
        """,
        text="Test Email\n\nIf you're seeing this, email delivery is working!\n\n- yarnnn",
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

    app_url = os.environ.get("APP_URL", "https://yarnnn.com")
    # Link to dashboard with project context and outputs surface open
    work_url = f"{app_url}/dashboard?project={project_id}&surface=output"

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
            <a href="{work_url}" style="display: inline-block; background: #111; color: #fff; padding: 12px 24px; text-decoration: none; border-radius: 9999px; font-weight: 500;">
                View Results
            </a>
        </div>

        <p style="color: #888; font-size: 12px; margin-top: 32px;">
            You're receiving this because you requested work in yarnnn.
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
You're receiving this because you requested work in yarnnn.
"""

    # Create a contextual subject line with project name and task summary
    task_preview = task[:40].strip()
    if len(task) > 40:
        task_preview += "..."

    return await send_email(
        to=to,
        subject=f"{project_name}: {agent_type} work complete – {task_preview}",
        html=html,
        text=text,
    )


async def send_deliverable_ready_email(
    to: str,
    deliverable_title: str,
    deliverable_id: str,
    deliverable_type: str,
    schedule_description: str,
    next_run_at: Optional[str] = None,
) -> EmailResult:
    """
    Send email notification when a deliverable version is staged and ready for review.

    Args:
        to: User's email address
        deliverable_title: Title of the deliverable
        deliverable_id: Deliverable ID for link
        deliverable_type: Type (status_report, client_proposal, etc.)
        schedule_description: Human-readable schedule (e.g., "Every Monday at 9:00 AM")
        next_run_at: Next scheduled run time (ISO format)

    Returns:
        EmailResult
    """
    app_url = os.environ.get("APP_URL", "https://yarnnn.com")
    review_url = f"{app_url}/dashboard/deliverable/{deliverable_id}/review"

    # Format type for display
    type_display = deliverable_type.replace("_", " ").title()

    # Format next run
    next_run_display = ""
    if next_run_at:
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(next_run_at.replace("Z", "+00:00"))
            next_run_display = dt.strftime("%b %d, %Y at %I:%M %p")
        except Exception:
            next_run_display = next_run_at

    html = f"""
    <html>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #111; margin-bottom: 4px;">Ready for Review</h2>
        <p style="color: #666; margin-top: 0;">Your <strong>{type_display}</strong> has a new version ready.</p>

        <div style="background: #f8f9fa; padding: 16px; border-radius: 8px; margin: 20px 0;">
            <h3 style="margin: 0 0 8px 0; color: #333;">{deliverable_title}</h3>
            <p style="margin: 0; color: #666; font-size: 14px;">
                Schedule: {schedule_description}
            </p>
            {f'<p style="margin: 8px 0 0 0; color: #888; font-size: 13px;">Next run: {next_run_display}</p>' if next_run_display else ''}
        </div>

        <div style="margin-top: 24px;">
            <a href="{review_url}" style="display: inline-block; background: #111; color: #fff; padding: 12px 24px; text-decoration: none; border-radius: 9999px; font-weight: 500;">
                Review Now
            </a>
        </div>

        <p style="color: #888; font-size: 12px; margin-top: 32px;">
            You're receiving this because you have a recurring deliverable in Yarn.
            <a href="{app_url}/dashboard/settings" style="color: #888;">Manage notifications</a>
        </p>
    </body>
    </html>
    """

    text = f"""Ready for Review

Your {type_display} "{deliverable_title}" has a new version ready.

Schedule: {schedule_description}
{f"Next run: {next_run_display}" if next_run_display else ""}

Review now: {review_url}

---
You're receiving this because you have a recurring deliverable in Yarn.
"""

    return await send_email(
        to=to,
        subject=f"[Yarn] {deliverable_title} ready for review",
        html=html,
        text=text,
    )


async def send_deliverable_failed_email(
    to: str,
    deliverable_title: str,
    deliverable_id: str,
    error_message: str,
) -> EmailResult:
    """
    Send email notification when a deliverable generation fails.

    Args:
        to: User's email address
        deliverable_title: Title of the deliverable
        deliverable_id: Deliverable ID for link
        error_message: Error description

    Returns:
        EmailResult
    """
    app_url = os.environ.get("APP_URL", "https://yarnnn.com")
    deliverable_url = f"{app_url}/dashboard/deliverable/{deliverable_id}"

    html = f"""
    <html>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #111; margin-bottom: 4px;">Generation Failed</h2>
        <p style="color: #666; margin-top: 0;">There was a problem generating your deliverable.</p>

        <div style="background: #fef2f2; border: 1px solid #fecaca; padding: 16px; border-radius: 8px; margin: 20px 0;">
            <h3 style="margin: 0 0 8px 0; color: #333;">{deliverable_title}</h3>
            <p style="margin: 0; color: #991b1b; font-size: 14px;">
                {error_message[:200]}{'...' if len(error_message) > 200 else ''}
            </p>
        </div>

        <p style="color: #666; font-size: 14px;">
            We'll try again at the next scheduled time. If this continues, check your data sources
            or <a href="mailto:support@yarnnn.com" style="color: #111;">contact support</a>.
        </p>

        <div style="margin-top: 24px;">
            <a href="{deliverable_url}" style="display: inline-block; background: #111; color: #fff; padding: 12px 24px; text-decoration: none; border-radius: 9999px; font-weight: 500;">
                View Deliverable
            </a>
        </div>

        <p style="color: #888; font-size: 12px; margin-top: 32px;">
            You're receiving this because a scheduled deliverable failed.
        </p>
    </body>
    </html>
    """

    text = f"""Generation Failed

There was a problem generating "{deliverable_title}".

Error: {error_message[:200]}{'...' if len(error_message) > 200 else ''}

We'll try again at the next scheduled time. If this continues, check your data sources.

View deliverable: {deliverable_url}

---
You're receiving this because a scheduled deliverable failed.
"""

    return await send_email(
        to=to,
        subject=f"[Yarn] Failed to generate {deliverable_title}",
        html=html,
        text=text,
    )
