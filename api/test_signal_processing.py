"""
Test script for signal processing - simulates cron execution

Usage:
    # Option 1: With environment variables set
    cd api && python test_signal_processing.py

    # Option 2: Using Render CLI (recommended for production testing)
    render run python api/test_signal_processing.py kvkthecreator@gmail.com

    # Option 3: Set env vars manually
    export SUPABASE_URL="your_url"
    export SUPABASE_SERVICE_KEY="your_key"
    export ANTHROPIC_API_KEY="your_key"
    export GOOGLE_CLIENT_ID="your_id"
    export GOOGLE_CLIENT_SECRET="your_secret"
    cd api && python test_signal_processing.py

This script simulates the signal processing phase from unified_scheduler.py
for a specific user account to test the implementation without waiting for cron.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Load .env manually (same approach as test_adr042_integration.py)
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key] = value

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_signal_processing(user_email: str, signals_filter: str = "all"):
    """
    Test signal processing for a specific user.

    Args:
        user_email: User's email address
        signals_filter: "all", "calendar_only", or "non_calendar"
    """
    from supabase import create_client
    from services.signal_extraction import extract_signal_summary
    from services.signal_processing import process_signal, execute_signal_actions
    from services.activity_log import get_recent_activity

    # Initialize Supabase client
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        logger.error("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        return

    supabase = create_client(supabase_url, supabase_key)

    # Get user_id from email
    try:
        user_result = supabase.auth.admin.list_users()
        user = next((u for u in user_result if u.email == user_email), None)

        if not user:
            logger.error(f"User not found: {user_email}")
            return

        user_id = user.id
        logger.info(f"✓ Found user: {user_email} (id: {user_id})")

    except Exception as e:
        logger.error(f"Failed to get user: {e}")
        return

    # Check platform connections
    try:
        conn_result = (
            supabase.table("platform_connections")
            .select("platform, status, created_at")
            .eq("user_id", user_id)
            .execute()
        )

        connections = conn_result.data or []
        logger.info(f"✓ Platform connections: {len(connections)}")
        for conn in connections:
            logger.info(f"  - {conn['platform']}: {conn['status']}")

        if not connections:
            logger.warning("No platform connections found - signal extraction will return empty")

    except Exception as e:
        logger.warning(f"Failed to check connections: {e}")

    # Extract signals
    logger.info(f"\n{'='*60}")
    logger.info(f"EXTRACTING SIGNALS (filter={signals_filter})")
    logger.info(f"{'='*60}")

    try:
        signal_summary = await extract_signal_summary(
            supabase, user_id, signals_filter=signals_filter
        )

        logger.info(f"\n✓ Signal extraction complete:")
        logger.info(f"  - Calendar signals: {len(signal_summary.calendar_signals)}")
        logger.info(f"  - Silence signals: {len(signal_summary.silence_signals)}")
        logger.info(f"  - Has signals: {signal_summary.has_signals}")

        if signal_summary.calendar_signals:
            logger.info(f"\nCalendar signals:")
            for sig in signal_summary.calendar_signals:
                logger.info(
                    f"  - '{sig.title}' in {sig.hours_until:.1f}h "
                    f"(event_id: {sig.event_id}, attendees: {len(sig.attendee_emails)})"
                )

        if signal_summary.silence_signals:
            logger.info(f"\nSilence signals:")
            for sig in signal_summary.silence_signals:
                logger.info(
                    f"  - '{sig.thread_subject}' with {sig.sender}: "
                    f"{sig.days_silent:.1f} days silent (thread_id: {sig.label_id})"
                )

        if not signal_summary.has_signals:
            logger.info("\n✗ No signals detected - stopping here")
            return

    except Exception as e:
        logger.error(f"✗ Signal extraction failed: {e}", exc_info=True)
        return

    # Get user context for reasoning
    logger.info(f"\n{'='*60}")
    logger.info(f"GATHERING CONTEXT")
    logger.info(f"{'='*60}")

    try:
        user_context_result = (
            supabase.table("user_context")
            .select("key, value")
            .eq("user_id", user_id)
            .limit(20)
            .execute()
        )
        user_context = user_context_result.data or []
        logger.info(f"✓ User context entries: {len(user_context)}")

        recent_activity = await get_recent_activity(
            client=supabase,
            user_id=user_id,
            limit=10,
            days=7,
        )
        logger.info(f"✓ Recent activity entries: {len(recent_activity)}")

        existing_deliverables_result = (
            supabase.table("deliverables")
            .select("id, title, deliverable_type, next_run_at, status")
            .eq("user_id", user_id)
            .in_("status", ["active", "paused"])
            .execute()
        )
        existing_deliverables = existing_deliverables_result.data or []
        logger.info(f"✓ Existing deliverables: {len(existing_deliverables)}")

    except Exception as e:
        logger.error(f"✗ Failed to gather context: {e}")
        return

    # Process signals (LLM reasoning)
    logger.info(f"\n{'='*60}")
    logger.info(f"PROCESSING SIGNALS (LLM reasoning)")
    logger.info(f"{'='*60}")

    try:
        processing_result = await process_signal(
            client=supabase,
            user_id=user_id,
            signal_summary=signal_summary,
            user_context=user_context,
            recent_activity=recent_activity,
            existing_deliverables=existing_deliverables,
        )

        logger.info(f"\n✓ Signal processing complete:")
        logger.info(f"  - Actions proposed: {len(processing_result.actions)}")
        logger.info(f"  - Reasoning: {processing_result.reasoning[:200]}...")

        if processing_result.actions:
            logger.info(f"\nProposed actions:")
            for action in processing_result.actions:
                logger.info(
                    f"  - {action.action_type}: {action.deliverable_type} "
                    f"(confidence: {action.confidence:.2f})"
                )
                logger.info(f"    Title: {action.title}")
                logger.info(f"    Signal context: {action.signal_context}")
        else:
            logger.info("\n✗ No actions proposed - stopping here")
            return

    except Exception as e:
        logger.error(f"✗ Signal processing failed: {e}", exc_info=True)
        return

    # Execute actions (create deliverables)
    logger.info(f"\n{'='*60}")
    logger.info(f"EXECUTING ACTIONS")
    logger.info(f"{'='*60}")

    try:
        created = await execute_signal_actions(
            client=supabase,
            user_id=user_id,
            result=processing_result,
        )

        logger.info(f"\n✓ Execution complete:")
        logger.info(f"  - Deliverables created: {created}")

        if created > 0:
            # Query the created deliverables
            recent_deliverables = (
                supabase.table("deliverables")
                .select("id, title, deliverable_type, origin, status, created_at")
                .eq("user_id", user_id)
                .eq("origin", "signal_emergent")
                .order("created_at", desc=True)
                .limit(created)
                .execute()
            )

            logger.info(f"\nCreated deliverables:")
            for d in (recent_deliverables.data or []):
                logger.info(
                    f"  - {d['title']} ({d['deliverable_type']}) "
                    f"[{d['status']}] - {d['id']}"
                )

    except Exception as e:
        logger.error(f"✗ Action execution failed: {e}", exc_info=True)
        return

    logger.info(f"\n{'='*60}")
    logger.info(f"TEST COMPLETE")
    logger.info(f"{'='*60}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test signal processing for a user")
    parser.add_argument(
        "email",
        nargs="?",
        default="kvkthecreator@gmail.com",
        help="User email address (default: kvkthecreator@gmail.com)"
    )
    parser.add_argument(
        "--filter",
        choices=["all", "calendar_only", "non_calendar"],
        default="all",
        help="Signal filter type (default: all)"
    )

    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"SIGNAL PROCESSING TEST")
    print(f"{'='*60}")
    print(f"User: {args.email}")
    print(f"Filter: {args.filter}")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print(f"{'='*60}\n")

    asyncio.run(test_signal_processing(args.email, args.filter))
