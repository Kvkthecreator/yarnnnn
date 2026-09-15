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

## A send that left no trace (found 2026-09-15) — two of three ruled, see `b4f251f`
- **(b) STILL OPEN.** `streamLaneTurn` has no deadline before the first byte (ADR-651 D3 bounds `request()`
  and the idle window only), so the edge's cutoff becomes "The lane turn failed" with no cause and the
  attachment chips are dropped. Needs its own ruling.
- **(a) mitigated, not cured.** The reach lookup retries once on a transient transport fault, which recovers
  the dropped socket. THE CURE — `get_user_client` is a sync dependency sharing one `lru_cache`d HTTP/2 pool
  across every threadpool worker — is a client-lifecycle change and still owes its own ADR.

## Beta readiness (pass run 2026-09-15) — what is OWED before strangers arrive
The core loop is PROVEN on prod: a chat send wrote `operation/beta-readiness-probe.md` in ws `bf5b25a9`,
revision `41708c79`, attributed `member:67c5c637 via anthropic/claude-sonnet-5`, ~13s send→durable write,
with the ADR-651 bounded wait visible live. Fixed this session: the reach 503, the sign-up success riding the
error channel, the 7× composition fetch, password reset (it did not exist), the undeliverable-address 500.
Still owed, none of them code in this repo:
- **Paste the six auth templates** into the Supabase dashboard (already listed under Email below). Highest
  priority of the remainder: every beta user's first contact is a Supabase-sent email.
- **Docs contradict `/pricing` on the free tier** — the marketing page says $0 for TWO people and paid from the
  3rd; `yarnnn.gitbook.io/docs/plans-and-billing/plans` says $0 for ONE, paid at the second, calls the plan
  "Starter" not "Team", and promises a $15/mo included pool the pricing page does not. Both are footer-linked.
  A buyer who checks the docs finds a different, costlier model. GitBook edit, not a repo change.
- **Every conversion CTA lands on Sign IN** ("Connect your AI", "Start free", "Bring the team", "Open yarnnn"
  → `/auth/login`, which defaults to sign-in mode). A new visitor must find the small "Sign up" toggle.
  `/auth/login` accepts no mode param today — adding one is a small repo change, not yet made.
- **Docs still document Freddie** ("the workspace steward", 1 of 4 entries under HOW IT WORKS, with Autonomy
  and Budget dials) — retired by ADR-632. Also app-name drift: docs say Docs/Studio, the product says
  Text/Slides, and `/how-it-works` uses both spellings on one page.
- `/terms` is 1,625 chars, dated 2026-01-28 (vs `/privacy` 2026-07-08), mentions no refund/billing/subscription
  while the site sells $20/seat, and carries no nav or footer. `/invest` repeats the old pricing model;
  `/engines` lists xAI while `/privacy` §4 — billed as the complete third-party list — omits it.
- Two prod probe accounts to tear down: `beta-cold-01@yarnnn.com` (3cd3cf45) and
  `probe-nodomain@thisdomaindoesnotexist-zzz.com` (9af29121), created 2026-09-15 while isolating the signup
  500. Use the product's purge path, not a hand-written DELETE.
- NOT covered by this pass, and each is its own run: a real cold sign-up driven end-to-end through the
  browser (the API half is probed by `probe_cold_user_genesis.py`; the UI half is not), N>2 members, a paid
  tier, any connected platform, a real phone, and the Slides/Blogger/Images authoring surfaces beyond load.

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
