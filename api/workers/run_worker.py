"""
Development Worker Runner (ADR-039)

Runs the RQ worker for local development.
For production, use `rq worker work --url $REDIS_URL` directly.

Usage:
    cd api && python -m workers.run_worker
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import logging

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s [%(name)s] %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Run the RQ worker."""
    import redis
    from rq import Worker, Queue

    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")

    logger.info(f"Connecting to Redis at {redis_url[:30]}...")

    try:
        conn = redis.from_url(redis_url)
        conn.ping()
        logger.info("Redis connection successful")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        sys.exit(1)

    # Create queue
    queue = Queue("work", connection=conn)
    logger.info(f"Queue 'work' has {len(queue)} pending jobs")

    # Create and start worker
    worker = Worker([queue], connection=conn, name="yarnnn-worker-dev")
    logger.info("Starting worker... Press Ctrl+C to stop")

    try:
        worker.work(with_scheduler=False, logging_level="INFO")
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")


if __name__ == "__main__":
    main()
