# Open items — what one session leaves the next

This file holds OPEN items only. Delete an item in the commit that closes it. Narrative
(what was found, how, the receipts) goes to the ADR, the evaluation record under
`docs/evaluations/`, or session memory — never here. The session-reorient hook warns past 120 lines.

Reset 2026-09-12: the 3,196-line journal (2026-08-18 → 09-12) was absorbed into ADRs, evaluation records and memory.

## Compose's dead brief-builders (found 2026-09-18, ADR-635 am.2 cleanup)

`services/compose/assembly.py` and `services/compose/revision.py` are re-exported
by `compose/__init__.py` and called by **nothing outside tests** —
`build_generation_brief`, `build_post_generation_manifest`,
`parse_draft_into_sections`, `classify_revision_scope`, `build_revision_brief`,
`get_prior_section_content` all have 0 non-test callers (censused). Their stale
"it will be auto-rendered" prompt strings were corrected in f9008fd rather than
deleted, because removing two live-looking compose modules is its own pass with
its own gate. The live compose path is `compose_task_output_html` →
`task_html.py` → `engine.py:compose_html` (2 route callers), untouched.
Decide: delete both modules and their re-exports, or keep with a tombstone.


## `/admin` renders a negative balance as `$-0.15`, not `-$0.15`
- `page.tsx` L455/462/465 use `${value.toFixed(2)}`, so a negative lands as `$-0.15`. Pre-existing from
  ADR-655 am.1, cosmetic (the NUMBER is right), found during the am.2 click-pass. One live row shows it
  today (`SK Personal`). Fix is an Intl.NumberFormat currency helper, not a sign swap at three sites.
- ⚠️ Local `/admin` boot needs two env vars absent from `api/.env`: `ADMIN_ALLOWED_EMAILS` (else 403)
  and `INTEGRATION_ENCRYPTION_KEY` (a Render var; `main.py` fails closed on it). The client gate also
  reads build-time `NEXT_PUBLIC_ADMIN_EMAILS`. Driving `/admin` in a browser needs a real session —
  prod serves `307 -> /auth/login?next=/admin` without one.

## Responsive gate stops at the marketing surfaces (2026-09-18)
- `api/test_library_responsive.py` rule 3 (a flex child holding a `max-w-*` block wider than a phone
  viewport must carry `min-w-0`) is scoped to `web/components/landing/` — the surfaces where the bug
  class was found (`98615c6`). The **authenticated app was not audited** for the same pattern. Owed:
  one sweep of `web/components/` beyond `landing/` + `library/`, then widen the gate's scope rather
  than copying the rule (the README says so).

## GitBook screenshots — one GitHub GC request remains
- **Ask GitHub Support to GC the orphaned objects.** `main` was force-pushed (`b17ca34` → `c574f31`,
  2026-09-18) to drop a consent screenshot carrying the operator's personal email. A fresh clone is
  clean, but commit `f576492` and blob `5e80a06c8a3cf42af9ff1e85b7ee410e427782e2` still return 200
  from the GitHub API by direct SHA — unreferenced objects survive until GitHub garbage-collects,
  which only happens on a support request. Until then a direct SHA link still serves the address.
- The publishable consent screenshot is `marketing/assets/screenshots/yarnnn-oauth-consent-claude-scrubbed.png`
  (the un-suffixed name is permanently blocked by its own tombstone — see the defect below).

## `move` and the upload door treat a tombstoned path as occupied
- Deleting `x.png` then moving or uploading onto `x.png` fails: `move` returns `destination_exists`
  and the upload door suffixes to `x-2.png`. `_move_file` in `api/services/primitives/workspace.py`
  (~L1905) selects from `workspace_files` on path with no deleted/tombstone filter, so a deleted row
  still occupies the name while `list` correctly hides it. Effect: a member cannot replace a file by
  delete-then-rewrite, and the canonical name is burned permanently. No gate covers this.

## ADR-427 ratchet is RED at HEAD — two unclassified `.content` readers
- `test_adr427_reader_classification.py` fails: `services/agent_faces/__init__.py` and
  `services/member_apps.py` read `.content` and are not in `CLASSIFICATION`; seven entries are
  stale (`routes/feed.py`, `routes/images.py`, `services/recurrence.py`, four
  `services/primitives/mirror_*.py`). Arrived with the ADR-653 work, not with ADR-623 §8 —
  confirmed by running the ratchet at `e15ae7f` with the §8 diff stashed. Classify the two,
  drop the seven.

## ADR-656 — the Supervisor app (Phases 1–2 SHIPPED 2026-09-18; memory + routing next)
- **Scope**: one app, one agent. KERNEL app (code); a member authors no app. ADR-653's
  member-authored layer is DELETED (its §13 has the census); `APP-BUILDER-UX.md` is UNSCOPED.
- **DONE**: the `supervisor` AGENTS row · `services/apps/supervisor.py` · a kernel surface row with
  **`register: "composition"`** (the FIRST tenant) · **the surface** — three declared sections
  (`needs-you` · `threads` · `note`) dispatched by kind with the honest amber miss · the app
  UNVEILED (`primary`, pinned, `/supervisor`). Click-passed: all three bands render, 19 threads with
  app·agent derived, three reading "not filed yet", and a click opens `/chat?chat.lane={id}`.
- ⭐**The sections were RE-DERIVED, not inherited.** ADR-653's `files` and `recent` are deliberately
  NOT carried — the supervisor owns no folder, and "what moved" is the timeline's job (duplicating
  it is the "glorified redirect" ADR-435 killed the last composition for). `threads` is the one new
  kind and the reason this app is not a redirect.
- **NEXT, in order**:
  1. **Memory's writer and reader** — `agents/supervisor/memory/` still has ZERO of each. RULED: it
     holds **private judgment only** (corrections, preferences, patterns), never context — the
     workspace IS the shared memory (ADR-411), so there is no store to build. Small by construction;
     ADR-624 preserved. Open: who may READ it.
  2. **Routing** — the act is *"stamp this lane with its app"* (`context_metadata.lane.app`, one
     existing field; the surface already SHOWS the gap as "not filed yet"). RULED: as the member's
     hands, inside a turn they began. An agent CANNOT open a lane (one writer behind a human JWT;
     RLS says *"AI principals are not members"*). **Propose-and-click ships BEFORE any verb.**
  3. `supervisor/DECISIONS.md` has no writer — the note band renders its honest empty until the
     supervisor (or the member) writes one. That is correct, not a gap to rush.
- ⚠️**Do not reason from live chat statistics** — the operator's own workspace; YARNNN is pre-user.
  They diagnose a defect, never demand (analysis §13.1 retracts two opposite conclusions from the
  same numbers).
- ⚠️**Another session held port 8000 during the click-pass** with lanes disabled, so the chat
  destination showed "Chat is not enabled". The navigation is verified (the URL carries the lane id)
  and the backend was driven directly instead. Check `ps` for a foreign uvicorn before blaming code.
- **Separate, still open**: (a) the CHAT layer — artifact-bound lanes are created eagerly, before
  anyone speaks; a dependency walk, not a count. (b) the UNATTENDED half — 0 live standing
  declarations, and the source predicate cannot name a workspace region.

## Genesis / the shared service client
- **`[Errno 11] Resource temporarily unavailable` on the shared HTTP/2 service client is UNFIXED** (first seen
  2026-09-12; still firing 2026-09-16). It is a transient read failure on `get_service_client()` under concurrency,
  and it lands wherever a sync auth dependency touches the client: `[MENTIONS] list failed`, `[ADR-373]
  owned-workspace list failed`, `workspace reach check failed`, and — 2026-09-16 — the ADR-465 owner-grant write.
  Every call site swallows it differently, so the SAME fault reports as a missing grant, an empty list, or a 403.
  Migration 256 removed its worst consequence (a half-minted workspace can no longer be produced by the race it
  raced with), but the transient itself remains. Owed: one decision about the shared client under concurrent
  sync dependencies — not per-site `except` arms. See `project_lane_turn_that_left_no_trace` in memory.
- **Sentry alerted on the SMALLER bug and stayed silent on the bigger one** (2026-09-16). The 2-workspace race
  paged because an unrelated transient broke a grant; the 9-workspace race on the same day raised nothing because
  every write succeeded. Genesis has no invariant probe — nothing asserts "one auto workspace per owner, and it is
  reachable" against live data on a schedule. Migration 256 enforces the first half in the DB; the second half
  (an owner-grant existence check across the fleet) is still only ever run by hand.

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
- Re-measure lane spend a week after 2026-09-08 (every number in 647/648 is pre-change) · DeepSeek funding;
  GLM via `openrouter/z-ai/glm-4.6` · Gemini's automatic cache is not explicit caching (named, unclosed).
- **ADR-654 click-pass DONE (2026-09-17)** — Designer re-pointed to `gemini/gemini-2.5-pro` on the rig
  (ws bf5b25a9); a new bound Images lane bound to it (session 24aa8b2c, `context_metadata.lane.model`),
  while all seven older lanes kept `anthropic/claude-sonnet-5`. Persistence survived a hard reload.
  The pass FOUND a defect: clearing an override 422'd (`Body(...)` reads a bare JSON `null` as a missing
  body) — fixed in `78f4dd9` and **driven on prod 01:51** (clear persisted `{}`, no 422, pane back to
  the default). The deliberate-commit chooser (`234cd83`) also driven: picking writes NOTHING (0 rows
  mid-pick), Cancel discards, Confirm writes `anthropic/claude-opus-5`, reopen re-seeds clean. Rig row
  deleted; ADR-654 is CLOSED.
- ⚠️`api/test_agent_registry.py` is RED at baseline — it hardcodes `services/apps/images/decompose.py`, deleted
  in `0b9920f`; the gate crashes at import and reports nothing. Pre-existing, untouched by ADR-654.
- ⚠️`api/test_adr412_chat_surface.py` is RED at baseline (7 failed, 1 passed at HEAD) — it reads
  `web/components/shell/chrome/ChatDrawer.tsx` and `web/components/agents/AgentContentView.tsx`, both long
  deleted, so it crashes on `FileNotFoundError` and reports nothing. Same family as the two above: a gate
  anchored to a name decays in both directions. Found while gating `dee2719`; untouched by it. Decide
  whether ADR-412's chat-surface claims still need a gate, then rewrite it against live anchors or delete it.
- **Data-heavy work has a located kernel gap (2026-09-16, `b937e2e` §11).** A 5,000-row CSV probe measured it: ADR-648's
  pagination is FINE (the lane read 100% of 287,762 chars across 3 windows); the wall is `_LANE_MAX_TOKENS = 4096` — the
  turn cannot carry the answer it read. The gap is that the agent is doing the ARITHMETIC. Owed: a decision on a
  projection verb — **but NOT owed as work**: demand-pull (ADR-337 D6) refuses it on one synthetic probe against 5 CSVs
  totalling <2KB, and 8 primitives are already dead-on-arrival in the matrix. The PROBE is the artifact to keep; build
  the verb when a real member or app is blocked. Deliberately NOT fixed by raising the token budget.
  `api/scripts/operator/probe_data_heavy_lane.py` scores 0/3 by design — an honest failure now, not a silent one.
- **The sharper open question is edge types** (ADR-653 §10 item 12): `derived_from` already makes the substrate a graph
  over files, with one WITNESSED edge kind. Whether asserted edges join it is unsettled. ⚠️Watch for MANY-TO-MANY —
  one-to-many is a folder; many-to-many is where paths stop being enough, and that is the signal, not file size.
- ⚠️A data-heavy app cannot be the FIRST app shipped — a CRM is what a non-technical member expects an app to be, and
  it is the one shape that fails until the above lands (§11.6).

## Standing work / apps
- Carried since 2026-09-04: `projection.ts`'s second CSV parser · a Files door for declaring
  standing work · blogger's first real standing declaration (compose-only) · the `/images` export click-pass.
- IMAGES tagline promises live rendering "on the canvas" — true via Designer in the lane, not a
  button; whether it wants an explicit affordance is a product call.

## Workspace binding (ADR-548 D9/D10, found 2026-09-13)
- **One personal file sits in the wrong workspace** — re-probed 2026-09-15: of the three, `operation/ideas.md` is
  still `active` in `yarnnn workspace` (d5b9029b) where it was owner-resolved by the pre-`8b4977d` path;
  `operation/personal-notes.md` and `operation/test.md` are now `archived` and need no repair. The code defect is
  fixed; MOVING the remaining file is a data repair and the operator's call — confirm intent, then move via
  `write_revision` at the correct binding (`SK Personal`, 9dc80079), never an UPDATE of `workspace_id` (the
  revision chain is the record).
- CLOSED 2026-09-15 (`b4f251f`): the multi-ownership exposure is 2 accounts, BOTH the operator's own — no
  stranger affected — and the "AT MOST one" docstring is corrected. All 19 live workspaces carry an active
  owner grant (0 orphans). Ownership is deliberately not capped.

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
  rig. (`testacct`'s stale "owns nothing" note was corrected 2026-09-16.) Top-level peer
  folders have no member door (D5 sends a folder from nowhere to Documents); if one is needed, `NewFolderModal` grows a destination picker — never a second fallback.

## Billing (found 2026-08-20 / 09-02, unverified)
- The undelivered-top-up banner has never rendered in a browser: mint a top-up checkout, abandon it, wait out
  `TOPUP_DELIVERY_GRACE_MINUTES`, load Billing. Sweep LS order history for orders the stale `api.ep-0.com` hook swallowed before 2026-09-02.

## Email (ADR-650, 2026-09-12)
- **Paste the six auth templates** — see the Beta readiness section below for the one-command helper. SMTP is on
  Resend (ACCESS.md); Supabase only reads templates from the dashboard.
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

## GitBook (2026-09-17)

- **The OpenAPI block needs a dashboard data source.** `{% openapi %}` parses and renders
  NOTHING on the docs space — driven live at `51154b4`: 0 raw syntax leaked, 0 spec-only
  strings, and the stub link inside the block swallowed too. Registering the spec with
  `openapi:` in `docs/gitbook/.gitbook.yaml` is not sufficient; add
  `https://yarnnn.com/openapi.json` as an OpenAPI data source in the GitBook dashboard,
  then re-apply the spike (reverted in `51154b4`, restore with `git show 92accbc`). Until
  then the hand-written parameter tables in `api-reference/mcp-tools.md` stand — gated
  against the enforced scope table, so they cannot drift silently.
  A dashboard fact, same class as the Git Sync mapping before `5c790be`.

## Gates red at baseline — each needs its own ruling
The authoritative list is `docs/evaluations/2026-09-13-gate-census.md` — 42 pytest + 28 script rows remain after the
Studio-era cluster (26 gates) was ruled 2026-09-13/14; the still-open shapes (ADR-209 live phases, retired-model subjects, the settings pane move) are named there. A ruling lowers the list in the same commit.

## A send that left no trace (found 2026-09-15) — two of three ruled, see `b4f251f`
- **(b) STILL OPEN.** `streamLaneTurn` has no deadline before the first byte (ADR-651 D3 bounds `request()`
  and the idle window only), so the edge's cutoff becomes "The lane turn failed" with no cause and the
  attachment chips are dropped. Needs its own ruling.
- **(a) mitigated, not cured.** The reach lookup retries once on a transient transport fault, which recovers
  the dropped socket. THE CURE — `get_user_client` is a sync dependency sharing one `lru_cache`d HTTP/2 pool
  across every threadpool worker — is a client-lifecycle change and still owes its own ADR.

## Beta readiness (pass 2026-09-15, remainder closed 2026-09-16)
The core loop is PROVEN on prod: a chat send wrote `operation/beta-readiness-probe.md` in ws `bf5b25a9`,
revision `41708c79`, attributed `member:67c5c637 via anthropic/claude-sonnet-5`, ~13s send→durable write,
with the ADR-651 bounded wait visible live. Record: `docs/evaluations/2026-09-15-beta-readiness-click-pass.md`.

CLOSED 09-15: the reach 503, the sign-up success on the error channel, the 7× composition fetch, password
reset (it did not exist), the undeliverable-address 500.
CLOSED 09-16: the GitBook docs rewrite (`04ff98c` — ~15 false files, Freddie deleted, Studio→Slides,
Docs→Text, Blogger/Images/Reach written from scratch, gated by `api/test_gitbook_docs_current.py`); the
sign-up CTA (`b98999b`); the xAI privacy omission + the last "Studio" on /how-it-works (`2e0f4cb`); the
`api/scripts/` invocation bug (`b53f5ce`, gated); both prod probe accounts torn down and verified gone
(17 accounts, 19 workspaces, 0 orphan grants).

**THE ONE ITEM LEFT — paste the six auth templates.** `python3 api/scripts/print_auth_templates.py` prints
all six in dashboard order with subjects; paste into Authentication → Emails → Templates. It needs a
dashboard click or a Supabase PAT (the Management API is the only programmatic route and this repo holds
only the service key, which governs data, not project config). Reset Password is newly load-bearing —
before 2026-09-15 there was no reset door, so that mail could never fire.

Also still open, lower stakes: `/terms` is 1,625 chars, dated 2026-01-28 (vs `/privacy` 2026-07-08),
mentions no refund/billing/subscription while the site sells $20/seat, and carries no nav or footer;
`/invest` repeats the pre-ADR-490 pricing model.

NOT covered by the pass, each its own run: a real cold sign-up driven end-to-end through the browser (the
API half is probed by `probe_cold_user_genesis.py`; the UI half is not), N>2 members, a paid tier, any
connected platform, a real phone, and the Slides/Blogger/Images authoring surfaces beyond load.

## Waiting (ADR-651, 2026-09-13)
- ~~Prod click-pass of a live turn~~ — DONE 2026-09-15 (see Beta readiness above): "is working…" rendered for
  ~8s on a real lane turn and resolved into an attributed write. The `: ping` heartbeat and the killed-connection
  "The reply stopped arriving" arm were NOT driven and are still owed.
- `framer-motion` is a dead dependency (imported nowhere) — removing it needs a lockfile write; `pnpm` is not on
  this machine's PATH and Vercel installs frozen.

## Copy (VOICE-AND-TONE, 2026-09-15)
- The plain-language pass swept the chrome, Chat, Reach, Notifications, the apps and the served prose;
  the owed remainder is the numbered list in `docs/design/VOICE-AND-TONE.md` §6 (marketing lines, the
  Files "revision" → "version" rename, two dead launcher rows, one duplicate tool-label table). The
  guard's Phase-3 allowlist is the meter.

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

## The operator console (ADR-655)
- **The console has had no browser click-pass.** `next build` is exit 0 and the gate is 23/23 with live
  credentials (migration 257 applied 2026-09-17), and the routes have been driven directly — but nobody has
  clicked `/admin` in a browser. Unverified against real rendering: the comp toggle's optimistic revert, the
  stale-heartbeat colour, and the Engines bar widths.