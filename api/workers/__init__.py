"""
YARNNN Workers (ADR-039: Background Work Agents)

Background worker processes for async job execution.
Run via RQ (Redis Queue):

    rq worker work --url $REDIS_URL

Or for development:

    cd api && python -m workers.run_worker
"""
