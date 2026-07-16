# The Agents Surface — the re-surface, the scaffold, and the debt ledger

**Status**: Spec + **debt ledger**. The operator's cut: *"mark the technical, architectural debt in documentation, whereas we double our efforts towards front end and wiring considerations, and base agent configurations."*
**Date**: 2026-07-16
**Relates to**: ADR-460 (the model) · the registry / personified / hiring-card specs (the substrate this surfaces) · ADR-297 (surfaces mirror substrate) · ADR-340 DP29 (mirror once, compose few) · ADR-436 (the app registry) · ADR-380/382 (the Rung-2 horizon this surface was demoted FOR).

---

## 1. The finding that reframes the request

The operator asked to *"re-surface the agent surface, and thus it becomes part of the launcher and dock that we've previously held."* Two receipts change the shape of that:

**Receipt A — the `/agents` surface is deliberately demoted, and the comment says why** (`kernel_surfaces.py:547`):

> `"launcher_tier": "search-only"` — *"Demoted to search-only (2026-07-08): Altitude-3 'hire an agent' is the deferred horizon (ADR-380 Rung-2 launch line)… The launch focus is the user's HANDS — the A2 chat lanes — not the user's HIRE. The roster stays URL-reachable + searchable; it just leaves the launcher's browse tiles + the dock **so it isn't a second, confusing AI door beside /chat**. One-word revert (→ "primary") re-surfaces A3 when the Rung-2 track-record clock says it's time."*

**Receipt B — the roster it guards is EMPTY.** `SELECT … FROM agents` → **0 rows** (ADR-414 retired the last one).

**So the demotion's own reasoning has inverted, on both clauses:**

1. *"The launch focus is HANDS not HIRE"* — the operator just **made hiring the launch focus**. Sonnet/Scout/Critic/Lisa exist and are hired today.
2. *"A second, confusing AI door beside /chat"* — that fear was **A2-vs-A3**: two kinds of AI, two doors, incoherent. **ADR-460 dissolved that ladder.** There is no second kind. There is *one* door, and it is currently a `<select>` inside a form.

**The re-surface is therefore not a revert of the 2026-07-08 decision — it is that decision's own condition being met, by a different route than it expected.** It expected the Rung-2 clock. What actually arrived was the ladder dissolving and hiring becoming real at Rung 1. **This distinction matters: nothing here re-opens Rung 2, and `/agents` must not become the persona-seat surface by accident.**

## 2. D1 — One surface, list + detail (not two)

The operator: *"the agent surface needs to be somewhat of a discovery (maybe for create) while showing list of your own created agents… each agent created will have its detailed page… or maybe this can be all same with discovery, you decide on details that is future proof, code scalable and disciplined."*

**Ruling: ONE surface, two modes — `/agents` (list) and `/agents?agent={slug}` (detail).**

This is not a new pattern; it is the codebase's oldest surface convention (ADR-167 list/detail with URL-driven mode, still live in the page's own docstring: *"List mode (no `?agent=`) shows the roster. Detail mode (`?agent={slug}`)… `?agent=X` is window-internal deep-link state — Figma-shaped, like `?node-id=X` — not a separate page navigation."*).

Why one and not two, on the operator's own criteria:

| Criterion | Why list+detail wins |
|---|---|
| **Future-proof** | A separate `/agents/{slug}` page is a second route, a second window in the OS shell, a second breadcrumb owner. The `?agent=` param is *window-internal state* — the ADR-358 D6 shape every surface already uses. |
| **Code-scalable** | Skills/Connections (§5) land as **panes inside detail**, not as new routes. The surface grows by adding panes, never by adding pages. |
| **Disciplined** | ADR-340 DP29 *"mirror once, compose few"*: `/agents` mirrors one substrate concern (the workspace's agents). Two routes for one concern is the duplication DP29 forbids. |

**Discovery and creation live in the SAME surface**: list mode shows *your* agents + the kernel three as **what you can hire**, with the hiring card inline. There is no separate "browse" — the base set *is* the catalogue, and it is three items long.

## 3. D2 — The scaffold: base agents are the floor, not a preset shelf

The operator: *"we can have base agents (like the lowest config without those added connectors or skills), like the Sonnet, or Gemini, ChatGPT like agent."*

**This is already built and it is exactly right** — `KERNEL_AGENTS` = Sonnet (Claude) · Scout (Gemini) · Critic (GPT-5). One per vendor, named for the work. **The lowest config**: five file verbs, no connectors, no skills, addressed-only.

The one honest correction to the framing: **they are the floor, not a shelf.** A "preset shelf" implies more presets arrive as the product grows. What actually arrives is **capability** (skills, connections) — and when it does, it attaches to a base agent's *class*, not as a fourth/fifth/sixth preset. Three engines, three characters, N hires. **Seven presets would be the spec sheet with makeup on.**

## 4. D3 — The chat re-write: what it actually is

The operator: *"the chat surface re-write needs to occur where currently new chat is via llm routing, but now needs full re-alignment towards our recent multi-chat, multi-agent (no longer choosing engine, but agent)."*

**Receipt: the re-write is already ~80% landed** and the remainder is small + specific:

| | State |
|---|---|
| The picker asks WHO (Agent chips, not a `<select>` of engines) | ✅ shipped (`f605c69`) |
| The lane is named by its Agent, falls back to the engine label | ✅ shipped |
| The member hires + names their own | ✅ shipped (`420f424`, `73dd006`) |
| **The model FILTER facet still groups lanes by ENGINE** | ❌ **the last spec-sheet surface** |
| **The hiring card lives in the chat picker, not on `/agents`** | ❌ wrong home (§2) |
| Multi-agent in ONE room | ❌ the rooms wave (unbuilt, next) |

**So "the chat re-write" = two removals and one relocation**, not a rewrite: the model-filter facet becomes an **agent** filter (or dies — `presentModels` over ≤8 lanes is a facet nobody needs); the hiring card moves to `/agents`; the picker keeps only the chips.

**The one thing that must NOT be swept up**: `models` stays on the envelope and every `LANE_MODELS` row stays routable — Studio/derive lanes bind an engine directly and never pick a colleague (a bound lane's job is the artifact). The registry changed what the **chooser asks**, never what the system can **run**.

## 4b. D3b — Studio's chat is an Agent too (the operator's reframe)

> *"even the current 'chat' nested under Studio becomes selecting an agent OR having a dedicated **Designer Agent**. It's more of a reframe and streamlining to make the user experience centered and consistent around Agents, so that it also considers the inter-exchange of work and chat sessions that may, will most likely occur between existing chat and studio surfaces."*

**Adopted — and the code hands us the receipt.** `StudioSurface.tsx:240`:

```ts
api.lanes.create({
  name: baseName(artifactPath),
  model: models[0].id,          // ← whatever engine is FIRST in the array
  artifact_path: artifactPath,
})
```

**Studio grabs `models[0]`.** Nobody chose that engine; nobody named it. It is not a design — it is an accident that has been running. §4's table called the bound lane's engine-binding *deliberate* ("a bound lane's job is the artifact, not the colleague"). **That defence holds for the Studio/derive path needing to bind a model directly. It does not defend `[0]`.** The re-cut corrects a real thing.

**The ruling: a bound lane carries an Agent like every other lane.**

- **The default is a kernel Agent** — the natural fourth capability is a **Designer** (authoring-shaped posture; the ADR-440 D3 Studio overlay is *already* a posture, so this is a re-home, not a new mechanism). Until it exists, the bound lane's default is a **named** kernel Agent, never `models[0]`.
- **The member may hire their own** and bind them — "my Designer is Maya, she's playful" is the same widening, one surface over.
- **The Studio posture still composes** (ADR-440 D3): a bound lane's system prompt = the Agent's character **+** the artifact posture. Same additive-overlay shape as the derive recipe (ADR-450 D3), which already composes *beside* the Studio overlay. **Three overlays, one rule.**

**Why this is the streamlining, not a feature**: the OS currently has two answers to "who am I talking to?" — chat says *a colleague you named*, Studio says *an unnamed engine at array index zero*. That is the same **incoherence** the `<select>` had, surviving in the one place nobody looked. One answer everywhere.

**The inter-exchange the operator names** is the real prize. Once both surfaces' conversations carry an Agent:
- A settle from a Studio lane attributes to *Maya*, not to `gemini-2.5-flash`.
- The chat↔Studio seam (Quick Look + owning apps) gains a **person** on both sides — you ask Lisa about a deck Maya made, and the ledger says so.
- The rooms wave inherits it for free: a room is Agents + a scope, and a *bound* room is Agents + a scope + an artifact. **No new object.**

**Sequenced after §7's steps 1–5** (the surface must exist before Studio points at it), and the Designer capability is its own small commit — a `KERNEL_AGENTS` row + re-homing the ADR-440 posture. **Named here so it is not lost; deliberately not swept into this pass.**

## 5. D4 — Skills · Connections: the detail pane's future, stated not built

Detail mode's panes, when they come:

- **Identity** (name · tone · avatar · colour) — **built** (the hiring card is this pane, homeless).
- **Capability** (what they're for · the five verbs · the engine, under a disclosure) — **built as prose**, wants a pane.
- **Skills** — **the machinery is DEAD** (`orchestration.py:1366`: *"returns False universally; no SKILL.md injection, no RuntimeDispatch"*; ADR-417 decommissioned the render service). A Skills pane today is an empty box that lies. Direction: `/workspace/agents/{slug}/skills/*.md` composed into the posture — **the folder already accommodates it** (that is what folder-per-Agent bought).
- **Connections** — the lane is **DORMANT** (ADR-404). ⚠️ **And it is where the cliff gets tested**: a connection that writes outward IS consequential action. Likely shape: a **workspace capability the kernel grants to a `based_on` class, never a key in a member's file**. Unanswered.

**The discipline that makes this scalable**: every pane above is *identity* or *capability*. **No pane is authority.** The detail page must never grow a switch — that is the ChatGPT `Never ask` dropdown, and the hiring card's gate already forbids it component-side.

---

# 6. THE DEBT LEDGER

The operator's ask: *"mark the technical, architectural debt in documentation."* Each item is **named, receipted, and NOT silently carried**.

## 6.1 Nothing built this week has been touched by a human

**Eight commits shipped** (W0 · settle · registry · personified · hiring card · the surface · face/row/modal · the D8/D9 fixes). **Every one is gate-green and prod-probed; NONE has been clicked.** Specifically unverified:
- settle's felt beat (the note landing in the transcript)
- the picker chips + the hiring card form + **the avatar upload round-trip** (the 415 wall is now down — §6.2a — so this is *testable* for the first time; still untested)
- Phase-A's live SSE abort + a real vision call (owed since `4c6c56d`; **could not have worked until 2026-07-16** — §6.2a)

**This is the largest debt on the board** and it is not code — it is that the whole point of these features is *felt*, and nobody has felt them.

> **The operator's single click on 2026-07-16 found what 111 gates could not** (the bucket 415). That is the ledger's own thesis, demonstrated: **a gate proves the code path; only a human proves the product.** When a feature crosses into Supabase/RLS/env, the honest report is *"needs a human click"* — never *"prod-probed ✅"*.

## 6.2 The avatar is stored but never rendered — ✅ **RESOLVED** (`4742a2c`)
~~The manifest carries `avatar: /workspace/uploads/…`; the card renders a **colour swatch**.~~

**Closed by "a face, a name" (`4742a2c`), which post-dates this ledger's drafting.** `AgentFace.tsx` resolves the signed URL via `api.documents.blobUrl` (passing through `https:|data:|blob:` untouched) and falls back to the colour swatch only when there is no avatar. Wired at all three call sites (`AgentsSurface` detail + both list rows). Backend emits `avatar_url` at four sites in `routes/agents.py`. **The chain is whole: upload → manifest → `avatar_url` → signed URL → `<img>`.**

## 6.2a The bucket that took no images — ✅ **RESOLVED** (migration 217 applied 2026-07-16)

The blocker under §6.2 and, far more seriously, under **Phase-A image attachments** (broken since `4c6c56d` shipped "gate-green"). The `documents` bucket's `allowed_mime_types` predated image support and Supabase Storage rejected every image with a 415 before our code ever ran.

**Applied receipts** (not a config read — a real Storage round-trip):
- `UPDATE 1`, then `UPDATE 0` on re-run — the `NOT (@> image/png)` guard makes it idempotent.
- `documents` now carries `{…, image/png, image/jpeg, image/webp, image/gif}`.
- Probed live: **png · jpeg · webp · gif all accepted**; negative control (`application/x-msdownload`) **still refused** — the bucket was widened, not thrown open.
- Invariant holds: the four MIMEs are exactly what `IMAGE_TYPES` {png,jpg,jpeg,webp,gif} produces through `upload_mime`'s jpg→jpeg normalization. No gap between what the API accepts and what the bucket takes.

**What this does NOT prove** (per §6.1's own discipline): that a *member's* upload renders, or that a real vision call round-trips. It proves the wall is down. **Still needs a human click.**

## 6.3 `/agents` is an empty page over an empty table — ✅ **RESOLVED** (`3c29bed`)
Closed by "the surface comes home" — the page is §2's list+detail surface over `KERNEL_AGENTS` + the member's own hires (the `agents` *table* was never the roster's source; the folder pattern is). The `[id]` route and the rebuilt `page.tsx` are live.

## 6.3 `/agents` is an empty page over an empty table
`SELECT … FROM agents` → 0 rows. The page renders `AgentContentView` for a roster that cannot populate. **`web/app/(authenticated)/agents/` is dead code today** — it must either become §2's surface or be deleted. It has been "URL-reachable" for 8 days and reaches nothing.

## 6.4 The kernel-agent slug/name coupling
`KERNEL_AGENTS["sonnet"]` names an engine ("Sonnet"). The registry spec named this a **wart it could not defend** and kept it because renaming the incumbent default costs without paying. Now that the member names their own, the wart is smaller — but a member seeing "Sonnet · Scout · Critic" still sees one spec-sheet word out of three. **Fix on the next naming pass; do not fix piecemeal** (the slug is persisted on every existing lane).

## 6.5 The chooser's `model` leak (fixed, but the class remains)
The gate caught `model` entering the chooser payload while `avatar` was added. **The class of bug is live**: the payload is hand-assembled in `list_agents()`, and each new identity field is an opportunity to leak a capability field. *Consider a serializer that whitelists rather than enumerates* — not now, but named.

## 6.6 Probe residue in prod (operator's call)
- `/workspace/agents/lisa/` — a **working** Agent (arguably a feature)
- 2 settle notes at `operation/sample/2026-07-15-6-slide-*`
- `execution_events`: 2 `settle` rows + ~3 `lane` rows (~$0.03 total)

`falsifier_2.settles = 2` is **two probe settles, not two felt ones.** Clear before the falsifier window is read, or accept with this note as provenance.

## 6.7 Studio's bound lane picks `models[0]` — an accident, not a design
`StudioSurface.tsx:240` binds **whatever engine is first in the array**. Nobody chose it; nobody named it. It is the last place in the OS that answers "who am I talking to?" with an array index. §4b rules it: a bound lane carries an Agent (a **Designer**), like every other lane. **Named as debt because the fix is sequenced AFTER the surface lands, not swept into it.**

## 6.8 Pre-existing, NOT ours (reproduced on clean HEAD)
- `test_adr412_chat_surface`: *"the Brand pane still gates on operation/ coverage"* — another lane's.
- `test_adr388_files` ×3 — long-standing (memory).

## 6.9 Deferred by decision, not by accident
- **Rooms** — the multi-agent conversation (the next wave; vocabulary now correct).
- **Skills machinery** — dead since ADR-417; a spec, not a field (§5).
- **Connections** — dormant lane + the cliff question (§5).
- **Per-turn engine override in a lane** — the routing ladder's rung (a). Free (five lines; attribution is already per-turn correct) and **not built**: the Agent IS the designation, so switching mid-thread is a different gesture than picking a colleague. Wants evidence first.

---

## 7. Build order (FE + wiring, per the operator's "double our efforts")

> **STATUS 2026-07-16 — steps 1–7 are DONE; step 8 is the frontier.** Receipts: `agents` is `launcher_tier: primary` with the inversion reasoning recorded in-comment (`kernel_surfaces.py:547`) · the surface is list+detail (`3c29bed`) · the dead roster is re-pointed, not both-and-neither · the hiring door left the picker and `NewChatModal` links out to `/agents` · the `presentModels` facet is **gone** (grep: zero hits) · the avatar renders (§6.2) · the D3.a ratchet is green at **111/111**.
>
> **Step 8 (§4b) is the only build-order item left**, and `StudioSurface.tsx:241` still reads `model: models[0].id` — the accident named in §6.7, exactly where it was left. **The two things standing between here and it are not code**: migration 217's human click (§6.2a) and §6.1's felt beat.

1. **`/agents` → `launcher_tier: "primary"`** + the dock. The one-word revert its own comment names — with §1's reasoning recorded so it does not read as re-opening Rung 2.
2. **The surface**: list mode = your agents + "who you can hire" (the kernel three) + the hiring card inline. Detail mode = `?agent={slug}` → Identity + Capability panes (the card, re-homed).
3. **Delete the dead roster** (`AgentContentView` over the empty `agents` table) or re-point it. **Not both, not neither** (Singular Implementation).
4. **Chat picker**: remove the hiring door (it lives on `/agents` now); keep the chips.
5. **The model-filter facet**: agent-filter or delete.
6. **The avatar renders** (§6.2) — or the field goes.
7. Gate: `/agents` is primary; the surface has no authority pane in any state; the dead roster is gone.
8. **THEN §4b** (its own commit): the **Designer** kernel Agent (a `KERNEL_AGENTS` row + the ADR-440 D3 posture re-homed) and Studio's bound lane carrying an Agent instead of `models[0]`. Sequenced last because the surface must exist before Studio points at it.

## 8. One-line statement

**The `/agents` surface was demoted eight days ago for two reasons that have both inverted — hiring is now the launch focus, and the A2/A3 ladder that made a roster a "confusing second door" no longer exists — so the re-surface is that decision's own condition being met: one surface, list plus detail, where discovery IS the base set of three, the hiring card comes home, and every future pane is identity or capability because none of them may ever be authority.**
