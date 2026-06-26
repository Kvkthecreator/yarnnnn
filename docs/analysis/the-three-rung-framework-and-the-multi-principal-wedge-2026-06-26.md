# Analysis — The Three-Rung Framework and the Multi-Principal Wedge

**Date**: 2026-06-26
**Hat**: B (external-developer discourse — strategic framing + a code-grounded metaphor test. Recommends Hat-A ADRs; makes no canon change.)
**Status**: Proposed framing for operator (KVK) ratification. No canon edits in this doc. It is the discourse base the follow-on ADRs cite.
**Trigger**: KVK asked to step back from feature/discourse into *framing* — "is the git → GitHub → Copilot metaphor (asserted in [interop-first-pivot-and-agent-gating](interop-first-pivot-and-agent-gating-2026-06-25.md) §3) actually the closest resemblance, against real codebase state?" — on the conviction that closing the metaphor honestly would define the higher-order framework that partitions the launch work.
**Receipts**: all code claims verified against the live repo 2026-06-26 (`authored_substrate.py`, `workspace_paths.py`, `mcp_server/server.py`, migration 158). Cited inline.

---

## 0. Why this doc exists

The interop-first pivot ([memo, 2026-06-25](interop-first-pivot-and-agent-gating-2026-06-25.md)) asserted YARNNN's stack maps onto **git → GitHub → Copilot** and used that mapping to justify interop-first GTM + agent-as-gated-beta. The mapping was *asserted from the strategy side*, never *tested against the code*. KVK's instinct: the metaphor is load-bearing — if it's wrong, the parity/comparison work it implies is aimed at the wrong competitors.

This doc tests the metaphor against code, finds it **2/3 wrong**, and replaces it with a framework — **ledger / membrane / steward** — that (a) survives the code, (b) separates two axes the original conflated, and (c) partitions the launch work by comparison set. It then records the launch-defining decisions that fell out of the discourse, including the one genuine pivot: **the wedge is a multi-principal workspace, and the `user_id → workspace_id` re-key is foundational and pre-launch.**

---

## 1. The metaphor test (code-grounded)

The git → GitHub → Copilot mapping has three rungs. Tested against the code, one is exact and two are wrong — and the *way* they're wrong is consistent and informative.

### Rung 1 — "git" — EXACT. Keep it verbatim.

Not a metaphor; a near-literal port, confirmed in code:

- `workspace_blobs` keyed on `sha256` → content-addressing ([authored_substrate.py:140-157](../../api/services/authored_substrate.py#L140)).
- `workspace_file_versions.parent_version_id` → parent-pointer history (the commit DAG).
- `authored_by` + `message`, **required**, single write path `write_revision()` → attribution ([authored_substrate.py:264](../../api/services/authored_substrate.py#L264)).
- Branching + distributed replication **explicitly excluded** — and [authored-substrate.md §7](../architecture/authored-substrate.md) goes out of its way to say this is *exclusion, not deferral*.

YARNNN is **git minus branches minus clone/push**: content-addressed, parent-pointered, attributed, single-head. The memo's "three of git's five capabilities" is exact. **This rung is the floor and it is real.**

### Rung 2 — "GitHub" — WRONG, and the break is structural.

GitHub's essence is **multi-party collaboration over a shared repo**: many human authors, branches, PRs, merge, forks, a social graph, access control *across people*. The memo maps "GitHub = connections + collaboration + the social/interop layer."

The code says the substrate is **single-principal, not multi-party**:

- Every substrate row is keyed on **`user_id` → `auth.users(id)`** ([migration 158:51](../../supabase/migrations/158_adr209_authored_substrate.sql#L51)). **There is no `workspace_id` column.** One account = one workspace = one user_id.
- Every query is `.eq("user_id", user_id)` ([authored_substrate.py:173,398,457,517,547](../../api/services/authored_substrate.py#L173)). Isolation is *between* people, never collaboration *among* them.
- The shared-workspace re-key (`user_id → workspace_id`) that would make it multi-party is **deferred in two ADRs** (ADR-310 D5, ADR-371 D4 — the auth-boundary ADR), named foundational-not-yet-needed. *(Now resolved by ADR-373.)*
- `CALLER_WRITE_POLICY` ([workspace_paths.py:241](../../api/services/workspace_paths.py#L241)) is **single-writer-per-path topology** (one authoritative writer per region) — the *opposite* of GitHub's many-writers-one-repo. Closer to Unix `access(2)` than to a collaboration model.
- Branches/forks/merge — the literal machinery of GitHub collaboration — **excluded by design** ([authored-substrate.md §7](../architecture/authored-substrate.md)).

**So the "GitHub" rung does not exist in the code, and its absence is deliberate.** What sits where GitHub should sit is the **interop face** (MCP `remember`/`recall`/`trace`, ADR-368) + **connectors** — but those are **multi-*client*, single-*principal***: the same person reaching the same substrate from different rooms (Claude, ChatGPT), and different feeds flowing in (Slack, Notion). That is not GitHub (multi-*principal*). It is closer to **Dropbox/iCloud-as-personal-substrate with git's history underneath** — which is precisely the commoditization trap the pivot memo itself flags (§7: "a pure files+connections wedge can commoditize, cf. Dropbox").

### Rung 3 — "Copilot" — WRONG, and this is the most important miss.

Copilot is a **stateless assistant that reads the substrate and suggests** — no standing identity, no intent, **accountable for nothing**; autocomplete you accept or reject. The memo maps "agent = Copilot = the intelligence layer that monetizes accumulation."

The code says the agent layer is **categorically not Copilot-shaped**:

- The Reviewer is a **persona-bearing judgment seat with standing intent** — holds the mandate as the same principal across wakes (ADR-319), reasons capital-EV over ground-truth, takes **accountable** action. Copilot holds no intent and stewards nothing.
- The integrity wake — even on a *memory* write — **invokes the seat to place and judge** the contribution ([mcp_composition.py:594](../../api/services/mcp_composition.py#L594), ADR-368 D5). Copilot never *judges* your commit; it has no opinion about whether your code should exist.
- The seat is the thing the moat is *named after the absence of in competitors*: the 2026-06-10 GTM ratification (project memory) — "nobody occupies **accountable judgment over portable authored substrate**." That is the explicit anti-Copilot. Copilot is commoditized; *accountable judgment* is the claimed moat.

Calling the agent "Copilot" **undersells it into the exact commodity category the strategy must escape.** Copilot is a feature bolted on. The Reviewer is a **fiduciary that runs in your absence**. Different *kinds* of thing.

### The pattern in the two errors

Both wrong rungs are wrong in the *same direction*: YARNNN **collapsed GitHub's "multi-party collaboration" into "single-party multi-room," and elevated Copilot's "stateless suggestion" into "accountable standing judgment."** Both moves are *away* from the developer-tooling metaphor. Name what they moved *toward* and you have the framework.

---

## 2. The framework — ledger / membrane / steward (two axes)

The original metaphor conflated two axes that must be held apart. Closing it cleanly requires both.

### Axis 1 — capability/tech (what each layer IS)

| Rung | git→GitHub→Copilot said | What the code actually is | Honest name |
|---|---|---|---|
| **Floor** | git | git-minus-branches: content-addressed, parent-pointered, attributed, single-head | **The ledger** — an attributed multi-principal context ledger |
| **Middle** | GitHub (multi-party collab) | one substrate, served to every LLM/tool/principal bound to it | **The membrane** — a workspace's substrate, reachable by every principal, across rooms |
| **Top** | Copilot (stateless assist) | persona-bearing seat with standing intent that places, judges, acts in absence | **The steward** — accountable fiduciary, not autocomplete |

The metaphor that actually fits all three rungs is not a dev-tooling stack — it is closer to **a bank**: a versioned, attributed *ledger* (every entry signed, history immutable — git's real insight); a *membrane* that lets you transact as the same accountholder from any branch/app/ATM (not a shared account — *your* account everywhere); and a *fiduciary* with standing authority who acts on your mandate while you are not watching and is *accountable* for it. git→GitHub→Copilot has **no fiduciary** — which is why its third rung never fit.

### Axis 2 — presentation/IA (how each layer SURFACES, and in what priority)

This is the axis KVK has "continuously struggled with — what to surface, in what priority." The struggle came from trying to surface all three rungs as **co-equal tabs**. The metaphor's *presentation* lesson says they are explicitly not co-equal:

| Presents as | Rung | Surface | Priority |
|---|---|---|---|
| **Infrastructure (on-demand)** — you don't open a "git tab"; it surfaces when you ask (log/blame/diff) | ledger | Files + revision/trace | **Floor** — the escape hatch + the proof, reached on demand (ADR-340 "mirror" class) |
| **The home / the face** — the repo page IS GitHub's product face; you land there | membrane | the boundary composition (Context In·Out·Flow, ADR-370-context) + the substrate face | **First — the landing.** "What is my context, what's flowing through it." Must read as a complete product with zero agent dependency. |
| **A posture the home enters** — Copilot appears *where you work*, never as a destination | steward | the decision queue / standing band *inside* Home (ADR-367); the program cockpit tab that *appears on activation* (ADR-369); the dockable command rail (ADR-316) | **"Added" = it lights up surfaces you already have.** NOT a fourth destination. |

**The trap this dissolves:** "the agent is bolted on top" must NOT mean "a separate Agent tab you visit" — that re-creates the fourth-co-equal-destination problem. The metaphor's deeper lesson: **Copilot is not a tab; it is a state the editor enters.** Applied to YARNNN — and this is what ADR-312/367/369 already built but had not *named* — **Home has no "agent section"; Home is the substrate composition that, when a program activates, the steward acts *through*.** The decision queue is the files/feed surface *gaining a verb* (ADR-367 "operating cockpit, not glance-only"), not a separate surface. ADR-369's split (kernel front page + additive program cockpit tab on activation) **is** the "agent bolts on" move done correctly. The shape is already built; the framework just says *this is correct — stop second-guessing it.*

**The one-word correction to the IA instinct:** not "feed/context/files **then** the agent **added on top**" but **"the substrate composition IS the product; the agent is the same composition gaining the ability to act."** Same priority KVK already stated — but it kills the fourth-tab trap.

---

## 3. The launch-defining decisions (settled in discourse 2026-06-26)

The framework forced a chain of connected calls. Recorded here as one coherent picture so the follow-on ADRs inherit them rather than re-deriving.

### D1 — No native chat in the base product. Chat is the steward's interface.

Decided: the base product (ledger + membrane) has **no chatbox of its own.** YARNNN is *the substrate your existing LLMs share*, not another chat window competing with ChatGPT/Claude (pivot memo §5 decision 1, arrived-at independently from the IA side).

**The sunk-cost reconciliation** (KVK flagged heavy prior commitment to internalized-Reviewer + chat-first UX): chat-first was the right UI/UX **for the steward**, not the base product. Chat is the *steward's interface* (the addressed-wake path is the Reviewer's; ADR-316 already made chat a dockable command rail, not a route). So "no native chat in base" **relocates** the chat-first work to the rung it belongs to — it is not thrown away. Shape:

- **Base product (steward off):** boundary composition is the home; the **command rail is present-but-inert** with an activation CTA (the ADR-369 "program tab appears on activation" pattern applied to the rail). No YARNNN chatbox competing with the LLMs it feeds.
- **Agent beta (steward on):** the **rail lights up** — now there is a Reviewer to address, and chat-first UX is exactly right *because there is now an agent on the other end.*

Open sub-decision (polish, not architecture): inert-rail-with-CTA vs no-rail-at-all. Lean: **present-but-inert with CTA** — makes the steward a visible upgrade path, not a hidden feature.

### D2 — The wedge is a MULTI-PRINCIPAL WORKSPACE (not personal memory).

This is the one genuine pivot, and KVK's reframe sharpened it past where the discourse started.

The market reasoning: the cross-LLM-context pain, **for an individual**, is the pain the frontier labs are most incentivized to kill *from inside their walls* (ChatGPT memory, Claude Projects). Wedging there means fighting free, fast, "good-enough" incumbents for a low-switching-frequency user. The pain **for multiple principals** is *structurally unowned*: a workspace's shared context **cannot live in any one lab's memory** — by definition each lab's memory is walled to that lab and that user. Being the *neutral, attributed commons across rival LLMs and arbitrary platforms* is **structurally incompatible with being any one of those principals.** Nobody occupies it because nobody *can*.

**KVK's correction to the framing** (the load-bearing one): the binding unit is not "personal vs team" (humans, and how many). It is the **multi-principal workspace**, where a *principal* is **any authenticated caller that reaches the substrate** — a human, that human's own agents, *other* humans, *their* agents, third-party platforms, foreign LLMs (claude.ai, ChatGPT), open-source/local models via A2A. "Personal" is the degenerate case (N=1). "Team" is N humans. "Pure platform integration" is 0 humans + K platform principals. **One model; the principal count is data.** You do not build personal-then-migrate — you build the multi-principal workspace and personal is the small case.

**Why this is the stronger moat statement** (and why it makes the differentiator load-bearing): the substrate's value scales with the **diversity of principals that attribute into it**, not the number of humans. An attributed substrate where every entry is signed `human:alice` / `agent:alice-researcher` / `mcp:bob-via-chatgpt` / `platform:slack` / `a2a:local-llama` is a record nothing else can produce. `trace` goes from "who decided this" (thin for a solo user — mostly *me*) to **"which principal — human, agent, platform, or foreign model — contributed each version, and how the seat reconciled them"** (load-bearing across principals). The steward rung clicks into place too: in a single-principal world the Reviewer judges *my* contributions against *my* ground-truth (thin); in a multi-principal workspace the Reviewer is **the accountable arbiter across principals** — it places and judges what *any* principal wrote to the commons, and none of them individually owns the truth. **That is the moat at full strength, and it only exists once the workspace is multi-principal.**

The moat sentence: **a single attributed substrate, written to by many principals (human, agent, platform, foreign LLM), under one accountable judgment seat — served to every room each principal works in.**

### D3 — The `user_id → workspace_id` re-key is foundational and PRE-LAUNCH.

Falls directly out of D2. **The imagined-consumer guard flips from "don't" to "do":** the non-human principals already exist (the `mcp` caller ships today; agents ship today; A2A's `a2a:` prefix is spec'd in ADR-371 D3). You are not building ahead of demand — you are **generalizing a model the code already half-implements.** The attribution taxonomy is *already principal-agnostic* (`VALID_AUTHOR_PREFIXES` = `operator` / `agent:` / `reviewer:` / `yarnnn:` / `specialist:` / `system:` / `dispatcher:`; `a2a:` spec'd-not-yet-added per ADR-371 D3) — [authored_substrate.py:80-97](../../api/services/authored_substrate.py#L80). The **keying** is the only thing still stuck at `user_id`. And it is the **same re-key all four futures need** — ADR-371 D4 already says verbatim: *"one re-key unlocks both futures … scope it to serve both — not one."* D2 generalizes "both" to "all principals."

Accepted costs, eyes open:
- **ADR-371's "1 account = 1 workspace" assumption gets reworked** — freshest sunk cost (shipped 2026-06-25, `cfd0f53`). Auth resolves a *principal → workspace + role*, which is the shape that ADR wanted for A2A anyway.
- **Slower activation** (multi-principal cold-start; one principal on a multi-principal product is a weaker first-run than one user on a personal product) — traded deliberately for a moat the labs cannot contest.

### D4 — Write-region authorization is PER-PRINCIPAL GRANT (role binding), not a coarse trust-class table.

How `CALLER_WRITE_POLICY` generalizes from today's fixed caller-classes to an open principal set. Decided: **per-principal grant** — each principal gets an explicit binding (`principal_id, workspace_id, role, write-region scopes`), ACL/OAuth-scope-shaped.

**Why it is the *consistent* choice, not merely the flexible one:**

1. **"Grant" is already load-bearing vocabulary — ADR-366.** The most recent governance work split `governance/` into **GRANT** (`_autonomy` + `_budget`, locked-always) vs **contract** (mode-governed). Per-principal write-region grant is *the same concept one level out*: the autonomy grant says *how far a principal's decisions bind*; the write-region grant says *what substrate a principal may author*. Same shape, same mental model. The trust-class table would have introduced a **second parallel authorization vocabulary** — the dual-implementation CLAUDE.md's Singular-Implementation discipline forbids.

2. **It closes an asymmetry the code already has.** Today the system *attributes* at principal granularity (`agent:alpha-research`, `reviewer:ai-sonnet-v8`, `yarnnn:mcp:claude.ai`) but *authorizes* only at the coarse caller-class level ([`CALLER_WRITE_POLICY`](../../api/services/workspace_paths.py#L241) keys: `reviewer` / `mcp` / `agent` / `operator` / `system`). You can attribute finer than you can authorize. Per-principal grant **makes authorization as fine-grained as attribution already is** — after which "who may write here" and "who wrote here" are described at the same granularity. That symmetry is itself a small moat property: every principal is individually authorized *and* individually attributed, which is what lets `trace` say "bob's agent, scoped to specs, wrote this" *with authority*.

The cost (a `principal_grants` binding + a grant-management surface) is real and pre-launch — but it **completes a symmetry, not invents a system.** Today's `CALLER_WRITE_POLICY` is the *class-level* special case the per-principal grant generalizes; the single-writer-per-path topology (ADR-286/320) is the right substrate for it (each path already has one authoritative writer; multi-principal means *different* paths bind *different* principal-writers).

---

## 4. How the framework partitions the launch work (the parity axes)

The payoff KVK predicted: **each rung's honest name dictates a different comparison set.** The git→GitHub→Copilot framing blurred all three into one developer-tooling story and mis-aimed two of three fights.

| Rung | Comparison set (who you benchmark against) | The fight | Verdict |
|---|---|---|---|
| **Ledger** | storage/memory MCPs — Mem0, Notion, Letta, generic MCP filesystems | attribution + parent-pointered history + single enforced write path, served cross-LLM | **Win, provably.** `trace` exposes a structural property *no storage connector has* ([server.py trace docstring](../../api/mcp_server/server.py): "which a plain storage connector cannot show"). The one rung with an uncopyable property → **lead the wedge here.** |
| **Membrane** | in-room LLM memories — ChatGPT memory, Claude Projects, Gemini context | cross-principal, cross-LLM, **neutral** portable substrate | **Win structurally.** A walled-garden memory cannot be neutral across rivals or across principals. The lab's strongest incentive (keep you in-room) is the exact thing it cannot do. |
| **Steward** | autonomous-agent / accountable-action products | accountable judgment over the multi-principal commons | **No incumbent** (2026-06-10 ratification). This is an **evidence problem, not a build problem** — prove judgment improves over tenure (project memory: CONCERN-3 closed, tenure-rule-revision proven). A moat to *demonstrate*, not a gap to close. |

So: **wedge work → vs storage-MCPs (win on `trace`); membrane work → vs in-room memories (win on neutrality+portability); steward work → vs autonomous agents (win on accountability, by evidence).** Three fights, three comparison sets, three kinds of work. That partition is the higher-order framework the metaphor-close was for.

---

## 5. Open seams (ADR-scoped — recorded, not resolved here)

Named so the follow-on ADRs own them rather than pretend they are settled:

1. **The principal/role/grant model specifics** (D4's center). What roles exist (owner / member / own-agent / foreign-llm / platform / a2a)? Is the grant per-principal-per-path-scope, or principal→role→role-defines-scopes? How does a foreign LLM (no pre-provisioned grant) get a default grant — is `mcp` always the lowest-trust `operation/memory/` floor, with richer grants opt-in? **This is the central decision of the re-key ADR.**
2. **The ADR-371 rework.** "1 account = 1 workspace" → "principal → workspace + role." How much of the just-shipped self-contained auth boundary survives? (The auth *mechanism* — self-contained, in-popup — survives; the *identity resolution* gains a workspace+role lookup.)
3. **The steward as arbiter when principals DISAGREE — CLOSED-BY-CONSTRUCTION (verified §7.3).** The single-principal model never had to answer "two principals write conflicting contributions — what does the seat do?" The resolution is the **single-writer-per-path** discipline (ADR-286/320), and it is already enforced in code: (a) *mechanical* conflict cannot occur — different principals write different paths (`remember` writes `operation/memory/{slug}.md` per-principal; [mcp_composition.py:240-270](../../api/services/mcp_composition.py#L240)), so no two principals ever co-write one file, no merge, no CRDT; (b) *semantic* conflict across paths (A's path says X about Acme, B's says not-X) is **not a data-layer problem — it is the steward's job**: it reads both, attributed, and reconciles against ground-truth into its own `reviewer:` revision. The disagreement is **signal the fiduciary is *for*** (a bank reconciles two conflicting slips; it does not crash), not a hole. The one place cross-principal content actually merges is the steward's *placed* file — where the steward is the sole writer (one principal, the seat), and contributor identity survives as `trace`-visible evidence ([mcp_composition.py:594](../../api/services/mcp_composition.py#L594), ADR-368 D5). **This seam shrinks from "unsolved" to "the moat doing its named work."** The merge/co-edit/CRDT layer Notion needs (because it allows same-block co-editing) is **excluded by construction** here — the single biggest thing the framework saves us from building.
4. **Home's substrate-forward empty state** (pivot memo §7 risk 3). ADR-312 designed it; D1/D3 here make it the *default product*, not a degraded ex-cockpit. **Verification, not work** — confirm it reads as intended.
5. **The agent-gating flag** (pivot memo §6). The four chokepoints (`unified_scheduler` drain+walker, `wake.submit_wake_proposal`, the addressed path, `kernel_surfaces.KERNEL_SURFACES` filter) — small, low-risk per the pivot audit. D1 (no native chat) resolves the one entanglement (chat is agent-coupled). This is an implementation ADR downstream of the re-key ADR.

---

## 6. Implementation scope (code-grounded audit, 2026-06-26)

The re-key was audited against the live repo. **Finding: the architecture has the seam pre-cut at every layer the re-key touches.** The blast radius is smaller than a "foundational data-model change" usually implies, because three prior ADRs (209 single-write-path, 288 caller-identity, 320 topology) already isolated the exact insertion points. Scoped below; each claim has a receipt.

### 6.1 The substrate keying (the foundational change) — bounded by a chokepoint, but larger than first claimed

**Scope correction (Phase-1 scoping pass, 2026-06-26):** an earlier draft of this section claimed "~16 `user_id` scoping sites in two files" — that grep was scoped to `authored_substrate.py` + `workspace.py` only and **undercounted**. The true census: **49 files** touch the substrate tables; **118 query sites** against `workspace_files`/`workspace_file_versions`. The re-key is **~3× the original claim** — still bounded, but a multi-day sweep, not a one-file edit. Two facts keep it tractable:

- **The `AuthenticatedClient` chokepoint** ([`supabase.py:44`](../../api/services/supabase.py#L44)). `user_id` is carried by **one dataclass** — `{client, user_id, email, caller_identity}` — passed as `auth` into every route. It already grew one field for ADR-288 (`caller_identity`); `workspace_id` is its natural second growth. **Derive `workspace_id` once at auth construction and thread the same object — do not re-derive at 118 sites.**
- **Dual-path scoping splits the 118.** The **user-JWT path** (operator routes) auto-scopes via RLS (`user_id = auth.uid()`) — most route reads carry *no* explicit `user_id` and change **zero lines** once RLS is re-keyed. The **service-key path** (scheduler, MCP, wake, `write_revision`) bypasses RLS and uses explicit `.eq("user_id", …)` — these are the real sweep. The write path itself is the spine: `write_revision()` + 4 helpers thread `user_id` as a keyword = **5 function signatures**.
- **No pre-existing `workspace_id` concept to collide with** — receipt: `grep -rln workspace_id api/` returns only `.venv` vendor hits. The name is free.
- **`workspace_blobs` is untouched** — content-addressed global (no `user_id`); scoping lives at the revision/file layer, which is what re-keys.
- **Schema is cleanly partitionable** (pivot memo §6 Finding 2, re-confirmed): substrate tables key on `auth.users`, agent tables key on `auth.users`, **no cross-layer FKs**. The re-key adds a `workspaces` table + `workspace_id` FK on substrate tables; `user_id` becomes a *membership* fact (`principal_grants`), not the substrate key.
- **Migration shape**: at launch scale (few rows) this is the *cheapest* time to do it (memo D3). Backfill: every existing `user_id` → a singleton `workspace_id` (owner = that user). The 1:1 world becomes the N=1 case of the N-principal model with zero behavior change — which is the proof the model is a clean generalization, not a rewrite.

### 6.2 The gate / per-principal grant (D4) — one insertion point, already isolated

The per-principal grant lands at **exactly one function** — receipt: [`_caller_class(auth)` at workspace.py:1753](../../api/services/primitives/workspace.py#L1753). Today it collapses a per-principal `caller_identity` down to a coarse class key (`operator|reviewer|mcp|agent|system`) and `_is_path_locked(caller_class, path)` reads `CALLER_WRITE_POLICY[class]`. The grant model is a **targeted substitution at this seam**:

- `_caller_class` already *has* the per-principal identity (`caller_identity`) in hand and throws away granularity to hit the class table. Per-principal grant means: instead of (or before) the class fallback, **consult `principal_grants(principal_id, workspace_id) → scopes`** and lock against the principal's own grant.
- `CALLER_WRITE_POLICY` is **not deleted** — it becomes the **default grant per principal-class** (the floor a principal gets with no explicit grant row). `mcp` → `operation/` only; `operator` → all-but-`system/`; etc. This is why the grant is *additive*: a new principal with no grant row inherits its class default (today's exact behavior); an explicit grant *narrows or widens within the class ceiling*. **Backward-compatible by construction** — the N=1 owner inherits the `operator` default and nothing changes.
- The single-writer-per-path topology (ADR-286/320) is **unchanged** — it is the substrate the grant model sits on. Per-principal grant decides *which principal owns which path-region*; single-writer guarantees *one owner per path*. They compose; neither is rebuilt.

**Net gate scope**: one function gains a `principal_grants` lookup; `CALLER_WRITE_POLICY` is reinterpreted as class-defaults (no code change to the table, only to how it is consulted); one new table + CRUD for grants.

### 6.3 The MCP→wake seam (seam #3 + ADR-371) — the code already wrote the TODO

The single most de-risking finding: **the placement adapter already contains the re-key, named and one-lined.** Receipt — [mcp_composition.py:594, the `submit_foreign_write_wake` docstring](../../api/services/mcp_composition.py#L594):

> *"Shared-workspace seam (Phase 3, deferred): the Reviewer is a WORKSPACE-level seat (one per workspace), not per-user. The wake must fire for the WORKSPACE that owns this substrate, independent of which member's LLM wrote it. Today user_id == workspace owner (1:1), so `wake_scope` below equals auth.user_id and is accidentally correct. When workspaces become shared (user_id → workspace_id re-key), `wake_scope` becomes the resolved workspace_id — a one-line change confined to this function, which is the sole MCP→wake seam."*

This confirms three things at once: (a) the steward is *already designed* as a workspace-level (not per-user) seat — the multi-principal arbiter role is latent, not new; (b) the MCP→wake coupling is *deliberately isolated to one function* (the comment says "sole MCP→wake seam"), so the re-key's blast radius here is one line; (c) the design *anticipated this exact re-key* and proved single-principal is the accidentally-correct N=1 case. **Seam #3's arbiter and the re-key's wake-scoping are the same already-isolated point.**

### 6.4 The auth rework (ADR-371) — mechanism survives, resolution gains a lookup

Receipt — the auth surface is three files (`auth.py`, `server.py`, `oauth_provider.py`). The rework (memo seam 2) is bounded:
- **Survives unchanged**: the self-contained auth *mechanism* (in-popup login, `client_credentials` for A2A, the shared-DB door — ADR-371 D1/D2). What a principal *does to authenticate* is untouched.
- **Gains a step**: `resolve_request_client` today returns a `user_id`; post-re-key it resolves `principal → (workspace_id, role/grant)`. The static-bearer path (`MCP_USER_ID`) and the OAuth path both gain the workspace+role lookup. This is the *identity resolution* change ADR-371 D4 already flagged as the shared dependency.
- **The `a2a:` prefix** (spec'd in ADR-371 D3, not yet in `VALID_AUTHOR_PREFIXES`) is added here — receipt: it is *absent* today (`grep a2a: authored_substrate.py` → no hit in `VALID_AUTHOR_PREFIXES`), confirming it is genuinely build-deferred, not half-shipped.

### 6.5 What is explicitly NOT in scope (the savings, stated so they are not silently re-added)

- **No merge / CRDT / OT / real-time co-edit** — excluded by single-writer-per-path (§7.3, seam #3). The largest avoided build.
- **No branching / fork / PR-review** — excluded by ADR-209 §7, unchanged.
- **No rich role taxonomy at launch** — the simplest-viable grant (owner = class-default `operator`; every other principal = its class floor, `mcp`/`agent`) ships first; granular per-path member grants are *additive post-launch* (new grant rows, no restructure). "Prepped, not scoped" (KVK's framing) is satisfied: the *key* and the *grant table* are foundational; the *grant UX/role richness* is deferred without foreclosure.
- **No presence / activity-of-others / collaboration-feed** — these are membrane-presentation features, not substrate; they wait for demonstrated multi-human demand.

### 6.6 Scope summary

| Layer | Change | Size | Pre-cut by |
|---|---|---|---|
| Substrate keying | `+workspaces` table, `+workspace_id` FK, `user_id`→membership; **118 query sites / 49 files** re-pointed (corrected from "~16/2") — chokepointed at `AuthenticatedClient`; RLS auto-scopes the user-JWT reads | **Foundational; multi-day sweep, not one file** | ADR-209 single write path + `AuthenticatedClient` chokepoint |
| Gate / grant | `_caller_class` consults `principal_grants`; `CALLER_WRITE_POLICY` reinterpreted as class-defaults; `+principal_grants` table + CRUD | **One function + one table** | ADR-288 caller-identity, ADR-320 topology |
| MCP→wake | `wake_scope = user_id` → `resolved workspace_id` | **One line** (the code's own TODO) | ADR-368 D5 isolation |
| Auth | `resolve_request_client` gains workspace+role lookup; `+a2a:` prefix | **Resolution-only; mechanism survives** | ADR-371 D1/D4 |
| Merge/CRDT/branching | **none** — excluded by construction | **Zero** | ADR-286 single-writer, ADR-209 §7 |

**Verdict:** the re-key is foundational (the data-model spine) and **larger than first claimed** — 118 query sites across 49 files, not the "~16 in 2 files" an earlier draft asserted (that grep was scoped to two files; the Phase-1 scoping pass corrected it). But it is **chokepointed, not sprawling**: `user_id` is carried by one dataclass (`AuthenticatedClient`) that already grew a field for ADR-288, so `workspace_id` is derived once and threaded — not re-derived at 118 sites; and the user-JWT read majority is re-keyed at the **RLS** layer (zero route-line changes), leaving the explicit-scope service-key callers as the real sweep. The single largest cost a multi-party substrate usually carries (merge/CRDT) remains excluded by single-writer-per-path. "Prep but don't scope the diff machinery" (KVK) holds: the revision chain *is* the per-principal diff; no diff/merge system is built.

---

## 7. Recommended follow-on (the ADRs this memo feeds)

Sequenced; each cites this memo as discourse base:

1. **The multi-principal workspace + re-key ADR** (the foundational one). Owns D2, D3, D4, and seam 1. The `user_id → workspace_id` re-key; the `principal_grants` model; the per-principal generalization of `CALLER_WRITE_POLICY` (as class-defaults, §6.2); the auth-resolution rework (seam 2). Pre-launch. **Implementation pre-scoped in §6** — the four seams (substrate keying, gate/grant, MCP→wake one-liner, auth resolution) with receipts; seam #3 (steward-as-arbiter) is **closed-by-construction**, so this ADR *records* it rather than discoursing it open. The ADR's genuine open decision is **seam 1 only** (the role/grant taxonomy — and §6.5 already names the simplest-viable shipping shape).
2. **The presentation/IA ADR** (Axis 2). Owns D1 and the "agent is a posture, not a tab" framing. No native chat in base; rail-on-activation; Home-as-membrane-face; the ledger/membrane/steward surface-priority. Cites ADR-312/316/367/369/370-context as the already-built shape this names.
3. **The Phase-1 product-definition ADR** (seam 5) — [ADR-375](../adr/ADR-375-phase-1-substrate-for-humans-and-external-agents.md). **Reframed 2026-06-26** (KVK): an earlier draft of this item read *"the agent-gating implementation ADR"* and a first ADR-375 was written that way — making *gating the internal steward off* the thesis. That conflated the word "agent": the agent in the **wedge** is the **external operator** (a principal that uses YARNNN like a human — §2 D2's "any authenticated caller"), **not** the internal steward. ADR-375 was rewritten to **define Phase 1 positively** — *the substrate operated by humans AND external agents as principals* — with the `AGENT_ENABLED` flag (four chokepoints + `kernel_surfaces` filter, default ON) demoted to a mechanism (§6), not the headline. The internal steward's eventual rename → **Freddie** and the deferred user-authored agent seats are named there as **Phase 2** (their own future ADRs). Downstream of (1) and (2).

This memo makes no canon change. It is the base the three ADRs cite, so the launch-defining calls are ratified once, in discourse, and inherited — not re-litigated three times.

> **Note on metaphor discipline:** git → GitHub → Copilot is retained *only* for Rung 1 (where it is exact). Rungs 2–3 use **ledger / membrane / steward** because the dev-tooling metaphor mis-describes a single-principal-multi-room substrate as multi-party collaboration, and an accountable fiduciary as a stateless assistant. When the multi-principal re-key lands, the "GitHub" rung will be *closer* to true (genuine multi-party) — but it will still differ in the load-bearing way: GitHub's principals are humans collaborating on code; YARNNN's principals are a heterogeneous swarm (humans, agents, platforms, foreign/local LLMs) attributing into one judged commons. The honest name survives the re-key; the borrowed one does not.
