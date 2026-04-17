# Agnosticism Audit — 2026-04-17

**Question**: Should the platform be truly agnostic to domain, business, or user context?

**Short answer**: No — and the better question is "which layers must be agnostic, which layers should stay opinionated?" YARNNN is *mostly* aligned with the right split already, but the split is leaking. Core primitives are universal (correct). The defaults layered on top of them carry three overlapping ICP assumptions — solo-consultant, B2B strategic-intelligence, and content-product-with-revenue — and those assumptions have crept into substrate that is supposed to be primitive.

---

## 1. What is truly agnostic (and should stay that way)

| Layer | Evidence | Status |
|---|---|---|
| **Specialist roles** | `agent_framework.py:140–426` — researcher / analyst / writer / tracker / designer all have `"domain": None`. ADR-176 explicitly deleted the ICP domain-stewards (competitive_intel, market_research, business_dev, operations, marketing). | ✅ Correct |
| **Task output_kinds** | `task_types.py:8–15` — four abstract shapes (accumulates_context, produces_deliverable, external_action, system_maintenance). Domain-neutral. | ✅ Correct |
| **Pulse / filesystem / pipeline** | ADR-141 (mechanical scheduling), ADR-181 (source-agnostic feedback), ADR-173 (accumulation-first) — all describe behaviors independent of what domain the work is about. | ✅ Correct |
| **MCP surface** | ADR-169 — three intent-shaped tools (`work_on_this`, `pull_context`, `remember_this`). No domain vocabulary. | ✅ Correct |
| **Demand-driven domains (principle)** | `directory_registry.py:682–700` — `scaffold_all_directories` only scaffolds `signals/` at signup. ADR-176 Decision 5. | ✅ Correct in code |
| **TP as meta-cognitive agent** | FOUNDATIONS Axiom 1 — TP owns "attention allocation", no domain. | ✅ Correct |

This layer is the load-bearing claim of the platform thesis (NARRATIVE.md Thesis 1: "the application layer for work" must not collapse into one vertical). It is mostly intact.

---

## 2. Where ICP assumptions have crept into substrate

### 2.1 Directory registry is still an ICP artifact

`directory_registry.py` pre-declares 11 canonical context domains. The file comment on line 60 is honest about it: *"Current ICP: solo founder / small team. Subject to expansion."* The entity templates lock in a specific lens:

- `competitors` entity template includes `## Funding & Size`, `## Leadership`, `## Threat Assessment`, `## Positioning` — B2B strategic-intelligence frame (line 99–102).
- `market` entity has `## Market Size & Growth`, `## Key Players` — market-intelligence frame (line 123).
- `relationships` entity has `## Role & Company` — B2B networking frame (line 144).

This is tolerable as a *default set*, but `scaffold_context_domain` (line 718–733) treats unknown domains as second-class — they get a one-line `landscape.md` stub while registered domains get full entity structure + synthesis + tracker + assets folder. A user whose work is nothing like the ICP (a translator, a physician, a visual artist) gets a degraded substrate compared to the baked-in domains.

**The principle is right (demand-driven domains). The execution creates a two-tier world.**

### 2.2 Pre-scaffolded bots that presume a business shape

`agent_framework.py:912–931` scaffolds **every** bot at signup, including paused ones:

```python
{"title": "Commerce Bot", "role": "commerce_bot"},   # ADR-183
{"title": "Trading Bot", "role": "trading_bot"},     # ADR-187
```

A lawyer signing up gets a Trading Bot in their roster. A trader gets a Commerce Bot. This is the opposite of agnosticism — it's "here are the ICPs we think you might be" embedded in the default filesystem. Compare to `slack_bot`/`notion_bot`/`github_bot`, which are also pre-scaffolded but correspond to neutral communication substrate (every knowledge worker uses something like Slack). Commerce and trading are *business-model* assumptions, not *platform* assumptions.

### 2.3 Revenue-as-moat is a foundational axiom now

FOUNDATIONS Axiom 4 was extended 2026-04-15 (v4.4) with *"Revenue as Moat Proof"*:

> For content product businesses, revenue is the proof that accumulated attention has value… Revenue is perception, not infrastructure.

This is a strong claim — a content-product operator is one specific ICP slice. By pulling it into the foundational axioms, the architecture now assumes every user has revenue as the downstream quality signal. A nonprofit, a researcher, a team lead at a large company — none of these are content-product businesses. The axiom either needs to be generalized ("external validation of accumulated attention, where revenue is one instance") or scoped to an ICP layer.

### 2.4 TP onboarding prompt bakes in the strategic-intelligence default

`tp_prompts/onboarding.py` task catalog (line 381–403) leads with `track-competitors`, `track-market`, `competitive-brief`, `market-report`, `stakeholder-update`, `meeting-prep`. The example scaffolding call uses Cursor / GitHub Copilot / Codeium as canonical competitors. TP's cognitive reach is shaped by this catalog — when a user describes generic work, TP will still reach for "do you want to track competitors?" because that's the first example it sees.

### 2.5 Daily-update heartbeat (ADR-161) is more opinionated than it looks

Every workspace gets a daily morning email, cannot be archived, runs even when empty. Reasonable for operators who want a briefing rhythm. Less obviously right for users whose work is episodic (quarterly deep investigations, project-bounded deliverables, reactive-only workflows). It is the one task every user is *forced* to have.

---

## 3. The tension summarized

| What | Thesis says | Implementation does |
|---|---|---|
| Specialist roles | Universal | Universal ✅ |
| Context domains | Demand-driven | Pre-declared with ICP-biased templates; unknown domains second-class |
| Agent roster | Scaffolded at signup but activated by need | Scaffolds roles the user may never need (commerce, trading) |
| Task catalog | Catalog, not prescription | Frames TP's default conversational pull |
| Moat | Accumulated attention | Revenue-as-moat elevated to foundational axiom |

The rigorous version of the thesis is: **primitives fully agnostic; defaults opinionated toward a chosen ICP; boundary explicit.** YARNNN is doing the first two but the boundary between them is drifting.

---

## 4. Recommendation

### 4.1 Don't try to be universally agnostic

NARRATIVE.md Beat 6 commits to an entry wedge ("solo consultants with recurring client obligations"). Pick an ICP, be opinionated about defaults for them, grow the concentric rings outward. Universal-at-all-layers would degrade the product for the core user without buying credibility with anyone else.

### 4.2 Harden the primitive / default boundary

Three concrete moves that preserve the ICP wedge while freeing the primitive layer:

**(a) Stop pre-scaffolding bots that presume a business model.** Commerce Bot and Trading Bot should be created *only* when the corresponding provider is connected, the way the registry already says domains work (ADR-176 Decision 5 applied to agents). A lawyer's roster shouldn't contain a Trading Bot in any form. `agent_framework.py:925–928` is the one line to change.

**(b) Give unknown domains the same treatment as registry domains.** `scaffold_context_domain:718–733` currently fork-paths unknown domains into a degraded shape (single landscape.md stub vs. full entity/synthesis/tracker structure). Instead, scaffold them with a *generic* entity template and let the tracker/synthesis machinery work identically. A user who wants to track "case files" or "patients" or "compositions" should get parity with one who tracks competitors.

**(c) Scope revenue-as-moat to an ICP layer, not Axiom 4.** The generalization is already there in your own text — *"accumulated attention produces value, revenue is the external proof when applicable."* The commerce substrate (ADR-183) can keep all its machinery; the axiom just shouldn't claim all users are content-product businesses. This is a doc edit, not a code change.

### 4.3 Two smaller cleanups

**(d) Reframe the TP task catalog.** The catalog in `tp_prompts/onboarding.py:381` leads with strategic-intelligence tasks. Reorder or group so the first examples TP sees aren't "track competitors" — instead show one task from each output_kind shape. This keeps the catalog available without priming TP to reach for it.

**(e) Tag registry defaults with `icp_default: true`.** Explicit metadata beats implicit convention. If `competitors`, `market`, `relationships`, `projects` are marked `icp_default=true` and `signals` is marked `primitive=true`, every future contributor has the split visible. The boundary stops drifting.

---

## 5. The headline

The platform's core bet (FOUNDATIONS + ADR-176 + NARRATIVE Thesis 1) is *not* that YARNNN is agnostic to everything — it's that the **application layer for work context** has to be domain-shape-aware at the defaults while being domain-shape-free at the substrate. That split is the product. Right now the substrate has a small but real ICP leak in four places (directory registry templates, pre-scaffolded commerce/trading bots, revenue-as-moat axiom, TP task catalog ordering). Closing those leaks preserves the wedge and protects the universality claim that makes the thesis coherent.

**Don't become agnostic. Tighten the boundary.**

---

### Evidence index

- `api/services/agent_framework.py:131–712` — AGENT_TEMPLATES (specialist roles, bots, TP)
- `api/services/agent_framework.py:912–931` — DEFAULT_ROSTER (pre-scaffolded bots including commerce + trading)
- `api/services/directory_registry.py:60` — *"Current ICP: solo founder / small team"*
- `api/services/directory_registry.py:91–331` — ICP-biased entity templates
- `api/services/directory_registry.py:682–776` — demand-driven scaffolding (signals only at signup)
- `api/services/task_types.py:8–15` — abstract output_kinds (agnostic)
- `api/agents/tp_prompts/onboarding.py:381–412` — task catalog framing
- `docs/architecture/FOUNDATIONS.md` v4.4 — Axiom 4 "Revenue as Moat Proof"
- `docs/NARRATIVE.md` Beat 6 — entry wedge = solo consultants
- ADR-176 — work-first universal specialist roster
- ADR-161 — daily-update as universal heartbeat
- ADR-183 / ADR-184 — commerce substrate + revenue metrics
- ADR-187 — trading substrate
