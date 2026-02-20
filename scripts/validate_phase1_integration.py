#!/usr/bin/env python3
"""
Validation script for Phase 1-3 integration

Verifies that:
1. Manual signal processing includes Layer 4 content
2. Automated cron includes Layer 4 content
3. New deliverable types are registered
4. Memory extraction is wired to approval endpoint
5. Pattern detection is scheduled
6. TP tools reference correct deliverable types
"""

import ast
import sys
from pathlib import Path

# Project root
ROOT = Path(__file__).parent.parent

def validate_signal_processing_manual_trigger():
    """Validate manual signal processing includes Layer 4 content."""
    print("\n🔍 Validating manual signal processing trigger...")

    file_path = ROOT / "api/routes/signal_processing.py"
    content = file_path.read_text()

    # Check for deliverable_versions join
    if "deliverable_versions!inner" not in content:
        print("❌ Manual trigger missing deliverable_versions join")
        return False

    # Check for recent_content extraction
    if "recent_content" not in content or "recent_version_date" not in content:
        print("❌ Manual trigger missing Layer 4 content extraction")
        return False

    print("✅ Manual trigger includes Layer 4 content")
    return True


def validate_signal_processing_cron():
    """Validate automated cron includes Layer 4 content."""
    print("\n🔍 Validating automated signal processing cron...")

    file_path = ROOT / "api/jobs/unified_scheduler.py"
    content = file_path.read_text()

    # Check for deliverable_versions join in signal processing section
    if "deliverable_versions!inner" not in content:
        print("❌ Cron missing deliverable_versions join")
        return False

    # Check for recent_content extraction
    if "recent_content" not in content or "recent_version_date" not in content:
        print("❌ Cron missing Layer 4 content extraction")
        return False

    print("✅ Automated cron includes Layer 4 content")
    return True


def validate_new_deliverable_types():
    """Validate Phase 2 deliverable types are registered."""
    print("\n🔍 Validating new deliverable types...")

    file_path = ROOT / "api/routes/deliverables.py"
    content = file_path.read_text()

    required_types = ["deep_research", "daily_strategy_reflection", "intelligence_brief"]

    for dtype in required_types:
        # Check in VALID_DELIVERABLE_TYPES
        if dtype not in content:
            print(f"❌ Missing deliverable type: {dtype}")
            return False

        # Check in DELIVERABLE_TYPE_STATUS
        if f'"{dtype}": "beta"' not in content:
            print(f"❌ Missing status for type: {dtype}")
            return False

    # Check type configs exist
    file_path = ROOT / "api/services/deliverable_pipeline.py"
    content = file_path.read_text()

    for dtype in required_types:
        # Check TYPE_PROMPTS
        if f'"{dtype}":' not in content:
            print(f"❌ Missing TYPE_PROMPTS entry for: {dtype}")
            return False

    print("✅ All new deliverable types registered")
    return True


def validate_memory_extraction_wiring():
    """Validate memory extraction is wired to approval endpoint."""
    print("\n🔍 Validating memory extraction wiring...")

    file_path = ROOT / "api/routes/deliverables.py"
    content = file_path.read_text()

    # Check for process_feedback import
    if "from services.memory import process_feedback" not in content:
        print("❌ Missing process_feedback import")
        return False

    # Check for async task creation
    if "asyncio.create_task(process_feedback(" not in content:
        print("❌ Missing process_feedback async task")
        return False

    # Check for activity log metadata enhancement
    if '"had_edits"' not in content or '"final_length"' not in content:
        print("❌ Missing enhanced activity log metadata")
        return False

    print("✅ Memory extraction wired to approval")
    return True


def validate_pattern_detection_scheduling():
    """Validate pattern detection is scheduled."""
    print("\n🔍 Validating pattern detection scheduling...")

    file_path = ROOT / "api/jobs/unified_scheduler.py"
    content = file_path.read_text()

    # Check for process_patterns import
    if "from services.memory import process_patterns" not in content:
        print("❌ Missing process_patterns import")
        return False

    # Check for midnight UTC scheduling logic
    if "now.hour == 0" not in content:
        print("❌ Missing midnight UTC scheduling")
        return False

    # Check for pattern detection call
    if "await process_patterns(" not in content:
        print("❌ Missing process_patterns call")
        return False

    print("✅ Pattern detection scheduled at midnight UTC")
    return True


def validate_pattern_detection_implementation():
    """Validate 5 pattern types are implemented."""
    print("\n🔍 Validating pattern detection implementation...")

    file_path = ROOT / "api/services/memory.py"
    content = file_path.read_text()

    required_patterns = [
        "pattern:deliverable_day",
        "pattern:deliverable_time",
        "pattern:deliverable_type_preference",
        "pattern:edit_location",
        "pattern:formatting_length",
    ]

    for pattern in required_patterns:
        if pattern not in content:
            print(f"❌ Missing pattern detection: {pattern}")
            return False

    print("✅ All 5 pattern types implemented")
    return True


def validate_type_prompts_count():
    """Validate TYPE_PROMPTS has exactly 24 entries."""
    print("\n🔍 Validating TYPE_PROMPTS count...")

    file_path = ROOT / "api/services/deliverable_pipeline.py"
    content = file_path.read_text()

    # Parse AST to find TYPE_PROMPTS dict
    try:
        tree = ast.parse(content)

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "TYPE_PROMPTS":
                        if isinstance(node.value, ast.Dict):
                            count = len(node.value.keys)
                            if count == 24:
                                print(f"✅ TYPE_PROMPTS has exactly 24 entries")
                                return True
                            else:
                                print(f"❌ TYPE_PROMPTS has {count} entries, expected 24")
                                return False
    except Exception as e:
        print(f"⚠️  Could not parse AST: {e}")
        # Fallback to counting with simple heuristic
        if content.count('"""') >= 48:  # Each prompt has opening/closing triple quotes
            print("✅ TYPE_PROMPTS appears complete (heuristic)")
            return True

    print("❌ Could not validate TYPE_PROMPTS count")
    return False


def validate_documentation():
    """Validate ADRs and documentation are created."""
    print("\n🔍 Validating documentation...")

    required_adrs = [
        "docs/adr/ADR-069-layer-4-content-in-signal-reasoning.md",
        "docs/adr/ADR-070-enhanced-activity-pattern-detection.md",
        "docs/adr/ADR-071-strategic-architecture-principles.md",
    ]

    for adr_path in required_adrs:
        if not (ROOT / adr_path).exists():
            print(f"❌ Missing ADR: {adr_path}")
            return False

    # Check four-layer-model.md has bidirectional learning section
    model_path = ROOT / "docs/architecture/four-layer-model.md"
    if model_path.exists():
        content = model_path.read_text()
        if "Bidirectional learning loops" not in content:
            print("❌ four-layer-model.md missing bidirectional learning section")
            return False

    print("✅ All documentation present")
    return True


def main():
    print("=" * 70)
    print("Phase 1-3 Integration Validation")
    print("=" * 70)

    validators = [
        validate_signal_processing_manual_trigger,
        validate_signal_processing_cron,
        validate_new_deliverable_types,
        validate_memory_extraction_wiring,
        validate_pattern_detection_scheduling,
        validate_pattern_detection_implementation,
        validate_type_prompts_count,
        validate_documentation,
    ]

    results = [v() for v in validators]

    print("\n" + "=" * 70)
    if all(results):
        print("✅ All validation checks passed!")
        print("=" * 70)
        return 0
    else:
        failed = sum(1 for r in results if not r)
        print(f"❌ {failed}/{len(results)} validation checks failed")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
