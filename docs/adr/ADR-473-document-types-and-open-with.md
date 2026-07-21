# ADR-473: Document Types and "Open With" — LaunchServices for Artifacts

> **Status**: **Accepted** (2026-07-21) — operator-ratified, implementation delegated. Completes the ADR-472 carve by giving the two authoring apps a real **type→app association**, and generalizes it so the Nth app costs one row.
> **Date**: 2026-07-21
> **Dimension**: **Channel** (Axiom 6 — which app opens what) primary; **Substrate** (Axiom 1 — the type is lifted from the artifact, never stored beside it) secondary.
> **Relates to**: ADR-472 (the IMAGES carve — this closes its leak), ADR-436 (the app registry / LaunchServices layer this extends), ADR-451 (the surface-owning app layer — `resolveSurfaceApplication`), ADR-459 (`data-template` as the artifact's kind, opaque-slug contract), ADR-427 D5 (type is DERIVED, never stored — the same principle, one layer up), ADR-222 (the kernel names the slot; the program fills the value).
> **Amends**: ADR-451 (its single hardcoded Studio row becomes a table lookup), ADR-436 (the registry gains the *authoring* half — its 7 rows were all passive viewers).

---

## 1. Context — the leak the carve left

ADR-472 gave IMAGES its own surface, route, dock icon, and backend module. It filtered the **template picker** so each app offers only its own shapes. It did not filter anything else — and the operator saw the result immediately (2026-07-21, on `/images`):

> "i notice that document types for images are showing on studio, while vice versa images should only show images. slight considerations of this was already provided within studio, now we need to make this more properly managed. think, in terms of a PDF viewer or finder on macOS on file format and 'open with' like logic here for a scalable, future proof solution."

The receipt: the Images landing's "Continue where you left off" lists **Test page · Test article · Build in the Downturn (Deck) · Prd for yarnnn (Document)** — every Studio artifact in the workspace — alongside the one real Image. `loadRecents()` calls `api.studio.artifacts()` with no notion of which app is asking.

**The deeper reading is the operator's, and it is right:** filtering recents is a one-line patch. The *scalable* question is the one macOS answered decades ago — **what document types does this app own, and what opens this document?** Patch the list and the same leak returns at Open, at the Files surface, at the Nth app.

## 2. Why extension is not enough (the fact that forces a new layer)

The existing resolver (`web/lib/file-types/index.ts::resolveViewerApplication`) keys on **file extension + MIME**, which is the right answer for `.pdf` / `.png` / `.mp4` — one format, one app.

**It cannot separate Studio from IMAGES: every artifact of both apps is `.html`.** A deck, an article, and an image stage are the same file format. So:

- `resolveSurfaceApplication` (ADR-451) hardcodes `isHtml → Studio`, which now sends an IMAGES stage into Studio.
- `resolveApps` (ADR-436) resolves every artifact to `web.viewer`, blind to which app authored it.

macOS has exactly this case and exactly this answer: a `.plist` is XML, a `.prproj` is XML, a `.sketch` is a zip — **the extension is the container; the TYPE is finer than the container.** LaunchServices resolves on the *declared type* (a UTI), which conforms upward to the container format. That is the missing layer here.

**The type already exists in our substrate** — `data-template` on the artifact's root, lifted by `artifact_kind()` (ADR-459 D1), opaque-slug and program-extensible. Every artifact already declares its type; nothing consumes it for routing. This ADR consumes it.

## 3. Decisions

### D1 — The document type is the artifact's `data-template`, lifted never stored

The artifact's root `data-template` slug IS its document type — the UTI analog. **Derived from content, never a stored sidecar column**, which is ADR-427 D5's principle ("type is derived, never stored") applied one layer up, and ADR-459 D3's opaque-slug contract preserved: a bundle-shipped `tearsheet` still round-trips with zero kernel edits.

The container format (`.html`) remains what a *generic* viewer keys on. Type conforms to container: an unrecognized artifact type still opens in the HTML viewer, exactly as an unknown UTI still opens in a text editor.

### D2 — A layout row DECLARES its owning app; the registry answers "who opens this"

The layout registry (ADR-472 D2) is already the one place both apps register their document types. Each row gains one field:

```
"app": "studio" | "images"     # the surface slug that OWNS this type
```

From that single declaration the kernel derives — never restates — all four behaviors:

| Question | Answered by |
|---|---|
| Which shapes may this app create? | rows where `app == me` |
| Which artifacts are MINE (recents, open)? | artifact's `kind` → row → `app == me` |
| Where does the Finder's open verb route this file? | `kind` → row → that app's surface + param |
| Which app is the fallback? | no row / unknown kind → the generic viewer |

**One declaration, four consumers.** Adding the Nth app is one field on its rows, not four filters. The FE never hardcodes a slug (ADR-472 already proved the value of this: canvas needed almost no FE code because the chrome derived from served `mode`).

### D3 — The association is served, not restated client-side

The kernel owns the table; the FE reads it. `GET /api/studio/vocabulary` + `/templates` already serve layout rows — they gain `app`, and the artifact list (`GET /api/studio/artifacts`) already carries `kind`. The FE resolves `kind → app` from the served vocabulary.

**Consequence (the discipline):** no FE file may contain a list of "which types are Studio's." The one existing hardcode (`resolveSurfaceApplication`'s `isHtml → studio`) is **replaced** by the table lookup, not supplemented — Singular Implementation, per the hooks discipline. A gate asserts the FE holds no such list.

### D4 — Filtering is by OWNERSHIP, and the default view is scoped, not global

Each authoring surface shows **only artifacts whose type it owns** — recents, the Open picker, and creation alike. This is the Finder/Preview behavior the operator named: Preview's Open dialog does not offer `.sketch`.

The backend takes an optional `app=` filter on the artifact list (the FE passes its own slug), so the scoping is one query, not a client-side sieve over an unbounded list — it stays correct when a workspace has 10,000 artifacts and a page of recents.

**Not a wall:** the *Files* surface remains the un-scoped Finder over everything (DP29 mirror), which is where a member goes to see all their work regardless of app. Scoping the app surface is not hiding; it is what makes an app an app.

### D5 — "Open With" is the resolver's SHAPE, still unrendered

`resolveApps` already returns an *ordered list* precisely so a second claimant lights up a picker (ADR-436 §4). This ADR keeps that stance: the association table now genuinely can return more than one app for a type, but **no picker UI ships until a real second claimant exists**. The shape is ready; the affordance is demand-gated.

The default is `apps[0]`, and the ordering rule is **first-registered-wins** — the same rule the layout registry already enforces for slug collisions (ADR-472 D2).

### D6 — An unowned type degrades to the generic viewer, never to an error

An artifact whose `data-template` no app claims (a bundle type, a hand-authored file, an artifact from a future app) opens in the HTML viewer and appears in Files. It simply does not appear in any app's recents. **Absence of an owner is a fallback, not a failure** — the grammar-not-schema rule (ADR-443 §6) at the association layer.

## 4. What this does NOT do

- **Does not add a UTI conformance DAG for artifacts.** ADR-427 D5 has one for *media* types (`public.image`…), earned by the intake gate. Artifact types have exactly one conformance edge today (`→ text/html`) and inventing a hierarchy for it would be machinery ahead of need.
- **Does not ship an Open-With picker** (D5) — the shape only.
- **Does not make apps installable by third parties.** The registry stays code-seeded (ADR-436's one-file ratchet is untouched); this ADR only makes the *authoring* half as real as the viewer half.
- **Does not scope the Files surface.** Files is the Finder — it shows everything, deliberately (D4).
- **Does not introduce a stored `app` column on artifacts.** The owner is derived from the type, which is derived from the content (D1). Two derivations, zero stored state.

## 5. Consequences

- **The operator's bug is fixed at its root**: Images shows images, Studio shows documents/decks/articles — because each app owns declared types, not because a list was filtered.
- **The Nth app costs one field.** When IMAGES P3 adds generated composition types, or a bundle ships a `tearsheet`, ownership rides the row it already needs.
- **The Finder's open verb becomes correct for every type**, not just the one Studio hardcode — an image stage opens in Images from the Files surface.
- **The kernel/FE boundary holds**: the FE learns the association at runtime and never hardcodes a slug, so a program-shipped type is routable without a frontend deploy.

## 6. The one-line statement

**An artifact declares its type in its own content, a layout row declares which app owns that type, and every "what can I make / what's mine / where does this open" question is derived from that one declaration — the LaunchServices answer, applied to a filesystem where two apps share one file format.**
