# Carry-over: how are agent sessions managed, and can we do per-agent chat?

Paste this whole file into a new session.

---

## The question

Today `/chat` is the engine surface: starting a conversation picks an ENGINE, and
who replies is the **cast** (`conversation_members`), joined from inside a
conversation. `/agents` shows BEINGS and (since ADR-612) lets a member scope
each one's connectors.

**What I want to understand and decide:** how are conversations/sessions
actually managed today, and could we offer a conventional chat-platform
experience — ChatGPT/Claude-style — **per agent**? A member picks Editor, sees
their history with Editor, starts a new conversation with Editor, and can be
redirected into a past one. Is that reachable from the current model, or does it
fight something ratified?

Do NOT start building. I want the audit and the shape decision first.

---

## Established facts (measured 2026-08-27 — verify, don't re-derive blindly)

- `chat_sessions` = 124 rows. **111 carry a lane binding** in
  `context_metadata.lane` (the JSONB holds `name`, `app`, `artifact_path`,
  `derive_recipe`, `model`). There is NO `lane_meta` column — it is inside
  `context_metadata`.
- `conversation_members` = 197 rows, **79 with `member_kind='agent'`** (the
  module is `services/conversation_cast.py`; the TABLE is
  `conversation_members` — the names differ, which cost me a wrong query).
  Per-agent conversation counts are real: designer 39, editor 31, supervisor 1,
  plus rows for **dissolved beings** (`scout`, `lisa`, `sonnet`, `keeper`).
- `lane_meta["agent"]` is **RETIRED**. A lane's being is DERIVED at read time by
  `routes/lanes.py::_lane_agent` (app → `resident_for_app`, else recipe, else a
  legacy pre-ADR-597 stamp). So "lanes for Editor" is not a DB predicate.
- `session_messages.metadata.agent_slug` IS stamped on assistant turns
  (`routes/lanes.py`), but only post-addressing rows; unbackfilled.
- `GET /lanes?include_bound=1` already returns every lane the member is in, each
  with `participants[]` and a derived `agent`. **There is no `?agent=` filter
  and no `/agents` router** (the pre-ADR-596 one was deleted whole, commit
  `083d25d`, with NO successor verb by design).
- **Not answerable, and this matters**: per-being authorship or spend. Agent
  writes attribute `member:{id} via {model}` (ADR-411 D4 — the agent acts AS the
  member), and editor/designer/supervisor all run `claude-sonnet-5`, so they are
  indistinguishable in `workspace_file_versions` and in `execution_events`
  (`slug='lane'`, `principal_id` = the member's UUID).

## Ratified constraints this must not quietly break

- **ADR-558**: chat is the ENGINE surface; `create_lane` 422s on `agent` for an
  unbound lane. Who replies is the CAST (ADR-495), joined from inside — never
  chosen at the door. **A per-agent front door is in tension with this**, and
  that tension is the actual design question.
- **ADR-596 D1 / ADR-460 D3.a**: authority/clock/judgment live on grants,
  declarations and gates — NEVER on a being. A being's registry row is kernel
  code with an `AGENT_ROW_KEYS` whitelist.
- **ADR-602 D2**: `designer` rides ~65 cast rows; retiring a slug needs a
  measured migration. Cast rows for dissolved beings already exist and any
  per-agent listing must decide what to show for them.
- **ADR-612** (just shipped): per-being connector opt-in in `member_state`
  (`agent_connectors` key), narrowing turn reach. A desk turn reaches when the
  member scoped that being; open chat reaches by default.

## What I actually want answered

1. **How are sessions managed today, end to end?** Creation, naming, binding,
   the cast, listing, resumption. Where does each live, and what is derived vs
   stored?
2. **Is a per-agent conversation home reachable** without contradicting ADR-558's
   "chat is engines, the cast is who replies"? Or does it require amending it?
   If it requires an amendment, say so plainly — do not build around it.
3. **What would the member-facing model be?** Specifically: does picking an
   agent create a *filtered view* over one conversation space, or a *separate
   conversation space per agent*? These differ in whether one conversation can
   have two agents (which the cast currently allows).
4. **What is cheap vs expensive?** A filtered list is a client-side filter over
   an envelope we already fetch. A per-agent conversation space with its own
   new/resume flow is a bigger change. Price both.

## Method I expect

- Measure production before asserting; execute the query, don't infer it.
- Baseline every gate before AND after, counting FAILING ASSERTIONS not exit
  codes.
- Any new gate must be MADE TO FAIL against pre-fix code before it counts, and a
  gate that passes must be shown to be observing the thing it claims (I have had
  three assertions this week pass while observing nothing).
- Concurrent lanes are common in this tree: stage by explicit path, never
  `git add -A`. If `next build` fails on a shared `.next`, inject
  `distDir: process.env.NEXT_DIST_DIR` into `next.config.js`, build to a private
  dir, then RESTORE the config and `git checkout -- web/tsconfig.json` (the
  build rewrites it).
- Read the ADR before proposing: `docs/adr/ADR-558-*`, `ADR-495`, `ADR-597`,
  `ADR-602`, `ADR-612`, plus `docs/architecture/GLOSSARY.md`.

## Deliverable

An audit + a recommended shape, with the ADR-558 tension named explicitly and
priced. Then stop and check with me before building.
