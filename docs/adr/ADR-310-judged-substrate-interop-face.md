# ADR-310 — Judged Substrate, Served Everywhere: Interop as the Distribution Face of One Moat

**Status:** Proposed (2026-06-01)
**Amended by [ADR-373](ADR-373-multi-principal-workspace-and-the-re-key.md) (2026-06-26):** D5's shared-workspace deferral (the `user_id → workspace_id` re-key) is **resolved** — the workspace becomes the substrate's binding unit and an open set of principals attribute into it. The "one moat, two faces" thesis is preserved unchanged; the foreign caller now resolves to `(workspace_id, grant)`, and the Reviewer that judges foreign contributions is the workspace-level seat (always its design).
**Supersedes:** ADR-169 (MCP as Context Hub — the cross-LLM tool surface; its OAuth/transport infrastructure is preserved and amended, not deleted)
**Amends:** FOUNDATIONS Axiom 6 (Channel — "Foreign LLM via MCP" row gains a judgment clause), ADR-296 (substrate_event wake source gains a new caller), ADR-288 (`yarnnn:mcp` caller-identity becomes load-bearing in the wake envelope)
**Preserves:** FOUNDATIONS Axioms 1–8, THESIS four commitments, ADR-209 Authored Substrate, ADR-222 OS framing, ADR-307 uniform permission gate, the frozen `submit_wake_proposal` interface
**Dimensional classification:** Channel (primary, Axiom 6) + Identity (Reviewer judges foreign contributions) + Substrate (the thing served)

---

## 1. Context — the orphan thesis and the worldview that moved underneath it

ADR-169 (2026-04-09) framed the MCP server as a **context hub**: foreign LLMs consult-and-contribute to YARNNN's substrate, and "cross-LLM continuity becomes the product, not a side-effect." It pinned the differentiated claim — "a category of one: a *living* hub" — on the **autonomous workforce** that grew the substrate in the background.

That organ no longer exists. Between April and June 2026 the conceptual center of YARNNN moved:

- ADR-222 canonized YARNNN as an **agent-native operating system** (literal, not metaphorical).
- ADR-231 dissolved the task abstraction; ADR-260/261/262 collapsed the execution model and made the **Reviewer real-time and central**.
- The bare-kernel ratification (2026-06-01) established **program-activation as the product floor** and confirmed that **"the Reviewer is the only conversational intelligence in the live system"** — there is no general workforce growing substrate in the background.

ADR-169's thesis was therefore **orphaned, not wrong**: its subject (the workforce) was removed. Internally the cross-LLM/MCP thread went silent — ADR-288 reduced MCP to an `authored_by` value, ADR-289 named MCP write-backs only as "a future invocation class." The hub thesis survived only as demoted "optionality beyond the current product" in NARRATIVE.md.

An audit of the live MCP code (2026-06-01) confirmed the orphaning concretely: the three tools predate the judgment seat and **have no connection to it whatsoever**. A foreign LLM's `remember_this` write lands as ordinary substrate, bypassing the ADR-307 uniform permission gate that every other consequential write now routes through. Two of the three tools also carried latent `AttributeError`s masked by try/except (fixed separately in commit `e9e69ab`).

## 2. Decision — one moat, two faces

YARNNN has **exactly one moat: authored substrate under a persona-bearing judgment seat** (THESIS Commitments 2 + 4). This ADR ratifies that the cross-LLM/interop capability is **not a second moat** and **not a separate product**. It is the **distribution face of the one moat** — the channel through which judged substrate reaches the LLMs an operator already uses.

This re-pins ADR-169's "living hub" claim from the dead workforce onto the **live Reviewer**:

> A storage MCP server (Notion, Linear, GitHub) returns whatever is stored — garbage in, garbage out, no opinion. **YARNNN's MCP returns substrate the Reviewer has judged, and accepts contributions the Reviewer evaluates.** The cross-LLM hub is a *judged* hub. The copyable half (three thin MCP tools) sits downstream of the uncopyable half (a calibrated judgment seat reasoning over authored ground-truth). That is what makes it defensible, and it is what a weekend-clone cannot reproduce.

### D1 — Two faces of one substrate (the framing)

| Face | Consumer | Purpose | Surface |
|------|----------|---------|---------|
| **Cockpit face** | The operator, in-app | Run an operation with judgment | YARNNN web shell (ADR-309 two registers) |
| **Interop face** | A foreign LLM, via MCP | Reach the *same* judged substrate from any LLM the operator uses | `yarnnn-mcp-server` (3 intent-shaped tools) |

The substrate is identical across both faces. THESIS Commitment 4's portability clause — context "travels with the operator across any model, any agent layer, any future incumbent" — is *the property that makes the interop face coherent*. The interop face is not an addition to the architecture; it is the portability commitment, exercised.

### D2 — The interop face is always downstream of judgment

This is the load-bearing discipline that distinguishes a judged hub from a storage hub. Two halves:

**Read side — judgment provenance travels with the fact.** `pull_context` results carry their `authored_by` standing (operator / agent / `yarnnn:mcp` / reviewer) so a foreign LLM receives not just the fact but *the fact's standing*. A fact authored by the operator and a fact contributed by another foreign LLM are not the same epistemic object; the read boundary must not flatten them.

**Write side — foreign contributions are judged (eventually-async).** A foreign LLM's `remember_this` write:
1. Lands immediately via the existing `WriteFile` primitive (revision attributed `authored_by="yarnnn:mcp"` per ADR-288). The foreign tool **never blocks**.
2. Explicitly submits a `substrate_event` wake (`submit_wake_proposal`, the frozen ADR-296 interface) so the **Reviewer evaluates the contribution after the fact** and flags it in the cockpit if it contradicts authored ground-truth.

This is the **eventually-judged** model (chosen over gatekeeper-sync and hybrid): captured instantly, judged shortly after. It matches ADR-296's existing async wake architecture and imposes zero latency on the foreign LLM.

### D3 — Foreignness reaches the Reviewer via the wake prompt, not a new contract field

The audit established that the `substrate_event` payload (`{hook, path, field_change, revision_id}`) **does not carry `authored_by`**. Rather than extend the wake contract — which must stay frozen while core Reviewer work proceeds — the MCP write path **surfaces the foreignness in the `hook.prompt` text it submits**:

> "A foreign LLM (via MCP) just wrote to `{path}`. Evaluate whether this contribution is consistent with authored ground-truth before it becomes load-bearing."

The author is *also* structurally present on the revision (`authored_by="yarnnn:mcp"`), so the Reviewer can verify by reading the revision. No wake-contract change; the coupling between the interop stream and the Reviewer stream is **one-directional** (MCP calls an existing entry point) and **prose-carried** (no shared schema). This is what keeps the two development streams independent.

### D4 — Per-request identity (Change A): the interop face works for each operator against their own workspace

The MCP server is currently hard single-tenant (one `MCP_USER_ID` env var read at boot; every request funnels to that user). The token layer **already persists a per-request `user_id`** (`mcp_oauth_access_tokens.user_id`, read by `load_access_token`) — the request path simply discards it for the boot-time singleton.

This ADR ratifies **per-request identity resolution**:
- `authorize()` stamps the real authenticating user (implements the Supabase login redirect that single-user mode currently stubs out), not the env var.
- The tool request path builds the data client from the request token's `user_id`, not the lifespan singleton.
- **No schema change** — every substrate query already filters `.eq("user_id", ...)`; correct isolation is automatic once the right `user_id` flows in.

Each operator installs the connector on their own LLM, authenticates as themselves, and their MCP calls reach **their own** judged substrate. "Multi-user" at the MCP layer means *correctly resolving which single user is calling* — not the server impersonating many users at once.

### D5 — Shared-workspace (Change B) is explicitly deferred and out of scope

"Multiple humans operating against ONE shared substrate" is a **separate, larger, foundational change** and is **not** part of this ADR. The schema audit confirmed: every substrate table (`workspace_files`, `workspace_file_versions`, `agents`, `tasks`) scopes by `user_id == owner`; `workspace_id` exists only on three billing tables; there is no membership table. Shared-workspace would require:
- a `workspace_members` table,
- adding `workspace_id` to every substrate table and re-keying scoping from `user_id` → `workspace_id`,
- rewriting every `.eq("user_id", ...)` query (scheduler, pipeline, primitives, Reviewer dispatch, working memory),
- a membership-aware RLS rewrite.

That migration touches the Reviewer's own substrate queries and would collide with active core development. It is the **coordination face** of the moat and is **demand-gated**: it should not begin until evidence shows operators want *cross-participant coordination*, not merely *cross-LLM continuity for themselves*. Naming it out of scope is what keeps the present work low-risk.

## 3. The frozen seam — why this is safe alongside core Reviewer/eval development

The interop stream lives in `api/mcp_server/` + `api/services/mcp_composition.py` (a separate Render service). Core Reviewer/eval work lives in `api/agents/reviewer_agent.py`, `api/services/review_*.py`, `api/services/wake*.py`, and the eval harness. These edit **different files in different services**; merge surface is near-zero.

The two streams meet at exactly **one seam**: the MCP write path calls `submit_wake_proposal(client, user_id, source="substrate_event", payload=...)`. This is a **one-directional call into an existing, stable entry point** — MCP is a new *caller*, exactly like cron and the scheduler. As long as `submit_wake_proposal`'s signature is held frozen for the duration, the streams evolve independently. The single coordination point is: *if core work must change the wake contract, that is the one moment the two streams synchronize.*

## 4. Consequences

**Positive:**
- The orphan thesis is given a correct organ (the Reviewer) and a correct frame (distribution, not second product). Canon stops carrying an unreconciled contradiction (doc-09-as-competitor vs ADR-169-as-client) — both resolve to "one moat, served two ways."
- The differentiated claim becomes real and defensible: judged hub, not storage hub.
- Per-request identity unblocks cross-LLM-for-one-operator with no schema change and no core-file touch.
- Shared-workspace stays a live, portable option (Commitment 4) without being prioritized under dub — the substrate need not be re-earned later.

**Costs / risks:**
- The eventually-judged model means a foreign contribution is *briefly* unjudged load-bearing substrate (between write and the next drain). Acceptable: the write is attributed, the wake is deterministic, and the cockpit surfaces the Reviewer's verdict. Gatekeeper-sync was rejected because it blocks the foreign tool and breaks the "just remember this" affordance.
- Per-request identity requires implementing the real OAuth login redirect (single-user mode stubs it). Bounded, MCP-isolated, no schema change.

## 5. Implementation phases

1. ✅ **Rot fixes** (commit `e9e69ab`) — `Recurrence.shape`→`.mode`, `paused` filter. MCP-isolated, stop-the-bleeding.
2. **This ADR** — doc-only ratification of the frame.
3. **Auth Change A (D4)** — per-request identity. MCP-isolated, no schema change.
4. **MCP tool rebuild** — re-derive the three tools from "judged substrate, interop as distribution face":
   - `pull_context` — surface judgment provenance (`authored_by`) on returned chunks (D2 read side).
   - `remember_this` — write via `WriteFile`, then explicit `submit_wake_proposal` with foreignness in `hook.prompt` (D2 write side + D3). Route through the ADR-307 gate via a proper caller-identity rather than a parallel path (Singular Implementation).
   - `work_on_this` — re-derive toward the **program frame**: a foreign LLM starting a session gets the operation's mandate + current judged state, not a generic active-work dump.
5. **Shared-workspace (Change B)** — DEFERRED, demand-gated. Out of scope (D5).

## 6. Rejected alternatives

- **Gatekeeper-sync writes** — blocks the foreign LLM, can reject contributions, breaks the low-friction "remember this" affordance. Rejected for general writes.
- **Extend the substrate_event payload with `authored_by`** — would couple the interop stream to the wake contract that must stay frozen during core work. Rejected in favor of prose-carried foreignness (D3).
- **Treat interop as a second moat** — two parallel features are a roadmap, not a moat; the copyable MCP tools must sit downstream of the uncopyable Reviewer to be defensible. Rejected (D2).
- **Build shared-workspace now** — foundational substrate re-key, collides with core work, demand-unproven. Deferred (D5).
