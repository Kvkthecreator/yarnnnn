"""
Output Validation Tests — Headless Agent Draft Quality

Tests the guardrails that prevent tool-use narration from leaking into
agent outputs (fix for Slack Recap v2 empty-output bug, 2026-03-16).

Covers:
1. _strip_tool_narration() — detects and rejects narration-only drafts
2. validate_output() — minimum content checks per skill type
3. Integration: narration + short-draft scenarios

No LLM calls or DB required — pure unit tests.
"""

import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def test_strip_tool_narration():
    """Test that tool-use narration is detected and stripped."""
    from services.agent_execution import _strip_tool_narration

    results = []

    # Case 1: Pure narration — should be stripped to empty
    narration_drafts = [
        "Let me check what platform content is available in your system.",
        "Let me search for recent Slack activity.",
        "I'll check the available platform content.",
        "Searching for platform content...",
        "Let me look at what's available.",
        "Let me find the relevant Slack channels.",
    ]
    for draft in narration_drafts:
        result = _strip_tool_narration(draft)
        passed = result == ""
        results.append(("strip_narration", draft[:50], passed))
        if not passed:
            logger.warning(f"  FAIL: Expected empty, got: {result[:80]}")

    # Case 2: Real content — should NOT be stripped
    real_drafts = [
        "## Highlights\n\n- Team discussed the Q2 roadmap in #engineering\n- No activity in #general this week",
        "No recent Slack activity was detected for the configured sources.\n\n## Highlights\n\nNothing to report.",
        "## Highlights\n\n- **Decision**: Moving to microservices architecture\n- Sprint 42 retrospective completed\n\n## By Source\n\n### #engineering\nActive discussion about deployment pipeline.",
    ]
    for draft in real_drafts:
        result = _strip_tool_narration(draft)
        passed = result == draft
        results.append(("keep_real_content", draft[:50], passed))
        if not passed:
            logger.warning(f"  FAIL: Real content was incorrectly stripped")

    # Case 3: Short but valid "no activity" message — should NOT be stripped
    valid_short = "No recent Slack activity was found for the configured sources during this period."
    result = _strip_tool_narration(valid_short)
    passed = result == valid_short
    results.append(("keep_valid_short", valid_short[:50], passed))

    # Case 4: Empty input
    result = _strip_tool_narration("")
    passed = result == ""
    results.append(("empty_input", "(empty)", passed))

    # Report
    total = len(results)
    passed_count = sum(1 for _, _, p in results if p)
    logger.info(f"\n{'='*60}")
    logger.info(f"_strip_tool_narration: {passed_count}/{total} passed")
    for category, detail, p in results:
        status = "PASS" if p else "FAIL"
        logger.info(f"  [{status}] {category}: {detail}")

    return passed_count == total


def test_validate_output():
    """Test validate_output catches quality issues per skill type."""
    from services.orchestration_prompts import validate_output

    results = []

    # Digest: too short
    v = validate_output("digest", "Short content here.", {})
    passed = not v["valid"]  # Should flag as invalid (< 50 words)
    results.append(("digest_too_short", passed))

    # Digest: missing bullets
    long_no_bullets = "This is a long recap. " * 30
    v = validate_output("digest", long_no_bullets, {})
    has_bullet_issue = any("bullet" in i.lower() for i in v.get("issues", []))
    results.append(("digest_no_bullets", has_bullet_issue))

    # Digest: valid
    valid_digest = "## Highlights\n\n" + "\n".join(
        f"- Point {i}: Important discussion about topic {i}" for i in range(10)
    ) + "\n\n## By Source\n\n### #engineering\n- Active discussion about deployments"
    v = validate_output("digest", valid_digest, {})
    results.append(("digest_valid", v["valid"]))

    # Research: too short
    v = validate_output("research", "Brief insight.", {})
    passed = not v["valid"]
    results.append(("research_too_short", passed))

    # Synthesize: too short for standard
    v = validate_output("synthesize", "Very brief summary. " * 10, {"detail_level": "standard"})
    has_length_issue = any("short" in i.lower() for i in v.get("issues", []))
    results.append(("synthesize_too_short", has_length_issue))

    # Report
    total = len(results)
    passed_count = sum(1 for _, p in results if p)
    logger.info(f"\n{'='*60}")
    logger.info(f"validate_output: {passed_count}/{total} passed")
    for name, p in results:
        status = "PASS" if p else "FAIL"
        logger.info(f"  [{status}] {name}")

    return passed_count == total


def test_narration_patterns_comprehensive():
    """Test edge cases for narration detection."""
    from services.agent_execution import _strip_tool_narration

    results = []

    # Multi-line narration — should be stripped
    multi_narration = "Let me check the platform content.\nSearching for Slack data..."
    result = _strip_tool_narration(multi_narration)
    results.append(("multiline_narration", result == ""))

    # Narration mixed with real content (>30 words) — should NOT be stripped
    mixed = (
        "Let me check the available content.\n\n"
        "## Highlights\n\n"
        "- Team discussed Q2 roadmap in engineering channel\n"
        "- Three new PRs merged for the auth system\n"
        "- Design review scheduled for Friday\n"
    )
    result = _strip_tool_narration(mixed)
    results.append(("mixed_keep", result == mixed))

    # Just whitespace
    result = _strip_tool_narration("   \n  \n  ")
    results.append(("whitespace_only", result == ""))

    # Report
    total = len(results)
    passed_count = sum(1 for _, p in results if p)
    logger.info(f"\n{'='*60}")
    logger.info(f"narration_edge_cases: {passed_count}/{total} passed")
    for name, p in results:
        status = "PASS" if p else "FAIL"
        logger.info(f"  [{status}] {name}")

    return passed_count == total


if __name__ == "__main__":
    all_passed = True
    all_passed &= test_strip_tool_narration()
    all_passed &= test_validate_output()
    all_passed &= test_narration_patterns_comprehensive()

    logger.info(f"\n{'='*60}")
    if all_passed:
        logger.info("ALL TESTS PASSED")
    else:
        logger.error("SOME TESTS FAILED")
        exit(1)
