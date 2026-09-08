# ADR-646 — The server scopes the type

**Status**: Accepted · 2026-09-08
**Supersedes nothing.** Completes ADR-473 D2/D4/D6, which declared the rule and
built the primitive that enforces it, and then never called it.

---

## 1. The report

> "blog types and slides types are still showing on especially slides side."

Driven, that reproduces as three distinct faults with one shared cause, plus a
fourth that is the same shape pointing the other way.

## 2. What was actually there

ADR-473 got the MODEL right and it has not needed changing. An artifact
declares its type in its own bytes (`<html data-template="deck">`), a layout
row declares which app owns that type, and both facts are derived — two
derivations, zero stored state. The registries agree:

```
LAYOUTS: {'deck': 'slides', 'post': 'blogger', 'image': 'images'}
slides -> {'deck'}   blogger -> {'post'}   images -> {'image'}
```

What was wrong is that **nothing on the server ever asked**. `kinds_for_app()`
— written by ADR-473 D2 as *"the inverse lookup… used to scope an app's
creation palette and its artifact list"* — had **zero production callers**. Its
only references were its own definition and its own test:

```
api/services/authoring.py:2609   ← the definition
api/test_adr473_document_types.py:50,78,79,80
```

So every endpoint served the CROSS-APP set tagged with an `app` field, and
every scoping decision happened on the client, by hand, in four places. One of
them was wrong; one had gone stale; one was capped at 20 rows; one was the only
thing standing between a member and another app's types.

**The gate was green throughout.** It asserted `kinds_for_app("slides") ==
{"deck"}` against a function nothing called — a true statement about dead code.

## 3. Decisions

### D1 — `GET /studio/templates` takes `?app=`, scoped by `kinds_for_app`

The palette is scoped SERVER-side. Omitted → every template (a legitimate
cross-app creation surface). The `app` field stays on each row: the association
is still served (D3), so a client still resolves kind→app without hardcoding.

The client filter this replaces (`res.templates.filter(t => t.app ===
app.slug)`) was a single line in `StudioSurface.tsx` — correct, and the entire
defense, on a payload that shipped every app's types to every app.

### D2 — the create door refuses a type the asking app does not own

`CreateArtifactRequest` carries `app`. When present it is ENFORCED: minting a
`post` from Slides is a 422. Optional because the door predates the field and a
cross-app creation path (Learn-from) is legitimate.

**A scoped list that no write door checks is a suggestion.** The palette is
client-rendered; nothing stopped a hand-built POST. Refuses rather than
silently re-homing — the member asked for a specific type, and a quiet
substitution is the worse answer.

### D3 — the vocabulary serves arrangements CROSS-APP

`get_vocabulary` read `STUDIO_ARRANGEMENTS` — Studio's OWN table — where every
neighbouring key read the cross-app registry. `BLOGGER_ARRANGEMENTS` and
`IMAGES_ARRANGEMENTS` both register through `register_layouts` and neither ever
reached the client.

`post` is `mode: "paged"`, so Blogger's paged chrome MOUNTED and then had
nothing to offer: an empty band gallery, no error anywhere to read. Added
`all_arrangements()`, the sibling of `all_layouts()`.

This is the leak pointing the OTHER way, and it is the same cause: a
per-app table read where the cross-app registry was meant.

### D4 — the Open picker passes the KIND

`OpenArtifactModal` called `resolveSurfaceApplication(node.path)` — dropping
the third argument. The type lives in the file's own bytes, so path alone
cannot answer, and every `.html` resolved to the default app:

- **In Slides**: `'slides' !== 'slides'` → every artifact in the tree passed.
  The only remaining gate was the `owned` set, which is capped at the served
  index's `_DISPLAY_LIMIT = 20` and is set to `null` on a failed fetch — where
  the predicate degrades to `true`. **The scoping degraded OPEN.**
- **In Blogger**: `'slides' !== 'blogger'` → nothing passed. Blogger's Open…
  was permanently empty.

That asymmetry is the reported symptom, and why it read as *"especially the
slides side."*

### D5 — an unowned type degrades to the generic viewer, never to an app

`resolveSurfaceApplication` ended `appForKind(kind) ?? DEFAULT_ARTIFACT_APP`.
That is ADR-473 D6 stated and then contradicted three lines below its own
comment: *"Absence of an owner is a fallback, not a failure"* means the HTML
viewer, not whichever app happened to ship first.

`DEFAULT_ARTIFACT_APP = 'slides'` is DELETED, in both of its homes (it also
filled in inside `registerKindApps`, for a field the server has always sent).
`appForKind` returns null and callers already handle it.

⚠️ **This is behaviour-visible.** Untyped HTML stops opening in Slides. That
population is real and includes every compose-engine output — `engine.py`'s
`_wrap_full_document` emits `<html lang="en">` with no `data-template` at all.
Those files were being filed under an app that never owned them.

### D6 — no hand-kept cross-app type list on the client

Two were found and both had gone stale:

- `studioShapes.SHAPE_STYLES` had **no `post` row** while carrying `document`
  (died with the Docs app) and `web` (aliases FORWARD to `post` at the kind
  lift, so the FE never sees it). Every Blogger artifact drew the neutral
  glyph; the one live outward type was the only one unstyled.
- `LearnTarget.template` pinned `'document' | 'deck' | null` **in two files**,
  and `writing-a-spec` targeted `document` — so `appForKind` returned null and
  the row was filtered out of every app. A Learn entry no member could reach.

The union is now an opaque slug, declared once and imported. Membership is
decided by `appForKind` at the filter site: a slug no app owns never renders.

### D7 — `vocabulary.layouts` stays cross-app, deliberately

It is the type→app ROUTING table (`registerKindApps` reads the same array).
Narrowing it to the asking app would make every OTHER app's type unowned and
route its artifacts to the generic viewer. Its consumers are lookups by the
open artifact's own slug, never enumerations. A layout PICKER built off it
would need `kinds_for_app` at the server, like the palette — not a filter here.

## 4. What this does NOT do

- **No `application/vnd.yarnnn.deck+html` conformance DAG.** ADR-473 §4
  deferred this as machinery ahead of need. It is now less premature than it
  was — the `content_type` column answers `text/html` for a deck, a post, a
  stage and a compose report alike, and the distinguishing fact is reachable
  only by reading content — but nothing in this report required it, and the
  cheaper fix is to ask the question the kernel already answers.
- **No denormalized `kind` column.** Worth doing, but for the truncation in
  `list_artifacts` (fetch 200, filter, keep 20), not for these bugs.
- **Does not scope the Files surface.** Files is the Finder — it shows
  everything, deliberately (ADR-473 D4).

## 5. What the gates learned

Four gates were repaired, and three of the four repairs are the same lesson.

- **`test_adr472`** pinned the exact import LINE, so adding a name to it went
  red while the rule it guards was more satisfied than before. Now asks the
  imported module for the binding. Falsified.
- **`test_adr473`** asserted *"the picker filters client-side on it"* — true,
  and the description of the defect. Now drives the scoped endpoint, the
  create-door REFUSAL **and its twin** (an owned type must get PAST ownership,
  or a door that refused everything would also pass).
- **`test_adr571`** proved the DEFAULT, not the claim: it asserted an UNTYPED
  `.html` landed on an authoring app, which would have stayed green if every
  type had been mis-routed to Slides. Now routes a typed `deck` and a typed
  `post` to their own apps.
- **`test_studio_name_is_one_fact`** had crashed at import since ADR-599 D5
  deleted the Docs app — **it had not run in months.** Its `.replace("Untitled
  document", …)` fixture was a silent no-op on an absent string, so the guard
  it meant to exercise was never reached.

One check went red against **the epitaph in the very comment explaining the
deletion** — the recurring "a gate check that matches its own documentation"
fault. Comments are stripped before the substring check.

## 6. A finding recorded, not fixed

**There is no `flow` layout registered any more.** Every live type is `paged`:

```
deck -> paged / slides    post -> paged / blogger    image -> paged / images
```

`document` died with the Docs app and `web` re-homed as `post`, which is paged.
So the h1-is-a-title branch of `set_artifact_title` — guard 1, `set_h1=True`,
and the whole flow half of the name-is-one-fact rule — has **no caller in
production**. The behaviour stays pinned in the gate for whenever a flow type
returns, and the gate now says so out loud rather than testing an empty set.

Out of scope here. It wants its own decision: either the publish medium is
genuinely paged and the flow branch is dead code to delete, or `post` is
mis-declared.

## 7. The one-line statement

**An app declares the types it owns, and the SERVER answers every "what may I
make / what is mine / where does this open" question from that one declaration
— because a scoping rule enforced only on the client is a suggestion, and a
primitive nothing calls is a green gate over a live bug.**
