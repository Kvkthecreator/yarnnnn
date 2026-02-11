"""
Quick test for primitives registry (ADR-038)

Run: cd api && python test_primitives.py
"""

from services.primitives import PRIMITIVES, execute_primitive
from services.primitives.registry import HANDLERS


def test_primitive_count():
    """Verify we have exactly 7 primitives (ADR-038)."""
    print(f"Primitive count: {len(PRIMITIVES)}")

    expected = ["Read", "Write", "Edit", "Search", "List", "Execute", "Clarify"]
    actual = [p["name"] for p in PRIMITIVES]

    print(f"Expected: {expected}")
    print(f"Actual:   {actual}")

    assert len(PRIMITIVES) == 7, f"Expected 7 primitives, got {len(PRIMITIVES)}"

    for name in expected:
        assert name in actual, f"Missing primitive: {name}"

    # Verify Respond and Todo are NOT in primitives
    assert "Respond" not in actual, "Respond should be removed"
    assert "Todo" not in actual, "Todo should be removed"

    print("✅ primitive_count: PASSED (7 primitives, no Respond/Todo)")


def test_handlers_exist():
    """Verify all primitives have handlers."""
    for prim in PRIMITIVES:
        name = prim["name"]
        assert name in HANDLERS, f"Missing handler for {name}"
        print(f"  ✓ {name} handler exists")

    print("✅ handlers_exist: PASSED")


def test_primitive_schemas():
    """Verify primitive schemas are valid for Claude tool use."""
    for prim in PRIMITIVES:
        name = prim["name"]
        assert "name" in prim, f"{name} missing 'name'"
        assert "description" in prim, f"{name} missing 'description'"
        assert "input_schema" in prim, f"{name} missing 'input_schema'"

        schema = prim["input_schema"]
        assert schema.get("type") == "object", f"{name} schema type should be 'object'"
        assert "properties" in schema, f"{name} schema missing 'properties'"

        print(f"  ✓ {name} schema valid")

    print("✅ primitive_schemas: PASSED")


def test_clarify_is_last():
    """Clarify should be last in the list (communication primitive)."""
    last = PRIMITIVES[-1]["name"]
    assert last == "Clarify", f"Expected Clarify last, got {last}"
    print("✅ clarify_is_last: PASSED")


if __name__ == "__main__":
    print("\n🧪 Running primitives registry tests...\n")

    test_primitive_count()
    test_handlers_exist()
    test_primitive_schemas()
    test_clarify_is_last()

    print("\n✅ All primitives tests passed!")
