"""
Deliverable Generation Worker

Background worker for generating deliverable content.
Called by RQ when deliverable_generate jobs are enqueued.

This runs the 3-step deliverable pipeline:
1. Gather - Pull context from sources
2. Synthesize - Generate content
3. Stage - Validate and mark for review
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

    Args:
        deliverable_id: Deliverable to generate
        version_id: Version record to update
        user_id: User ID who owns the deliverable
        supabase_url: Supabase URL (uses env var if not provided)
        supabase_key: Service role key (uses env var if not provided)

    Returns:
        Dict with generation result
    """
    logger.info(f"[DELIVERABLE_WORKER] Starting generation: deliverable={deliverable_id[:8]}, version={version_id[:8]}")

    result = asyncio.run(_generate_async(
        deliverable_id=deliverable_id,
        version_id=version_id,
        user_id=user_id,
        supabase_url=supabase_url or os.environ.get("SUPABASE_URL"),
        supabase_key=supabase_key or os.environ.get("SUPABASE_SERVICE_ROLE_KEY"),
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
    Async implementation of deliverable generation.
    """
    if not supabase_url or not supabase_key:
        logger.error("[DELIVERABLE_WORKER] Missing Supabase credentials")
        return {
            "success": False,
            "error": "Missing Supabase credentials",
        }

    client = create_client(supabase_url, supabase_key)

    try:
        # Import the pipeline
        from services.deliverable_pipeline import run_deliverable_pipeline

        # Run the pipeline
        result = await run_deliverable_pipeline(
            client=client,
            deliverable_id=deliverable_id,
            version_id=version_id,
            user_id=user_id,
        )

        return result

    except Exception as e:
        logger.error(f"[DELIVERABLE_WORKER] Generation failed: {e}", exc_info=True)

        # Update version status to failed
        try:
            client.table("deliverable_versions").update({
                "status": "failed",
                "error_message": str(e),
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
