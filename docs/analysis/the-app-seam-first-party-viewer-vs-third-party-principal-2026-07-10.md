# The App Seam — first-party reference viewer vs. third-party principal, and the sequencing

*The OS picture is ~90% complete. The last 10% is one serving primitive and one grant class — and they arrive in a fixed order, discovered not designed.*

> **Status**: Analysis (2026-07-10). Doc-first, receipts-backed @ `7a03a8c`. **No ADR rides this document.** It is the third in the OS-framing triptych — after `the-app-layer-and-the-desktop-2026-07-09.md` (the viewer/apps distinction) and `the-commons-is-the-os-2026-07-09.md` (the *why*, one altitude up). This doc closes the loop those two opened: **now that the powerbox has shipped (ADR-434), what is actually left to make a third-party editor first-class, and in what order does it arrive.**
> **Authors**: KVK, Claude
> **Hat**: A (system canon). Vocabulary: operator, member, principal, substrate, grant, powerbox, viewer, app, minted capability, reference app, launch verb.
> **Method**: the four-primitive frame (ADR-427's adopted lens) pressed against live code @ `7a03a8c`. Every load-bearing claim carries a `file:line` or an ADR. Where the two 07-09 companions cited a gap, this doc re-checks it against the ADR-434 commit and marks it closed or standing.
> **Positioning**: unchanged, and this doc reaffirms it. ESSENCE v15's host-elsewhere lead stands (ADR-427 §11, ADR-380 §5). yarnnn-as-OS is an internal architecture truth; the app layer stays demand-gated. This doc **completes the map** so the gate is decidable, not so it opens.

---

## 0. The question this document closes

A recurring pull: *"yarnnn should have a video editor, an image editor — a dedicated surface where a user works on an artifact. Does the workspace have shared apps?"*

The pull is correct and the two words in it are fused. Unfused:

- *"A dedicated editor surface"* is either **yarnnn's own reference app** (cheap, on-thesis-adjacent, a feature-race trap if overbuilt) **or a third party's app** (the OS bet, gated on named primitives). They look identical from the operator's chair and are opposite bets from the platform's.
- *"Shared apps in the workspace"* has a precise answer that dissolves the uncertainty: **an app is shared like a contractor (a grant), never like a folder (a surface).** There is no video-editor *tab*. There is `promo.mp4` → Open With → a scoped, expiring capability to that one blob → the editor's own window → attributed revisions back. That is the macOS model, exactly.

This document states, in one place: what the four OS primitives are, which yarnnn holds after ADR-434, what precisely remains, why the remainder arrives in a fixed order, and why the first thing to build is **not an editor**.

**The thesis, stated once:**

> **yarnnn does not build apps; it builds the reason someone else's app is first-class *inside* the commons. After ADR-434, three of the four OS primitives are complete and the fourth is complete on its authorization half. What remains is a serving primitive (the minted blob capability), a binary blob an editor can round-trip (ADR-427 Phase 2/3), and an app-principal grant class — and they must land in that order, with a *read-only reference viewer* exercising the first two before any third-party principal designs the third.**

---

## 1. The four-primitive ledger, re-scored @ `7a03a8c`

macOS makes anyone's Final Cut a first-class citizen with exactly four primitives and no more (ADR-427's adopted frame). yarnnn adds a fifth no OS has — the attributed revision — and that is the *only* place its novelty budget is spent. Here is the exact standing after the powerbox commit:

| # | macOS primitive | yarnnn mechanism | Status @ `7a03a8c` |
|---|---|---|---|
| 1 | **byte-range-addressable file identity** | `workspace_blobs` behind `StorageBackend` (ADR-427) | 🟡 **text-native; Phase 1 seam shipped** (`8c91018`). Binary is still an un-versioned `content_url` sidecar until Phase 2. |
| 2 | **open declarative type system + conformance DAG** | `resolveViewerApplication` + the tier-1/2/3 fallback chain | ✅ shipped (self-described macOS-UTI; `web/lib/file-types/index.ts`) |
| 3 | **capability model — install fact + open fact** | `principal_grants` (install) + the two-axis scope gate (open) | ✅ **install shipped (ADR-373); open-fact *authorization* shipped (ADR-434)**. Serving half (minted capability) standing — §3. |
| 4 | **association table that LAUNCHES a process, never embeds** | the launch verb (redirect + scoped token) | 🔴 **not built** — no `role='app'`, no launch verb. §5. |
| **5** | **the attributed revision** *(no OS has this)* | `write_revision` + `workspace_file_versions` + `trace` (ADR-209) | ✅ shipped — the moat, the only novelty spend |

> **What ADR-434 changed on this ledger.** It closed the primitive-3 *open fact* on its **authorization** axis. The two 07-09 companions both named this as the one live gap ("no read gate; `scopes:[]` fails open; object-scoping mechanically impossible"). All three are now closed: `path_under_scopes` is one longest-prefix matcher at arbitrary depth; `read_scopes`/`write_scopes` are two independent axes; `NULL ≠ [] ≠ [..]` is a real three-state polarity. A read-only, object-scoped principal is now representable (`read: operation/`, `write: []`). **The commons's `access(2)` is complete.**

**Read this table as the map.** Primitives 2, 3-install, 3-open-authorization, and 5 are done. What blocks a third-party editor is precisely: **1 (a binary an editor can round-trip), 3's serving half (hand it *this* blob, expiring), and 4 (let it *be* a principal at all).** Nothing else. Not a manifest system, not a widget ABI, not a project format, not a merge algorithm — *that absence is the platform* (ADR-427 §6; the OpenDoc/OLE/Bonobo/KParts graveyard, app-layer doc Appendix C).

---

## 2. The fork, and why "not sure which editor" is the right instinct

There are exactly two ways yarnnn can "have a video editor." They are not points on a spectrum — they are opposite bets that look identical to the operator and diverge completely for the platform.

| | **Bet 1 — yarnnn ships the editor (first-party surface)** | **Bet 2 — yarnnn houses someone else's editor** |
|---|---|---|
| What you build | An image/video/deck editor: a dedicated surface, static-imported, mutating substrate files | The four primitives such that *anyone's* editor is first-class |
| Feels like | "the OS has apps now" | "nothing shipped" (the primitives are invisible) |
| Actually is | the **feature-race trap** — Figma/Descript/Photoshop's turf, where you are structurally worse | the **OS bet** — structurally sound, the layer above the engines |
| Novelty budget | spent on a commodity editor | spent on primitive #5 only; #1–4 are boring decade-old standards |
| Precedent in this repo | *"the lane felt like a worse Claude.ai because it competed on chat"* (the scar) | macOS: Apple's value is not Final Cut; it is the primitives that make anyone's Final Cut first-class |
| The one honest exception | a **reference app** (Preview.app) so the platform isn't empty day one | — |

**Why "not sure which" is correct:** from the operator's chair, both are "click a `.png`, an editor opens." The difference is entirely in *whose code runs and where the durable object lives.* That is a platform decision, not a UX decision — which is exactly why it must be made from the platform's chair, deliberately, not slid into by shipping an editor because it's cheap.

**The test that separates them** (commons-is-the-OS §4):

> **Does the app's value come from yarnnn having *built* it, or from yarnnn having *housed* it?**
> Built → a feature race you lose. Housed → the OS bet, structurally sound.

---

## 3. What primitive #4 has left — the minted capability (the serving half)

ADR-434 built the powerbox's **authorization** — the gate that answers *"may this principal read/write this path?"* at `execute_primitive`. It deliberately **deferred** the serving-layer half, and named it precisely (ADR-434 "Deferred" §; ADR-427 D4):

> **The minted capability** — a per-request, per-principal, TTL'd blob capability computed from `(blob_sha, principal, active grant)`, minted at read time by the LFS-batch serving path. **A cached capability is a leaked capability**, so it is never a stored column; its authority, expiry, and object-scope are computed each request.

**Why this is the piece an editor needs, specifically.** An in-shell viewer reads a file *through* `execute_primitive` — the ADR-434 gate covers it, done. But a third-party editor runs on *its own infra*; it cannot call `execute_primitive`. It fetches the blob **out of band**, over HTTP, from a serving URL. That serving URL *is* the capability — and it must be object-scoped and expiring, or handing an editor `holiday.mov` leaks a standing read of the commons. This is the macOS security-scoped bookmark: the user's file-pick **is** the grant, scoped to that object, for now.

> **So primitive #4's authorization is done and its serving is not — and the serving is precisely the third-party seam.** ADR-434 gates the *primitive call*; the minted capability gates the *out-of-band blob fetch*. Different mechanism, and it couples to ADR-427 Phase 3 (out-of-band blob serving, git-lfs batch shape). **The minted capability derives its scope from the two axes ADR-434 established** — so the authorization work was the hard, ordering-sensitive part, and it is behind us.

---

## 4. What primitive #1 has left — a binary an editor can round-trip

An editor round-trips bytes: read `promo.mp4`, edit, write it back. Today that write *has nowhere true to land* (ADR-427 §2; the substrate-keystone memory):

- `workspace_blobs.content` is **TEXT**; the CAS hashes `content.encode("utf-8")`. Binary lives in a **parallel, un-versioned** Supabase bucket referenced by `content_url`.
- A `.mp4` through `WriteFile` therefore has no attributed revision, no `trace`, no revert, no ADR-406 linearity. The moat mechanism is **text-only**.
- `FileBody` honestly renders `BlobMissing` for a versioned `.mp4` — the correct honest state *until ADR-427 Phase 2* (app-layer doc §7).

**ADR-427 Phase 1 shipped the seam** (`StorageBackend`, stream-first, byte-identical; `8c91018`). **Phases 2/3 are the media unlock**: binary as Category-1 (content-addressed, attributed, revisioned, revertible, portable) + real serving URLs. An editor cannot round-trip a video that is not a first-class versioned blob — so **Phase 2 is a hard prerequisite for a media editor**, and it is on paper, phased, not started.

> **The dependency softens for non-media.** For `.md`/`.html`/`.png`/`.pdf` — everything the viewer already renders — a lane writing `report.html` shows a rendered card *today*. The binary blocker is specifically **video and audio**. An *image* editor is closer to reachable than a *video* editor, because image bytes are smaller and the round-trip is less streaming-sensitive — but both still want Category-1 binary to be attributed.

---

## 5. What primitive #4 has left — the app-principal grant class

For a stranger's editor to *be* a principal (attribute revisions as itself, hold a scoped grant), three concrete things are missing — and the code says exactly what they are:

1. **`role='app'` does not exist.** `principal_grants.role` is a CHECK-constrained enum of six — `owner | member | own-agent | foreign-llm | platform | a2a` (`189_adr373_multi_principal_rekey.sql:64`). An `app:` caller has no branch in `_caller_class` and **falls through to `agent`** (`primitives/workspace.py`), which is write-capable on `operation/`. Admitting `'app'` is a migration + a class-default policy row.
2. **No launch verb.** An app is launched, not navigated (app-layer doc §9): a **redirect** hands off to another origin with a scoped token; there is **no surface slot, no `DeskState` window.** "Open With" is a launch; a launch is not `foregroundSurface(slug)`. This verb does not exist yet.
3. **Origin-derived types + the one-viewer-per-type falsification.** Today `resolveViewerApplication` returns a **closed TS union of nine kinds**; a third party cannot produce a value of that type. The minimal pre-app refactor (app-layer doc §12): `ViewerApplication` becomes an opaque app id; `FileBody`'s switch becomes a lookup in a mutable app table seeded with the nine kernel defaults; the seeds become ordinary rows, indistinguishable from a third party's. **This is a one-file change confined to `FileBody` — and it should run red until someone asks.**

> **This is the genuinely-deferred part, and the docs are right that it is last.** The app-principal is the primitive we understand *least*, because its shape is defined by real third-party requirements we do not yet have. Designing it speculatively is the dual-implementation the codebase forbids. It should be **discovered by the second app, not designed before the first.**

---

## 6. The sequencing — a fixed order, and why

The app-layer doc §11 names the order; ADR-434 shifted where we are on it. The order is not a preference — each step's *design inputs* come from the step before, so reordering means designing in the dark.

```
✅  ADR-373         install fact (principal_grants exists)
✅  ADR-434         open-fact AUTHORIZATION (two-axis scope gate)     ← just shipped
✅  ADR-427 Ph1     the storage seam (StorageBackend, stream-first)
─────────────────────────────────────────────────────────────────── you are here
🔲  ADR-427 Ph2/3   binary as Category-1 + minted serving capability  ← primitives #1 + #4-serving
     │
🔲  a READ-ONLY reference viewer of a type you don't author           ← the first "app"
     │   • runs under the OPERATOR's own grant — ZERO new grant machinery
     │   • exercises: type declaration + fallback chain + range read
     │     + the minted-capability serving path + the launch verb
     │   • the rehearsal of the hard parts with the risky part (a foreign
     │     principal) REMOVED
     │
🔲  the app-principal ADR                                             ← primitive #4-principal
         informed by whatever the read-only viewer had to reach around
         (role='app', origin types, the powerbox's real requirements)
     │
🔲  the first EDITOR (the second app)                                 ← the thing that needs it all
         a third-party principal round-tripping a binary blob under a
         minted, expiring, object-scoped capability
```

**The load-bearing insight** (app-layer doc §11, made concrete by ADR-434): the first reference app must exercise the powerbox **without being a third-party principal**. A read-only viewer runs under *your* grant — so it needs no `role='app'`, no launch-handoff-to-a-stranger — yet it exercises type declaration, the fallback chain, the range read, and *the minted-capability serving path* (the one piece of #4 still to build). It is a full-dress rehearsal of the hard parts with the one dangerous part removed. **The editor — which actually needs the app-principal — is the second app, so #4-principal's shape is discovered by real requirements, not invented.**

> **Building an editor first inverts the risk.** You would design the app-principal grant class, the launch verb, and the serving capability all at once, speculatively, against a use case you are simultaneously inventing. The read-only viewer decomposes that into: *build the serving capability (concrete), then design the principal (informed).*

---

## 7. "Shared apps in the workspace" — the answer, stated plainly

The operator's uncertainty (*"workspace will have shared apps? not sure"*) resolves cleanly, and the resolution is the whole point of the OS framing:

**An app is not a surface. It is a process; the document window is its chrome** (app-layer doc §9, the finding that *failed* on contact with code). The kernel surface registry is **finite (24 rows), closed-union, kernel-owned** (`web/types/desk.ts::KernelSurfaceSlug`, CI-parsed). An app can **never** get a `register: application` slot — that reopens a closed taxonomy to admit an unbounded set.

So:

- **Shared into the commons: yes, structurally.** An app is a principal with a grant. It is "shared" the same way a member or a connected AI is shared — it appears on the **roster** (`WorkspaceMembersCard`), the roster *is* the app manager (`ensure_principal_grant` / `narrow_grant` / `evict_principal`), and its access is the two-axis powerbox scope. This is the ADR-414 D5 program-as-hire move, reused.
- **As a dedicated kernel surface: no, never.** There is no video-editor tab. An app **launches** (redirect + scoped token, its own window) — Finder's "Open With" opens the app's window, not a Finder window. Side-by-side is *open Files beside Chat and drag* — yarnnn already has a real window manager (ADR-297 D15); nesting a second pane inside a surface is building a second window manager inside the first (app-layer doc §8, Appendix B).

> **A "shared video editor" is a contractor with a scoped key, not a folder in your workspace.** `promo.mp4` → Open With → a minted, expiring capability to *that one blob* → the editor runs on its own infra → its edits return as `app:{id}`-attributed revisions that settle next to everyone else's work. That is the macOS model done exactly right, and it is why the **powerbox — not a surface, not a runtime — was the whole unlock.**

---

## 8. The recommendation, and what it is NOT

Given the operator's frame ("complete the OS picture, not launch scope"):

- **You are not missing "apps." You are missing ADR-427 Phase 2/3 (binary Category-1 + the minted serving capability) — that is it, for architectural completeness.** With those, plus the type table and the two-axis gate you already have, the OS is *architecturally* complete for a housed third-party editor. The app-principal ABI is real but correctly **last**, and correctly **discovered**.
- **The right first-party build is not an editor — it is the read-only reference viewer against the ADR-427 seam** (a media viewer that round-trips a real, versioned blob). It exercises primitives #1 and #4-serving and hands you the app-principal's requirements as a dividend. It runs under the operator's own grant, so it adds *zero* grant machinery.
- **The first-party ratchet should currently fail, on purpose** (app-layer doc §12). `resolveViewerApplication` returns a closed union; `FileBody` static-imports; a third party cannot replace them. **That is ESSENCE v15's positioning, already ratified** — Claude Artifacts fails the same test. Read the ratchet as *"when a third party asks,"* not *"before the viewer."* ADR-434 made the pre-app refactor a **one-file** fact (`FileBody`), not a diffuse one.

What this document does **not** do:

- **Does not write the app-principal ADR or the public-ABI ADR.** The demand gate holds (ADR-380 §5; app-layer doc §11). This doc completes the *map* so the gate is decidable; it does not open it.
- **Does not build the minted capability.** It names it (§3), points at its spec (ADR-427 D4), and places it in the order (§6). It is ADR-427 Phase 3's, coupled to out-of-band blob serving.
- **Does not build an editor, first- or third-party.** It argues the *viewer* comes first (§6) and the editor is the second app.
- **Does not reopen positioning.** ESSENCE v15's host-elsewhere lead stands (ADR-427 §11). yarnnn-as-OS is the architecture beneath the lead, not a new pitch (commons-is-the-OS §7).
- **Does not add a launcher row or a surface.** Apps add zero surfaces (§7; app-layer doc §9).
- **Does not resolve which editor (first- vs third-party) yarnnn should reach for as a product bet.** It resolves the *architecture* of each and the order they'd arrive; the product call is the operator's, and it is not on the launch critical path.

---

## 9. The one-line statement

**After the powerbox (ADR-434), three of the four OS primitives are complete and the fourth is complete on authorization — so "internalizing apps" is not a platform to design but a fixed sequence to walk: binary as a Category-1 blob and a minted, expiring, object-scoped serving capability (ADR-427 Phase 2/3), then a read-only reference viewer that rehearses them under the operator's own grant, and only then — discovered, not designed — the app-principal grant class that lets a stranger's editor be a first-class contractor in the commons; an app is shared like a contractor, never like a folder, and it adds no surface at all.**

---

## Appendix A — receipts index

| Claim | Receipt |
|---|---|
| The moat is "system of record where human and AI work settles" | `docs/ESSENCE.md:9` (v15, ADR-414 D1) |
| Powerbox authorization shipped: two-axis, arbitrary-depth, three-state | ADR-434 (Accepted + Implemented 2026-07-10) · `path_under_scopes` (`workspace.py:2013`) · migrations 211/212 |
| The three prior gaps (no read gate / `[]` fails open / object-scoping impossible) are closed | ADR-434 §1–§2 · supersedes `the-powerbox-scope-audit-*` Half-A/Half-B seam |
| A read-only, object-scoped principal is now representable | ADR-434 D1 (`read: operation/`, `write: []`) |
| The minted capability is deferred, spec'd, coupled to Phase 3 | ADR-434 "Deferred" § · ADR-427 D4 |
| "A cached capability is a leaked capability" | ADR-427 D4 |
| Binary is text-only today; Phase 1 seam shipped | ADR-427 §2 · `8c91018` · `services/storage_backend.py` |
| `FileBody` renders `BlobMissing` for a versioned `.mp4` | app-layer doc §7 · `web/components/workspace/FileBody.tsx` |
| `role` is a CHECK enum of six; no `'app'`; falls through to `agent` | `189_adr373_multi_principal_rekey.sql:64` · `primitives/workspace.py` |
| An app is not a surface; the registry is finite/closed | app-layer doc §9 · `web/types/desk.ts::KernelSurfaceSlug` |
| The roster is the app manager | `principal_grants.py` (`ensure_principal_grant`/`narrow_grant`/`evict_principal`) · `WorkspaceMembersCard.tsx` |
| The read-only viewer runs under the operator's grant, zero new grant machinery | app-layer doc §11 |
| The pre-app refactor is now a one-file fact | app-layer doc §12 · `FileBody.tsx` |
| yarnnn's shipped Preview.app = the one viewer, two mounts | `FileBody.tsx` + `chat-surface/ArtifactCard.tsx` · app-layer doc §7-8 |
| Fifth primitive (attributed revision) is the only novelty spend | ADR-427 §6 (the four-primitive frame) · ADR-209 |
| App layer deferred, demand-gated | ADR-380 §5 · ADR-382 precedent · app-layer doc §11 |
| The OpenDoc/OLE/Bonobo/KParts graveyard; never a component ABI | app-layer doc Appendix C |

## Appendix B — the fork, as a decision table for later

When the app product bet is actually made (not on the launch critical path), this is the table to bring:

| Question | First-party editor | Third-party editor |
|---|---|---|
| Who writes it | yarnnn | a stranger |
| Where it runs | in-shell (static import) | its own infra (redirect + token) |
| Grant machinery | none (operator's grant) | `role='app'` + launch verb + minted capability |
| Novelty spend | on a commodity editor | on primitive #5 only |
| Risk | feature race (worse Figma) | none to the moat — it *deepens* the commons |
| When justified | only as a reference app that exercises missing machinery | when a third party asks (demand gate) |
| Blocks on | ADR-427 Phase 2 (for media) | ADR-427 Phase 2/3 + the app-principal ADR |
| Correct first move | the **read-only** reference viewer, not an editor | discovered *by* the read-only viewer, designed after |
