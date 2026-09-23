# Open items — what one session leaves the next

This file holds OPEN items only. Delete an item in the commit that closes it. Narrative
(what was found, how, the receipts) goes to the ADR, the evaluation record under
`docs/evaluations/`, or session memory — never here. The session-reorient hook warns past 120 lines.

Reset 2026-09-12: the 3,196-line journal (2026-08-18 → 09-12) was absorbed into ADRs, evaluation records and memory.

## Office formats not yet driven with APPLICATION-authored files (2026-09-23)

The production click-pass (ADR-395 am.2 §11.12) drove every format, Save-as, agent read/edit and binary
revert on GENERATED fixtures. Still owed, on production: upload one real Excel `.xlsx` (formulas, merged
cells), Word `.docx` (images, header) and PowerPoint `.pptx`, plus one real Hancom `.hwp` and `.hwpx` —
check each draws (light + dark) and its "what it says" text has no control-code junk; and open one
Save-as output in real Word / PowerPoint / Excel. Known cosmetic: a deck's metric block exports as
"42%label▲ 8%" (inline runs joined without spaces). Delete once seen.

## Vercel skip rule not yet observed skipping (2026-09-23)

`web/vercel.json` (`037f838`) skips builds unless `web/` or `content/` changed. Unverified on Vercel:
the next docs/api-only push should show "Canceled — Ignored Build Step". If it builds instead, check the
project's Root Directory is `web`. Delete this item once one skip is seen.

## A member's workspace pin does not survive the first landing — CAUSE STILL OPEN (2026-09-21)

**Driven on production** with the declared rig pair (`kvkthecreator@yarnnn.com` owner of
`bf5b25a9`, `testacct@yarnnn.com` joining). THE JOIN ITSELF IS SOUND — receipted: a fresh
`principal_grants` row `role=member / status=active / granted_by=invite:67c5c637… /
scopes=null`, and the invite flipped to `accepted` with the right principal and timestamp.
Roster, role badge, counts (1명 → 2명, AI excluded), the owner-only hint and revoke all render
correctly, in Korean.

**THE SYMPTOM**: a member holding TWO workspaces picks the other one in the switcher, lands in
its chat, and a later full page load silently puts them back in their OWN workspace —
`yarnnn.active-workspace` is `null` again. Seen on `/chat` and on `/files`.

⚠️ **CORRECTION to this entry's first version (same day).** It claimed "cleared with NO 403,
so a second undocumented path clears the pin". **That was an artifact of the instrument.** The
self-heal RETRIES the failed call without the header and returns the retry, so the devtools
network panel lists only the successful 200 — the 403 that triggered the heal is not in the
list (`lib/api/client.ts:445` — "the in-flight retry runs FIRST and its result is returned").
Verified by pinning a workspace the caller genuinely has no grant to: the pin cleared and the
page reloaded with **all 25 requests showing 200**, in a case where healing is CORRECT. So the
ADR-499 mechanism is working, and "no 403 was observed" must never again be read as "no 403
occurred" on this path.

**WHAT REMAINS UNEXPLAINED — and it is the actual bug.** During the two-account run the pin was
wiped while the member's grant WAS valid (with the pin set by hand immediately afterwards,
every rig surface rendered correctly as 멤버 and the pin then persisted). So a 403 fired against
a workspace the member could reach. Most likely a RACE between the freshly-minted grant and the
first fan-out after `setActiveWorkspace` + `window.location.assign('/chat')` — a read that
resolves before the grant is visible to it. That would also explain why it is intermittent
(one hard load of `/chat` with the pin pre-set survived intact) and why client-side navigation
(dock buttons, settings→chat→back) ALWAYS survives.

**How to finish this**: log inside `clearActiveWorkspace`/`healStaleWorkspacePin` (not the
network panel — see above), capture the endpoint and the server's detail string at the moment
of the heal, and check `get_user_client`'s grant read for a staleness/replica window right
after an invite-accept. A heal that fires against a VALID grant is the defect; the heal itself
is not.

**SEVERITY BOUND — measured, and why this is NOT release-blocking.** The pin is `null` for a
single-workspace user by design, so there is nothing to wipe and the defect is UNREACHABLE for
them. Of 22 human principals with an active grant, exactly **2 hold more than one workspace —
`kvkthecreator@gmail.com` and `seulkim88@gmail.com`, both operator-controlled**. No real
external user can reach this today. It goes live the moment a second real person holds two
grants, which onboarding any invited user who already owns a workspace produces.

A second, quieter consequence when it fires: `shellStateSuffix` (`lib/shell/
surface-preferences.ts:186-196`) keys ALL persisted shell state on the pin, so a mid-session
flip reads and writes window/dock/attention state under the wrong key. Already visible in live
localStorage — one user carries keys under both `owner:<uid>` and `<wsid>:<uid>`.

## OWED: prove the server refuses a member's governance verbs (2026-09-22)

The UI half is fixed (`b31aed3` — `governable` now reads the VIEWER's role, so a member no
longer sees narrow / spend-cap / revoke on any row). **The server half is unproven.**

Driven as `testacct` on the rig, the ⋯ menu had offered all three verbs on the member's own
row, directly beneath the card's own sentence saying only the owner can change access. The
operator packet's rule is **"hidden is not refused"** — and the direct-fetch probe was blocked
by the sandbox (it required reading the Supabase auth cookie), so whether the live server
refuses was never established.

**Before the next release, run the packet's §4 console probe** (`docs/evaluations/
OPERATOR-PACKET-settings-click-pass.md`) from a logged-in MEMBER's devtools console against:
`POST /workspace/members/{self}/narrow` widening own `write_scopes` to include `governance/`;
`POST /workspace/members/{self}/cap`; `GET /workspace/invites`. **A 200 on the first is the
2026-07-31 escalation reopened** (a member widened their own grant; receipted in
`docs/evaluations/findings/2026-07-31-member-can-widen-own-grant.md`).

`test_governance_verbs_are_owner_gated.py` is 8/8 with its new ADR-537 arm proven RED — but a
gate reads SOURCE, not the live server, which is exactly the gap this probe closes.

## Membership pass leftovers — what stays OPEN (2026-09-22)

Closed and deleted from here: the seat cap at one of two doors (`3c24354`), the un-clickable
upgrade prompt and `SeatPanel`'s never-ending spinner (`b31aed3`), the revoke dialog's
AI-shaped copy shown to humans (`b31aed3`), and the stale governance gate (`c3e626d`).

- A revoked invite page still reads "You've been invited as a member" ABOVE "This invite is
  revoked." Two true lines that contradict each other.
- The invite landing is English while the inviter's shell may be Korean — it sits outside the
  shell and resolves the locale per-account, so the joiner can see a different language from
  the person who invited them. (Correct per ADR-660 D2; the question is whether an invite
  should carry the INVITER's locale as a hint.)
- ⚠️ `browser_login_link.py`'s roster is STALE: `beta-cold-01@yarnnn.com` and
  `beta-cold-02@yarnnn.com` were annotated "COLD — unused as of 2026-09-15" but **neither auth
  user exists any more** (teardown ran; 22 users live, neither present). Annotations corrected
  in `d77821e`, but **no cold instrument exists** — re-mint one before any first-run pass.

## ADR-661/662/663 — the desktop app: what stays OPEN (2026-09-23)

**ADR-663: the desktop app IS the website in a native window.** The installer carries the host
(`src-tauri/`) + one bootstrap page; the window opens `https://www.yarnnn.com/desktop` (debug:
`localhost:3000`). The static export, the `.web.tsx` two-build split, the shell's own Supabase client
and locale chain are DELETED — a web deploy updates every desktop app. The host is the one versioned
thing: `src-tauri/Cargo.toml` (0.2.0), tag `desktop-vX.Y.Z` per handed-out build; the page sends
`X-Yarnnn-Client: desktop/X.Y.Z`; the API refuses a host below `DESKTOP_MIN_VERSION`
(`api/services/desktop_client.py`) with 426 → `DesktopUpdateNotice`. Gates `test_adr663_*` **34/34**,
`test_adr661_*` 64/64.

**OPEN:**
1. **Every 0.1.x install is retired** (the Tauri origins left CORS). Reinstall 0.2.0 on the operator's
   Mac and on any Windows tester.
2. **0.2.0 is cut and tagged** (`desktop-v0.2.0` → `5ed64e6`): Mac DMG 4.8MB (local build), Windows
   installer 2.4MB (run `35812342700`). DRIVEN on the Mac build against production: the window opened
   the live website and `/auth/login` chose `DesktopSignIn` — the Tauri bridge IS present on the
   remote page; production refuses `desktop/0.1.0` with 426 + `access-control-allow-origin`.
   NOT driven (no Accessibility permission for synthetic clicks): the button → opener from the
   remote origin, and the rest below. **Drive ADR-663 on a real build**: sign in with the one button (the
   hand-off lands in the WEBSITE's cookie session now — `refreshSession` through auth-helpers); the
   window drags by its top bar; Settings → Desktop app shows the version; offline launch shows the
   bootstrap's message. Windows: the hand-off reaches the RUNNING app (single-instance).
3. **Apple Developer ID** (operator) — the Mac build is unsigned (*"damaged"* on download); ADR-662's
   prerequisite too. Publishing a build = set its https URL in `web/lib/shell/desktop-app.ts` — and
   add that host to the opener scope in `src-tauri/capabilities/default.json`, or the in-app
   Download link opens nothing.
4. **Windows signing** — SmartScreen warns; Azure Trusted Signing eligibility for a Korean entity
   unchecked. Installer: `shell-windows.yml`, manual dispatch.
5. **Auto-update** — deferred by ADR-663 D6 (its own keypair + a hosted manifest); D3's 426 is the lever.
6. **ADR-662's browser pane is BUILT, not yet driven** (amendment 1, D14; host **0.3.0**, not cut).
   Owed, in order: (a) **cut 0.3.0** for the Mac (`scripts/release-shell.sh`) and run `shell-windows.yml`
   — the Windows target was NOT compiled (a Mac stops in `tauri-winres`); (b) **the driven trace**: in
   the 0.3.0 app, Settings → Desktop app → *Let your agent use a browser* (the HOST's dialog must
   appear), then ask a real browser job in chat; read the reply row's `metadata.receipts` back from
   `session_messages`, and watch the pane; (c) then ratify ADR-662 (Status → Accepted retires ADR-661's
   tripwire). The page's routines (`src-tauri/src/hands/page.js`) were driven in Chrome; the Rust glue
   (eval callback, navigation settle, the dialog) only compiles.
7. ⚠️ Watch: the browser and the app share one refresh-token lineage. If the app is signed out ~1h
   after signing in, suspect Supabase's reuse detection — a hypothesis, unverified.

⚠️ **Testing leaves ghosts** in Launch Services; unregister by path (the publishing doc).

**Found RED at HEAD, not from this arc** (measured on a clean worktree, left for their owners):
ADR-660's literal-copy meter reads **251 > 248**; `test_adr244_workspace_settings_surface.py`
crashes on the long-deleted `WorkspaceSection.tsx`. (The `.web` rename had also blinded seven gates
that read the old paths — adr308, adr513, adr563, auth-gate coverage, action-feedback,
workspace-binding and the voice guard; ADR-663's renames returned them to health.)

## App click-passes: Text · Chat · Slides — what stays OPEN (2026-09-22)

Three apps driven on production as a real member. Everything fixed is in the commits
(`ca4169a`, `532a3fb`, `8785490`) and the detail lives there; only the OPEN items are below.

⚠️ **Text and Chat were driven in KOREAN by accident** — the rig accounts carry
`user_metadata.locale='ko'` and the account step outranks cookie/Accept-Language, so the whole
product came up Korean unannounced. Slides was then driven deliberately in English. Set the
locale on purpose (Settings → Language, persists to the account) and say which mode a pass was
in: a locale pass and a core pass find different defect classes.

**Open — needs a RULING, not a patch:**

1. **Text's two doors disagree about non-Latin paths.** Create ASCII-folds a typed name
   through `naming.py::path_slug` (`투자자 미팅 노트` → `operation/untitled.md`, canon, made
   safe by `disambiguate`). Rename on the same file accepts `operation/투자자 미팅 노트.md`
   with no folding, stored correctly NFC (migration 259 verified live on a fresh path). The
   substrate handles Hangul fine. So either `path_slug` at creation is a constraint the product
   outgrew, or rename is the door that should fold. **Do not fix one door before deciding.**
2. **A single-agent lane is titled by its ENGINE, not its agent** — picking Editor produced a
   lane called "Claude Sonnet 5"; a two-agent lane correctly reads "Editor, Supervisor".
   ADR-558 makes the engine the member's pick and ADR-614 leads the door with colleagues, so
   titling with the engine reads as the older model.

**Open — copy, cheap:**

3. Agent DESCRIPTIONS and "last used" in the new-chat picker are English inside a Korean UI
   (the agent NAMES are identifiers and correctly literal). Same class as the add-file menu
   already recorded under ADR-395 am.1, and as `/settings` → Notifications, whose category
   names and descriptions are also English there.
4. Editor's description truncates in the picker ("Writes with you — decks and docu…") — it is
   the only one long enough to clip.
5. "New chat" stays English in the lane header until renamed.
6. With a folded path, Text's window title and Properties header read "Untitled" /
   `untitled.md` while the member's name sits in the 개요 field two lines below. The title
   should prefer the document's own name over its path stem.

⚠️ **Two non-findings, recorded so nobody re-finds them.** A Slides "clipped canvas" was a
narrow-window artifact (stage 0.71 at 1158px, 1.36 at 1600px; the slide honours its baked
992×558 and the stage is width-driven by design) — **measure a layout at two viewport widths
before calling it a bug**. And a "canvas ignores slide selection" was a transient
mid-recompose state; re-testing tracked correctly both times.

## App click-passes: Blogger · Images · Files — what stays OPEN (2026-09-22)

Driven on production **in ENGLISH, set deliberately** (Settings → Language before anything
else; the rig account does carry `locale='ko'` and comes up Korean otherwise). Fixes are in
`8e35f85`, `c5bdae2`, `8e2c3d3`, `083f7b4`, `1f918e6`, `990f08f`, `b65dde4`.

**Open — a product question this pass could not answer:**

1. **The SYNC lane path drops a multi-round preamble.** `c5bdae2` fixed the STREAMED path,
   which is the one members use — a round boundary no longer welds the plan to the report.
   `run_lane_turn` (the non-streaming sibling) keeps only the LAST round's text, so it discards
   the preamble instead of welding it. Wrong in the opposite direction and not member-visible
   today, so it was left rather than fixed blind. Decide whether the sync path should
   accumulate with the same separator, or whether dropping is correct for its callers.

**Open — not release-blocking, bounded:**

2. **The Files list crushes NAME to ~16px at 900px viewport.** Found while measuring the AUTHOR
   clip (`b65dde4`) and PRE-DATES it: at 900px the four-column template leaves Name almost
   nothing, because the `md:` breakpoint that drops the Where column fires well below the width
   at which four columns stop fitting. The fix is probably to drop Where at `lg:` rather than
   `md:`, but that is a Finder-parity judgment, not a measurement. Unclipped and correct from
   1280px up.

3. `test_adr587_handle_grammar_parity.py` — **7 pre-existing failures**, an ADR-587 D5
   path-naming arc (Properties/share-sheet/tile/row do not render the path through the shared
   CopyField; the verb-roster arm names three verbs not on the roster). Identical before and
   after `990f08f`, which added 2 green arms beside them (39 → 41 checks).

4. `test_files_selection_model.py` — 2 pre-existing failures (`5. double-click opens via the
   funnel`, `11d. Download is in the shared menu`). Identical before and after `b65dde4`.

5. `test_adr412_chat_surface.py` **crashes on collection** — it reads
   `web/components/shell/chrome/ChatDrawer.tsx`, deleted at some point. A gate that crashes
   reports nothing; it needs re-pointing or retiring.

6. `test_adr657_two_lanes.py` — 2 failures from a missing local `mcp` module (env gap, not
   product). Identical before and after this pass.

⚠️ **One non-finding, recorded so nobody re-finds it.** Navigating `/blogger` → `/images`
client-side rendered Blogger's landing under the `/images` URL on the FIRST load and Images
correctly on the second — a transient registry re-resolve, not a routing defect. **Re-test any
"it showed the wrong thing" before filing it**; this is the second pass in a row where that
rule prevented a false finding.

## The upload door is open — two owed follow-ups (ADR-395 am.1, 2026-09-21)

Shipped: the intake door drops its format allowlist (D8), a file with no projection is retained
with a legible marker instead of failing the upload (D9), `xlsx`/`pptx` join the text family and
the `docx` extractor is repaired of silent table/header loss (D10). Gate 42/42, falsified six ways.

**CLICK-PASSED 2026-09-21** (ADR §8.8): four files driven through the real door — `.xlsx` and
`.pptx` (both refused before), a table-bearing `.docx` (whose table was silently dropped before),
and an unknown `.sketch`. All landed; projections carry `derived_from`; the `.sketch` took the
marker. It found one defect no gate could: **the drop-zone caption still read "PDF · DOCX · TXT ·
MD · ZIP"** after D8 deleted the `accept` filters, and its sibling "Your agents can read these
files" had become a false promise. Both reworded in `en.json`/`ko.json`.

**THE TOPIC IS CLOSED** (2026-09-21). Inbound office formats work end to end: the door takes every
file (D8), nothing is silently dropped (D9), xlsx/pptx/docx are read correctly (D10), a member can
tell readable from not (D11), sees the extracted words (D12) and can save the file from the panel
that tells them to (D13). All driven in a browser; `python-pptx` verified on BOTH services from
their live build logs. `render.yaml`'s cron block was reconciled against the live service on the
way (no `buildCommand`, wrong schedule) — ⭐verify infra against `get_service`, never against that
file.

Deliberately NOT built, each with its reason in the ADR: round-trip editing · Google Drive (a connector question — ⚠️**ADR-131
sunset the Google tools**, read why before re-proposing) · a visual/thumbnail preview and the
sandbox behind it (§8.7 scopes it with a named trigger: a member asking twice for something that
needs code execution).

1. **The add-file menu is English inside a Korean interface** — "New Folder" / "Add Files…" are
   unlocalized while everything around them is Korean. Noticed during the click-pass; belongs to
   ADR-660's coverage, not here.

Two pre-existing defects found and fixed in passing, both unrelated to the amendment:
`test_adr621` monkeypatched `execute_primitive` at module import and never restored it, turning
three ADR-395 arms RED on run ORDER alone; and `test_resend_webhooks.py` was DEAD for 26 days —
it imported two mapper functions deleted 2026-08-26 with `agent_runs`, so it errored at COLLECTION
and its two live signature arms never ran. RE-CUT (not deleted): the mapping test has no subject,
and what replaced it — the raw event type landing on `export_log.outcome` — is asserted instead.

**Suite baseline for the next session**: 45 failed / 593 passed across the 76 collectible gates
(`for f in test_*.py; do grep -q 'sys\.exit' "$f" || echo "$f"; done`). The 45 are pre-existing —
measured identical against stashed changes. The other ~318 gates are script-shaped (`sys.exit`) and
abort pytest collection, so a whole-suite run is not possible today.

## Korean substrate: BOTH migrations applied (2026-09-21)

Migrations **259** (NFC paths) and **260** (Korean search) are **APPLIED to production** and verified
on the live object, not on the runner's exit code.

**259 — one Unicode spelling for a path.** 0 non-NFC rows in `workspace_files` and
`workspace_file_versions`; all 4 Hangul paths intact; every Hangul head matches a version-chain row;
the two files that were previously unfindable by their composed name now resolve.
⚠️ The doors that MINT a path fold to NFC (`services/naming.py::nfc` at the upload slug and at
`parse_file_reference`, plus the TS twin). **Reads are deliberately NOT normalized** — folding a read
would orphan a legacy row by its own stored spelling. Gate `test_nfc_one_unicode_spelling.py` 17/17.

**260 — search speaks Korean.** `pgroonga` installed; a third tier below 246's strict/loose ladder,
firing only on a double miss. `본문` and `삭제` went 0 → 1, labelled `match_mode='korean'`; every
English query is byte-identical. ⚠️**pgroonga is ADDED, never substituted** — alone it regresses
English (`reports` 185 → 106, it does not stem). ⚠️A `korean` row grades **WEAK** like `loose`; a
substring hit reported as precise is the inverse of the 2026-08-22 false-miss defect.
⚠️`pg_relation_size` reads **0** for a pgroonga index — measure cost by `pg_database_size` delta
(this one is ~90MB for ~8.6MB of content). Gate `test_search_speaks_korean.py` 20/20 against the
LIVE database; it SKIPS loudly without a DB URL rather than passing over nothing.

⚠️ **Only `SUPABASE_DB_URL` (superuser) is configured locally** — `_RO` and `_MIGRATE` from
ACCESS.md were never created. Any "read-only" probe in this repo is actually running as superuser.

## Korean marketing: phase 1 COMPLETE (2026-09-21)

ADR-660 §14. **Seven** page pairs ship Korean: `/`, `/pricing`, `/how-it-works`, `/faq`, `/about`,
`/developers`, `/support`, each with a `/ko/...` twin. The toggle swaps IN PLACE both directions — a
reader who clicks 한국어 on /pricing lands on /ko/pricing, not the homepage. 30 static routes, gate
**47/0**, voice 0, tsc 0.

⚠️ **The toggle assumes exactly TWO languages** (it shows "the other one"). A third locale must turn
it into a menu; the gate asserts `len(LOCALES) == 2` so that day names the file.

⚠️ **On `/developers`, identifiers are never translated** — verb names, `files:read`, `GET /llms.txt`
and every URL are the contract a client types. Only the sentences around them are worded.

⚠️ **`TRANSLATED_PATHS` must never run ahead of the routes.** A rostered path with no
`app/ko/.../page.tsx` becomes a 404 reachable from the header, footer and hero. `localePath` refuses
to prefix an unrostered path and the gate pairs roster against route — add a path there in the SAME
commit that adds its route.

⚠️ **`TraceCard` and `CompoundsStepper` must stay hook-free** (words as props). They render inside
blog posts via `lib/blog-embeds.tsx`, outside every scope; a translation hook in either breaks 2
posts' prerender while tsc and every gate stay green.

**Prices are never translated** — they arrive as ICU arguments from `PRICE_COPY` so ADR-445 §6's
single source survives translation.

**Still English by ruling**: the blog (113 posts — a content project), `/privacy` + `/terms` (a
mistranslated clause is a liability; wants a professional translation), `/invest`, `/engines`,
`/privacy-architecture`.

## Korean beyond the interface — five rulings awaited (audit 2026-09-21)

`docs/analysis/korean-beyond-the-interface-2026-09-21.md` (`64b7dd1`). Audit only, nothing built.
**Read `docs/analysis/language-support-korean-feasibility-2026-09-16.md` alongside it** — it ranked
the work behaviour → search → chrome five days before ADR-660 shipped the chrome, and no ADR cites it.

**Two findings block real Korean use:**
- **Search** silently under-returns. Driven through the real RPC on a real Korean file already in the
  substrate: bare nouns hit, particle-bearing and conjugated forms return **0**, English returns 20.
  `pgroonga` 3.2.5 **is available on Supabase and not installed** — that is the unlock.
- **NFC/NFD** — 4 Hangul paths in production, 2 NFC and 2 NFD, each findable only in its stored form.
  No write path normalizes. This is `(workspace_id, path)`, the substrate's binding unit.

**Already ruled — do not re-report as gaps**: ADR-660 D5 (verified holding), ADR-469 (Korean
filenames), `80b9874` (IME, 15 importers). Layout is measured clean — Korean is 0.86× English width.

**Awaiting an operator ruling (never ruled, not deferred):** search under Korean; NFC normalization;
whether to write down the unattended-language behaviour that is currently correct by silence; whether
skills stay English and whether their ceiling should be characters/tokens rather than bytes (Korean
needs ~6.6KB against 4000); whether English email to a Korean member is acceptable or merely unbuilt.

## Korean: coverage is COMPLETE (ADR-660 §13, 2026-09-21)

The interface speaks Korean. 2330 keys / 17 namespaces; every member-facing surface reads the catalog.
Driven in both languages across eight surfaces. Gate **36/36**, voice guard 0, tsc 0, build 135 prerendered.

**`LITERAL_COPY_CEILING` now means something different.** It reads 262, but **226 of those are FALSE
POSITIVES** inside fully-translated files (the meter marks Prettier-wrapped continuation lines of `t(…)`
calls and counts JS identifiers as prose). The other 36 are the ruled-English floor. Do not chase either —
the ceiling now guards against NEW literal copy, not remaining work.

⚠️ **`SCOPELESS_BY_RULING` in the gate is load-bearing.** `NewArtifactModal`, `WorkspacePicker`, `Working`
and `BlogPostList` are reachable only from `/invite/{token}`, `/s/{token}`, `/mcp/authorize`,
`/auth/callback` and `/blog` — all outside every `IntlScope` by operator ruling. A translation hook in any of
them is a **runtime crash on a signed-out entry path** that tsc, the build and every other arm pass cleanly.
If a later ruling scopes those routes, delete that set in the same commit.

**Still English and still open**: served strings (ADR-660 §8) — surface titles beyond the shell's slug map,
agent names/blurbs, the notification-kind registry, connector titles, 136 `HTTPException` details, the lane's
default name. Plus `lib/formatting.ts`'s relative times (`just now`, `2m ago`), a shared layer on **15
surfaces** that wants its own pass. The `/admin` console chrome stays English by ruling.

## The local `node_modules` does not match what Vercel installs (found 2026-09-20)

The deploy resolves from `web/package-lock.json` (npm); the local tree is a pnpm layout with no committed
pnpm lockfile, so it floats. Measured: **19 top-level packages differ** (`@supabase/supabase-js` 2.116 local
vs 2.93 locked, `@sentry/nextjs` 10.75 vs 10.51, `framer-motion` 12.43 vs 12.29). A green local build has not
been verifying the deployed dependency set. Pick one manager and one lockfile. Do NOT run `npm install` into
the pnpm tree, and do not commit a `pnpm-lock.yaml` beside the npm lock — it switches Vercel's manager.

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

## ADR-657 click-pass DONE (2026-09-18) — one copy finding open

Driven in a real browser (own API :8010 + web :3000, isolated from a foreign uvicorn on :8000).
Both lanes render visibly two; the curated set-up step renders every field a URL cannot carry;
the shape resolved live to `https://acme-supply.myshopify.com/api/mcp`; the attach landed
`mcp:shopify` with `aperture {}`, `category Commerce`, no verdict/rationale on the row, and the
credential envelope decrypted back to `X-Shopify-Access-Token` + the exact token. The open lane's
paste box is `type="url"`, visible, 396x38, not readOnly — the browser agrees with gate check 5d-ii.
Row deleted after the pass.

- **OPEN — the curated `rationale` is written for the canon, not the member.** It renders verbatim
  as the first paragraph of the set-up step and says "the member's own commercial records",
  "derived_from naming the source", and "the opposite of the Higgsfield case" — a vendor a real
  operator has never heard of, in an ADR-internal comparison. The field is member-facing copy doing
  double duty as the admission argument. Decide: split `rationale` (the record, gate-checked) from a
  member-facing `why_line`, or rewrite this one in VOICE-AND-TONE register. No gate covers it —
  `test_adr657_two_lanes.py` §2e asserts the rationale is PRESENT, never that it is legible.

## The Supervisor — OPEN items (ADR-656 → superseded by ADR-658/659/660; see the ledger)
- ⚠️ The DONE/vocabulary narrative that stood here is stale and was deleted: `threads` no longer
  exists (ADR-658 §2 deleted the kind, `THREAD_CAP` and `_threads`), the sections are
  `work` · `needs-you` · `note`, and sources are a LIST (am.5). The shipped history lives in the
  ADR-LEDGER and in ADR-658's amendments 1–5; only the unbuilt items below are open.
- **OPEN, in order**:
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
- **A cold URL load can foreground the shell's REMEMBERED window instead of the one the URL names**
  (found 2026-09-19, ADR-658 click-pass). `/supervisor` rendered the Text surface with an empty Dock, and
  on another load flipped to Files ~30s in, while the address bar still read `/supervisor`; the same for
  `/notifications?notifications.pane=standing` — the URL the `/strings` stub redirects to. The Supervisor
  DID mount (its three reads were served 200). This is the race `web/lib/shell/route-sync.ts` says it
  closes; its gate did not see it. Entering through the Dock works. Not reproduced on a fresh account —
  the operator's `member_state.shell` row carried `open: […, notifications, supervisor]` and a remembered
  `foregrounded` at the time. Drive it before reasoning about it.
- ⭐**READ FIRST: `docs/analysis/the-supervisor-from-first-principles-2026-09-20.md`** — the operator ruled
  ADR-658 a half measure (it asked what the canon PERMITS, not which limits are LAW). Audited; it holds. Steps
  0–2 SHIPPED as **ADR-659** (2026-09-20): a source may be a workspace path so kept files CHAIN, a run whose
  sources have not moved is skipped at $0, the claim is its own lock column. **NEXT, in the analysis's order
  (each its own ADR):** (3) `needs-you` reads the WORK — a refused run, a problem declaration — not only chat
  mentions; the Supervisor's job text is still ADR-656's subject and never mentions standing work
  (`build_supervisor_posture`, 0 occurrences of *standing · declar · schedule*); the cockpit draws the graph
  the ledger now witnesses. (4) the PROPOSED ACT — a run ends in a send/publish that waits for the member's
  click (the queue is live: `action_proposals`, `ProposeAction`). (5) compose targets, the generator
  cardinality, and the 4096-token ceiling (a kept file is still a short document).
- ⚠️**ADR-659's door is NOT click-passed.** `tsc` clean, `next build` green, the lock DRIVEN against the live
  `tasks` table — but the new "Your workspace" source field (its folder list from `getRoots`), the detail's
  "from …" line and the `source_cycle` copy have not been driven in a browser. Drive: create from the
  workspace start over a real folder → Run now → the run row names what it was made from → a second Run-less
  tick reads *"Checked. Nothing new to read"* → chain a second declaration off the first kept file.
- ⚠️**Named limit (ADR-659 D4 rule 6)**: the DOOR refuses a source its declarer cannot read; the
  conversational path writes the YAML through `WriteFile`, which checks WRITE scopes only. Safe today — every
  narrowed-read grant is share-as-view with `write_scopes=[]` — and a hole the day a write-but-narrowed-read
  grant exists: the run must then check the declaration's AUTHOR.
- **Connector capture has NO driver**: `run_connector_capture`'s only caller is the standing sweep, so with 0
  declarations nothing is captured from any connected platform. `intake-pipeline.md` §5's "the scheduler
  drives" row contradicts its own status row.
- The MCP `delete` verb's docstring promises a FOLDER grain; `reference: "click-pass-brief"` answered
  `file_not_found` while two live files sat under it (2026-09-20). Files deleted by name instead. Undriven
  beyond that one call — it may want a trailing slash, in which case the docstring should say so.
- `test_retired_vocabulary_ratchet.py` is RED at baseline: `ADR-LEDGER.md` 49 > 48 retired-term lines, and has
  been across at least the last eight ledger commits (back past `9e3d5e9`). ADR-659's and ADR-618's entries
  add ZERO. Find the line that crossed it and reword it; do not raise the ceiling.
- `test_adr557_router_hardening.py` now CRASHES (`FileNotFoundError: services/apps/images/decompose.py`) — the
  gate census lists it as drift; it has decayed to reporting nothing.
- `scripts/alpha_ops/activate_persona.py`, `restore_track_universe_schedule.py` and
  `scripts/oneshot/adr267_pnl_unification_migration.py` import `materialize_scheduling_index`, which ADR-632
  DELETED — they raise on import of that name. alpha_ops is Hat A; rule whether they are rewritten against
  standing work or deleted with the recurrences they activated.
- **`GET /api/supervisor/state` took ~23s from a cold local API** (the mentions read, through the shared
  service client — likely the `[Errno 11]` item below). The surface no longer waits on it (A1.9); the read
  itself is unexamined.
- Carried since 2026-09-04: `projection.ts`'s second CSV parser · blogger's first real standing
  declaration (compose-only) · the `/images` export click-pass. (The Files door for declaring standing
  work closed 2026-09-19 as the Supervisor's door — ADR-658 D4.)
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