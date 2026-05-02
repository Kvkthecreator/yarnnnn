# ADR-245 — TP Meta-Awareness of the Workspace Settings Surface

**Status:** Implemented (2026-05-01, single commit)

**Builds on:** ADR-244 (Workspace Settings Surface) — the substrate this prompt-layer ADR makes legible to TP.

**Amends:** ADR-156 (CONTEXT_AWARENESS prompt section under `prompts/chat/onboarding.py`) — adds a "Workspace surface awareness" subsection.

**Preserves:** ADR-186 (prompt profile registry), ADR-159 (compact index 600-token ceiling), ADR-205 F1 (chat-first landing), ADR-206 D6 (CRUD split: substrate authoring stays in chat), ADR-226 (activation overlay for `post_fork_pre_author`), ADR-235 D1 (substrate writes route through inference primitives + WriteFile).

---

## Context

ADR-244 shipped a permanent `Settings → Workspace` surface for program lifecycle (activate / switch / deactivate / inspect substrate status / see capability gaps). The first production session post-deploy revealed three TP awareness gaps:

1. **TP doesn't reference the Workspace surface.** When the operator said "full autonomy," TP correctly wrote AUTONOMY.md but didn't surface that the same state is now visible at `Settings → Workspace`. When the operator said "Want to connect a trading account?", TP didn't deep-link to the surface where capability gaps are visible.

2. **The activation overlay is silent in two of three states.** `prompts/chat/activation.py` engages only on `activation_state === "post_fork_pre_author"`. For `none` (no program) and `operational` (mandate authored), the overlay never fires. TP has no awareness that programs exist at `none` state, and no awareness of where the operator can manage program lifecycle at `operational` state.

3. **Compact index doesn't surface per-file substrate status or capability gaps.** TP sees `identity: rich`, `brand: rich` but doesn't see whether MANDATE, AUTONOMY, or Reviewer principles are skeleton vs authored. It also doesn't see whether the active program's required platforms are connected. Both signals exist server-side (ADR-244 D2 endpoint), they're just not in the compact index TP reads on every turn.

The fix is small and prompt-layer-only. No new endpoints, no schema changes, no new primitives. Surface what already exists.

---

## Decisions

### D1. Extend `workspace_state` with substrate_status + capability_gaps + active_program

`api/services/working_memory.py::build_working_memory` reads the same signals the ADR-244 endpoint computes (per-file richness for MANDATE / AUTONOMY / Reviewer principles; capability gaps for the active bundle) and stitches them into the existing `workspace_state` dict alongside `identity`, `brand`, `activation_state`. No new RPC, no new query — same `UserMemory.read()` calls + same `bundle_reader._load_manifest()` + same `_classify_richness` heuristic.

The fields added:

```python
"workspace_state": {
    # ... existing fields ...
    "mandate": "empty" | "sparse" | "rich",
    "autonomy": "empty" | "sparse" | "rich",
    "principles": "empty" | "sparse" | "rich",
    "capability_gaps": [
        {"capability": "...", "platform": "...", "connected": bool},
        ...
    ],
    # active_program_slug already implied by activation_state when bundle active;
    # surface explicitly so the prompt doesn't have to re-parse MANDATE.md.
    "active_program_slug": Optional[str],
}
```

`identity` and `brand` already follow the `empty | sparse | rich` shape. The three new file richness fields use the same vocabulary so TP's existing reasoning patterns transfer directly. `capability_gaps` is a slimmed mirror of the surface's structure — no `capability` semantic detail beyond name + platform name + connected flag (TP doesn't need richer signal at this layer).

### D2. Surface in compact index — at most three lines, conditional

The compact index has a 600-token ceiling (ADR-159). ADR-245 adds **at most three lines**, each conditional on signal:

1. **Authored substrate roll-up** (in the "Intent (authored rules)" section): one line summarizing the five authored files. Already existing: `- Identity: {identity} · Brand: {brand} · {docs} uploaded documents`. Extended:
   `- Identity: {identity} · Brand: {brand} · Mandate: {mandate} · Autonomy: {autonomy} · Reviewer principles: {principles} · {docs} documents`
   No new line — same line, more fields.

2. **Active program + gap signal** (under "Intent (authored rules)", only when active_program_slug is set):
   `- Active program: {slug} ({operational | post_fork_pre_author | unmet capability: {platform}})`
   New line, conditional, ≤ 80 chars typical.

3. **Surface pointer** (in "Key files" section):
   `- /settings?tab=workspace — program lifecycle, substrate status, capability gaps`
   Co-located with the existing `/workspace/...` file pointers. ~70 chars.

Net token impact: ~30-40 tokens worst-case. Within ceiling.

### D3. Add `WORKSPACE_SURFACE_AWARENESS` subsection to CONTEXT_AWARENESS

`prompts/chat/onboarding.py::CONTEXT_AWARENESS` gains a new subsection (placed after "Workspace Context Awareness" intro, before "Situational Awareness (AWARENESS.md)"). The subsection tells TP:

- The `Settings → Workspace` surface exists and what it shows (status board: active program · substrate status · capability gaps).
- When to deep-link: operator asks "what programs can I run", "what's my activation state", "is my mandate authored", "is alpaca connected for my program" — point at `/settings?tab=workspace` instead of (or alongside) reading files inline.
- When NOT to deep-link: operator is mid-flow on substrate authoring (the activation walk per ADR-226). The surface is for inspection / lifecycle ops, not for replacing the chat-driven authoring path (ADR-206 D6).
- Three states, three postures:
  - `none` (no program): TP can suggest programs exist and offer to walk through one if intent suggests programmatic work; deep-link to surface for the operator to browse.
  - `post_fork_pre_author`: ADR-226 ACTIVATION_OVERLAY engages; TP walks the operator through MANDATE / IDENTITY / principles. Surface awareness is silent here (don't conflict with the walk).
  - `operational`: TP can deep-link to surface when the operator asks about lifecycle ops (switch program, deactivate, see capability gaps).

The subsection is ~30 lines; total CONTEXT_AWARENESS adds ~700 chars.

### D4. No new prompt module, no new overlay

ADR-245 is intentionally minimal. The first instinct was to add a `no_program.py` overlay analogous to `activation.py`. Rejected because:

- The CONTEXT_AWARENESS prompt is already always-on and already discusses the mandate-authoring posture for the empty-MANDATE case (under "Priority: Mandate → Operation → Identity → Brand"). A second "no program" overlay would duplicate it.
- The `Settings → Workspace` surface is itself the empty-state's affordance — the operator can browse and pick from there. The chat-side prompt just needs to know the surface exists and when to point at it.
- Singular implementation: one CONTEXT_AWARENESS prompt, one ACTIVATION_OVERLAY, one Workspace surface. Don't proliferate.

### D5. No primitive changes, no schema changes

Per ADR-244 the surface reads existing substrate via existing primitives. ADR-245 adds prompt awareness, not capability. The only code change beyond the prompt is the `working_memory.py` extension that surfaces signal already computed elsewhere.

---

## What this ADR does NOT do

- No new prompt module. Inline subsection only.
- No new overlay (no `no_program.py` analogue to `activation.py`).
- No change to the activation overlay engagement criteria (`post_fork_pre_author` only — same as ADR-226).
- No change to ADR-244 surface, endpoint shape, or boundary discipline.
- No new primitives, no new endpoints, no schema migration.
- Does not address the *separate* FE bug surfaced in the production screenshot (file viewer not rendering content). That's a `/context` rendering issue, not a prompt issue.

---

## Implementation seam (single commit)

1. **`api/services/working_memory.py`** — extend `build_working_memory`:
   - Read MANDATE.md, AUTONOMY.md, REVIEW_PRINCIPLES_PATH (already partly read for activation-state classification; reuse the reads).
   - Add `mandate`, `autonomy`, `principles` richness fields to `workspace_state` via `_classify_richness`.
   - Compute `capability_gaps` from active bundle's `capabilities[*].requires_connection` × `platform_connections` (mirrors ADR-244 endpoint logic).
   - Surface `active_program_slug` from `parse_active_program_slug(mandate_content)`.

2. **`api/services/working_memory.py::format_compact_index`** — extend:
   - Append mandate/autonomy/principles to the existing identity/brand line.
   - New conditional line for active program + capability gap.
   - New file pointer line for `/settings?tab=workspace`.

3. **`api/agents/prompts/chat/onboarding.py::CONTEXT_AWARENESS`** — insert new subsection.

4. **`api/prompts/CHANGELOG.md`** — `[2026.05.01.3]` entry.

5. **`CLAUDE.md`** — ADR-245 entry in ADR list.

6. **`api/test_adr245_tp_meta_awareness.py`** — regression gate.

---

## Acceptance

- `workspace_state` dict carries `mandate`, `autonomy`, `principles`, `capability_gaps`, `active_program_slug`.
- Compact index includes the extended substrate line + active-program line (conditional) + Workspace surface pointer.
- `CONTEXT_AWARENESS` contains a `### Workspace surface awareness` subsection that names `/settings?tab=workspace` and the three-state posture.
- Token ceiling enforcement still holds (compact index < 600 tokens).
- TypeScript typecheck clean (no FE changes; included for parity).
- Regression gate passes.

---

## Cross-references

- ADR-244 — substrate this surfaces; reads the same signals.
- ADR-226 — ACTIVATION_OVERLAY semantics preserved; surface awareness is silent during the walk.
- ADR-186 — prompt profile registry; no profile changes here.
- ADR-159 — compact index ceiling; respected.
- ADR-156 — CONTEXT_AWARENESS canonical home.
- ADR-205 F1 — chat-first landing; HOME_ROUTE unchanged.
- ADR-206 D6 — CRUD split; substrate authoring stays in chat, lifecycle ops on the surface.
