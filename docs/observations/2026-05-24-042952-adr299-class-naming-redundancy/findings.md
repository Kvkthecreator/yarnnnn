# ADR-299 architectural-class-naming redundancy — Hat-B finding

**Hat**: External Developer of the System (Hat B per CLAUDE.md §"The Two Hats").

**Captured**: 2026-05-24 by operator-prompted re-review after ADR-299 Phase 1 shipped (commit `3f0cabb`, 2026-05-22).

**Trigger**: operator asked *"can you double check if we don't actually have other capabilities that are of the similar universal kernel respects? i feel like the conceptual framing we may have created is redundant."* The challenge prompted a survey that surfaced the redundancy the original ADR-299 drafting missed.

## Finding

**ADR-299's "kernel-universal capability" architectural class is a redundant renaming of an existing pattern.** The genuinely novel structural property is something narrower and worth naming differently.

### Evidence

The `CAPABILITIES` dict at `api/services/orchestration.py:1129` already shipped (pre-dates ADR-299) and already contains the architectural pattern ADR-299 D1 claims to introduce:

- 15 existing entries have `platform_connection_requirement: None` — the structural property ADR-299 D1 names as the distinguishing kernel-universal test
- These entries are kernel-shipped (not in any bundle MANIFEST), apply across all archetypes, are gated by something other than `platform_connections`, and address operator-or-kernel-owned surfaces
- The resolution path (`_resolve_capability` → kernel-first then bundle-fallthrough per ADR-224) already handles the kernel-vs-bundle distinction structurally

Examples of pre-existing kernel-universal-shaped entries:

| Capability | Category | `platform_connection_requirement` |
|---|---|---|
| `summarize`, `detect_change`, `alert`, `cross_reference`, `data_analysis`, `investigate`, `produce_markdown` | cognitive | None |
| `web_search`, `read_workspace`, `search_knowledge` | tool (internal) | None |
| `chart`, `mermaid`, `image`, `video_render` | asset (python_render) | None |
| `compose_html` | composition | None |

ADR-299 D5 introduced a **parallel registry** (`KERNEL_UNIVERSAL_CAPABILITIES` in new module `api/services/kernel_capabilities.py`) that duplicates the structural slot the existing `CAPABILITIES` dict already provides. The resolution path (`get_platform_tools_for_capabilities` kernel-universal pre-check) is a second path doing what the existing single path already does.

### What IS genuinely novel about `send_operator_email`

The actual architectural novelty `send_operator_email` introduces is NOT "kernel-universal" (existing class) but **"operator-addressing"** — a capability whose addressee resolves from `auth.users.email` for the workspace owner, regardless of whether a wire-gate is present.

This distinguishes from THREE existing patterns:

1. **No-wire-gate kernel capabilities** (15 existing entries): `summarize`, `web_search`, `chart`, etc. — no external API; addressee is N/A
2. **Wire-gated audience-addressing bundle capabilities** (existing): `write_slack`, `write_notion` — external API + LLM-supplied addressee → third-party / audience surface
3. **Wire-gated operator-addressing capability** (NEW, the actual novelty): `send_operator_email` — external API + addressee structurally pinned to operator identity → operator surface

The (3) shape is the genuine architectural novelty. ADR-299 surfaced it correctly via D2 (the structural addressee pin) + D4 (observability autonomy posture) + D7 (out-of-scope clarifications). But ADR-299 D1's category name *"kernel-universal capability"* names a class that already exists, not the novelty.

### Why the redundancy escaped initial drafting

Pre-ADR-299 drafting research (delegated to general-purpose agent) read `orchestration.py` and noted there was *"no explicit CAPABILITIES = {} dict currently visible (capabilities are embedded in role definitions + bundle MANIFESTs)."* That was incorrect — the dict is at line 1129, ~110 lines below where the agent looked. I did not personally verify the claim before drafting ADR-299 D5's parallel-registry design.

Discipline lesson: **delegate research to subagents, but verify the load-bearing facts before designing on top of them.** Especially for architectural-class claims like "no existing dict for this shape" — those are exactly the claims that, if wrong, produce redundant infrastructure.

## Recommendation (Hat-A correction)

Surface the redundancy + reframe the class in a single Hat-A commit (cross-hat in-session per CLAUDE.md three-commit shape):

1. **Delete `api/services/kernel_capabilities.py`** — parallel registry, duplicates existing `CAPABILITIES` dict slot
2. **Add `send_operator_email` entry to `CAPABILITIES` dict** in `api/services/orchestration.py` with a new field `addressee_class: "operator"` capturing the genuine novelty
3. **Revert the kernel-universal pre-check** in `get_platform_tools_for_capabilities` — the existing resolution path handles this via `_resolve_capability` per ADR-224 fallthrough; need to wire `addressee_class` recognition into the existing tool-surface assembly instead
4. **Keep `platform_email_send_to_operator` tool definition + handler `send_to_operator` branch + structural addressee pin** — these are genuinely new and correct; only the registry-housing changes
5. **Amend ADR-299** with a Discovery note (in-place per Singular Implementation, no v1/v2):
   - D1's category name reframed from "kernel-universal capability" (existing pattern) to **"operator-addressing capability"** (the genuine novelty)
   - D5's parallel-registry decision retracted; replaced with "extend existing `CAPABILITIES` dict with `addressee_class` field"
   - Discovery note explicitly names the redundancy + the discipline lesson (delegate research, verify load-bearing facts)
   - All other decisions (D2 structural addressee pin, D3 ADR-283 clarification, D4 AUTONOMY-as-observability, D6 kernel-placement justification, D7 out-of-scope) stand unchanged
6. **Update regression test** to match corrected shape: drop parallel-registry assertions, keep structural-pin + handler-rejection + resolution-via-existing-path assertions

The correction does NOT revert Phase 1's tool wrap or handler — those are genuinely new and correct. Only the architectural-class-naming + parallel-registry housing get corrected.

## Cross-hat shape

Per CLAUDE.md §"The Two Hats", this finding + fix qualifies for the **single-session-three-commit shape**:
- **Commit 1** (this file): Hat-B observation documenting the finding
- **Commit 2**: Hat-A correction (code + ADR amendment)
- **Commit 3**: Hat-B resolution confirming the correction landed cleanly

The fix is small enough + has named in-canon precedent (ADR-235 Singular Implementation pattern; ADR-224 kernel/bundle resolution) that cross-hat in-session is appropriate per the discipline rule.

## Severity

Low-medium. The redundancy doesn't break functionality — Phase 1 works correctly and the regression gate passes. The cost is architectural clarity: a future contributor reading `CAPABILITIES` (existing) + `KERNEL_UNIVERSAL_CAPABILITIES` (new) would not know which to use for a new capability, and the discipline rule ADR-299 D5 names (kernel-universal class is for operator-identity-addressing capabilities only) isn't enforceable when two registries exist with similar shape.

Catching it within 48 hours of Phase 1 shipping (rather than after the class becomes a dumping ground) is the right time to correct.

## Status

**OPEN** — Hat-A correction commit follows next; Hat-B resolution commit confirms after correction lands.
