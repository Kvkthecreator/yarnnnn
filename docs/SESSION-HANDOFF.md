# Open items — what one session leaves the next

This file holds OPEN items only. Delete an item in the commit that closes it. Narrative
(what was found, how, the receipts) goes to the ADR, the evaluation record under
`docs/evaluations/`, or session memory — never here. The session-reorient hook warns past 120 lines.

Reset 2026-09-12: the 3,196-line journal (2026-08-18 → 09-12) was absorbed into ADRs, evaluation records and memory.

## Reach / outbound (ADR-642 · 645 · 628)
- **§7 — workspace identity for unattended reach**: a standing declaration is correctly refused a member credential,
  so unattended work has no outbound reach. Successor: a workspace-owned bot token, additive, never adoption
  (ADR-645 D1 closed adoption and mirroring). Drive the N>1 member case first — "Read by" only becomes
  load-bearing at two members, and that case has never been looked at.
- One real Slack send to a channel the operator names (their click) · the remote-binding ADR (a file that knows its
  remote; two tenants now) · ADR-635 distribution (registry publish, plugin-directory submission, the attach click-pass).
- WordPress D8 read-back (`read_post` behind the seam + a canary); phase (b), the narrow non-agent publish identity
  `system:publish-wordpress`, begins only on phase (a) receipts — never a general headless auth.

## Context budget / engines (ADR-647 · 648)
- Re-measure lane spend a week after 2026-09-08 (every number in 647/648 is pre-change) · no door to SET the engine
  preference; DeepSeek funding; GLM via `openrouter/z-ai/glm-4.6` · browser click-pass of a truncated read (an agent
  hitting the bound and continuing with `offset`) · Gemini's automatic cache is not explicit caching (named, unclosed).

## Standing work / apps
- Carried since 2026-09-04: `projection.ts`'s second CSV parser · a Files door for declaring
  standing work · blogger's first real standing declaration (compose-only) · the `/images` export click-pass.
- IMAGES tagline promises live rendering "on the canvas" — true via Designer in the lane, not a
  button; whether it wants an explicit affordance is a product call.

## Workspace binding (ADR-548 D9/D10, found 2026-09-13)
- **Three personal files sit in the wrong workspace with no copy in the right one** — written bound to `SK Personal`
  (9dc80079) but owner-resolved into `yarnnn workspace` (d5b9029b) by the pre-`8b4977d` path: `operation/ideas.md`,
  `operation/personal-notes.md`, `operation/test.md`. The code defect is fixed; MOVING them is a data repair and the
  operator's call — confirm intent, then move via `write_revision` at the correct binding, never an UPDATE of
  `workspace_id` (the revision chain is the record).
- Exposed population: exactly **2 accounts** own more than one live workspace. `resolve_owner_workspace_id`'s
  docstring still claims "AT MOST one" (no unique constraint on `workspaces.owner_id`) — correct the docstring or
  cap ownership, not both.

## Genesis (ADR-414 D4 · 465; found 2026-09-12)
- No live workspace has the governance dials, so `initialize_workspace` (`api/services/workspace_init.py`) is
  effectively dead the way the state route was; `budget.py` degrades to kernel defaults, so a bare row is usable.
  Decide: delete it or re-reach it. `GET /api/workspace/state`'s remaining payload (program lifecycle,
  substrate_status) has no live reader except `/settings` behind a swallowed catch.

## Evaluations (2026-09-13)
- **No current thesis suite**: the steward suite retired 2026-09-13; the runner's measured turn is `send_message`.
  Cutting the next one is a Hat-B decision with a cost line — candidates: the register (ADR-638), the skills index
  (ADR-630). `DECLARED_CURRENT` in `test_eval_suite_gate.py` + the README registry go together; the `scenarios/`
  corpus still spells steward-era setup — a corpus pass belongs to whoever cuts that suite.

## Files (ADR-649, 2026-09-12)
- Rig `anr-scout@yarnnn.com` (ws `4023cb7b`) holds `operation/first-folder/` from the click-pass; trash it for a cold
  rig. `testacct` owns a workspace — its "owns nothing" note in `browser_login_link.py` is stale. Top-level peer
  folders have no member door (D5 sends a folder from nowhere to Documents); if one is needed, `NewFolderModal` grows a destination picker — never a second fallback.

## Billing (found 2026-08-20 / 09-02, unverified)
- The undelivered-top-up banner has never rendered in a browser: mint a top-up checkout, abandon it, wait out
  `TOPUP_DELIVERY_GRACE_MINUTES`, load Billing. Sweep LS order history for orders the stale `api.ep-0.com` hook swallowed before 2026-09-02.

## Email (ADR-650, 2026-09-12)
- **Paste the six auth templates** from `supabase/templates/auth/` into Authentication → Emails → Templates (subjects
  in that folder's README); SMTP is on Resend (ACCESS.md) — Supabase only reads templates from the dashboard.
- **Security-change mail** (next tenants of the `account` kind, one hook each): a new AI connection on the OAuth code
  path (`_ensure_foreign_llm_grant`), a credential connected/removed on Reach, BYOK set or cleared.
- `routes/webhooks.py` reconciles Resend delivery events only against `export_log` (0 rows); a bounce on a notification
  email is logged and dropped. Store the message id on the transport row to close it.

## Mobile typing (2026-09-13)
- Driven at 390x844 in a real browser: the three-tab bar renders Document | Properties | Chat, one tap each. NOT driven
  on a device: the list continuation and the soft-keyboard Enter — both proven headlessly (13/13 + 15/15), so the
  remaining risk is the SOFT keyboard itself (`enterKeyHint`; whether a phone IME reports the flag this rule reads).
  Owed: one pass on an actual phone.
- The local API wedged mid-click-pass (`/health` stopped answering), so the document never mounted CodeMirror —
  undiagnosed; know it before the next local click-pass.
- `web/scripts/gates/adr519_container_reorder.mjs` crashes (`SyntaxError: Unexpected identifier 'from'`) and reports
  nothing — pre-existing (worktree at 80b9874~1), the silent-crash class of 43babc0, not in the census.

## Gates red at baseline — each needs its own ruling
The authoritative list is `docs/evaluations/2026-09-13-gate-census.md` — 42 pytest + 28 script rows remain after the
Studio-era cluster (26 gates) was ruled 2026-09-13/14; the still-open shapes (ADR-209 live phases, retired-model subjects, the settings pane move) are named there. A ruling lowers the list in the same commit.

## A send that left no trace (found 2026-09-15, ws d5b9029b lane 506b7bbf)
- The operator's Text-bound send with two image attachments (2026-09-13 15:53Z) reached NO handler: no access
  line, no `chat_sessions` read, no error, 0 messages — while both uploads succeeded and the identical send ran
  green on the rig (lane 5dd54228, `tools=5 artifacts=1`). Three defects sit behind the generic message:
  (a) `get_user_client` is a sync dependency on the `lru_cache`d shared service client, whose HTTP/2 socket
  throws `httpx.ReadError: [Errno 11]` under concurrent requests (7 bursts, 5 instances, 09-12→13; a 500 on
  `GET /api/lanes` 04:51Z, three 403s 16:23:49Z) — a thread stuck there is invisible; (b) `streamLaneTurn` has no
  deadline before the first byte (ADR-651 D3 bounds `request()` and the idle window only), so the edge's cutoff
  becomes "The lane turn failed" with no cause and the attachment chips are dropped; (c) `principal_reaches_workspace`
  returns False on ANY exception, so a socket error reads as "No active grant". Each needs its own ruling.

## Waiting (ADR-651, 2026-09-13)
- Prod click-pass once both deploys are live: a lane turn shows "Lisa is working… 12s"; the network tab shows
  `: ping` every 15s during a silence; a killed connection ends in "The reply stopped arriving" with the composer
  text restored. The primitive was driven in Chrome (light, dark, reduced motion); the live path was not.
- `framer-motion` is a dead dependency (imported nowhere) — removing it needs a lockfile write; `pnpm` is not on
  this machine's PATH and Vercel installs frozen.

## Cleanup owed since ADR-632
- `api/scripts/operator/` shadows the stdlib `operator` module for any script run BY PATH from `api/scripts/`
  (`python3 scripts/x.py`; the next `import re` dies). Reproduced 2026-09-13; affects `backfill_embeddings.py`,
  `purge_user_data.py`, `refresh_connector_directory.py` (their docstrings say run by path); `python3 -m scripts.x`
  works. Rename the package or fix the three docstrings — one decision.
- Strip the steward env vars from Render (`AGENT_ENABLED`, `YARNNN_MODEL_{SHAPE}`, `YARNNN_ROUNDS_{SHAPE}`,
  `STEWARD_SURFACE_SLUGS`): needs `render login` or an API key — the MCP tool sets but cannot list or delete. (The
  `wake_queue` drop landed as migration 254; `tasks` is ADR-639's live drain index and stays.) ADR-596 D3(d) still owed.
- **Retired vocabulary, frozen by `api/test_retired_vocabulary_ratchet.py`** (per-file ceilings, only lowered): canon
  230 lines / 27 files (ADR-LEDGER 48 — historical; FOUNDATIONS 37, GLOSSARY 37, primitives-matrix 13); code 265
  lines / 74 modules (`judgment_log.py` 17, `review_policy.py` 15, `orchestration.py` 12, `workspace.py` 11). A file
  is a session each, ADR-632/603/596 as the spec; lower its ceiling in the same commit.
- ADR-632 §3, second half — the perception/trading primitives (`TrackRegime` · `TrackUniverse` · `TrackWebSources` ·
  `SyncPlatformState`) keep a DECLARED reach via a capture declaration's `@primitive:` directive
  (`services/capture/lane.py`). Audited 2026-09-13: zero prod rows contain `@primitive:` at all; deleting them
  removes a CAPABILITY (web-source watch, regime/universe tracking), not plumbing — the operator's call, asked
  2026-09-14. (The entity half was deleted 2026-09-13.)
- `.claude/agents/alpha-operator.md` was deleted 2026-09-12 (it instructed retired Reviewer auto-approval,
  `ManageRecurrence`, `_recurring.yaml`); if alpha rituals are wanted, rebuild it against the live model (`docs/alpha/`, `api/scripts/alpha_ops/`).
