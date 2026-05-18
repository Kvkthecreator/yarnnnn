# ADR-259: Feed Surface — Multi-Actor Operations Timeline (Renames Chat Surface)

> **⚠ Rendering grammar arc closed by [ADR-289](ADR-289-feed-and-conversation-surfaces.md) (2026-05-18)**: this ADR renamed the surface; ADR-289 split the rendering grammar between FeedTimeline (typed-event rows on /feed) and ConversationDrawer / ConversationPanel (bubble grammar on right-panel mounts + /feed drawer). The vocabulary rename established here is preserved; ADR-289 finishes the structural arc.

**Status**: Implemented 2026-05-08
**Renames**: "chat surface" → "feed surface" as the canonical operator-facing concept
**Supersedes vocabulary in**: ADR-167 (list/detail surfaces), ADR-214 (agents page consolidation), ADR-215 (surface contracts), ADR-219 (invocation and narrative), ADR-251 (system agent + reviewer first-class), ADR-258 (Reviewer as personified chat-mode operator → now "Reviewer as personified feed-mode operator"). Banners added to historical ADRs noting the rename.
**Preserves**: All architectural decisions in the renamed ADRs. Only the surface vocabulary changes; layer model, primitive matrix, three-party narrative, autonomy semantics, and authored substrate all remain intact.

---

## Why this rename

The architecture has been building a **multi-actor, asynchronous, continuously-running operations timeline** since at least ADR-205 (chat-first triggering) and accelerating through ADR-219 (invocation and narrative), ADR-247 (three-party narrative model), ADR-256 (unified Reviewer invocation), and ADR-258 (Reviewer as personified operator). Every recent ADR pushed the surface further from request-response chat and toward an operator's-cockpit feed.

The vocabulary stayed at "chat surface." That mismatch is observable in the past day's debugging churn:

- **The silent-Reviewer bug** (commit `1dea115`) — `loadScopedHistory()` had a once-per-page-load guard. Correct for chat (load history on mount, stream events on top). Wrong for a feed where every event-driven reload needs to refresh.
- **The IDENTITY.md fetch loop** (commit `d61c60b`) — per-component `useReviewerPersona()` fetch. Acceptable for chat (one bubble shape). Catastrophic for a feed where every message row is a participant card that mounts the persona hook.
- **`weight=routine` System Agent rendering** (commit `3bbc30b`) — System Agent narrations rendered as dim mono one-liners. Correct for chat (system messages are background log). Wrong for a feed where System Agent IS a participant.
- **`stream_start` placeholder** (commit `f9ff6f9`) — designed for "assistant types in real time" UX. Wrong for the Reviewer's tool-use loop (discrete events, not streaming tokens).
- **Reviewer prompt deferring to "ask the operator"** (commits `6123f8d`, `a8b71a1`) — chat training data says assistants ask clarifying questions when uncertain. The Reviewer is an autonomous principal in a feed, not an assistant in a chat.

Each was an Option A patch on a chat-frame surface. Cumulative cost is real. Pre-users is the right time to commit to the correct frame.

---

## Decision

### D1 — Operator-facing surface concept is "Feed"

The operator's primary view is **the feed** — a chronological, multi-actor, continuously-updating timeline of everything that happens in the workspace. Operator messages are one event class among many. The feed updates whether the operator is watching or not.

Vocabulary across canon docs, UI labels, and component names converges on "feed":
- "chat surface" → "feed surface"
- "the chat" → "the feed"
- "chat layer" → "feed layer" (where it's the user-facing surface; see D2 for what stays)
- Tab label "Chat" → "Feed"
- URL `/chat` → `/feed` (with permanent redirect from `/chat`)

### D2 — `chat` permission mode survives as runtime characteristic

The primitive registry's `chat` vs `headless` permission modes describe **runtime characteristics**, not surfaces. `chat` mode means: synchronous-ish, full-tool surface, operator-may-be-present, low-latency. `headless` means: background, curated tools, no live operator.

These names stay. They describe the *shape of the LLM call*, not where it appears. A Reviewer invocation in `chat` mode might land on the feed surface, but the mode names what kind of LLM runtime it is, not where its output goes.

Keeps the rename surgical. `CHAT_PRIMITIVES` and `chat_completion_with_tools` are unchanged.

### D3 — `chat_sessions` DB table stays

Schema rename is high-risk, low-value. The table is a session container; operator never sees its name. Aliased in docs as "feed sessions" where it appears in operator-facing prose.

### D4 — `/api/chat/*` URL prefix renames to `/api/feed/*`

Internal API consumers are us. Symmetric with `/feed` page route. One commit, one rename, no compat layer.

### D5 — Frontend operator-facing labels migrate

Tab nav label, page title, empty-state copy all switch to "Feed" vocabulary. Composer placeholder ("Type, drop a file...") stays — composer is composer regardless of surface name.

### D6 — Component / file / directory names migrate

| Before | After |
|---|---|
| `web/components/tp/ChatPanel.tsx` | `web/components/feed/FeedPanel.tsx` |
| `web/components/chat-surface/ChatSurface.tsx` | `web/components/feed-surface/FeedSurface.tsx` |
| `web/components/chat-surface/ChatFilterBar.tsx` | `web/components/feed-surface/FeedFilterBar.tsx` |
| `web/components/chat-surface/ChatEmptyState.tsx` | `web/components/feed-surface/FeedEmptyState.tsx` |
| `web/app/(authenticated)/chat/page.tsx` | `web/app/(authenticated)/feed/page.tsx` |
| `api/routes/chat.py` | `api/routes/feed.py` |
| `web/lib/routes.ts::CHAT_ROUTE` | `FEED_ROUTE` |
| `web/lib/routes.ts::HOME_ROUTE` | points at `/feed` |
| Tab id `chat` | `feed` |

Identifier renames within files: `ChatPanel` → `FeedPanel`, `ChatSurface` → `FeedSurface`, `ChatFilterBar` → `FeedFilterBar`, `ChatEmptyState` → `FeedEmptyState`. Move `WorkspaceContextOverlay.tsx` along with the directory rename (it lives there but isn't chat-surface specific).

### D7 — Permanent redirect `/chat` → `/feed`

Any external bookmarks or copied URLs survive. Implemented via Next.js middleware redirect.

### D8 — Historical ADRs get retroactive banner

ADRs that landed in the chat-surface vocabulary era — ADR-167, ADR-214, ADR-215, ADR-219, ADR-251, ADR-258 — receive a small banner at the top noting the rename to "feed surface" per ADR-259, with their inline references to "chat surface" preserved as period vocabulary. The decisions in those ADRs are not touched; only their vocabulary header is annotated.

### D9 — Canon docs are rewritten (not just find-replaced)

`FOUNDATIONS.md`, `SERVICE-MODEL.md`, `GLOSSARY.md`, `LAYER-MAPPING.md`, `THESIS.md`, `SURFACE-CONTRACTS.md`, `primitives-matrix.md` all get their chat-surface-era references rewritten with the feed-surface framing. The Glossary gains a Feed Surface entry. The chat-surface entry is preserved as a deprecated alias with a pointer to the new entry.

---

## What does NOT change

- **`chat_sessions` DB table.** Schema-level rename out of scope.
- **`session_messages` table** — already actor-neutral.
- **`chat` permission mode** in `CHAT_PRIMITIVES` registry — runtime characteristic, not surface.
- **`chat_completion_with_tools`** Anthropic-API wrapper — internal.
- **Internal function names** like `_dispatch_reviewer_turn`, `_dispatch_execution_turn` — they live inside what's now `feed.py` but their names describe their behavior, not the surface.
- **Historical observation logs** in `docs/alpha/observations/*.md` — preserved as dated artifacts.
- **Historical ADR body content** — only a banner is added; decision text stays as-is.

---

## Implementation footprint (single commit)

- ~50 files touched
- ~8 file/directory renames
- ~150 line-edits (mostly imports + identifier swaps)
- 3 substantive doc rewrites (FOUNDATIONS section, SERVICE-MODEL section, GLOSSARY entry)
- 1 new ADR (this file)
- 6 historical ADR banners
- 1 redirect rule in Next.js middleware
- 1 CHANGELOG entry

---

## What this enables (architecturally)

Once the frame is locked in, future commits can pursue feed-shape extensions without paying chat-frame migration tax:

- **Live updates via Supabase realtime** — subscribe to `session_messages` on the workspace; new entries push to the feed regardless of who inserted them. Operator sees autonomous Reviewer activity live without refresh.
- **"Since you were away" markers** — the existing block in `working_memory.format_compact_index` already exists; could become a visual divider in the feed itself when the operator returns.
- **Multi-participant scroll position** — feed remembers where operator stopped reading.
- **Autonomous-message visual distinction** — heartbeat-Reviewer messages render with a small "auto" chip distinguishing them from operator-addressed responses.
- **Feed filters / pinning** — operator can filter feed by participant, by event class, or pin material events.

None of these require the rename to ship. But all of them get cheaper and more obvious in the feed frame, where they're not bolting on top of chat patterns.
