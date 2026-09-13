# Open items — what one session leaves the next

This file holds OPEN items only. Delete an item in the commit that closes it. Narrative
(what was found, how, the receipts) goes to the ADR, the evaluation record under
`docs/evaluations/`, or session memory — never here. The session-reorient hook warns past 120 lines.

Reset 2026-09-12: the 3,196-line journal (Parts A–Z5, 2026-08-18 → 09-12) was absorbed. Every arc
lives in its ADR, its evaluation record, and memory. Only the debt below survived.

## Reach / outbound (ADR-642 · 645 · 628)
- **§7 — workspace identity for unattended reach.** A standing declaration is correctly refused a
  member credential, so unattended work has no outbound reach. The successor is a workspace-owned
  bot token, additive, never adoption (ADR-645 D1 closed adoption and mirroring). Drive the N>1
  member case first: two principals each holding their own connections — "Read by" only becomes
  load-bearing at two members, and that case has never been looked at.
- One real Slack send to a channel the operator names (their click).
- The remote-binding ADR: a file that knows its remote (two tenants now).
- WordPress D8 read-back (`read_post` behind the seam + a canary). Phase (b), the narrow non-agent
  publish identity `system:publish-wordpress`, begins only on phase (a) receipts — never a general
  headless auth.
- ADR-635 distribution: registry publish, plugin-directory submission, the attach click-pass.

## Context budget / engines (ADR-647 · 648)
- Re-measure lane spend a week after 2026-09-08 — every number in 647/648 is pre-change.
- No door to SET the engine preference; DeepSeek funding; GLM via `openrouter/z-ai/glm-4.6`.
- Browser click-pass of a truncated read: an agent hitting the bound and continuing with `offset`.
- Gemini's automatic cache is not equivalent to explicit caching (named, unclosed).

## Standing work / apps
- Carried since 2026-09-04: `projection.ts`'s second CSV parser · a Files door for declaring
  standing work · blogger's first real standing declaration (compose-only) · the `/images` export click-pass.
- IMAGES tagline promises live rendering "on the canvas" — true via Designer in the lane, not a
  button; whether it wants an explicit affordance is a product call.
- `test_adr472_images.py` is 24/27 at baseline: it pins ADR-488's hidden state, reversed by
  ADR-629 D3. Re-pin to the beta state or retire — a decision, not a cleanup.

## Workspace binding (ADR-548 D9/D10, found 2026-09-13)
- **Three files sit in the wrong workspace and have no copy in the right one** — written while the session
  was bound to `SK Personal` (9dc80079) but owner-resolved into `yarnnn workspace` (d5b9029b) by the
  pre-`8b4977d` write path: `/workspace/operation/ideas.md`, `/workspace/operation/personal-notes.md`,
  `/workspace/operation/test.md`. All three are personal content. The code defect is fixed; MOVING them is a
  data repair and the operator's call — confirm intent before touching, and move via `write_revision` at the
  correct binding rather than an UPDATE of `workspace_id` (the revision chain is the record).
- Exposed population is exactly **2 accounts** — the only principals owning more than one live workspace.
  `resolve_owner_workspace_id`'s docstring still claims a user owns "AT MOST one"; that has never been true
  (no unique constraint on `workspaces.owner_id`). Correct the docstring or cap ownership, but not both.

## Genesis (ADR-414 D4 · 465; found 2026-09-12)
- No live workspace on prod has the governance dials, so `initialize_workspace` in
  `api/services/workspace_init.py` is effectively dead the way the state route was; `budget.py` degrades
  to kernel defaults, so a bare row is usable. Decide: delete it or re-reach it.
- Genesis no longer needs `GET /api/workspace/state`; its remaining payload (program lifecycle,
  substrate_status) has no live reader except `/settings` behind a swallowed catch.

## Evaluations (2026-09-13)
- **No current thesis suite**: the steward suite retired 2026-09-13; the runner's
  measured turn is now `send_message` (a lane turn). Cutting the next one is a Hat-B decision with a cost
  line — candidates: the register (ADR-638), the skills index (ADR-630). `DECLARED_CURRENT` in
  `test_eval_suite_gate.py` + the README registry go together. The `scenarios/` corpus still spells
  steward-era setup; a corpus pass belongs to whoever cuts that suite.

## Files (ADR-649, 2026-09-12)
- Rig `anr-scout@yarnnn.com` (ws `4023cb7b`) now holds `operation/first-folder/` from the click-pass; trash it
  if a cold rig is wanted. `testacct` owns a workspace too — its "owns nothing" note in
  `browser_login_link.py` is stale.
- Top-level peer folders have no member door any more (D5 sends a folder from nowhere to Documents); if one
  is ever needed, `NewFolderModal` grows a destination picker — never a second fallback.
- OPEN, operator-reported 2026-09-13: **delete on the Files surface opens the file in Text**. The trash
  succeeds; the navigation after it is spurious. NOT the portal-unmount re-target — that was diagnosed,
  driven in Chrome, and FALSIFIED (removing an element mid-click leaves the original target; the browser
  does not re-dispatch). Leading suspect: `handleFileClick` in `web/app/(authenticated)/files/page.tsx`
  opens on `(e?.detail ?? 0) >= 2`, the UA multi-click counter, which no element appearing or disappearing
  between two clicks at one point resets — and the confirm button sits dead-centre over the listing
  (measured). Needs a real pointer or CDP `Input.dispatchMouseEvent` with fixed x/y and rising `clickCount`;
  it cannot be synthesized from JS. The modal hardening in `5c3b143` may MASK the symptom without fixing
  the cause — verify against that commit's parent.

## Billing (found 2026-08-20 / 09-02, unverified)
- The undelivered-top-up banner has never rendered in a browser. To drive it: mint a top-up
  checkout, abandon it, wait out `TOPUP_DELIVERY_GRACE_MINUTES`, load Billing. Sweep LS order
  history for orders the stale `api.ep-0.com` hook swallowed before 2026-09-02.

## Email (ADR-650, 2026-09-12)
- **Paste the six auth templates** from `supabase/templates/auth/` into Authentication → Emails →
  Templates (subjects in that folder's README). SMTP is on Resend and recorded in ACCESS.md; the templates
  are rendered and gated but Supabase only reads them from the dashboard.
- **Security-change mail** (the next tenants of the `account` kind, one hook each): a new AI connection
  on the OAuth code path (`_ensure_foreign_llm_grant`), a credential connected/removed on Reach, BYOK set
  or cleared.
- `routes/webhooks.py` reconciles Resend delivery events only against `export_log` (0 rows); a bounce on a
  notification email is logged and dropped. Store the message id on the transport row to close it.

## Gates red at baseline — each needs its own ruling, none touched
`test_adr224_kernel_boundary` (5 red: the alpha-trader bundle's task-type templates) ·
`test_adr299_kernel_universal_capability` (1 red: `test_handler_refuses_llm_supplied_addressee_fields`) ·
`test_adr353_composio_isolation` (1 red: the `_FakeQuery` fixture has no `.limit`) ·
`test_adr614_cast_follows_the_registration` (3 red: cast seeding + persisted engine) ·
`test_adr346` / `test_adr349` (retire or re-anchor on ADR-603) ·
`test_adr404_member_invites` (1 red: greps the literal "Only the workspace owner can manage invites" in
`routes/workspace.py`, which dropped it on 2026-07-31 in `5223750` — a stale literal, found 2026-09-12) ·
`test_adr386_member_lifecycle` (1 red: `test_provider_id_resolves_via_registry` expects bare "Claude" to
resolve to None; ADR-373 D2.a made it resolve to `claude.ai` by design — the test pins the pre-D2.a rule)) ·
`test_adr571_text_app` (115/279: node/sucrase shell-outs fail in this environment) · `test_adr242` (2/6) ·
`test_adr445` (1/14) · `test_resend_webhooks` (collection error) · `test_adr427` ratchet ·
`test_adr322_entity_pruning` (5/9: pins a `services.primitives.search` module and an ENTITY_TYPES set that
no longer exist) — all identical at a clean HEAD worktree on 2026-09-12. `test_adr388_files_surface` was
re-anchored the same day (14/14) and leaves this list.

## Cleanup owed since ADR-632
- `api/scripts/operator/` shadows the stdlib `operator` module for any script run BY PATH from
  `api/scripts/` (`python3 scripts/x.py` puts `scripts/` first on `sys.path`; the next `import re` dies).
  Reproduced 2026-09-13; affects `backfill_embeddings.py`, `purge_user_data.py`,
  `refresh_connector_directory.py` (whose docstrings say to run them by path). `python3 -m scripts.x`
  works. Rename the package or fix the three docstrings — one decision.
- Strip the steward env vars from Render; drop the `wake_queue` and `tasks` tables; ADR-596 D3(d).
- **Retired vocabulary, frozen by `api/test_retired_vocabulary_ratchet.py`** (per-file ceilings, only ever
  lowered): canon 230 lines across 27 files (ADR-LEDGER 48 — historical by nature; FOUNDATIONS 37, GLOSSARY 37,
  primitives-matrix 13) and code 273 lines across 75 modules (`judgment_log.py` 17, `review_policy.py` 15,
  `orchestration.py` 12, `workspace.py` 11). A file is a session each, ADR-632/603/596 as the spec; lower its
  ceiling in the same commit.
- ADR-632 §3: the entity primitives (`LookupEntity`/`EditEntity`/`ListEntities`/`ManageDomains`) and the
  trading primitives keep handlers nothing in the live frame reaches — each owes a caller audit, then
  deletion or a declared reach.
- `.claude/agents/alpha-operator.md` was deleted 2026-09-12: it instructed Reviewer auto-approval,
  `ManageRecurrence` and `_recurring.yaml`, all retired. If alpha rituals are still wanted, rebuild
  the agent against the live model (`docs/alpha/`, `api/scripts/alpha_ops/`).
