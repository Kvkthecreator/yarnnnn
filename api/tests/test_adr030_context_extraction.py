"""
ADR-030 Context Extraction Methodology Test Suite

Comprehensive validation of:
1. Delta extraction logic
2. Source scope configuration
3. Caching behavior
4. Parallel fetching
5. Haiku extraction integration
6. Source freshness tracking

This test uses the service key to bypass RLS for testing.
"""

import os
import sys
import asyncio
from datetime import datetime, timedelta
from uuid import uuid4

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
TEST_USER_ID = "2abf3f96-118b-4987-9d95-40f2d9be9a18"


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


# =============================================================================
# Schema Tests
# =============================================================================

def test_schema(results):
    """Validate database schema for ADR-030."""
    print("\n=== Schema Validation ===")
    client = get_client()

    # Test 1: deliverable_source_runs table exists
    try:
        result = client.table("deliverable_source_runs").select("*").limit(1).execute()
        results.record("deliverable_source_runs table exists", True)
    except Exception as e:
        results.record("deliverable_source_runs table exists", False, str(e))
        return

    # Test 2: Check required columns on deliverable_source_runs
    required_columns = [
        "id", "deliverable_id", "version_id", "source_index", "source_type",
        "provider", "resource_id", "scope_used", "time_range_start",
        "time_range_end", "status", "items_fetched", "items_filtered",
        "error_message", "created_at", "completed_at"
    ]

    # Create a test row to check columns
    try:
        # Get a deliverable to use
        del_result = client.table("deliverables").select("id").eq("user_id", TEST_USER_ID).limit(1).execute()
        if del_result.data:
            test_deliverable_id = del_result.data[0]["id"]

            # Try inserting with all required columns
            test_run = client.table("deliverable_source_runs").insert({
                "deliverable_id": test_deliverable_id,
                "source_index": 0,
                "source_type": "integration_import",
                "provider": "test",
                "status": "pending",
            }).execute()

            if test_run.data:
                # Check all columns exist
                row = test_run.data[0]
                missing = [col for col in required_columns if col not in row]
                if missing:
                    results.record("required columns exist", False, f"Missing: {missing}")
                else:
                    results.record("required columns exist", True)

                # Clean up test row
                client.table("deliverable_source_runs").delete().eq("id", row["id"]).execute()
            else:
                results.record("required columns exist", False, "Insert returned no data")
        else:
            results.record("required columns exist", False, "No deliverables to test with")
    except Exception as e:
        results.record("required columns exist", False, str(e))

    # Test 3: deliverable_versions.source_fetch_summary column exists
    try:
        result = client.table("deliverable_versions").select("source_fetch_summary").limit(1).execute()
        results.record("source_fetch_summary column exists", True)
    except Exception as e:
        results.record("source_fetch_summary column exists", False, str(e))

    # Test 4: Check get_last_source_fetch_time function exists
    try:
        del_result = client.table("deliverables").select("id").eq("user_id", TEST_USER_ID).limit(1).execute()
        if del_result.data:
            test_id = del_result.data[0]["id"]
            result = client.rpc("get_last_source_fetch_time", {
                "p_deliverable_id": test_id,
                "p_source_index": 0
            }).execute()
            results.record("get_last_source_fetch_time function exists", True)
        else:
            results.record("get_last_source_fetch_time function exists", False, "No deliverables to test")
    except Exception as e:
        results.record("get_last_source_fetch_time function exists", False, str(e))

    # Test 5: Check get_deliverable_source_freshness function exists
    try:
        del_result = client.table("deliverables").select("id").eq("user_id", TEST_USER_ID).limit(1).execute()
        if del_result.data:
            test_id = del_result.data[0]["id"]
            result = client.rpc("get_deliverable_source_freshness", {
                "p_deliverable_id": test_id
            }).execute()
            results.record("get_deliverable_source_freshness function exists", True)
        else:
            results.record("get_deliverable_source_freshness function exists", False, "No deliverables to test")
    except Exception as e:
        results.record("get_deliverable_source_freshness function exists", False, str(e))


# =============================================================================
# Scope Configuration Tests
# =============================================================================

def test_scope_configuration(results):
    """Test scope configuration in deliverable sources."""
    print("\n=== Scope Configuration ===")
    client = get_client()

    # Test 1: Create deliverable with scope configuration
    try:
        test_sources = [
            {
                "type": "integration_import",
                "provider": "gmail",
                "source": "inbox",
                "scope": {
                    "mode": "delta",
                    "fallback_days": 7,
                    "max_items": 200
                }
            },
            {
                "type": "integration_import",
                "provider": "slack",
                "source": "C12345",
                "scope": {
                    "mode": "fixed_window",
                    "recency_days": 14,
                    "max_items": 100
                }
            }
        ]

        # Try to create/update a deliverable with these sources
        result = client.table("deliverables").select("id, sources").eq("user_id", TEST_USER_ID).limit(1).execute()
        if result.data:
            deliverable_id = result.data[0]["id"]
            update_result = client.table("deliverables").update({
                "sources": test_sources
            }).eq("id", deliverable_id).execute()

            # Verify the update
            verify = client.table("deliverables").select("sources").eq("id", deliverable_id).single().execute()
            if verify.data and verify.data.get("sources"):
                sources = verify.data["sources"]
                if len(sources) == 2:
                    if sources[0].get("scope", {}).get("mode") == "delta":
                        results.record("delta mode scope saved", True)
                    else:
                        results.record("delta mode scope saved", False, "scope.mode not delta")

                    if sources[1].get("scope", {}).get("mode") == "fixed_window":
                        results.record("fixed_window mode scope saved", True)
                    else:
                        results.record("fixed_window mode scope saved", False, "scope.mode not fixed_window")
                else:
                    results.record("delta mode scope saved", False, "Wrong number of sources")
                    results.record("fixed_window mode scope saved", False, "Wrong number of sources")
            else:
                results.record("delta mode scope saved", False, "No sources returned")
                results.record("fixed_window mode scope saved", False, "No sources returned")
        else:
            results.record("delta mode scope saved", False, "No deliverable to test")
            results.record("fixed_window mode scope saved", False, "No deliverable to test")
    except Exception as e:
        results.record("delta mode scope saved", False, str(e))
        results.record("fixed_window mode scope saved", False, str(e))


# =============================================================================
# Source Run Tracking Tests
# =============================================================================

def test_source_run_tracking(results):
    """Test source run tracking functionality."""
    print("\n=== Source Run Tracking ===")
    client = get_client()

    # Test 1: Create and complete a source run
    try:
        del_result = client.table("deliverables").select("id").eq("user_id", TEST_USER_ID).limit(1).execute()
        if not del_result.data:
            results.record("source run lifecycle", False, "No deliverable to test")
            return

        deliverable_id = del_result.data[0]["id"]

        # Create a source run
        run_result = client.table("deliverable_source_runs").insert({
            "deliverable_id": deliverable_id,
            "source_index": 99,  # Use high index to avoid conflicts
            "source_type": "integration_import",
            "provider": "gmail",
            "resource_id": "test_inbox",
            "scope_used": {"mode": "delta", "fallback_days": 7},
            "time_range_start": (datetime.utcnow() - timedelta(days=7)).isoformat(),
            "time_range_end": datetime.utcnow().isoformat(),
            "status": "fetching",
        }).execute()

        if not run_result.data:
            results.record("source run lifecycle", False, "Failed to create source run")
            return

        run_id = run_result.data[0]["id"]

        # Update to completed
        update_result = client.table("deliverable_source_runs").update({
            "status": "completed",
            "items_fetched": 42,
            "items_filtered": 5,
            "completed_at": datetime.utcnow().isoformat(),
        }).eq("id", run_id).execute()

        # Verify
        verify = client.table("deliverable_source_runs").select("*").eq("id", run_id).single().execute()
        if verify.data:
            if verify.data["status"] == "completed" and verify.data["items_fetched"] == 42:
                results.record("source run lifecycle", True)
            else:
                results.record("source run lifecycle", False, f"Status: {verify.data['status']}, items: {verify.data['items_fetched']}")
        else:
            results.record("source run lifecycle", False, "Could not verify source run")

        # Clean up
        client.table("deliverable_source_runs").delete().eq("id", run_id).execute()

    except Exception as e:
        results.record("source run lifecycle", False, str(e))

    # Test 2: Failed source run
    try:
        del_result = client.table("deliverables").select("id").eq("user_id", TEST_USER_ID).limit(1).execute()
        deliverable_id = del_result.data[0]["id"]

        run_result = client.table("deliverable_source_runs").insert({
            "deliverable_id": deliverable_id,
            "source_index": 98,
            "source_type": "integration_import",
            "provider": "slack",
            "status": "fetching",
        }).execute()

        run_id = run_result.data[0]["id"]

        # Update to failed
        client.table("deliverable_source_runs").update({
            "status": "failed",
            "error_message": "Test error: API unavailable",
            "completed_at": datetime.utcnow().isoformat(),
        }).eq("id", run_id).execute()

        # Verify
        verify = client.table("deliverable_source_runs").select("*").eq("id", run_id).single().execute()
        if verify.data and verify.data["status"] == "failed" and verify.data["error_message"]:
            results.record("failed source run tracked", True)
        else:
            results.record("failed source run tracked", False, "Status or error not recorded")

        # Clean up
        client.table("deliverable_source_runs").delete().eq("id", run_id).execute()

    except Exception as e:
        results.record("failed source run tracked", False, str(e))


# =============================================================================
# Caching Tests (Unit Level)
# =============================================================================

def test_caching_logic(results):
    """Test caching helper functions."""
    print("\n=== Caching Logic ===")

    try:
        from services.deliverable_pipeline import (
            _cache_key, _get_cached_result, _set_cached_result,
            SourceFetchResult, _source_fetch_cache
        )

        # Clear cache for testing
        _source_fetch_cache.clear()

        # Test 1: Cache key generation
        key1 = _cache_key("user1", "gmail", "inbox", None)
        key2 = _cache_key("user1", "gmail", "inbox", datetime(2026, 2, 1))
        key3 = _cache_key("user2", "gmail", "inbox", None)

        if key1 != key2 and key1 != key3:
            results.record("cache key uniqueness", True)
        else:
            results.record("cache key uniqueness", False, "Keys not unique")

        # Test 2: Cache set and get
        test_result = SourceFetchResult(
            content="Test content",
            items_fetched=10,
            items_filtered=2,
        )

        _set_cached_result(key1, test_result)
        cached = _get_cached_result(key1)

        if cached and cached.content == "Test content" and cached.items_fetched == 10:
            results.record("cache set/get works", True)
        else:
            results.record("cache set/get works", False, "Cached result doesn't match")

        # Test 3: Cache miss for unknown key
        missed = _get_cached_result("nonexistent_key")
        if missed is None:
            results.record("cache miss returns None", True)
        else:
            results.record("cache miss returns None", False, "Got value for unknown key")

        # Clean up
        _source_fetch_cache.clear()

    except Exception as e:
        results.record("cache key uniqueness", False, str(e))
        results.record("cache set/get works", False, str(e))
        results.record("cache miss returns None", False, str(e))


# =============================================================================
# Haiku Extraction Tests (Unit Level)
# =============================================================================

def test_haiku_extraction(results):
    """Test Haiku extraction function."""
    print("\n=== Haiku Extraction ===")

    try:
        from services.deliverable_pipeline import extract_with_haiku, HAIKU_MODEL

        # Test 1: Model constant is correct
        if "haiku" in HAIKU_MODEL.lower():
            results.record("Haiku model constant set", True)
        else:
            results.record("Haiku model constant set", False, f"Model: {HAIKU_MODEL}")

        # Test 2: Short content bypass (no extraction needed)
        async def test_short_content():
            short = "Brief content"
            result = await extract_with_haiku(short, "test goal")
            return result == short

        if asyncio.run(test_short_content()):
            results.record("short content bypass", True)
        else:
            results.record("short content bypass", False, "Short content was modified")

        # Test 3: Function signature check
        import inspect
        sig = inspect.signature(extract_with_haiku)
        params = list(sig.parameters.keys())
        expected = ["raw_content", "extraction_goal", "max_output_chars"]
        if all(p in params for p in expected):
            results.record("extraction function signature", True)
        else:
            results.record("extraction function signature", False, f"Params: {params}")

    except ImportError as e:
        results.record("Haiku model constant set", False, f"Import error: {e}")
        results.record("short content bypass", False, f"Import error: {e}")
        results.record("extraction function signature", False, f"Import error: {e}")
    except Exception as e:
        results.record("Haiku model constant set", False, str(e))
        results.record("short content bypass", False, str(e))
        results.record("extraction function signature", False, str(e))


# =============================================================================
# API Endpoint Tests
# =============================================================================

def test_freshness_api(results):
    """Test the sources/freshness API endpoint."""
    print("\n=== Freshness API ===")

    # This tests the endpoint exists and returns correct schema
    # Full integration test would require running server

    try:
        from routes.deliverables import SourceFreshnessItem
        import inspect

        # Check model fields
        fields = SourceFreshnessItem.model_fields
        expected = ["source_index", "source_type", "provider", "last_fetched_at", "last_status", "items_fetched", "is_stale"]

        missing = [f for f in expected if f not in fields]
        if not missing:
            results.record("SourceFreshnessItem model", True)
        else:
            results.record("SourceFreshnessItem model", False, f"Missing: {missing}")

    except ImportError as e:
        results.record("SourceFreshnessItem model", False, f"Import error: {e}")
    except Exception as e:
        results.record("SourceFreshnessItem model", False, str(e))


# =============================================================================
# Parallel Fetching Tests
# =============================================================================

def test_parallel_fetch_structure(results):
    """Test that parallel fetching is properly structured."""
    print("\n=== Parallel Fetching ===")

    try:
        import inspect
        from services.deliverable_pipeline import execute_gather_step

        # Get source code and check for asyncio.gather usage
        source = inspect.getsource(execute_gather_step)

        if "asyncio.gather" in source:
            results.record("asyncio.gather used in gather step", True)
        else:
            results.record("asyncio.gather used in gather step", False, "No asyncio.gather found")

        if "fetch_with_index" in source or "parallel" in source.lower():
            results.record("parallel fetch implementation", True)
        else:
            results.record("parallel fetch implementation", False, "No parallel fetch pattern found")

    except Exception as e:
        results.record("asyncio.gather used in gather step", False, str(e))
        results.record("parallel fetch implementation", False, str(e))


# =============================================================================
# Main Test Runner
# =============================================================================

def run_all_tests():
    """Run all ADR-030 tests."""
    print("\n" + "="*60)
    print("ADR-030 Context Extraction Methodology Tests")
    print("="*60)

    results = TestResults()

    # Run all test categories
    test_schema(results)
    test_scope_configuration(results)
    test_source_run_tracking(results)
    test_caching_logic(results)
    test_haiku_extraction(results)
    test_freshness_api(results)
    test_parallel_fetch_structure(results)

    # Print summary
    success = results.summary()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
