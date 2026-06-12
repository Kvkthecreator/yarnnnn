# ADR-339: Working-Tree Perception Economics — Recursive Metadata Listing, Exact-Search Legibility, Batching as Capability

**Status**: Implemented (2026-06-12)
**Evidence**: `docs/analysis/wake-round-economics-audit-2026-06-12.md` (round-by-round receipts for `execution_events` `90a59d88` — the housekeeping-genesis wake)
**Extends**: ADR-168 (file-layer naming), ADR-209 Phase 3 (authored-substrate read filters), ADR-235 Option A (scopes), ADR-337 (working-tree verbs)
**Amends**: ADR-337 D4 (SearchFiles exact contract), ADR-337 D7 (mechanical-sensing trigger sharpened)
**Preserves**: ADR-303 (round budgets unchanged — D4 below), ADR-305 (no dead substrate), FOUNDATIONS Axiom 1

## Context

The first organic exercise of the ADR-337 verbs (housekeeping-genesis eval,
2026-06-12) passed its judgment core but exhausted its 20-round budget after
only two substrate actions. The round-economics audit reconstructed all 20
rounds from Render logs and found the budget was consumed by the perception
contract, not by the work:

- **7/20 rounds** were directory drill-down forced by `ListFiles`' one-level,
  names-only projection — the handler fetched the **full subtree** from the DB
  on every call, then discarded everything but one level of names before the
  model saw it. The tool description taught the walk as the canonical pattern.
- **3/20 rounds** were `SearchFiles(match='exact')` calls passing multi-word
  phrases ("conflict backup merge stale empty") that match only as literal
  substrings — all returned a **silent zero**, while 3 live conflict-backup
  files sat with "conflict" in their paths. Silent zero-yield reads as
  "nothing exists."
- A 0-byte file — the litter class the wake was hunting — was invisible in
  listings (no size field), costing a confirmation `ReadFile` per suspect.
- Emission was strictly serial (20 rounds = 20 tool calls); nothing documented
  that independent calls batch in one turn.

Counterfactual floor under a correct contract: ~9–12 rounds for the full task
including the cells the budget cut off. Axiom 1 + ADR-209 promise that
"current state + how it got here" is cheap; the perception primitives were
not delivering on it.

## Decisions

### D1 — `ListFiles` returns the subtree with metadata (the `git status` shape)

`handle_list_files` returns the **full recursive subtree** under `path` in one
call. Each entry: `path` (relative, directly usable as the `path` argument of
`ReadFile`/`EditFile`/`DeleteFile`/`MoveFile` in the same scope), `bytes`
(content size — 0-byte litter visible without a read), `updated_at`,
`authored_by` (head-revision author, via the `head_version_id` embed).

- Backed by a new `content_bytes` generated column on `workspace_files`
  (migration 185, `GENERATED ALWAYS AS (octet_length(content)) STORED`).
- Result capped at 500 entries with an **explicit** `truncated: true` +
  message (no silent caps).
- The ADR-209 Phase 3 filters (`authored_by`/`since`/`until`) now apply to the
  **head revision** — the documented "most-recent revision" semantics. (The
  prior implementation matched ANY revision in the window; that drift dies.)
- The one-level names-only projection is **deleted** in both scopes (Singular
  Implementation). `AgentWorkspace.list` is untouched (internal callers).
- Tool description rewritten: the drill-down walk is explicitly proscribed;
  `ListFiles(scope='workspace')` with no path is named as the working-tree
  view.

### D2 — `SearchFiles(match='exact')` zero-yield legibility

The exact-mode result now carries `semantics: "case-insensitive literal
substring over content and path"`, and a zero-yield result carries an explicit
message: no matches for the LITERAL substring; multi-word queries match only
as exact phrases; hunt terms one call per term (batchable) or use semantic
mode. The tool description gains the same warning. Multi-term OR semantics is
deferred (demand-pull).

### D3 — Batching documented as capability, not pressure

One line each in the `ReadFile` description and the exact-mode guidance:
independent calls may be issued together in a single turn. This is capability
documentation (the dispatch loop has always executed every `tool_use` in a
response within one round) — explicitly NOT the round-counter/urgency nudge
class that ADR-303's population audit deleted.

### D4 — Round budgets unchanged (rejected alternative)

20 rounds was sufficient for the audited task under this contract. Raising
budgets would have papered over the perception defect at population-wide cost.
ADR-303's cost-ceiling framing stands.

### D5 — ADR-337 D7 mechanical mirror stays deferred, with a sharper trigger

A recursive metadata listing **is** the working-tree mirror, served live and
pull-shaped — no new writer, no staleness window, no dead substrate (ADR-305).
The D7 mechanical-sensing layer ships only if **push-shaped** anomaly wakes
(a wake *triggered by* a 0-byte or topology anomaly) are ever wanted.
Envelope pre-loading of tree state is likewise rejected: addressed wakes are
generic; one pull round beats taxing every envelope.

## Regression guard

D1–D3 touch no judgment prompts, no verdict path, no budgets. **Canary
caveat**: fewer tool-call rounds means less tool JSON in `output_tokens` —
the judgment-wake baseline (~3,000–7,000) shifts downward post-deploy.
Re-baseline before reading a drop as collapse; judge by judgment content
(`judgment_log` reasoning depth, verdict synthesis) for the first week.

## Key files

- `supabase/migrations/185_adr339_content_bytes.sql` (new)
- `api/services/primitives/workspace.py` — `_list_tree` (new), `handle_list_files`
  (rewritten), `_exact_search` (echo added), `LIST_FILES_TOOL` / `SEARCH_FILES_TOOL`
  / `READ_FILE_TOOL` descriptions
- `api/test_adr339_perception_economics.py` (new gate)
- `api/test_adr209_phase3.py` (ListFiles assertion updated to entry-dict shape)
- `docs/architecture/primitives-matrix.md` (ListFiles + SearchFiles rows)
- `docs/analysis/wake-round-economics-audit-2026-06-12.md` (evidence)
- `api/prompts/CHANGELOG.md` `[2026.06.12.1]`
