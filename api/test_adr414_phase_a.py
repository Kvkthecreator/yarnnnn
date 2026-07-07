"""ADR-414 Phase A regression gate — the re-key remainders stay closed.

Three files carried raw ``.eq("user_id", ...)`` substrate filters after the
ADR-373/407 sweeps (the named remainders): ``services/bundle_reader.py``,
``routes/integrations.py``, and the scheduler's tasks-index read. Phase A
swept them to ``substrate_scope_filter``. This gate keeps them swept.

The scheduler's owner-keyed ITERATION unit is NOT a violation — it is the
ratified wake-stack contract (ADR-408 ``acting_workspace_owner``; ADR-373 D1
one-owner-one-workspace). Only substrate-table FILTERS are gated here.
"""

import re
from pathlib import Path

API = Path(__file__).resolve().parent

RAW_FILTER = re.compile(r'\.eq\(\s*"user_id"\s*,')

SWEPT_FILES = [
    "services/bundle_reader.py",
    "routes/integrations.py",
    "jobs/unified_scheduler.py",
]


def _source(rel: str) -> str:
    return (API / rel).read_text()


def test_no_raw_user_id_filters_in_swept_files():
    """No swept file regresses to a raw user_id substrate filter."""
    offenders = {}
    for rel in SWEPT_FILES:
        hits = [
            i + 1
            for i, line in enumerate(_source(rel).splitlines())
            if RAW_FILTER.search(line)
        ]
        if hits:
            offenders[rel] = hits
    assert not offenders, (
        f"raw .eq(\"user_id\", ...) substrate filters reappeared: {offenders} — "
        "use .eq(*substrate_scope_filter(user_id)) per ADR-373/407/414 Phase A"
    )


def test_swept_files_import_the_scope_helper():
    for rel in ["services/bundle_reader.py", "routes/integrations.py"]:
        assert "substrate_scope_filter" in _source(rel), (
            f"{rel} lost its substrate_scope_filter usage"
        )


def test_scheduler_tasks_read_is_scope_filtered():
    src = _source("jobs/unified_scheduler.py")
    assert "substrate_scope_filter" in src, (
        "scheduler tasks-index read must go through substrate_scope_filter "
        "(ADR-414 Phase A)"
    )
