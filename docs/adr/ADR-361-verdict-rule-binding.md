# ADR-361 — Verdict→Rule Binding: a material verdict records which principle drove it

**Status**: Proposed — **DEFERRED-CONDITIONAL per [ADR-364](ADR-364-the-reflection-organ.md) D5** (2026-06-24)
**Deciders**: KVK + Claude
**Dimensional classification** (Axiom 0): **Substrate** (primary — a new structured field on the judgment lineage) + **Channel** (the verdict tool's contract).
**Concern + sequence**: This is the **rule-attribution dimension** of self-improvement. **[ADR-364](ADR-364-the-reflection-organ.md) re-founded the split**: the actual missing primitive was the *verdict→outcome join key* (`proposal_id`, shipped in ADR-364 D1), not this *verdict→rule* binding. So `cited_rules` is now **deferred-conditional** — the basic reflection loop (ADR-364: verdict→outcome, via `reflection.md`) closes first; this rule dimension is pulled **only if** `reflection.md` shows that per-rule attribution is the missing depth. It is NOT a prerequisite for the basic loop. (`cited_rules` is self-improvement plumbing, NOT context handling — that distinction is why ADR-363 exists; the loop-keystone is why ADR-364 exists.) Gated behind: Concern 1 (ADR-363, settled) + ADR-364's basic loop proving it needs the rule dimension.
**Prerequisite for**: [ADR-362](ADR-362-inspector-auditor-seat.md) (the Inspector/Auditor seat — it cannot assess rule track-records without this binding).
**Extends / reuses (no new taxonomy)**: ADR-281 §5 (judgment_log material-outcome lineage), ADR-258 (ReturnVerdict tool), ADR-209 (authored substrate — the binding is attributed substrate like everything else). Distinct from [ADR-357](ADR-357-citation-binds-to-source-not-internal-path.md)/DP31, which binds a *claim* to its external *Source*; this binds a *verdict* to the internal *rule* (`principles.md` clause) it applied. Source-binding and rule-binding are orthogonal — DP31 is output→world, this is verdict→rulebook.
**Discourse base**: [`context-continuity-and-self-improvement-2026-06-24.md`](../analysis/context-continuity-and-self-improvement-2026-06-24.md) §3e (the judgment-calibration organ) + the 2026-06-24 pressure-test (BREAK 1: the verdict→rule join does not exist on current substrate).

---

## 1. The problem (BREAK 1, receipt-grounded)

The self-improvement design (the Inspector seat, ADR-362) rests on a mechanical join: *for each material verdict, which rule(s) did it apply, and did applying them produce a good ground-truth outcome?* The pressure-test falsified the premise that this join exists:

- **`judgment_log.md` records the rule only in free-form prose.** `reviewer_audit.py` schema (the `--- material-outcome ---` block): `timestamp`, `slug`, `trigger`, `reviewer_identity`, `outcome_kind`, then `<free-form Reviewer verdict + reasoning>`. There is **no structured field naming the applied principle.** A zero-LLM attribution mirror has nothing to join on.
- **DP31 (ADR-357) is the wrong binding.** It binds a *claim* to its external *Source* (`source_ref` — a URL, a repo path). It says nothing about which `principles.md` clause drove a verdict. The two are orthogonal; conflating them was the design error the pressure-test caught.

Without a structured verdict→rule binding, the Inspector can only LLM-infer which rule drove each verdict from prose — which violates DP19 (the organ would no longer be mechanical) and makes the *evidence base itself a judgment that can be wrong*. The honest fix is to make the binding **explicit at authoring time**, where the Reviewer already knows which rule it applied.

## 2. Why this belongs to the Reviewer seat, not the Inspector

This is independently valuable to the Reviewer regardless of whether the Inspector ever ships: **it makes the Reviewer's own reasoning auditable.** An operator (or the Reviewer one wake later) reading `judgment_log.md` can trace each verdict to the rule that authorized it — the mandate→reasoning chain the persona-frame already asks for in prose, now structured. So ADR-361 is a Reviewer-side substrate hardening; ADR-362 is a *consumer* of it. Separating them keeps "make judgment auditable" (useful alone) distinct from "add a seat that audits it" (the new seat).

## 3. Decisions

### D1 — `cited_rules` field on the ReturnVerdict contract

`RETURN_VERDICT_TOOL.input_schema.properties` (`agents/reviewer_agent.py`) gains an **optional** field:

```
"cited_rules": {
  "type": "array",
  "items": {"type": "string"},
  "description": (
    "The principle(s) from principles.md that drove THIS verdict, each as a "
    "stable clause reference (e.g. 'anti-slop:§3.2', 'cadence-flag:§4', "
    "'risk-floor:§2.1'). Name the rule(s) your verdict actually rests on — "
    "the same rule you'd cite in your reasoning. Omit only when no specific "
    "rule applied (a pure stand-down on a quiet world). This makes your "
    "judgment auditable: a later read can trace the verdict to its authority."
  ),
}
```

**Optional, not required** — D5 explains why (a forced field degrades into noise). The persona-frame already directs the Reviewer to cite the load-bearing MANDATE/principle clause in prose; this lifts that existing discipline into a structured field.

### D2 — `cited_rules` written to the lineage frontmatter

`reviewer_audit.py::render_lineage_entry_if_material` writes `cited_rules` into the material-outcome frontmatter block (a YAML list line) when present on the verdict. Absent → the line is omitted (no empty-field noise). Written through the Authored Substrate (ADR-209) like every other lineage field — `authored_by="reviewer:<identity>"`.

### D3 — clause-reference shape: program-declared, kernel-neutral

The kernel does NOT hardcode rule identifiers (ADR-222: kernel names categories, bundles name instances). A `cited_rule` string is a free-form stable reference the *program's* `principles.md` defines (alpha-author uses `anti-slop:§3.2`; alpha-trader uses `risk-floor:§2.1`). The kernel stores and joins on the string; it never interprets it. The Inspector (ADR-362) joins `cited_rules` strings against the same `principles.md` clause headings — a string match, no kernel semantics. **Discipline:** a bundle's `principles.md` should carry stable clause anchors (a heading or `§N` tag per rule) so the references resolve; this is a bundle-authoring convention, documented in the bundle `_workspace_guide.md`, not a kernel schema.

### D4 — the false-negative bound, stated honestly

`judgment_log.md` records only **material** outcomes (the ADR-281 §5 5-condition gate). A verdict that produces no material outcome — a pure stand-down — leaves no lineage entry, so it carries no `cited_rules`. Consequence: **a rule that causes the Reviewer to wrongly stand down (a false negative) leaves no auditable trace.** The Inspector built on this binding can assess rules that *fired* (produced an action), not rules that *suppressed* action. This is a real bound, not a defect — closing it would mean logging every stand-down's rule-reasoning, which the ADR-277/281 material-gate deliberately rejected to keep the log signal-dense. ADR-362 must state this bound; ADR-361 names it here so the limit is canon, not surprise.

### D5 — optional-not-required (the Goodhart guard)

A *required* `cited_rules` field would force the Reviewer to name a rule on every verdict, including ones where no specific rule applied — producing rationalized noise (the agent inventing a citation to satisfy the schema). That is the exact pressure DP24's floor-discipline warns against. The field is **optional**; an honest omission ("no specific rule — quiet world") is more valuable than a forced citation. The Inspector treats absence as a real signal (a verdict with no cited rule is a category of its own), not as missing data to impute.

## 4. What this does NOT do

- **No new primitive, no new table.** A field on an existing tool + a line in an existing substrate file.
- **No change to verdict semantics.** The verdict enum, the material gate, the autonomy flow — all unchanged.
- **No retroactive backfill.** Historical free-form entries stay free-form; `cited_rules` populates going forward. ADR-362 must not assume a complete historical corpus (it accumulates from D1's ship date).
- **No DP31 change.** Source-citation (claim→world) is untouched; this is the orthogonal verdict→rulebook binding.

## 5. Consequences

- The Reviewer's judgment becomes mechanically auditable: verdict → cited rule → (via ADR-330 attestation) outcome. This is the join ADR-362's organ needs, and it is DP19-clean (the Inspector reads structured fields, infers nothing).
- The Reviewer must be *prompted* to populate `cited_rules` — a persona-frame addition (the close-contract gains "name the rule(s) your verdict rests on"). Small prompt surface; the discipline already exists in prose form.
- A validation note (not a hard gate, per D5): when `cited_rules` is present, each entry should resolve to a `principles.md` clause; a non-resolving reference is logged as a warning (drift signal), not rejected.

## 6. Implementation scope (sketch — not built by this ADR)

1. `agents/reviewer_agent.py` — add `cited_rules` to `RETURN_VERDICT_TOOL.input_schema`; persona-frame close-contract gains the one-line directive.
2. `services/reviewer_audit.py::render_lineage_entry_if_material` — write `cited_rules:` frontmatter line when present.
3. `api/prompts/CHANGELOG.md` — record the close-contract change (Prompt Change Protocol).
4. Bundle convention — `principles.md` clause anchors documented in `_workspace_guide.md` (alpha-author + alpha-trader).
5. Regression gate — a verdict carrying `cited_rules` round-trips into the lineage frontmatter; absent → no line.

Probe-before-canon: ship behind a regression gate; a funded wake should show `cited_rules` populating on a material verdict before ADR-362 builds on it.
