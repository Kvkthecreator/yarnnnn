# Finding — `recall` returns empty because nothing is embedded (the Embed primitive isn't being invoked)

> **Date**: 2026-06-29
> **Hat**: B (evaluation finding) → recommends a Hat-A fix
> **Trigger**: every live `remember → recall/trace` round-trip across multiple sessions (2026-06-26 → 06-29) returned empty `recall`/`trace`, despite `remember` reporting `captured: true`. A Claude-side analysis hypothesized a date-resolution bug; this finding chases it to the real root with substrate receipts.
> **Scope note**: separate from the ADR-379 widget-leak work (that task is done + live-validated). This is the round-trip / `recall` value-prop, surfaced while validating it.

## TL;DR

Three hypotheses were tested and **falsified by receipts**; the fourth is the real root cause:

1. ❌ **Date-resolution bug** — both `remember` date sources (`server.py::_today_iso`, `mcp_composition.py:165`) use `datetime.now(timezone.utc)` (live clock). The 06-27 writes stamped 06-27 and the 06-29 write stamped 06-29 **in the revision chain at rest** — correct elapsed time, two sessions two days apart. No bug.
2. ❌ **`AGENT_ENABLED` gated off** — `substrate_event` wakes fired **75×** with `escalate`, the Reviewer actively writes reports/persona/calibration. Steward is on.
3. ❌ **Placement wake doesn't fire / seat doesn't run** — every test `remember` produced an `mcp-foreign-write-review` wake that ran to `success` (2–4 tool rounds, real output tokens). **8/8 succeeded**, one ~27s after the latest write. The seat wakes, reads, reasons, completes.
4. ✅ **ROOT CAUSE — embeddings are 100% unpopulated workspace-wide (642/642 `embedding IS NULL`).** `recall` ranks via `QueryKnowledge` → vector similarity → needs embeddings. With none, semantic recall matches nothing and falls back to exact lexical/path resolution, so anything not named near-exactly returns empty.

Plus a **secondary, by-design** observation: the test notes were test scaffolding (`[TEST NOTE — ADR-379 …]`), and the seat correctly invoked the derive-and-cite prompt's explicit escape hatch ("if the observation carries no understanding worth deriving yet … it is legitimate to derive nothing") — so test noise was *deliberately* not derived into `operation/memory`. That is the seat working as intended, NOT the bug. The bug is the embedding gap, which affects even substantive content.

## The mechanism (root cause)

- `_embed_workspace_file` (`services/primitives/workspace.py:30`) is **dead code** — defined, never called. Its docstring still says "scoped to `/workspace/context/` paths only (ADR-174 Phase 2)", but `context/` was retired → `operation/` by the ADR-320/321 topology cut, so even if it were called the guard would never match.
- The call site comment (`workspace.py:815`) states the intent: *"Embedding is no longer a write side-effect — it is the explicit **Embed primitive (ADR-325)**."* ADR-325 deliberately decoupled embedding from writes and made "make-AI-ready" an explicit, autonomy-gated `Embed` primitive.
- **The gap:** nothing in the `remember` → `substrate_event` wake → derive-and-cite flow (nor the report/derivation flows) ever calls `Embed`. So files accumulate unembedded; `recall`'s semantic path is dark across the whole workspace.

## Receipts (reproducible)

```sql
-- 642/642 files unembedded, workspace-wide:
select (embedding is not null) as embedded, count(*) from workspace_files group by 1;
--  f | 642

-- the seat DID wake + run on every foreign write (8/8 success):
select created_at, funnel_decision, status, slug, tool_rounds, output_tokens
from execution_events where wake_source='substrate_event' and created_at > '2026-06-27'
order by created_at desc;
--  all escalate / success / slug=mcp-foreign-write-review

-- remember writes persist with correct path + attribution + live-clock date:
select path, authored_by, created_at from workspace_file_versions
where authored_by ilike 'yarnnn:mcp%' order by created_at desc;

-- 3 derived memory files exist (06-26, substantive content) — none embedded:
select path, (embedding is not null) from workspace_files where path like '/workspace/operation/memory/%';
```

## Recommended Hat-A fix (for a dedicated session)

The decision is a product one, not just mechanical — ADR-325 made embedding *explicit* on purpose (cost + autonomy governance). So the fix must choose **where the explicit `Embed` belongs in the memory loop**, not silently re-couple it to writes. Options, in order of likely fit:

1. **Embed as the tail of derive-and-cite.** When the seat authors a derived understanding into `operation/` from a `remember`, that authoring step should call `Embed` on the derived file (it IS the make-AI-ready moment for memory the operator will recall). Keeps ADR-325's "explicit" property (the seat decides) while closing the loop. Most aligned.
2. **Embed in the `remember` raw-capture path** — likely wrong: raw inbound is a source of record, not the recall surface; embedding raw dumps re-introduces the conflation ADR-376 removed.
3. **A backfill `Embed` sweep** for the 642 existing files — needed regardless of (1) to make existing substrate recall-able, but it's remediation, not the structural fix.

Whatever lands must update `_embed_workspace_file`'s stale docstring or delete it (it's dead), and add a regression check that semantic `recall` over a freshly-derived memory actually returns it (the memory-note lesson: *a read-path test asserting "returns a bundle" passes on EMPTY — assert it FINDS what you wrote*).

## What this finding does NOT claim

- It does not claim the seat is broken (it isn't — 8/8 wakes succeeded).
- It does not claim test notes *should* have derived (they correctly didn't — scaffolding has no understanding to derive).
- It does not propose re-coupling embedding to every write (that would undo ADR-325). The fix is *where* the explicit Embed belongs in the memory loop.
