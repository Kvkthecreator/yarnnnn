"""
Quick tests for platform registry (ADR-047)

Run: cd api && python test_platform_registry.py
"""

from integrations.platform_registry import (
    get_platform_config,
    get_supported_platforms,
    validate_param,
    validate_params,
    map_params_to_mcp,
    get_tp_guidance,
)


def test_supported_platforms():
    """Verify we have the expected platforms."""
    platforms = get_supported_platforms()
    expected = ["slack", "gmail", "notion"]

    print(f"Supported platforms: {platforms}")

    for p in expected:
        assert p in platforms, f"Missing platform: {p}"

    print("✅ supported_platforms: PASSED")


def test_slack_config():
    """Verify Slack configuration is correct."""
    config = get_platform_config("slack")
    assert config is not None
    assert config["mcp_server"] == "@modelcontextprotocol/server-slack"
    assert "channel" in config["params"]
    assert config["params"]["channel"]["mcp_name"] == "channel_id"

    print("✅ slack_config: PASSED")


def test_validate_slack_channel():
    """Test Slack channel validation."""
    # Valid formats - channels
    valid, error = validate_param("slack", "channel", "C0123ABC456")
    assert valid, f"Channel ID should be valid: {error}"

    valid, error = validate_param("slack", "channel", "#general")
    assert valid, f"#channel should be valid: {error}"

    # Valid formats - user IDs for DMs
    valid, error = validate_param("slack", "channel", "U0123ABC456")
    assert valid, f"User ID should be valid (for DMs): {error}"

    # Invalid formats
    valid, error = validate_param("slack", "channel", "@me")
    assert not valid, "@me should be invalid"
    assert "@me" in error or "invalid" in error.lower()

    valid, error = validate_param("slack", "channel", "@username")
    assert not valid, "@username should be invalid"

    print("✅ validate_slack_channel: PASSED")


def test_validate_params():
    """Test full params validation."""
    # Valid
    is_valid, errors = validate_params("slack", {"channel": "#general", "message": "Hello"})
    assert is_valid, f"Should be valid: {errors}"

    # Invalid channel
    is_valid, errors = validate_params("slack", {"channel": "@me", "message": "Hello"})
    assert not is_valid, "Should be invalid"
    assert len(errors) > 0

    # Missing message
    is_valid, errors = validate_params("slack", {"channel": "#general"})
    assert not is_valid, "Should be invalid (missing message)"

    print("✅ validate_params: PASSED")


def test_map_params_to_mcp():
    """Test parameter name mapping."""
    mapped = map_params_to_mcp("slack", {"channel": "#general", "message": "Hello"})

    assert "channel_id" in mapped, "Should map channel to channel_id"
    assert "text" in mapped, "Should map message to text"
    assert mapped["channel_id"] == "#general"
    assert mapped["text"] == "Hello"

    print("✅ map_params_to_mcp: PASSED")


def test_tp_guidance():
    """Test TP guidance generation."""
    guidance = get_tp_guidance("slack")

    assert "Slack" in guidance
    assert "channel" in guidance.lower()
    assert "@me" in guidance or "invalid" in guidance.lower()  # Should mention invalid formats

    print(f"\nSlack guidance:\n{guidance}\n")
    print("✅ tp_guidance: PASSED")


def test_notion_config():
    """Verify Notion configuration is correct."""
    config = get_platform_config("notion")
    assert config is not None
    assert config["display_name"] == "Notion"
    assert "page_id" in config["params"]
    assert "content" in config["params"]
    assert "add_comment" in config["capabilities"]

    print("✅ notion_config: PASSED")


def test_validate_notion_page_id():
    """Test Notion page_id validation."""
    # Valid formats - UUID with dashes
    valid, error = validate_param("notion", "page_id", "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    assert valid, f"UUID with dashes should be valid: {error}"

    # Valid formats - UUID without dashes
    valid, error = validate_param("notion", "page_id", "a1b2c3d4e5f67890abcdef1234567890")
    assert valid, f"UUID without dashes should be valid: {error}"

    # Valid formats - Notion URL
    valid, error = validate_param("notion", "page_id", "https://notion.so/workspace/Page-abc123")
    assert valid, f"Notion URL should be valid: {error}"

    # Valid formats - Notion Sites URL
    valid, error = validate_param("notion", "page_id", "https://myspace.notion.site/Page-abc123")
    assert valid, f"Notion Sites URL should be valid: {error}"

    # Invalid formats - @mention style
    valid, error = validate_param("notion", "page_id", "@my-page")
    assert not valid, "@mention should be invalid"

    print("✅ validate_notion_page_id: PASSED")


def test_notion_tp_guidance():
    """Test Notion TP guidance generation."""
    guidance = get_tp_guidance("notion")

    assert "Notion" in guidance
    assert "page_id" in guidance.lower()

    print(f"\nNotion guidance:\n{guidance}\n")
    print("✅ notion_tp_guidance: PASSED")


if __name__ == "__main__":
    print("\n🧪 Running platform registry tests...\n")

    # Slack tests
    test_supported_platforms()
    test_slack_config()
    test_validate_slack_channel()
    test_validate_params()
    test_map_params_to_mcp()
    test_tp_guidance()

    # Notion tests
    test_notion_config()
    test_validate_notion_page_id()
    test_notion_tp_guidance()

    print("\n✅ All platform registry tests passed!")
