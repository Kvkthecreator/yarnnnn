"""
ADR-005 Validation Test Suite

Comprehensive validation of the unified memory architecture:
1. Database schema
2. RPC functions
3. Data integrity
4. Query patterns

This test uses the service key to bypass RLS for testing.
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
TEST_USER_ID = "2abf3f96-118b-4987-9d95-40f2d9be9a18"
TEST_PROJECT_ID = "d135f1ff-368a-41d2-bffa-71c9ee739b44"


def get_client():
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


class TestResults:
    def __init__(self):
        self.passed = []
        self.failed = []

    def record(self, name, passed, details=""):
        if passed:
            self.passed.append((name, details))
            print(f"  ✓ {name}")
        else:
            self.failed.append((name, details))
            print(f"  ✗ {name}: {details}")

    def summary(self):
        total = len(self.passed) + len(self.failed)
        print(f"\n{'='*60}")
        print(f"Results: {len(self.passed)}/{total} tests passed")
        if self.failed:
            print("\nFailed tests:")
            for name, details in self.failed:
                print(f"  - {name}: {details}")
        print('='*60)
        return len(self.failed) == 0


def test_schema(results):
    """Validate database schema is correct."""
    print("\n=== Schema Validation ===")
    client = get_client()

    # Check memories table exists with correct columns
    try:
        result = client.table("memories").select("*").limit(1).execute()
        results.record("memories table exists", True)
    except Exception as e:
        results.record("memories table exists", False, str(e))
        return

    # Check required columns
    required_columns = [
        "id", "user_id", "project_id", "content", "embedding",
        "tags", "entities", "importance", "source_type", "is_active"
    ]

    # Get one row to check columns
    if result.data:
        row = result.data[0]
        for col in required_columns:
            has_col = col in row
            results.record(f"  Column '{col}'", has_col,
                          "" if has_col else "missing")

    # Check chunks table
    try:
        result = client.table("chunks").select("*").limit(1).execute()
        results.record("chunks table exists", True)
    except Exception as e:
        results.record("chunks table exists", False, str(e))

    # Check documents table has new columns
    try:
        result = client.table("documents").select("processing_status, word_count").limit(1).execute()
        results.record("documents processing columns", True)
    except Exception as e:
        results.record("documents processing columns", False, str(e))

    # Check old tables are dropped
    old_tables = ["user_context", "blocks", "block_relations", "extraction_logs"]
    for table in old_tables:
        try:
            client.table(table).select("*").limit(1).execute()
            results.record(f"  Legacy table '{table}' dropped", False, "still exists")
        except:
            results.record(f"  Legacy table '{table}' dropped", True)


def test_rpc_functions(results):
    """Validate RPC functions exist and work."""
    print("\n=== RPC Functions ===")
    client = get_client()

    # Test search_memories function (with mock embedding)
    try:
        # Create a mock embedding (1536 dimensions of zeros)
        mock_embedding = [0.0] * 1536

        result = client.rpc("search_memories", {
            "query_embedding": mock_embedding,
            "match_user_id": TEST_USER_ID,
            "match_project_id": TEST_PROJECT_ID,
            "match_count": 5,
            "similarity_threshold": 0.0  # Low threshold since no real embeddings
        }).execute()

        # Function exists and returns data
        results.record("search_memories RPC", True)
        results.record(f"  Returns {len(result.data)} results", True)
    except Exception as e:
        results.record("search_memories RPC", False, str(e))

    # Test match_chunks function (needs a document_id, we'll just check it exists)
    try:
        mock_embedding = [0.0] * 1536
        # Use a fake UUID - function should return empty but not error
        fake_doc_id = "00000000-0000-0000-0000-000000000000"

        result = client.rpc("match_chunks", {
            "query_embedding": mock_embedding,
            "match_document_id": fake_doc_id,
            "match_count": 5,
            "similarity_threshold": 0.0
        }).execute()

        results.record("match_chunks RPC", True)
    except Exception as e:
        results.record("match_chunks RPC", False, str(e))


def test_data_patterns(results):
    """Test data query patterns work correctly."""
    print("\n=== Query Patterns ===")
    client = get_client()

    # User-scoped memories (project_id IS NULL)
    try:
        result = client.table("memories")\
            .select("*")\
            .eq("user_id", TEST_USER_ID)\
            .is_("project_id", "null")\
            .eq("is_active", True)\
            .execute()

        count = len(result.data)
        results.record(f"User memories query ({count} results)", count > 0)
    except Exception as e:
        results.record("User memories query", False, str(e))

    # Project-scoped memories
    try:
        result = client.table("memories")\
            .select("*")\
            .eq("project_id", TEST_PROJECT_ID)\
            .eq("is_active", True)\
            .execute()

        count = len(result.data)
        results.record(f"Project memories query ({count} results)", count > 0)
    except Exception as e:
        results.record("Project memories query", False, str(e))

    # Importance ordering
    try:
        result = client.table("memories")\
            .select("importance")\
            .eq("user_id", TEST_USER_ID)\
            .eq("is_active", True)\
            .order("importance", desc=True)\
            .execute()

        if len(result.data) >= 2:
            ordered = all(
                result.data[i]["importance"] >= result.data[i+1]["importance"]
                for i in range(len(result.data)-1)
            )
            results.record("Importance ordering", ordered)
        else:
            results.record("Importance ordering", True, "not enough data")
    except Exception as e:
        results.record("Importance ordering", False, str(e))

    # Tag filtering (array contains)
    try:
        result = client.table("memories")\
            .select("*")\
            .eq("user_id", TEST_USER_ID)\
            .contains("tags", ["technical"])\
            .execute()

        results.record(f"Tag filtering ({len(result.data)} with 'technical')", True)
    except Exception as e:
        results.record("Tag filtering", False, str(e))


def test_crud_operations(results):
    """Test CRUD operations work correctly."""
    print("\n=== CRUD Operations ===")
    client = get_client()

    memory_id = None

    # CREATE
    try:
        new_memory = {
            "user_id": TEST_USER_ID,
            "project_id": TEST_PROJECT_ID,
            "content": f"ADR-005 validation test at {datetime.utcnow().isoformat()}",
            "tags": ["test", "validation"],
            "entities": {"concepts": ["ADR-005"]},
            "importance": 0.5,
            "source_type": "manual",
            "is_active": True
        }

        result = client.table("memories").insert(new_memory).execute()
        memory_id = result.data[0]["id"]
        results.record("CREATE memory", True)
    except Exception as e:
        results.record("CREATE memory", False, str(e))
        return

    # READ
    try:
        result = client.table("memories")\
            .select("*")\
            .eq("id", memory_id)\
            .single()\
            .execute()

        results.record("READ memory", result.data["id"] == memory_id)
    except Exception as e:
        results.record("READ memory", False, str(e))

    # UPDATE
    try:
        result = client.table("memories")\
            .update({
                "importance": 0.9,
                "tags": ["test", "validation", "updated"],
                "updated_at": datetime.utcnow().isoformat()
            })\
            .eq("id", memory_id)\
            .execute()

        updated = result.data[0]
        results.record("UPDATE memory",
                      updated["importance"] == 0.9 and "updated" in updated["tags"])
    except Exception as e:
        results.record("UPDATE memory", False, str(e))

    # SOFT DELETE
    try:
        result = client.table("memories")\
            .update({"is_active": False})\
            .eq("id", memory_id)\
            .execute()

        # Verify excluded from active queries
        check = client.table("memories")\
            .select("*")\
            .eq("id", memory_id)\
            .eq("is_active", True)\
            .execute()

        results.record("SOFT DELETE memory", len(check.data) == 0)
    except Exception as e:
        results.record("SOFT DELETE memory", False, str(e))

    # HARD DELETE (cleanup)
    try:
        client.table("memories").delete().eq("id", memory_id).execute()
        results.record("HARD DELETE cleanup", True)
    except Exception as e:
        results.record("HARD DELETE cleanup", False, str(e))


def test_context_bundle(results):
    """Test context bundle assembly."""
    print("\n=== Context Bundle ===")
    client = get_client()

    try:
        # User memories
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

        user_count = len(user_result.data)
        project_count = len(project_result.data)
        docs_count = len(docs_result.data)

        results.record(f"Context bundle: {user_count} user + {project_count} project memories, {docs_count} docs",
                      user_count > 0 or project_count > 0)

    except Exception as e:
        results.record("Context bundle assembly", False, str(e))


def test_data_quality(results):
    """Validate data quality and constraints."""
    print("\n=== Data Quality ===")
    client = get_client()

    # Check all memories have required fields
    try:
        result = client.table("memories")\
            .select("id, content, user_id, source_type, is_active")\
            .eq("user_id", TEST_USER_ID)\
            .execute()

        all_valid = all(
            m["content"] and m["user_id"] and m["source_type"] is not None
            for m in result.data
        )
        results.record(f"All memories have required fields ({len(result.data)} checked)", all_valid)
    except Exception as e:
        results.record("Required fields check", False, str(e))

    # Check importance is in valid range
    try:
        result = client.table("memories")\
            .select("importance")\
            .eq("user_id", TEST_USER_ID)\
            .execute()

        all_valid = all(
            0.0 <= (m["importance"] or 0.5) <= 1.0
            for m in result.data
        )
        results.record("Importance values in range [0,1]", all_valid)
    except Exception as e:
        results.record("Importance range check", False, str(e))

    # Check tags are arrays
    try:
        result = client.table("memories")\
            .select("tags")\
            .eq("user_id", TEST_USER_ID)\
            .execute()

        all_valid = all(
            isinstance(m["tags"], list)
            for m in result.data
        )
        results.record("Tags are arrays", all_valid)
    except Exception as e:
        results.record("Tags array check", False, str(e))


def run_all():
    """Run complete validation suite."""
    print("=" * 60)
    print("ADR-005 Unified Memory Architecture Validation")
    print("=" * 60)
    print(f"\nTest User: {TEST_USER_ID}")
    print(f"Test Project: {TEST_PROJECT_ID}")

    results = TestResults()

    test_schema(results)
    test_rpc_functions(results)
    test_data_patterns(results)
    test_crud_operations(results)
    test_context_bundle(results)
    test_data_quality(results)

    return results.summary()


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
