# Workspace Concept Components

**Version:** v1.0 (2026-05-06)
**Status:** Canonical
**Principle:** Render meaning from substrate, not the substrate itself.

---

## Why this doc exists

The workspace files (`MANDATE.md`, `AUTONOMY.md`, `IDENTITY.md`, `BRAND.md`,
`principles.md`) are kernel substrate — they exist for every workspace regardless
of program. The operator should never see file paths, state badges derived from
file format, or raw markdown dumps. They should see **what the files mean** in
their vocabulary.

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

**What the operator needs to see:**
- Primary Action (one sentence — the "what")
- Success criteria (bullet list — the "how we'll know")
- Whether it's set at all (empty state = clear CTA)

**Variants:**
| Variant | Used on | Shows |
|---|---|---|
| `full` | `/workspace` page | Primary Action headline + success criteria bullets + boundary count |
| `compact` | context overlay | Primary Action headline only + "Not set" state |
| `headline` | cockpit face | Primary Action sentence, one line, truncated |

**Empty state behavior:** All variants surface a "Set up in chat →" CTA when
`primaryAction` is null. The CTA text varies by variant density.

---

### 2. Delegation (Autonomy)

**File:** `/workspace/context/_shared/AUTONOMY.md`
**L2 parser:** `web/lib/content-shapes/autonomy.ts` *(already complete)*
**L3 component:** `web/components/workspace-concepts/DelegationCard.tsx`
**Write contract:** `configuration` (Direct mutation via `setLevel()` — no chat needed)

**What the operator needs to see:**
- Current delegation level (one of four: Manual / Assisted / Bounded / Autonomous)
- What that level means behaviorally (one sentence)
- Ability to change it inline (Direct control — the only concept with a Direct mutation)

**Variants:**
| Variant | Used on | Shows |
|---|---|---|
| `full` | `/workspace` page | Four-option control (radio/segment), behavioral description, ceiling if bounded |
| `compact` | context overlay | Current level name + one-line description + change link |
| `chip` | chat composer | Level badge only (read-only, links to `/workspace`) |

**Level descriptions (operator language):**
- `manual` → "Every action waits for your approval before executing."
- `assisted` → "YARNNN can prepare and stage; you approve before consequences."
- `bounded_autonomous` → "Acts autonomously within your declared ceiling. Flags above it."
- `autonomous` → "Full delegation within declared boundaries. You review outcomes."

---

### 3. Principles

**File:** `/workspace/review/principles.md`
**L2 parser:** `web/lib/content-shapes/principles.ts` *(stub — parse() needed)*
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

## Surface assembly map

| Surface | Components used | Variant |
|---|---|---|
| `/workspace` page | Mandate + Delegation + Principles + IdentityBrand | `full` |
| Chat context overlay | Mandate + Principles + Recent (non-component) | `compact` |
| Chat composer chip | Delegation | `chip` |
| Cockpit Mandate face | Mandate | `headline` |
| Cockpit Tracking face | Principles (threshold summary) | `headline` |

---

## What this replaces

- `WorkspaceFileView` used for Mandate and Principles in `WorkspaceContextOverlay` — raw markdown dump, file-path visible, no structure
- `ConfigFileCard` with `<pre>` blocks in `WorkspaceConfigSection` — expand-to-read raw content
- `MandateTab` / `AutonomyTab` / `PrinciplesTab` on the YARNNN agent detail — bespoke per-file viewers, not reusable

---

## Adding a new concept component

1. Add or extend the L2 parser in `web/lib/content-shapes/`.
2. Add the L3 component in `web/components/workspace-concepts/`.
3. Register it in this catalog (variants table + surface assembly map).
4. Wire it into the relevant surfaces.
5. Remove any `WorkspaceFileView` / raw-file-dump usage for the same path.

Do not add a new concept component unless it appears on at least two surfaces.
Single-surface rendering belongs in the surface itself.
