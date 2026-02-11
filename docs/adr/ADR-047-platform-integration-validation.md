# ADR-047: Platform Integration Validation

> **Status**: Draft
> **Created**: 2026-02-11
> **Related**: ADR-026 (Integration Architecture), ADR-039 (Agentic Platform Operations), ADR-040 (Proactive Notifications)

---

## Context

Platform integrations (Slack, Gmail, Notion) have platform-specific quirks that are discovered at runtime:

- MCP servers expect different parameter names than documented (`channel_id` vs `channel`)
- Platforms have different addressing schemes (Slack: `C...` IDs, `#name`; Gmail: emails; Notion: UUIDs)
- Invalid formats that "look right" to TP fail silently or with cryptic errors (`@me`, `@self`)
- Each platform has unique authentication flows and token types

**Current problem**: These quirks are discovered in production, causing:
1. Failed operations that confuse users
2. TP generating plausible-but-invalid requests
3. Debugging cycles that could be prevented
4. No systematic knowledge capture for future platforms

---

## Decision

**Platform integration validation becomes a formal phase during onboarding, not a production debugging exercise.**

### Core Components

#### 1. Platform Quirks Registry

A structured registry documenting platform-specific behaviors:

```python
# api/integrations/platform_registry.py

PLATFORM_REGISTRY = {
    "slack": {
        "mcp_server": "@modelcontextprotocol/server-slack",
        "params": {
            "channel": {
                "mcp_name": "channel_id",  # What MCP actually expects
                "valid_formats": ["C*", "#*"],  # Channel ID or #name
                "invalid_formats": ["@*"],  # @mentions don't work
                "resolution": "list_platform_resources",  # How to find valid values
            }
        },
        "capabilities": {
            "send_message": True,
            "send_dm": "requires_channel_lookup",  # Not direct
            "list_channels": True,
            "read_history": True,
        },
        "known_quirks": [
            "MCP expects 'channel_id' not 'channel'",
            "DMs require opening conversation first",
            "#channel names may need resolution to C... IDs",
        ],
    },
    "gmail": {
        "mcp_server": None,  # Direct API, not MCP
        "params": {
            "to": {
                "valid_formats": ["*@*.*"],  # Email pattern
            },
            "thread_id": {
                "valid_formats": ["*"],  # Gmail thread ID
                "resolution": "list_gmail_messages",
            }
        },
        "capabilities": {
            "send_message": True,
            "create_draft": True,
            "list_messages": True,
            "read_thread": True,
        },
        "auth": {
            "type": "oauth_refresh",
            "requires": ["refresh_token", "client_id", "client_secret"],
        },
    },
    "notion": {
        "mcp_server": "@notionhq/notion-mcp-server",
        "params": {
            "page_id": {
                "valid_formats": ["uuid", "url"],
                "resolution": "search_notion_pages",
            }
        },
        "capabilities": {
            "create_page": True,
            "add_comment": True,
            "search": True,
        },
    },
}
```

#### 2. Integration Validation Phase

When a user connects a platform, run validation tests before marking it "active":

```python
# api/integrations/validation.py

async def validate_integration(auth, provider: str) -> ValidationResult:
    """
    Run validation tests for a newly connected integration.

    Returns detailed results about what works and what doesn't.
    """
    results = ValidationResult(provider=provider)

    # 1. Auth validation - can we authenticate?
    results.auth = await test_auth(auth, provider)

    # 2. Read validation - can we list resources?
    results.read = await test_list_resources(auth, provider)

    # 3. Write validation - can we send a test message?
    if provider == "slack":
        results.write = await test_slack_send(auth, test_channel=results.read.first_channel)
    elif provider == "gmail":
        results.write = await test_gmail_draft(auth)  # Draft, don't send
    elif provider == "notion":
        results.write = await test_notion_comment(auth, test_page=results.read.first_page)

    # 4. Capture actual parameter formats that worked
    results.discovered_params = capture_working_params(results)

    return results
```

#### 3. Health Check Endpoint

```
GET /api/integrations/{provider}/health

Response:
{
  "provider": "slack",
  "status": "healthy",
  "last_validated": "2026-02-11T10:00:00Z",
  "capabilities": {
    "send_message": {"status": "ok", "last_tested": "..."},
    "list_channels": {"status": "ok", "channels_found": 12},
    "read_history": {"status": "ok"}
  },
  "known_quirks": ["MCP expects 'channel_id' not 'channel'"],
  "recommended_actions": []
}
```

#### 4. TP Consumes Registry

Instead of hardcoded documentation, TP reads the registry:

```python
def get_platform_guidance(provider: str) -> str:
    """Generate TP guidance from registry."""
    config = PLATFORM_REGISTRY.get(provider, {})

    guidance = []
    for param, spec in config.get("params", {}).items():
        if spec.get("invalid_formats"):
            guidance.append(
                f"For {param}: use {spec['valid_formats']}, "
                f"NOT {spec['invalid_formats']}"
            )
        if spec.get("resolution"):
            guidance.append(
                f"Use {spec['resolution']} to find valid {param} values"
            )

    return "\n".join(guidance)
```

#### 5. Changelog for Platform Updates

Track changes to platform behaviors over time:

```markdown
# docs/integrations/CHANGELOG.md

## 2026-02-11

### Slack
- **Breaking**: MCP server expects `channel_id` not `channel` for `slack_post_message`
- **Known issue**: `@username` format not supported; use channel ID lookup for DMs
- **Workaround**: Call `list_platform_resources` before `platform.send`

### Gmail
- No changes

### Notion
- No changes
```

---

## Implementation Phases

### Phase 1: Documentation (Immediate)
- Create `docs/integrations/CHANGELOG.md`
- Create `docs/integrations/QUIRKS.md` with current known issues
- Document Slack channel_id discovery

### Phase 2: Registry (Short-term)
- Implement `PLATFORM_REGISTRY` structure
- Add validation helpers
- TP reads registry for guidance

### Phase 3: Validation Endpoint (Medium-term)
- `/api/integrations/{provider}/validate` endpoint
- Run during OAuth callback
- Store validation results in `user_integrations.metadata`

### Phase 4: Health Monitoring (Future)
- Periodic health checks
- Alert on capability degradation
- Auto-suggest re-validation when MCP servers update

---

## Consequences

### Positive
- Platform issues discovered during setup, not production
- Systematic knowledge capture reduces repeat debugging
- TP gets accurate, up-to-date platform guidance
- New platforms have clear integration checklist
- Changelog enables versioning and migration support

### Negative
- Upfront investment in validation infrastructure
- Registry needs maintenance as platforms evolve
- May slow down initial integration setup (validation takes time)

### Mitigations
- Validation runs in background after OAuth
- Registry updates are lightweight (just config)
- Changelog is append-only, low friction

---

## Testing Strategy

### Unit Tests
- Validate registry schema correctness
- Test parameter format validation regex
- Test TP guidance generation

### Integration Tests
- Mock MCP servers for validation flow
- Test each platform's validation sequence
- Verify health endpoint responses

### Manual Validation Checklist
For each new platform:
1. [ ] OAuth flow completes successfully
2. [ ] Can list resources (channels/labels/pages)
3. [ ] Can send test message (or create draft)
4. [ ] Parameter names match MCP expectations
5. [ ] Error messages are actionable
6. [ ] Quirks documented in registry

---

## See Also

- [ADR-026: Integration Architecture](ADR-026-integration-architecture.md)
- [ADR-039: Agentic Platform Operations](ADR-039-agentic-platform-operations.md)
- [Integration Changelog](../integrations/CHANGELOG.md)
- [Platform Quirks Guide](../integrations/QUIRKS.md)
