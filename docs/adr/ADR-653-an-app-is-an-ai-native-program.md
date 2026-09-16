# ADR-653 — An app is an AI-native program: the member scaffolds an agent, its skills, and a surface

> **Status**: **Proposed** (2026-09-16), doc-first. Awaiting operator ratification. **No code rides this document.**
> **Date**: 2026-09-16
> **Authors**: KVK (operator) + Claude (collaborator)
> **Dimensional classification** (Axiom 0): **Identity** (Axiom 2 — a member may author an agent again) + **Channel** (Axiom 6 — a surface may be composed, not only mirrored) + **Mechanism** (Axiom 5 — where an app declaration LIVES and who may assert it). **No authority change**: every reach decision stays on grants and gates, and nothing here widens what any principal may do.
>
> **Derivation**: [the-app-is-an-ai-native-program-2026-09-16.md](../analysis/the-app-is-an-ai-native-program-2026-09-16.md) — the conceptual frame, derived from first principles at the operator's instruction. This ADR is its mechanism half and does not restate its argument.
>
> **Origin**: a real member. The operator's sister, onboarded as a beta tester, said: *"all this is cool, but what would be cooler is if it could help me manage my photos for work."* The frame doc's §1 records why that sentence is a structural diagnosis rather than a feature request.

**Reopens** (each explicitly, with the reason on the record):
- **[ADR-599](ADR-599-the-roster-empties-and-studio-becomes-slides.md) D2** — the member-agent machinery was deleted with the ruling that *"member agents return, if they return, **as pairings with apps** — rebuilt against the stabilized scaffold, not carried as dormant machinery."* This ADR is that pairing. §3 argues the scaffold is now stable.
- **[ADR-435](ADR-435-delete-the-home-surface.md)** — composition was resolved by SUBTRACTION rather than by naming, and the ADR's explicitly rejected alternative was to *"promote `composition` to a validated register."* §5 reopens exactly that option, on the ground that ADR-435's stated reason (*"a glorified redirect"*) does not describe an app surface.

**Preserves** (load-bearing, untouched):
- **ADR-460 D3.a — the authority cliff.** No app declaration and no agent row may carry consequential authority. §6.
- **ADR-596** — an agent is identity ⊕ character ⊕ engine and nothing else; authority, clock, purpose and judgment live on grants, declarations and gates. §6 is the whole reconciliation.
- **ADR-630** — a skill is a file, the public Agent Skills convention verbatim, and never grants reach.
- **ADR-639** — standing work is a kernel lane. This ADR does not make it an app; §7.
- **ADR-562 / ADR-636** — an app declares itself once on each side of the wire, and no client row carries authority.
- **ADR-222** — the kernel never branches on a program; specialization lives at the compositor.

---

## 1. Context — three layers, three different states

The frame doc establishes *what* an app is. This section establishes *what exists*, driven against live code at `aaf641a` by two independent audits plus direct verification. Every claim carries a receipt.

An app, per the frame, scaffolds three things: **an agent, the skills it works by, and a surface that shows its state.** Those three layers are in radically different states, and the whole shape of this ADR follows from that asymmetry.

| Layer | State | Receipt |
|---|---|---|
| **Skills** | ✅ **Shipped and marketplace-compatible** | `api/services/skills/__init__.py` — public spec verbatim; 12 kernel skills on disk; member skills read from `/workspace/skills/%/SKILL.md` at `:584` |
| **Agent** | 🟡 **One field away** | `AGENTS` at `api/services/agents_registry.py:86` already carries `kernel: bool` as descriptive provenance; no data ingress exists |
| **Surface** | 🔴 **Demolished, and the demolition was partly accidental** | `composition_resolver.py` 354 live lines; the dispatch registry deleted in `e18e178` |

### 1.1 The skills layer is done

`parse_skill` (`api/services/skills/__init__.py:240-297`) implements the public Agent Skills spec: `name` + `description` frontmatter, body under 500 lines, progressive disclosure. Host-specific frontmatter (`allowed-tools`, `model`, `tools`, `argument-hint`) is **stripped and named** (`:271-276`), so an import says what it lost.

Member skills are already read into every lane turn: `read_member_skills` (`:574-608`), called once per turn from `build_lane_conventions` (`api/services/lane_runner.py:1360`). The index is a byte budget with an **evidence-ordered eviction table** (`_INDEX_RANK`, `:453-471`) and two ceilings — 3,400 bound, 4,000 unbound (`:173`, `:204`).

⚠️ **Two stale facts found in the audit, owed separately (§10):** the `UNBOUND_INDEX_CEILING` docstring says *"today's ELEVEN … 3,947 of 4,000"* (`:187`, `:201-202`) and there are **12** kernel skills on disk — the open lane is at or past its ceiling and evicting its rank-2 tail. And `metadata.needs` has **zero live declarations**: the only `needs:` string in any `SKILL.md` is documentation prose in `creating-skills/SKILL.md:22`. The mechanism is live and untested against a real skill.

⚠️ **A measured ceiling on the marketplace claim.** ADR-630 §1 counted that only **5 of Anthropic's 19 public skills** are pure work verbs achievable with file verbs, recall, search and image generation; the rest are format- or code-bound. "The marketplace" is a smaller usable set than the headline suggests. This ADR does not depend on that count, but a product claim built on it would.

### 1.2 The agent layer is one field away, and one contradiction away

`AGENTS` (`api/services/agents_registry.py:86-202`) holds **three rows** — `designer`, `editor`, `blogger` — all `offered: False`, all `kernel: True`, all running `anthropic/claude-sonnet-5` at `token_profile: 8192`. The registry's only live discriminant is the `posture` string.

**The row already distinguishes provenance from authority.** `kernel: bool` is declared at `:31-37` as *"DESCRIPTIVE, NEVER AUTHORITY … it says who wrote the row, never what the agent may do."* A member-authored agent is therefore **already representable in the row shape** — `kernel: False` is a legal value that no row uses.

**There is no data ingress.** `AGENTS` is a module-level literal; `grep -rn "AGENTS\[" api/services api/routes` returns zero hits. No mutation, no registration function. Two docstrings (`api/services/apps/__init__.py:18`, `api/services/authoring.py:2358`) describe `agents/{slug}/_agent.yaml` as the member shape — *"theirs to author, discovered never registered"* — and `grep -rn "_agent.yaml" api/services api/routes` returns **zero live hits.** The path is prose describing a deleted mechanism.

**Four apps, three agents** — Editor serves both slides and text. Many-to-one is live and free: ADR-601 D1 measured the job overlay at 86.7% of a Slides frame against the character's 2.4%, so an agent's prompt weight is constant in the number of apps it serves.

### 1.3 The surface layer — what is live, what is dead, and what died by accident

This is the finding that most shapes the ADR, and it is finer-grained than the frame doc stated.

**`surfaces[]` is LIVE and load-bearing.** `resolve_workspace_composition` (`composition_resolver.py:42`) returns four keys; the `surfaces[]` array is seeded from `kernel_surface_entries()` at `:70` **always**, served at `GET /api/programs/surfaces` (`api/routes/programs.py:34`, mounted `api/main.py:252`), and consumed by seven live frontend sites — the Dock (`TopBarSurface.tsx:101`), the Launcher (`LauncherSurface.tsx:24`), the viewport (`SurfaceViewport.tsx:67`), route sync (`AuthenticatedLayout.tsx:97`), and three more.

**The `composition.tabs` tree is DEAD.** Its only reader is `getTab` (`web/lib/compositor/useComposition.ts:158`), whose only caller is `BundleBanner.tsx:25`, which has **zero importers**. `getDetailMiddles` and `getActiveBundles` have zero callers. `chat_chips` has no renderer.

⭐⭐⭐ **The half the bundles populate is the dead half.** All five bundle `SURFACES.yaml` files declare `tabs:`; **none declares the top-level `surfaces:` block** that `_resolve_program_surfaces` (`:282`) reads — stated in the resolver's own docstring at `:302-305`. So the program-composition path is not merely unconsumed; the bundles fill the tree nothing renders, and leave empty the one the shell actually reads.

**The dispatch registry died as collateral, not by a ruling.** `web/components/library/registry.tsx` held `LIBRARY_COMPONENTS` — a string-`kind` → React component table — plus `dispatchComponent`, which rendered an amber *"Component `{kind}` referenced in composition but not registered in the system component library"* box on a miss. **This was the only data-driven rendering path YARNNN ever had.** It was deleted in `e18e178` (2026-08-24, *"fix(agents): ADR-596→603 audit hardening"*) holding two entries, together with `MiddleResolver`, `ChromeRenderer` and `WorkDetail` — ADR-603 D5 deleted the Recurrence window, its only tenant.

ADR-435 had **explicitly preserved** `LIBRARY_COMPONENTS`/`dispatchComponent` ("Preserves §E — shared with WorkDetail, do NOT delete"). It outlived the ADR that spared it by six weeks and then died without a ruling of its own. **Nothing ever decided that YARNNN should not have a data-driven rendering path.**

**The hard constraint: a program surface is displayable but not openable.** `KERNEL_SURFACES` (`api/services/kernel_surfaces.py:220`) is a static list, never mutated (`grep` for `.append`/`+=`/`.extend` → zero). On the client, `KernelSurfaceSlug` is a hand-written union (`web/types/surface.ts:28`) and `Launcher.navigate` hard-gates the click:

```ts
if (isKernelSurfaceSlug(surface.slug)) onForeground(...)   // Launcher.tsx:268
```

A program-tier surface **reaches the Launcher list** and is grouped under a `program:{slug}` header (`Launcher.tsx:134-137`), but the click does nothing. `create_lane` refuses an unregistered app with a 422 (`api/routes/lanes.py:965`). **`Launcher.tsx:268` is the one line this ADR must break.**

### 1.4 The resident is already derived, never stored

A structural fact that makes §4 cheap: `create_lane` deliberately does **not** stamp the resident (`api/routes/lanes.py:1074-1080`). `_lane_agent` (`:404-439`) re-derives it on every serve and every turn through `app_for_lane` → `resident_for_app`. The lane frame composes character-then-job with `+=` (`lane_runner.py:1327-1336`).

So **an app's identity already flows from a declaration through a derivation into a turn.** This ADR widens where the declaration may live; it does not invent the path.

### 1.5 Agent memory is an address with no writer and no reader

`agents/{slug}/memory/` is declared (`api/services/workspace_paths.py:98-161`), protected (`_is_foreign_agent_home`, `api/services/primitives/workspace.py:2644-2672`), and served as an address on the `/agents` payload (`api/routes/lanes.py:645`). **Nothing writes it and nothing reads it into a turn** — verified: `grep -rn "agent_memory_root" api/services api/routes` returns three hits, all the definition or the address. `grep -n "memory" api/services/lane_runner.py` returns one unrelated docstring line.

This matters for the frame's *"accumulates judgment about this specific work."* **That accumulation does not exist today.** §9 records it as the load-bearing open question rather than pretending the shelf is full.

---

## 2. The problem, stated once

A workspace is general, and generality reads as emptiness to a member who does not already know what to ask for (frame doc §1). The three layers that would make capability legible exist in three different states, and **the one that carries the legibility — the surface — is the one that was demolished, half of it without a ruling.**

The narrower engineering statement: **YARNNN can declare what an app is on the server, derive its agent, scope its skills, and serve its surface row — and then cannot render it**, because the component behind a slug is a compile-time import and the only runtime dispatch table it ever had was deleted as collateral damage.

---

## 3. D1 — An app is a member-authored declaration in the workspace, and it is a file

An app is declared at `apps/{slug}/_app.yaml`, an ordinary workspace file: attributed, versioned, revertible, forkable, exportable.

```yaml
# apps/photos/_app.yaml
name: Photos
about: Client shoots, culled and delivered.
agent:
  name: Mara
  character: |
    You look after this member's photo work...
skills: [culling-a-shoot, delivering-a-set]
surface:
  sections:
    - kind: file-grid
      source: clients/
```

**Why a file and not a table.** ADR-464's ruling, held verbatim across ADR-562 and `services/apps/__init__.py:16-23`: *the member's copy is a folder; the kernel's is code.* A kernel app is a Python module with `register_app`; a member's app is a folder they author. **Same convention, different tree — and that difference IS the cliff.** A member app declaration can never re-point a kernel app's resident, because it is not in the kernel's registry and is never read as one.

**What being a file buys, at zero cost:** every property of the substrate. Versioned (ADR-209), attributed, revertible, `derived_from`-citable, exportable (`git_export`), and **shareable by being copied** — an app marketplace is file-sharing, with no distribution machinery to build. This is the frame doc §4.2's third point, and it is the strongest argument for the format.

**What it may NOT carry** — enforced by a key whitelist, the same mechanism `AGENT_ROW_KEYS` (`agents_registry.py:207-210`) uses:
- no engine pin (the member's engine preference and the kernel's whitelist decide — ADR-647)
- no tool grant, no reach list, no scope (§6)
- no authority of any kind

Unknown keys are **parked inert**, never read — the `DECLARATION_KEYS` discipline (`standing_work.py:141-143, 291-292`), whose docstring records why: a rule with no reader is prose, and a parser that can be talked into reading a new key is an authority surface waiting to happen.

---

## 4. D2 — The app's agent is a member-authored row, and `kernel: False` is how it is known

ADR-599 D2 deleted member agents with the condition that they return *as pairings with apps*. An app declaration **is** that pairing: an agent may only be declared inside `_app.yaml`, never free-floating. There is no roster of member agents, no "Make one" door, no manifest parser returning.

**The row shape does not change.** A member agent is an `AGENTS`-shaped row with `kernel: False` and `offered: False`, resolved through the same `resolve_agent` path. `AGENT_ROW_KEYS` is unchanged, and the cliff prose at `agents_registry.py:46-53` applies to member rows exactly as to kernel rows.

**Resolution order is kernel-first, and a member app may not shadow a kernel slug.** A declaration naming a kernel slug is a **refusal**, not an override — the ADR-548 lesson (a plausible default is worse than an honest absence), and the D3.a cliff (a workspace could otherwise re-point Editor through a config file).

**`assert_editable` gets its first caller.** It was built pre-emptively (`agents_registry.py:297-322`) and is dead by design — its docstring says so. The member-app edit door is the door it was built to guard.

---

## 5. D3 — `composition` becomes a validated register, and one dispatch table returns

This reopens ADR-435's explicitly rejected alternative.

**Why the rejection no longer holds.** ADR-435 removed Home because the composition was *"in practice, a glorified redirect"* — its six slots each deep-linked to a mirror that already owned the concept. That is an argument against *that* composition, not against composition. **An app surface composes over a region and a rhythm that no other surface shows.** It redirects to nothing, because nothing else displays it.

**D3.a — `register: "composition"` is added to the validated set**, and `register` gains a runtime reader. Today it is a dead field: zero runtime reads across `api/` and `web/`, validated only by a test gate (`api/test_adr297_phase1.py:284-298`). ADR-435's §1 named precisely this — Home and Files both wore `register: "application"` and *"the taxonomy could not express its distinctness."* Naming the class is the fix ADR-435 declined; this ADR takes it, with the reason recorded.

**D3.b — a bounded component vocabulary, dispatched by kind.** `dispatchComponent` returns as the one data-driven rendering path, seeded with a small set of kinds an app's `surface.sections` may name. Its amber *"referenced in composition but not registered"* box returns with it — an honest miss, never a silent blank.

⭐ **The vocabulary is the whole product surface, and it is the riskiest decision in this ADR.** Too small and nothing composes; too large and this is a page builder — the feature race the app-seam analysis warns against. The discipline: **a kind is added when a real app needs it and cannot be served, never speculatively**, and the count of refused kinds is the demand measurement (§9.6).

**D3.c — the compile-time gate breaks at exactly one line.** `Launcher.tsx:268` gates foregrounding on `isKernelSurfaceSlug`. A member app surface is not a kernel slug and never will be. The gate widens to *kernel slug OR a declared app slug served on the roster*; the window mounts one generic `AppSurface` component parameterized by the declaration, so **no new static import is added per app** and the ADR-338 parity gate's three-way lockstep over *kernel* surfaces is untouched.

---

## 6. D4 — The declaration carries rhythm and region; it never carries reach

This is the reconciliation the frame doc's §5 requires and the cliff demands. It must be read as one sentence:

> **The app declares WHEN and WHERE. The agent is identity only. Reach is the member's, asked for continuously and granted per act.**

`agents_registry.py:15-19` states that an agent holds *"NO standing intent … no wake source, no mandate, no autonomy dial."* The frame's resident agent — watching, working on a rhythm, raising what matters — is standing intent. **The contradiction resolves exactly as ADR-596 already resolved it: those live on grants, declarations and gates, never on the agent.** The rhythm is a property of the declaration, and the agent that runs it stays a character.

**Reach is never declared.** The frame doc §6 records the operator's accepted risk — boundaries soft, hardened by use — and §6.1 records its cost: *"this agent may reach whatever this work needs"* is not safely implementable. The resolution: **the app grows its reach by asking, and each ask is a moment of trust.** Concretely, an app's unattended work runs through the existing toolless path (§7), and anything needing reach is an attended act under the member's own grant.

**The dial already exists.** `agents/{slug}/_autonomy.yaml` is live machinery — `load_autonomy` already prefers the per-agent path over the workspace one (`api/services/review_policy.py:38`), and ADR-551 D1 re-homed autonomy to the agent detail *"when ADR-382 builds the agent roster."* ⚠️ `review_policy.py:24-34` carries an explicit warning that a missing file defaults every write to `manual` — do not treat its absence as cleanup.

**Not this ADR**: the powerbox's serving half, `role='app'`, a launch verb, or any third-party principal. A member's app runs **in-workspace under the member's own grant** and is not a stranger's program. The app-seam analysis's demand gate is untouched.

---

## 7. D5 — Standing work is reused, not forked

An app's rhythm rides `{folder}/_standing.yaml` + `CONTRACT.md` exactly as it exists (`api/services/standing_work.py`), drained by the ONE loop (`scheduling.py:523`). ADR-639's ruling — *standing work is a kernel lane, not an app* — is **preserved, not reversed**: an app does not become the lane; it *declares* one, the way any member does.

Two facts make this fit without modification:

1. **`_standing.yaml` names an APP, never an agent.** `_classify_app` (`standing_work.py:248-264`) requires `resolve_app` to succeed, which structurally rejects an agent slug. A member app registering through the same door inherits that refusal.
2. **The unattended path is toolless by construction.** `run_bounded_derive_turn` never passes `tools=` (`api/services/derive_turn.py:91-97`). `resolve_turn_reach`'s docstring (`lane_runner.py:692-696`) names this as the structural reason *a clock plus a credential stays impossible*. An app's standing work therefore **cannot** reach a connector unattended, which is D4's safety property enforced by construction rather than by policy.

⚠️ **One honest gap, recorded because it bites prose work specifically:** a prose (`md`) standing run has **no machine contract check**. `run_bounded_derive_turn` tests only the `NO_CHANGE` sentinel (`derive_turn.py:103-104`); `shape` validation (`map_structured`, `standing_work.py:786-845`) applies only to csv/json/txt — exactly the paths that never reach the derive. `standing_executor` is declared by **zero** apps, so `standing_executor_for_app` always falls through to the resident.

---

## 8. D6 — Three origins, and the first one to build is not the builder

The frame doc §7.2 names three origins. Their build order is not their naming order:

| Origin | What it needs | First user |
|---|---|---|
| **Chosen** — a starting shape at signup | a small catalog of declarations | minute zero; nothing to derive from |
| **Derived** — proposed from work already done | judgment over existing files | the member who has worked a while |
| **Authored** — described in conversation, or edited | a lane that writes `_app.yaml` | the member fixing a wrong guess |

⭐ **The builder as a surface someone visits is the smallest part of this.** Derivation needs no builder; the catalog needs no builder. The builder is the **escape hatch that makes the other two safe** — if a derived app is slightly wrong it must be fixable, or the derivation will not be trusted.

**Authored costs nearly nothing** and should ship first for that reason: a lane writing a declaration file is `WriteFile`, and `creating-skills` already teaches the adjacent shape. **Chosen** is the onboarding win. **Derived** is the differentiated one and is gated on §9's memory question.

---

## 9. What is open — named, not hidden

1. ⭐⭐⭐ **What makes two pieces of work one app rather than two?** If boundaries are emergent (D4), something must make an app cohere or "app" means nothing. Working intuition: **the who** — one app is one agent's remit. **Unsettled, and it is the load-bearing definition of the core object.** Operator's call.
2. ⭐⭐ **Accumulation does not exist.** The frame promises an agent that *"accumulates judgment about this specific work."* `agents/{slug}/memory/` has **no writer and no reader** (§1.5). Either the promise is deferred or this ADR grows a memory mechanism. **The "derived" origin depends on it.**
3. **The component vocabulary** (D3.b) — the riskiest single decision; see §5.
4. **The quiet discipline.** A standing watcher's failure mode is surfacing noise to prove it is alive. *"Most of the time it says nothing"* must be a design goal. Judgment, not mechanism — unscaffoldable, and the reason this is a bigger build than it looks.
5. **Residents compound.** Six apps is six agents entitled to speak. Staffed or surveilled is not obvious; it may argue for few apps, or for pooled raising.
6. **Property extraction is a bounded kernel cost.** Properties a model can judge by looking are unlimited; those needing an extractor (EXIF, PDF fields, media duration) are finite. Apps declare freely and are told what is unavailable — which makes the roadmap **demand-measured** rather than guessed. Same logic for a missing verb.
7. **The word writes a check.** "App" imports expectations about installing, opening and closing that are wrong here. Probably right anyway — it is the only word that gets someone to try it — but deliberate, not backed into.
8. **Generic apps are worse than none.** A first app that is a folder structure and a prompt is something a member can already do in Finder.

---

## 10. Owed — pre-existing defects this ADR must NOT absorb

Found during the audit. Each is real, each predates this work, and **none is caused or fixed here.**

1. ⚠️ **`api/test_adr338_surface_registry_parity.py` is RED at baseline — 15 passed, 2 failed.** Verified directly. `connectors` is a **phantom slug**: in the FE union (`web/types/surface.ts:91`) and allowlist (`:133`), absent from the served roster (`stage: internal`, `kernel_surfaces.py:832`), absent from the component registry. Clicking anything naming it opens an **empty window** (`Launcher.tsx:268` passes it, `SurfaceViewport.tsx:185` renders `null`). ADR-425 lineage, stranded when ADR-645 deleted the Settings → Connectors door. **This ADR touches that gate; it must be green on its own merits first, or its green here is meaningless.**
2. **The gate's exhaustiveness claim is false.** Its docstring (`:24-26`) relies on a `tsc` check over `Record<KernelSurfaceSlug, ComponentType>`; the type is `Partial<Record<...>>` (`SurfaceRegistry.tsx:101`), so **no** exhaustiveness coupling exists. Assertion 6 is the only thing holding that leg.
3. **`surfaces[]` is untyped at the API-client boundary.** `web/lib/api/client.ts:1606-1620` omits the single most load-bearing field; `web/lib/compositor/client.ts:70` launders it with `as unknown as`.
4. **The skills index docstring is stale** — claims 11 kernel skills and a 3,947/4,000 measurement; there are **12** (§1.1). The unbound lane is at or past its ceiling.
5. **`metadata.needs` has zero live declarations** (§1.1) — live, untested against a real skill.
6. **`run_lane_turn` has no production caller** (`lane_runner.py:1612`) — ~250 lines duplicating the streaming loop; the live path is `run_lane_turn_stream`. **Re-verified 2026-09-16** (`grep -rln run_lane_turn api/ --include=*.py` → tests and probes only). ⚠️ The duplication is not inert: the two loops are byte-identical at the `if not routed.tool_calls:` break, so a bug found on the sync path is LIVE on the streamed one. `9005b23` had to patch both, and its gate falsifies the stream-only revert specifically — a fix on the sync path alone would have left the live surface silent.
7. **`scheduling.__all__` names four symbols that do not exist** (`:416-423`) — `from services.scheduling import *` would `AttributeError`; the module's actual live exports are absent from it.
8. **`register_app(name=...)` and `standing_executor=` never fire** — no call site passes either (`grep` → zero); `token_profile` on every agent row has **no reader**.
9. **`web/components/library/README.md` documents ~15 files deleted in `e18e178`**, and `chat-drawer` is declared backend-side (`kernel_surfaces.py:954`) with no `ChromeRegistry` entry — silently skipped at `ShellCompositor.tsx:97`.
10. **`test_adr341_two_settings_doors.py` asserts rows that no longer exist** (`mandate`, `identity`) — likely red, not run here.
11. **Data-heavy work has a located kernel gap** (analysis §11, `b937e2e`; fix `9005b23`). Measured, not argued: a 5,000-row CSV probe (287,762 chars, `api/scripts/operator/probe_data_heavy_lane.py`) showed ADR-648's pagination working perfectly — the lane followed `next_offset` through THREE windows and read **100%** of the file — and then died on `_LANE_MAX_TOKENS = 4096`, returning `finish_reason='length'` with empty text. **The substrate carried the data; the turn could not carry the answer.** The gap is that the agent is being asked to do the ARITHMETIC (summing 1,010 rows is not judgment), so the located verb is a *projection* over a shaped file — never a database, which would break portability and need a second attribution plane beside ADR-209. Row-grain append is the deferred sibling. ⚠️ **A verb is NOT proposed here — demand-pull (ADR-337 D6, the ADR-225 lesson).** Eight of the registered primitives are already marked *"none — registered, no live surface"* in primitives-matrix.md (~28% of the surface), and the demand behind this one is a single synthetic probe in a workspace holding five CSVs totalling under 2KB. The probe is the right artifact to keep: it costs nothing idle and proves the gap on demand, where a verb would cost a line in every tool payload forever. Build it when a real member, or a real app, is actually blocked. ⚠️ **Consequence for this ADR's roadmap: a data-heavy app cannot be the first app shipped** — a CRM is exactly what a non-technical member expects an app to be, and it is the one shape that fails until the verb lands (§9.8's "generic apps are worse than none", inverted).

12. **Is provenance the only edge type the substrate carries, or the first of several?** ⭐ **Unsettled, and more load-bearing than item 11.** A data-heavy app's real structure is not its rows — it is its edges (*this deal belongs to this client; these notes are about that deal*). YARNNN **already has a relationship primitive**: `derived_from` (ADR-448, a JSONB path list on every revision) is read by `trace`, `list_revisions`, and `list_dependents` — which has two live callers in the delete path (`routes/documents.py:1077`, `:1144`) powering the *"N files were made from this"* warning. SCHEMA-NOTES states the position outright: *"importance is a **GRAPH position** (legibility=edges, protection=powerbox grants, version-coupling=data-ref pins), never a folder class."* **The substrate is already a graph over files.** What it lacks is *arbitrary* edges — `derived_from` means one thing (X was made from Y) and cannot express "X is the client of Y."

    The fork: **one edge type, or several?** Provenance is special because it is **witnessed** — automatic, unfalsifiable, the system recording what it was present for. Any other relation is **asserted** — a claim someone makes, which can be wrong, go stale, and needs maintaining. Collapsing the two into one graph would break, at the one place it is currently clean, the separation the canon draws everywhere else: Axiom 1's ninth sub-clause (raw observation vs derived understanding), `revision_kind`'s `authored | observation | derivation` split (`authored_substrate.py:221`), ADR-335's *"reality enters only as attributed observation."* A delete-confirm would have to distinguish *"this was made from that"* from *"someone claimed these are related"* — a distinction a member should not have to hold.

    **Working position (not a ruling): one edge type stays.** Most relationships a data-heavy app needs are already expressible as **path + content** — `clients/acme/deals/q3.md` encodes its parent in its path, which is ADR-384's *"directory is meaning"*, and the join is a `ListFiles` prefix, not a foreign key. ⚠️ **The case to watch for is MANY-TO-MANY** (one deal involving three people, each on other deals). One-to-many is a folder; many-to-many is where a filesystem genuinely stops being enough, and no amount of path structure fixes it. **That, not "a CSV was big," is the signal that would reopen this.**

---

## 11. Gate

`api/test_adr653_app_is_a_program.py`, falsified in both directions before it ships:

1. A member `_app.yaml` naming a **kernel** agent slug is refused (D2) — falsify by declaring one and asserting red.
2. A declaration carrying a reach, tool or engine key is refused by the whitelist (D1/D6) — falsify by adding one.
3. `register: "composition"` is in the validated set AND has a runtime reader (D3.a) — falsify by removing the read.
4. Every `surface.sections[].kind` resolves in the component vocabulary, and an unknown kind renders the honest miss rather than a blank (D3.b).
5. A declared app slug foregrounds from the Launcher (D3.c), and the ADR-338 three-way lockstep over **kernel** surfaces is unchanged.
6. An app's standing declaration resolves its executor through the app, never an agent slug (D5).
7. The `AGENT_ROW_KEYS` whitelist is unchanged and no authority key appears on any member row (§6, the D3.a ratchet).

⚠️ **Preconditions**: §10.1 must be green first. A gate that crashes reports nothing (the ADR-648 lesson), and a script-shaped gate reports a count, not an exit code.

---

## 12. The one-line statement

**An app is an AI-native program a member scaffolds — a versioned declaration file naming an agent, the skills it works by, and a surface that shows its state — reintroducing member agents as the app pairing ADR-599 D2 held them for, and promoting composition to the validated register ADR-435 declined to name, on the ground that an app surface composes what no mirror shows; the declaration carries rhythm and region and never reach, the agent stays identity ⊕ character ⊕ engine, and the member remains the only thing that pins what any of it may touch.**
