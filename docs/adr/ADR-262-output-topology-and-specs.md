# ADR-262: Output Topology and Specs — Filesystem-Native Output Without Registries

**Status**: Proposed 2026-05-08
**Companion ADRs (atomic together)**:
- ADR-260 — Real-Time Reviewer Loop: Cron is a Nudge, Continuation is Not a Trigger
- ADR-261 — Recurrences as Prompts: Single Execution Shape

**Supersedes / replaces**:
- ADR-152 §"Directory Registry as runtime authority" (`directory_registry.py::WORKSPACE_DIRECTORIES` as the dispatch-time authority for path resolution and structural validation) — registry becomes operator-readable conventions in markdown; runtime no longer consults a Python registry for path decisions.
- ADR-149 §"DELIVERABLE.md as a quality contract dispatched by output_kind" — DELIVERABLE.md (now reframed as a "spec" in this ADR) survives as operator-authored markdown, but is no longer dispatched by output_kind. Recurrence prompts cite specs explicitly.
- ADR-167 v9.1 §"KindMiddle dispatch on output_kind" — `KindMiddle` switching on `output_kind` is reshaped: detail middles dispatch on the recurrence's *output shape inferred from the prompt + spec*, not a registry enum. Implementation detail per §6.
- ADR-213 §"task pipeline auto-composes produces_deliverable outputs as a post-step" — auto-dispatch of compose deletes; compose becomes an ordinary primitive the Reviewer calls when the prompt directs it.

**Amends**:
- FOUNDATIONS Axiom 1 — strengthens the corollary "Substrate grows from work, not from signup scaffolding" by extending it to: *the system prescribes the minimum structure required for filesystem-native operation; the rest is operator-authored or bundle-shipped.*
- ADR-209 (Authored Substrate) — restates §D5: the revision chain *is* the cross-session continuity record (ADR-260 D1, ADR-261 D9, this ADR D5).

**Preserves**:
- The compose engine itself (`render/compose.py`, `api/services/compose/`, ADR-148/170/177/213 mechanical pipeline) — ratified as one of many possible primitives the Reviewer's loop calls. Compose is mechanical rendering; it survives because rendering is genuinely deterministic work worth keeping deterministic. What changes is the *trigger* — compose is invoked by the Reviewer's prompt naming it as a step, not by task-pipeline post-step auto-dispatch.
- ADR-176 specialist roles (researcher, analyst, writer, tracker, designer, reporting + thinking_partner + 3 platform-bots).
- ADR-194 v2 Reviewer substrate.
- ADR-209 Authored Substrate.
- ADR-247 three-party narrative model.

---

## 1. Why this ADR

ADR-261 deletes `task_types.py`, `directory_registry.py`'s runtime dispatch role, and `recurrence_paths.py`. Together those three carried the "where does output land, what shape does it have" load. The deletion is correct under the unified model — but it leaves a real question open: **how does a recurrence prompt encode filesystem-native, multi-file, structured-output expectations without the registries?**

This is where YARNNN must do more than Claude Code. Claude Code prompts are throwaway — output is the conversation, the user reads and moves on. YARNNN's filesystem is the substrate. A prompt that says "produce the daily briefing" is hand-wavy in our world: where does it land, what does it look like, how does it relate to the prior version, does it overwrite or accumulate, what files does it touch.

ADR-262's job is to answer that question without re-implementing what we just deleted. The framing the operator confirmed (2026-05-08):

> "minimal amount of manifest and conventions to 'work with a file system' on its own accords … this seems to be the axiomatic, rather more fundamental direction that actually empowers our agents to be MORE file system native than less."

Under this ADR there are two layers, named explicitly. Both are operator-authored markdown. Neither is a Python registry.

---

## 2. Decision

### D1 — Layer A: filesystem topology (mechanical, lives in CONVENTIONS.md)

A small set of universal filesystem conventions — declared once, applied workspace-wide — covers where things live and how they relate. These conventions are **operator-readable markdown**, not Python registries with enum dispatch.

The canonical home: `/workspace/_shared/CONVENTIONS.md` (this file already exists per the operator-authored substrate set; it gains the topology section).

The starting set of conventions (ratified for alpha; extensible per workspace or per program bundle):

```markdown
## Filesystem Topology

### Composed reports (replacive — each fire produces a new dated artifact)
- Path: `/workspace/reports/{slug}/{YYYY-MM-DD}/output.md`
- Composed HTML (when produced): `/workspace/reports/{slug}/{YYYY-MM-DD}/output.html`
- Manifest: `/workspace/reports/{slug}/{YYYY-MM-DD}/manifest.json` (sections, assets, compose engine version, attribution)
- Latest pointer: `/workspace/reports/{slug}/latest/` (symlink-equivalent — substrate-side mechanism per implementation)
- Per-report feedback: `/workspace/reports/{slug}/_feedback.md`

### Accumulated context (additive — entities accumulate over time)
- Per-entity: `/workspace/context/{domain}/{entity}.{md|yaml}` — `.md` for prose, `.yaml` for structured records
- Cross-entity synthesis: `/workspace/context/{domain}/_*.md` — underscore prefix indicates synthesis
- Per-entity assets: co-located with entity file (e.g., `{entity}-favicon.png` adjacent to `{entity}.md`)
- Per-domain feedback: `/workspace/context/{domain}/_feedback.md`

### Operator authored (the operator's declarations)
- `/workspace/_shared/MANDATE.md`
- `/workspace/_shared/IDENTITY.md` (or whatever the active program names)
- `/workspace/_shared/BRAND.md`
- `/workspace/_shared/AUTONOMY.md` (prose) + `/workspace/_shared/_autonomy.yaml` (machine-parsed)
- `/workspace/_shared/CONVENTIONS.md` (this file)
- `/workspace/_shared/PRECEDENT.md`
- `/workspace/review/IDENTITY.md`, `/workspace/review/principles.md`
- Specs: `/workspace/specs/{name}.md` (per Layer B)

### Reviewer's own substrate
- `/workspace/review/IDENTITY.md` (operator-authored)
- `/workspace/review/principles.md` (operator-authored)
- `/workspace/review/decisions.md` (Reviewer-authored, append-only)
- `/workspace/review/reflections.md` (Reviewer-authored, append-only)

### Recurrences
- Single canonical file: `/workspace/_recurrences.yaml`
```

These are **conventions, not enforced rules.** The Reviewer reads them at session start (or as needed), follows them when its prompt does not override. A recurrence prompt may direct writes to non-conventional paths if the work calls for it; the convention is shared knowledge between operator and Reviewer, not a runtime guard.

**What this dissolves**: `directory_registry.py::WORKSPACE_DIRECTORIES` — the registry that previously declared per-directory structure. Survives only as a thin metadata helper if needed for FE rendering (e.g., what icon to show next to a directory in the file tree). Runtime dispatch by directory shape: gone.

#### D1 sub-clause: conventional paths are slug-templated structurally; non-conventional paths are operator intent

Conventional paths in CONVENTIONS topology contain only slug + runtime variables (date, entity name, domain) — no free-text. Examples:

- `/workspace/reports/{slug}/{YYYY-MM-DD}/output.md` — `{slug}` is the recurrence's slug field; `{YYYY-MM-DD}` is the runtime date. Both substrate-level data; no free-form authorship.
- `/workspace/context/{domain}/{entity}.md` — `{domain}` is recurrence-declared (or CONVENTIONS-declared per program bundle); `{entity}` is workspace-substrate-derived (the entity exists; the path follows the entity's slug).

For conventional outputs, **the Reviewer interpolates the convention against substrate-level data — it does not free-form-author the path.** This is structural correctness without a registry: the convention is markdown, the substrate-data is real, and the path is determined by the join of the two. Typo-resistance comes from the fact that the slug, the date, and the entity are not strings the Reviewer types — they're structured fields.

For non-conventional paths, the recurrence prompt explicitly names the path. This is the operator's intent — they wanted writes somewhere outside the conventional topology, and they say so. The framework does not validate; the prompt is the authority. If the prompt typos a path, the operator catches it during review (the audit log shows the wrong-path write attributed to whoever directed it).

The honest split: **conventional = slug-templated structurally; non-conventional = operator intent in the prompt.** Both shapes are valid; their correctness mechanisms are different and named here so future ADRs don't conflate them.

### D2 — Layer B: semantic shape (lives in prompts and operator-authored specs)

The semantic shape of a recurrence's output — its sections, its tone, its required fields, its quality bar — lives in the **prompt** or in **operator-authored spec docs that the prompt cites**. There are three patterns the prompt can use, in increasing structure:

**Pattern (i) — Inline**: prompt directly describes the output.

```yaml
- slug: morning-summary
  schedule: "0 7 * * *"
  prompt: |
    Write a 300-word morning summary covering: (1) yesterday's market close,
    (2) overnight news affecting universe tickers, (3) today's pre-market
    movers. Save to /workspace/reports/morning-summary/{YYYY-MM-DD}/output.md
    per CONVENTIONS topology.
```

**Pattern (ii) — Cite a spec doc**: prompt points at an operator-authored markdown file describing structure.

```yaml
- slug: weekly-market-conditions
  schedule: "0 8 * * 1"
  prompt: |
    Produce the weekly market-conditions report. Follow the spec at
    /workspace/specs/market-conditions.md. Save to
    /workspace/reports/weekly-market-conditions/{YYYY-MM-DD}/output.md
    per CONVENTIONS topology. Compose to HTML via the compose primitive
    after writing all section partials.
```

The spec at `/workspace/specs/market-conditions.md`:

```markdown
# Market Conditions Report — Spec

## Purpose
Weekly synthesis of market conditions for the operator's decision-making.

## Required sections
- `## Market Summary` — 200 words, headline finding first paragraph
- `## Notable Movers` — bullet list, top 5 universe tickers by % move
- `## Sector Rotation` — paragraph or table on sector flows
- `## Watch List` — bullet list of tickers approaching signal entry conditions

## Quality criteria
- Cite specific tickers with current prices in parentheses
- Reference live data — never stale-cache language
- Length: 600-1000 words total
```

The Reviewer reads both the prompt and the spec, produces the output that conforms.

**Pattern (iii) — Cite a concrete prior example**: prompt points at last week's output as the structural reference.

```yaml
- slug: weekly-portfolio-review
  schedule: "0 17 * * 5"
  prompt: |
    Produce this week's portfolio review. Match the structure of last week's
    output at /workspace/reports/weekly-portfolio-review/latest/output.md.
    Save to /workspace/reports/weekly-portfolio-review/{YYYY-MM-DD}/output.md
    per CONVENTIONS.
```

The Reviewer reads the prior, infers structure from it, replicates with this week's data.

**All three patterns are prompt-level. None require a Python registry. None require enum dispatch.** Specs are markdown the operator authors. Prior examples are substrate the system already produced.

### D3 — Specs are operator-authored substrate, not framework structure

Specs live at `/workspace/specs/{name}.md`. They are markdown files. They are operator-authored (or bundle-shipped at activation, per ADR-261 D6).

There is **no schema for specs.** A spec is whatever markdown the operator writes that helps the Reviewer (or specialists) produce conforming output. If the operator writes a spec with section headings, the Reviewer follows section headings. If the operator writes a spec with field-by-field requirements, the Reviewer fills fields. If the operator writes a spec in plain prose ("the report should feel like a research analyst's note"), the Reviewer matches the tone.

**There is no `specs.py` registry, no schema validator, no enum of spec types.** Operators can author specs of arbitrarily different shapes for different recurrences. The framework's role is zero — recurrences cite specs by path; the Reviewer reads them; output conforms.

### D4 — Compose is a primitive AND an opt-out structural default

`Compose` survives as a callable primitive that takes section partials + manifest data and produces composed HTML via the existing `render/compose.py` engine (preserving ADR-148, ADR-170, ADR-177, ADR-213 mechanical pipeline).

**Compose is opt-out by default**, triggered structurally — not by free-text prompt content. The trigger is mechanical (no LLM judgment): when a Reviewer session writes section partials matching the deliverable convention (presence of `sections/*.md` files in `/workspace/reports/{slug}/{date}/`) and the session is closing, the framework auto-runs Compose unless the recurrence prompt explicitly opts out.

```yaml
# Default: compose runs automatically when section partials are detected.
- slug: weekly-market-conditions
  schedule: "0 8 * * 1"
  prompt: |
    Produce the weekly market-conditions report per the spec at
    /workspace/specs/market-conditions.md. Write each section to
    /workspace/reports/weekly-market-conditions/{YYYY-MM-DD}/sections/*.md.
  # No explicit compose step needed — auto-detected from section partials.

# Opt-out: prompt explicitly disables auto-compose.
- slug: raw-research-log
  schedule: "0 17 * * 1-5"
  prompt: |
    Append today's research notes to /workspace/notes/research.md.
    Skip composition — this is a running log, not a deliverable.
  options:
    skip_compose: true
```

The opt-out mechanism is one machine-parsed field on the recurrence record (`options.skip_compose: true`). When unset (the default), Compose runs as a post-write structural hook if section partials exist. When set, Compose does not run regardless of substrate shape.

**Why opt-out, not opt-in**: prompts drift. Operators who edit a recurrence prompt will forget to re-add a "compose at end" step; bundle-shipped prompts will get diverged-from over time. Auto-compose triggered by substrate shape (rather than by prompt text) means the operator gets HTML when section partials exist, period. Failure mode is now "operator gets too much HTML" (recoverable — they add `skip_compose`) rather than "operator gets raw markdown when they expected HTML" (silent, harder to spot).

**Compose is also callable as an explicit primitive** (`Compose(sections=[...], manifest={...}, output_path="...")`) for cases where the Reviewer needs to compose mid-session (e.g., compose an interim version, then continue working). The primitive surface and the structural auto-trigger share the same engine — there is no separate code path.

**The compose engine's mechanical innards (section kind dispatch, structured-data renderers, content-addressed cache per ADR-213) are unchanged.** What this ADR changes is the *trigger surface*: structural auto-trigger by default + explicit primitive when needed, replacing ADR-213's task-pipeline-post-step coupling.

### D5 — Authored Substrate as the continuity backbone

Restated from ADR-260 D1 and ADR-261 D9:

Every revision to substrate is attributed (per ADR-209). The revision chain is the cross-session continuity record. A Reviewer waking on the next cron fire reads the head revision of the relevant substrate, sees prior revisions' authored messages, and knows what its prior selves did.

In this ADR's framing, this means: **conventions, specs, and recurrence outputs all participate in the same authored-substrate plane.**

- Conventions: revisions show how conventions evolve (operator updates `CONVENTIONS.md`; revision attributes to operator with message describing the change).
- Specs: same — operators evolve specs; revisions log evolution.
- Outputs: each fire produces a new dated artifact (`reports/{slug}/{date}/output.md`); each revision of that artifact attributes to `reviewer:{occupant}` or `agent:{slug}`. If an output is amended after the fact (e.g., operator-corrected), the amendment is its own revision with operator attribution.

This deletes the need for separate "version metadata" or "audit logs" — the substrate itself is the audit log. Per ADR-209's commitment, this is enforced at the write-path boundary, not by convention.

### D6 — Bundle activation seeds conventions, specs, recurrences

Per ADR-261 D6 (workspace init), program bundle activation:
1. Copies the bundle's `reference-workspace/` files into `/workspace/` (verbatim).
2. Merges the bundle's `recurrences.yaml` into `/workspace/_recurrences.yaml`.

Bundles can ship:
- A `CONVENTIONS.md` that extends the workspace-default conventions with program-specific topology (e.g., alpha-trader bundle ships `/workspace/_shared/CONVENTIONS.md` adding `## Trading Topology` for `/workspace/context/trading/` structure).
- Spec docs at `/workspace/specs/{name}.md` — the bundle's pre-authored specs for its recurrences.
- Recurrence entries in `recurrences.yaml` whose prompts cite the shipped specs.
- Reviewer substrate: `/workspace/review/IDENTITY.md`, `/workspace/review/principles.md`.
- Operator substrate skeletons or pre-filled: MANDATE, BRAND, _operator_profile, _risk, etc.

After activation, the operator has a fully-loaded operation. They modify what the bundle laid down to customize. The Reviewer wakes (addressed by operator's first chat, or scheduled cron fire) and the mandate-driven loop runs.

**ADR-226's three-tier `canon | authored | placeholder` frontmatter system is dissolved** (per ADR-261's amendment). Every authored substrate file is just markdown the operator owns. The Reviewer reads bundle-shipped MANDATE the same way it reads operator-revised MANDATE — they're both `MANDATE.md` content; the revision log distinguishes "this content was forked from bundle" (`authored_by="system:bundle-fork"`) from "this content was operator-edited" (`authored_by="operator"`). One file, one read path, attribution captures the distinction.

---

## 3. The shift in burden — and how it's mitigated

### The shift

**Today**: framework knows a lot. Registries are dense. Operator chooses a task type from a catalog and gets a structured invocation back.

**Under ADRs 260-262**: framework knows almost nothing about output shape. CONVENTIONS.md is short. The compose engine is mechanical. Operator (or program bundle) authors more — recurrence prompts cite specs the operator wrote; CONVENTIONS encodes filesystem-topology choices.

This is real. It is the same tradeoff Claude Code makes: the user does more authoring of intent; the framework does less prescriptive structuring. We move closer to that pole.

### The mitigation: program bundles do the authoring

Program bundles (per ADR-222 + ADR-223 OS framing) ship the spec docs AND the recurrence prompts AND the CONVENTIONS additions. The alpha-trader bundle ships:

- `/workspace/specs/market-conditions.md`
- `/workspace/specs/portfolio-review.md`
- `/workspace/specs/ticker-snapshot.md`
- `/workspace/specs/performance-rollup.md`
- `/workspace/specs/weekly-review.md`
- A `/workspace/_shared/CONVENTIONS.md` extending the default with trading topology
- A `recurrences.yaml` with morning-reflection, morning-calibration, signal-evaluation, track-universe, outcome-reconciliation, weekly-review entries — each prompt citing the shipped specs by path

After activation, the alpha-trader operator has a fully-loaded operation. They customize by editing the markdown specs (or recurrence prompts). They author from scratch only when they want something the bundle didn't ship.

This preserves the "drop into a working operation" experience while moving the locus of structure into operator-readable markdown rather than framework-code registries.

### Why this is *more* filesystem-native, not less

The Reviewer reading `/workspace/specs/market-conditions.md` is the same act as the operator reading it. There is no privileged framework-internal representation that operators can't see. There is no "look at the registry to know what's possible" — operators look at their workspace, see the conventions, see the specs, see the recurrences, and that's the entire system.

The agents are *more* filesystem-native because they work with the same artifacts the operator works with, in the same shape. No translation layer. No registries-vs-files duality.

---

## 4. What this fixes (validation)

### 4.1 Operator authoring a new recurrence (alpha-trader)

Operator (in chat): *"I want a daily 4pm summary of intraday signal hits for next-day prep."*

YARNNN (orchestration surface, per ADR-235 D1.c routing through `Schedule`):
1. Drafts a recurrence prompt that cites a spec (creating the spec if needed):
   - Recurrence: `slug: daily-signal-recap`, `schedule: "0 16 * * 1-5"`, `prompt: "Summarize today's intraday signal hits. Follow the spec at /workspace/specs/daily-signal-recap.md. Save to /workspace/reports/daily-signal-recap/{YYYY-MM-DD}/output.md."`
   - Spec at `/workspace/specs/daily-signal-recap.md`: drafted from operator's chat description.
2. Confirms with operator. Operator adjusts. Once confirmed:
3. Calls `Schedule(action="create", slug="daily-signal-recap", schedule="0 16 * * 1-5", prompt=...)`.
4. Calls `WriteFile(path="/workspace/specs/daily-signal-recap.md", content=...)` with `authored_by="operator"` (per ADR-235's chat-routed feedback shape).

Recurrence is live. Tomorrow at 4pm, the Reviewer wakes with that prompt, reads the spec, produces the output. No registry. No enum.

### 4.2 Operator changing output shape later

Operator (in chat): *"I want the daily-signal-recap to also include what positions I should consider closing tomorrow."*

YARNNN:
1. Reads `/workspace/specs/daily-signal-recap.md`.
2. Drafts an updated spec adding the new section.
3. Confirms with operator.
4. Calls `WriteFile(path="/workspace/specs/daily-signal-recap.md", content=updated)` — the revision log captures the change with operator attribution.

Next time the recurrence fires, the Reviewer reads the updated spec, produces output with the new section. The recurrence's `prompt` field never changed — only the spec it cites did.

### 4.3 Bundle activation produces a working operation

Operator activates `alpha-trader` bundle. Bundle fork:
1. Copies bundle's `reference-workspace/` files (specs, conventions, mandate skeleton, identity skeleton, brand skeleton, autonomy, principles).
2. Merges bundle's `recurrences.yaml` into `/workspace/_recurrences.yaml`.

Operator opens the feed. Their first chat: *"morning, what's the state of things?"*

Reviewer wakes (addressed). Reads MANDATE, IDENTITY, principles, _performance.md (if it exists yet — empty on day 1), the active recurrences. Replies with a status overview. Loop closes.

At 6am tomorrow, the morning-calibration recurrence fires. Reviewer wakes (scheduled). Reads the recurrence's prompt. Reads `_performance.md` (still empty). Reasoning bubbles back: *"No realized P&L to calibrate against yet. Re-engage after first execution."* Loop closes.

This is the "fully-loaded operation from activation" experience preserved despite the framework holding less structure. The bundle did the authoring.

---

## 5. What gets deleted

| Component | Reason |
|---|---|
| `directory_registry.py::WORKSPACE_DIRECTORIES` runtime dispatch role | D1 — CONVENTIONS.md replaces it for path conventions; survives as thin FE-metadata helper if needed |
| Per-directory `entity_assets` / `assets_folder` flags as runtime dispatch | D1 — convention-shaped, not flag-shaped |
| `recurrence_paths.py` natural-home path resolution by output_kind | D1 — paths are prompt-named per CONVENTIONS |
| `task_types.py::STEP_INSTRUCTIONS` per task type | Per ADR-261 D8 — prompts encode their own steps |
| `task_types.py::TASK_TYPE_CATEGORIES` and `output_category` fields | Per ADR-261 D8 |
| Auto-dispatch of `compose` as task-pipeline post-step (per ADR-213) | D4 — compose is a primitive the prompt names |
| Three-tier `canon | authored | placeholder` frontmatter parser | Per ADR-261 D6 amendment to ADR-226 |
| `is_skeleton_content` + `_strip_tier_frontmatter` per ADR-226 | Same |
| `programs.py::fork_reference_workspace` tier-based decisions | Same — fork copies all bundle files; revision log captures attribution |

`directory_registry.py` survives as a near-empty module (or is fully deleted) depending on what FE metadata is genuinely needed. The Python code that today *dispatches* by directory metadata: gone.

---

## 6. Open questions (resolved at implementation time)

### 6.1 KindMiddle dispatch on the FE

ADR-167 v9.1 introduced `KindMiddle` switching on `output_kind` for the `/work` detail surface. With output_kind dissolved, the FE needs another axis to dispatch detail-mode rendering. Options:

- **(α) Infer shape from filesystem topology**: if the recurrence has a folder under `/workspace/reports/{slug}/`, render the latest output as a deliverable; if it has writes scattered across `/workspace/context/{domain}/`, render as accumulation tracking; if its prompt directs an `external_action`-shape primitive (submit_order, etc.), render as action.
- **(β) Optional metadata field on the recurrence**: `display_kind: report | tracking | action | maintenance` — operator-authored hint for FE rendering only, not consulted at execution.

I lean (α) for the structural cleanliness — the substrate's shape *is* the recurrence's nature; FE inferring it is consistent with the "filesystem is the substrate" principle. (β) is a fallback if (α) proves brittle.

This ADR does NOT pick. Implementation PR resolves at first FE touch.

### 6.2 Compose primitive's exact name and signature

The primitive is logically named `Compose`. Whether it lives at `api/services/primitives/compose.py` as a new file or extends an existing module is implementation choice. Signature shape: `Compose(sections: list[SectionRef] | str, manifest: dict, output_path: str)` or similar.

### 6.3 Latest pointer mechanism

The CONVENTIONS topology specifies `/workspace/reports/{slug}/latest/` as a "symlink-equivalent" for prior-output reference. The substrate-side implementation could be:
- **(α)** A real symlink (filesystem-native, requires storage-backend support).
- **(β)** A redirect indicator file that resolves at read time.
- **(γ)** A recurrence-level metadata pointer the FE/CONVENTIONS resolution consults.

Defer to implementation. The convention is what matters; the mechanism is incidental.

---

## 7. Out of scope (deferred to future ADRs if pressure)

- **Spec validation** — enforcing that an output conforms to a spec. Today: zero validation; the Reviewer is trusted. If post-alpha we observe drift, a future ADR introduces lightweight validation (e.g., section-heading match check).
- **Spec inheritance / composition** — operators may want shared spec fragments (`/workspace/specs/_shared/tone.md` cited by multiple specs). Currently a convention; operators can do this with markdown cross-references. A formal include mechanism is deferred.
- **Per-recurrence authored-by override on outputs** — currently the recurrence's outputs attribute to whoever wrote them (Reviewer, specialist). If operators want to claim authorship of an output (e.g., for publication), they can revise the file with operator attribution. A first-class "co-authored" attribution field is deferred.
- **CONVENTIONS schema** — currently CONVENTIONS.md is free-form markdown. If a future ADR wants machine-readable conventions (so FE can parse them), that's its scope.

---

## 8. Implementation plan (sketch — exact commits TBD in code PR)

This ADR's code changes land in the same follow-on PR as ADR-260 and ADR-261. High-level phases:

1. **CONVENTIONS.md scaffold**: workspace-default `CONVENTIONS.md` template lands in `workspace_init.py` skeleton scaffold. alpha-trader bundle's `CONVENTIONS.md` extends with trading topology.
2. **Specs scaffold**: alpha-trader bundle's `/workspace/specs/*.md` authored.
3. **Compose primitive**: extracted from task-pipeline post-step into a callable primitive. Tool definition added to `CHAT_PRIMITIVES`, `REVIEWER_PRIMITIVES`, and (selectively) `HEADLESS_PRIMITIVES` if specialists ever need to compose directly. Existing `render/compose.py` engine unchanged.
4. **`directory_registry.py` deletion or shrink**: delete dispatch role; preserve only what FE actually consumes.
5. **`KindMiddle` reshape per §6.1**: implementation-time choice.
6. **ADR-226 three-tier dissolution**: simplify `programs.py::fork_reference_workspace` and delete tier parser.
7. **Validation**: alpha-trader workspace activation produces working operation per §4.3; recurrence-prompt + spec citation flow per §4.1; spec-evolution flow per §4.2.

CHANGELOG entry. Test gate: regression tests assert `task_types.py` is gone, `directory_registry.py` no longer dispatches by output_kind, `compose` is callable as a primitive, alpha-trader bundle activation produces expected substrate.

---

## 9. The principle, restated

The framework prescribes the minimum needed to be filesystem-native: a small set of conventions in markdown, one canonical recurrence file, one compose engine. Everything else — output shape, semantic structure, quality bar — lives in operator-authored markdown that recurrence prompts cite. Specs are markdown. CONVENTIONS is markdown. Recurrence prompts are markdown. The Reviewer reads them all the same way the operator does.

Program bundles ship the markdown. Operators edit the markdown. The Reviewer follows the markdown. The framework holds the shape; the markdown holds the meaning.

This is YARNNN gearing toward Claude Code at the framework level, while preserving the filesystem-native commitment that makes YARNNN distinct: the substrate IS the artifact, the artifact IS the conversation, and the conversation IS the operation.
