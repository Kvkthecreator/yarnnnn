# ADR-570: The markdown editor — the member's cursor reaches the prose currency

> **Status**: **Accepted + Implemented, HOUSING SUPERSEDED by
> [ADR-571](ADR-571-the-text-app-a-dedicated-surface-for-the-prose-currency.md)**
> (2026-08-14 — drafted from the connector round-trip session's scoping; ratified
> same day by the operator, who delegated implementation. Stages 1–3 landed
> `17fe1bf` · `7f22e7d` · `daa77c3`).
>
> ⚠️ **Read D1/D2 as history, not as current design.** The operator's correction
> the next day — *"my understanding was that it is a dedicated app. just like
> docs"* — re-cut the housing: prose edits in the **Text app** (a kernel surface
> with a bound **Editor** lane), not in an inline `markdown.editor` app inside
> Files. That registry row, its module, and its selection plumbing are DELETED
> (`fe62786`). **Everything below the housing CARRIES unchanged and is still
> current**: D4's member write door widened by format class, the studio door's
> principal-gate repair, D5's CAS/409 spine (now inside the Text canvas), and
> D6's chat-seam linkification. ADR-571 §1 records why the two come apart —
> the ADR-550→551 shape: a mechanism can be live and still be housed wrong.
> **Date**: 2026-08-14
> **Dimension**: **Channel** (a new app on the file-type registry + one widened write
> door) primary; **Substrate** (no new file class — the prose currency as it stands)
> secondary.
> **Relates to**: ADR-456 D1 (this ADR *executes* its named deferral, under its
> constraints), ADR-436 + ADR-514 D2 (the Open-With machinery this rides — already
> shipped), ADR-427 §10 (the designated SECOND reference app: revision write + CAS +
> 409 + attribution on exactly the public contract), ADR-398 D3 (OS-owned
> linkification, extended to reach the lane surface), ADR-406 D2 (the conditional
> save), ADR-209 (one revision chain, no filename versioning), ADR-254 (format
> discipline — unchanged), ADR-501 (S1 — a sibling door repaired in this arc),
> ADR-569 (adjacent, disjoint: Strings tends designated files on a cadence; the
> editor is the member's own hand, no standing writer).
> **Amends**: ADR-236's "mutation → chat" clause as inherited by the app registry
> (ADR-436): the law is re-cut as *a viewer never edits; an editor edits only through
> the member write door*. Docs/Studio canon is untouched: **ADR-456's ruling stands —
> HTML is the sole canonical artifact source; Docs is never bimodal; `.md` is never
> converted to be edited.**

---

## 1. Context — the round-trip that already works, minus the cursor

The 2026-08-14 connector session is the receipt. Claude.ai, acting as its own
principal over MCP, authored `marketing/video/human-clipboard/transcript.md` into the
commons; the member referenced it on the chat surface; the colleague read it and
offered refinement; the external platform will read the same path back. The file
stayed the file — both platforms addressed it by path, every write attributed. That
round-trip is the product's pitch, and it survived precisely because nothing
converted the `.md` into something else.

One asymmetry surfaced. Every principal can put a cursor in the commons' prose
except the member: agents write through the primitives, connectors through the MCP
`edit` verb, but the member's browser has **no write path to an arbitrary `.md` at
all** — `PATCH /workspace/file` is a closed prefix allowlist of config shapes
(`routes/workspace.py`), and `/studio/artifacts/write` refuses anything but `.html`.
The member's only mutation route is relaying edits through chat. For working prose —
transcripts, briefs, notes, exactly what external platforms default to producing —
that relay is friction the OS should not impose on its own operator.

ADR-456 D1 named this moment in advance and deferred it with constraints:
*"a `markdown.editor` app claiming the `markdown` type beside `markdown.viewer`
(the ADR-436 Open-With moment — textarea/CodeMirror-grade, never block-grade;
Studio's machinery must not leak into it) … an app decision, not a Studio format
decision."* ADR-427 §10 independently designated the same build as the second
first-party reference app, and scoped what it must prove: **revision write + CAS +
409 + attribution, on exactly the public contract, zero private API.** The Open-With
machinery ADR-436 deferred has since shipped (ADR-514 D2: the submenu, the per-file
default override in Get Info, the `applyDefaultOverride` re-rank). The moment ADR-456
was waiting for has arrived, and the demand is observed, not speculative.

**What does NOT move**: `.md` remains the substrate's prose currency and `.html` the
authored-artifact currency (ADR-456); the editor changes who can hold a pen, not what
the paper is. Default prose output stays `.md` by participant discipline — the editor
makes that default fully round-trippable rather than changing it.

## 2. Decisions

### D1 — An app claiming the type, never a verb on the menu

`markdown.editor` registers beside `markdown.viewer` as a second app owning the
`markdown` type. It surfaces through the shipped Open-With machinery: the submenu
lights up because the type now has two apps (`resolveHandlers` length > 1), the
viewer stays first-registered — **Preview remains the default open everywhere** (Files
inline, chat's `ArtifactCard`, `FileOpenModal`) — and a member who wants a given file
to open in the editor by default says so per-file in Get Info, machinery that already
ships. An editor is never an implicit mount: no context-menu "Edit" verb, no
double-click surprise. The app IS the affordance, which is the ADR-456 framing taken
literally.

### D2 — Inline in Files; not a surface

The editor mounts where the viewer mounts — the Files preview frame. No new kernel
surface slug, no `SurfaceRegistry` row, no param registry entries, no arrival door,
no ADR-308 stub. A textarea-grade editor holds no window-worthy state: document
identity is Files' selection, exactly as it is for Preview. The Docs-pattern surface
(`{slug}.file` owned + ephemeral, shareable URL) is **refused for v1** and revisited
only if shareable edit-links are demanded by observed use.

### D3 — The registry contract gains an honest second class

`AppRegistration` rows declare `mode: 'view' | 'edit'` (absent = view). The registry
header's law — "never edits (mutation → chat, ADR-236)" — is re-cut, not deleted:

> **A viewer never edits. An editor edits only through the member write door
> (`PATCH /workspace/file`), conditionally (D5), attributed as the member — never
> through private API, never through a side channel.**

Chat remains the conversational mutation path; the editor is the cursor path. Both
land attributed revisions on the same chain — the substrate cannot tell the
difference, which is the point. Mechanically: `inlineHandler` maps over the **full**
`resolveApps` list (today it discards the tail, so a second inline app would be
invisible), labels from the registry row (Preview / Edit); `FileBody` stays the
single kind-switch — an Open-With choice passes the *chosen* app id down as a
selection, never a re-derivation, keeping the `test_lane_artifacts` gate honest.

### D4 — The write door widens by format class, not by enumeration

This is the permission-surface discourse ADR-456 §Context explicitly deferred out of
its own wave ("a permission-surface change that gets its own discourse"), now had:

- `PATCH /workspace/file` accepts the **prose text class** — `.md`, `.markdown`,
  `.txt` — at any path where `_is_path_locked_for_principal(auth, path)` allows.
  The principal gate is already on this door (ADR-501 S1); the class rule replaces
  the closed prefix enumeration *for prose only*. The existing enumerated shapes
  (`system/`, `context/`, the `_design.yaml` convention, …) survive unchanged.
- Machine formats stay narrow (ADR-254): no generalized `.yaml`/`.json` editing
  through this door. The editor app claims the `markdown` type only.
- A member's reach through this door is exactly their reach through the primitives:
  class ceiling (member → agent: `governance/ contract/ constitution/ persona/
  system/` locked) plus `principal_grants` where configured. One authorization
  answer, whichever hand holds the pen.

**Sibling repair, same arc**: this scoping found `POST /studio/artifacts/write`
carries **no** `_is_path_locked_for_principal` — a scoped member can write `.html`
into `constitution/` or `governance/`, past their ceiling (the ADR-501 S1 defect,
unfixed on that door). The gate lands there in the same stage. A new door must not
copy a hole; an audit that finds one names it.

### D5 — CAS is the editor's spine, because the commons is multi-principal

The load carries `head_version_id`; every save passes `expectedHeadVersionId`
(ADR-406 D2 — the machinery exists end-to-end, `StaleWriteError` → 409 with the
intervening revision's attribution). On 409 the editor says **who** moved the head
("Claude via MCP revised this file 2 minutes ago") and offers reload; v1 has no merge
machinery — the member re-applies on the new head. This is not an edge case to
tolerate but the product story to surface: the same file may be under an external
platform's pen mid-session, and the editor is where the member *sees* that the
commons is shared.

### D6 — The chat seam completes the round-trip

The observed flow's first hop — the colleague's reply naming the file — renders as
plain text today. ADR-398 D3 (OS-owned linkification; the model never authors URLs)
shipped with a root-prefix allowlist that cannot see meaning-named folders
(`marketing/…/transcript.md` matches nothing), and the lane surface never opted in.
Two repairs, both inside ADR-398's own decision:

- Detection gains an **extension-shaped file rule** (a path-shaped token ending in a
  known substrate extension), since meaning folders are unenumerable by design.
  Fenced/inline code stays skipped; folders keep the existing root rule.
- `LanePanel` assistant messages turn on `linkifySubstrate`, so a named path is a
  `SurfaceLink` into Files — where Preview, and now Open With → Editor, take over.

### D7 — v1 grade and refusals

Textarea-grade, dependency-free: monospace plain text, dirty state, Cmd/Ctrl+S and a
Save affordance, cancel restores the loaded revision, a successful save returns to
Preview. CodeMirror is a possible upgrade, not a v1 dependency. **Never**
block-grade; no Studio machinery (no block ids, no `data-ref`, no arrangements); no
preview-split pane (the viewer is one Open-With switch away); no AI in the loop —
the editor is direct manipulation, metered at zero.

### D8 — Falsifiers, pre-registered

(1) The member saves an `.md` in a meaning folder from the browser; the revision
lands on the timeline attributed to their identity uuid. (2) A scoped member is
refused `governance/x.md` through the *same* door — falsified as the real principal,
not by source inspection. (3) A connector edit mid-session makes the member's save
409 with the connector's attribution shown. (4) A colleague's chat reply naming a
meaning-folder path links into Files. (5) The ADR-514 D2 gate and the
single-kind-switch gate stay green untouched. (6) `/studio/artifacts/write` refuses
a scoped member's `.html` outside their ceiling. (7) Docs/Studio behavior is
byte-identical — no `.md` ever enters an authoring canvas.

## 3. What this ADR does NOT do

- **No conversion.** md→html up-projection stays ADR-456 Wave 4, demand-gated.
- **No Docs/Studio change.** The canvas never opens `.md`; never bimodal.
- **No machine-config editing.** `_*.yaml` / `.json` keep their existing doors.
- **No new surface, slug, or params** (D2).
- **No standing writer.** Keeping a file current is ADR-569/Strings; this is a hand.
- **No format-default change.** Prose stays `.md` by discipline, not enforcement.
- **No AI, no meter.** Zero LLM involvement in the editor path.

## 4. Implementation stages (post-ratification)

1. **The doors** (api): D4 prose-class rule on `edit_workspace_file` + the studio
   door's principal gate; `api/test_adr570_member_prose_door.py` (falsifying, as the
   real principal, both allow and refuse).
2. **The app** (web): `MarkdownEditor` viewer-tree component; registry row + `mode`;
   `inlineHandler` maps the full list; chosen-app selection through `FileBody`;
   Open-With + Get Info override verified against the ADR-514 D2 gate.
3. **The chat seam** (web): extension-shaped detection + `LanePanel` opt-in.
4. **Click-pass**: the full round-trip — connector-authored file, chat link, Preview,
   Open With → Editor, save, timeline attribution, and the D5 409 driven for real by
   an MCP edit mid-session.
