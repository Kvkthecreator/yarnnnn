# ADR-627 + ADR-629 click-pass — Blogger live on production (run 1)

**Date**: 2026-09-01 · **Deploy**: `deb430a` (API live on Render; Vercel
status `success` on the commit) · **Principal**: the rig owner
(`kvkthecreator@yarnnn.com`, workspace bf5b25a9) via a minted single-use
magic link, driven through the chrome-devtools MCP browser (own profile;
one stale profile-holder from 08-31 killed by lstart first).

## PASS — observed, in order

| Claim | Observed |
|---|---|
| Auth cover is roster-derived (no hand-listing for a served app) | logged-out `curl /blogger` → 307 to `/auth/login?next=%2Fblogger` |
| ADR-629 D1 wire | `/api/programs/surfaces` carries `"slug":"blogger","stage":"primary","badge":"beta"` and the same pair on `images` |
| ADR-629 D1 launcher chip | launcher rows read **BloggerBETA** / **ImagesBETA** in the WORKSPACE group |
| ADR-629 D1 Dock tooltip | the open-surface Dock icon is announced **"Blogger (beta)"** (title + aria-label) |
| Curated Dock untouched (ADR-592 byte-equality reseed) | the rig owner's persisted Dock kept its six icons; Blogger arrived via the launcher and joined the Dock as an OPEN surface |
| App-scoped creation | Blogger's New menu offers exactly **Post** ("A published piece — blog post, essay, landing page") — no deck |
| D1 article-first scaffold | created `operation/adr627-click-pass-post/post.html`; canvas rendered kicker · h1 · standfirst · byline · prose band (no hero) |
| Band grain, not slides | navigator reads **SECTIONS**; Add door says "a **section**, component, text, media, or data" |
| D2 resident derivation | composer reads **"Message Blogger…"**; bound lane created server-side (`POST /api/lanes` 200) |
| D2 the being writes through the lane | asked for a real title + standfirst; canvas h1 became *"Introducing Blogger: a desk for publishing, right inside the workspace"*, standfirst replaced, kicker/byline/body **untouched** as instructed |
| The posture behaves, not just serves | Blogger **recalled first** ("Searching knowledge for Blogger desk publishing posts") and stated its assumption ("No existing settled positioning… I'll write a direct, honest announcement") before revising |
| Receipted | reply carries `read a file · searched knowledge · searched your workspace · revised a file` |
| Promotion derivation (ADR-602 D3 via 629) | `/agents` lists all four: Designer (Images) · Editor (Slides, Text) · Supervisor (Strings) · **Blogger (Blogger)** — Designer's row appeared from the stage flip alone |
| Type→app association at its real consumer | double-clicking `post.html` in Files routed to `/blogger?blogger.file=…` |

## Harness notes

- ⭐ **A page loaded seconds after push renders the PREVIOUS bundle.** The
  first launcher read showed no chips while the API already served `badge` —
  Vercel's build finished ~1 min later; a reload fixed it. Confirm the
  commit's Vercel status (`gh api …/commits/<sha>/status`) before reading a
  negative off the surface.
- ⭐ **The MCP `fill` tool does not arm React's Send** (value visible in the
  a11y tree, state not updated) — and the native-setter replay is SKIPPED if
  the value is unchanged (React's change tracker dedupes). Clear to `""` with
  an `input` event, then set the real text with a second `input` event.
  (Extends the ADR-626 click-pass lesson.)

## NOT proven (declared, not silent)

- A **fresh principal's default Dock** carrying both new icons (no
  uncurated principal driven; the derivation is gate-asserted).
- The **IMAGES app's own flow** post-promotion (tile verified present +
  badged; the compose loop was not driven — it predates this arc).
- The **standing leg** — first real `blogger` declaration still owed.
- Revision attribution row in the DB (the surface receipt was accepted).
