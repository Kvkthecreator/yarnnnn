# Agents API

Manage autonomous agents and their version history.

## Agent types

Current supported `agent_type` values:

- `digest`
- `brief`
- `status`
- `watch`
- `deep_research`
- `coordinator`
- `custom`

## Agent modes

Current `mode` values:

- `recurring`
- `goal`
- `reactive`
- `proactive`
- `coordinator`

## Create agent

```text
POST /api/agents
```

Example:

```json
{
  "title": "Weekly Engineering Digest",
  "agent_type": "digest",
  "mode": "recurring",
  "schedule": {
    "frequency": "weekly",
    "day": "monday",
    "time": "09:00",
    "timezone": "America/Los_Angeles"
  },
  "sources": [
    {
      "type": "integration_import",
      "provider": "slack",
      "source": "C123ABC",
      "value": "C123ABC",
      "label": "#engineering"
    }
  ],
  "agent_instructions": "Summarize decisions, blockers, and owners."
}
```

## List agents

```text
GET /api/agents
```

Optional query params:

- `status=active|paused|archived`
- `limit=<int>`

## Get agent

```text
GET /api/agents/{agent_id}
```

## Update agent

```text
PATCH /api/agents/{agent_id}
```

## Archive agent

```text
DELETE /api/agents/{agent_id}
```

## Trigger immediate run

```text
POST /api/agents/{agent_id}/run
```

Returns execution status and new version metadata when successful.

## Version endpoints

- `GET /api/agents/{agent_id}/versions`
- `GET /api/agents/{agent_id}/versions/{version_id}`
- `PATCH /api/agents/{agent_id}/versions/{version_id}`
- `POST /api/agents/{agent_id}/versions/{version_id}/enable`
- `DELETE /api/agents/{agent_id}/versions/{version_id}/dismiss`

## Source freshness endpoint

```text
GET /api/agents/{agent_id}/sources/freshness
```

Returns per-source freshness metadata for the agent.
