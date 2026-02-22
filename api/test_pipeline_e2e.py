"""
End-to-End Pipeline Test — ADR-072 System State Awareness Validation

Generates synthetic users with platform_content, runs full pipeline,
reports failures before quality assessment.

Usage:
    cd api && python test_pipeline_e2e.py

This tests:
1. Signal processing pass
2. Deliverable execution (headless TP mode)
3. Simulated user edit
4. Memory extraction
5. Second deliverable run (verify edit patterns reflected)

If execution fails at any step, stops and reports exact error.
"""

import asyncio
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

# Load .env
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key] = value

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# Phase 1: Synthetic Fixture Definitions
# =============================================================================

@dataclass
class SyntheticUser:
    """Synthetic user persona with platform content."""
    name: str
    email: str
    role: str
    company: str
    timezone: str
    platforms: list[str]
    content_records: list[dict] = field(default_factory=list)
    deliverable_config: Optional[dict] = None
    edit_instructions: list[str] = field(default_factory=list)
    user_id: Optional[str] = None  # Set after creation


# Maya: Client-focused Growth Lead
MAYA = SyntheticUser(
    name="Maya Chen",
    email=f"maya.test.{uuid4().hex[:8]}@yarnnn-test.local",
    role="Growth Lead",
    company="Acme Corp",
    timezone="America/Los_Angeles",
    platforms=["gmail"],
    content_records=[
        # Gmail: Client project status (14 days, 2 labels)
        {"platform": "gmail", "resource_name": "Client/ProjectAlpha", "title": "Re: Project Alpha Status Update", "content": "Hi Maya, the Q1 deliverables are on track. We've completed the analytics dashboard integration and are moving to phase 2. Main blocker: waiting on API credentials from their IT team. Best, Sarah", "days_ago": 1},
        {"platform": "gmail", "resource_name": "Client/ProjectAlpha", "title": "Project Alpha - Weekly Sync Notes", "content": "Attendees: Maya, Sarah, Client PM. Action items: 1) Finalize dashboard mockups by Friday 2) Schedule technical review with their engineering 3) Follow up on API access. Next sync: Thursday 2pm.", "days_ago": 3},
        {"platform": "gmail", "resource_name": "Client/ProjectAlpha", "title": "Re: Analytics Dashboard Feedback", "content": "Maya, the client loved the dashboard mockups! Only feedback: they want the date picker to default to last 30 days instead of 7. Can we make that change before Thursday?", "days_ago": 5},
        {"platform": "gmail", "resource_name": "Client/ProjectAlpha", "title": "Project Alpha - Budget Approval", "content": "Good news - the additional budget for the premium API tier has been approved. We can proceed with the advanced analytics features. Please update the timeline accordingly.", "days_ago": 7},
        {"platform": "gmail", "resource_name": "Client/ProjectAlpha", "title": "Re: Phase 1 Completion", "content": "Phase 1 is officially complete. All 12 user stories delivered, 2 minor bugs logged for Phase 2 backlog. Client NPS: 8/10. Scheduling retrospective for next week.", "days_ago": 10},
        {"platform": "gmail", "resource_name": "Client/ProjectBeta", "title": "Project Beta - Kickoff Prep", "content": "Maya, we're prepping for the Beta kickoff next Monday. Can you confirm the scope document is finalized? Also need your input on the resource allocation.", "days_ago": 2},
        {"platform": "gmail", "resource_name": "Client/ProjectBeta", "title": "Re: Beta Stakeholder List", "content": "Here's the confirmed stakeholder list for Project Beta: 1) VP of Product (exec sponsor) 2) Engineering Lead (technical) 3) Product Manager (day-to-day). First checkpoint: end of month.", "days_ago": 4},
        {"platform": "gmail", "resource_name": "Client/ProjectBeta", "title": "Beta - Technical Requirements", "content": "Requirements doc attached. Key points: SSO integration required, mobile-responsive design, 99.9% uptime SLA. Let's discuss any concerns in Thursday's sync.", "days_ago": 6},
        {"platform": "gmail", "resource_name": "Client/ProjectBeta", "title": "Re: Resource Constraints", "content": "Maya, heads up - we may have a resource conflict in week 3. The senior dev originally allocated is now needed for a critical bug fix. Working on alternatives.", "days_ago": 8},
        {"platform": "gmail", "resource_name": "Client/ProjectBeta", "title": "Beta Timeline Concerns", "content": "The client is asking if we can compress the timeline by 2 weeks. I think it's risky but wanted your input before pushing back. Their Q2 deadline is driving this.", "days_ago": 12},
        # Additional emails for variety
        {"platform": "gmail", "resource_name": "INBOX", "title": "Team OOO Next Week", "content": "Hi team, reminder that I'll be OOO Monday-Tuesday for the offsite. Sarah will cover urgent items. Best, David", "days_ago": 1},
        {"platform": "gmail", "resource_name": "INBOX", "title": "Q1 Planning Finalized", "content": "Team, Q1 planning is complete. Key focus areas: 1) Client retention 2) New feature rollout 3) Team scaling. OKRs attached.", "days_ago": 9},
        {"platform": "gmail", "resource_name": "INBOX", "title": "Expense Report Reminder", "content": "Friendly reminder to submit Q4 expense reports by Friday. Let me know if you have questions.", "days_ago": 11},
        {"platform": "gmail", "resource_name": "INBOX", "title": "New Team Member Starting", "content": "Please welcome Alex who joins as Product Designer next Monday. I'll send calendar invites for intro 1:1s.", "days_ago": 13},
        {"platform": "gmail", "resource_name": "INBOX", "title": "Holiday Schedule", "content": "Office will be closed Dec 23-26 and Dec 30-Jan 1. Please plan accordingly.", "days_ago": 14},
    ],
    deliverable_config={
        "title": "Client Project Brief",
        "deliverable_type": "intelligence_brief",
        "schedule": {"frequency": "weekly", "day": "monday", "time": "09:00", "timezone": "America/Los_Angeles"},
        "sources": [{"type": "integration_import", "provider": "google", "source": "gmail"}],
        "recipient_context": {"name": "Self", "channel": "review"},
    },
    edit_instructions=[
        "Soften the phrase about 'resource conflict' to 'resource adjustment'",
        "Remove the sentence about expense report reminder",
        "Add 'Priority: High' to the Beta timeline section",
    ],
)


# James: Product-focused founder
JAMES = SyntheticUser(
    name="James Park",
    email=f"james.test.{uuid4().hex[:8]}@yarnnn-test.local",
    role="Founder & CEO",
    company="StartupXYZ",
    timezone="America/New_York",
    platforms=["slack", "gmail", "notion"],
    content_records=[
        # Slack: Product discussions
        {"platform": "slack", "resource_name": "#product", "title": "Feature shipped", "content": "Just shipped the new onboarding flow! Conversion from signup to first action improved by 15% in A/B test.", "days_ago": 1, "author": "sarah"},
        {"platform": "slack", "resource_name": "#product", "title": "Metrics update", "content": "DAU hit 12.5k yesterday, up 8% WoW. Retention at 7-day still 42%, working on push notifications to improve.", "days_ago": 2, "author": "james"},
        {"platform": "slack", "resource_name": "#product", "title": "User feedback", "content": "Got feedback from 3 enterprise prospects: they all want SSO. Moving up in roadmap priority.", "days_ago": 3, "author": "mike"},
        {"platform": "slack", "resource_name": "#product", "title": "Roadmap discussion", "content": "Q2 roadmap draft is ready. Big bets: 1) Enterprise tier 2) Mobile app v2 3) API marketplace. Review session tomorrow.", "days_ago": 4, "author": "james"},
        {"platform": "slack", "resource_name": "#product", "title": "Competitor alert", "content": "Competitor Y just announced a similar feature. Their pricing is 20% lower. Should we adjust our positioning?", "days_ago": 5, "author": "lisa"},
        {"platform": "slack", "resource_name": "#product", "title": "Launch prep", "content": "All systems go for the enterprise launch next week. Marketing has the press release draft, engineering confirmed feature freeze.", "days_ago": 6, "author": "sarah"},
        {"platform": "slack", "resource_name": "#product", "title": "Support tickets", "content": "Seeing increase in support tickets around billing. Main issue: customers don't understand usage-based pricing. Need better docs.", "days_ago": 7, "author": "support-bot"},
        {"platform": "slack", "resource_name": "#product", "title": "Design review", "content": "New dashboard designs look great. One concern: the analytics section feels cluttered. Simplify before shipping?", "days_ago": 8, "author": "james"},
        {"platform": "slack", "resource_name": "#product", "title": "Customer call", "content": "Just finished call with our largest customer. They want to expand from 50 to 200 seats. Pricing discussion next week.", "days_ago": 9, "author": "mike"},
        {"platform": "slack", "resource_name": "#product", "title": "Sprint planning", "content": "Sprint 24 planned. Focus: performance improvements and the SSO feature. 8 story points committed.", "days_ago": 10, "author": "sarah"},
        # Slack: Engineering
        {"platform": "slack", "resource_name": "#engineering", "title": "Deploy complete", "content": "v2.4.1 deployed to production. No issues so far. Monitoring dashboards look clean.", "days_ago": 1, "author": "alex"},
        {"platform": "slack", "resource_name": "#engineering", "title": "Incident resolved", "content": "The DB connection pool issue from this morning is resolved. Root cause: connection leak in the batch job. PR merged.", "days_ago": 2, "author": "alex"},
        {"platform": "slack", "resource_name": "#engineering", "title": "Tech debt", "content": "Added 3 tech debt items to the backlog: 1) Upgrade to Node 20 2) Migrate to new auth library 3) Clean up deprecated endpoints", "days_ago": 3, "author": "chris"},
        {"platform": "slack", "resource_name": "#engineering", "title": "Code review", "content": "SSO PR is ready for review. It's a big one - 1.2k lines changed. Need 2 approvals before merge.", "days_ago": 4, "author": "alex"},
        {"platform": "slack", "resource_name": "#engineering", "title": "Performance update", "content": "After the caching optimization, p95 latency dropped from 450ms to 180ms. Users are noticing the improvement.", "days_ago": 5, "author": "chris"},
        {"platform": "slack", "resource_name": "#engineering", "title": "On-call handoff", "content": "On-call handoff complete. Quiet week - only 2 alerts, both false positives. Tuning thresholds tomorrow.", "days_ago": 6, "author": "alex"},
        {"platform": "slack", "resource_name": "#engineering", "title": "Security scan", "content": "Weekly security scan clean. No new vulnerabilities. Dependencies up to date.", "days_ago": 7, "author": "security-bot"},
        {"platform": "slack", "resource_name": "#engineering", "title": "New hire onboarding", "content": "Emma starts Monday as senior backend engineer. Assigning her to the API marketplace project.", "days_ago": 8, "author": "james"},
        # Slack: General
        {"platform": "slack", "resource_name": "#general", "title": "Team lunch", "content": "Team lunch tomorrow at 12:30. Thai place on 5th. Please RSVP in thread.", "days_ago": 2, "author": "office-bot"},
        {"platform": "slack", "resource_name": "#general", "title": "All hands", "content": "All hands Friday 3pm. Agenda: Q1 retro, Q2 goals, new hires intro. Pizza provided.", "days_ago": 5, "author": "james"},
        # Gmail: Investor updates
        {"platform": "gmail", "resource_name": "Investors", "title": "Monthly Investor Update - January", "content": "Hi investors, January highlights: ARR grew to $1.2M (+12% MoM), closed 3 enterprise deals, shipped SSO. Challenges: churn in SMB segment, working on retention features. Fundraise timing: exploring Series A conversations in Q2.", "days_ago": 5, "author": "james"},
        {"platform": "gmail", "resource_name": "Investors", "title": "Re: Board Meeting Prep", "content": "James, materials look good. One question: can you add a slide on competitive landscape? Board wants to understand our differentiation vs. the recent entrant.", "days_ago": 8, "author": "investor"},
        {"platform": "gmail", "resource_name": "Investors", "title": "Intro: Series A Lead Candidate", "content": "James, introducing you to Sarah from Venture Partners. She's interested in learning more about StartupXYZ for a potential Series A lead. I've cc'd her here.", "days_ago": 10, "author": "advisor"},
        {"platform": "gmail", "resource_name": "Investors", "title": "Re: Runway Update", "content": "Current runway: 14 months. We're not in a rush but starting Series A conversations now to have options. Will keep you posted on progress.", "days_ago": 12, "author": "james"},
        {"platform": "gmail", "resource_name": "Investors", "title": "Q4 Board Deck", "content": "Attached is the Q4 board deck. Key metrics on slide 3, product roadmap on slide 7, hiring plan on slide 12. Let me know if you have questions before the meeting.", "days_ago": 14, "author": "james"},
        # Notion: Roadmap
        {"platform": "notion", "resource_name": "Product", "title": "Q2 Roadmap", "content": "## Q2 Roadmap\n\n### April\n- Enterprise tier launch\n- SSO + SCIM\n- Usage analytics dashboard\n\n### May\n- Mobile app v2\n- Push notifications\n- Offline mode\n\n### June\n- API marketplace beta\n- Partner integrations\n- Self-serve billing", "days_ago": 3, "author": "james"},
    ],
    deliverable_config={
        "title": "Weekly Founder Brief",
        "deliverable_type": "daily_strategy_reflection",
        "schedule": {"frequency": "weekly", "day": "friday", "time": "17:00", "timezone": "America/New_York"},
        "sources": [
            {"type": "integration_import", "provider": "slack", "source": "#product"},
            {"type": "integration_import", "provider": "slack", "source": "#engineering"},
            {"type": "integration_import", "provider": "google", "source": "gmail"},
        ],
        "recipient_context": {"name": "Self", "channel": "review"},
    },
    edit_instructions=[
        "Cut the output to 50% length - keep only strategic items",
        "Move the 'Key Decisions' section to the top",
        "Remove operational details about deploys and incidents",
    ],
)


# Sarah: Engineering Lead
SARAH = SyntheticUser(
    name="Sarah Kim",
    email=f"sarah.test.{uuid4().hex[:8]}@yarnnn-test.local",
    role="Engineering Lead",
    company="TechCo",
    timezone="America/Chicago",
    platforms=["slack"],
    content_records=[
        # Engineering discussions
        {"platform": "slack", "resource_name": "#engineering", "title": "Architecture RFC", "content": "Posted RFC for the new event-driven architecture. Key change: moving from REST polling to WebSocket push. Review deadline: Friday.", "days_ago": 1, "author": "sarah"},
        {"platform": "slack", "resource_name": "#engineering", "title": "PR merged", "content": "Merged the authentication refactor. Breaking change: JWT tokens now expire after 24h instead of 7 days. Migration guide in docs.", "days_ago": 1, "author": "alex"},
        {"platform": "slack", "resource_name": "#engineering", "title": "Load test results", "content": "Load test complete. System handles 10k concurrent users with p99 < 200ms. Bottleneck identified: DB connection pool. Increasing to 50 connections.", "days_ago": 2, "author": "sarah"},
        {"platform": "slack", "resource_name": "#engineering", "title": "Incident postmortem", "content": "Postmortem for yesterday's outage published. Root cause: runaway query on analytics table. Action items: add query timeout, improve monitoring.", "days_ago": 2, "author": "chris"},
        {"platform": "slack", "resource_name": "#engineering", "title": "Code freeze reminder", "content": "Reminder: code freeze starts Monday for the enterprise launch. Only critical bug fixes after that. Get your PRs in by EOD Friday.", "days_ago": 3, "author": "sarah"},
        {"platform": "slack", "resource_name": "#engineering", "title": "New service deployed", "content": "The notification service is now live. It handles email, push, and in-app notifications. Dashboard for monitoring in Grafana.", "days_ago": 3, "author": "emma"},
        {"platform": "slack", "resource_name": "#engineering", "title": "Dependency update", "content": "Updated all dependencies to latest versions. No breaking changes. Run npm install after pulling latest.", "days_ago": 4, "author": "alex"},
        {"platform": "slack", "resource_name": "#engineering", "title": "Feature flag setup", "content": "Added feature flags for the new billing system. Flags: BILLING_V2, USAGE_TRACKING, STRIPE_CHECKOUT. All off in production until launch.", "days_ago": 4, "author": "sarah"},
        {"platform": "slack", "resource_name": "#engineering", "title": "API docs update", "content": "API documentation updated for v2.5. New endpoints: /webhooks, /usage, /billing. Swagger spec in the repo.", "days_ago": 5, "author": "chris"},
        {"platform": "slack", "resource_name": "#engineering", "title": "Database migration", "content": "Running the partition migration tonight at 11pm. Expected downtime: 15 minutes. Runbook linked in thread.", "days_ago": 5, "author": "alex"},
        {"platform": "slack", "resource_name": "#engineering", "title": "Hiring update", "content": "Two candidates moving to final round for senior backend role. Interviews next week. Sarah and Chris on the panel.", "days_ago": 6, "author": "hr-bot"},
        {"platform": "slack", "resource_name": "#engineering", "title": "Tech talk", "content": "Reminder: tech talk tomorrow on observability best practices. 2pm in the main conference room. Recording available after.", "days_ago": 6, "author": "sarah"},
        {"platform": "slack", "resource_name": "#engineering", "title": "Sprint retro", "content": "Sprint retro notes: What went well - SSO delivery, team collaboration. What to improve - more time for code review, better test coverage.", "days_ago": 7, "author": "scrum-bot"},
        {"platform": "slack", "resource_name": "#engineering", "title": "Monitoring alert", "content": "Alert: memory usage on api-prod-3 at 85%. Not critical yet but watching. May need to scale horizontally.", "days_ago": 7, "author": "pagerduty-bot"},
        {"platform": "slack", "resource_name": "#engineering", "title": "Design review", "content": "Reviewed the new error handling UX. Looks good but needs more specific error messages. Feedback shared in Figma.", "days_ago": 8, "author": "sarah"},
        # Product channel
        {"platform": "slack", "resource_name": "#product", "title": "Launch checklist", "content": "Enterprise launch checklist: 1) Feature complete ✓ 2) QA sign-off ✓ 3) Docs ready ✓ 4) Marketing ready ⏳ 5) Support trained ⏳", "days_ago": 1, "author": "pm"},
        {"platform": "slack", "resource_name": "#product", "title": "Customer feedback", "content": "Customer feedback from beta: SSO works great, onboarding could be smoother, would like more granular permissions.", "days_ago": 2, "author": "support"},
        {"platform": "slack", "resource_name": "#product", "title": "Pricing discussion", "content": "Pricing for enterprise tier: $500/month for up to 100 users, $4/user after. Includes SSO, audit logs, dedicated support.", "days_ago": 3, "author": "james"},
        {"platform": "slack", "resource_name": "#product", "title": "Demo request", "content": "Fortune 500 company requested a demo for next week. Sarah, can you join to answer technical questions?", "days_ago": 4, "author": "sales"},
        {"platform": "slack", "resource_name": "#product", "title": "Beta results", "content": "Beta results summary: 12 companies participated, 8 converting to paid, 3 need more features, 1 churned (bad fit).", "days_ago": 5, "author": "pm"},
        {"platform": "slack", "resource_name": "#product", "title": "Competitor analysis", "content": "Updated competitor analysis in Notion. Key insight: we're the only one with real-time sync. Others batch every 15 minutes.", "days_ago": 6, "author": "analyst"},
        {"platform": "slack", "resource_name": "#product", "title": "Feature request", "content": "Top feature request this week: Slack integration for notifications. 15 customers asked for it. Adding to Q2 backlog.", "days_ago": 7, "author": "support"},
        {"platform": "slack", "resource_name": "#product", "title": "Roadmap update", "content": "Roadmap updated based on customer feedback. Moved Slack integration up, pushed API marketplace to Q3.", "days_ago": 8, "author": "pm"},
        {"platform": "slack", "resource_name": "#product", "title": "Launch date", "content": "Confirmed: Enterprise tier launches March 15. Press release goes out same day. All hands prep meeting tomorrow.", "days_ago": 9, "author": "james"},
        {"platform": "slack", "resource_name": "#product", "title": "Training materials", "content": "Training materials for support team ready. Includes FAQ, troubleshooting guide, and escalation procedures.", "days_ago": 10, "author": "sarah"},
    ],
    deliverable_config={
        "title": "Engineering Weekly Digest",
        "deliverable_type": "intelligence_brief",
        "schedule": {"frequency": "weekly", "day": "friday", "time": "16:00", "timezone": "America/Chicago"},
        "sources": [
            {"type": "integration_import", "provider": "slack", "source": "#engineering"},
            {"type": "integration_import", "provider": "slack", "source": "#product"},
        ],
        "recipient_context": {"name": "Team", "channel": "slack"},
    },
    edit_instructions=[
        "Cut the output to 40% of original length",
        "Move the 'Key Technical Decisions' section to the top",
        "Remove routine items like dependency updates and bot messages",
    ],
)

PERSONAS = [MAYA, JAMES, SARAH]


# =============================================================================
# Phase 1: Fixture Creation
# =============================================================================

async def create_synthetic_user(client: Any, persona: SyntheticUser) -> str:
    """Create a synthetic user with platform content. Returns user_id."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Creating synthetic user: {persona.name}")
    logger.info(f"{'='*60}")

    # Use existing test user (FK constraint requires user in auth.users)
    # kvkthecreator@gmail.com is the primary test account
    TEST_USER_ID = "2abf3f96-118b-4987-9d95-40f2d9be9a18"
    user_id = TEST_USER_ID
    persona.user_id = user_id
    now = datetime.now(timezone.utc)

    # Use test prefix for cleanup
    test_prefix = f"TEST_{persona.name.replace(' ', '_').upper()}_"

    try:
        # 0. Clean up any previous test data for this persona first
        logger.info(f"  Cleaning up previous test data...")
        persona_deliverable_title = persona.deliverable_config.get("title") if persona.deliverable_config else None
        await cleanup_synthetic_user(client, user_id, persona.name, persona_deliverable_title)

        # 1. Create user_context (profile) with test prefix keys (upsert pattern)
        logger.info(f"  Creating user_context...")
        profile_rows = [
            {"key": f"{test_prefix}name", "value": persona.name},
            {"key": f"{test_prefix}role", "value": persona.role},
            {"key": f"{test_prefix}company", "value": persona.company},
            {"key": f"{test_prefix}timezone", "value": persona.timezone},
        ]

        for row in profile_rows:
            # Check if exists
            existing = (
                client.table("user_context")
                .select("id")
                .eq("user_id", user_id)
                .eq("key", row["key"])
                .execute()
            )
            if existing.data:
                # Update
                client.table("user_context").update({
                    "value": row["value"],
                    "updated_at": now.isoformat(),
                }).eq("user_id", user_id).eq("key", row["key"]).execute()
            else:
                # Insert
                client.table("user_context").insert({
                    "user_id": user_id,
                    "key": row["key"],
                    "value": row["value"],
                    "source": "user_stated",
                    "confidence": 1.0,
                }).execute()
        logger.info(f"    ✓ Ensured {len(profile_rows)} user_context rows")

        # 2. Create/update platform_connections (upsert to handle existing)
        logger.info(f"  Creating platform_connections...")
        for platform in persona.platforms:
            # Check if connection exists
            existing = (
                client.table("platform_connections")
                .select("id")
                .eq("user_id", user_id)
                .eq("platform", platform)
                .execute()
            )
            if existing.data:
                # Update existing connection
                client.table("platform_connections").update({
                    "status": "active",
                    "last_synced_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                }).eq("user_id", user_id).eq("platform", platform).execute()
            else:
                # Create new connection
                conn_row = {
                    "id": str(uuid4()),
                    "user_id": user_id,
                    "platform": platform,
                    "status": "active",
                    "credentials_encrypted": "test_encrypted_creds",
                    "last_synced_at": now.isoformat(),
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                }
                client.table("platform_connections").insert(conn_row).execute()
        logger.info(f"    ✓ Ensured {len(persona.platforms)} platform_connections")

        # 3. Create platform_content records
        logger.info(f"  Creating platform_content ({len(persona.content_records)} records)...")
        for record in persona.content_records:
            days_ago = record.get("days_ago", 0)
            source_timestamp = (now - timedelta(days=days_ago)).isoformat()

            content_row = {
                "id": str(uuid4()),
                "user_id": user_id,
                "platform": record["platform"],
                "resource_id": record["resource_name"].replace("/", "_").replace("#", ""),
                "resource_name": record["resource_name"],
                "item_id": str(uuid4()),
                "content": record["content"],
                "content_type": "message" if record["platform"] == "slack" else "email",
                "title": record.get("title", ""),
                "author": record.get("author", persona.name.split()[0].lower()),
                "is_user_authored": record.get("author", "").lower() == persona.name.split()[0].lower(),
                "source_timestamp": source_timestamp,
                "fetched_at": now.isoformat(),
                "retained": True,  # Simulate post-sync retained state
                "retained_reason": "test_fixture",
                "retained_at": now.isoformat(),
                "created_at": now.isoformat(),
            }
            client.table("platform_content").insert(content_row).execute()
        logger.info(f"    ✓ Created {len(persona.content_records)} platform_content records")

        # 4. Create/update sync_registry entries (upsert to handle existing)
        logger.info(f"  Creating sync_registry...")
        resources = set((r["platform"], r["resource_name"]) for r in persona.content_records)
        for platform, resource_name in resources:
            resource_id = resource_name.replace("/", "_").replace("#", "")
            # Check if entry exists
            existing = (
                client.table("sync_registry")
                .select("id")
                .eq("user_id", user_id)
                .eq("platform", platform)
                .eq("resource_id", resource_id)
                .execute()
            )
            item_count = len([r for r in persona.content_records if r["resource_name"] == resource_name])
            if existing.data:
                # Update existing entry
                client.table("sync_registry").update({
                    "last_synced_at": now.isoformat(),
                    "item_count": item_count,
                    "updated_at": now.isoformat(),
                }).eq("user_id", user_id).eq("platform", platform).eq("resource_id", resource_id).execute()
            else:
                # Create new entry
                sync_row = {
                    "id": str(uuid4()),
                    "user_id": user_id,
                    "platform": platform,
                    "resource_id": resource_id,
                    "resource_name": resource_name,
                    "last_synced_at": now.isoformat(),
                    "item_count": item_count,
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                }
                client.table("sync_registry").insert(sync_row).execute()
        logger.info(f"    ✓ Ensured {len(resources)} sync_registry entries")

        # 5. Create deliverable (with test marker in title for cleanup)
        if persona.deliverable_config:
            logger.info(f"  Creating deliverable...")
            deliverable_id = str(uuid4())
            test_title = f"[TEST] {persona.deliverable_config['title']}"
            deliverable_row = {
                "id": deliverable_id,
                "user_id": user_id,
                "title": test_title,
                "deliverable_type": persona.deliverable_config["deliverable_type"],
                "status": "active",
                "schedule": persona.deliverable_config["schedule"],
                "sources": persona.deliverable_config["sources"],
                "recipient_context": persona.deliverable_config["recipient_context"],
                "next_run_at": now.isoformat(),
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }
            client.table("deliverables").insert(deliverable_row).execute()
            persona.deliverable_config["id"] = deliverable_id
            persona.deliverable_config["test_title"] = test_title
            logger.info(f"    ✓ Created deliverable: {test_title}")

        logger.info(f"  ✓ User {persona.name} created successfully (id: {user_id})")
        return user_id

    except Exception as e:
        logger.error(f"  ✗ Failed to create user {persona.name}: {e}")
        import traceback
        traceback.print_exc()
        raise


async def cleanup_synthetic_user(client: Any, user_id: str, persona_name: str, persona_deliverable_title: str = None) -> None:
    """Clean up synthetic user data. Only deletes test-marked records for this persona."""
    logger.info(f"  Cleaning up {persona_name}...")

    test_prefix = f"TEST_{persona_name.replace(' ', '_').upper()}_"

    try:
        # Delete user_context with test prefix for this persona only
        client.table("user_context").delete().eq("user_id", user_id).like("key", f"{test_prefix}%").execute()
    except Exception:
        pass

    try:
        # Delete test deliverables for this persona only (use persona-specific title)
        if persona_deliverable_title:
            test_title = f"[TEST] {persona_deliverable_title}"
            # First get IDs to delete versions
            deliverables_result = client.table("deliverables").select("id").eq("user_id", user_id).eq("title", test_title).execute()
            for d in (deliverables_result.data or []):
                try:
                    client.table("deliverable_versions").delete().eq("deliverable_id", d["id"]).execute()
                except Exception:
                    pass
            client.table("deliverables").delete().eq("user_id", user_id).eq("title", test_title).execute()
    except Exception:
        pass

    try:
        # Delete platform_content with test_fixture retained_reason
        client.table("platform_content").delete().eq("user_id", user_id).eq("retained_reason", "test_fixture").execute()
    except Exception:
        pass

    try:
        # Delete sync_registry entries for test resources
        # These have resource_names that don't match real resources
        client.table("sync_registry").delete().eq("user_id", user_id).like("resource_name", "Client%").execute()
        client.table("sync_registry").delete().eq("user_id", user_id).like("resource_name", "#%").execute()
        client.table("sync_registry").delete().eq("user_id", user_id).like("resource_name", "Investors").execute()
        client.table("sync_registry").delete().eq("user_id", user_id).like("resource_name", "Product").execute()
    except Exception:
        pass

    try:
        # Delete activity_log test events (signal_processed with test deliverables)
        # This is best-effort - we can't easily identify test events
        pass
    except Exception:
        pass

    logger.info(f"  ✓ Cleaned up {persona_name}")


# =============================================================================
# Phase 2: Pipeline Execution
# =============================================================================

@dataclass
class StepResult:
    """Result of a single pipeline step."""
    step_name: str
    success: bool
    data: Any = None
    error: Optional[str] = None
    traceback: Optional[str] = None
    tables_queried: list[str] = field(default_factory=list)


@dataclass
class PipelineResult:
    """Result of full pipeline execution for a persona."""
    persona_name: str
    steps: list[StepResult] = field(default_factory=list)
    completed: bool = False


async def run_pipeline_for_persona(client: Any, persona: SyntheticUser) -> PipelineResult:
    """Run the full 5-step pipeline for a persona."""
    logger.info(f"\n{'='*60}")
    logger.info(f"PIPELINE: {persona.name}")
    logger.info(f"{'='*60}")

    result = PipelineResult(persona_name=persona.name)
    user_id = persona.user_id

    # Step 1: Signal Processing
    logger.info(f"\n  Step 1: Signal Processing")
    step1 = await run_signal_processing(client, user_id, persona)
    result.steps.append(step1)
    if not step1.success:
        logger.error(f"    ✗ Step 1 failed: {step1.error}")
        return result
    logger.info(f"    ✓ Step 1 complete: {step1.data}")

    # Step 2: Deliverable Execution
    logger.info(f"\n  Step 2: Deliverable Execution")
    step2 = await run_deliverable_execution(client, user_id, persona)
    result.steps.append(step2)
    if not step2.success:
        logger.error(f"    ✗ Step 2 failed: {step2.error}")
        return result
    logger.info(f"    ✓ Step 2 complete: generated version")

    # Step 3: Simulate User Edit
    logger.info(f"\n  Step 3: Simulate User Edit")
    step3 = await simulate_user_edit(client, user_id, persona, step2.data)
    result.steps.append(step3)
    if not step3.success:
        logger.error(f"    ✗ Step 3 failed: {step3.error}")
        return result
    logger.info(f"    ✓ Step 3 complete: applied {len(persona.edit_instructions)} edits")

    # Step 4: Memory Extraction
    logger.info(f"\n  Step 4: Memory Extraction")
    step4 = await run_memory_extraction(client, user_id, persona, step3.data)
    result.steps.append(step4)
    if not step4.success:
        logger.error(f"    ✗ Step 4 failed: {step4.error}")
        return result
    logger.info(f"    ✓ Step 4 complete: extracted {step4.data.get('count', 0)} memories")

    # Step 5: Second Deliverable Run
    logger.info(f"\n  Step 5: Second Deliverable Run")
    step5 = await run_deliverable_execution(client, user_id, persona, is_second_run=True)
    result.steps.append(step5)
    if not step5.success:
        logger.error(f"    ✗ Step 5 failed: {step5.error}")
        return result
    logger.info(f"    ✓ Step 5 complete: generated v2")

    result.completed = True
    logger.info(f"\n  ✓ Pipeline complete for {persona.name}")
    return result


async def run_signal_processing(client: Any, user_id: str, persona: SyntheticUser) -> StepResult:
    """Step 1: Run signal processing."""
    try:
        from services.signal_extraction import extract_signal_summary
        from services.signal_processing import process_signal, execute_signal_actions
        from services.activity_log import get_recent_activity

        # Extract signals
        signal_summary = await extract_signal_summary(client, user_id, signals_filter="all")

        if not signal_summary.has_signals:
            return StepResult(
                step_name="signal_processing",
                success=True,
                data={"signals_found": False, "actions": []},
                tables_queried=["platform_content", "platform_connections"],
            )

        # Get context for reasoning
        user_context_result = (
            client.table("user_context")
            .select("key, value")
            .eq("user_id", user_id)
            .limit(20)
            .execute()
        )
        user_context = user_context_result.data or []

        recent_activity = await get_recent_activity(client, user_id, limit=10, days=7)

        existing_deliverables = (
            client.table("deliverables")
            .select("id, title, deliverable_type, next_run_at, status")
            .eq("user_id", user_id)
            .in_("status", ["active", "paused"])
            .execute()
        ).data or []

        # Process signals
        processing_result = await process_signal(
            client=client,
            user_id=user_id,
            signal_summary=signal_summary,
            user_context=user_context,
            recent_activity=recent_activity,
            existing_deliverables=existing_deliverables,
        )

        # Execute actions
        created = 0
        if processing_result.actions:
            created = await execute_signal_actions(client, user_id, processing_result)

        return StepResult(
            step_name="signal_processing",
            success=True,
            data={
                "signals_found": True,
                "actions": [a.action_type for a in processing_result.actions],
                "deliverables_created": created,
            },
            tables_queried=["platform_content", "platform_connections", "user_context", "activity_log", "deliverables"],
        )

    except Exception as e:
        import traceback
        return StepResult(
            step_name="signal_processing",
            success=False,
            error=str(e),
            traceback=traceback.format_exc(),
            tables_queried=["platform_content", "platform_connections"],
        )


async def run_deliverable_execution(
    client: Any,
    user_id: str,
    persona: SyntheticUser,
    is_second_run: bool = False,
) -> StepResult:
    """Step 2/5: Run deliverable execution."""
    try:
        from services.deliverable_execution import execute_deliverable_generation

        deliverable_id = persona.deliverable_config.get("id")
        if not deliverable_id:
            return StepResult(
                step_name="deliverable_execution",
                success=False,
                error="No deliverable configured for persona",
            )

        # Fetch deliverable
        result = (
            client.table("deliverables")
            .select("*")
            .eq("id", deliverable_id)
            .single()
            .execute()
        )

        if not result.data:
            return StepResult(
                step_name="deliverable_execution",
                success=False,
                error=f"Deliverable not found: {deliverable_id}",
            )

        deliverable = result.data

        # Execute
        exec_result = await execute_deliverable_generation(
            client=client,
            user_id=user_id,
            deliverable=deliverable,
            trigger_context={"type": "test", "run": 2 if is_second_run else 1},
        )

        # Check if content was generated (version_id means content was created)
        version_id = exec_result.get("version_id")
        if not version_id:
            return StepResult(
                step_name="deliverable_execution",
                success=False,
                error=exec_result.get("message", exec_result.get("error", "No version created")),
                tables_queried=["deliverables", "deliverable_versions", "platform_content"],
            )

        # Get the generated content from the version
        version_result = client.table("deliverable_versions").select(
            "draft_content, final_content, status, delivery_status"
        ).eq("id", version_id).single().execute()

        content = ""
        if version_result.data:
            content = version_result.data.get("final_content") or version_result.data.get("draft_content", "")

        # Consider successful if content was generated, even if delivery failed
        # (delivery failure is expected in test environment without OAuth)
        generation_success = bool(content)
        delivery_status = version_result.data.get("delivery_status") if version_result.data else None

        return StepResult(
            step_name="deliverable_execution",
            success=generation_success,
            data={
                "version_id": version_id,
                "content": content,
                "is_second_run": is_second_run,
                "delivery_status": delivery_status,
                "delivery_note": "Delivery skipped (no email integration in test)" if delivery_status == "failed" else None,
            },
            tables_queried=["deliverables", "deliverable_versions", "platform_content", "user_context"],
        )

    except Exception as e:
        import traceback
        return StepResult(
            step_name="deliverable_execution",
            success=False,
            error=str(e),
            traceback=traceback.format_exc(),
            tables_queried=["deliverables"],
        )


async def simulate_user_edit(
    client: Any,
    user_id: str,
    persona: SyntheticUser,
    execution_data: dict,
) -> StepResult:
    """Step 3: Simulate user edit on deliverable version."""
    try:
        version_id = execution_data.get("version_id")
        original_content = execution_data.get("content", "")

        if not version_id or not original_content:
            return StepResult(
                step_name="simulate_edit",
                success=False,
                error="No version_id or content from execution",
            )

        # Apply edit instructions (simple text transforms)
        edited_content = original_content

        for instruction in persona.edit_instructions:
            if "Cut" in instruction and "%" in instruction:
                # Cut to percentage
                import re
                match = re.search(r'(\d+)%', instruction)
                if match:
                    pct = int(match.group(1))
                    target_len = int(len(edited_content) * pct / 100)
                    # Cut by paragraphs
                    paragraphs = edited_content.split('\n\n')
                    result_paragraphs = []
                    current_len = 0
                    for p in paragraphs:
                        if current_len + len(p) <= target_len:
                            result_paragraphs.append(p)
                            current_len += len(p)
                        else:
                            break
                    edited_content = '\n\n'.join(result_paragraphs)

            elif "Move" in instruction and "to the top" in instruction:
                # Move a section to the top
                import re
                match = re.search(r"'([^']+)'", instruction)
                if match:
                    section_name = match.group(1)
                    # Simple: look for ## Section Name pattern
                    lines = edited_content.split('\n')
                    section_start = -1
                    section_end = len(lines)
                    for i, line in enumerate(lines):
                        if section_name.lower() in line.lower() and line.startswith('#'):
                            section_start = i
                        elif section_start >= 0 and line.startswith('#') and i > section_start:
                            section_end = i
                            break
                    if section_start >= 0:
                        section = lines[section_start:section_end]
                        rest = lines[:section_start] + lines[section_end:]
                        edited_content = '\n'.join(section + [''] + rest)

            elif "Remove" in instruction:
                # Remove specific content
                import re
                match = re.search(r"[Rr]emove.*['\"]([^'\"]+)['\"]", instruction)
                if match:
                    to_remove = match.group(1)
                    edited_content = edited_content.replace(to_remove, "")
                # Also handle "Remove routine items" type instructions
                elif "routine" in instruction.lower() or "bot" in instruction.lower():
                    # Remove lines mentioning bots or routine
                    lines = [l for l in edited_content.split('\n') if 'bot' not in l.lower()]
                    edited_content = '\n'.join(lines)

            elif "Soften" in instruction:
                # Soften a phrase
                import re
                match = re.search(r"['\"]([^'\"]+)['\"].*['\"]([^'\"]+)['\"]", instruction)
                if match:
                    old_phrase = match.group(1)
                    new_phrase = match.group(2)
                    edited_content = edited_content.replace(old_phrase, new_phrase)

            elif "Add" in instruction:
                # Add text (e.g., "Add 'Priority: High' to...")
                import re
                match = re.search(r"[Aa]dd ['\"]([^'\"]+)['\"]", instruction)
                if match:
                    to_add = match.group(1)
                    # Add to beginning of content
                    edited_content = f"{to_add}\n\n{edited_content}"

        # Update the deliverable version with edited content
        client.table("deliverable_versions").update({
            "final_content": edited_content,
            "status": "approved",
            "approved_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", version_id).execute()

        return StepResult(
            step_name="simulate_edit",
            success=True,
            data={
                "version_id": version_id,
                "original_length": len(original_content),
                "edited_length": len(edited_content),
                "edits_applied": len(persona.edit_instructions),
                "edit_diff": {
                    "original_preview": original_content[:200],
                    "edited_preview": edited_content[:200],
                },
            },
            tables_queried=["deliverable_versions"],
        )

    except Exception as e:
        import traceback
        return StepResult(
            step_name="simulate_edit",
            success=False,
            error=str(e),
            traceback=traceback.format_exc(),
            tables_queried=["deliverable_versions"],
        )


async def run_memory_extraction(
    client: Any,
    user_id: str,
    persona: SyntheticUser,
    edit_data: dict,
) -> StepResult:
    """Step 4: Run memory extraction against the edit diff."""
    try:
        from services.memory import process_conversation

        version_id = edit_data.get("version_id")
        if not version_id:
            return StepResult(
                step_name="memory_extraction",
                success=False,
                error="No version_id from edit step",
            )

        # Get the edited version
        version_result = (
            client.table("deliverable_versions")
            .select("final_content, draft_content")
            .eq("id", version_id)
            .single()
            .execute()
        )

        if not version_result.data:
            return StepResult(
                step_name="memory_extraction",
                success=False,
                error=f"Version not found: {version_id}",
            )

        final_content = version_result.data.get("final_content", "")
        draft_content = version_result.data.get("draft_content", "")

        # Simulate a richer conversation that triggers extraction
        # MIN_MESSAGES_FOR_EXTRACTION = 3 user messages required
        simulated_messages = [
            {"role": "user", "content": f"Can you generate my {persona.deliverable_config['title']}?"},
            {"role": "assistant", "content": f"Here's your {persona.deliverable_config['title']}:\n\n{draft_content}"},
            {"role": "user", "content": "I prefer shorter, more concise content. Can you trim this down?"},
            {"role": "assistant", "content": "I'll make it more concise. Here's a shorter version."},
            {"role": "user", "content": f"I've edited this further. Here are my final changes:\n\n{final_content}"},
            {"role": "assistant", "content": "I'll remember your preference for concise content."},
            {"role": "user", "content": "Yes, always keep my deliverables brief and to the point."},
        ]

        # Run memory extraction
        extracted_count = await process_conversation(
            client=client,
            user_id=user_id,
            messages=simulated_messages,
            session_id=str(uuid4()),
        )

        # Query what was written to user_context (source="tp_extracted" per memory.py)
        context_result = (
            client.table("user_context")
            .select("key, value, source")
            .eq("user_id", user_id)
            .eq("source", "tp_extracted")
            .execute()
        )
        extracted_memories = context_result.data or []

        return StepResult(
            step_name="memory_extraction",
            success=True,
            data={
                "count": extracted_count,
                "memories": [{"key": m["key"], "value": m["value"][:100]} for m in extracted_memories],
            },
            tables_queried=["deliverable_versions", "user_context"],
        )

    except Exception as e:
        import traceback
        return StepResult(
            step_name="memory_extraction",
            success=False,
            error=str(e),
            traceback=traceback.format_exc(),
            tables_queried=["deliverable_versions", "user_context"],
        )


# =============================================================================
# Phase 3: Reporting
# =============================================================================

def generate_report(results: list[PipelineResult]) -> str:
    """Generate structured comparison report."""
    lines = [
        "\n" + "="*80,
        "PIPELINE TEST REPORT",
        "="*80,
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Personas tested: {len(results)}",
        "",
    ]

    # Summary
    completed = [r for r in results if r.completed]
    failed = [r for r in results if not r.completed]

    lines.append("SUMMARY")
    lines.append("-"*40)
    lines.append(f"Completed: {len(completed)}/{len(results)}")
    lines.append(f"Failed: {len(failed)}/{len(results)}")
    lines.append("")

    # Failures first (report failures before quality)
    if failed:
        lines.append("FAILURES")
        lines.append("-"*40)
        for r in failed:
            lines.append(f"\n{r.persona_name}:")
            for step in r.steps:
                status = "✓" if step.success else "✗"
                lines.append(f"  {status} {step.step_name}")
                if not step.success:
                    lines.append(f"    Error: {step.error}")
                    if step.traceback:
                        # First 5 lines of traceback
                        tb_lines = step.traceback.strip().split('\n')[-5:]
                        for tb in tb_lines:
                            lines.append(f"    {tb}")
                    lines.append(f"    Tables: {', '.join(step.tables_queried)}")
        lines.append("")

    # Successful completions
    if completed:
        lines.append("COMPLETED PERSONAS")
        lines.append("-"*40)
        for r in completed:
            lines.append(f"\n{r.persona_name}:")

            # Signal processing
            signal_step = next((s for s in r.steps if s.step_name == "signal_processing"), None)
            if signal_step and signal_step.data:
                d = signal_step.data
                lines.append(f"  Signal processing:")
                lines.append(f"    Signals found: {d.get('signals_found', False)}")
                lines.append(f"    Actions: {d.get('actions', [])}")
                lines.append(f"    Deliverables created: {d.get('deliverables_created', 0)}")

            # Deliverable execution (v1 vs v2)
            exec_steps = [s for s in r.steps if s.step_name == "deliverable_execution"]
            if len(exec_steps) >= 2:
                v1 = exec_steps[0].data or {}
                v2 = exec_steps[1].data or {}
                v1_len = len(v1.get("content", "")) if v1.get("content") else 0
                v2_len = len(v2.get("content", "")) if v2.get("content") else 0
                lines.append(f"  Deliverable versions:")
                lines.append(f"    v1 length: {v1_len} chars")
                lines.append(f"    v2 length: {v2_len} chars")
                lines.append(f"    Delta: {v2_len - v1_len} chars ({((v2_len - v1_len) / max(v1_len, 1)) * 100:.1f}%)")

            # Memory extraction
            mem_step = next((s for s in r.steps if s.step_name == "memory_extraction"), None)
            if mem_step and mem_step.data:
                d = mem_step.data
                lines.append(f"  Memory extraction:")
                lines.append(f"    Count: {d.get('count', 0)}")
                for m in d.get("memories", [])[:3]:
                    lines.append(f"    - {m['key']}: {m['value'][:50]}...")

            # Edit step
            edit_step = next((s for s in r.steps if s.step_name == "simulate_edit"), None)
            if edit_step and edit_step.data:
                d = edit_step.data
                lines.append(f"  Edit simulation:")
                lines.append(f"    Original: {d.get('original_length', 0)} chars")
                lines.append(f"    Edited: {d.get('edited_length', 0)} chars")
                lines.append(f"    Edits applied: {d.get('edits_applied', 0)}")

    lines.append("")
    lines.append("="*80)
    lines.append("END REPORT")
    lines.append("="*80)

    return "\n".join(lines)


# =============================================================================
# Main
# =============================================================================

async def main():
    """Main entry point."""
    from supabase import create_client

    # Check environment
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

    if not supabase_url or not supabase_key:
        logger.error("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        sys.exit(1)

    if not anthropic_key:
        logger.error("ANTHROPIC_API_KEY must be set")
        sys.exit(1)

    client = create_client(supabase_url, supabase_key)

    logger.info("="*80)
    logger.info("E2E PIPELINE TEST")
    logger.info("="*80)
    logger.info(f"Personas: {', '.join(p.name for p in PERSONAS)}")
    logger.info("")

    results: list[PipelineResult] = []
    created_personas: list[SyntheticUser] = []  # For cleanup with full context

    try:
        # Phase 1: Create fixtures
        logger.info("\n" + "="*60)
        logger.info("PHASE 1: CREATE FIXTURES")
        logger.info("="*60)

        for persona in PERSONAS:
            try:
                user_id = await create_synthetic_user(client, persona)
                created_personas.append(persona)
            except Exception as e:
                logger.error(f"Failed to create {persona.name}: {e}")
                # Clean up and exit
                for p in created_personas:
                    deliverable_title = p.deliverable_config.get("title") if p.deliverable_config else None
                    await cleanup_synthetic_user(client, p.user_id, p.name, deliverable_title)
                sys.exit(1)

        # Phase 2: Run pipelines
        logger.info("\n" + "="*60)
        logger.info("PHASE 2: RUN PIPELINES")
        logger.info("="*60)

        for persona in PERSONAS:
            result = await run_pipeline_for_persona(client, persona)
            results.append(result)

            # If all personas fail at step 1, stop
            if len(results) == len(PERSONAS):
                step1_failures = sum(1 for r in results if r.steps and not r.steps[0].success)
                if step1_failures == len(results):
                    logger.error("\n✗ All personas failed at step 1. Stopping.")
                    break

        # Phase 3: Report
        logger.info("\n" + "="*60)
        logger.info("PHASE 3: REPORT")
        logger.info("="*60)

        report = generate_report(results)
        print(report)

        # Write report to file
        report_path = Path(__file__).parent / "test_pipeline_report.txt"
        with open(report_path, "w") as f:
            f.write(report)
        logger.info(f"\nReport written to: {report_path}")

    finally:
        # Cleanup
        logger.info("\n" + "="*60)
        logger.info("CLEANUP")
        logger.info("="*60)

        for persona in created_personas:
            deliverable_title = persona.deliverable_config.get("title") if persona.deliverable_config else None
            await cleanup_synthetic_user(client, persona.user_id, persona.name, deliverable_title)

        logger.info("\n✓ Test complete")


if __name__ == "__main__":
    asyncio.run(main())
