"""
Live test for context builder with actual database (ADR-038)

Run: cd api && python test_context_live.py
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from supabase import create_client
from services.context import build_session_context, format_context_for_prompt, estimate_context_tokens


async def test_live_context():
    """Test context injection with live database."""
    # Create Supabase client
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")  # Use service key for testing

    if not url or not key:
        print("❌ Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
        return

    client = create_client(url, key)

    # Get a test user ID (first user in database)
    result = client.table("deliverables").select("user_id").limit(1).execute()

    if not result.data:
        print("⚠️ No deliverables found - trying user_memories")
        result = client.table("memories").select("user_id").limit(1).execute()

    if not result.data:
        print("⚠️ No data found - testing with empty context")
        user_id = "00000000-0000-0000-0000-000000000000"
    else:
        user_id = result.data[0]["user_id"]

    print(f"Testing with user_id: {user_id}")
    print()

    # Build context
    context = await build_session_context(user_id, client)

    print("=== Raw Context ===")
    import json
    print(json.dumps(context, indent=2, default=str))
    print()

    # Format for prompt
    formatted = format_context_for_prompt(context)
    print("=== Formatted for Prompt ===")
    print(formatted)
    print()

    # Check token budget
    tokens = estimate_context_tokens(context)
    print(f"Estimated tokens: {tokens}/2000")

    # Summary
    print("\n=== Summary ===")
    print(f"  User profile: {'populated' if context.get('user_profile', {}).get('name') else 'empty'}")
    print(f"  User facts: {len(context.get('user_facts', []))} facts")
    print(f"  Active deliverables: {len(context.get('active_deliverables', []))} deliverables")
    print(f"  Connected platforms: {len(context.get('connected_platforms', []))} platforms")
    print(f"  Recent sessions: {len(context.get('recent_sessions', []))} sessions")

    print("\n✅ Live context test complete!")


if __name__ == "__main__":
    asyncio.run(test_live_context())
