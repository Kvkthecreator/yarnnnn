"""ADR-396 §11 — a computed field must SURVIVE the response model.

WHAT HAPPENED (2026-08-19): `get_usage_detail` was extended with `trend_days`,
`by_model`, `activity.spend_usd` and `by_work[].pct_runs`. The service computed
all four correctly — and `UsageDetailResponse` did not DECLARE them, so FastAPI
serialized them away. The API returned the pre-change 3-key shape while running
post-change code, with no error anywhere: no exception, no log line, no failing
test. The FE read the missing key and crashed the whole Workspace Settings door.

THE RULE THIS PINS: when the service dict grows a key, the Pydantic response
model must grow it too. A response model is a FILTER, not documentation —
anything it omits is dropped silently.

Run: python3 test_adr396_usage_payload_survives_serialization.py   (from api/)
"""
import json
import sys

sys.path.insert(0, ".")

failures = 0


def check(name, fn):
    global failures
    try:
        fn()
        print(f"  PASS  {name}")
    except Exception as e:  # noqa: BLE001
        failures += 1
        print(f"  FAIL  {name}\n        {e}")


print("\nadr396-usage-payload-survives-serialization:")

# The keys the service produces that did not exist in the original contract.
POST_CONTRACT_TOP = ("trend_days", "by_model")
POST_CONTRACT_NESTED = {
    "activity": ("spend_usd",),
    "by_work": ("pct_runs",),
    "trend": ("runs", "failed"),
}

SAMPLE = {
    "by_work": [
        {"slug": "lane", "runs": 175, "cost_usd": 15.51, "pct": 97, "pct_runs": 70}
    ],
    "trend": [{"date": "2026-08-18", "cost_usd": 4.76, "runs": 60, "failed": 0}],
    "trend_days": 23,
    "by_model": [
        {"model": "claude-sonnet-5", "runs": 80, "cost_usd": 8.05, "pct": 51}
    ],
    "activity": {
        "runs": 251,
        "success_rate": 100,
        "avg_cost_usd": 0.064,
        "failed": 0,
        "spend_usd": 15.9432,
    },
}


def _served():
    from routes.integrations import UsageDetailResponse

    resp = UsageDetailResponse(**SAMPLE)
    raw = resp.model_dump_json() if hasattr(resp, "model_dump_json") else resp.json()
    return json.loads(raw)


def top_level():
    served = _served()
    for k in POST_CONTRACT_TOP:
        if k not in served:
            raise AssertionError(
                f"'{k}' is computed by get_usage_detail but DROPPED by "
                f"UsageDetailResponse — declare it on the model"
            )


def nested():
    served = _served()
    for container, fields in POST_CONTRACT_NESTED.items():
        node = served[container]
        node = node[0] if isinstance(node, list) else node
        for f in fields:
            if f not in node:
                raise AssertionError(
                    f"'{container}.{f}' is computed but DROPPED by its response "
                    f"model — declare it"
                )


def values_round_trip():
    """Declaring the field is not enough; the VALUE must survive intact."""
    served = _served()
    if served["trend_days"] != 23:
        raise AssertionError(f"trend_days mangled: {served['trend_days']}")
    if len(served["by_model"]) != 1 or served["by_model"][0]["model"] != "claude-sonnet-5":
        raise AssertionError(f"by_model mangled: {served['by_model']}")
    if abs(served["activity"]["spend_usd"] - 15.9432) > 1e-6:
        raise AssertionError(f"spend_usd mangled: {served['activity']['spend_usd']}")
    if served["by_work"][0]["pct_runs"] != 70:
        raise AssertionError(f"pct_runs mangled: {served['by_work'][0]['pct_runs']}")


def service_keys_are_all_declared():
    """The real guard: every top-level key the SERVICE returns must be declared.

    Reads the service's own `empty` literal rather than a hand-kept list, so a
    future key is caught without editing this gate.
    """
    import re

    src = open("services/platform_limits.py").read()
    i = src.index("def get_usage_detail")
    block = src[i : src.index("try:", i)]
    keys = set(re.findall(r'"(\w+)":', block))
    # nested activity keys live one level down; keep to the top-level contract
    keys -= {"runs", "success_rate", "avg_cost_usd", "failed", "spend_usd"}
    served = set(_served().keys())
    missing = keys - served
    if missing:
        raise AssertionError(
            f"service returns key(s) the response model drops: {sorted(missing)}"
        )


check("post-contract top-level fields survive serialization", top_level)
check("post-contract nested fields survive serialization", nested)
check("values round-trip intact, not just the keys", values_round_trip)
check("every key in the service's empty-shape is declared", service_keys_are_all_declared)

print(
    f"\nadr396-usage-payload gate: {4 - failures}/4 passed"
    if failures == 0
    else f"\nadr396-usage-payload gate: {failures} FAILED"
)
sys.exit(1 if failures else 0)
