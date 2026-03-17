# Versioning & Sync

This page tracks GitBook sync metadata and the role of the public docs layer.

## Documentation layers

YARNNN uses separate documentation layers on purpose:

- `docs/gitbook/` -> public product and developer docs
- `docs/architecture/` -> canonical internal architecture
- `docs/adr/` -> decision records and implementation history
- `docs/analysis/` -> exploratory analysis and unresolved questions

Public docs may simplify. They should not contradict canonical docs.

<!-- GITBOOK_VERSIONING_START -->
## Current snapshot

| Field | Value |
|---|---|
| Last synced (UTC) | `2026-03-04 07:33:57Z` |
| Docs version | `v5.0.0-docs.20260304` |
| API version | `5.0.0` |
| Web version | `5.0.0` |
| Source commit | `45ff552` |
| Source range | `c190893..45ff552` |
| New commits since last sync | `0` |

## Recent sync history

| Synced at (UTC) | Docs version | Commit | Range | Commits |
|---|---|---|---|---|
| `2026-03-04 07:32:45Z` | `v5.0.0-docs.20260304` | `45ff552` | `0c9ab5e..45ff552` | `18` |
<!-- GITBOOK_VERSIONING_END -->

## How auto-sync works

1. Reads recent git commits.
2. Builds a docs sync version from API/Web versions + date.
3. Updates GitBook changelog auto section.
4. Updates this versioning snapshot.
5. Persists sync state to `docs/gitbook/.sync-state.json`.

## Run manually

```bash
python3 scripts/sync_gitbook.py
```
