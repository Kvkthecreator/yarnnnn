"""
Capture drainer (ADR-393) — the scheduler-tick maintenance phase for captures.

An ADAPTER on the ONE drain loop (`services/scheduling.py::drain_due`, ADR-639
D3): this module supplies the capture kind's due scan and run body; the
claim → run → record-in-finally mechanics are the loop's. Before ADR-639 this
file carried a byte-twin of that loop beside the strings lane's.

A capture is deterministic, wakes no one, and runs in the scheduler tick's
maintenance phase behind its own flag (`services/capture_lane_gating.py`);
ADR-632 unwrapped it from the retired steward gate.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def drain_due_captures(client) -> tuple[int, int, int]:
    """Find due captures and run each one through the capture lane.

    Returns (found, succeeded, failed). The "run" is deterministic lane
    execution (zero LLM).
    """
    from services.capture.lane import run_capture_declaration
    from services.capture.scheduling import CAPTURE_KIND, due_captures, record_capture
    from services.scheduling import drain_due

    return await drain_due(
        client, CAPTURE_KIND,
        due=due_captures, run=run_capture_declaration, record=record_capture,
    )


__all__ = ["drain_due_captures"]
