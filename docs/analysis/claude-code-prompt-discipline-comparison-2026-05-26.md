# Claude Code Prompt-Discipline Comparison — First-Principles Notes for YARNNN

**Date**: 2026-05-26
**Source examined**: `docs/analysis/src_claudeCC/` (snapshot of Claude Code source, March 2026 — extracted from upstream for reference)
**Scope of comparison**: prompt-envelope authoring, tool-error surfacing, tool-use loop completion semantics, memory aging
**Purpose**: ground YARNNN's ADR-302 (prompt-envelope discipline) and ADR-303 (Reviewer posture taxonomy) in first-principles where Claude Code's patterns inform our derivation, and explicitly mark the boundaries where YARNNN must derive its own discipline because Claude Code doesn't have an analogous concern.

**Discipline rule for this document**: not conformance theater. Every observation here either (a) confirms a YARNNN derivation against an independent precedent, (b) sharpens a YARNNN derivation that was under-specified, (c) inverts a YARNNN default that the source-comparison shows was backwards, or (d) names a region where YARNNN is doing original work because Claude Code's surface doesn't extend there. Patterns that don't pull on YARNNN's problem space are noted but not adopted.

---

## What Claude Code does that YARNNN should ratify

### 1. Typed section registry with cache-aware variants — `constants/systemPromptSections.ts`

Claude Code's system prompt is **not a string**. It's a registered list of typed `SystemPromptSection` objects:

```typescript
type SystemPromptSection = {
  name: string
  compute: ComputeFn
  cacheBreak: boolean
}

systemPromptSection(name, compute)                              // cached default
DANGEROUS_uncachedSystemPromptSection(name, compute, _reason)   // un-cached, requires justification
```

The `DANGEROUS_` prefix is intentional friction: an author who wants to add a volatile section has to consciously type the prefix AND supply a `_reason` string. The naming + the mandatory argument together make the rare-and-justified case structurally explicit.

**Why this is load-bearing for YARNNN**: our drift problem in `_PERSONA_FRAME` (64 cross-mentions of operator-substrate files, three generations of contradictory write-capability guidance stacked over time) is *exactly* the failure mode this discipline closes. Sections as named registered objects make "one canonical place per concern" structurally enforceable rather than authoring convention. Adding a second section with the same name requires either renaming or making the contradiction obvious in the registry.

**Adopted in ADR-302 D5**: `PersonaFrameSection` shape mirroring Claude Code's pattern (named + compute + cache_break + DANGEROUS_ prefix for volatile variants).

### 2. Static / dynamic boundary marker — `constants/prompts.ts:560-577`

```typescript
return [
  // --- Static content (cacheable) ---
  getSimpleIntroSection(...),
  ...
  getOutputEfficiencySection(),
  // === BOUNDARY MARKER - DO NOT MOVE OR REMOVE ===
  ...(shouldUseGlobalCacheScope() ? [SYSTEM_PROMPT_DYNAMIC_BOUNDARY] : []),
  // --- Dynamic content (registry-managed) ---
  ...resolvedDynamicSections,
].filter(s => s !== null)
```

The explicit `=== BOUNDARY MARKER - DO NOT MOVE OR REMOVE ===` comment is refactoring friction. An edit that moves a dynamic section above the boundary or static below it has to consciously delete the marker — making the violation visible at review time.

**Adopted in ADR-302 D6**: same boundary discipline in `_PERSONA_FRAME_SECTIONS`. Static sections (axiom citations, write-authority declaration, anti-pattern enumeration) before; dynamic sections (operating-context per ADR-274) after; marker between.

### 3. tool_choice never forced — `query.ts:674`

```typescript
options: {
  ...
  toolChoice: undefined,
  ...
}
```

Throughout the entire query loop, Claude Code passes `toolChoice: undefined`. Never forces a specific tool. Never even forces "use SOME tool." The model decides every turn whether to call tools or emit text.

**Combined with the loop-exit check at `query.ts:826-835`**:

```typescript
const msgToolUseBlocks = message.message.content.filter(
  content => content.type === 'tool_use',
) as ToolUseBlock[]
if (msgToolUseBlocks.length > 0) {
  toolUseBlocks.push(...msgToolUseBlocks)
  needsFollowUp = true
}
```

Loop continues only if the assistant message contained tool calls. Text-only → `needsFollowUp = false` → loop ends → text shown to user as final answer.

**This is the first-principles position**: model agency over loop continuation is non-negotiable. Forcing a tool call is a worse failure mode than allowing a natural text-only completion. The source's silence on "what if the model exits early?" is the answer — it's not an early exit, it's a completion the model chose.

**Validates ADR-303 P2 (decided-nothing-material as legitimate posture)** and **invalidates the option-A "force ReturnVerdict on terminal rounds" path** that was considered and rejected. The right place to handle silent-exit is operator-visible substrate (the dispatcher-write path in ADR-303 D2), not model coercion.

### 4. Tool errors always surface with `is_error: true` — `query.ts:140`

```typescript
yield createUserMessage({
  content: [
    {
      type: 'tool_result',
      content: errorMessage,
      is_error: true,
      tool_use_id: toolUse.id,
    },
  ],
  ...
})
```

When a tool fails, Claude Code emits a tool_result with `is_error: true`. The error goes back to the model AND surfaces to the user. **No filter analogous to YARNNN's `surface_reviewer_actions:408` exists.**

The first-principles position: all tool outcomes are operator-visible because operator judgment requires the substrate-receipt of what actually happened, not a curated view of what succeeded.

**Inverted ADR-303 D3 to match**: visibility-first default, denylist-explicit-noise. The prior draft used an allowlist (`SURFACE_FAILURE_REASONS` enumeration) — but allowlist defaults to silence on novel failure classes. The source's pattern is denylist defaults to visibility on novel failure classes. YARNNN's case is closer to Claude Code's: operator-relevant failure reasons (path_locked, capability_required_missing, etc.) should NEVER be filtered, even if not yet enumerated. The asymmetry favors surfacing.

### 5. Memory aging — human-readable + system-reminder warning — `memdir/memoryAge.ts`

Two functions worth noting:

```typescript
export function memoryAge(mtimeMs: number): string {
  const d = memoryAgeDays(mtimeMs)
  if (d === 0) return 'today'
  if (d === 1) return 'yesterday'
  return `${d} days ago`
}
// Comment: "Models are poor at date arithmetic — a raw ISO timestamp doesn't
// trigger staleness reasoning the way '47 days ago' does."

export function memoryFreshnessNote(mtimeMs: number): string {
  // For memories >1 day old, returns a <system-reminder> wrapped warning
  // citing: "user reports of stale code-state memories ... being asserted as
  // fact — the citation makes the stale claim sound more authoritative, not
  // less."
}
```

This is **substrate-staleness signaling in the prompt envelope**. YARNNN doesn't have an analog. We load `MANDATE.md` / `IDENTITY.md` / `_operator_profile.md` etc. into the wake envelope with no staleness signal. If the operator hasn't touched `_operator_profile.md` in 60 days, the Reviewer reads it as fresh canon — same authority as a same-day edit.

**Not adopted in ADR-302/303** because it's a different concern. **Filed as a net-new candidate** for a future ADR (provisionally ADR-304) on substrate-staleness signaling. When the persona-frame asserts "operator authored this declaration with perspective you don't have in a single wake," the implicit assumption is the declaration is *recent*. Staleness changes the epistemic-deference reasoning.

---

## What Claude Code does NOT have that YARNNN has to derive on its own

### 1. The autonomy ladder + lock-set concept

Claude Code is a synchronous user-driven CLI. The user is always present. There's no concept of:
- "Reviewer-amends-operator-canon when autonomous mode permits"
- A lock-set distinguishing operator-authored substrate from agent-amendable substrate
- The contradiction class our `_PERSONA_FRAME` exhibits (canon says "you can amend"; lock-set says "you can't amend autonomy.yaml")

These are YARNNN-original problems. The discipline derived in ADR-302 D1/D2/D3 (one canonical capability statement per file, templated from code constant, concern-separation per mention) is original work; Claude Code's silence on the autonomy-amendment surface confirms we're authoring canon, not adapting it.

### 2. Posture-cell taxonomy

Claude Code's loop-completion model is binary (tool_use → continue; text-only → done). No P1/P2/P3/P4/P5 distinction. Because the user is present, "the model exited and didn't say anything substantive" is handled by the user reading the result and asking again.

YARNNN's Reviewer is invoked across hours, sometimes days, between operator observations. A silent exit that the operator only discovers on the morning briefing is a different failure shape than a CLI text-only response the user reads immediately. The posture-cell taxonomy in ADR-303 D1 is YARNNN-original derivation; the per-cell substrate side-effect contract in D2 is YARNNN-original derivation.

### 3. Per-bundle persona-frame variants

Claude Code has one CLAUDE.md per project, but the system prompt is uniform across projects. YARNNN's failed-WriteFile concentration on author-class personas (korea-thriller-shorts, netflix-script-author) but not trader-class personas (kvk, alpha-trader) suggests we may need per-bundle persona-frame overlays. Claude Code's surface doesn't extend here; we'll derive when the question becomes load-bearing (ADR-303 D5 explicit defer).

### 4. Substrate-attribution discipline

Claude Code writes to user files as "Claude wrote this" — no model-vs-harness distinction. YARNNN's ADR-209 Authored Substrate model is more sophisticated: `authored_by="reviewer:..."` vs `authored_by="operator"` vs `authored_by="system:..."` vs (per ADR-303 D2 + D6) `authored_by="dispatcher:silent_exit_fallback"`. The fine-grained attribution is YARNNN-original; the discipline in ADR-303 D6 (don't conflate model-authored with dispatcher-synthesized) preserves the distinction's load-bearing semantics.

---

## What Claude Code does that YARNNN should NOT adopt

### 1. Token-budget anchors as user-visible guidance — `prompts.ts:531-549`

Claude Code includes prompt sections for token-budget anchors ("Length limits: keep text between tool calls to ≤25 words. Keep final responses to ≤100 words unless the task requires more detail."). This is research-validated for output-token reduction but specifically targeted at user-visible terseness.

**Why YARNNN should not adopt**: the Reviewer's user-facing surface is asynchronous (feed entries, cockpit substrate writes), not synchronous terminal output. Terseness optimization in the wrong direction reduces operator visibility into reasoning — exactly opposite of what ADR-303 is trying to achieve. If we hit token-cost ceilings, the right lever is per-wake budget management (ADR-291 telemetry → cost-aware wake routing), not making the Reviewer terser.

### 2. MCP per-server instructions section — `prompts.ts:579-604`

Claude Code dynamically composes MCP server instructions into the system prompt as each MCP server connects/disconnects. The pattern is sound for Claude Code's plugin model but YARNNN's primitive surface is fixed (REVIEWER_PRIMITIVES is a curated subset per ADR-258 revised). No MCP-style runtime extension surface exists; the pattern doesn't apply.

### 3. Streaming tool execution overlap — `query.ts:561-568`

Claude Code's `StreamingToolExecutor` executes tools while the model is still streaming subsequent tokens. Pattern optimizes for synchronous CLI latency. YARNNN's Reviewer is wake-fired and asynchronous; latency optimization within a single wake doesn't move the needle on operator experience (which is dominated by wake-to-feed-update latency, not within-wake latency).

---

## Where this comparison was substantively load-bearing

Three concrete refinements landed in the ADRs that wouldn't have without reading the source:

1. **ADR-302 D5 + D6** — the typed section registry + boundary marker discipline. Promoted from "one canonical place per concern (prose convention)" to "one canonical place per concern (structural enforcement via typed registry)." Sharper, harder to violate.

2. **ADR-303 D3 inverted** — from allowlist (surface specific reasons) to denylist (silence specific noise classes, default to visibility). First-principles aligned with the canon's "full-substrate-authoring Reviewer" claim per Derived Principle 21.

3. **Validation of no-in-loop-intervention** — ADR-303's stance against forcing tool_choice on terminal rounds is confirmed as first-principles correct by Claude Code's `toolChoice: undefined` discipline. Not changed; just no longer hedged.

Plus one net-new ADR candidate: substrate-staleness signaling (future ADR-304+).

---

## Discipline rule going forward

This document exists as **reference, not authority**. Future ADRs that touch prompt-envelope, tool-error surfacing, or loop-completion semantics should:

1. Derive from YARNNN's substrate evidence first.
2. Cross-check against this comparison doc to see if Claude Code's surface offers a precedent that sharpens or inverts the derivation.
3. Cite the comparison explicitly when a refinement is adopted (as ADR-302 D5/D6 and ADR-303 D3 now do).
4. Cite the comparison explicitly when a Claude Code pattern is examined and **rejected** for YARNNN reasons (so the rejection is visible, not implicit).
5. Update this document with new findings when future ADR work surfaces new precedents.

The Claude Code source snapshot is from March 2026; patterns may have evolved upstream. Re-snapshotting (and re-comparing against the current snapshot, not assumed-current Claude Code) is the discipline.

---

## Cross-references

- Source snapshot: `docs/analysis/src_claudeCC/`
- Driving findings: `docs/observations/2026-05-25-053951-reviewer-behavior-population-audit/findings.md`, `docs/observations/2026-05-26-152500-failed-action-substrate-blindspot/findings.md`
- ADRs ratifying refinements: `docs/adr/ADR-302-prompt-envelope-discipline.md` (D5 + D6 refinements added per this comparison), `docs/adr/ADR-303-reviewer-posture-taxonomy.md` (D3 invert per this comparison)
- Future ADR candidate (not yet drafted): substrate-staleness signaling — provisional ADR-304+

---

## Last updated

2026-05-26 — initial scaffold from same-session source read. Update on each subsequent comparison cycle.
