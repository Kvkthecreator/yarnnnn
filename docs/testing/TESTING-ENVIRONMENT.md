# Testing Environment Guide

> **Purpose**: Quick reference for local testing and validation
> **Updated**: 2026-02-10

---

## Quick Start

### Required Environment Variables

```bash
# api/.env
SUPABASE_URL=https://noxgqcwynkzqabljjyon.supabase.co
SUPABASE_SERVICE_KEY=sb_secret_-8NWVKf09Cf56mO3JrjPqw_5FqL423G
ANTHROPIC_API_KEY=<your-key>
OPENAI_API_KEY=<your-key>  # Required for embeddings/skill detection
```

### Start API Server

```bash
cd api
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Health check: `curl http://localhost:8000/health`

---

## Testing Patterns

### Pattern 1: Direct Python Tests (Primitives, Services)

Best for testing backend logic without HTTP overhead.

```python
import asyncio
import os

# Set env vars
os.environ["SUPABASE_URL"] = "https://noxgqcwynkzqabljjyon.supabase.co"
os.environ["SUPABASE_SERVICE_KEY"] = "sb_secret_-8NWVKf09Cf56mO3JrjPqw_5FqL423G"

from supabase import create_client

# Create authenticated client
supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_KEY"]
)

# Mock auth context (mimics UserClient from routes)
class MockAuth:
    def __init__(self, user_id, client):
        self.user_id = user_id
        self.client = client

auth = MockAuth("<user-uuid>", supabase)

# Test your code
from services.primitives import execute_primitive

async def test():
    result = await execute_primitive(auth, "List", {"pattern": "memory:*"})
    print(result)

asyncio.run(test())
```

**Key points**:
- Use `SUPABASE_SERVICE_KEY` to bypass RLS for testing
- Mock auth with `user_id` and `client` attributes
- Run with `asyncio.run()` for async functions

### Pattern 2: Agent Testing (TP with Primitives)

Testing the full TP agent flow requires additional env vars.

```python
os.environ["OPENAI_API_KEY"] = "<your-key>"  # For skill detection embeddings
os.environ["ANTHROPIC_API_KEY"] = "<your-key>"  # For Claude calls

from agents.thinking_partner import ThinkingPartnerAgent
from agents.base import ContextBundle

agent = ThinkingPartnerAgent()
context = ContextBundle(memories=[], documents=[])

async def test_agent():
    async for event in agent.execute_stream_with_tools(
        task="What memories do I have?",
        context=context,
        auth=auth,
        parameters={"include_context": True, "history": []},
    ):
        if event.type == "tool_use":
            print(f"[TOOL] {event.content['name']}")
        elif event.type == "tool_result":
            print(f"[RESULT] {event.content}")
```

**Common issues**:
- Missing `OPENAI_API_KEY` → skill detection fails
- Context too large → token limit exceeded (reduce history/context)

### Pattern 3: HTTP Endpoint Testing

For full E2E including auth middleware.

```bash
# Get a valid JWT (from browser dev tools or Supabase dashboard)
TOKEN="eyJ..."

curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"content": "List my memories", "include_context": true}'
```

---

## Test Users

Query available test users:

```bash
psql "postgresql://postgres.noxgqcwynkzqabljjyon:yarNNN%21%21%40%40%23%23%24%24@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require" \
  -c "SELECT id, email FROM auth.users LIMIT 5;"
```

---

## Database Queries

### Direct SQL Access

```bash
psql "postgresql://postgres.noxgqcwynkzqabljjyon:yarNNN%21%21%40%40%23%23%24%24@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require"
```

### Common Debug Queries

```sql
-- Count entities by user (ADR-059: user_context replaces memories)
SELECT user_id, COUNT(*) FROM user_context GROUP BY user_id;
SELECT user_id, COUNT(*) FROM deliverables GROUP BY user_id;

-- Recent memories
SELECT key, value, source, confidence, updated_at FROM user_context
WHERE user_id = '<uuid>'
ORDER BY updated_at DESC LIMIT 5;

-- Check platform connections (ADR-059: platform_connections replaces user_integrations)
SELECT platform, status, updated_at FROM platform_connections
WHERE user_id = '<uuid>';
```

---

## Troubleshooting

### Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| `object APIResponse can't be used in 'await'` | Using `await` with sync Supabase client | Remove `await` from `.execute()` calls |
| `unsupported operand type(s) for \|` | Python 3.9 type annotation | Add `from __future__ import annotations` and use `Union[]` |
| `prompt is too long` | Context/history too large | Reduce history messages or context size |
| `OpenAIError: api_key must be set` | Missing OPENAI_API_KEY | Set `OPENAI_API_KEY` env var |
| `Unknown primitive: <object>` | Wrong function signature order | Check `execute_primitive(auth, name, input)` order |

### Module Reload (Live Testing)

When testing code changes without restarting:

```python
import importlib
import services.primitives.registry
importlib.reload(services.primitives.registry)
from services.primitives.registry import execute_primitive
```

---

## See Also

- [database/ACCESS.md](../database/ACCESS.md) — Connection strings and passwords
- [development/SETUP.md](../development/SETUP.md) — Full development setup
- [architecture/primitives.md](../architecture/primitives.md) — Primitives specification
