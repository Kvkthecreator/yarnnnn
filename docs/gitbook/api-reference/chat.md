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
- If your plan budget is exhausted, returns `429`.

## Get recent chat history

```text
GET /api/chat/history?limit=1
```

Response includes recent sessions and message arrays.

## List chat sessions

```text
GET /api/chat/sessions
```

Returns chat session metadata for the current user.

## List available commands

```text
GET /api/commands
```

Returns the command definitions the Thinking Partner can expose in the UI.
