#!/usr/bin/env python3
"""
Verify Supabase schema and RLS policies.
Run with: python -m scripts.verify_schema
"""

import os
import sys
from dotenv import load_dotenv

# Load env from api/.env
load_dotenv()

from supabase import create_client

def main():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")

    if not url or not key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        sys.exit(1)

    print(f"Connecting to: {url}")
    client = create_client(url, key)

    # Check tables exist
    tables = [
        "workspaces", "projects", "blocks", "documents",
        "block_relations", "work_tickets", "work_outputs", "agent_sessions"
    ]

    print("\n=== TABLE CHECK ===")
    for table in tables:
        try:
            result = client.table(table).select("id").limit(1).execute()
            print(f"✅ {table}: exists ({len(result.data)} rows sampled)")
        except Exception as e:
            print(f"❌ {table}: {e}")

    # Check RLS is enabled (requires service key to see)
    print("\n=== RLS STATUS ===")
    try:
        # Query pg_tables to check RLS
        result = client.rpc('check_rls_status').execute()
        print(result.data)
    except Exception as e:
        print(f"Note: RLS check requires custom function. Run this SQL in Supabase:")
        print("""
SELECT
    schemaname,
    tablename,
    rowsecurity
FROM pg_tables
WHERE schemaname = 'public';
        """)

    # Check policies
    print("\n=== POLICY CHECK ===")
    print("Run this SQL in Supabase SQL Editor to see policies:")
    print("""
SELECT
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual,
    with_check
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;
    """)

    print("\n=== QUICK TEST: Create workspace ===")
    # This will fail with RLS if using anon key, succeed with service key
    try:
        # Use a fake user ID for testing (service key bypasses RLS)
        test_result = client.table("workspaces").select("*").limit(1).execute()
        print(f"Service key can read workspaces: {len(test_result.data)} found")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
