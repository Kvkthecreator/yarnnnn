# Workspace Concept Components

**Version:** v1.2 (2026-05-24)
**Status:** Canonical
**Principle:** Render meaning from substrate, not the substrate itself.

> **v1.2 changes (2026-05-24 design polish):**
> (1) `DelegationCard` renamed to `AutonomyCard`; `/delegation` route renamed to `/autonomy` (redirect stub preserves bookmarks). Operator-surface label aligns with `_autonomy.yaml`. Schema field `default_delegation` kept — precise data-layer term.
> (2) New §5 Pace concept component (ADR-300) documenting `PaceCard` + `/pace` atomic surface.
> (3) New top-level §"Confirm-modal pattern for high-stakes dials" — `AutonomyCard` and `PaceCard` full variants now gate every mutation behind `ConfirmDialChange`. Single-click optimistic commits were too easy to flip accidentally.
>
> **v1.1 changes (ADR-266):** schema discipline locked in for `MANDATE.md`
> (one-sentence Primary Action); render contract closed for L3-on-L2-output
> via `web/lib/content-shapes/_render.ts`; per-card "Updated X by Y"
> footnote driven by ADR-209 revision metadata; bundled `/workspace/setup-bundle`
> endpoint replaces 7 round-trips with 1; cards accept optional `data` +
> `lastRevision` props (singular implementation: prop presence is the only
> signal — never surface-aware branching).

---

## Why this doc exists

The workspace files (`MANDATE.md`, `_autonomy.yaml`, `_pace.yaml`,
`IDENTITY.md`, `BRAND.md`, `principles.md`) are kernel substrate — they exist
for every workspace regardless of program. The operator should never see file
paths, state badges derived from file format, or raw markdown dumps. They
should see **what the files mean** in their vocabulary.

These files are rendered in multiple surfaces (the `/workspace` config page, the
chat context overlay, cockpit faces). Each surface assembles the same concept
components at different densities. This catalog is the contract that keeps them
aligned.

---

## Architecture: L2 Parsers + L3 Components

Per [ADR-245](../adr/ADR-245-frontend-kernel-three-layer-content-rendering.md):

```
Substrate file (workspace_files)
    ↓
L2 Parser (web/lib/content-shapes/{concept}.ts)
    — pure TypeScript, no React, no API calls
    — extracts structured data from markdown/YAML
    — shared across every surface that reads the file
    ↓
L3 Concept Component (web/components/workspace-concepts/{Concept}Card.tsx)
    — React component, surface-agnostic
    — accepts parsed data + a `variant` prop
    — knows nothing about which surface it is on
    ↓
Surface Assembly
    — /workspace page, context overlay, cockpit face
    — picks variant, wires edit callbacks
    — does not re-implement rendering logic
```

**The discipline:** If two surfaces render Mandate differently, the component has
a `variant` prop — not two implementations. If a surface needs a field the
component doesn't expose, the L2 parser adds the field and the component
renders it conditionally.

---

## Concept registry

### 1. Mandate

**File:** `/workspace/context/_shared/MANDATE.md`
**L2 parser:** `web/lib/content-shapes/mandate.ts`
**L3 component:** `web/components/workspace-concepts/MandateCard.tsx`
**Write contract:** `authored_prose` (Chat edits via `WriteFile` or `InferContext`)

**Schema (ADR-266 D3):** YARNNN's chat agent honors a canonical structure when
writing MANDATE.md so the L3 card has structured data to render. The schema is:

- `## Primary Action` — **one declarative sentence**, the value-moving external
  write the operation produces. Period. Not a paragraph; not multi-clause.
- `## Success Criteria` — terse bullet list. One line each.
- `## Boundary Conditions` — terse bullet list. One line each.

Other operator-authored sections (`## Edge hypothesis`, `## Rules of operation`,
`## Position lifecycle`, `## Daily Discipline`, etc.) are valid prose substrate
the LLM still reads in full — they're operator intellectual content, not schema.

**What the operator needs to see:**
- Primary Action (one sentence — the "what")
- Success criteria (top 3 bullets — the "how we'll know")
- Boundary count
- Whether it's set at all (empty state = clear CTA)

**Variants:**
| Variant | Used on | Shows |
|---|---|---|
| `full` | `/workspace` page | Primary Action callout + top 3 success criteria + boundary count + "Refine in chat" + "View full mandate ▾" expand |
| `compact` | context overlay | Primary Action headline only + "Not set" state |
| `headline` | cockpit face | Primary Action sentence, one line, truncated |

**Schema-met vs schema-absent paths (ADR-266 D4):** When `parse()` extracts a
one-sentence Primary Action (per the D3 schema), the card renders the structured
callout. When the section runs longer than one sentence (≥80% of cleaned content
must fit in the first sentence), the card degrades gracefully — first-sentence
excerpt + "Mandate set but not in canonical structure — refine in chat" hint +
"View full mandate ▾" inline expand. **Never dumps prose.** The "View full"
expand renders the source as preformatted text (markdown source visible) inside
a bordered scroll region.

**Empty state behavior:** All variants surface a "Set up in chat →" CTA when
`primaryAction` is null. The CTA text varies by variant density.

---

### 2. Autonomy

**Surface:** `/autonomy` (atomic kernel surface — renamed from `/delegation` 2026-05-24)
**File:** `/workspace/context/_shared/_autonomy.yaml` (machine-parsed, ADR-254)
**Prose doc:** `/workspace/context/_shared/AUTONOMY.md` (human/LLM reading only)
**L2 parser:** `web/lib/content-shapes/autonomy.ts` — reads `_autonomy.yaml`, strips tier frontmatter
**L3 component:** `web/components/workspace-concepts/AutonomyCard.tsx`
**Write contract:** `configuration` (Direct mutation via `setLevel()` — no chat needed, writes `_autonomy.yaml`; **full variant gates every mutation behind a confirm modal — see §"Confirm-modal pattern for high-stakes dials"**)

> **Naming note (2026-05-24):** the operator surface is "Autonomy" — aligned with the substrate file `_autonomy.yaml` and the operator's mental model. The schema field `default_delegation: bounded` is **kept** in the YAML — it's the precise data-layer term for the delegated level. The two terms compose: *autonomy* is the broader concept (the dial system), *delegation* is the specific level value. At the operator surface they read as synonyms because at the operator's level of abstraction they are.

**What the operator needs to see:**
- Current autonomy level (one of three per Commit F: Manual / Bounded / Autonomous)
- What that level means behaviorally (one sentence)
- The one-line consequence of switching levels (surfaced inside the confirm modal)
- Ability to change it inline with a confirm gate (Direct control — the only concept with Direct mutation)

**Variants:**
| Variant | Used on | Shows |
|---|---|---|
| `full` | `/autonomy` page | Three-option control (radio), behavioral description, ceiling if bounded, **confirm modal on switch** |
| `compact` | context overlay | Current level name + one-line description + change link |
| `chip` | chat composer | Level badge only (read-only, links to `/autonomy`) |

**Level descriptions (operator language, Commit F 2026-05-11):**
- `manual` → "Every action waits for your approval before executing."
- `bounded` → "Acts autonomously within your declared ceiling. Flags above it."
- `autonomous` → "Full delegation within declared boundaries. You review outcomes."

> **Commit F (2026-05-11)** retired `assisted` (no backend semantics distinct from `manual`) and collapsed `bounded_autonomous` → `bounded`. Three values, matching backend `_VALID_DELEGATION_LEVELS` in `api/services/review_policy.py`.

---

### 3. Principles

**File:** `/workspace/review/principles.md`
**L2 parser:** `web/lib/content-shapes/principles.ts`
**L3 component:** `web/components/workspace-concepts/PrinciplesCard.tsx`
**Write contract:** `configuration` (Chat edits; complex judgment framework)

**What the operator needs to see:**
- Active auto-approve thresholds per domain (e.g., "Trading: auto-approve below $500")
- Reject conditions (bullet list of what always gets blocked)
- Whether any domain has principles declared at all

**Variants:**
| Variant | Used on | Shows |
|---|---|---|
| `full` | `/workspace` page | Per-domain thresholds + reject conditions + "Refine in chat" |
| `compact` | context overlay | Key threshold per domain, one line each |
| `headline` | cockpit face | "N domains · ceiling $X" summary line |

---

### 4. Identity + Brand

**Files:** `/workspace/context/_shared/IDENTITY.md` + `/workspace/context/_shared/BRAND.md`
**L2 parsers:** `web/lib/content-shapes/identity.ts` + `web/lib/content-shapes/brand.ts`
**L3 component:** `web/components/workspace-concepts/IdentityBrandCard.tsx`
**Write contract:** `authored_prose` (Chat edits via `InferContext`)

**Why merged:** Both are operator-authored prose with no discrete schema. Both have
the same empty state ("Not set → Set up in chat"). Splitting them into two cards
on the same surface adds visual noise without operator value. A future program
that needs them split (e.g. a multi-voice content operation) can introduce
separate components at that point.

**What the operator needs to see:**
- Whether identity is authored (first substantive line of IDENTITY.md)
- Whether brand voice is declared (first rule or voice descriptor from BRAND.md)
- Combined "not set" state when neither is authored

**Variants:**
| Variant | Used on | Shows |
|---|---|---|
| `full` | `/workspace` page | Identity excerpt + brand voice excerpt + "Refine in chat" per file |
| `compact` | context overlay | Single-line summary: "Identity: set · Brand: skeleton" |

---

### 5. Pace

**Surface:** `/pace` (atomic kernel surface — ADR-300)
**File:** `/workspace/context/_shared/_pace.yaml` (machine-parsed, operator-only — path in `DEFAULT_REVIEWER_WRITE_LOCKS`)
**L2 parser:** `web/lib/content-shapes/pace.ts` — reads `_pace.yaml`, strips tier frontmatter, round-trip-preserves `every` + `monthly_budget_usd`
**L3 component:** `web/components/workspace-concepts/PaceCard.tsx`
**Write contract:** `configuration` (Direct mutation via `setKind()` — routes through `writeShape('pace', ...)` per ADR-245 D5; **full variant gates every mutation behind a confirm modal — see §"Confirm-modal pattern for high-stakes dials"**)

**What the operator needs to see:**
- Current pace kind (one of four: Weekly / Daily / Hourly / Continuous)
- What that kind means behaviorally — drain frequency cap (one sentence)
- One-line consequence of switching kinds (surfaced inside the confirm modal — cost implications front-and-center)
- Secondary fields if present (`every`, `monthly_budget_usd`) — read-only display, edit-via-chat per ADR-300 D2
- Ability to change it inline with a confirm gate

**Variants:**
| Variant | Used on | Shows |
|---|---|---|
| `full` | `/pace` page | Four-option control (radio), description, secondary fields if present, **confirm modal on switch** |
| `compact` | context overlay (not yet wired) | Current kind + one-line summary + change link |
| `chip` | not yet wired (reserved for future composer chip) | Kind badge only, deep-link to `/pace` |

**Kind descriptions (operator language):**
- `weekly` → "Reviewer wakes ~7×/week. Lowest cost; longest latency for paced work."
- `daily` → "Reviewer wakes ~24×/day. Default for most operators."
- `hourly` → "Reviewer wakes ~168×/day. Higher cost; supports time-sensitive workflows."
- `continuous` → "No drain cap — paced lane drains as fast as it accumulates. Highest cost ceiling."

> **The PaceBadge** (`web/components/work/PaceBadge.tsx`) is the **read-only deep-link to `/pace`** mounted on the Cockpit — not an L3 concept-card variant. It surfaces kind + queue depth at-a-glance and clicks through to the atomic surface for edits. Per ADR-300 D5: edit affordances live at `/pace` only, never on the badge.

---

## Confirm-modal pattern for high-stakes dials (2026-05-24)

`AutonomyCard` and `PaceCard` full variants share a UX discipline: **every mutation pops a confirm modal before commit.** The original Direct-mutation pattern (single click → optimistic write) was too easy to trigger accidentally for dials whose consequences are capital (autonomy) or cost (pace). Operator feedback surfaced the gap; this section codifies the pattern.

**Component:** `web/components/workspace-concepts/ConfirmDialChange.tsx` — shared confirm modal wrapping `InteractiveModal`. Takes:

- `dialName` — short label (e.g. "autonomy", "pace")
- `fromLabel` / `toLabel` — current and proposed level labels
- `consequence` — one-line operator-facing summary of what changes (the consumer owns this copy — knows its dial better)
- `onCancel` / `onConfirm` — handlers; `onConfirm` is async because consumers run a workspace write

**Discipline rules:**

1. **Per-option `consequence` copy lives next to the option's `value` + `label` + `description` in the LEVELS / KIND_OPTIONS array** in the card. Singular source of truth — the radio surfaces description; the confirm modal surfaces consequence; both come from the same record.
2. **Phrased as outcome, not definition.** "The Reviewer will auto-execute every action up to the ceiling without first checking in. You review outcomes after the fact." — what changes about behavior, not what the dial "means."
3. **No confirm pop on selecting the already-active level.** Click handler early-returns when `lvl.value === currentLevel`. Avoids confirm-on-no-op annoyance.
4. **Symmetric across raise/lower.** Confirm fires equally on Manual→Autonomous (escalation) and Autonomous→Manual (de-escalation). The point isn't to gate dangerous moves only — it's to make every dial mutation deliberate.
5. **Modal closes on backdrop click + Escape via `InteractiveModal`.** Submitting state disables Cancel + Confirm + backdrop close while the write is in flight.
6. **Compact + chip variants never mutate, so no confirm gate.** Confirm modal is full-variant only; compact + chip are display-only or delegate to chat.

**What this pattern is NOT:**

- Not a generic two-step apply (no "Save" button — radios still feel like radios). The radio click is the staging step; the modal is the commit step.
- Not a tiered gate (no "confirm only on dangerous escalations"). The rejected alternative would have created an asymmetric UX that's harder to reason about. Confirm-on-every-switch is simpler and equally protective.
- Not extensible to `compact` or `chip` variants. Those variants exist for read-mostly contexts; mutations there route through deep-link to the full-variant surface.

**Adding a confirm gate to a new high-stakes dial:** 
1. Extend the card's options array with a `consequence: string` field per value.
2. Replace direct `onClick={() => void setX(value)}` with a `setPending(value)` state hook + early-return on `value === currentValue`.
3. Mount `<ConfirmDialChange>` at the end of the full variant's render with `pendingMeta` / `currentMeta` lookups + `onConfirm` that calls the actual mutation.
4. Document the `consequence` copy alongside the option in the card source — never split.

---

## Render contract for L3-on-L2-output (ADR-266 D5)

L2 parsers extract structured fields from prose markdown files. The fields are
returned as plain strings — they may carry residual markdown (`**bold**`,
backtick-paths) from the source. **L3 components must clean parser output
before render.** The render contract:

- **Markdown in extracted fields must be either parsed or stripped.** Never leak
  literal asterisks, backticks, or other markdown syntax in operator-facing
  strings. Use `cleanProse()` from `web/lib/content-shapes/_render.ts` for plain
  text; use a markdown-to-jsx renderer if rich rendering is wanted.
- **No raw file paths in operator-facing strings (ADR-244 D7).** If a parser
  field references `/workspace/...` or backtick-wrapped paths, `cleanProse()`
  strips them with a generic `(workspace file)` substitution.
- **No raw enum tokens in operator-facing strings.** Bundle MANIFEST `phases[].label`
  is the source of truth for `current_phase` display; never render the bare
  enum slug.

The helper module:

```typescript
// web/lib/content-shapes/_render.ts
stripInlineMarkdown(s)    // bold/italic/code → plain text
stripWorkspacePaths(s)     // /workspace/... → (workspace file)
cleanProse(s)              // composed: paths → markdown → whitespace collapse
firstSentence(s)           // schema-absent fallback for headline degradation
```

**Discipline:** the helper is the render contract for **every** L3 component
that renders parser output, not a per-card fix. Audited by retroactive grep
when v1.1 landed; future cards must apply it from day one.

---

## Bundled endpoint (ADR-266 D8)

The `/workspace` page collapses 7 round-trips (state + 6 file reads) into one
call: `GET /api/workspace/setup-bundle`. Returns:

```typescript
{
  state: WorkspaceStateResponse,
  mandate:          { path, content, last_revision },
  autonomy_yaml:    { path, content, last_revision },
  principles_prose: { path, content, last_revision },
  principles_yaml:  { path, content, last_revision },
  identity:         { path, content, last_revision },
  brand:            { path, content, last_revision },
}
```

`WorkspaceConfigSection` (the `/workspace` page body) calls this once on mount,
parses each content via the L2 parsers, and passes parsed `data` + `lastRevision`
props to each card. Cards keep their self-fetch path as a fallback for the
`/agents` reuse surface — when the parent passes data props, the card skips its
own fetch.

**Singular-implementation invariant:** prop presence is the only signal that
selects between data-prop and self-fetch paths. There is no surface-aware
branching (no `if (variant === 'full' && surface === '/workspace')` etc.).
One card, two data-source modes selected by a single, prop-presence rule.

---

## Last-updated footnote (ADR-266 D7)

Every full-variant card surfaces the most-recent ADR-209 revision metadata as
a single muted line under the card title:

> *Updated 3 days ago by you*

Driven by `WorkspaceRevisionSummary` data (existing `workspace_file_versions`
table). The `RevisionFootnote` component handles the `authored_by` taxonomy
mapping (`operator` → "you"; `yarnnn:*` → "YARNNN"; `reviewer:*` → "Reviewer";
`agent:slug` → slug; `system:bundle-fork` → "program activation"; etc.) and
the relative-time formatting. Returns `null` when no revision data is
available — graceful degradation.

---

## Surface assembly map

| Surface | Components used | Variant |
|---|---|---|
| `/autonomy` page (atomic) | AutonomyCard | `full` (self-fetch + confirm modal) |
| `/pace` page (atomic, ADR-300) | PaceCard | `full` (self-fetch + confirm modal) |
| `/mandate` page (atomic) | MandateCard | `full` (self-fetch) |
| `/principles` page (atomic) | PrinciplesCard | `full` (self-fetch) |
| `/identity` page (atomic, also serves `/brand`) | IdentityBrandCard | `full` (self-fetch) |
| `/workspace` legacy bundled page | Mandate + Autonomy + Principles + IdentityBrand | `full` (data props from setup-bundle) |
| `/agents?agent=reviewer&tab=autonomy` | AutonomyCard + cadence panel | `full` (self-fetch) |
| `/agents?agent=reviewer&tab=principles` | PrinciplesCard | `full` (self-fetch) |
| Chat context overlay | MandateCard + PrinciplesCard + AutonomyCard + Recent | `compact` |
| Chat composer chip | AutonomyCard | `chip` |
| Cockpit header | PaceBadge (read-only deep-link to `/pace`) | n/a (badge, not card variant) |
| Cockpit Mandate face | MandateCard | `headline` |
| Cockpit Tracking face | PrinciplesCard (threshold summary) | `headline` |

---

## What this replaces

- `WorkspaceFileView` used for Mandate and Principles in `WorkspaceContextOverlay` — raw markdown dump, file-path visible, no structure
- `ConfigFileCard` with `<pre>` blocks in `WorkspaceConfigSection` — expand-to-read raw content
- `MandateTab` / `AutonomyTab` / `PrinciplesTab` on the YARNNN agent detail — **deleted**. Replaced by `AutonomyCard` and `PrinciplesCard` directly in `ReviewerDetail` tabs.
- **v1.1**: per-card independent file fetches on `/workspace` mount (7 round-trips) — replaced by single `getSetupBundle()` call (ADR-266 D8). Self-fetch path retained as fallback for `/agents` reuse only.
- **v1.1**: raw `{data?.field}` rendering in MandateCard / PrinciplesCard / IdentityBrandCard / cockpit MandateFace — replaced by `cleanProse()` helper (ADR-266 D5). No more leaking `**bold**` or backtick-wrapped paths.
- **2026-05-24**: `DelegationCard` component → **renamed** `AutonomyCard`. `/delegation` route → **redirect stub** to `/autonomy`. Singular Implementation — old component file deleted, no dual-export shim. Operator surface label aligns with substrate file `_autonomy.yaml`. Schema field `default_delegation` kept (precise data-layer term).
- **2026-05-24**: optimistic single-click commit on `AutonomyCard` and `PaceCard` full variants → **replaced** by confirm modal on every mutation (see §"Confirm-modal pattern for high-stakes dials"). Operator feedback: capital-impact + cost-impact dials were too easy to flip by accident.

---

## Adding a new concept component

1. Add or extend the L2 parser in `web/lib/content-shapes/`.
2. Add the L3 component in `web/components/workspace-concepts/`. **Apply
   `cleanProse()` from `_render.ts` to every parser-output string the card
   renders as text.** This is the render contract, not a per-card option.
3. Register it in this catalog (variants table + surface assembly map).
4. Wire it into the relevant surfaces. **If the card needs to participate
   in the `/workspace` bundled fetch, accept optional `data?` + `lastRevision?`
   props — never read surface-specific signals.**
5. Remove any `WorkspaceFileView` / raw-file-dump usage for the same path.
6. Surface a `RevisionFootnote` in the full-variant header so operators can
   see who edited the source last and when (ADR-266 D7).

Do not add a new concept component unless it appears on at least two surfaces.
Single-surface rendering belongs in the surface itself.
