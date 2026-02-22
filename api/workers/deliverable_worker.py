"""
Deliverable Generation Worker

ADR-042: DEPRECATED - Background worker for deliverable generation.

The simplified execution flow (execute_deliverable_generation) runs inline
in the Execute handler. This worker is kept for backwards compatibility
with any queued jobs but should not be used for new work.

For new implementations, use:
    from services.deliverable_execution import execute_deliverable_generation
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from supabase import create_client

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s [%(name)s] %(message)s"
)
logger = logging.getLogger(__name__)


def generate_deliverable(
    deliverable_id: str,
    version_id: str,
    user_id: str,
    supabase_url: Optional[str] = None,
    supabase_key: Optional[str] = None,
) -> dict:
    """
    Background worker entry point for deliverable generation.

    ADR-042: DEPRECATED - Use execute_deliverable_generation() instead.
    This is kept for backwards compatibility with any queued jobs.
    """
    logger.warning(
        f"[DELIVERABLE_WORKER] DEPRECATED: Using legacy worker. "
        f"Prefer inline execute_deliverable_generation()."
    )
    logger.info(f"[DELIVERABLE_WORKER] Starting: deliverable={deliverable_id[:8]}")

    result = asyncio.run(_generate_async(
        deliverable_id=deliverable_id,
        version_id=version_id,
        user_id=user_id,
        supabase_url=supabase_url or os.environ.get("SUPABASE_URL"),
        supabase_key=supabase_key or os.environ.get("SUPABASE_SERVICE_KEY"),
    ))

    logger.info(f"[DELIVERABLE_WORKER] Completed: success={result.get('success')}")
    return result


async def _generate_async(
    deliverable_id: str,
    version_id: str,
    user_id: str,
    supabase_url: str,
    supabase_key: str,
) -> dict:
    """
    Async implementation using the simplified execution flow.
    """
    if not supabase_url or not supabase_key:
        logger.error("[DELIVERABLE_WORKER] Missing Supabase credentials")
        return {
            "success": False,
            "error": "Missing Supabase credentials",
        }

    client = create_client(supabase_url, supabase_key)

    try:
        # Get deliverable
        deliverable_result = (
            client.table("deliverables")
            .select("*")
            .eq("id", deliverable_id)
            .single()
            .execute()
        )

        if not deliverable_result.data:
            return {"success": False, "error": "Deliverable not found"}

        deliverable = deliverable_result.data

        # ADR-042: Use simplified execution
        from services.deliverable_execution import execute_deliverable_generation

        result = await execute_deliverable_generation(
            client=client,
            user_id=user_id,
            deliverable=deliverable,
            trigger_context={"type": "background_worker"},
        )

        return result

    except Exception as e:
        logger.error(f"[DELIVERABLE_WORKER] Generation failed: {e}", exc_info=True)

        # Update version status to failed
        try:
            client.table("deliverable_versions").update({
                "status": "rejected",
                "feedback_notes": str(e),
            }).eq("id", version_id).execute()
        except Exception:
            pass

        return {
            "success": False,
            "error": str(e),
        }


# For direct execution (development/testing)
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 4:
        print("Usage: python -m workers.deliverable_worker <deliverable_id> <version_id> <user_id>")
        sys.exit(1)

    deliverable_id = sys.argv[1]
    version_id = sys.argv[2]
    user_id = sys.argv[3]

    result = generate_deliverable(deliverable_id, version_id, user_id)
    print(f"Result: {result}")
