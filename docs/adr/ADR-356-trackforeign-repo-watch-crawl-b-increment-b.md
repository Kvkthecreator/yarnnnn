# ADR-356 — TrackForeign + the Repository Watch (ADR-335 Crawl-B Increment B)

**Status**: Implemented (2026-06-22)
**Dimensional classification**: **Substrate** (Axiom 1 §8 — the perception field) + **Trigger** (Axiom 4 — a mechanical standing watch)
**Implements**: ADR-335 D4 (the MCP transport client) + D5 (watch binding) — the **demand-pulled Crawl-B** stage, triggered by the named trigger "alpha-author post-330 deepening" (ADR-335 §237). ADR-335 Crawl-B Increment A (the metered executor `read_foreign_tool`) was already shipped; this is Increment B (the watch executor + the first binding).
**Preserves**: ADR-335 every anti-goal (no connector catalog, no perception manager, distilled-not-raw, transports-as-peripherals), ADR-336 (`TrackWebSources` — the web sibling; this is the MCP sibling), ADR-291 (one cost ledger — every foreign read is a `mode='mechanical'` `execution_events` row via `read_foreign_tool`), ADR-355 (the agent authors — this gives a repo-subject author workspace the perception to author *from*)
**Driving evidence**: the 2026-06-22 author validation (`docs/evaluations/2026-06-22-author-the-agent-authors-VALIDATION.md`) — the agent would author about the repo (ADR-355) but couldn't *perceive* it; the repo was structurally outside its perception field. This closes that gap.

---

## 1. Problem statement — the agent could author about the repo but not perceive it

ADR-355 established that the agent authors (full autonomy, full accountability). But the author validation found the next floor: a YARNNN-about-YARNNN author workspace's *subject is this repo*, and the agent correctly refused to author from sources it couldn't verify (`docs/adr/ADR-354.md` lives in git, not the agent's workspace substrate). The alpha-author bundle's only source transport was `TrackWebSources` (RSS/Atom). There was **no transport that turns repo files into attributed observations** — a perception-field gap.

The operator's challenge — *"don't we already have the infra?"* — was correct. Most of it existed:
- `mcp_client.py` (transport-pure MCP client, ADR-335 D4).
- `read_foreign_tool` (the metered mechanical executor, Crawl-B Increment A — the §282 metering precondition already resolved: every foreign read records to `execution_events`).
- The Crawl-A watch representation (`substrate_abi.watches`, the D3 observation contract, `platform_connections.watch_id` + `attestation_grade`).
- The GitHub MCP bind, proven (2026-06-18 receipt).

**Empirical check (2026-06-22):** the GitHub MCP server (`https://api.githubcopilot.com/mcp/`) exposes `get_file_contents` + `search_code` + `list_commits` among 44 tools (verified via `mcp_client.list_tools`). Arbitrary repo file reads — exactly what's needed — are available.

The gap was the **last mile**: no watch primitive called `read_foreign_tool`, and no binding wired the GitHub MCP server to a workspace as a watch.

## 2. Decisions

**D1 — `TrackForeign`: the MCP-transport standing-watch executor.** `api/services/primitives/track_foreign.py::handle_track_foreign` — the MCP sibling of `TrackWebSources` (web) and `TrackUniverse` (Alpaca head driver). Mechanical, deterministic, dispatcher-only (HANDLERS), never in an LLM tool surface. Directive: `@primitive: TrackForeign(declaration=…, distills_to=…, tool=get_file_contents)`. It reads a declaration yaml (`{server, repo, sources: [{id, path, attestation}]}`), resolves the watch-bound MCP connection, calls `read_foreign_tool(tool, {owner, repo, path})` per declared path, and distills each into a bounded excerpt (`_MAX_FILE_CHARS=8000`) in the `_repo_signal.yaml` per the ADR-335 D3 observation contract (`source_ref` + `attestation` + `observed_at` + excerpt). Per-source failure isolates (absence/error is perceivable). Program-agnostic — paths arrive as directive kwargs (ADR-224 boundary).

**D2 — The watch binding resolves from a watch-bound `platform_connections` row.** `_resolve_binding` reads the active row for the declared `server` key with `watch_id` set (NULL = capability binding per ADR-207; set = watch binding per ADR-335 D5). `server_url` from `metadata`, token decrypted via `TokenManager`. A foreign watch must not borrow a bare capability connection's auth — the watch/capability boundary (D5). `attestation_grade=platform` for the first-party GitHub MCP server.

**D3 — The alpha-author bundle declares the repository watch.** A second `substrate_abi.watches` entry (`repo-sources`, shape `repo_file_read`, transport `mcp`) + a `track-repo` mechanical recurrence (`@primitive: TrackForeign`) + a `_repo_sources.yaml` declaration (ships EMPTY — `repo: ""`, `sources: []` — a repo-subject workspace declares its repo; others leave it a no-op). Distinct `distills_to` (`_repo_signal.yaml`) so it doesn't collide with the web watch's `_watch_signal.yaml`.

**D4 — `mcp_client` surfaces embedded-resource content (transport fix).** GitHub MCP `get_file_contents` returns the file BODY in an embedded `resource` block (`TextResourceContents.text`), while the `text` block carries only a status line (`"successfully downloaded text file (SHA: …)"`). `mcp_client.call_tool` previously `str()`-truncated non-text blocks into `raw_blocks`, dropping the content. Now it extracts `resource`/`embedded_resource` `.text` into `text_parts` so any foreign read surfaces real content — singular fix at the transport layer, benefits every caller. (Verified: excerpt went from 81 chars [status line] → 8067 chars [status + real ADR markdown].)

**D5 — The generic program-envelope renderer (closes the pre-ADR-336 envelope gap).** A bundle-declared `reviewer_wake_envelope` key was loaded into the context dict by `reviewer_envelope.py` but never *rendered* into the wake message unless `_build_user_message` had a bespoke `ctx.get(key)` render site. So `watch_signal` (ADR-336) AND `repo_signal` landed in the dict but never reached the agent — a pre-existing gap. Fix: `reviewer_envelope.py` records `_program_envelope_keys`; `_build_user_message` adds a generic renderer that emits any program-declared key with no bespoke site under its own header (skipping the bespoke trader keys). Zero per-key kernel edits for future bundle envelope keys — the bundle-declares-its-envelope design (ADR-281 D2) now actually reaches the agent.

## 3. Validation (end-to-end, substrate receipts)

Workspace yarnnn-author (`0b7a852d`), binding staged (watch_id `1a6f62cf`, GitHub MCP, encrypted gh token, `attestation_grade=platform`), `_repo_sources.yaml` declaring `Kvkthecreator/yarnnnn` + ADR-354/355/validation paths:

1. **Perceive** — `track-repo` (`handle_track_foreign`) read all 3 declared files via GitHub MCP `get_file_contents`: `items_processed: 3`, 0 errors, `_repo_signal.yaml` written with real content (8067 chars/file). Metered: 3 `foreign-read:repo_sources` rows in `execution_events` (`mode='mechanical'`, success).
2. **Author** — `compose-piece` fired (exec_event `6a912c26`): the agent read `_repo_signal.yaml` from the wake envelope (D5) and **authored a 6,696-char essay** (`content.md`) in the declared voice (claim-first, receipt-backed), citing the actual ADRs it read — emitted as a `WriteFile` proposal (pending under `manual` witness; would auto-apply under `autonomous` per ADR-345). Standing_intent records the authoring act.

The full loop closes: **git repo → perception field (TrackForeign/MCP) → wake envelope → the agent authors with verifiable citations → proposes (witness-gated).**

## 4. What this is NOT

- **Not** a connector catalog or a new transport family — `mcp_client` is the one MCP transport; this is its first watch binding (ADR-335 D4).
- **Not** raw mirroring — distilled + bounded (8000 chars/file, source_ref retained for citation), per ADR-153.
- **Not** a new cost ledger — reuses `execution_events` via `read_foreign_tool` (ADR-291).
- **Not** workspace-level watch declaration — the watch is program-declared (alpha-author MANIFEST), per ADR-335 §259. The operator fills in the repo + paths; the program declares the watch shape.
- **Not** auto-apply under manual — the authored `content.md` is a pending WriteFile proposal (the witness dial, ADR-345). Under `autonomous` it applies subconsciously.

## 5. Render-service parity

`mcp` is already in `api/requirements.txt` (`mcp>=1.0.0`, Python 3.11 on the deployed API + Scheduler). `track_foreign` imports `read_foreign_tool`/`mcp_client` lazily (inside the handler), so the registry imports cleanly even where `mcp` is absent (local 3.9), and the API service does not crash on startup. The binding reuses `platform_connections` + `INTEGRATION_ENCRYPTION_KEY` — no new secret, no new service, no new env var.

## 6. Files

- `api/services/primitives/track_foreign.py` (new — D1/D2)
- `api/services/primitives/registry.py` (HANDLERS registration)
- `api/integrations/core/mcp_client.py` (D4 — embedded-resource extraction)
- `api/services/reviewer_envelope.py` + `api/agents/reviewer_agent.py` (D5 — generic program-envelope renderer)
- `docs/programs/alpha-author/reference-workspace/_recurrences.yaml` (track-repo recurrence)
- `docs/programs/alpha-author/reference-workspace/operation/authored/_repo_sources.yaml` (new — D3 declaration)
- `docs/programs/alpha-author/MANIFEST.yaml` (repo-sources watch + repo_signal envelope key)
- `api/prompts/CHANGELOG.md` — `[2026.06.22.3]`
- Evaluation: `docs/evaluations/2026-06-22-author-the-agent-authors-VALIDATION.md` (the gap → this close)
