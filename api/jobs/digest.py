"""
YARNNN v5 - Digest Content Generation

Generates weekly digest content for a user:
- Recent deliverable versions (delivered, in progress)
- New memories added

ADR-090 Phase 3: Migrated from work_tickets/work_outputs → deliverable_versions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID


@dataclass
class DigestContent:
    """Structured digest content for email."""

    user_name: str
    period_start: datetime
    period_end: datetime

    # Activity counts (ADR-090: sourced from deliverable_versions)
    versions_delivered: int = 0
    versions_in_progress: int = 0
    memories_added: int = 0

    # Highlights (top items to feature)
    top_outputs: list[dict] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        """Check if there's any activity to report."""
        return (
            self.versions_delivered == 0
            and self.versions_in_progress == 0
            and self.memories_added == 0
        )

    @property
    def subject(self) -> str:
        """Email subject line."""
        if self.is_empty:
            return "yarnnn: Weekly digest – no activity this week"
        return f"yarnnn: Weekly digest – {self.versions_delivered} delivered, {self.memories_added} memories"

    @property
    def text(self) -> str:
        """Plain text email content."""
        lines = [
            f"Weekly Digest for {self.user_name}",
            f"Period: {self.period_start.strftime('%b %d')} - {self.period_end.strftime('%b %d, %Y')}",
            "",
        ]

        if self.is_empty:
            lines.append("No activity this week.")
            lines.append("")
            lines.append("Start a new deliverable to get things moving!")
        else:
            lines.append("Activity Summary:")
            lines.append(f"  - Deliverables completed: {self.versions_delivered}")
            lines.append(f"  - Deliverables in progress: {self.versions_in_progress}")
            lines.append(f"  - Memories added: {self.memories_added}")

            if self.top_outputs:
                lines.append("")
                lines.append("Recent Deliveries:")
                for output in self.top_outputs[:3]:
                    lines.append(f"  - {output['title']}")

        lines.append("")
        lines.append("---")
        lines.append("yarnnn")

        return "\n".join(lines)

    @property
    def html(self) -> str:
        """HTML email content."""
        # Minimal HTML email - could be templated later
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #1a1a1a; font-size: 24px; margin-bottom: 8px; }}
        .period {{ color: #666; font-size: 14px; margin-bottom: 24px; }}
        .stats {{ background: #f5f5f5; padding: 16px; border-radius: 8px; margin-bottom: 24px; }}
        .stat {{ display: inline-block; margin-right: 24px; }}
        .stat-value {{ font-size: 24px; font-weight: bold; color: #1a1a1a; }}
        .stat-label {{ font-size: 12px; color: #666; }}
        .section {{ margin-bottom: 24px; }}
        .section-title {{ font-size: 14px; font-weight: 600; color: #666; text-transform: uppercase; margin-bottom: 8px; }}
        .item {{ padding: 8px 0; border-bottom: 1px solid #eee; }}
        .footer {{ margin-top: 32px; padding-top: 16px; border-top: 1px solid #eee; font-size: 12px; color: #999; }}
    </style>
</head>
<body>
    <h1>Weekly Digest</h1>
    <div class="period">{self.period_start.strftime('%B %d')} - {self.period_end.strftime('%B %d, %Y')}</div>

    {"<p>No activity this week. Create a new deliverable to get things moving!</p>" if self.is_empty else f'''
    <div class="stats">
        <div class="stat">
            <div class="stat-value">{self.versions_delivered}</div>
            <div class="stat-label">Delivered</div>
        </div>
        <div class="stat">
            <div class="stat-value">{self.versions_in_progress}</div>
            <div class="stat-label">In Progress</div>
        </div>
        <div class="stat">
            <div class="stat-value">{self.memories_added}</div>
            <div class="stat-label">Memories</div>
        </div>
    </div>

    {"".join(f'<div class="section"><div class="section-title">Recent Outputs</div>' + "".join(f'<div class="item">{o["title"]}</div>' for o in self.top_outputs[:3]) + '</div>' if self.top_outputs else '')}
    '''}

    <div class="footer">
        yarnnn
    </div>
</body>
</html>
"""

    def to_dict(self) -> dict[str, Any]:
        """Serialize for storage in JSONB."""
        return {
            "user_name": self.user_name,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "versions_delivered": self.versions_delivered,
            "versions_in_progress": self.versions_in_progress,
            "memories_added": self.memories_added,
            "top_outputs": self.top_outputs,
        }


async def generate_digest_content(
    supabase_client,
    user_id: str,
    user_name: str,
) -> DigestContent:
    """
    Query database and generate digest content for a user.
    Looks at activity from the past 7 days.
    """
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    # Initialize content
    content = DigestContent(
        user_name=user_name,
        period_start=week_ago,
        period_end=now,
    )

    # ADR-090 Phase 3: Query deliverable_versions instead of work_tickets/work_outputs.
    # Join deliverable_versions → deliverables to scope by user_id and get titles.

    # Count delivered versions this week
    delivered_result = supabase_client.table("deliverable_versions").select(
        "id", count="exact"
    ).eq("status", "delivered").gte(
        "delivered_at", week_ago.isoformat()
    ).execute()
    # Filter by user via deliverable ownership (deliverable_versions has no user_id)
    # We fetch IDs via deliverables first
    user_deliverable_ids_result = supabase_client.table("deliverables").select(
        "id"
    ).eq("user_id", user_id).execute()
    user_deliverable_ids = [d["id"] for d in (user_deliverable_ids_result.data or [])]

    if user_deliverable_ids:
        delivered_result = supabase_client.table("deliverable_versions").select(
            "id", count="exact"
        ).in_("deliverable_id", user_deliverable_ids).eq(
            "status", "delivered"
        ).gte("delivered_at", week_ago.isoformat()).execute()
        content.versions_delivered = delivered_result.count or 0

        in_progress_result = supabase_client.table("deliverable_versions").select(
            "id", count="exact"
        ).in_("deliverable_id", user_deliverable_ids).eq(
            "status", "generating"
        ).execute()
        content.versions_in_progress = in_progress_result.count or 0

        # Recent delivered versions with deliverable titles for highlights
        recent_result = supabase_client.table("deliverable_versions").select(
            "id, deliverable_id, delivered_at, deliverables(title)"
        ).in_("deliverable_id", user_deliverable_ids).eq(
            "status", "delivered"
        ).gte("delivered_at", week_ago.isoformat()).order(
            "delivered_at", desc=True
        ).limit(5).execute()

        content.top_outputs = [
            {
                "title": (v.get("deliverables") or {}).get("title", "Untitled"),
                "delivered_at": v.get("delivered_at"),
            }
            for v in (recent_result.data or [])
        ]

    # Count new memories (ADR-059: user_memory entry-type keys)
    memories_result = supabase_client.table("user_memory").select(
        "id", count="exact"
    ).eq("user_id", user_id).or_(
        "key.like.fact:%,key.like.instruction:%,key.like.preference:%"
    ).gte(
        "created_at", week_ago.isoformat()
    ).execute()

    content.memories_added = memories_result.count or 0

    return content
