# Documentation Layers

## Where things live

YARNNN keeps documentation in separate layers on purpose:

| Layer | What it is |
|---|---|
| `docs/gitbook/` | These public product docs |
| `docs/ESSENCE.md` | The canonical product narrative |
| `docs/architecture/` | Canonical internal architecture — FOUNDATIONS, GLOSSARY, service model |
| `docs/adr/` | Decision records; the implementation history |
| `docs/analysis/` | Exploratory work and open questions |

Public docs may simplify. They should never contradict the canonical layer. Where these pages describe something as not-yet-running, that reflects the shipped state rather than the intended one — the goal is that a reader is never surprised.

<!-- GITBOOK_VERSIONING_START -->
## Current snapshot

| Field | Value |
|---|---|
| Last synced (UTC) | `2026-09-15 23:54:04Z` |
| Docs version | `v5.0.0-docs.20260915` |
| API version | `5.0.0` |
| Web version | `5.0.0` |
| Source commit | `b98999b` |
| Source range | `deaa24f..7dc5ae8` |
| New commits since last sync | `0` |

## Recent sync history

| Synced at (UTC) | Docs version | Commit | Range | Commits |
|---|---|---|---|---|
| `2026-09-15 23:53:25Z` | `v5.0.0-docs.20260915` | `b98999b` | `174b43d..b98999b` | `2486` |
| `2026-03-22T15:30:00Z` | `v6.0.0-docs.20260322` | `174b43d` | `147a7bc..174b43d` | `165` |
| `2026-03-17 02:18:50Z` | `v5.0.0-docs.20260317` | `147a7bc` | `45ff552..147a7bc` | `157` |
| `2026-03-04 07:32:45Z` | `v5.0.0-docs.20260304` | `45ff552` | `0c9ab5e..45ff552` | `18` |
<!-- GITBOOK_VERSIONING_END -->

## What the 8.0 rewrite changed

The docs had drifted roughly six months behind the product — they were last synced
2026-03-22 and still described a service model that no longer exists. Everything
false was replaced:

- **Freddie, the workspace steward** — the page is deleted and every reference
  removed. The steward seat is retired: judgment is a grant a member holds, and
  nothing in the workspace acts on its own initiative.
- **Studio → Slides, Docs → Text** — and Studio's outward half (posts, essays,
  landing pages) moved to **Blogger**, which is its own app with its own agent.
- **Radar** — deleted, not paused. The page that described it is gone.
- **Blogger, Images and Reach** — three shipped, Dock-pinned apps that had no
  documentation at all. They have pages now.
- **The agent roster** — Thinker, Researcher and Critic never existed as anything
  a reader could use. The live roster is Editor, Designer and Blogger, each bound
  to an app, none of them hireable.
- **Chat** — you pick an ENGINE, not a colleague. The old "you pick who, not which
  model" framing was exactly inverted.
- **Plans** — the monthly allowance is retired; "$0 for one person" and "Starter"
  are gone. Free is two people; the third is a seat; usage is pure pay-as-you-go.
- **The Dock** — five apps became eight.

The standing rule below is what this rewrite was measured against, and what the
docs had been violating: *public docs may simplify, but they must never contradict
the canonical layer.*

## Auto-sync

A helper script refreshes the changelog and this snapshot from git history:

```bash
python3 scripts/sync_gitbook.py
```

It updates the auto-generated sections only. The narrative pages are maintained by hand against the canonical docs.
