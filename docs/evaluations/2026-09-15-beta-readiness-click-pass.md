# Beta-readiness click-pass — 2026-09-15

**Question asked**: is the product ready to accept beta users?
**Verdict**: **go, with known gaps** — none of the remaining gaps is code in this repo.
**Environment**: production (`www.yarnnn.com` + `yarnnn-api.onrender.com`), HEAD `0e7a482`.
**Principals**: `kvkthecreator@yarnnn.com` (rig owner, ws `bf5b25a9`) for the driven half;
a repo-blind subagent for the stranger half. The operator's live ws `d5b9029b` was read-only.

---

## Scope of this sign-off — what it does NOT cover

Per BROWSER-CLICK-PASS-PLAYBOOK §8, the mark is a note to the next session, not a certificate.
**Not covered, each its own run:**

- **A browser-driven cold sign-up.** The API half is probed by `scripts/operator/probe_cold_user_genesis.py`;
  the UI half — a stranger creating an account and reaching first value — was NOT driven. The stranger agent
  was deliberately stopped before account creation.
- **N>2 members.** Every observation is single-principal. "Read by", the member/owner split, and the whole
  joining lifecycle are untested here.
- **A paid tier**, any **connected platform** (the rig has 0 connections), a **real phone**, and the
  **Slides / Blogger / Images authoring surfaces beyond load** (they render; nothing was composed in them).
- **The `: ping` heartbeat and the killed-connection arm** of ADR-651. The turn itself was driven; these were not.

---

## §1 The core loop — PROBED, both halves

The product's central promise, driven end to end on production.

| Half | Observation |
|---|---|
| DOM | Composer → send → `"is working…"` rendered ~8s → reply with a file chip reading `you via Claude Sonnet 5`, tool trace `read a file · wrote a file` |
| Substrate | baseline **0 rows** → `workspace_files` `5c927ec7`, path `/workspace/operation/beta-readiness-probe.md`, lifecycle `active`, content exact |
| Attribution | revision `41708c79`, `authored_by = member:67c5c637-501d-43d1-836a-a15ff32b5901 via anthropic/claude-sonnet-5`, `revision_kind = authored` |
| Binding | `workspace_id = bf5b25a9` — the session's workspace, not the owner-resolved oldest. ADR-548 D9/D10 holds on the live path. |
| Timing | send 11:48:33Z → revision 11:48:46Z = **13s** |
| Restore | asked the agent to trash it; file is now `lifecycle = archived`. Append-only, so the revision chain remains the record. |

**This also closes ADR-651's owed prod click-pass for the turn** — the bounded wait was observed live, not only in Chrome.

## §2 Surfaces driven — all 8 dock apps + 2 settings doors + Notifications

Every surface loaded, resolved out of its loading state, and rendered a real empty state or real content.
No blank pages, no stuck spinners, no console errors (the single 404 in the log was my own bad fetch).

`/desktop` · `/chat` · `/files` · `/reach` · `/agents` · `/blogger` · `/images` · `/notifications` ·
`/workspace-settings` · `/text` · `/slides`

**Route parity**: all **119** distinct `/api/...` paths the frontend calls resolve to a served route (0 dead doors).

## §3 Defects found and FIXED this session

| # | Defect | Found by | Commit |
|---|---|---|---|
| 1 | Reach check returned `False` on ANY exception, so a dropped socket read as "No active grant" | known item | `b4f251f` |
| 2 | Sign-up SUCCESS written to the `error` state, coloured by `error.includes("Check your email")` | reading the first screen | `a7387cc` |
| 3 | `/api/programs/surfaces` fetched **7×** per page load; the hook's "caches per session" was never true | driving `/desktop` | `4737c0e` |
| 4 | **No password reset existed at all** — no call, no route, anywhere | stranger | `ea6c31b` |
| 5 | `me@gmail` → HTTP 500 naming OUR mail infrastructure | stranger | `ea6c31b` |

Each carries a gate whose every assertion was falsified and restored:
`test_reach_undecidable_is_not_a_denial.py` 18/18 · `auth_notice_tone_is_declared.mjs` 6/6 ·
`compositor_surfaces_cached_once.mjs` 10/10 · `auth_first_screen_doors.mjs` 13/13.

### A correction, recorded in place

The stranger reported the signup 500 as **"email signup is broken — BLOCKER"**, reproduced 3/3. That is
**wrong as stated**, and the correction matters more than the finding:

- a real address (`beta-cold-01@yarnnn.com`) → **200**, `confirmation_sent_at` populated;
- a nonexistent but well-formed domain → **200**;
- only a bare TLD-less domain (`@notanemail`) → **500**.

Real sign-ups work. The defect is real but is FRICTION, not a blocker: it fires on a plausible typo
(`me@gmail`) and blames the vendor for it. **Method note**: the stranger could not see the code and so
could not distinguish "the product is broken" from "this input is unusual" — which is exactly why its
findings are receipted before being believed, and exactly why it is still worth running.

## §4 Method strength (playbook §7)

| Strength | Applies to |
|---|---|
| **Probed** | ALL FIVE FIXES, plus the core loop (§1), every surface in §2, and the signup 200-vs-500 discrimination. Each re-driven against its own deployed build. |
| **Verified by code + live data** | nothing remains at this tier |
| **Inferred** | nothing is claimed at this tier |

### Post-deploy re-probe (both deploys live)

Deploys land independently, so each was re-checked after its own went live — "deploy is live" is not
"every instance serves the new code".

**API** (`dep-dakj5d9srm7s73c3r650`, live 11:59:12Z) — the reach change, driven with a real JWT:

| Case | Status | Body |
|---|---|---|
| own workspace `bf5b25a9` | **200** | — |
| no-grant workspace `d5b9029b` | **403** | `No active grant into workspace d5b9029b…` |
| nonexistent workspace `00000000…` | **403** | `No active grant into workspace 00000000…` |

The third case is the one that matters: the fix did **not** convert genuine denials into 503s.

**Vercel** — the auth fixes, driven in a real browser on `www.yarnnn.com/auth/login`:

| Claim | Observation |
|---|---|
| `me@gmail` no longer 500s | notice reads *"That email address looks incomplete — check the part after the @."*; no account created |
| the error tone is DECLARED | `role="alert"`, `color: rgb(220, 38, 38)` |
| the success tone is DECLARED | reset notice `role="status"`, `color: rgb(5, 150, 105)` — green, so the tone fix does not mis-colour the success path |
| password reset exists and answers | *"If that address has an account, a reset link is on its way."* |
| the rule is stated before submit | "At least 6 characters" rendered in sign-up mode |
| the composition is fetched ONCE (#3) | a fresh cache-bypassed `/desktop` load shows exactly **one** `GET /api/programs/surfaces` (reqid 819 of 13 XHRs), down from seven |

## §5 What a beta launch still owes — none of it code in this repo

1. **Paste the six Supabase auth templates** (`supabase/templates/auth/`) into the dashboard. Highest priority:
   every beta user's first contact is a Supabase-sent email, and it is currently unbranded.
2. **Docs contradict `/pricing` on the free tier by a whole person** — marketing says $0 for TWO and paid from
   the 3rd; the docs say $0 for ONE, paid at the second, name the plan "Starter" not "Team", and promise a
   $15/mo pool the pricing page does not. Both are footer-linked. A buyer who checks finds a costlier model.
3. **Every conversion CTA lands on Sign IN** — "Connect your AI", "Start free", "Bring the team", "Open yarnnn"
   all point at `/auth/login`, which defaults to sign-in. A new visitor must find the small "Sign up" toggle.
4. **Docs still document Freddie**, retired by ADR-632, as 1 of 4 entries under HOW IT WORKS with two dials.
   Also app-name drift: docs say Docs/Studio, the product says Text/Slides; `/how-it-works` uses both.
5. `/terms` is 1,625 chars, dated 2026-01-28, mentions no refund/billing/subscription while the site sells
   $20/seat, and has no nav or footer.
6. **Tear down two prod probe accounts** created here: `beta-cold-01@yarnnn.com` (`3cd3cf45`) and
   `probe-nodomain@thisdomaindoesnotexist-zzz.com` (`9af29121`). Use the product's purge path.

## §6 Receipted negatives — things suspected and shown NOT to be happening

- **Cold-signup grant defect has not recurred**: all **19** live workspaces carry an active owner grant, 0 orphans.
- **The multi-workspace exposure reaches no stranger**: exactly 2 accounts own >1 workspace, and both are the
  operator's own. Of the 3 "stranded" files in the handoff, 2 are already `archived`; only `operation/ideas.md`
  is still active in the wrong workspace, and moving it is a data repair for the operator to authorise.
- **No second site sniffs tone from prose**: swept the whole frontend; `AuthForm` was the only one.
- **The reach fix did not turn denials into 503s**: probed live — a nonexistent workspace still answers 403.

---

**Bottom line.** The kernel and the surfaces held up under a real drive: the core loop writes attributed,
correctly-bound substrate in 13 seconds, every app opens, no door is dead. What would embarrass you in front
of strangers is the material AROUND the product — contradictory pricing, docs describing a retired feature,
and unbranded auth mail. Those are edits, not engineering.
