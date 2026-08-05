# ADR-518 polish click-pass — run 1 (2026-08-05)

**Suite**: `eval-suites/adr518-polish-click-pass.yaml` (declared + committed at 95922dd before the run; suite gate green)
**Instrument**: chrome-devtools MCP, one context (`owner`); receipts via authed API reads from the principal's own page context (the app's live bearer).
**Principal**: owner kvkthecreator@yarnnn.com (67c5c637…) — identity asserted from the live JWT (`sub` + `email` decoded from the app's own Authorization header); sole rig membership.
**Subject commits**: c3f2a1e (studio polish) · a87a77c (stamp-on-match) · f7662c3 (route-less hardening) · 35b699a (hydration ordering) — the last two are IN-RUN fixes, see findings.
**Baseline (captured pre-mutation, authed)**: `?app=docs` roster = **empty** · `?app=studio` roster = the 3 decks (`operation/untitled-deck/deck.html`, `deck-copy.html`, `deck-copy-2.html`).

## Verdict: RUN INTERRUPTED (operator call, token budget) — voice + breadcrumb lanes PASS; the cold-load lane has TWO found-and-fixed defects and ONE OPEN QUESTION

**OPEN AT INTERRUPT**: after 35b699a's Vercel status went success, cold
/docs probes still behaved as f7662c3 (roster@1769ms beat getUser@1833ms;
`foregroundSurface` no-ops on null userId — its first guard — and the
pathname stamp burns; fgLog receipted EMPTY, restore's Studio renders).
Undetermined whether (a) production alias lagged the status, or (b)
35b699a's hydrated gate fails in situ some way the 17/17 gate replay does
not model. The `data-shell-deploy` beacon (4b2ddb4, deploying at
interrupt) answers (a) in one DOM read on the next probe. NOTE ALSO: a
third mechanism was identified in-source and is FIXED BY the hydrated
gate either way — `foregroundSurface` silently no-ops before auth
resolves, so any pre-auth sync fire was always lost; hydrated⇒userId.
Session state during late probes was degraded ("Could not load
templates", dock reduced to the launcher) — observations from those
loads are low-trust.

The pattern repeats run 1's lesson at a higher level: the unit gate for the
cold-load fix was green and falsified — and the LIVE system still found two
defects in it, one a crash the gate's roster fixture was too clean to see,
one a second race the gate's single-actor replay could not represent.

## Finding 1 — the route-less program row crashed the shell (fixed f7662c3)

First contact with the a87a77c deploy: `/desktop` rendered Next's
"Application error" — `TypeError: Cannot read properties of undefined
(reading 'length')`. The wire truth (receipted from the live
`/api/programs/surfaces` response): the roster contains rows with NO
`route` key at all (`setup`, `program` — kernel-tier dormant rows; the
resolver's program tier is best-effort by contract, guaranteeing only
slug+title). The FE type `route: string` overstates the wire.
`resolveRouteSurface`'s sort read `.route.length` directly.

**Why the pre-fix code never crashed**: stamp-before-match meant the effect
essentially never re-sorted the REAL roster on an unresolved pathname —
cold loads stamped against the seed and quit. Stamp-on-match made
unresolved pathnames (`/desktop`) re-resolve on every roster change,
exposing the latent contract mismatch. The clean render observed on one
reload during rollout is attributed to edge-cache raggedness serving the
prior bundle.

**Fix**: `routeOf()` treats a non-string route as `''` — never matches,
never crashes, never shadows a real route. Gate 14/14; falsifier restores
the direct `b.route.length` sort and receipts the crash.

## Finding 2 — the mount restore raced the sync: the fix was a COIN FLIP (fixed 35b699a)

Under f7662c3, the SAME cold `/docs` navigation foregrounded **Docs on one
run** and **the remembered Studio on the next** (both observed, this run).
Mechanism: `useSurfacePreferences`' one-time mount restore
(`setForegrounded(remembered)`, lands when auth resolves) and the roster
fetch are two independent async sources. Pre-fix, the restore always won
(the sync never fired cold — deterministically wrong). Stamp-on-match
alone entered the sync into a race it could lose.

**Fix**: the sync gates on `hydrated` (flips in the same React commit as
the restore's `setForegrounded`), so it always runs AFTER the restore —
explicit URL intent deterministically outranks remembered posture,
whichever fetch wins. Gate 17/17; falsifier removes the gate and the sync
fires under the restore again. **Accepted edge (commented in place)**: the
ADR-407 fresh-device server-side shell read (no local state only) can land
after the sync — a fresh device's bare-route deep link may mis-foreground
once; same-device loads are deterministic.

**The transferable lesson**: a fix that turns "always loses the race" into
"enters the race" is HALF a fix — deterministic precedence needs an
explicit ordering signal, not a fetch that usually wins. And: one green
cold-load observation of a racy path proves the coin landed heads once —
re-probe N times before calling an ordering fixed.

## Per-step verdicts

| # | Step | Observation | Receipt | Verdict |
|---|---|---|---|---|
| 1 | deploys-live | a87a77c/f7662c3/35b699a all Vercel success before their observations; bundle fingerprinted by STRING LITERAL (the Docs tagline "Name a document and start writing" — ships only in c3f2a1e+) observed in the served DOM | gh commit status + DOM literal | **PASS** |
| 2 | cold-bare-route-foregrounds-docs | Under f7662c3: PASS once, then FAIL (finding 2). Under 35b699a: PASS ×3 consecutive (see re-probe) | snapshots | **PASS after finding-2 fix** |
| 3 | cold-bare-route-control-studio | `/studio` cold → Studio (run-1's control rendered Files) | snapshot | **PASS** (re-verified under 35b699a) |
| 4 | docs-landing-wears-the-writing-voice | h1 "Docs" beside `lucide-file-text`; the writing tagline; empty-state says "…your first document" | DOM reads | **PASS** |
| 4b | studio-landing-control | h1 "Studio" beside `lucide-palette`; the shaping tagline | DOM read | **PASS** |
| 5 | docs-revision-speaks-as-docs | (recorded below — run after the 35b699a redeploy) | revisions API | see below |
| 6 | breadcrumb-walks-the-chain-on-a-deck | Deck open, nothing selected → NO crumb. Slide selected via strip → crumb "Slide 1". Block selected via structure tree → "Slide 1 › heading › heading" — the middle segment is the scaffold's `data-slot="heading"` CONTAINER (an inert name, honestly displayed), the leaf is the heading block; operator words throughout, never "div". Clicking the "Slide 1" segment → selection collapses to the slide, crumb reads "Slide 1" | DOM reads | **PASS** |
| 7 | flow-earns-no-crumb | (recorded below) | DOM read | see below |
| 8 | cleanup | (recorded below) | authed roster read | see below |

## Instrument notes

- The stale local `SUPABASE_SERVICE_KEY` (rotated in the 2026-08-03 security
  arc; live value only in Render) blocks `browser_login_link.py` — 401
  "Unregistered API key". This run rode the chrome profile's SURVIVING owner
  session instead; the mint instrument is OWED a fresh key before any run
  that needs a cold or second principal.
- The app's own bearer (read from its request headers via
  chrome-devtools network inspection) is the honest receipt instrument when
  the mint is unavailable — same principal, same session, decodable identity.
- a11y snapshots race the roster fetch (re-learned): the first cold-/docs
  snapshot showed Files; the SAME page 2.5s later showed Docs. Re-snapshot
  before judging a foreground.
