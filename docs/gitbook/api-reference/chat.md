# Chat API

Chat endpoints power the Thinking Partner experience.

## Send message

```text
POST /api/chat
```

Request body:

```json
{
  "message": "What changed in #engineering this week?",
  "surface_context": {
    "type": "idle"
  }
}
```

Notes:

- Response is streamed as `text/event-stream`.
- The API reuses/creates a chat session automatically.
- If daily token budget is exceeded for your tier, returns `429`.

## Get recent chat history

```text
GET /api/chat/history?limit=1
```

Response includes recent sessions and message arrays.

## List available skills

```text
GET /api/skills
```

Returns skill metadata used by the assistant.
