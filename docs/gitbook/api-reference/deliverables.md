# Deliverables API

Create, manage, and trigger deliverables programmatically.

## List your deliverables

```
GET /api/deliverables
```

Returns all deliverables for your account.

## Create a deliverable

```
POST /api/deliverables
```

### Request

```json
{
  "title": "Weekly Engineering Digest",
  "deliverable_type": "digest",
  "sources": [
    {
      "platform": "slack",
      "resource_id": "C123ABC",
      "resource_name": "#engineering"
    }
  ],
  "schedule": {
    "frequency": "weekly",
    "day": "monday",
    "time": "09:00",
    "timezone": "Asia/Singapore"
  }
}
```

## Get deliverable details

```
GET /api/deliverables/:id
```

Returns the deliverable configuration and its recent versions.

## Update a deliverable

```
PATCH /api/deliverables/:id
```

Update the title, sources, schedule, or status.

## Archive a deliverable

```
DELETE /api/deliverables/:id
```

Archives the deliverable. It stops running, but version history is preserved.

## Run a deliverable now

```
POST /api/deliverables/:id/execute
```

Triggers an immediate run, producing a new version. Useful for testing or on-demand generation.
