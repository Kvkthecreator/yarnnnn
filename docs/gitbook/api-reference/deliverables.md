# Deliverables API

Manage autonomous deliverables and their version history.

## Deliverable types

Current supported `deliverable_type` values:

- `digest`
- `brief`
- `status`
- `watch`
- `deep_research`
- `coordinator`
- `custom`

## Deliverable modes

Current `mode` values:

- `recurring`
- `goal`
- `reactive`
- `proactive`
- `coordinator`

## Create deliverable

```text
POST /api/deliverables
```

Example:

```json
{
  "title": "Weekly Engineering Digest",
  "deliverable_type": "digest",
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
  "deliverable_instructions": "Summarize decisions, blockers, and owners."
}
```

## List deliverables

```text
GET /api/deliverables
```

Optional query params:

- `status=active|paused|archived`
- `limit=<int>`

## Get deliverable

```text
GET /api/deliverables/{deliverable_id}
```

## Update deliverable

```text
PATCH /api/deliverables/{deliverable_id}
```

## Archive deliverable

```text
DELETE /api/deliverables/{deliverable_id}
```

## Trigger immediate run

```text
POST /api/deliverables/{deliverable_id}/run
```

Returns execution status and new version metadata when successful.

## Version endpoints

- `GET /api/deliverables/{deliverable_id}/versions`
- `GET /api/deliverables/{deliverable_id}/versions/{version_id}`
- `PATCH /api/deliverables/{deliverable_id}/versions/{version_id}`
- `POST /api/deliverables/{deliverable_id}/versions/{version_id}/enable`
- `DELETE /api/deliverables/{deliverable_id}/versions/{version_id}/dismiss`

## Source freshness endpoint

```text
GET /api/deliverables/{deliverable_id}/sources/freshness
```

Returns per-source freshness metadata for the deliverable.
