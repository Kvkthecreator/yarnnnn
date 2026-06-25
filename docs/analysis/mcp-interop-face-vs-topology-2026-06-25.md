# Analysis — the MCP interop face: what to refactor, and is it still the right thing to expose

**Date**: 2026-06-25
**Hat**: B (external developer — strategic discourse + findings. Recommends a Hat-A ADR; makes no change.)
**Status**: Proposed framing for operator (KVK) ratification. No canon edits in this doc.
**Trigger**: KVK ran a manual smoke test of the `yarnnn` connector on claude.ai — asked it to "remember this (a sample document)." The write was refused with `governance_locked`. KVK asked: is this a routing bug, a tool-surface problem, or a sign the whole interop approach needs re-examining before we refactor?
**Probe**: [`api/probe_mcp_remember_this_default.py`](../../api/probe_mcp_remember_this_default.py) — 7/7, live receipts (§7).

---

## A. Strategic frame — the moat is settled; this refactor doesn't reopen it

KVK asked to re-examine the whole moat framing before touching tools. Done — and the honest conclusion is **the framing holds, and was re-validated three weeks ago.** This refactor is *downstream* of a settled strategy, not an occasion to relitigate it. Laying that out so we don't accidentally treat an implementation gap as a strategy crisis:

**What is settled (don't reopen):**
- **One moat, two faces** (ADR-310): authored substrate under a persona-bearing judgment seat, served as a Cockpit face (in-app) + an Interop face (any LLM via MCP). The interop face is the *distribution* of the one moat, not a second moat.
- **The interop face's standalone wedge** ([sequenced-moat-strategy-2026-06-01](sequenced-moat-strategy-2026-06-01.md)): *cross-LLM continuity / portable authored memory* — valuable with the lightest substrate, no calibrated Reviewer required. The judgment layer is **additive**, turned on by a program.
- **The killer primitive** (ADR-311 §3): the **attributed, walkable revision chain**. "Who authored this claim, how did it evolve, has it been judged" — exposed across the boundary. No storage-MCP (Notion/Linear/GitHub) has attribution-as-structural to expose. This is THESIS Commitment 4 made operable.
- **The competitive read** ([cumulative-workspace-product-formulation-2026-06-10](cumulative-workspace-product-formulation-2026-06-10.md), per project memory): June-2026 incumbents commoditized "persistent / compounds / runs-in-absence" *verbally*; nobody occupies **accountable judgment over portable authored substrate**. The lead is the judgment seat; substrate-portability is the proof beneath it. Copy must carry the mechanism, not the adjective.

**What the test actually pressured** — none of the above. It pressured the *implementation* of the interop face, which is **two generations stale**:
1. The shipped tools are the ADR-169 **intent surface** (`work_on_this`/`pull_context`/`remember_this`).
2. ADR-311 (2026-06-01) **already ratified replacing them** with the kernel's **primitive surface** (`ReadFile`/`ListFiles`/`SearchFiles`/`QueryKnowledge`/`WriteFile`/`ListRevisions`/`ReadRevision`/`DiffRevisions`, MCP-mode, scoped to the commons) — operator-confirmed §7 decisions, **never implemented.**
3. ADR-320/366 then **replaced the lock mechanism** ADR-311's safety case depends on (`DEFAULT_MCP_WRITE_LOCK_PREFIXES` → the `CALLER_WRITE_POLICY` topology table), so even ADR-311's *own* D4 receipts are now stale.

So the strategic answer to "is this still the right thing to expose?" is **yes, and we already decided how — we just never built it, and the kernel moved underneath the decision twice.** The refactor is: *implement ADR-311, re-based on the live topology, plus the operator-visibility requirement the original missed.* The three sub-sections below (B: what ADR-311 got right and should survive; C: what's now stale in it; D: the one genuinely-open strategic edge) are the discourse that scopes that ADR. The evidence is §0–§7.

### B. What ADR-311 got right — survives verbatim

- **Primitive altitude over intent altitude.** The Claude Code model: a foreign LLM composes `pull_context` itself from `QueryKnowledge → ReadFile`; `work_on_this` is `ListFiles → ReadFile` (no tool); `remember_this` is `WriteFile`. Lower altitude → fewer arbitrary decisions (the "which phase does work_on_this belong to" question *dissolves*) → Singular Implementation (one vocabulary — the kernel's files — not two).
- **Revision-archaeology as the differentiator.** `ListRevisions`/`DiffRevisions` over the boundary is the moat surfaced. This is the part of the refactor that *adds* capability, not just reshapes it — and it's the part no competitor can mirror.
- **All-consequence-at-the-gate.** A foreign LLM holds raw `WriteFile`; safety is the single ADR-307 gate, not a curated allowlist. (This invariant is *more* true now under ADR-320's topology than it was under ADR-311's flat prefix list.)
- **Protocol-agnostic verbs** (D7): the file+revision verbs are the contract; MCP is the first binding. A second protocol (A2A, direct-API) is a new binding, not a surface reframe.

### C. What's now STALE in ADR-311 — the new ADR must correct

- **D4's lock-set is dead code.** ADR-311 D4 cites `DEFAULT_MCP_WRITE_LOCK_PREFIXES = ("review/", "context/_shared/")` and `permission.py:179-187`. ADR-320 **collapsed both divergent lock functions into one** `CALLER_WRITE_POLICY` root-prefix table ([workspace_paths.py:241](../../api/services/workspace_paths.py#L241)); ADR-366 split `governance/` into grant+contract. The `mcp` caller is now locked from `governance/ contract/ constitution/ persona/ system/` and writes **only `operation/`**. ADR-311's safety receipts must be re-derived against this — the *conclusion* is unchanged (foreign writes are gated) but the *mechanism it documents no longer exists*.
- **The routing layer ADR-311 deletes is exactly what's broken.** ADR-311 deletes `dispatch_remember_this` and its five-target enum — the very thing producing the `governance_locked` failure (§0). So ADR-311's refactor *is* the fix; the bug is a symptom of not having shipped it. Good news: the fix and the strategic direction are the same motion.
- **Operator-visibility is absent from ADR-311.** ADR-311 covers the *write gate* but says nothing about how the operator *learns* a foreign write happened. The test exposed that this is silent in the modal cross-room case (§6). This is a genuine gap in the ratified design, not just the implementation.

### D. The one genuinely-open strategic edge — proactivity vs. primitives

ADR-311 deletes all three intent tools. But the **MCP server instructions** ([server.py:127-142](../../api/mcp_server/server.py#L127)) carry a *behavioral* promise the primitives don't: *"Use these proactively — YARNNN is supposed to be ambient. Do not wait for the user to ask."* That ambient-proactivity is a product claim (the "it follows you across rooms" magic), and it currently rides on the intent tools' descriptions. **Raw primitives are not self-proactivating** — `WriteFile` doesn't tell a foreign LLM "call me when the user shares a decision." The open question for the ADR:

> When the intent tools are deleted, **where does the proactivity instruction live?** Options: (a) the server-level `instructions` block (already exists — strengthen it to teach the primitive compositions + when to reach for them); (b) accept that proactivity degrades to the host LLM's own judgment over the primitives (purist ADR-311 read); (c) keep *one* thin intent-shaped affordance — a `remember_this`-equivalent — purely as the proactivity carrier, composed over `WriteFile(operation/)` + the wake, with no enum that can hit a locked root. This is the Option-C hybrid from §4.

This is the only place the "pure primitives" decision has a real product cost, and it's worth an explicit decision rather than letting it fall out of the implementation. My lean: **(a) + (c)** — strengthen server instructions AND keep one write-affordance as the ambient carrier, because the cross-room *write* is the magic moment and we shouldn't make it depend on every host LLM independently deciding to compose it. Reads can be pure primitives; the one proactive write is worth a named verb.

---

## 0. The receipt (what actually happened, traced through code)

The transcript narration is accurate. The mechanism, end to end:

1. `remember_this("generic test note")` → [`classify_memory_target()`](../../api/services/mcp_composition.py#L313). No identity / brand / agent-feedback / task-feedback marker matched → default branch fires: `{"target": "memory", "confidence": "high"}` ([mcp_composition.py:388](../../api/services/mcp_composition.py#L388)).
2. `dispatch_remember_this(target="memory")` → hardcoded `WriteFile(scope="workspace", path="system/notes.md", mode="append")` ([mcp_composition.py:716-730](../../api/services/mcp_composition.py#L716)).
3. The permission gate refuses. The MCP caller class is `mcp`; [`CALLER_WRITE_POLICY["mcp"]`](../../api/services/workspace_paths.py#L243) locks `system/` (among others). A foreign-LLM write to `system/notes.md` returns `governance_locked`.

The lock is correct. The routing is wrong. The two were authored against different kernels and never reconciled.

---

## 1. What canon says SHOULD happen (the three clauses the live surface is measured against)

Three canon clauses are load-bearing here. The finding measures the live tool surface against each.

**C1 — Topology trust class (ADR-320 D3 + the grant/contract-split ADR, 2026-06-25).**
Per [`workspace_paths.py:225-228`](../../api/services/workspace_paths.py#L225): *"`mcp` — foreign LLM (yarnnn:mcp). Lowest trust. Writes ONLY the `operation/` commons; locked from everything else."* Operationalized: **every successful `remember_this` write target must resolve to a path under `operation/`.** Any target resolving to `governance/`, `contract/`, `constitution/`, `persona/`, or `system/` is, by the kernel's own access table, unreachable for this caller.

**C2 — Judged-write seam (ADR-310 D2/D3).**
A foreign-LLM contribution commits to the `operation/` commons, then wakes the Reviewer to evaluate it against authored ground-truth (eventually-async; never blocks). The tool's job is to *land a contribution in the commons* and *let the seat judge it* — NOT to amend the operator's constitution or the orchestration runtime. Operationalized: **`remember_this` should only ever write substrate that the judged-write wake is designed to evaluate** — i.e. `operation/` material, not `persona/IDENTITY.md` or `constitution/MANDATE.md`.

**C3 — One moat, two faces (ADR-310/311).**
The moat is authored substrate under a judgment seat, served as a cockpit face (in-app) + an interop face (any LLM via MCP). ADR-311 declares the interop face to be *raw kernel file + revision primitives* (`ReadFile` / `WriteFile` / `SearchFiles` / `QueryKnowledge` / `ListRevisions` / `DiffRevisions`), explicitly *superseding ADR-169's intent-shaped tools*. Operationalized: **the live MCP surface should match the ADR-311 primitive shape, or there should be a ratified reason it still ships the ADR-169 intent tools.**

---

## 2. Are those three clauses well-formed?

Before measuring the live surface against them, check each clause holds up:

- **C1 is well-formed and live.** The topology is the singular lock source (ADR-320 collapsed the two prior lock functions). There is no ambiguity about what `mcp` may write.
- **C2 is well-formed and live.** ADR-310 is implemented; [`submit_foreign_write_wake()`](../../api/services/mcp_composition.py#L815) is wired and fires on every successful write.
- **C3 names a target state that is NOT YET BUILT.** ADR-311 is **Proposed, not Implemented.** Grep of `api/mcp_server/server.py` confirms only three `@mcp.tool()` registrations ship today: `work_on_this`, `pull_context`, `remember_this` — all ADR-169. **The "interop face" the canon describes does not exist on the MCP server.** This is the real finding: canon moved to ADR-311's primitive surface, code stayed at ADR-169's intent surface. Measuring the live tools against C3 isn't "the tools are broken" — it's "the tools are a generation behind ratified canon."

This pre-flight matters: a naive read says "remember_this has a routing bug, fix the default path." The criterion audit shows the routing bug is a *symptom* of C3 — the intent-shaped tool is carrying a five-target enum (`memory | identity | brand | agent | task`) inherited from the pre-topology `UpdateContext`, and that enum has no coherent meaning under the topology trust classes.

---

## 3. Adherence — where the live surface fails each criterion

**Against C1 (topology):** Two of five routing targets resolve into locked roots for the `mcp` caller:

| `remember_this` target | resolves to | under `mcp` lock? |
|---|---|---|
| `memory` (the DEFAULT) | `system/notes.md` | **LOCKED** — `system/` |
| `identity` | `author_identity()` → `persona/` + `constitution/` | **LOCKED** — `persona/`, `constitution/` |
| `brand` | `operation/BRAND.md` | writable |
| `agent` | `agents/{slug}/memory/feedback.md` | writable |
| `task` | resolved natural-home, usually `operation/.../feedback.md` | writable |

The **default target is dead** for the most generic case — which is the modal case for an ambient "remember this." And the workaround the transcript proposed to KVK ("scope it to identity") *would also have failed*, because identity routes into `persona/`+`constitution/`, both locked for `mcp`. The transcript's advice was well-reasoned against the old model and wrong against the live kernel.

**Against C2 (judged-write):** When routing *does* succeed (`brand`/`agent`/`task`), it can write `operation/BRAND.md` and agent feedback — defensible commons contributions. But the *enum still offers* `identity` and `memory`, conceptually inviting a foreign LLM to amend the operator's constitution and the orchestration runtime. That's not what the judged-write seam is for. The enum encodes a trust model the kernel has since rejected.

**Against C3 (two faces):** The live surface is the ADR-169 face. The ADR-311 face is unbuilt. The connector KVK tested *is* the moat's interop face — and it's the wrong shape per ratified canon.

---

## 4. The discourse — three reconciliations, and the recommendation

KVK selected **"rethink the tool surface itself."** This finding agrees, and sharpens *what* the rethink is. The drift is not in any one tool — it's that the intent-shaped enum is the wrong abstraction now that ADR-311 ratified the primitive interop face. Three coherent endpoints:

### Option A — Re-base routing on topology (point-fix, does NOT match operator's verdict)
`remember_this` writes ONLY `operation/`. Default → `operation/notes.md` (or `operation/{domain}/`). `identity`/`memory` targets become `ambiguous` candidates requiring operator confirmation in-app — a foreign LLM never silently amends the constitution. **Unblocks the smoke test and fixes C1/C2. Does NOT address C3** — still the ADR-169 surface. Smallest honest change; a stepping-stone, not the destination.

### Option B — Build the ADR-311 interop face (matches operator's verdict)
Implement ADR-311 on the MCP server: expose `ReadFile` / `WriteFile` / `SearchFiles` / `QueryKnowledge` / `ListRevisions` / `DiffRevisions` as MCP tools, gated by the *same* `_is_path_locked('mcp', path)` topology that gates every other caller. `WriteFile('mcp', 'operation/...')` is the contribution path; the topology *itself* refuses constitution/persona/system writes with a coherent error a foreign LLM can read and recover from. The judged-write wake (C2) fires on the `WriteFile` seam exactly as it does today. **This makes the interop face match the cockpit face — one gate, one moat, two faces, as the canon already claims.** The three intent tools either retire or become thin convenience compositions *over* the primitive surface (e.g. `remember_this` = `WriteFile(operation/...)` + the wake), with no enum that can target a locked root.

### Option C — Hybrid (likely the actual shipping shape)
ADR-311 primitives as the *substrate* of the interop face; keep ONE intent-shaped convenience verb (`pull_context` is the genuinely-useful retrieval ergonomic — see [tool-contracts.md §Tool 2](../features/mcp/tool-contracts.md)) layered on top. Retire `remember_this`'s five-target enum entirely; its successor is `WriteFile(scope=operation)` + wake. `work_on_this` becomes a composition over `QueryKnowledge` + `ReadFile`. The *intent* names survive as ergonomics; the *enum that fought the topology* dies.

**Recommendation:** the fix is **C3-shaped (Option B/C), and it belongs in a Hat-A ADR that amends or implements ADR-311**, not a quiet patch to `mcp_composition.py`. Specifically the ADR should resolve:

1. **Does the MCP write path go through the topology gate the same way every other caller does?** (It should. Today `dispatch_remember_this` reaches `WriteFile` which *does* hit the gate — that's why the test failed correctly. The gate is right; the routing-before-the-gate is the bug.)
2. **What happens to the five-target enum?** (Recommendation: delete it. `identity`/`memory` targets are kernel-incoherent for `mcp`. A foreign LLM contributes to `operation/`; everything else is the operator's or the seat's.)
3. **Do the three ADR-169 intent tools retire, or thin out over ADR-311 primitives?** (Open — this is the canon decision. ADR-311 as written says retire; product ergonomics may argue for keeping `pull_context`. Worth an explicit decision rather than drift.)
4. **The judged-write seam (C2) is already correct** and should be preserved verbatim across whichever surface ships — it's the actual moat mechanic and the one piece that already matches canon.

---

## 5. What this finding does NOT claim

- It does **not** claim the permission lock is wrong. The lock is the kernel working as designed (ADR-320). The test *validated* governance enforcement — that part of the transcript's read is correct and worth keeping.
- It does **not** claim ADR-169 was a mistake. It was correct for its kernel (2026-04-09, pre-topology). The drift is that the kernel moved twice (ADR-320 topology, ADR-310/311 interop reframe) and the tool surface absorbed neither.
- It does **not** land the fix. Per Hat-B discipline, the fix is a ratified ADR amending/implementing ADR-311, authored in Hat-A territory (`api/mcp_server/`, `docs/adr/`). This document recommends; it does not implement.

## 6. Operator visibility — how does the user know our in/outs from external?

KVK's second question, and it surfaces a gap as load-bearing as the routing one. Traced through code + confirmed by the probe (P3/P4):

**What a foreign write produces today, in order:**

1. **The write commits** to substrate (when it lands in `operation/` — once Option A/B fixes the routing).
2. **The revision is attributed** `authored_by="yarnnn:mcp"` ([probe P2c, confirmed](../../api/probe_mcp_remember_this_default.py)). This is the *durable* record — visible in the Files surface revision history and to the Reviewer. **This is correct and the strongest part of the story.**
3. **The judged-write wake enqueues** — `submit_foreign_write_wake` → `queue_depth 0→1` ([probe P3, confirmed](../../api/probe_mcp_remember_this_default.py)). The Reviewer will evaluate the foreign contribution against ground-truth on its next drain. **This is the moat seam and it works.**
4. **A narrative entry** is *attempted* via [`_emit_mcp_narrative`](../../api/mcp_server/server.py#L66) with `role="external"`, `weight="routine"`.

**The gap is at step 4, and there is no step 5.** Two distinct holes:

**Hole A — the feed entry is session-gated (silent when the operator is away).** [`_emit_mcp_narrative`](../../api/mcp_server/server.py#L78) calls `find_active_workspace_session()` and **returns early, writing nothing, if there is no active session** ([narrative.py:282](../../api/services/narrative.py#L282), [server.py:79-85](../../api/mcp_server/server.py#L79)). The whole point of the interop face is the *cross-room* user — they write to YARNNN from claude.ai at 3pm and may have no YARNNN tab open at all. In exactly that modal case, **the foreign write leaves no feed trace.** The user switches to their YARNNN cockpit tomorrow and the contribution is in their substrate with zero narration of how it got there. The probe confirmed the mechanism (P4): the entry only writes when a session is present.

**Hole B — there is no notification path on the MCP write at all.** Grep confirms: `send_notification` / `notify_*` is **never called** from `api/mcp_server/` or `mcp_composition.py` (probe P4). Notifications exist ([notifications.py](../../api/services/notifications.py): email via Resend + a chat-session insert + an audit row) and fire for agent-delivered / agent-failed / event-triggered. **A foreign LLM writing to your substrate is not in that set.** So even if the user has email notifications on, a cross-room contribution generates no out-of-band signal.

**Why this matters for trust, not just polish.** The interop face's promise is "your thinking stays coherent across rooms" — but coherence requires the operator to *know what entered their substrate and from where*. Right now:
- ✅ The **durable attribution** is perfect (`authored_by` on the revision + the ADR-162 provenance comment in the file body).
- ✅ The **Reviewer** sees it (judged-write wake).
- ❌ The **operator** may never be told, in-the-moment, that an external LLM contributed — unless they happen to have a live session, and never out-of-band.

This is the asymmetry: the *system* (Reviewer) is fully informed of foreign in/outs; the *operator* is not. For a moat whose pitch is operator-accountable judgment over authored substrate, the human needs at least parity with the seat on "what just entered from outside."

**Recommendation (folds into the same Hat-A ADR):** a foreign write should produce a **durable, session-independent operator-facing trace** — not a session-gated best-effort narrative. Options, cheapest first:
1. **Make the MCP narrative session-independent.** Drop the `find_active_workspace_session` early-return; write the `role="external"` entry to the daily session (get-or-create), the way `_insert_chat_notification` already does ([notifications.py:172](../../api/services/notifications.py#L172)). The entry is then waiting in the feed whenever the operator returns. ~Small change, closes Hole A.
2. **Add a foreign-write notification tier** — a low-urgency, batchable "N external contributions to your workspace since you last looked" digest, gated by a new notification preference (`external_contribution`). Closes Hole B without spamming (a per-write email for an ambient tool would be wrong; a digest is right). This is the ADR-202 "notifications are pointers" discipline applied to the interop face.
3. **Surface foreign in/outs as a first-class Management-Plane reading** (ADR-338/340) — a "what entered from outside" lane in the cockpit, derived from `authored_by LIKE 'yarnnn:mcp'` revisions. This is the durable home; (1) and (2) are the in-the-moment signals that point at it.

The ADR should treat **operator-visibility of foreign in/outs as a named requirement of the interop face**, co-equal with the routing reconciliation — because an interop face the operator can't audit in-the-moment isn't trustworthy regardless of how clean the routing is.

## 7. Probe — already run (this finding is de-risked)

The cheapest validation has been executed: [`api/probe_mcp_remember_this_default.py`](../../api/probe_mcp_remember_this_default.py), driving the REAL `remember_this` dispatch + wake against a live workspace with the MCP-shaped caller (`caller_identity="yarnnn:mcp"`). **7/7 assertions pass.** Receipts:

| Probe | Claim proven | Receipt |
|---|---|---|
| P1a | generic content classifies to `target='memory'` (the default) | `got=memory` |
| P1b | the default is DEAD — `memory` → `system/notes.md` → `governance_locked` | `got=governance_locked` |
| P2a | Option A's home works — `operation/` write succeeds | `path=/workspace/operation/_interop_probe/...` |
| P2b | round-trips via `ReadFile` | content matches |
| P2c | revision attributed `authored_by='yarnnn:mcp'` — foreignness on the durable record | `got=yarnnn:mcp` |
| P3 | the judged-write wake enqueues (the ADR-310 moat seam) | `queue_depth 0→1` |
| P4 | the operator-visibility gap is real | `feed entry session-gated · notification path ABSENT` |

So the load-bearing assumptions under Option B/C are confirmed: **the topology gate + the judged-write wake compose correctly for a foreign write to `operation/`.** The ADR is now scoped to "expand the surface + close the visibility gap," NOT "discover whether the seam works." The probe is a throwaway evaluation scaffold (Hat B), not a regression gate — it leaves no substrate residue (verified: 0 residual wakes, 0 residual files).

**The fix still belongs in a ratified Hat-A ADR** (amending/implementing ADR-311 + naming operator-visibility as a requirement). The probe de-risks it; it does not substitute for it.

---

## 8. Resolution (2026-06-25) — ADR-368, memory-first

The discourse this doc opened resolved through three operator decisions and shipped as **[ADR-368](../adr/ADR-368-memory-first-interop-surface.md)**:

1. **The moat framing was re-examined and held** (operator's first ask). It was not reopened — the test pressured the *implementation*, not the strategy.
2. **The primary use case was settled: memory-first** (Model A), with delegation (Model C) deferred as the forward-compatible superset. The deciding axis was reversibility under uncertainty: A is a strict subset of C, delivers the full *substrate* moat, and C's extra has an unsolved sync-vs-stream hinge + unproven demand.
3. **The surface was re-derived from first principles** against the user's memory mental model, and against the host-reality finding (consumer hosts chain only ~3–5 rounds — so composition lives server-side, not in the host). Result: **three clean verbs — `remember` / `recall` / `trace`** — put in, get out, trace history. The raw kernel primitives remain `defer_loading` for agentic hosts.

ADR-368 supersedes ADR-311's pure-primitive conclusion (its substrate truths preserved), deletes the topology-incoherent five-target enum (the bug this doc opened on), routes writes to the `operation/` commons only, names operator-visibility as a requirement (closing Hole A — session-independent narrative), and preserves the integrity wake.

**Shipped + validated.** Implementation in `services/mcp_composition.py` + `mcp_server/server.py`; feature docs at `docs/features/mcp/` updated to the verb surface. New probe `api/probe_mcp_memory_surface.py` (supersedes the §7 probe) — **8/8 against the live workspace**: `remember`→`operation/` round-trips (the write that used to `governance_lock`), attributed `yarnnn:mcp`, integrity wake `queue 0→1`, `recall`/`trace` compose in one call, operator-visibility session-independent. No substrate residue.

**Separate finding surfaced en route** (not ADR-368's concern, filed for follow-up): the `get_or_create_chat_session` RPC body still references the dropped `chat_sessions.project_id`/`deliverable_id` columns and **errors on every call** — so `notifications.py`'s chat-insert and `feed.py`'s session creation degrade silently via their try/except. ADR-368's visibility fix deliberately uses plain table ops, not this RPC, so it doesn't inherit the breakage. The RPC drift wants its own small fix.

> **Note on §1–§7 framing:** sections above retain the pre-resolution "FINDING / criterion / Option A·B·C" shape from when this doc was scoped under `docs/evaluations/`. They are the discourse trail ADR-368 was derived from; §A–D (top) + this §8 are the resolved analysis. The §7 probe receipts reference the original `probe_mcp_remember_this_default.py` (now superseded by `probe_mcp_memory_surface.py`); both prove the same load-bearing seam.
