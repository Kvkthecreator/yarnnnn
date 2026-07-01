"""
services/capture — the perception/capture pipeline (ADR-393).

Capture is deterministic, upstream, intent-free perception (ADR-335/389:
peripherals are driver-class transports, judged for HEALTH not honesty). It
runs on cadence to MAKE substrate fresh; it wakes no one. This is the lane
the mechanical `@primitive: ...` work moved OUT of the wake/Reviewer funnel
into — the "theatre" bypass (`wake.py::_dispatch_mechanical`, pre-ADR-393)
is deleted, not carried as a fallback.

The two concerns are now cleanly separated:

  - `_recurrences.yaml`  — the AGENT's judgment scheduling (a recurrence is a
                           judgment prompt; the wake funnel serves it). Owner:
                           `services.recurrence` + `services.wake`.
  - `_captures.yaml`     — deterministic intake declarations (connector
                           captures, ground-truth state mirrors, perception
                           watches, substrate mirrors). Owner: THIS package.

The capture lane runs as a maintenance phase in the scheduler tick — sibling
to `services.kernel_mirrors` + `services.wake_drainer`, never inside
`wake.py`. Same precedent: kernel maintenance runs scheduler-side, not as a
workspace-side recurrence.

Public surface:
  - declarations.py — CaptureDeclaration dataclass, parse/walk, the thin
                      per-declaration health signal (_capture_signal.yaml).
  - lane.py         — run_capture_declaration: parse directive → HANDLERS →
                      execute deterministically → write health signal →
                      execution_events(funnel_decision="capture"). No LLM.
"""

from __future__ import annotations

from services.capture.declarations import (
    CaptureDeclaration,
    capture_signal_path,
    captures_path,
    parse_captures_yaml,
    walk_workspace_captures,
    write_capture_signal,
)

__all__ = [
    "CaptureDeclaration",
    "capture_signal_path",
    "captures_path",
    "parse_captures_yaml",
    "walk_workspace_captures",
    "write_capture_signal",
]
