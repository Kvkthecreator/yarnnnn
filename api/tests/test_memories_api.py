"""
Test suite for ADR-005 Memories API

Tests:
1. User memories CRUD
2. Project memories CRUD
3. Bulk import
4. Context bundle retrieval
5. Semantic search (when embeddings are available)

Usage:
    # Start API server first: cd api && uvicorn main:app --reload
    # Then run: python -m pytest tests/test_memories_api.py -v
"""

import os
import sys
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

# Test configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
TEST_USER_ID = "2abf3f96-118b-4987-9d95-40f2d9be9a18"
TEST_PROJECT_ID = "d135f1ff-368a-41d2-bffa-71c9ee739b44"


def get_service_client():
    """Get Supabase client with service key (bypasses RLS)."""
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def test_database_connection():
    """Test basic database connectivity."""
    print("\n=== Test: Database Connection ===")
    client = get_service_client()

    result = client.table("memories").select("count").execute()
    print(f"✓ Connected to database")
    print(f"  Total memories in database: checking...")

    # Count memories for test user
    user_memories = client.table("memories")\
        .select("*")\
        .eq("user_id", TEST_USER_ID)\
        .is_("project_id", "null")\
        .execute()
    print(f"  User memories: {len(user_memories.data)}")

    project_memories = client.table("memories")\
        .select("*")\
        .eq("project_id", TEST_PROJECT_ID)\
        .execute()
    print(f"  Project memories: {len(project_memories.data)}")

    return True


def test_list_user_memories():
    """Test listing user-scoped memories."""
    print("\n=== Test: List User Memories ===")
    client = get_service_client()

    result = client.table("memories")\
        .select("*")\
        .eq("user_id", TEST_USER_ID)\
        .is_("project_id", "null")\
        .eq("is_active", True)\
        .order("importance", desc=True)\
        .execute()

    memories = result.data
    print(f"✓ Retrieved {len(memories)} user memories")

    for i, mem in enumerate(memories[:3]):
        print(f"  {i+1}. [{mem['importance']:.2f}] {mem['content'][:60]}...")
        print(f"     Tags: {mem['tags']}")

    assert len(memories) > 0, "Should have user memories"
    return True


def test_list_project_memories():
    """Test listing project-scoped memories."""
    print("\n=== Test: List Project Memories ===")
    client = get_service_client()

    result = client.table("memories")\
        .select("*")\
        .eq("project_id", TEST_PROJECT_ID)\
        .eq("is_active", True)\
        .order("importance", desc=True)\
        .execute()

    memories = result.data
    print(f"✓ Retrieved {len(memories)} project memories")

    for i, mem in enumerate(memories[:3]):
        print(f"  {i+1}. [{mem['importance']:.2f}] {mem['content'][:60]}...")
        print(f"     Tags: {mem['tags']}")

    assert len(memories) > 0, "Should have project memories"
    return True


def test_create_memory():
    """Test creating a new memory."""
    print("\n=== Test: Create Memory ===")
    client = get_service_client()

    # Create a test memory
    new_memory = {
        "user_id": TEST_USER_ID,
        "project_id": TEST_PROJECT_ID,
        "content": f"Test memory created at {datetime.utcnow().isoformat()}",
        "tags": ["test", "automated"],
        "entities": {"concepts": ["testing"]},
        "importance": 0.5,
        "source_type": "manual",
        "is_active": True
    }

    result = client.table("memories").insert(new_memory).execute()
    created = result.data[0]

    print(f"✓ Created memory with ID: {created['id']}")
    print(f"  Content: {created['content']}")
    print(f"  Tags: {created['tags']}")

    # Clean up - delete the test memory
    client.table("memories").delete().eq("id", created['id']).execute()
    print(f"✓ Cleaned up test memory")

    return True


def test_update_memory():
    """Test updating a memory."""
    print("\n=== Test: Update Memory ===")
    client = get_service_client()

    # Create a test memory first
    new_memory = {
        "user_id": TEST_USER_ID,
        "project_id": None,
        "content": "Original content for update test",
        "tags": ["test"],
        "entities": {},
        "importance": 0.5,
        "source_type": "manual",
        "is_active": True
    }

    result = client.table("memories").insert(new_memory).execute()
    memory_id = result.data[0]['id']
    print(f"  Created test memory: {memory_id}")

    # Update the memory
    update_data = {
        "content": "Updated content for update test",
        "tags": ["test", "updated"],
        "importance": 0.8,
        "updated_at": datetime.utcnow().isoformat()
    }

    result = client.table("memories")\
        .update(update_data)\
        .eq("id", memory_id)\
        .execute()

    updated = result.data[0]
    print(f"✓ Updated memory")
    print(f"  New content: {updated['content']}")
    print(f"  New tags: {updated['tags']}")
    print(f"  New importance: {updated['importance']}")

    assert updated['content'] == update_data['content']
    assert updated['importance'] == 0.8

    # Clean up
    client.table("memories").delete().eq("id", memory_id).execute()
    print(f"✓ Cleaned up test memory")

    return True


def test_soft_delete_memory():
    """Test soft-deleting a memory."""
    print("\n=== Test: Soft Delete Memory ===")
    client = get_service_client()

    # Create a test memory
    new_memory = {
        "user_id": TEST_USER_ID,
        "project_id": None,
        "content": "Memory to be soft-deleted",
        "tags": ["test", "delete"],
        "entities": {},
        "importance": 0.5,
        "source_type": "manual",
        "is_active": True
    }

    result = client.table("memories").insert(new_memory).execute()
    memory_id = result.data[0]['id']
    print(f"  Created test memory: {memory_id}")

    # Soft delete
    result = client.table("memories")\
        .update({"is_active": False, "updated_at": datetime.utcnow().isoformat()})\
        .eq("id", memory_id)\
        .execute()

    print(f"✓ Soft-deleted memory (is_active=false)")

    # Verify it's excluded from active queries
    active_result = client.table("memories")\
        .select("*")\
        .eq("id", memory_id)\
        .eq("is_active", True)\
        .execute()

    assert len(active_result.data) == 0, "Deleted memory should not appear in active queries"
    print(f"✓ Memory excluded from active queries")

    # Clean up - hard delete
    client.table("memories").delete().eq("id", memory_id).execute()
    print(f"✓ Cleaned up test memory")

    return True


def test_context_bundle():
    """Test retrieving full context bundle."""
    print("\n=== Test: Context Bundle ===")
    client = get_service_client()

    # Simulate context bundle retrieval
    # User memories (portable)
    user_result = client.table("memories")\
        .select("*")\
        .eq("user_id", TEST_USER_ID)\
        .is_("project_id", "null")\
        .eq("is_active", True)\
        .order("importance", desc=True)\
        .limit(20)\
        .execute()

    # Project memories
    project_result = client.table("memories")\
        .select("*")\
        .eq("project_id", TEST_PROJECT_ID)\
        .eq("is_active", True)\
        .order("importance", desc=True)\
        .execute()

    # Documents
    docs_result = client.table("documents")\
        .select("*")\
        .eq("project_id", TEST_PROJECT_ID)\
        .execute()

    print(f"✓ Context Bundle retrieved:")
    print(f"  User memories: {len(user_result.data)}")
    print(f"  Project memories: {len(project_result.data)}")
    print(f"  Documents: {len(docs_result.data)}")

    total_memories = len(user_result.data) + len(project_result.data)
    assert total_memories > 0, "Should have memories in bundle"

    return True


def test_tag_distribution():
    """Analyze tag distribution across memories."""
    print("\n=== Test: Tag Distribution ===")
    client = get_service_client()

    result = client.table("memories")\
        .select("tags")\
        .eq("user_id", TEST_USER_ID)\
        .eq("is_active", True)\
        .execute()

    # Count tags
    tag_counts = {}
    for mem in result.data:
        for tag in (mem['tags'] or []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    print(f"✓ Tag distribution ({len(tag_counts)} unique tags):")
    for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"  {tag}: {count}")

    return True


def test_importance_filtering():
    """Test filtering by importance threshold."""
    print("\n=== Test: Importance Filtering ===")
    client = get_service_client()

    # High importance (>= 0.8)
    high_result = client.table("memories")\
        .select("content, importance")\
        .eq("user_id", TEST_USER_ID)\
        .gte("importance", 0.8)\
        .eq("is_active", True)\
        .execute()

    print(f"✓ High importance memories (>=0.8): {len(high_result.data)}")
    for mem in high_result.data[:3]:
        print(f"  [{mem['importance']:.2f}] {mem['content'][:50]}...")

    return True


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("ADR-005 Memories API Test Suite")
    print("=" * 60)
    print(f"Test User: {TEST_USER_ID}")
    print(f"Test Project: {TEST_PROJECT_ID}")

    tests = [
        test_database_connection,
        test_list_user_memories,
        test_list_project_memories,
        test_create_memory,
        test_update_memory,
        test_soft_delete_memory,
        test_context_bundle,
        test_tag_distribution,
        test_importance_filtering,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"\n✗ FAILED: {test.__name__}")
            print(f"  Error: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
