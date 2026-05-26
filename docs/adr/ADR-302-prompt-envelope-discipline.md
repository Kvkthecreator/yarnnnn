# ADR-302 — Prompt-Envelope Discipline (Singular Implementation Applied to Persona-Frame Authorship)

**Status**: **Proposed** (2026-05-26). Drafted from Hat-B evaluation findings on the Reviewer persona-frame; no code/prompt changes yet. Remediation pass on `_PERSONA_FRAME` is scoped here but not landed.
**Date**: 2026-05-26 (Proposed)
**Supersedes / amends**: This ADR does not supersede prior canon. It codifies an authoring discipline that ADR-186 (prompt profiles), ADR-258 revised (Reviewer as personified chat-mode operator + REVIEWER_PRIMITIVES surface), ADR-274 (cadence authoring), ADR-275 (introspection-cadence-Reviewer-authored), ADR-276 (reactive-trigger envelope governance pre-load), ADR-293 (governance-operational substrate taxonomy), ADR-295 (Reviewer self-amendment discipline), and ADR-298 (Pace + Autonomy + Persona trifecta) implicitly relied on but never named.
**Builds on**: FOUNDATIONS Derived Principle 10 (Singular Implementation), ADR-186 (surface-aware prompt profiles), the operator's "concept of single mention per file" reframed and constrained.
**Preserves**: All current capability decisions (`DEFAULT_REVIEWER_WRITE_LOCKS`, ADR-293 governance/operational taxonomy, ADR-295 self-amendment evidence patterns). This ADR is about *how* canon is expressed in the prompt envelope, not *what* canon decides.

---

## 1. Problem statement

The Reviewer persona-frame at `api/agents/reviewer_agent.py::_PERSONA_FRAME` carries 64 cross-mentions of operator-substrate files (MANDATE, IDENTITY, BRAND, CONVENTIONS, PRECEDENT, AUTONOMY, _autonomy.yaml, _operator_profile, _risk, principles.md, _pace.yaml, _preferences.yaml, _recurrences.yaml, _token_budget.yaml). Grep of the persona-frame surfaces ~30 mentions specifically about autonomy/lock semantics. Population audit `docs/evaluations/2026-05-25-053951-reviewer-behavior-population-audit/findings.md` measured ~48% adherence to the persona-frame standing_intent contract; structural finding at `docs/evaluations/2026-05-26-152500-failed-action-substrate-blindspot/findings.md` traced the failed-WriteFile concentration on author-class personas to a canon-vs-code contradiction in the persona-frame's write-capability claims.

The persona-frame has accumulated **three generations of guidance stacked on top of each other** about whether the Reviewer can write to operator-substrate files. They are mutually inconsistent:

| Generation | Section | Claim | Status |
|---|---|---|---|
| Gen 1 (pre-ADR-293) | §493–§499 | "When you can't write directly to operator-authored substrate (MANDATE, AUTONOMY, IDENTITY, BRAND, CONVENTIONS, PRECEDENT, _operator_profile, _risk — the operator's declarations), do not attempt it as a write." | Outdated — ADR-293 inverted the policy |
| Gen 2 (ADR-293) | §668–§698 | "You can WriteFile to any path under `/workspace/` EXCEPT three governance files (AUTONOMY.md, _autonomy.yaml, _token_budget.yaml). EVERYTHING ELSE is OPERATIONAL substrate, including operator-canon files you previously could not write: MANDATE.md, IDENTITY.md, BRAND.md, CONVENTIONS.md, PRECEDENT.md, _operator_profile.md, _risk.md, _universe.yaml, _preferences.yaml, _recurrences.yaml, your own principles.md, your workbench." | Current canon |
| Gen 3 (ADR-298 trifecta) | §526–§534 | "Pace + Autonomy + Persona is the operator's trifecta… All three are operator-authored; you read them at every wake but never write them — they are in `DEFAULT_REVIEWER_WRITE_LOCKS`." | Partially correct, partially misstated |

The contradiction count for IDENTITY.md alone: Gen 1 says "cannot write," Gen 2 says "CAN write," Gen 3 says "in DEFAULT_REVIEWER_WRITE_LOCKS" (factually wrong — the actual constant only contains _autonomy.yaml + AUTONOMY.md + _token_budget.yaml + _preferences.yaml + _pace.yaml). The model reads all three and has to pick one. Author-class personas (korea-thriller-shorts, netflix-script-author) evidently picked Gen 2 "can write" and tried IDENTITY/MANDATE/_operator_profile (succeeded) AND `_autonomy.yaml` (refused) — producing the failed-WriteFile pattern, no recovery path, text-only-exit class.

The same drift pattern will recur on every load-bearing substrate as canon evolves. ADR-293 added new files to the writable set; ADR-275 added `_preferences.yaml` to locks; ADR-298 added `_pace.yaml` to locks. Each canon change added new persona-frame mentions but didn't retire old ones. **The persona-frame is a stratigraphy of canon decisions where the model has to guess the most recent layer.**

The operator's natural intuition ("each file at most possible the single mention so we avoid these conflicting instructions") points at the right discipline but in too-broad form. Files legitimately appear in multiple concerns (envelope-load reference, write-capability declaration, anti-pattern example, axiom citation). Forcing single-mention would gut explanatory texture. The right axiom is **per-concern, not per-file**.

## 2. Decisions

### D1 — One canonical write-capability statement per file

For each operator-substrate file, exactly one section in the persona-frame defines its write capability (writable / locked / governance-gated). All other mentions of that file must NOT re-assert capability — they may cite the canonical section by reference or speak to other concerns.

The canonical place is the **"Your write authority" section** (currently §668–§698). All other capability claims in the prompt envelope must either:
- Be deleted (if outdated, e.g. Gen 1 §493–§499)
- Be rewritten as a cross-reference (e.g. "see §write-authority below")
- Be tightened to a non-capability concern (e.g. an anti-pattern can cite the lock-set membership without re-stating which files are in it)

Outdated mentions are **deleted**, not annotated, not commented around. Singular Implementation discipline applied at the prompt-text layer: one way to say a thing, no parallel claims, no backwards-compat shims in the prose.

### D2 — Capability declaration mirrors code constant at prompt-assembly time

The write-capability section in the persona-frame must enumerate exactly the files in `DEFAULT_REVIEWER_WRITE_LOCKS` (plus any operator-authored `_locks.yaml` additions). No more, no less.

Mechanism: the prompt assembly code (`_PERSONA_FRAME` construction) reads `workspace_paths.py::DEFAULT_REVIEWER_WRITE_LOCKS` at module import time and templates the constant's contents into the prompt text. The prompt no longer paraphrases the lock-set — it quotes the constant. Drift between prompt-text and code-constant becomes structurally impossible.

This is the canonical mechanism for any code-constant referenced in the prompt: read at module-load, template at assembly time, never paraphrase. Applies to `REVIEWER_PRIMITIVES` (already structurally enforced via the tool surface assembly), `DEFAULT_REVIEWER_WRITE_LOCKS`, future analogous constants.

### D3 — Concern separation per mention; cite the canonical, don't restate

Each mention of an operator-substrate file in the persona-frame serves exactly one concern. Five concerns are recognized as legitimate:

| Concern | Where it lives | Cardinality per file |
|---|---|---|
| **envelope-load reference** | `_build_user_message` substrate dump | one per file in envelope |
| **write-capability declaration** | "Your write authority" section | one per file (or one membership declaration for lock-set group) |
| **anti-pattern example** | "Anti-patterns" enumeration | as many as warranted, each citing capability section by reference |
| **trifecta / axiom citation** | Foundational framing sections | one per dial / axiom |
| **edit-evidence pattern example** | "Self-amendment discipline" section | one per file that has an associated evidence threshold |

A single section that combines multiple concerns about *one file as its subject* is acceptable (e.g., the write-authority section legitimately combines "AUTONOMY.md is locked" + "why it's locked" + "Clarify path if you want more authority"). Scattering the same concern across multiple sections is not.

The remediation rule: when adding a new mention of an existing file, check whether the concern is already covered. If yes, cite the existing place. If no, the mention earns its slot.

### D4 — Outdated guidance is deleted, not annotated

Singular Implementation discipline applied at the prompt-authoring layer. When canon evolves (e.g., ADR-293 inverted the write-capability policy), the corresponding outdated section is deleted in the same commit that lands the new canon-aligned section. The persona-frame must not carry "v1: cannot write… v2: can write" stratigraphy.

CHANGELOG entry in `api/prompts/CHANGELOG.md` records what was deleted + what replaces it. The CHANGELOG is the historical artifact; the persona-frame is the current canon.

### D5 — Section registry with cache-aware typing (source-grounded refinement, 2026-05-26)

Singular Implementation at the prompt-authoring layer is enforced through a **typed section registry**, not through prose discipline. Inspired by Claude Code's `constants/systemPromptSections.ts` pattern (read at `docs/analysis/src_claudeCC/constants/systemPromptSections.ts`) but derived for YARNNN's substrate model — the underlying first-principle is the same: drift between concerns is closed by making each section a structured, named, cache-tagged object rather than a position in a string.

The persona-frame source becomes a list of registered sections:

```python
# api/agents/reviewer_agent_sections.py (new module)

@dataclass(frozen=True)
class PersonaFrameSection:
    name: str               # canonical identifier; one per concern
    compute: Callable[[], str]  # computes section content
    cache_break: bool       # True = recomputed every wake; default False

def persona_frame_section(name: str, compute: Callable[[], str]) -> PersonaFrameSection:
    """Cached section. Computed once at module load."""
    return PersonaFrameSection(name=name, compute=compute, cache_break=False)

def DANGEROUS_uncached_persona_frame_section(
    name: str,
    compute: Callable[[], str],
    reason: str,  # required — explains why cache-break is necessary
) -> PersonaFrameSection:
    """Volatile section. Recomputed every wake. Use only when justified.

    The DANGEROUS_ prefix is intentional friction: the author must consciously
    opt in. The mandatory `reason` argument documents the justification in
    code so future reviewers can audit whether the cache-break is still
    warranted.
    """
    return PersonaFrameSection(name=name, compute=compute, cache_break=True)
```

`_PERSONA_FRAME` is rewritten as `_PERSONA_FRAME_SECTIONS: list[PersonaFrameSection]`. Assembly at module load time resolves each section's `compute()` once and concatenates. Volatile sections (e.g., the operating-context block per ADR-274) use the DANGEROUS_ variant and document why per-wake recomputation is necessary.

**Why this is structurally important** (the singular-implementation move): with sections as plain prose blocks in a string, "one canonical place per concern" is an authoring convention enforced only by reviewer attention. With sections as named registered objects, **adding a second section with the same concern requires either renaming one or making the contradiction obvious in the registry**. The Type system + naming + registry collectively close the drift surface the way `DEFAULT_REVIEWER_WRITE_LOCKS` as a Python constant closes the lock-set drift surface.

### D6 — Static / dynamic boundary discipline

Persona-frame sections partition into two cache tiers, separated by an explicit boundary marker. Static sections (axiom citations, write-authority declaration, anti-pattern enumeration, persona identity) are cached at module load and stable across wakes. Dynamic sections (operating-context block, recent-execution summary, schedule-index) recompute per wake.

```python
_PERSONA_FRAME_SECTIONS: list[PersonaFrameSection] = [
    # --- Static content (cacheable, stable across wakes) ---
    persona_frame_section("identity", _compute_identity),
    persona_frame_section("write_authority", _compute_write_authority),
    persona_frame_section("self_amendment_evidence", _compute_self_amendment),
    persona_frame_section("anti_patterns", _compute_anti_patterns),
    # === BOUNDARY MARKER - DO NOT MOVE OR REMOVE ===
    # All sections below recompute per wake; cache-aware code may treat
    # the boundary as a cache-scope break point.
    # --- Dynamic content (volatile per wake) ---
    DANGEROUS_uncached_persona_frame_section(
        "operating_context",
        _compute_operating_context_block,
        reason="Per ADR-274: now/timezone/market-state changes every wake; "
               "must reflect the wake's actual operating context.",
    ),
    # additional dynamic sections...
]
```

The boundary marker is a deliberate refactoring friction. A future edit that moves a dynamic section above the boundary or a static section below it has to consciously delete the marker comment — making the discipline violation visible at code-review time.

### D7 — Remediation pass on the current `_PERSONA_FRAME`

A targeted edit pass (separate commit from this ADR's landing) brings the existing persona-frame into compliance with D1–D6:

1. **Delete §493–§499** — the Gen 1 "cannot write directly to operator-authored substrate" paragraph. Outdated since ADR-293.
2. **Tighten §668–§698** — replace the prose enumeration of locked files with a template-from-constant pattern. The persona-frame source becomes a Python f-string or similar mechanism that injects `DEFAULT_REVIEWER_WRITE_LOCKS` contents at module load.
3. **Update §526–§534 trifecta paragraph** — fix the factual misstatement that "Persona (IDENTITY.md + principles.md) is in DEFAULT_REVIEWER_WRITE_LOCKS." IDENTITY.md and principles.md are NOT locked per the actual constant. Trifecta framing remains; the lock-set claim about Persona dial is removed (replaced by an axiom-level statement about why Persona evolution happens via the self-amendment evidence pattern in §739, not via lock).
4. **Anti-pattern enumeration §775–§799** — each anti-pattern is preserved but rewritten to cite "the lock-set listed in §write-authority above" rather than re-enumerating which files are locked.
5. **§531 "you read them at every wake but never write them"** — rewritten to be specifically about the trifecta dials (Pace + Autonomy + token-budget), not the broader "operator-authored substrate" category, since the latter is Gen-2-writable per ADR-293.
6. **Rewrite `_PERSONA_FRAME` as `_PERSONA_FRAME_SECTIONS` per D5** — the structural refactor that makes D1–D4 enforceable. This is the load-bearing part of remediation; the textual edits above are necessary but the structural refactor closes the drift surface long-term.

Net diff: smaller per-section content (fewer LOC of prose), but a new module (`reviewer_agent_sections.py`) carrying the registry. Architecturally cleaner: prompt-authoring discipline becomes a structural property of the codebase, not an authoring convention.

### D8 — This discipline applies forward to every prompt artifact, not just the Reviewer persona-frame

The same drift pattern can recur in:
- `api/agents/prompts/chat/workspace.py` and other YARNNN prompt profiles (ADR-186)
- `api/agents/prompts/headless/*.py` posture overlays
- Tool definitions in `api/services/primitives/*.py` (description fields are LLM-facing prompts)
- Activation overlays (ADR-226)

The five axioms (D1–D3 content discipline + D5–D6 structural discipline) apply to all of them. The remediation pass (D7) scopes only the Reviewer persona-frame because that's where the failed-WriteFile pattern was observed; analogous passes for the other prompt artifacts follow when their respective drift surfaces in observation findings.

## 3. What this ADR does NOT do

- Does not change `DEFAULT_REVIEWER_WRITE_LOCKS` (still operator's policy call per ADR-293).
- Does not change AUTONOMY-mode behavior (still ADR-293's three-mode model).
- Does not introduce per-bundle persona-frame variants — the trader-vs-author divergence in failed-WriteFile concentration is a separate question for [forthcoming posture-taxonomy ADR](ADR-303-reviewer-posture-taxonomy.md) (ADR-303).
- Does not address the **substrate-surfacing blindspots** (failed actions invisible, silent-exit prose unrecorded). Those are ADR-303 territory — operator-visibility into the Reviewer's actual cognition is a posture-substrate-contract question, not a prompt-discipline question. This ADR's remediation may reduce the failed-WriteFile rate by eliminating the canon contradiction, but the visibility floor is set by ADR-303.

## 4. Acceptance criteria

After D5 remediation lands:

1. **Grep test**: `grep -c "AUTONOMY\|_autonomy\|MANDATE\|IDENTITY\|principles\.md" api/agents/reviewer_agent.py` decreases meaningfully (target: ~30 from current 64) — exact target negotiated at remediation-commit time, not pre-committed here. The point isn't absolute count; the point is no repeated claims.
2. **Code-constant parity**: the persona-frame's enumeration of locked files is generated from `DEFAULT_REVIEWER_WRITE_LOCKS` at module load, verifiable by editing the constant and seeing the prompt change without a separate prompt edit.
3. **No contradiction sweep**: a re-audit of the persona-frame finds zero files where capability is asserted differently in two places. Verifiable by re-running the per-file mention map exercise from §1.
4. **Population-audit signal**: re-run the population audit (predecessor `2026-05-25-053951`) against the new criterion (ADR-303). Failed-WriteFile rate on author-class personas should drop as the canon-vs-code contradiction stops misleading the model. Specific target deferred to ADR-303 criterion definition.

## 5. Why this matters beyond the failed-WriteFile pattern

The Reviewer persona-frame is the single most-read LLM-facing artifact in YARNNN canon — read by every Reviewer wake across every workspace. Drift in it compounds at every fire. The discipline above is **Singular Implementation applied to prompt-envelope authorship**: one canonical place per concern per substrate, downstream citations rather than re-statements, code constants quoted into prompts at assembly time rather than paraphrased.

Without this discipline, every future canon evolution (next ADR that touches lock-set, next bundle that ships its own persona overlay, next axiom that adds a substrate file) adds another stratigraphic layer. The system pays alignment tax forever on under-specified criteria. The discipline closes the drift surface.

## 6. Relationship to ADR-303 (forthcoming posture taxonomy)

ADR-302 and ADR-303 are siblings, drafted in the same session, addressing different layers of the same finding:

- **ADR-302 (this)**: how the prompt expresses canon. Axiom-level. Affects every prompt artifact going forward.
- **ADR-303 (sibling)**: what postures the Reviewer can take and what substrate contract each posture honors. Cognition-level. Affects what the operator sees on cockpit surfaces.

ADR-302 reduces the canon-vs-code contradiction class. ADR-303 defines per-cell substrate visibility contracts. Both must land for the operator's "true autonomy not realized" experience to improve structurally rather than cosmetically.

## 7. Implementation phases

- **Phase 1**: ratify this ADR (the proposal itself).
- **Phase 2**: D5 + D6 structural refactor — create `api/agents/reviewer_agent_sections.py` with the section-registry typing + boundary-marker discipline. Migrate `_PERSONA_FRAME` to `_PERSONA_FRAME_SECTIONS`. CHANGELOG entry per D4. This is the load-bearing structural change; D7 textual edits follow naturally because each section's content becomes a discrete `_compute_*` function easier to edit cleanly.
- **Phase 3**: D7 remediation textual pass — delete outdated Gen 1, fix Gen 3 misstatements, replace prose enumeration with template-from-constant per D2. Most of the diff is removing duplicated capability claims now that each concern has one canonical section.
- **Phase 4**: prompt-assembly code change to template `DEFAULT_REVIEWER_WRITE_LOCKS` into the prompt at module load (D2 mechanism). Small Python edit in `reviewer_agent_sections.py::_compute_write_authority`.
- **Phase 5**: re-run population audit to measure adherence shift. If failed-WriteFile rate on author-class personas does not drop, ADR-302 is necessary-but-insufficient and ADR-303 carries the rest.

## 8. Open questions

- **Does D2's template-from-constant mechanism extend to bundle-supplied lock additions?** Operator-authored `_locks.yaml` adds paths to the lock-set at runtime. If the persona-frame templates from the constant only, operator-added locks won't appear in the prompt text. Options: (a) merge at prompt-assembly time (runtime — but breaks the cache, see D6), (b) accept that operator-added locks are runtime-discovered via WriteFile-refused-with-reason, (c) surface to operator via Clarify on first hit. Path (b) preserves caching but reduces in-prompt operator visibility; path (a) requires DANGEROUS_uncached treatment for the write-authority section. Resolved at Phase 4 implementation.
- **What's the right place to surface the canonical write-authority section in the prompt order?** Currently it's mid-prompt (§668). Closer to the decision-point ("when you're about to write") would be better but conflicts with the current sectioning that puts foundational framing first. Resolved at Phase 3 remediation.
- **Should the section registry persist sections across model versions?** As underlying LLMs change (Haiku 4.5 → Haiku 5, etc.), some sections may need per-model variants (e.g., terser phrasing for smaller-context models). Defer to a later ADR if the question becomes load-bearing.

## 9. Cross-references

- Predecessor finding: `docs/evaluations/2026-05-26-152500-failed-action-substrate-blindspot/findings.md`
- Population audit: `docs/evaluations/2026-05-25-053951-reviewer-behavior-population-audit/findings.md`
- Source-grounded refinement basis: `docs/analysis/src_claudeCC/constants/systemPromptSections.ts` (Claude Code's typed section registry) + `docs/analysis/src_claudeCC/constants/prompts.ts:560-577` (boundary marker discipline) — first-principles compatibility documented in `docs/analysis/claude-code-prompt-discipline-comparison-2026-05-26.md`
- Related canon: ADR-186 (prompt profiles), ADR-258 revised (Reviewer surface), ADR-274 / ADR-275 / ADR-276 (cadence + envelope), ADR-293 (governance taxonomy), ADR-295 (self-amendment evidence patterns), ADR-298 (Pace + Autonomy + Persona trifecta)
- Lock-set source: `api/services/workspace_paths.py::DEFAULT_REVIEWER_WRITE_LOCKS`
- Persona-frame source: `api/agents/reviewer_agent.py::_PERSONA_FRAME`
- Sibling ADR: ADR-303 — Reviewer Posture Taxonomy (drafted same session)
