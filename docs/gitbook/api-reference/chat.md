# Chat API

The Chat API lets you send messages to YARNNN's AI assistant programmatically. Responses are streamed in real time.

## Send a message

```
POST /chat
```

### Request

```json
{
  "message": "What was discussed in #engineering this week?",
  "session_id": "optional-session-id"
}
```

| Field | Required | Description |
|---|---|---|
| `message` | Yes | Your message to the AI assistant |
| `session_id` | No | Continue an existing conversation. Omit to start a new one. |

### Response

Responses are streamed in real time. The final event includes the session ID for continuing the conversation.

## Get conversation history

```
GET /chat/history?session_id=<session-id>
```

Returns the full message history for a conversation session.

## Sessions

- Each conversation is a **session** with its own history
- Sessions persist across page reloads
- Start a new session by omitting `session_id`, or continue an existing one by including it
