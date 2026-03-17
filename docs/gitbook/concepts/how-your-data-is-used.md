# How Your Data Is Used

YARNNN uses your data to ground responses, run agents, and improve output quality over time.

## What YARNNN reads

| Platform | What YARNNN can access |
|---|---|
| Slack | Selected channel content |
| Gmail | Selected label content |
| Notion | Selected pages and databases |
| Google Calendar | Upcoming events and schedule context |
| Documents | Files you upload directly to YARNNN |

Coverage is user-scoped and can be refined after connection.

## What YARNNN does with that data

### Grounds TP responses

When you ask a question, TP can answer from your synced work context instead of relying on generic assumptions.

### Produces agent runs

Agents use the relevant parts of your substrate to create digests, briefs, status updates, research, and other work products.

### Improves future output

YARNNN also uses:

- prior runs
- approvals and edits
- standing instructions and preferences

to improve later output quality.

## What YARNNN does not do

- it does not post, send, or edit content inside Slack, Gmail, Notion, or Calendar
- it does not share your data with other users
- it does not train external foundation models on your data
- it does not store your passwords; it stores encrypted OAuth tokens

## Retention model

YARNNN is designed to keep what proves useful and let low-value synced content expire over time.

In practice that means:

- raw synced platform content is not all treated as permanent
- outputs and feedback that become part of useful work can persist longer
- disconnecting a platform stops future sync immediately

## Your controls

You can:

- change source coverage
- disconnect integrations
- update or remove remembered preferences
- delete uploaded documents
- reset or delete account-level data through account controls

## Security

- data is encrypted in transit and at rest
- OAuth tokens are encrypted at rest
- access is scoped to the authenticated user
- platform integrations are read-only
