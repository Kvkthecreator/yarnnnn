# Wake Round-Economics Audit — the housekeeping-genesis 20/20 exhaustion was a perception-contract defect, not a budget problem

**Date**: 2026-06-12
**Subject wake**: `execution_events` `90a59d88-d100-4acc-86db-a5a183f22100` — user `0b7a852d` (yarnnn-author), slug=addressed, 2026-06-12 00:49:11 UTC, success, 20 tool rounds, 2,722 output tokens, 45,738 fresh input / 585,298 cache-read / 51,131 cache-create, $0.29, 55.3s.
**Triggering question**: the housekeeping-genesis eval (`docs/evaluations/2026-06-12-004813-yarnnn-author-housekeeping-genesis/`) PASSED its judgment core but exhausted 20/20 rounds after only two substrate actions; findings.md filed "hygiene wakes are round-hungry; watch, don't fix." Was that round count ever necessary, given FOUNDATIONS Axiom 1 + ADR-209 promise that "current state + how it got here" is cheap?
**Verdict**: **No.** The dominant cause is the `ListFiles` perception contract (one-level projection, names only, no metadata), amplified by silently zero-yielding `SearchFiles(match='exact')` phrase semantics and strictly serial tool emission. The 20-round budget (ADR-303) was sufficient for the full task — including the unreached cadence-authoring cell — under a correct contract. The eval's "watch, don't fix" is overturned by these receipts; the fix belongs at the perception-contract layer, not the budget layer.

## 1. Receipts — round-by-round reconstruction

Source: Render API logs `srv-d5sqotcr85hc73dpkqdg` 00:48:00–00:50:00 UTC (`[REVIEWER] tool=` lines + decoded Supabase REST queries), cross-checked against `execution_events.tool_rounds=20` and the loop counter semantics at `api/agents/reviewer_agent.py:1095-1096` (one increment per API call; ALL `tool_uses` in a response execute within that round).

**Serial emission is rigorous, not inferred**: 20 rounds and exactly 20 tool executions means one tool call per response, every response. Inter-call gaps of 1.2–3.5s (one API round-trip each) confirm it; batched calls would land milliseconds apart inside one round.

Pre-loop (not rounds): ADR-276 governance envelope + operating context assembled 00:48:20–22.5 — MANDATE, IDENTITY, principles, PRECEDENT, AUTONOMY, `_preferences.yaml`, `_budget.yaml`, OCCUPANT, standing_intent, three kernel mirrors (`_schedule_index`, `_recent_execution`, `_calibration`), program substrate (`_voice`, `_editorial`, `_signal` ×2, `_watch_signal.yaml`, `specs/`).

| R | time (00:4x) | tool | target | classification |
|---|---|---|---|---|
| 1 | 8:24.5 | ListFiles | `/workspace/` | novel — but returns ONE LEVEL of folder names only |
| 2 | 8:27.3 | ListFiles | `operation/` | forced drill-down |
| 3 | 8:29.0 | ListFiles | `operation/reports/` | forced drill-down |
| 4 | 8:30.1 | ListFiles | `…/weekly-corpus-review/` | forced drill-down |
| 5 | 8:31.8 | ListFiles | `…/2026-05-26/` | forced drill-down |
| 6 | 8:33.0 | ListFiles | `…/2026-05-26/sections/` | forced drill-down |
| 7 | 8:34.5 | SearchFiles(exact) | "conflict backup merge stale empty" | **zero-yield** (literal-phrase semantics) |
| 8 | 8:36.2 | ListRevisions | provenance | legit |
| 9 | 8:37.9 | ReadFile | `2026-05-26/output.md` | needed only because listings carry no size |
| 10 | 8:40.9 | SearchFiles(exact) | ".bak .conflict .old .backup" | **zero-yield** |
| 11 | 8:42.4 | ListFiles | `operation/authored/` | forced drill-down |
| 12 | 8:44.2 | ReadFile | `phase4-canary-v3…/profile.md` | batchable with R13–14 |
| 13 | 8:45.7 | ReadFile | `phase4-canary-v4…/profile.md` | batchable |
| 14 | 8:47.2 | ReadFile | `phase4-canary-v5…/profile.md` | batchable |
| 15 | 8:49.5 | ListRevisions | provenance | legit |
| 16 | 8:55.0 | SearchFiles(exact) | "status draft ready_for_review published" | **zero-yield** |
| 17 | 8:58.5 | ReadFile | `eval-anti-pattern-voice-defer/profile.md` | legit |
| 18 | 9:00.7 | ReadFile | `persona/judgment_log.md` | legit (not envelope-resident) |
| 19 | 9:08.5 | DeleteFile | `2026-05-26/output.md` | action |
| 20 | 9:11.5 | MoveFile | `eval-anti-pattern…/profile.md` → test-archive | action — budget exhausted mid-archival |

Decomposition of the 18 perception rounds: **7 tree-walking** (35% of total budget), **3 zero-yield searches** (15%), 2 provenance, 6 targeted reads (3 of them a batchable sibling trio).

## 2. The three suspects, judged against receipts

### Suspect 2 (wake-envelope / perception gap) — GUILTY, as the dominant cause, at a sharper location than hypothesized

It is not (primarily) that no mirror pre-derives working-tree state. **The working-tree perception primitive itself is `ls` when the substrate could serve `find`.** `handle_list_files` scope='workspace' (`api/services/primitives/workspace.py:1357-1405`) **fetches the full subtree from the DB on every call** (`path LIKE '{prefix}%'`, no row limit) and then *projects the result down to direct children, names only* — discarding depth, size, updated_at, and authorship before the model sees it. The tool's own description teaches the drill-down walk as the usage pattern (lines 398–400). Rounds 2–6 and 11 — six rounds, 30% of the budget — re-fetched data the backend had already retrieved in Round 1 and thrown away. The model was not inefficient; the contract forced a serial dependency chain (each level's names are only knowable after the parent call returns), making this segment *unbatchable even in principle*.

Two corollary defects compound it:

- **No size in listings.** A 0-byte file — the exact litter class this wake was hunting — is invisible in a names-only listing. R9 (ReadFile to confirm emptiness) exists only because of this. The kernel's own write-integrity work (f1ef557) made 0-byte writes a named defect class; the perception layer can't see them without a read per suspect.
- **`SearchFiles(match='exact')` treats multi-word queries as one literal substring** (`_exact_search`, `workspace.py:863`: single `content.ilike.%{phrase}%` OR `path.ilike.%{phrase}%`). The model issued grep-OR-intent queries ("conflict backup merge stale empty"); all three returned zero rows. Receipts: 3 files at `/workspace/_shared/conflict-backups/…` (3,234 / 14,679 / 13,724 bytes, lifecycle=active) sat live with "conflict" literally in their paths while the searches reported nothing. The zero-yield was **silent** — `count: 0` is indistinguishable from "no conflict backups exist" — and plausibly contributed to the conflict-backups retention decision never being reached (the model saw `_shared/` in R1 but pursued search instead of drilling, and search lied by omission). 3 wasted rounds plus a falsified negative.

### Suspect 1 (serial tool emission) — confirmed, but secondary

Zero batching across all 20 rounds. Cleanest evidence: R12–14, three sibling `profile.md` reads with no inter-dependency, emitted one per round. Nothing in the Reviewer's system prompt or tool docs tells the model independent calls may be issued together in one turn, and the dispatch loop (`reviewer_agent.py:1258`) already executes every `tool_use` in a response within one round. Cost: ~2–4 rounds. Worth a one-line capability note in tool docs; not the main story.

### Suspect 3 (redundant re-reads of envelope-resident files) — EXONERATED at the model layer

The model re-read **zero** envelope-resident files. `judgment_log.md` (R18) is not in the envelope. The `_budget.yaml` reads at :29.803 and :59.803 are a 30-second backend poller, not model rounds. Two genuine backend-layer redundancies surfaced as side findings (DB latency only, no rounds, no tokens):

- The ADR-276 envelope gather reads MANDATE 4× and IDENTITY 2× within one assembly (parallel sub-gathers each fetching it).
- The working-memory compact index was fully rebuilt twice mid-wake (00:48:26 and 00:48:56, ~30 queries each) — triggered by the streaming/narration path, not by the model.

Both are minor `asyncio.gather` hygiene items, ~no urgency.

## 3. Counterfactual floor

With a recursive, metadata-bearing listing (78 live files in this workspace ≈ one ~5K-token tool result), the same judgment work is: 1 full-tree listing (0-byte `output.md` immediately visible by size; `conflict-backups/` visible by path; canary/eval residue visible by name+authorship) + 2 provenance ListRevisions + 2–3 targeted reads (batched) + 2–4 actions + 1 Schedule + 1 ReturnVerdict ≈ **9–12 rounds**. The wake completes — *including* the cadence-authoring cell (criterion d / ADR-275 D5) that went unmeasured — inside the existing 20-round budget, with margin.

## 4. Where the fix belongs — decisions

**D1 (primary) — ListFiles returns the subtree with metadata.** Make scope='workspace' listing recursive by default (or via `recursive: true`, decided at implementation), returning per-file `path`, `bytes`, `updated_at`, and head `authored_by`. The handler already fetches the full subtree; the defect is the projection. This is `git ls-files` / `find` vs `ls`, and it is the operational delivery of Axiom 1's "current state is cheap." Update the tool description's taught examples (drop the drill-down walk as the canonical pattern). Token cost: bounded by workspace size (78 files here); a `path` filter still scopes it.

**D2 — SearchFiles(exact) legibility.** Echo the semantics in the result (`"0 matches for literal substring '…'"`) and sharpen the description: exact = single literal substring; multi-term intent needs one call per term (or batched calls per D3). Multi-term OR semantics is a demand-pull follow-up, not shipped now. The dangerous part — silent zero-yield reading as "nothing exists" — dies with the echo.

**D3 (secondary) — batching as capability documentation.** One line in the Reviewer tool-use guidance: independent reads may be issued together in a single turn. This is capability documentation (Claude is trained on parallel tool calls), NOT behavioral pressure — explicitly distinct from the round-counter nudge class ADR-303's population audit deleted (that nudged *pace and urgency*; this documents *a mechanism*). No round counters, no urgency language.

**D4 (rejected) — raising the round budget.** 20 was sufficient under a correct contract (§3). Raising it would paper over the perception defect and raise cost-per-wake population-wide. ADR-303's cost-ceiling framing stands unchanged.

**D5 (deferred, with a sharper trigger) — ADR-337 D7 mechanical working-tree mirror.** The eval is real demand evidence, but D1 satisfies it better than a mirror would: a recursive metadata listing **is** the working-tree mirror, served live, pull-shaped — no new writer, no staleness window, no dead substrate (ADR-305 discipline). D7's mechanical sensing layer now has a sharper ship trigger: it ships only when **push-shaped** anomaly detection is wanted (a wake *triggered by* a 0-byte or topology anomaly), not for pull-shaped inspection. Likewise rejected: pre-loading a tree listing into the wake envelope — addressed wakes are generic, and taxing every envelope for an occasional need loses to one pull round.

## 5. Regression guard — protect the judgment quality the eval demonstrated

D1–D3 are read-contract and documentation changes; they touch no judgment prompts, no verdict path, no budgets. Expected effect is *more* budget available for judgment, not less. **Canary caveat**: D1 will shift the output-token baseline downward (fewer tool-call rounds = less tool-JSON in output tokens). The current baseline (~3,000–7,000; collapse fingerprint <1,500) must be **re-baselined after deploy** — a post-D1 drop toward ~2,000 on read-heavy wakes is the fix working, not collapse. Judge collapse by judgment content (verdict synthesis, reasoning depth in `judgment_log`), not by the raw token band, for the first week after the contract change.

## 6. Independent pending items (closed or carried this session)

- **kvk balance refilled**: $4.61 → **$29.61 effective** (`balance_transactions` `341a1f6f-79fe-47f5-9f2c-938257a8bae2`, admin_grant +$25, workspace `d5b9029b`). The Sunday 2026-06-14 18:00 UTC weekly-performance-review proof point (f1ef557) is funded.
- **ADR-275 criterion-d (cadence authoring) — still UNMEASURED.** No yarnnn-author wake since the eval (verified: zero `execution_events` after 00:50; zero `_recurrences.yaml` revisions on 06-12). Next measurement opportunities: outcome-reconciliation 06-12 05:00 UTC (mechanical — unlikely to read standing_intent), revision-audit 06-12 22:00 UTC, weekly-corpus-review 06-14 18:00 UTC. The standing_intent P4 note from the exhausted wake is the thread the next judgment wake should pick up.

## Implementation status

**Implemented same day as ADR-339** (`docs/adr/ADR-339-working-tree-perception-economics.md`): migration 185 (`content_bytes`), `handle_list_files` rewrite (recursive + metadata, both scopes), exact-search zero-yield echo, batching capability notes, `api/prompts/CHANGELOG.md` `[2026.06.12.1]`. The eval findings.md observation 1 ("watch, don't fix") is amended to point here.
