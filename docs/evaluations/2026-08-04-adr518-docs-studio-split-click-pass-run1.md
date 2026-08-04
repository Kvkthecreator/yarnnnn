# ADR-518 Docs·Studio split click-pass — run 1 (2026-08-04)

**Suite**: `eval-suites/adr518-docs-studio-split-click-pass.yaml` (declared before the run; suite gate green)
**Instrument**: chrome-devtools MCP, one isolated context (`owner`); receipts via authed API reads
executed from the principal's own session (no RLS claim in this suite → no psql half).
**Principal**: owner kvkthecreator@yarnnn.com (67c5c637…) — identity re-asserted from the session
JWT before any observation; sole membership = the rig (bf5b25a9, `is_active`), so the subject
binds itself.
**Deploys verified live BEFORE the pass**: API `dd2b5dd` (dep-d9or1p0ae00c7397qja0, Render);
FE behaviorally (the Docs dock row ships only in dd2b5dd — observed on first shell load).
**Baseline (captured pre-mutation)**: rig artifact roster = 3 decks
(`operation/untitled-deck/deck.html`, `deck-copy.html`, `deck-copy-2.html`); `?app=docs`
roster = **empty**; `?app=studio` roster = the 3 decks.

## Verdict: PASS WITH TWO FOUND-AND-FIXED DEFECTS (+ two stale strings fixed, one pre-existing shell race recorded)

Both defects were caught by the Files lanes — exactly the per-site class the
counting-gate lesson predicts: every unit gate was green while the call sites lied.
The second was found only because the FIRST fix's re-probe ran in a FRESH session —
the original lane-7 "PASS" turned out to be session-history-dependent and is
corrected below.

## Per-step verdicts

| # | Step | Observation | Receipt | Verdict |
|---|---|---|---|---|
| 1 | deploys-live | Render deploy `dd2b5dd` status=live before the pass; Dock renders Chat · **Docs** · Studio · Radar · Files · Agents (the FE-deploy receipt) | dep-d9or1p0ae00c7397qja0 | **PASS** |
| 2 | docs-surface-mounts-as-docs | Header "Docs"; New menu offers **Document only** (+ Name-it-first / Learn-from — creation modes, not types); recents empty at baseline | — | **PASS** |
| 3 | dock-presence | The owner's dock was un-curated → the 2026-08-04 reseed generation fired: six-app Dock observed | — | **PASS** (reseed case) |
| 4 | create-document-in-docs | Created from Docs; URL gained `docs.file=operation/untitled-document/document.html` (the Docs param namespace); workbench crumb rooted "Docs"; scaffold rendered | GET file: `data-template="document"` + annotated blocks; GET revisions (absolute path): 1 revision, `authored_by=operator`, rev `a4bafa84` | **PASS** |
| 5 | studio-offers-layout-media-only | Studio New menu: **Deck + Web only**; recents = the 3 decks, the new document **excluded** (first snapshot caught the fetch race — re-snapshot before judging an empty shelf) | `?app=docs` roster gained exactly the document | **PASS** |
| 6 | vocabulary-carries-the-association | — | GET /studio/vocabulary: `document→docs (flow)` · `deck→studio` · `web→studio` · `image→images` | **PASS** |
| 7 | files-open-routes-document-to-docs | First run: Open routed to Docs **but only because this session had visited the Docs landing** (which populated the kind→app map); the menu read "Studio (default) · Preview · Chat" with Docs absent. Fresh-session control after fix 1: **Open fired `studio.file=` — the deeper defect.** After fix `7c0b352`, fresh-session re-probe: menu shows **Docs (default)** and Open routes `docs.file=` (below) | — | **PASS after both fixes** |
| 8 | studio-deep-link-still-opens | `?studio.file=<document>` honored — the Studio window holds the document (crumb "Back to Studio", iframe = the path). The shell kept the REMEMBERED surface foregrounded on the cold navigation — the pre-existing race below, not a param failure | — | **PASS** (owned param honored) |
| 9 | legacy-docs-id-is-gone | `/docs/workspace%2Fuploads%2Fnope.md` → "Page not found" (404); no redirect, no detail page | — | **PASS** |
| 10 | cleanup-trash-test-document | Move to Trash (confirm dialog honest: "stays recoverable") | Post-trash roster == baseline exactly: 3 decks; `?app=docs` roster empty | **PASS** |

## The re-probe (post-`7c0b352`, Vercel success confirmed via GitHub commit status)

Hard-reload (module state reset), Files → right-click the document: Open With reads
**"Docs (default) · Preview · Chat"** (Studio absent — it does not claim the kind; the
set = owning app + inline viewer + chat, per ADR-514). Open fires → `docs.file=…`.
The crumb tooltip reads "Back to Docs". Instrument note: the reload's landing surface
(Studio, the remembered foreground) warms the association before the Files probe, so
the browser verifies the END STATE; the truly-cold path (no authoring surface ever
mounted) is covered by the falsified per-site gate — `openPath` *awaits*
`ensureKindApps()` before resolving, so there is no race to observe.

## Finding 2 — the association was session-lazy (fixed in `7c0b352`)

Re-probing fix 1 on the deployed bundle **in a fresh session** exposed the deeper half:
`KIND_TO_APP` (the served kind→app association) was populated only by the authoring
surfaces' vocabulary fetches. A session that went straight to Files consulted an EMPTY
map — `appForKind` fell to the default app for every kind, so a document double-clicked
in a fresh session routed to **Studio**. The original lane-7 PASS was an instrument
artifact: this run's session had mounted the Docs landing first.

**Fix**: `ensureKindApps()` — an idempotent one-shot in the file-types home that fetches
the served vocabulary and registers the rows (retry on failure; dynamic import), loaded
at every consult site: openPath alongside the content read, the Files menu once per
surface, Get Info alongside its read. Gate grew to 31/31, falsified on the openPath site.

**The transferable lesson**: with a single app owning everything, "lazy until an
authoring surface loads" and "always loaded" are indistinguishable. The moment a second
app owns a kind, every consult site that doesn't LOAD the association is a mis-route —
and a click-pass lane that passed in a warm session can be a false positive. Re-probe
fixes in a FRESH principal state.

## Finding 1 — the kind-less menu (fixed in `6c64c18`)

`openPath` (the Open funnel) reads the file and resolves handlers WITH its kind — so
double-click/Open routed a document to Docs correctly. But `handlersFor` (the context
menu), `openWith` (the alternative fire), and Get Info's Opens-with all resolved
**kind-less**, falling to `DEFAULT_ARTIFACT_APP='studio'`. Pre-split this was invisible:
the kind-less answer and the true answer agreed for every Studio-owned type (the IMAGES
stage carried the same latent mislabel, unnoticed on its hidden tier). The moment Docs
owned `document`, the menu showed "Studio (default)" and never offered Docs — while the
actual Open contradicted it.

**Fix shape**: a `PATH_KIND` cache in the one file-types home. Every content read
remembers (`openPath`, Get Info's existing fetch); sync resolutions consult it; a menu
opened on an artifact of unknown kind fires one read and re-renders the open menu honest.
Until the read lands, the kind-less order shows — never a wrong route, only the pre-split
label. Gate: per-site assertions (29/29, falsified on the `openWith` site).

Also fixed from the pass: the landing empty-state ("document, deck, article, or page" —
stale twice over: article/page died in ADR-505, and the list is cross-app post-518) now
derives from the app's served templates; the crumb tooltip reads `Back to ${app.label}`
(was hardcoded "Back to Studio", visible in Docs).

## Recorded, not fixed — the cold-load route-foreground race (pre-existing)

Cold-navigating a bare surface ROUTE (`/docs`) rendered the *remembered* foreground
surface (Studio's landing) — and the control reproduced it exactly on `/studio` (rendered
Files). Mechanism: `AuthenticatedLayout`'s pathname→surface effect runs against the
SEEDED composition (chrome-only, routes all empty) before `/api/programs/surfaces`
resolves, records `lastSyncedPathname`, finds no match, and the effect no-ops when the
real roster (which DOES serve `docs:/docs:primary` — receipted) lands on the same
pathname. Every in-product door (dock, launcher, param-carrying deep links) works; the
bare-URL door mis-foregrounds for every content surface alike. Owed to the shell lane.

## Deferred (declared in the suite)

In-canvas editing lanes (human-owed; sandboxed iframe, unchanged by 518) · a
fresh-principal un-curated-dock observation (this run happened to cover it — the owner's
dock was un-curated) · member-pair lanes (no governance surface moved).
