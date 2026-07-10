# The Studio — the app's own content, project storage, and the reference mechanics

*The app brings program, not substrate — nothing hidden ever enters the commons. Projects live where their meaning lives, not in an app silo. And the duplicate-vs-reference dilemma dissolves against two substrate receipts: blobs already dedupe (a copy stores zero new bytes) and moves already tombstone (a broken reference is diagnosable) — so the answer is cite-by-path with a self-healing pin, which is pptx-grade robustness without paying the embed tax.*

> **Status**: Analysis (2026-07-10). Doc-first, receipts-backed. Part 3 of the authoring-app probe — follows the benchmark (part 1) and the surface/lane design (part 2). Feeds the Studio ADR.
> **Authors**: KVK, Claude
> **Hat**: A. Vocabulary: posture, envelope, settle-then-cite, pin, tombstone, projection, GC root.
> **Operator questions this doc answers** (2026-07-10): (1) the app's content — the lane's bounded prompt-envelope documents: are they filesystem files hidden/non-editable to normal users? (2) Studio-project file management — do referenced objects (especially binary) get duplicated into the project ("what's in a project's folder is its domain," the pptx model) or multi-referenced (graph-like, with move/delete fragility)?

---

## 1. The app's own content — program, not substrate; nothing hidden, ever

The instinct behind the question ("closer to non-editable, essentially hidden, to normal users") names a real need — the Studio's operating text must not be user-mangled — but the mechanism is already canon, and it is *not* hidden files:

**The Studio's prompt envelope is code, not filesystem.** The posture, template grammars, and reference syntax live as kernel constants composed into the lane's system prompt *at turn time* — the exact mechanism lanes already use (the conventions projection, "derived, never stored" — ADR-411 D6, `lane_runner.py:21-24`) and the exact precedent ADR-414 D2 set when it converted the steward's constitution from seeded files to kernel constants. Program text is versioned in git, updated by deploy, and never appears in the workspace at all — so there is nothing to hide.

**Why hidden substrate is refused on principle**, so this never reopens:
- **DP29 (mirror discipline)**: the Files surface mirrors the substrate. A region of the filesystem invisible to members would make the mirror a lie.
- **ADR-328 (portability invariant)**: the authored filesystem is the exportable system of record. Hidden files either leak into exports (confusing) or are silently dropped (dishonest).
- **The re-founding direction**: permission and provenance are *metadata on files*, never namespace tricks. The established pattern for "operator sees it, operator cannot edit it" is **visible-but-write-locked** (the governance lock-set; the powerbox's `write_scopes`), and it remains available if the Studio ever needs a persistent machine sidecar — a `_studio.yaml` per ADR-254's underscore convention, visible, machine-parsed, write-gated. Hidden is unprecedented and stays that way.

**Per-artifact state prefers self-description over sidecars.** The artifact is HTML — its template is a `data-template` attribute on the root, its citations are `data-ref` attributes on the elements that hold them (§3). State that is *of* the artifact lives *in* the artifact, where it travels with every revision and every export. A sidecar is the fallback for state that must not live in the served markup (pin ledgers at publish, later); it is not the default.

> **The principle, stated once: apps bring program, not substrate. The filesystem holds the work; it never holds an app's operating manual.** If the Studio seeded envelope files into workspaces, we would re-create everything ADR-414 D4 killed — skeleton seeding, export pollution, files the operator never authored — one app at a time.

## 2. Where projects live — the app owns no namespace

Claude Design silos projects inside the tool. That is the sealed-island shape wearing a folder costume, and the meaning-first filesystem (the re-founding: *directory = meaning*) refuses it:

- **A Studio project is a folder, and it lives where its meaning lives.** The IR deck belongs at `operation/fundraise/ir-deck/`, not at `studio/ir-deck/` — the deck is fundraise work that happens to be authored in the Studio, exactly as a memo is operation work that happens to be written through a lane. The app-seam's rule extends naturally: *an app is shared like a contractor, never like a folder* — and it owns no directory either.
- **The project folder's shape**: one artifact file (`deck.html`) plus a local `assets/` sibling for objects imported *through* the Studio (§3's settle-point). New-artifact creation asks for (or defaults) a landing zone; the Studio never invents an app-named root.

This keeps the operator's "what's in a project's folder is its domain" instinct — satisfied by *locality*, not by *copying* (§3).

## 3. The reference mechanics — cite by path, heal by pin

The two naive options the question poses, scored against the substrate receipts:

| Option | What it buys | What it costs |
|---|---|---|
| **Duplicate into the project** (the pptx model) | robustness; folder-is-domain simplicity | **forfeits the entire structural bet** — the living reference (swap the wordmark once) is the reason this app exists instead of using Claude Design. And the byte-saving argument for *not* copying is void anyway: blobs are content-addressed, a copy stores zero new bytes (`authored_substrate.py:236` — "Insert a blob if not already present"). Duplication buys nothing at the storage layer and costs the product thesis. |
| **Bare path reference** (the graph model) | living updates | fragile exactly as the question fears: paths move and die |

**The design: every citation carries a path AND a last-resolved pin.**

```html
<img data-ref="operation/brand/wordmark.png"     ← the living reference (identity)
     data-ref-rev="rev_01J…"                     ← the last-resolved pin (survival)
     src="…resolved at render time…">
```

Resolution at render (the projection pass — mechanically, compose's existing `assets: [{ref, url}]` rewrite contract, `engine.py:49`, generalized):

1. **Path resolves** → serve the head; update the pin to the resolved revision. The reference is *living* — this is the head-tracking half of part 2 §4.
2. **Path dangles** (moved or deleted) → serve the **pinned revision's blob** — blobs are immutable and content-addressed, so the bytes the artifact last cited remain fetchable — and flag the citation as broken-but-rendering.
3. **Healing is mechanical-then-judgment**: a move leaves a tombstone at the old path whose message records the destination (`"MoveFile: to {abs_dst}"` — `workspace.py:1188-1205`), so the resolver — or the lane, on its next turn — follows the tombstone and rewrites the `data-ref` to the new path, as an attributed revision. A delete has no forwarding address; the lane surfaces it to the member ("this article cites a deleted file — re-pick or keep the pinned copy?").

**This is the pptx property without the embed tax.** PowerPoint embeds because a .pptx travels alone — the file must be its own universe. Inside yarnnn, *the workspace is the container* — the artifact never travels alone internally, so self-containedness is only *required* at the boundary (publish/export), and the boundary already has its mechanism: Article pins every reference at publish (part 2 §4); a downloaded export (future) flattens refs into a bundle. We do not pay the embed tax on every internal artifact to buy a property only the boundary needs. The pin makes every artifact *renderable forever*; the path makes it *alive while the source lives*. That pair is strictly stronger than either naive option.

**Two refinements that fall out of HTML's own semantics:**

- **Relative refs for the project's own assets.** Objects imported through the Studio settle into `assets/` beside the artifact and are cited **artifact-relative** (`./assets/hero.png`), resolved against the artifact's current path — so *moving the project folder moves the domain intact*, no healing needed. External citations (the shared wordmark, a ground-truth metric) are **workspace-absolute** and head-track. This is exactly relative-vs-absolute URLs — native to an HTML artifact, zero invented machinery.
- **Pins are GC roots.** A blob cited by any artifact's pin is retention-exempt. Cheap (content-addressing dedupes) and necessary (a published article must not lose its images to a retention sweep). This rider joins the retention rules when publish lands.

**The honest binary caveat.** Images are Category-1 binary under ADR-427 Phase 1 — served via the signed-URL path but *not yet in the revision chain* (the un-versioned `content_url` sidecar until Phase 2). So v1's reference model is **complete for text-native objects** (markdown, SVG, CSV-as-table — pin and all) and **path-only for binary images** (living reference works; the pin hardens when ADR-427 Phase 2 lands binary in the chain). Same dependency, same honesty as publish — named, not hidden.

## 4. What this settles for the app format (residue, running list)

| Question | Answer from this part |
|---|---|
| Does an app ship substrate? | **No — program, not substrate.** Kernel constants + turn-time projection (ADR-414 D2 / ADR-411 D6 precedent). Visible-but-locked sidecars are the fallback; hidden files never. |
| Does an app own a namespace? | **No.** Projects live where meaning lives; the app is a contractor over them. |
| Per-artifact state? | In the artifact (self-describing markup) by default. |
| Reference identity | path (living) + last-resolved pin (survival), relative for the project's own assets, absolute for the commons. |
| Reference lifecycle | resolve→update pin; dangle→serve pin + flag; move→tombstone-heal; delete→lane surfaces the choice. |
| Retention interaction | pins are GC roots. |
| Binary | living refs now; pins harden at ADR-427 Ph2. |

## 5. The one-line statement

**The Studio's envelope is program, not substrate — kernel constants projected at turn time, nothing hidden ever entering the commons (DP29 + portability forbid it; visible-but-locked is the fallback, ADR-414 D2 the precedent); projects are meaning-placed folders the app holds no namespace over; and citations carry a living path plus a last-resolved pin — blobs dedupe so copying buys nothing, tombstones make moves healable, pins make deletes non-fatal and published artifacts immortal — which is PowerPoint's self-containedness earned at the boundary only, while inside the commons every artifact stays what a pptx can never be: alive.**
