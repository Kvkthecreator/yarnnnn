#!/usr/bin/env python3
"""
ADR-060 Test Script: Conversation Analyst E2E Test

This script tests the full analysis pipeline locally without needing
the API server running. It directly invokes the analysis functions.

Usage:
    cd api
    python scripts/test_conversation_analyst.py [user_id]

If no user_id is provided, it will find a user with recent sessions.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()


async def main():
    from supabase import create_client

    # Initialize Supabase client
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        print("ERROR: Missing SUPABASE_URL or SUPABASE_SERVICE_KEY environment variables")
        print("Make sure you have a .env file with these values")
        sys.exit(1)

    supabase = create_client(supabase_url, supabase_key)
    print(f"✓ Connected to Supabase: {supabase_url}")

    # Get user_id from args or find one
    if len(sys.argv) > 1:
        user_id = sys.argv[1]
        print(f"✓ Using provided user_id: {user_id}")
    else:
        # Find user with recent sessions
        result = supabase.table("chat_sessions")\
            .select("user_id")\
            .order("updated_at", desc=True)\
            .limit(1)\
            .execute()

        if not result.data:
            print("ERROR: No chat sessions found in database")
            sys.exit(1)

        user_id = result.data[0]["user_id"]
        print(f"✓ Found user with recent activity: {user_id}")

    # Import analysis functions
    print("\n--- Phase 1: Importing Analysis Functions ---")
    try:
        from services.conversation_analysis import (
            get_recent_sessions,
            get_user_deliverables,
            get_user_knowledge,
            analyze_conversation_patterns,
            create_suggested_deliverable,
        )
        print("✓ All analysis functions imported successfully")
    except ImportError as e:
        print(f"ERROR: Failed to import analysis functions: {e}")
        sys.exit(1)

    # Step 1: Get recent sessions
    print("\n--- Phase 2: Fetching Recent Sessions ---")
    sessions = await get_recent_sessions(supabase, user_id, days=7)
    print(f"✓ Found {len(sessions)} sessions in last 7 days")

    if not sessions:
        print("WARNING: No recent sessions found. Creating mock data for testing...")
        # We can't test without sessions, but let's show what would happen
        print("  The analyst needs chat sessions to analyze patterns.")
        print("  Try having some conversations first, then run this again.")
        return

    # Show session preview
    for i, session in enumerate(sessions[:3]):
        msg_count = len(session.get("messages", []))
        print(f"  Session {i+1}: {msg_count} messages, updated {session.get('updated_at', 'unknown')}")

    # Step 2: Get existing deliverables
    print("\n--- Phase 3: Fetching Existing Deliverables ---")
    deliverables = await get_user_deliverables(supabase, user_id)
    print(f"✓ Found {len(deliverables)} existing deliverables")

    for d in deliverables[:5]:
        print(f"  - {d.get('title', 'Untitled')} ({d.get('status', 'unknown')})")

    # Step 3: Get user knowledge
    print("\n--- Phase 4: Fetching User Knowledge ---")
    knowledge = await get_user_knowledge(supabase, user_id)
    print(f"✓ Knowledge context retrieved")
    print(f"  Knowledge entries: {len(knowledge)}")

    # Step 4: Run analysis
    print("\n--- Phase 5: Running Conversation Analysis ---")
    print("  Calling Claude to analyze patterns...")

    try:
        suggestions = await analyze_conversation_patterns(
            client=supabase,
            user_id=user_id,
            sessions=sessions,
            existing_deliverables=deliverables,
            user_knowledge=knowledge,
        )
        print(f"✓ Analysis complete: {len(suggestions)} suggestions generated")
    except Exception as e:
        print(f"ERROR: Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return

    if not suggestions:
        print("  No patterns detected that warrant new deliverables.")
        print("  This is normal if conversations don't have recurring themes.")
        return

    # Show suggestions
    print("\n--- Phase 6: Suggestions Generated ---")
    for i, suggestion in enumerate(suggestions):
        print(f"\n  Suggestion {i+1}:")
        print(f"    Title: {suggestion.title}")
        print(f"    Type: {suggestion.deliverable_type}")
        print(f"    Confidence: {suggestion.confidence * 100:.0f}%")
        print(f"    Reason: {suggestion.detection_reason}")
        print(f"    Schedule: {suggestion.schedule}")

    # Step 5: Create suggestions in DB (optional)
    print("\n--- Phase 7: Persisting Suggestions ---")
    create_in_db = input("Create these suggestions in the database? (y/N): ").strip().lower()

    if create_in_db == 'y':
        created_count = 0
        for suggestion in suggestions:
            if suggestion.confidence >= 0.50:
                result = await create_suggested_deliverable(supabase, user_id, suggestion)
                if result:
                    created_count += 1
                    print(f"  ✓ Created: {suggestion.title}")
                else:
                    print(f"  ✗ Failed: {suggestion.title}")

        print(f"\n✓ Created {created_count} suggestions in database")
        print(f"  View them at: /deliverables (look for purple 'Suggested for you' section)")
    else:
        print("  Skipped database creation (dry run)")

    # Step 6: Verify in DB
    print("\n--- Phase 8: Verification ---")
    suggested_result = supabase.rpc(
        "get_suggested_deliverable_versions",
        {"p_user_id": user_id}
    ).execute()

    suggested_count = len(suggested_result.data) if suggested_result.data else 0
    print(f"✓ Total suggested deliverables for user: {suggested_count}")

    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)
    print("\nNext steps:")
    print("1. Check /deliverables page for purple suggestion cards")
    print("2. Test Enable (checkmark) and Dismiss (X) buttons")
    print("3. Check Settings → Notifications for the toggle")


if __name__ == "__main__":
    asyncio.run(main())
