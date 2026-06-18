# FINDING — "head driver vs MCP" is not an architectural distinction; the structurally-right model is flow-participation → derived trust-tier → attested binding (derive, never store)

**Date:** 2026-06-18
**Hat:** B (External Developer of the System) — surfaces a finding; recommends a Hat-A amendment to ADR-335. Does **not** itself amend canon.
**Status:** Open — recommends an ADR-335 amendment before Crawl-B (D4 MCP client) is built.
**Trigger:** Cross-analysis of Vercel's Eve announcement (2026-06-18) → operator interrogation: "what's the difference between a head driver and MCP? is this architecturally right?" → on pushback, the directive: *reason to the first-principles structure that is future-proof and won't force a fundamental rewrite later — not to any particular phrasing.*
**Amends target:** [ADR-335 §7 (D4)](../adr/ADR-335-perception-field.md) — the head/tail split text (lines ~163–166) and §13 (binding storage claim, line ~252).

---

## 0. Criterion declared before adherence reported (Discipline rule 0)

**Canon clause under test:** ADR-335 §7 D4 head/tail split — "*Head platforms keep hand-authored drivers … The MCP client serves the tail.*"

**Operationalization:** A classification is architecturally sound iff it (a) partitions the real cases without appeal to history, (b) survives a read changing role across programs, (c) lives in the data model at the level the distinction is actually a property of, and (d) introduces no second source of truth (Derived Principle 7).

**Finding (per rule 0): the criterion is mis-leveled, and the fix is not to relocate the head/tail category — it is to retire it.** "Head/tail" is not a property of a platform, a transport, or even (a second draft of this finding wrongly proposed) a stored attribute of the read. It is the *output* of a function that is already computable from declarations YARNNN forces every program to author (ADR-332 four flows). Naming the function makes the category, and any new stored field, unnecessary. The load-bearing finding is that derivation.

---

## 1. First principles (the only inputs)

Three invariants, each already canon. The right structure is whatever is *forced* by them:

1. **State lives in files; computation is stateless over them** (Axiom 1) ⇒ Derived Principle 7: no dual-tracking. Anything *declared* lives in substrate once; anything that is *policy* is computed fresh from substrate, never stored as a second authority that can drift.
2. **Judgment is transport-blind; only `attestation` crosses the observation contract upward** (ADR-335 §6 / D3) ⇒ whatever distinguishes reads **cannot** be a transport property — by construction nothing above Layer 2 can see the transport, so the transport cannot carry the distinction.
3. **A program is a set of flow declarations** (ADR-332, DP26) ⇒ the authoritative statement of "what this read is *for*" **already exists** on the program's four flows. It is not on the platform, and it must not be re-invented elsewhere.

---

## 2. The derivation (what the invariants force)

"Head vs tail / Direct API vs MCP" compresses **three** different questions, each a property of a different thing. The compression is the bug. Decompress:

| Question | Property of | Already declared? |
|---|---|---|
| **What is this read *for*?** (feeds ground-truth? a primary action? only context?) | the **program's flows** | **Yes** — `substrate_abi.ground_truth` + primary-action flows already say this (ADR-332) |
| **How much trust must the transport carry?** | **derived** from the above | No — and per DP7 must **not** be stored; it is a pure function |
| **Which wire fetches it?** | the **binding** (url, auth, attestation grade) | Partially — `platform_connections` today |

The structurally-right model is therefore **two declared layers with the middle derived, stored nowhere as policy:**

**Layer A — a read's role is its participation in flows (ADR-332). Not a new attribute. Already authored.**
A watch/read either is or isn't referenced by:
- `substrate_abi.ground_truth` → it feeds **truth**
- a **primary-action** flow → it feeds an **act**
- only **context-in** → it feeds **attention**

**Layer B — required transport trust-tier is a pure function of Layer A. Derived at bind-time. Stored nowhere.**
```
required_tier(read, program) =
    HIGH   if read ∈ (program.ground_truth ∪ program.primary_actions)
    OPEN   otherwise
```
A binding is **permitted** iff `binding.attestation_grade ≥ required_tier(read, program)`. That is the entire gate.

- Direct API and an official-OAuth-2.1 / registry-attested MCP server **both can** satisfy HIGH.
- A community/unverified MCP server, a generic web/RSS read, an operator-pasted CSV satisfy **OPEN only**.

**"Head/tail" dissolves.** It was never a category — it was the output of `required_tier`. Direct-API-vs-MCP never enters the gate; the gate reads an **attestation grade**, not a protocol. "Head driver" and "MCP server" are two transports that each carry a grade.

### Why "scope" and "type" were dead ends (the second-draft correction)

A prior draft proposed adding a *consequence-radius* / *type* / *scope* attribute to each read. **That violates invariant 1.** Severity and scope are not new facts to author — they are already *entailed* by flow-participation:
- **Severity** = *which* flow the read feeds (ground-truth/action = HIGH; context-only = OPEN). Already in the flow graph.
- **Scope** = *how many* flows / *how many* programs reference the read. A **count over the flow graph**, not a stored number.

Adding a `type`/`scope`/`tier` field would create a second source of truth that can disagree with the flow declarations — exactly the dual-tracking DP7 forbids (the `sync_registry`/`_perception_tracker.md` disease ADR-335 §8 already refuses). **The read carries no head/tail/type/scope field. The binding carries an attestation grade. Everything else is a query.**

---

## 3. Future-proofing test (the cases that would otherwise force a rewrite)

The model is "right" only if the changes that break the alternatives leave it untouched:

| Change | Per-platform model (ADR-335 as written) | Per-read `type` field (rejected draft 2) | **Flow-participation → derived tier (this finding)** |
|---|---|---|---|
| A new program declares **GitHub as ground-truth** | breaks — GitHub is "head by history," no rule says why; ambiguous for the new program | breaks or churns — the read's stored `type` must be re-authored, and it's now HIGH for program B but OPEN for program A → one field can't hold both | **works untouched** — `required_tier(github, B)=HIGH`, `required_tier(github, A)=OPEN`, evaluated per (read, program) against the flow graph; the same read is both, simultaneously, correctly |
| An **official MCP server** becomes trustworthy enough for a head read | breaks — "MCP = tail" is baked into the capability surface | n/a (type is on the read, but transport policy still hard-codes Direct=head) | **works untouched** — server carries HIGH attestation grade from registry provenance; `grade ≥ HIGH` passes; protocol never consulted |
| **Alpaca stays Direct API** | preserved by special-casing ("money-truth never via community server") | preserved by authoring its type=HIGH | **preserved by derivation** — Alpaca ∈ alpha-trader.ground_truth ⇒ HIGH; today only the hand-authored driver carries a HIGH grade; zero special-casing |
| A read is **promoted from attention to action** mid-tenure | breaks — no per-read level to flip | churns — re-author the field | **works untouched** — operator adds the read to a primary-action flow; `required_tier` flips automatically; the binding is re-checked against the new tier at next bind/fire |

The per-(read, program) evaluation is the property the other two models cannot express. It is the exact case — *the same platform being constitutive for one program and ambient for another* — that proves the distinction cannot live on the platform **or** on a single stored field on the read. It must be **derived from the (read × program) flow relationship.**

---

## 4. The answer to the operator's question, stated precisely

> **Is the head-driver-vs-MCP distinction architecturally right?**
>
> **No — not as a distinction between platforms or transports, and it should not be built that way.** The structurally-right model is: a read's role is *declared* by its participation in a program's flows (already true, ADR-332); the required transport trust-tier is a *pure derived function* of that role (HIGH for ground-truth/action reads, OPEN otherwise), stored nowhere; a binding is permitted iff its **attestation grade** meets the required tier. "Head driver" and "MCP server" are simply two transports, each carrying a grade. The gate reads the grade, not the protocol. Direct-API-vs-MCP stops being an architectural question and becomes a per-binding attestation number — which is exactly what makes it future-proof: new programs, new trustworthy servers, and reads changing role all resolve by re-evaluating the function, never by re-architecting.

This is strictly stronger than ADR-335 §7 as written, and it *preserves* every guarantee that ADR cared about (Alpaca stays Direct API; money-truth never flows through a community server; the B1/B2/B3 provenance funnel governs the OPEN tier; "MCP failure is a driver swap") — now **derived** rather than asserted.

---

## 5. Substrate receipts (the coupling the amendment must break)

- **Capability-gating is enum-coupled to `platform`.** `api/services/orchestration.py:1363-1364`:
  ```python
  .eq("platform", req["platform"])
  .eq("status", req["status"])
  ```
  `capability_available()` gates on a `platform` enum-string match against `platform_connections`. Under the derived-tier model this becomes: resolve the read's `required_tier` from flow-participation, then admit the binding iff `binding.attestation_grade ≥ required_tier`. The replacement is a **function over substrate**, not a new enum value — and emphatically **not** synthetic `mcp:<x>` platform strings (that would re-couple the gate to the transport, re-breaking invariant 2).
- **`platform_connections` is per-`(user_id, platform)`** (UNIQUE; `platform` TEXT enum). It is the right home for *the binding* (it already stores encrypted auth) but it needs **`attestation_grade`** (from registry provenance / first-party status) and **`watch_id`** (which declared watch this binding serves). It does **not** need — and must not get — a head/tail/type/tier column: the tier is derived. ADR-335 §13 line ~252 ("reuse the table … no new storage") is *almost* right: the table is reused; two columns are added (`attestation_grade`, `watch_id`); **no policy column is added** because policy is derived.
- **No dual-tracking introduced.** The only stored facts are (1) flow declarations (already authored, ADR-332) and (2) the binding + its attestation grade. `required_tier` and the head/tail concept are computed, never persisted — satisfying DP7.

---

## 6. Why this blocks Crawl-B (sequencing)

Crawl-B (the in-kernel MCP client, ADR-335 D4) is demand-pulled and not yet built. Built against the per-platform framing it would (a) overload `platform` with `mcp:<x>` synthetic enums — re-coupling the gate to the transport and **violating transport-blindness** — or (b) add storage the ADR says it won't, as an *implicit* decision. The derived-tier model makes the binding's data shape an explicit, minimal, future-proof decision (`+attestation_grade`, `+watch_id`, derive the rest) **before** the client hardens the wrong shape.

**The first real increment is unchanged in spirit:** bind one real OAuth-2.1 server end-to-end, land one distilled observation with `source_ref` + `attestation`. **GitHub-via-MCP** is the ideal first target precisely because it is the case that *proves the model*: GitHub is "head by history" today, and under the derived model its tier is whatever its flow-participation says — forcing the classification to be computed, not defaulted.

---

## 7. The ADR-076 ghost — DISCHARGED 2026-06-18 (receipt below)

ADR-335 D4's premise that "the specific things ADR-076 retreated from no longer exist" (line 153) reasoned from **protocol** maturity (registry, OAuth 2.1, `.well-known`), not from a **real server** bound end-to-end. ADR-076's killer was *server-level* (Notion demanded `ntn_` tokens, rejected OAuth passthrough), not *spec-level*. **This is now resolved by receipt, not reasoning.**

**Crawl-B increment 1 — RECEIPT (2026-06-18).** A real GitHub remote MCP server (`https://api.githubcopilot.com/mcp/`) was bound end-to-end through YARNNN's own in-kernel client (`api/integrations/core/mcp_client.py`, the Hat-A module this finding's amendment specifies), driven by `api/scripts/mcp_crawlb_increment1.py` (Hat-B, side-effect-free):
- **RFC 9728 discovery** returned `authorization_servers: ['https://github.com/login/oauth']` — the *same* OAuth authorize endpoint the existing GitHub head driver uses (`api/integrations/core/oauth.py:91`). The amendment's central claim (same OAuth powers head driver and MCP binding) is verified.
- **Authenticated `initialize` + `tools/list`** with a standard GitHub OAuth token over `Authorization: Bearer` → **HTTP 200, 44 tools, no token-format rejection.** February's failure mode did NOT reproduce. The ghost is dead.
- **`call_tool('get_me')`** → `is_error: False`, real data (`Kvkthecreator`, 19 public repos).
- **ADR-335 D3 observation contract round-trips**: `source_ref: mcp:https://api.githubcopilot.com/mcp/#get_me`, `attestation: platform` (GitHub is platform-published ⇒ gold ⇒ satisfies the HIGH tier in the derived-tier model), `observed_at`, `distilled_content`. No substrate written (receipt is side-effect-free).
- SDK: `mcp 1.28.0`, `streamablehttp_client` + `ClientSession` — the "same SDK family as the FastMCP server" claim (ADR-335 §14) confirmed. Local env required Python 3.11 (system 3.9 too old; `mcp` needs ≥3.10); Render runs ≥3.10 so the path is production-valid.

**Consequence for sequencing:** the empirical gate ADR-335 §12 placed on *Walk* ("N real watches through real servers") should be read as also satisfied for *Crawl-B's first binding* at the auth-shape level. The remaining Crawl-B risk is NOT auth — it is **foreign-call metering** (§8.3 below, now a hard precondition) and the **capability-gate generalization** (§5, the Singular-Implementation absorption of `platform_connection_requirement`).

---

## 7b. Per-platform migration candidacy (the "full collapse" validation, 2026-06-18)

Operator directive: pursue **full collapse** — where a platform's official MCP server passes, *delete the hand-authored head driver* so there is one transport mechanism (the hardest reading of Singular Implementation). A PASS authorizes a deletion, so the probe must be rigorous: **server-exists ≠ YARNNN's-token-accepted** (the exact February distinction). The candidacy test is three gates: (1) official remote MCP server exists, (2) it accepts the OAuth token YARNNN already stores, (3) it covers the head driver's read surface.

**Gate-1 probe (server existence + OAuth-2.1 RFC-9728 discovery) — receipts:**

| Server | HTTP | RFC-9728 `resource_metadata` | Gate 1 |
|---|---|---|---|
| `api.githubcopilot.com/mcp/` | 401→200 w/ token | yes (`auth_servers: github.com/login/oauth`) | ✅ |
| `mcp.notion.com/mcp` | 401 | **yes** (`mcp.notion.com/.well-known/...`) | ✅ |
| `mcp.slack.com/mcp` | 401 | yes (`mcp.slack.com/.well-known/...`) | ✅ |

**Finding (ecosystem maturity): all three OAuth platforms' remote MCP servers now exist and speak OAuth-2.1 discovery — including Notion, the platform whose `ntn_`-token demand killed the February gateway (ADR-076).** The spec-shape ADR-335 D4 bet on is real across the board. This is strong evidence for the *direction*.

**Gate-2 (token acceptance) — BLOCKED, and this blocks the deletions:**

Substrate receipt (`platform_connections`, queried 2026-06-18 via the ACCESS.md pooler):
```
 platform | status |        only live rows
----------+--------+-------------------------------
 trading  | active |  ×3  (Alpaca — API-key, not OAuth)
```
**There are zero Slack / Notion / GitHub connections in the database.** Therefore Gate 2 (does YARNNN's stored OAuth token get accepted by the platform's MCP server?) **cannot be run** — there are no stored tokens to test. The GitHub receipt (§7) used a *developer* `gh` CLI token, which proves the *protocol and client work*, but is NOT the same as YARNNN's app-minted, encrypted, `repo`-scoped operator token being accepted — and critically, Notion/Slack MCP servers run their *own* authorization server (`mcp.notion.com`, not `api.notion.com`), so the platform-API token YARNNN stores may or may not be accepted. **This is exactly the February distinction and it is untested.**

**Per-platform verdict:**

| Platform | Class | Verdict | Rationale |
|---|---|---|---|
| **GitHub** | read-surface + 2 writes | **MIGRATE-ELIGIBLE, deletion UNTESTED** | Server + protocol + client all green (§7). But no operator GitHub connection exists to test app-token acceptance → cannot delete `github_client.py` on a dev-token receipt. |
| **Notion** | read + write surface | **READS MIGRATE-ELIGIBLE, deletion UNTESTED** | Server now OAuth-2.1 (Feb ghost gone). No connection to test; separate MCP auth server → token acceptance unknown. Write paths (`create_comment`) out of perception scope. |
| **Slack** | read + write surface | **READS MIGRATE-ELIGIBLE, deletion UNTESTED** | Same as Notion. `post_message` write out of scope. |
| **Alpaca (trading)** | **action + ground-truth surface** | **STAYS HEAD — do not migrate** | `submit_order`/`close_position` = capital movement (primary action, never a perception read); `get_account`/`get_positions` = money-truth ground-truth (HIGH-tier, `platform`-grade existential). API-key auth, no OAuth-MCP path. Three independent reasons it stays first-party. The derived-tier model *working*, not failing. |
| **Lemon Squeezy (commerce)** | **action + ground-truth surface** | **STAYS HEAD — do not migrate** | `issue_refund`/`create_checkout` = commerce actions; revenue reads = ground-truth. Same class as Alpaca. |

**Net:** "Full collapse for all platforms" resolves, on real evidence, to: **2 platforms (Alpaca, Lemon Squeezy) provably STAY HEAD** (action/ground-truth surfaces — the derived-tier model forbids their collapse, which is correct); **3 platforms (GitHub, Notion, Slack) are migration-*eligible* for their read paths but their head-driver DELETION is UNTESTABLE right now** because no operator connection exists to verify app-token acceptance. **No head driver is deleted this session.** A deletion authorized by an untested probe is the false-positive the discipline exists to prevent.

**What unblocks the deletions:** one real operator OAuth connection per platform (or a Hat-B operator-proxy connection) → run Gate-2 token acceptance + Gate-3 surface coverage against the real encrypted token → green Gate-2/3 authorizes that platform's `*_client.py` deletion in a focused migration commit. Until then, GitHub/Notion/Slack head drivers **remain**, and the MCP client serves *new* tail bindings only — which is the singular model honoring itself (one gate, transport chosen by tested grade-availability per platform), not a parallel implementation.

---

## 8. Recommended next commits (Hat-A, separate from this finding)

1. **ADR-335 §7 + §13 amendment** — retire the head/tail *category*; replace with flow-participation → `required_tier` (pure derived) → attestation-graded binding. §13 binding model: `+attestation_grade`, `+watch_id` on `platform_connections`; no tier/type column; tier derived. Cross-link this finding (Discipline rule 5).
2. **Crawl-B increment 1** — in-kernel MCP client (API + Scheduler, ADR-335 §13); bind GitHub-via-MCP (the model-proving ambiguous case); one authenticated read → one distilled observation carrying `source_ref` + `attestation`; the new gate reads `attestation_grade ≥ required_tier`. The receipt for §7.
3. **Foreign-call metering** — re-classified from "Crawl-B follow-up" to **Crawl-B precondition** (an unmetered mechanical executor calling arbitrary foreign servers scales the cost/abuse surface with the openness D4 sells). Land the meter with increment 1.

---

## 9. Open Question A resolved (2026-06-18) — connection vs watch fork closed

The amendment's deferred Open Question A (*should "connect a platform" become a special case of "declare a watch"?*) was reasoned to closure this session. **Verdict: NO — structurally, not pragmatically.** Receipt-grade reasoning (ADR-343 read directly):

- A **watch is a declaration** in the *aperture* (ADR-343 §31, verbatim: *"the perception field's watch portfolio per ADR-335 **is** an aperture — the selection surface of what the operation perceives"*). Judgment-layer; carries intent + cadence + `distills_to`.
- A **connection is a transport**, below the *"declaration sovereign over transport"* boundary (ADR-343 §47); transport-blind to judgment (ADR-335 §6). Carries only `url` + `auth` + `attestation_grade`.
- They sit on **opposite sides of the one boundary the kernel enforces three ways** (ADR-335 §6 transport-blindness, ADR-307 gate, ADR-320 topology). A watch *consumes* a connection (D5: *declare a watch → resolve a transport*; the connection is step 2's output); it is not *made of* one. "Connection = special case of watch" **inverts the dependency** and would collapse the boundary that licenses transport-blind judgment.
- They unify only **compositionally**: shared derived-tier gate (§5) + shared aperture roof (watches *are* apertures, connections *feed* them). `aperture selects → transport serves → gate licenses`. Two layers of one stack.

Full resolution text: [ADR-335 amendment §E.A](../adr/ADR-335-AMENDMENT-derived-trust-tier.md). The two binding shapes (§7b Q4) are confirmed **permanent and correct**, not transitional. Surviving adjacent (separate) thread: whether *orphan* capability bindings should be deprecated (connections only in service of a declared watch) — a watch-first tightening, distinct from this fork, left open.

---

## Cross-links

- [ADR-335 Perception Field](../adr/ADR-335-perception-field.md) — §6 transport-blind judgment, §7 D4 (amend target), §8 D5 watch-first, §12 staging, §13 implementation (binding storage, amend target).
- [ADR-332 Four-Flow Completeness](../adr/ADR-332-four-flow-completeness-model.md) — the flow declarations `required_tier` is a function of. **Load-bearing dependency of this finding.**
- [ADR-330 Ground-Truth Intake](../adr/ADR-330-ground-truth-intake.md) — the attestation enum (`platform`/`operator`/`agent`) the binding's `attestation_grade` and the observation contract reuse.
- [ADR-076 Eliminate MCP Gateway](../adr/ADR-076-eliminate-mcp-gateway.md) — prior retreat; the unverified-premise receipt (§7).
- FOUNDATIONS Axiom 1 + Derived Principle 7 (no dual-tracking) — why tier/type/scope are derived, never stored.
- `api/services/orchestration.py:1363-1364` — the `platform`-enum coupling the amendment replaces with a derived-tier gate.
