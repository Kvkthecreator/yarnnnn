# The Viewer, the Desktop, and the App Layer

*One viewer, two mounts. Generation is rented. Third-party apps stay deferred.*

> **Status**: Analysis (2026-07-09, **rewritten in place** the same day). Doc-first, receipts-backed. **No ADR rides this document.** The demand gate on the app-principal ADR and the public app ABI holds (ADR-380 §5 / ADR-382 precedent); §11 names the pressure that would open it.
> **Code that rode the rewrite**: the §7 consolidation and the §8 chat artifact card shipped in the same session under this document's §12 discipline — a bounded FE + one-field-backend change, no schema, no migration, no Render-service parity impact. Everything downstream of §11 remains unbuilt.
> **Authors**: KVK, Claude
> **Hat**: A (system canon). Vocabulary: operator, member, principal, substrate, grant, mirror, composition, Freddie.
> **Method**: the four-primitive frame (ADR-427's adopted lens) pressed against live code @ `8895821`. Every load-bearing claim carries a `file:line`.
> **Positioning**: unchanged. ESSENCE v15's host-elsewhere lead stands (ADR-427 §11). yarnnn-as-OS is an internal architecture truth.

---

## 1. The correction this document exists to record

The first draft answered a **platform** question — *"can a stranger ship a Final Cut into yarnnn?"* — with the four macOS primitives, an app-principal grant class, an origin-derived type namespace, a conformance DAG, and an RFC-9396 powerbox. All of that is correct, and all of it is **deferred**.

The question actually in front of us was a **product** question: *"when a lane makes something, can the member see it and change it?"*

Those are different questions with different answers, and conflating them made the second look far harder than it is.

**The plain reading of the platform, stated once:**

| | Generation | Viewing / editing | Third-party apps |
|---|---|---|---|
| **Who owns it** | rented (ADR-417/420) | **first-party, closed set** | nobody yet |
| **The precedent** | Sora, Veo, an image model reached through the member's own connector | **Claude Artifacts / ChatGPT Canvas** | macOS LaunchServices |
| **The mechanism** | ADR-420 D1 connector-first; yarnnn builds no async-job driver | a hardcoded type→renderer switch | manifest + principal + powerbox |
| **Status** | ratified, connector half demand-gated | **shipped, §7–§8** | **deferred, §11** |

**Claude Artifacts is not an app platform.** Anthropic ships a fixed set of renderers — markdown, HTML, React, SVG, mermaid, code — and *nobody else can add one*. Canvas is the same. Neither has a manifest, a principal, or a capability model. Both are exactly the hardcoded kind-switch that `ContentViewer` already was.

**So the app layer was never on the critical path for anything the operator can feel.** What was on the critical path was a `.mp4` rendering as text and a lane that told you it had called `WriteFile` without telling you what it wrote.

---

## 2. The two findings that survive contact with live code

The first draft carried ten inherited findings. Two were load-bearing, and one of them **failed**.

### F2 — "the members roster is already the app manager." **Survives, amended twice.**

Installing an app really is writing a `principal_grants` row. `ensure_principal_grant` / `narrow_grant` / `evict_principal` (`api/services/principal_grants.py:200,313,348`), the operator verbs `POST /api/workspace/members/{principal_id}/{narrow,revoke}` (`routes/workspace.py:1167,1190`), the role-grouped roster (`WorkspaceMembersCard.tsx:429-434`), and `resolve_principal_id`'s own docstring: *"a new principal type needs a mapping entry HERE and a grant row — no gate change"* (`services/supabase.py:207-208`). That is the ADR-414 D5 program-as-hire move, reused.

**Amendment 1** (cheap): `principal_grants.role` is a CHECK-constrained enum of six (`189_adr373:63-64`) — `'app'` is a migration; `_caller_class` has no `app` branch, so an `app:` caller falls through to `agent` (`primitives/workspace.py:1861-1862`), which is **write-capable on `operation/`**.

**Amendment 2** (structural): **the roster cannot express the powerbox.** See §10.

### F7 — "apps are mirrors, not compositions." **FAILS.**

Mirrors and compositions are both **kernel surface registry rows**. `api/services/kernel_surfaces.py` declares exactly **24**. `web/types/desk.ts::KernelSurfaceSlug` is a **closed TypeScript union** — and the ADR-297 parity gate literally parses it up to the first semicolon (`desk.ts:34-36`). `SurfaceRegistry.tsx` maps slug → component with **static imports**.

A surface is finite, named, kernel-owned, route-bearing. An open document is instance-shaped and unbounded: `resolveViewerApplication(path, contentType)` returns a **kind**, never a slug.

DP29's "mirror once" is a claim about **concerns**, which are countable. If every opened file were a mirror, the count would be unbounded and the principle vacuous.

> **Apps are not a third surface class. They are not surfaces at all.** They are processes; the document window is their chrome. DP29 partitions the *launcher*. The type table dispatches *documents*. Two registries, two kinds — §9.

And a corollary premise fails with it: the app layer and the ADR-340 §9 launcher thread were **never the same thread**. §9(a) is *closed* (ADR-349, Implemented 2026-06-19, says so in its own status line). §9(b) is *deferred by name* (ADR-414 §9b). Apps add **zero launcher rows** — §9.

---

## 3. The spine

> **Generation is rented. Viewing and editing are ours, first-party and closed. Mutation goes through chat. One resolver, three tiers. One viewer, two mounts. Third-party apps are deferred until someone asks.**

Six clauses, each with an owner in canon:

| Clause | Owner | Status |
|---|---|---|
| Generation is rented | ADR-417, ADR-420 D1 | ratified; connector half demand-gated |
| The viewer is first-party and closed | this doc §7 | shipped |
| Mutation goes through chat, never inline | ADR-236 | shipped 2026-04-30 |
| One resolver, three tiers | this doc §6 | shipped |
| One viewer, two mounts | this doc §7–§8 | shipped |
| Third-party apps deferred | ADR-380 §5, ADR-382 precedent | gate holds, §11 |

Plus a seventh, running the other way: **`ui://` is the outbound mount** — §13.

---

## 4. Generation is rented, and ADR-420 already said so

ADR-420 D1 (Accepted 2026-07-08), verbatim:

> *"The purest form of 'rented' (ADR-417) is not **yarnnn rents the engine and resells it through a driver it maintains** (engine breadth) — it is **the member rents the engine directly and yarnnn never touches the async-job driver at all** (connector breadth)."*

The member attaches the platform's MCP connector under their own key; the lane composes it into its tool surface at turn time. yarnnn integrates nothing engine-specific. ADR-413 D5.1's reserved async-job driver **may never come due.** (Higgsfield was specifically *retracted* from the seed list — "a competing commons, not a dumb peripheral." The moat-leak test governs which platforms are safe to connect at all.)

The one thing yarnnn must own is **ADR-420 D2 step 4**:

> *"The lane takes the connector's result (a video URL, an image) and writes it to a workspace file through WriteFile — attributed `member:{id} via {model}`."*

That step wrote a cheque yarnnn cannot yet fully cash: a `.mp4` through `WriteFile` has nowhere true to land — binary is an unversioned `content_url` sidecar outside Category 1. **ADR-427 Phase 2 is what cashes it.**

**But the cheque is not all-or-nothing.** For `.md` / `.html` / `.png` / `.pdf` — everything the viewer already renders — a lane writing `report.html` shows a rendered card **today**, and does. The binary dependency softens to: *video and audio wait; everything else does not.*

---

## 5. What was actually there — four dispatch tables that didn't know about each other

| # | Table | Dispatches on | Entry | Consumers (before) |
|---|---|---|---|---|
| 1 | `resolveViewerApplication` | file **type** | `web/lib/file-types/index.ts` | `ContentViewer` only |
| 2 | `CONTENT_SHAPES` / `shapeForPath` | file **path** (glob) | `web/lib/content-shapes/index.ts:132` | **zero — dead code** |
| 3 | `LIBRARY_COMPONENTS` / `dispatchComponent` | SURFACES.yaml `kind` | `web/components/library/registry.tsx` | Home program_sections, MiddleResolver |
| 4 | `SurfaceRegistry` | kernel surface slug | `web/components/shell/SurfaceRegistry.tsx` | `SurfaceViewport` |

Plus `MiddleResolver`, a fifth micro-resolver whose own docstring calls `DeliverableMiddle` *"the universal viewer"*. A different universal viewer.

**And two chat renderers sharing nothing but `MarkdownRenderer`:**

- **`tp/`** — the steward rail. `MessageDispatch` (four shapes, ADR-272) → `MessageBlocks` / `InlineToolCall` (20+ tool icons) → `ToolResultCard` → `ProposalCard`. `MessageBlock.tool_call` carries `{id, tool, input, status, result}` (`desk.ts:189`).
- **`chat-surface/LanePanel`** — 262 lines. Assistant text rendered as `whitespace-pre-wrap`, not markdown. Tool calls rendered as a **joined string of names in a footer**.

And the backend gave it nothing more: `lane_runner.py` yielded `("tool", {"name": name})`. **Name only.**

> **The lane — the exact surface where ADR-420 D2.4 says a generated artifact arrives — had the weakest renderer in the codebase.** A lane that wrote an image produced: `gemini-2.5-pro · WriteFile…`

That is backwards, and it is the whole finding.

---

## 6. The conformance fallback chain, specified (Q4, resolved)

The old table was a flat first-match extension switch with no chain. Two observations:

- The terminal `return 'text'` is **unconditional**. An unknown type always resolves to *something* — the escape hatch that makes an open type system safe. ADR-245's L1 raw view, in code, before the table it falls through.
- But `video/x-matroska` returned `'text'` and **painted 25 MB of bytes as text**. There was no `video/*` node, and `download` was a hardcoded four-extension allowlist rather than a terminal.

**The chain, as shipped:**

```
derived type  (ADR-427 D5: path extension + magic bytes)
  │
  ├─ tier 1  path-exact    → a bespoke renderer for one known path
  │                          (today: the IDENTITY inference view)
  │
  ├─ tier 2  type-exact    → markdown · html · image · video · audio · pdf · csv
  │
  └─ tier 3  terminal, DERIVED from text-ness (never enumerated):
         text/* or a structured-text type   →  `text`      (the L1 raw view)
         otherwise                          →  `download`  (the binary terminal)
```

Two corrections this forced, both now landed in `web/lib/file-types/index.ts`:

1. **`download` is the binary terminal** — `public.data ∧ ¬text/*` — computed from `isTextualContentType()`, not from an extension allowlist.
2. **The `text` leaf asserts text-ness before rendering.** That assertion is precisely ADR-427 §8's read-side classification requirement, arriving at the frontend. **The §8 `.content`-reader ratchet and the conformance chain are the same work**, approached from two ends.

And the mapping to ADR-245 is sharper than the first draft claimed. L3 is not "structured affordances" as a separate axis — **L3 is an association matched at the exact type; L2 is an association matched at an ancestor; L1 is the terminal.** ADR-245's three layers *are* the DAG's depth strata. The kernel named a hierarchy it had already shipped, one level down.

*(A note on discipline: `content-shapes/shapeForPath` — a real path-glob resolver — has **zero consumers**. Tier 1 is today a hardcoded `IDENTITY_PATH` const inside the viewer. That seam is named in the `file-types` header and deliberately left alone: a path→component table is invention, and nothing yet demands it.)*

---

## 7. One viewer, two mounts (shipped)

`ContentViewer` was 808 lines mixing a folder listing, a header, a delete verb, a context menu, and — buried at the bottom — the kind-switch and the blob previews. Five consumers mounted it (`files/page`, `RecentsView`, `FileContextMenu`, `InferenceContentView`, itself). **All Files-adjacent. Zero on the chat side.**

So the universal viewer already existed and was already shared. It simply could not be reached from the surface where artifacts arrive.

**`web/components/workspace/FileBody.tsx`** now holds the body: the kind-switch, `useSignedBlobUrl`, the image/video/audio/PDF previews, the CSV table, the raw view, the binary terminal, and `FileActions`. `ContentViewer` (566 lines, −242) keeps the **document chrome** and mounts it.

Two mounts, one dispatch:

1. **The document chrome** — Files / Recents / Context. Header (name, derived type, `Last edited by …` off the ADR-209 head revision) + `<FileBody file={file} />`.
2. **The artifact card** — `chat-surface/ArtifactCard`. A bounded frame + `<FileBody file={file} compact />`.

`compact` is a **display hint, not a different renderer** — it trims intrinsic heights so the body sits inside a card. Same tree, same dispatch. A third mount wraps this component; it does not fork it.

**Two things landed with the extraction and deserve naming:**

- **`BlobMissing`.** A type that resolved to a blob-backed viewer with no blob now says *"This video has no stored bytes yet"* rather than painting an empty player. That is the honest state for a versioned `.mp4` **until ADR-427 Phase 2** — and it is strictly better than the prior behavior, which resolved the same file to `text` and painted its bytes.
- **`sandbox=""` on the HTML iframe.** The document chrome rendered agent-authored HTML via `srcDoc` with no sandbox — same-origin, scripts enabled. That was survivable while the only mount was a full-window Files view the operator had navigated to deliberately. It is **not** survivable once the same component renders inline in a chat transcript. The new mount forced the fix. Compose output (`services/compose/engine.py`) is static HTML + CSS, so nothing regresses.

---

## 8. The chat surface, specifically (shipped)

Three changes, in dependency order.

**(a) The stream carries the path.** `lane_runner.artifact_path_from(name, result)` is a pure function gated on the **write verbs** (`WriteFile`, `EditFile`) and on `result["success"]`. It reads the path from the primitive's **result**, never from the model's arguments — because `handle_write_file` normalizes (`/workspace/…` and `workspace/…` prefixes stripped, then re-absolutized, `workspace.py:770-773,823`) and the result carries the one canonical form the Files surface deep-links on.

The gate is on the verb, not on the result's shape, because `ReadFile` / `ListFiles` / `SearchFiles` also return a `path`. **A card for a read would be a lie about what the lane did to the commons.**

New SSE frame: `{"artifact": {"path", "verb"}}`, emitted *after* execution, success only. `{"done": …}` carries the authoritative `artifacts` list. Both land in `session_messages.metadata`, so **a reloaded lane keeps its cards.**

**(b) The card.** `ArtifactCard` fetches the file, renders `FileBody` bounded at 360px with a gradient fade, and offers *Show more* + **Open in Files** (a `SurfaceLink to="files" params={{path}}` — the sanctioned cross-surface jump through the window manager).

It **renders and opens. It never edits.** ADR-236 deleted `SubstrateEditor` and made chat the canonical mutation surface. That is the Artifacts model, not the Canvas model, and it was a ratified decision four surfaces ago.

It also *reinforces* the ADR-411 lane contract rather than violating it. The lane's promise is: *the transcript is private; the work lands in files.* The card is a **pointer to that file, carrying its attribution**. It is the contract, rendered.

**(c) The lane finally renders markdown.** Assistant replies were `whitespace-pre-wrap` for no reason other than that `LanePanel` was a reimplementation of a subset of `ConversationPanel`.

**Layout, and what we deliberately did not build.**

- The card sits **outside** the assistant bubble, at row width. A bubble is `max-w-[85%]`; a rendered document is not speech and does not belong in a speech container.
- A tool-only turn shows **only the card** — no `[no reply]` bubble above it, because the card *is* the reply.
- The artifact appears **mid-turn**, the moment the write lands, before the model finishes narrating it.
- **No side pane.** Claude Artifacts splits chat-left / artifact-right. yarnnn already has a real window manager (ADR-297 D15: `windowStates`, absolute-positioned z-stacked windows, `toggleMaximize`, `desktopBounds`). Side-by-side is *open Files beside Chat and drag*. Nesting a second pane inside the chat window would be **building a second window manager inside the first** — the one thing the prior-art survey says never to do (Appendix B).

---

## 9. Two registries, one shell (Q5, resolved)

They are different **kinds**, and must not merge:

| | Kernel surfaces | Type → viewer associations |
|---|---|---|
| Cardinality | **finite** (24 rows) | **open** |
| Owner | kernel | (one day) third parties |
| Extension cost | migration + closed-union edit + static import | **must be zero kernel change** |
| Names | a substrate concern (mirror) or an operator act (composition) | a document instance |

**An app does not get a `register: application` slot.** The register enum is a taxonomy of *kernel surfaces*, and ADR-340 D4 already retired registers as the user-facing sort key. Handing apps a register reopens it *and* requires a closed union to admit an unbounded set.

What the two share is exactly one thing: **a launch verb.** Per deployment shape:

- **in-shell** — mount a component. Only yarnnn can ship these. **Therefore this shape is a performance optimization, never a capability.**
- **redirect** — hand off to another origin with a scoped token. **No surface slot, no `DeskState` window.** The macOS model; the only shape in which a third party can exist.
- **local** — nothing. The file is on the disk.

> **"Open With" is a launch, and a launch is not navigation.** Navigation is `foregroundSurface(slug)` inside `DeskState`. A launch hands off. Finder's "Open With" does not open a Finder window.

**And the launcher census is healthy and contains zero apps.** Live at-rest tiers, parsed from `kernel_surfaces.py` @ `8895821`: `primary` = **home · chat · files**; three settings doors (`settings`, `workspace-settings`, `system-agent`); everything else `search-only`. **Six top-level, below ADR-340 D5's ~7 target.** The re-sort didn't just close — it overshot.

The `search-only` residue does not decompose the way F7 predicted: `activity` and `queue` are mirrors, `notifications` is a composition fronted by the bell, `agents` is a roster, `setup` is a Sequence. **None is an app.**

> **A drift note worth keeping.** ADR-340 D5's own reconciliation banner (written 2026-06-25) names the primary tier as *Home · Context · Notifications · Files · Agents*. **Four of those five have since moved** — `context`/`channels` dissolved (ADR-415), `notifications` demoted, `agents` demoted, `chat` added (ADR-412 D3). CLAUDE.md is stale on the same fact. The session brief warned that *CLAUDE.md* drifts from code; true — and **the ADR annotation layer is now drifting too.** The only reliable receipt is the registry file, the TS union, and the migration.

---

## 10. The two grants — and the live gap that has nothing to do with apps

This is F2's amendment 2, and it is the most actionable thing in the analysis.

macOS has **two** capability facts, in different places:

1. **The install fact** — `/Applications/FinalCut.app` exists; LaunchServices knows its types. Durable, system-wide.
2. **The open fact** — the user picked `holiday.mov`; the app holds a **security-scoped bookmark** to that one object. Ephemeral, per-user, per-object, expiring.

Confusing them is how you get ambient authority. **yarnnn has only the first**, and calls it `principal_grants`.

The open-grant does not exist. ADR-427 D4 specifies it precisely and builds nothing: *"a per-request, per-principal, TTL'd response field, minted at read time from `(blob_sha, principal, active grant)`… a cached capability is a leaked capability."*

They are not substitutable, and the failure mode of pretending otherwise is concrete:

- `_grant_root_set` (`primitives/workspace.py:1939-1946`) does `s.rstrip("/") + "/"`. A scope of `operation/reports/q3.md` becomes `operation/reports/q3.md/`, which never prefix-matches the file. **Object-scoping through `scopes` is mechanically impossible, silently.**
- **There is no read gate.** `_is_path_locked_for_principal` is called from exactly two sites, both in the *write* branch of `primitives/permission.py` (`:270`, `:364`). A principal with *any* active grant reads the entire workspace.
- `if raw:` (`primitives/workspace.py:1996`) collapses `[]` and `NULL` to the same fallback. **The empty scopes list — the only way to say "this principal writes nothing" — resolves to the class default**, which for `agent` permits `operation/`, `agents/`, `working/`, `uploads/`.

> **Therefore: a read-only viewer principal is not representable today. And the reason is not that apps are missing — it is that the grant model has no read axis and its write axis has an undefined empty-set polarity.**

This is **live**, right now, for the seven `foreign-llm` principals holding grants (ADR-386 backfill receipt, 2026-06-30; two of them provider-collapsed by ADR-373 D2.a): **narrowing Claude restricts its writes and not its reads.**

The commons will force the powerbox before any app does. **The minted-capability work is not blocked on apps and should not wait for them.**

---

## 11. The demand gate holds — and what would open it

**No app-principal ADR. No public-ABI ADR.** ADR-380 §5 / ADR-382's build-when-demanded discipline applies. Three triggers, and the third was found in the code:

1. **The first third-party request** — an actual developer asking to write into a workspace. The shape is now on paper (§9, §10, Appendix A) so the conversation starts from a position.
2. **The first-party reference viewer hitting a wall** — concretely, **the moment a second app claims the same derived type.** One viewer per type needs no manifest, no registration, no association table. Two viewers need all of it. That is the precise falsification boundary, and it is cheap to watch for.
3. **[found this session, live] The moment any non-operator principal must not see the whole commons.** §10.

**The hard ordering constraint holds, and the code says why.** ADR-427 §10 phase 5 prescribes a *read-only viewer of a type you do not author* as the first reference app. In grant terms: **it needs no app-principal at all** — it runs under the operator's own grant, in-shell, and exercises type declaration + the fallback chain + the range read + the launch verb while exercising **zero new grant machinery**. That is exactly right, because §10 established that the grant machinery is the part we understand least. **The powerbox's requirements should be discovered by the second app (the editor), not designed in advance by the first.**

A viewer built before ADR-427 Phase 3 would read `file.content_url` — **a stored column ADR-427 D4 deletes** (blast radius: 11 non-test files). Note that `FileBody.useSignedBlobUrl` is now the *single FE site* that consumes it, so the retirement lands there and nowhere else. That consolidation was free, and it was not the point of the exercise; it is a dividend of "one viewer."

**Order:** ADR-427 Phases 1–3 → a read-only viewer against the seam → the app-principal ADR, informed by whatever the viewer had to reach around.

---

## 12. First-party discipline — the ratchet we should currently choose to fail

ADR-427 §10 phase 5's CI-enforceable test:

> *Can your own viewer be deleted and replaced by a third party's, with no kernel change?*
> **Yes → OS. No → product.**

**Today the answer is no, three times over:**

1. `resolveViewerApplication` returns a **closed TS union** of nine kinds. A third party cannot produce a value of that type.
2. `FileBody` switches on that kind with static imports. There is no indirection an association could point elsewhere.
3. `SurfaceRegistry` static-imports every surface. *(This one is correct — surfaces are finite and kernel-owned, §9.)*

**And that is fine.** Claude Artifacts fails this test. Canvas fails this test. **Failing it is not a defect; it is ESSENCE v15's positioning, already ratified.** Read §10 phase 5 as *"when a third party asks,"* not *"before the viewer."*

What the consolidation bought is that failing it is now a **one-file** fact rather than a diffuse one. The minimal pre-app refactor that flips the answer — whenever someone asks — is:

- `ViewerApplication` stops being a closed union of *kinds* and becomes an opaque **app id**;
- `FileBody`'s switch becomes a lookup in a **mutable app table**, seeded with the nine kernel defaults;
- the nine seeds become **ordinary rows**, indistinguishable from a third party's.

Small, safe, and now confined to one component. **It is the honest first line of the future ABI — and the one change that turns the ratchet from an aspiration into a test that can run red.**

---

## 13. The outbound mount — `ui://`, and why it runs the other way

If "an artifact viewer for Claude, ChatGPT" means *yarnnn's artifacts rendering inside their chats*, that is **MCP Apps** (`ui://` + `_meta.ui.resourceUri` + sandboxed iframe + JSON-RPC over postMessage), standardized 2026-01-26, live in Claude, ChatGPT, VS Code, Goose. yarnnn already ships `ui://` widgets for `trace` / `recall` / `remember` (ADR-372; `api/mcp_server/presentation/`).

**One renderer, two mounts — and then a third.** The Files chrome, the chat artifact card, and the foreign host.

This is the host-elsewhere lead applied to artifacts, and it runs in the **opposite direction** from everything §9–§11 worry about. MCP Apps is a **host-owned component ABI** — the OLE / OpenDoc / Bonobo / KParts lineage, all of which died. It cannot be how a third party ships an editor *into* yarnnn. It is how yarnnn's widgets reach *out*. The two coexist and never meet.

*(Standing follow-on, untouched here: ADR-427 §11's note that ADR-379's per-host widget gating may now be collapsible, since ChatGPT and Claude no longer diverge. And AG-UI as an agent↔UI event-stream standard, worth an evaluation against ADR-411 lanes. Both named, neither urgent.)*

---

## 14. What this document does NOT do

- **Does not write the app-principal ADR or the public-ABI ADR.** The gate holds (§11).
- **Does not build the powerbox.** It names it (§10), and names the door it will arrive through, which is not the app door.
- **Does not touch ADR-427's phases.** Phase 2 remains the unlock for video and audio; §7's `BlobMissing` is the honest state until then.
- **Does not reopen positioning.** ESSENCE v15's lead stands (ADR-427 §11).
- **Does not resolve Home** (ADR-414 §9b's deferral holds) and does not re-open the launcher IA (ADR-349 closed it; §9 records the drift without acting on it).
- **Does not wire `shapeForPath`.** Tier 1 stays a hardcoded const with a named seam (§6). A path→component table is invention until something demands it.
- **Does not converge the two chat renderers.** `LanePanel` keeps its own light body; `tp/InlineToolCall` keeps the steward's. ADR-411's "a lane is a working thread, not the OS terminal" is a deliberate simplicity, and the artifact card did not require breaking it. *Named as the next candidate if a second duplication appears.*
- **Does not define** the project format, a widget ABI, a merge algorithm, a UI framework, or how sub-components compose into an artifact. *That absence is the platform.*

---

## 15. The one-line statement

**Generation is rented, viewing is ours, mutation goes through chat — so the whole of "internalizing video, image, and the rest" is one type table, one viewer, two mounts, and a `blob_sha` that ADR-427 Phase 2 will provide; the app layer is a different, later, third-party question that adds no surfaces and blocks nothing.**

---

## Appendix A — receipts index

| Claim | Receipt |
|---|---|
| Generation is rented; connector-first | ADR-420 D1 (Accepted 2026-07-08) · ADR-417 |
| The artifact lands as an attributed revision | ADR-420 D2 step 4 |
| Chat is the canonical mutation surface; inline edit deleted | ADR-236 · `ContentViewer.tsx` ADR-236 comment block |
| The old table had no video node; `.mp4` → `text` | pre-change `web/lib/file-types/index.ts:88` (`return 'text'`) |
| `download` was an xlsx allowlist, not a terminal | pre-change `file-types/index.ts:80-87` |
| The terminal is now derived from text-ness | `file-types/index.ts::isTextualContentType` |
| `ContentViewer` was the only mount of the viewer | 5 consumers, all Files-adjacent (`files/page`, `RecentsView`, `FileContextMenu`, `InferenceContentView`) |
| The lane emitted tool NAME only | pre-change `lane_runner.py:477` — `yield ("tool", {"name": name})` |
| The steward rail carries `{id, tool, input, status, result}` | `web/types/desk.ts:189` |
| `LanePanel` rendered assistant text as raw | pre-change `LanePanel.tsx:200` — `whitespace-pre-wrap` |
| WriteFile's result carries the canonical absolute path | `primitives/workspace.py:770-773, 823` |
| Read verbs also return a `path` (hence the verb gate) | `handle_read_file` result shape |
| Surfaces are finite + kernel-owned (24 rows) | `api/services/kernel_surfaces.py` |
| `KernelSurfaceSlug` is a closed union, CI-parsed | `web/types/desk.ts:34-36` |
| `SurfaceRegistry` static-imports every surface | `web/components/shell/SurfaceRegistry.tsx` |
| Live primary tier is home · chat · files | `kernel_surfaces.py` @ `8895821` |
| Launcher re-sort CLOSED, not open | ADR-349 status line; ADR-340 D5 reconciliation banner |
| Real window manager exists (side-by-side is free) | ADR-297 D15 · `SurfaceViewport.tsx` · `surface-preferences.ts::windowStates` |
| Install = a grant row; the roster is the app manager | `principal_grants.py:200,313,348` · `routes/workspace.py:1167,1190` |
| "A new principal type needs a mapping entry HERE and a grant row" | `services/supabase.py:207-208` |
| `role` is a CHECK-constrained enum of six | `189_adr373_multi_principal_rekey.sql:63-64` |
| Unknown caller class defaults to `agent` (write-capable) | `primitives/workspace.py:1861-1862` · `workspace_paths.py::CALLER_WRITE_POLICY` |
| Grant `scopes` are write-region root prefixes; object-scoping impossible | `primitives/workspace.py:1939-1946` |
| **No read gate anywhere** | `primitives/permission.py:270,364` (write branch only) |
| **`scopes: []` fails open to the class default** | `primitives/workspace.py:1996` (`if raw:`) |
| `content_url` is a minted capability, to be deleted as a column | ADR-427 D4 |
| `useSignedBlobUrl` is now its single FE consumer | `web/components/workspace/FileBody.tsx` |
| `ui://` widgets already ship | ADR-372 · `api/mcp_server/presentation/` |
| Compose emits static HTML (so `sandbox=""` regresses nothing) | `api/services/compose/engine.py` |

## Appendix B — prior art, and why there is no library

Type→viewer dispatch exists in five mature systems and has **never** been extracted as a standalone library:

- **JupyterLab** — `DocumentRegistry` (type → widget factory) + `IRenderMimeRegistry` (mimetype → renderer, **rank-ordered**), on **Lumino**, a dock-panel window manager with persisted layout. An exact structural match for `resolveViewerApplication` + `useSurfacePreferences` + the register split. yarnnn independently rediscovered it.
- **Theia** — `OpenerService.getOpener(uri)` → highest-priority `OpenHandler`. "Open With" as a DI service.
- **VS Code** — `contributes.customEditors`: `filenamePattern` + `priority`.
- **Emacs** — `auto-mode-alist`. The cleanest statement of the idea.
- **GIO** — `g_app_info_get_default_for_type`.

**Why no library exists:** LiteLLM extracts because a model call is stateless and the contract is one function. Surface resolution cannot, because **the result of resolution is a live widget bound to the host's frame** — you cannot ship a dispatcher without shipping the window manager.

**What *is* portable in all five is the declaration, not the dispatcher.** `shared-mime-info` is a data file. `contributes.customEditors` is JSON. `SURFACES.yaml` (ADR-223) is already yarnnn's `contributes.*`; the compositor is already its `OpenerService`. **There was never a library to import.**

Corollary, and the reason §8 refuses a side pane: **if yarnnn ever needs a real in-shell multi-document frame, use Lumino or Theia. Never build a window manager.** It already has one.

## Appendix C — the graveyard

Every attempt to standardize *"an artifact composed of third-party sub-components against a shared ABI"* is dead: **OpenDoc, OLE compound documents, Bonobo, KParts.** The living descendants are thin (Block Protocol 0.4; MCP Apps). What survives is **file-format standards + a capability model + type association.** Never a component ABI.

yarnnn must never define: the project format · a widget ABI · a merge algorithm · a UI framework · how sub-components compose into an artifact.

The novelty budget is spent on exactly one primitive that no OS has: **the attributed revision.** `trace` falls out for free. Everything else — the type system, the data plane, the powerbox, the association table — is a boring decade-old standard.
