# Interop-First Pivot & Agent Gating — Strategy + Impact-Radius Analysis

**Date:** 2026-06-25
**Status:** Analysis / discourse — pre-decision. Not canon. No ADR yet.
**Author context:** Strategic consult (KVK) on repositioning YARNNN's GTM and product surface. Codebase impact-radius audited against the live repo (`/Users/macbook/yarnnn`) at time of writing.

---

## 1. The question

YARNNN has grown into two cleanly separable layers:

1. **A file-system-native substrate + interop layer** — the Authored Substrate (ADR-209: content-addressed, parent-pointered, attributed filesystem), the file primitives, the revision chain, the MCP interop face (ADR-310/311), and the platform connections that feed it.
2. **A separated autonomous-agent / Reviewer layer** — the persona-bearing judgment seat, wake architecture (ADR-296/298), pace/budget governance, program bundles (alpha-trader, alpha-author, …), and the proposal/queue/autonomy stack.

The original proposal was to **fork**: clone the repo to a new product ("freddyy.ai", Frankenstein-inspired) carrying both layers, and strip the *current* repo down to the interop play alone.

This analysis rejects the fork in favor of a stronger framing: **one umbrella, interop-first GTM, agent as a gated beta / added service.** It documents why that sequencing is correct, what the base product actually is, the open decisions to resolve, and a code-grounded feasibility audit of gating the agent layer.

---

## 2. Decision: one umbrella, interop-first, agent-as-beta

Keep a single codebase. Sequence the **narrative and the product surface**, not the code:

- **Default product = the substrate + interop + connections layer.** Foregrounded in activation, landing, and marketing as *"a version-controlled, attributed, cross-LLM context filesystem, fed by your connected tools."*
- **Agent layer = a gated beta / premium add-on.** Present but disabled-by-default for new users; surfaced as an expansion once trust and substrate density are established.

### Why the fork is rejected

The fork was solving exactly one real problem — **brand-isolating the speculative agent bet from the proven substrate.** The beta flag solves that same problem at a fraction of the cost. A literal repo duplication incurs a permanent porting tax (every substrate improvement must be hand-ported between diverging repos), which is the classic way forks die.

If an escape-hatch is still wanted, take a **tagged git snapshot** (e.g. `v-pre-interop-pivot`), not a parallel maintained repo. The "separate creature" instinct is satisfied by a feature surface, not a second codebase.

> The feasibility audit (§6) shows the fork is *doubly* unnecessary: the architecture already cut the seam this strategy needs, so gating the agent is ~3 flag checks, not a rebuild.

---

## 3. Why this sequencing is correct — benchmarks

The pattern across companies that won is monotonous: **a tool/substrate wedge that is independently valuable and accumulates proprietary data through use, THEN an intelligence layer that monetizes the accumulation.** The intelligence layer is a wedge-expander and margin-expander, never the wedge itself.

### Truest mirror: git → GitHub → Copilot

This is not an analogy — it is the same architecture one layer up. ADR-209 literally adopts three of git's five capabilities (content-addressing, parent-pointer history, attribution).

- **git** = the primitive: a content-addressed, attributed, versioned filesystem. Useful alone, with zero intelligence.
- **GitHub** = the substrate-as-product: connections, collaboration, the social/interop layer on top of git. A complete, beloved, monetizable business for ~13 years with no AI in it. **The substrate alone won.**
- **Copilot** = the intelligence layer — only possible *and* valuable because a decade of attributed, versioned substrate existed to ground it.

YARNNN's stack maps exactly: authored substrate (git-equivalent) → interop/connections/files product (GitHub-equivalent) → agent (Copilot-equivalent). The lesson is blunt: the substrate was independently a winner; the AI was an expansion.

### Monetization mirror: Notion → Notion AI

Years as a docs/database substrate that accumulated users and content, *then* AI layered as a separate paid add-on. Notion AI only works because there is a populated substrate to act on. Same shape: Figma → AI, Salesforce → Einstein, Intercom inbox → Fin, Stripe payments-primitive → platform.

(The originally-floated Slack/Slackbot framing is the weakest candidate — Slackbot was garnish, never a value layer, and under-describes how serious the agent is meant to be. Notion AI and Copilot are the right altitude.)

### The non-obvious reason this is right (not merely cautious)

The strongest argument is not "ship the reliable thing first to build trust" (true though it is — files don't hallucinate). It is:

**The agent gets better the longer you wait, because it feeds on accumulated substrate.** Notion AI and Copilot were good *on launch day* because they launched onto a mountain of existing content. An agent launched into empty workspaces underwhelms and burns its one first impression. Interop-first is therefore the *mechanism* by which the agent becomes good — substrate accumulation is the agent's grounding fuel — not a delay tolerated for caution's sake.

### Pricing architecture that falls out (consistent with ADR-334)

- **Substrate + interop = the base.** Cheap or free. Land-grab. Low trust cost, broad top of funnel.
- **Agent = the premium add-on.** Notion AI / Copilot priced the intelligence layer at ~$10–20; the existing delegation-tier thinking ($149/$299/$499) is the same shape one notch up. The substrate *lands*; the agent *monetizes the accumulation.*

---

## 4. What the base product IS

The wedge must be a **complete product, not a teaser for the agent.** Two commitments make that true:

1. **Lead with the `trace` differentiator, not with storage.** The differentiator is already named in the code — the `trace` MCP tool returns the authored revision chain, its docstring stating it shows *"which a plain storage connector cannot show."* The hero claim is *"your context, version-controlled and traceable across every LLM"* — write in Claude, it's instantly in ChatGPT, attributed and versioned. If the hero claim is "store your context," the product is Dropbox and commoditizes. If it's git's model served cross-LLM, it doesn't.

2. **Make mechanical / foreign-LLM distillation the default.** The one place the base product currently leans on the agent is the *intelligence of what-to-keep* when distilling raw platform dumps. The mechanical perception primitives (`TrackWebSources` / `TrackForeign`, zero-LLM) already prove the write path can be agent-free. Product invariant: **the base value loop — connected tools → attributed substrate → served cross-LLM via MCP — must close with zero YARNNN-agent dependency.**

**The "who we are NOT" sentence** (moat statement): *attribution + parent-pointered revision history + a single enforced write path (git's model), served cross-LLM.* YARNNN is git for LLM context — not a memory cache, MCP filesystem, or notes app.

---

## 5. Open decisions to resolve before implementation

1. **What is "chat" in the base product?** The chat/feed surface is an agent entry point, not pure substrate (it routes to the Reviewer via the addressed-wake path). This is product-defining, not cosmetic. **Recommendation: the base product has no chat of its own.** YARNNN is *the substrate your existing chats share*, not another chat window competing with ChatGPT/Claude. A YARNNN-native chat/judgment surface reappears in the agent beta. The whole nav and onboarding follow from this call, so resolve it first.

2. **Naming / snapshot.** Drop "freddyy.ai" as a separate product. Keep the established `yarnnn` brand on the proven substrate. If an escape-hatch is wanted, tag a git snapshot rather than fork.

3. **Density-gate the agent beta.** Don't open the beta into a cold workspace. Gate activation on substrate density (N connected sources + M revisions) so the agent launches onto fuel and makes a strong first impression. Operationalizes the "substrate is the agent's fuel" insight.

4. **Which agent surface to beta first.** Start with the lightest, most obviously-useful, lowest-trust-cost capability (ambient cross-LLM memory / substrate-curation). The autonomous capital-action Reviewer is the *last* surface to expose, not the first beta. Match the beta's autonomy to the trust earned by then.

---

## 6. Impact-radius audit (code-grounded)

Repo: **~189K source LOC** (137K API Python, 52K web TS/TSX). All counts are real `wc -l` against the live repo.

### Two-layer split

| | Agent layer (gate behind beta) | Substrate + interop + connections (keep, foreground) |
|---|---|---|
| Backend | ~22.0K LOC, ~44 files | ~13.5K LOC (substrate 3.0K · MCP 1.8K · connections/perception 7.5K · compositor 1.1K) |
| Frontend | ~10.5K LOC, ~50 files | ~15.7K LOC (macOS shell, Files, revisions, connectors, content-shapes) |
| Bundles | 77 files / 7.6K lines (5 programs) | — |
| **Total** | **~32.5K LOC (~17% of repo)** | **~29K LOC** |

The agent layer is mid-weight (~17% of the codebase) but the single most architecturally central slice — where the last ~150 ADRs concentrated. Backend is the heavy end (~2:1 over frontend); five files exceed 1,500 LOC (`reviewer_agent.py` 2032, `wake.py` 1820, `routes/agents.py` 1678, `routes/feed.py` 1515, `outcomes/ledger.py` 1183).

### Finding 1 — the keeper layer is already a complete standalone product

- **Own UI shell:** the macOS-desktop window manager (`web/lib/shell/useSurfacePreferences.tsx` 871 + `web/components/shell/*` ~4.8K) + Files surface (`files/page.tsx` 761) + revision history (`RevisionHistoryPanel.tsx` 384) + connectors. Surfaces are *derived from substrate* (ADR-297: `kernel_surfaces.py` declares 1:1 surface↔substrate; FE renders via L2 content-shapes + L3 library) — they render with zero agent dependency.
- **Own data model (strongest asset):** `workspace_files` + `workspace_blobs` (content-addressed CAS) + `workspace_file_versions` (parent-pointered, attributed, required `authored_by` + `message`), behind a single enforced `write_revision()` (`authored_substrate.py:264`). Git's three durable capabilities minus branching, fully independent of any agent.
- **Own value loop:** connected tools → attributed substrate → served cross-LLM via MCP (`remember` / `recall` / `trace`). Closes without the Reviewer. The only seam is distillation *quality* (see §4 commitment 2).

The base product is not something to be extracted and built — it already exists inside the repo.

### Finding 2 — gating the agent is a feature-flag, not a rebuild

Feasibility verdict from the seam audit: **small effort, low risk.** The architecture already cut this seam:

- `write_revision()` contains **zero** wake/Reviewer calls. The producer (file writes) is decoupled from the consumer (the agent) by a scheduler poll, not a synchronous call. Writing a file fires nothing. The only synchronous write→wake site is the MCP foreign-write adapter (`mcp_composition.py:468`), deliberately isolated and "never raises" — substrate commits regardless of wake outcome.
- DB schema is cleanly partitioned: substrate tables (`workspace_files`, `workspace_blobs`, `workspace_file_versions`, `platform_connections`) and agent tables (`wake_queue`, `action_proposals`, `execution_events`) share only `auth.users`. **No cross-layer foreign keys in either direction.** Agent off → agent tables stay empty (no migration); independently safe to drop later.

### Chokepoints to gate the agent OFF

| # | Chokepoint | File:line | Action when flag OFF |
|---|------------|-----------|----------------------|
| 1 | Wake-queue **drain + hook-walker + due dispatch** | `api/jobs/unified_scheduler.py` ~`:371` (`drain_all_users_with_pending`), ~`:335` (`walk_hooks`), ~`:317` (`dispatch_due_invocations`) | Wrap the block in `if AGENT_ENABLED` → nothing ever wakes the Reviewer. Cleanest single gate. |
| 2 | Wake **enqueue** gateway | `api/services/wake.py:118` (`submit_wake_proposal`) | Early-return disabled. Belt-and-suspenders; #1 alone suffices. |
| 3 | Addressed (chat→Reviewer) path | `api/routes/feed.py:1126` (`wake_addressed_stream`) + manual-fire callers (`routes/agents.py`, `routes/recurrences.py`, `routes/admin.py`) | Per §5 decision 1: base product drops native chat, or degrades it to a thin substrate assistant. |
| 4 | Surface catalog (nav) | `api/services/kernel_surfaces.py:203` (`KERNEL_SURFACES`) | Filter out agent surfaces. **Frontend nav is 100% backend-driven** — filtering this list removes agent surfaces from the UI with zero FE code change. |

**Filter at #4 (agent surfaces):** `agents`, `queue`, `notifications`, `autonomy`, `program`, `recurrence`, `expected-output`, `activity`.
**Keepers:** `files`, `connectors`, `sources`, `settings`/`workspace-settings`, `identity`/`mandate`/`principles` (constitution mirrors), `home` (designed with a substrate-forward empty state).

Frontend keepers (`files/page.tsx`, `shell/Desktop.tsx`, `useSurfacePreferences`) import **no** agent/reviewer/proposal components; the surface registry is the only coupling point, and it is backend-driven.

---

## 7. Risks / entanglements to watch

1. **Chat is an agent entry point (the one keeper-looking surface that is agent-coupled).** Resolve §5 decision 1 deliberately — it is the most user-visible call.
2. **Gate the hook-walker too, not just the drain.** The substrate_event walker fires for all active users every scheduler tick. If only the drain is gated, flagged-off workspaces silently accumulate undrained `wake_queue` rows. Gate the walker+drain block as a unit at chokepoint #1.
3. **Home's six-slot composition assumes the agent.** It was designed with a substrate-forward empty state (ADR-312), so this is *verification, not work* — confirm it reads as the intended default product, not a degraded ex-cockpit.
4. **Permanent-beta / commoditization (strategic).** A pure files+connections wedge can commoditize (cf. Dropbox). The defense is never stripping the differentiated substrate property (attribution + versioning + cross-LLM coherence — §4), and giving the beta agent a credible date and demo rather than an indefinite "coming soon."

---

## 8. CLAUDE.md drift (fix in the same pass)

The audit found stale references in `CLAUDE.md`'s file map — these files **no longer exist**:

- `invocation_dispatcher.py` — dispatch absorbed into the wake architecture (ADR-296/298).
- `pace.py` — collapsed into budget (ADR-327).
- `manage_recurrence.py` / `recurrence_paths.py` — recurrence lifecycle moved into `primitives/schedule.py`.

Worth correcting so downstream analysis (and any ADR derived from this memo) cites real files.

---

## 9. Recommended sequencing

1. **Resolve the four open decisions in §5** (chat first — it gates nav and onboarding).
2. **Extract / confirm the seam as a single `AGENT_ENABLED` flag** at the four chokepoints in §6. No deletion; gating only.
3. **Reframe the default surface** to substrate-forward (Files + Connections + the `trace`/cross-LLM coherence story); confirm Home's empty state.
4. **Make mechanical/foreign-LLM distillation the default** so the base value loop is agent-independent (§4 commitment 2).
5. **Rewrite landing/activation** around the `trace` differentiator and the "who we are NOT" sentence.
6. **Gate the agent beta on substrate density** (§5 decision 3); expose the lightest agent surface first (§5 decision 4).
7. **Promote to an ADR** once the chat decision and flag placement are settled — this memo is the pre-decision discourse, not canon.

> Net: one-umbrella, interop-first, agent-as-gated-beta dominates the fork strategically (same brand isolation, no porting tax) *and* mechanically (the codebase was built with this seam pre-cut — ~3 flag checks + a list filter + a product decision on chat).
