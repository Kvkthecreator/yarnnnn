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
- Text's create modal wrote the told-name into the path: two phantom `/workspace/Documents/` files
  exist on prod; the PATCH door runs no `HOME_ALIASES` pass.
- IMAGES tagline promises live rendering "on the canvas" — true via Designer in the lane, not a
  button; whether it wants an explicit affordance is a product call.
- `test_adr472_images.py` is 24/27 at baseline: it pins ADR-488's hidden state, reversed by
  ADR-629 D3. Re-pin to the beta state or retire — a decision, not a cleanup.

## Genesis (ADR-414 D4 · 465; found 2026-09-12)
- No live workspace on prod has the governance dials, so `initialize_workspace` in
  `api/services/workspace_init.py` is effectively dead the way the state route was; `budget.py` degrades
  to kernel defaults, so a bare row is usable. Decide: delete it or re-reach it.
- Genesis no longer needs `GET /api/workspace/state`; its remaining payload (program lifecycle,
  substrate_status) has no live reader except `/settings` behind a swallowed catch.

## Billing (found 2026-08-20 / 09-02, unverified)
- The undelivered-top-up banner has never rendered in a browser. To drive it: mint a top-up
  checkout, abandon it, wait out `TOPUP_DELIVERY_GRACE_MINUTES`, load Billing. Sweep LS order
  history for orders the stale `api.ep-0.com` hook swallowed before 2026-09-02.
- `post.html` for the ADR-627 click-pass post read 0 bytes over `GET /api/workspace/file` while the
  row held ~36KB, and carried `content_type: text/markdown` on an `.html` artifact. Not chased.

## Gates red at baseline — each needs its own ruling, none touched
`test_adr297_navigation_enactment` · `test_adr340_p2_settings_fold` · `test_adr422_files_legibility` ·
`test_eval_suite_gate` (an ADR-518 manifest missing `restore:`) ·
`test_adr614_cast_follows_the_registration` (3 red: cast seeding + persisted engine) ·
`test_adr346` / `test_adr349` (retire or re-anchor on ADR-603).

## Cleanup owed since ADR-632
- Strip the steward env vars from Render; drop the `wake_queue` and `tasks` tables; ADR-596 D3(d).
- `.claude/agents/alpha-operator.md` was deleted 2026-09-12: it instructed Reviewer auto-approval,
  `ManageRecurrence` and `_recurring.yaml`, all retired. If alpha rituals are still wanted, rebuild
  the agent against the live model (`docs/alpha/`, `api/scripts/alpha_ops/`).
