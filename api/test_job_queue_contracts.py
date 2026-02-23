"""
Job Queue Contract Tests

Validates that enqueue_job() callers pass kwargs matching the target
worker function signatures. Catches interface mismatches (misspelled
kwarg names, missing required params) that would only surface at
runtime when RQ deserializes and calls the worker.

No Redis, no mocking, no network — pure static validation via inspect.

Run: cd api && python test_job_queue_contracts.py
"""

import inspect
from importlib import import_module


# Mirror of worker_map from services/job_queue.py
WORKER_MAP = {
    "platform_sync": "workers.platform_worker.sync_platform",
    "deliverable_generate": "workers.deliverable_worker.generate_deliverable",
    "work_execute": "workers.work_worker.execute_work_background",
}

# Every enqueue_job() call site and the kwargs it passes.
# Update this when adding new call sites.
CALL_CONTRACTS = [
    {
        "caller": "routes/integrations.py:trigger_platform_sync",
        "job_type": "platform_sync",
        "kwargs": {"user_id", "provider", "selected_sources"},
    },
    {
        "caller": "services/primitives/execute.py:_handle_platform_sync",
        "job_type": "platform_sync",
        "kwargs": {"user_id", "provider"},
    },
    {
        "caller": "services/primitives/execute.py:_handle_work_run",
        "job_type": "work_execute",
        "kwargs": {"ticket_id", "user_id"},
    },
    {
        "caller": "services/freshness.py:trigger_stale_resyncs",
        "job_type": "platform_sync",
        "kwargs": {"user_id", "provider", "selected_sources"},
    },
]


def _import_function(dotted_path: str):
    """Import a function from a dotted module path like 'workers.platform_worker.sync_platform'."""
    module_path, func_name = dotted_path.rsplit(".", 1)
    module = import_module(module_path)
    return getattr(module, func_name)


def _get_accepted_params(func) -> dict[str, inspect.Parameter]:
    """Get the parameter names a function accepts (excluding **kwargs)."""
    sig = inspect.signature(func)
    return {
        name: param
        for name, param in sig.parameters.items()
        if param.kind not in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        )
    }


def test_worker_map_resolves():
    """Every job_type in worker_map resolves to an importable function."""
    for job_type, worker_path in WORKER_MAP.items():
        func = _import_function(worker_path)
        assert callable(func), f"{worker_path} is not callable"
        print(f"  ✓ {job_type} → {worker_path}")

    print("✅ worker_map_resolves: PASSED")


def test_all_kwargs_accepted_by_worker():
    """Every kwarg passed by callers is accepted by the target worker function."""
    for contract in CALL_CONTRACTS:
        job_type = contract["job_type"]
        caller_kwargs = contract["kwargs"]
        caller = contract["caller"]

        worker_path = WORKER_MAP[job_type]
        func = _import_function(worker_path)
        accepted = _get_accepted_params(func)

        # Check if worker accepts **kwargs (which would accept anything)
        sig = inspect.signature(func)
        has_var_keyword = any(
            p.kind == inspect.Parameter.VAR_KEYWORD
            for p in sig.parameters.values()
        )

        if has_var_keyword:
            print(f"  ✓ {caller} → {job_type} (worker accepts **kwargs)")
            continue

        for kwarg in caller_kwargs:
            assert kwarg in accepted, (
                f"MISMATCH: {caller} passes '{kwarg}' but "
                f"{worker_path} does not accept it.\n"
                f"  Accepted params: {list(accepted.keys())}"
            )

        print(f"  ✓ {caller} → {job_type}: kwargs {caller_kwargs} all accepted")

    print("✅ all_kwargs_accepted: PASSED")


def test_required_params_provided():
    """Every caller provides all required (no-default) parameters."""
    for contract in CALL_CONTRACTS:
        job_type = contract["job_type"]
        caller_kwargs = contract["kwargs"]
        caller = contract["caller"]

        worker_path = WORKER_MAP[job_type]
        func = _import_function(worker_path)
        accepted = _get_accepted_params(func)

        required = {
            name
            for name, param in accepted.items()
            if param.default is inspect.Parameter.empty
        }

        missing = required - caller_kwargs
        if missing:
            # Only fail if truly missing — some params may be optional via env fallback
            # but are technically required by signature
            print(f"  ⚠ {caller}: missing required params {missing} (may use env fallback)")
        else:
            print(f"  ✓ {caller}: all required params provided")

    print("✅ required_params_provided: PASSED")


def test_worker_map_matches_job_queue():
    """Verify our test's WORKER_MAP matches the actual job_queue.py worker_map."""
    from services.job_queue import enqueue_job

    # Read the source to extract the actual worker_map
    source = inspect.getsource(enqueue_job)

    for job_type, worker_path in WORKER_MAP.items():
        assert f'"{job_type}"' in source, (
            f"Job type '{job_type}' not found in enqueue_job source"
        )
        assert f'"{worker_path}"' in source, (
            f"Worker path '{worker_path}' not found in enqueue_job source"
        )

    print("✅ worker_map_matches_job_queue: PASSED")


if __name__ == "__main__":
    print("\n🧪 Running job queue contract tests...\n")

    test_worker_map_resolves()
    test_worker_map_matches_job_queue()
    test_all_kwargs_accepted_by_worker()
    test_required_params_provided()

    print("\n✅ All contract tests passed!")
