# Plans

Plan limits below are aligned to current backend enforcement as of **March 4, 2026**.

## Plan comparison

| | **Free** | **Starter** | **Pro** |
|---|---|---|---|
| Price | $0 | $9/mo | $19/mo |
| Platforms available | 4 | 4 | 4 |
| Slack sources | 5 | 15 | Unlimited |
| Gmail labels | 5 | 10 | Unlimited |
| Notion pages | 10 | 25 | Unlimited |
| Calendar sources | Automatic | Automatic | Automatic |
| Active agents | 2 | 5 | Unlimited |
| Sync frequency | 1x daily | 4x daily | Hourly |
| Daily token budget | 50,000 | 250,000 | Unlimited |

## Sync cadence

| Plan | Schedule |
|---|---|
| Free | 08:00 (user timezone) |
| Starter | 00:00, 06:00, 12:00, 18:00 (user timezone) |
| Pro | Every hour |

## Notes

- Source limits are enforced per provider.
- Calendar is read from connected calendars and does not require per-resource source selection.
- Usage and next sync timestamp are available via `GET /api/user/limits`.
- Limit values may be revised over time; check the [changelog](../changelog.md) and [versioning page](../resources/versioning.md) for updates.
