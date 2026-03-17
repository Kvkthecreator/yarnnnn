# Agents API

Manage persistent agents, trigger runs, and inspect run history.

## Base path

```text
/api/agents
```

## Create agent

```text
POST /api/agents
```

Example request:

```json
{
  "title": "Weekly Engineering Recap",
  "skill": "digest",
  "trigger_type": "schedule",
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
  "agent_instructions": "Prioritize decisions, blockers, and owners."
}
```

Notes:

- `skill` defines what kind of work the agent does
- `trigger_type` controls whether the agent is scheduled, event-driven, or manual
- `mode` defines how it decides when to act
- `scope` is inferred server-side from the sources and configuration

## List agents

```text
GET /api/agents
```

## Get agent

```text
GET /api/agents/{agent_id}
```

## Update agent

```text
PATCH /api/agents/{agent_id}
```

Common update fields:

- `title`
- `skill`
- `mode`
- `schedule`
- `sources`
- `agent_instructions`
- `recipient_context`

## Delete agent

```text
DELETE /api/agents/{agent_id}
```

## Trigger immediate run

```text
POST /api/agents/{agent_id}/run
```

## Source freshness

```text
GET /api/agents/{agent_id}/sources/freshness
```

Returns freshness metadata for the sources attached to that agent.

## Run history

```text
GET /api/agents/{agent_id}/runs
GET /api/agents/{agent_id}/runs/{run_id}
PATCH /api/agents/{agent_id}/runs/{run_id}
```

Use these endpoints to inspect prior runs, review run content, and update run state.

## Agent-scoped chat sessions

```text
GET /api/agents/{agent_id}/sessions
```

Returns chat sessions attached to that specific agent.
