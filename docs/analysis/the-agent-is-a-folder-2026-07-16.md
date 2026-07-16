# The agent is a folder — converging on the market's conventions

> ## ⚠️ SUPERSEDED IN PART by [ADR-464](../adr/ADR-464-skills-the-convention-without-the-engine.md) (2026-07-16, same day)
>
> **§1 (the ADR-118/417 misreading) and §3 (the wall is about authority, not files) are RATIFIED — they are ADR-464's §1 and §3.**
>
> **§5's "kernel agents ship as folder CONTENT, not as a dict" is WRONG, and the check I flagged as the open question is what refuted it.** I asked *"where do kernel agents live before a member touches them?"* (ADR-414 seeds nothing) and went looking. The answer was already ratified, twice, in two different shapes:
>
> - **`DERIVE_RECIPES` (ADR-450)** — prose instructions in a *kernel dict*, no member folder. Nobody calls it misfiled, because **the kernel corpus is code**.
> - **Design systems (ADR-449)** — a *member folder*, no kernel set at all. Present iff the member made one.
>
> `KERNEL_AGENTS` is already the correct composition of both: kernel corpus in code + member folder via `based_on`, composing beside each other. **The architecture was right; I mistook "not a file" for "not a convention."** The real gap was narrower and is what ADR-464 fixes: the *member's* folder had no room for prose or skills (`tone` — LLM-read prose — sat in a `_.yaml`, and `skills/` didn't exist).
>
> Kept unedited below as the reasoning trail, because the wrong turn is instructive: **the upstream check I nearly skipped is the one that saved the build.**

**Status**: Analysis + direction. **§5 partially superseded — see the banner above.** **The upstream question the operator named**: *"we need to start from even more upstream considerations… concepts like skills and connections should not be on legacy, but similarly how to treat conventional concepts that are more agent harness, readily available in the market… not only model agnostic (thus following similar discipline we made for the llm routing themselves), but more market-wide conventional known approaches."*
**Date**: 2026-07-16
**Relates to**: ADR-118 (skills as capability layer — the convention this codebase adopted first) · ADR-417 (what actually died) · ADR-449 (the meaning-folder) · ADR-460 D3.a (the cliff) · ADR-463 (capability-not-vendor — the discipline this extends) · ADR-373/386/434 (grants + powerbox — the auth the operator says is already resolved, and is)

---

## 1. The correction that reframes everything

I framed skills and connections as **legacy to route around**. That was wrong, and the receipt is in this repo's own history.

**ADR-118 (2026-03) adopted the market convention explicitly:**

> *"Claude Code demonstrated that structured instructions (SKILL.md) + a local filesystem + a local compute environment = indefinitely expandable agent capabilities. Yarnnn already has the instructions (AGENT.md) and the filesystem (workspace_files). **The missing primitive is the compute environment.**"*
>
> *"Adopt Claude Code's naming conventions (skills, SKILL.md) directly — **no yarnnn-specific terminology where Claude conventions exist**."*

That is the operator's discipline, ratified here four months ago.

**Then ADR-417 killed it — but read what it killed.** ADR-417 retired the **compute environment** (`yarnnn-render`) and **asset generation**. Its own §2a names the successor:

> *"When generative capability returns to the product, it returns **rented** — a member-attached connector… never an in-house engine."*

**So "skills machinery is dead" was my error.** The *engine* died. ADR-118's third leg — the thing it said we already had. **The convention was never disproven; it was orphaned by a decision about hosting.** ADR-118's first two legs (structured instructions + a filesystem) are not only alive, they are the moat.

## 2. The upstream thing I was standing on without checking

The operator: *"you're assuming even existing agent config and scope is correct."*

They are not. `AGENT_ROW_KEYS = {slug, name, blurb, icon, model, token_profile, posture, tools}` is **a bespoke schema I invented last week**, with `posture` as a Python string literal inside a kernel dict. Meanwhile:

- **The market convention** for an agent's instructions is a **file** (SKILL.md, AGENTS.md, CLAUDE.md). Anthropic, OpenAI, and the agent-harness ecosystem converged here.
- **This codebase's own deepest pattern** is a file. The registry comment says so out loud: ADR-449's meaning-folder is *"the fourth instance of a ratified pattern (recipes · models · design systems · agents)."*
- **ADR-411 D6 already composes an AGENTS.md-shaped system prompt** at turn time.

**So the kernel agents are the one thing in the system that isn't a file.** I added `tools` as a tuple in a dict and called the field landed — when both the market and our own filesystem say the answer is frontmatter in a folder the member can read.

## 3. The wall — tested, and it is not where the comment says

The registry argues hard against member-authored agent files:

> *"If an Agent were PURELY a member file, the workspace could author an Agent — and an Agent is a thing that holds a persona, tools, and eventually authority. That is a straight line to the ADR-382 persona-agent seat arriving through the back door as a config file: Rung 2 rebuilt without the ADR-307 gate… nothing would catch it because 'it's just YAML the member wrote'."*

**This argument is load-bearing about AUTHORITY and wrong about FILES.** Four receipts:

1. **The gate has never heard of an agent manifest.** `grep` for `_agent.yaml` / `agents_registry` / `parse_agent_manifest` in `permission.py` + `workspace.py` → **zero hits**. `_caller_class` branches on **`caller_identity`**.
2. **`caller_identity` is computed by the RUNTIME, from runtime facts.** `_lane_auth` stamps `lane_caller_identity(auth.user_id, model)`. A member's file cannot reach it. The attribution that decides everything is not in the file's vocabulary and never could be.
3. **Two independent defenses, and neither is the file format.** The parser refuses `tools`/`authority`/`wake`/`mandate` loudly — *and even if it didn't*, `resolve_agent_tools` reads the **kernel** row for the `based_on` capability, so a file declaring tools is ignored on the way past.
4. **`posture` is not gate-relevant at all.** Exactly one consumer (`agents_registry.py:561`, building a prompt string). It never touches the gate, the ledger, or cost. **It is prose only an LLM reads.**

**The conclusion**: the cliff is held by *what the runtime stamps* and *what the gate derives*, **not by posture living in Python**. Keeping the character in a dict buys **zero** safety. It costs the convention.

By the codebase's own law (CLAUDE.md §9 — *format follows the consumer*): prose an LLM reads, never machine-parsed, **is a `.md` file**. `posture` is misfiled *by our own rule*.

## 4. The symmetry — the ADR-463 discipline, applied twice more

We just ruled: **capability is not vendor** — the agent asks, the kernel resolves. Skills and connections are the same shape:

| | Today | The conventional shape | Model-agnostic because |
|---|---|---|---|
| **Engine** | ✅ solved (ADR-463 P0/P1) | `provider/model` + a resolver | LiteLLM translates |
| **Skills** | orphaned with the render service | **SKILL.md** — instructions, not an engine | *prose is portable by construction* — a skill is text any model reads |
| **Connections** | dormant lane | **MCP** — and **we are already an MCP server** | the protocol is the standard |

**Skills are the easy one, and this is the insight worth holding**: a skill has **no vendor problem at all**. ADR-118 needed a render service because it wanted skills to *execute* (matplotlib, PDF). A skill as **structured instructions** needs nothing but a file and a model that can read — which is every model. **The model-agnostic discipline is free here; it was only ever the compute that bound us to a vendor, and we already stopped hosting compute.**

**Connections is the sharp one, and the operator is right that auth is resolved.** `principal_grants` gives per-principal `scopes`, roles (`owner|member|own-agent|foreign-llm|platform|a2a`), `narrow`/`evict`, the ADR-434 powerbox, and ADR-463 D4.a's derivation-from-the-gate. **That is the hard half of connections and it is built.** The direction is the missing piece: we serve MCP *inbound* (ChatGPT/Claude connect in — ADR-310/368); the conventional way an agent reaches *out* is **MCP client**. Same protocol, opposite direction — ADR-404 already names it the deferred a2a lane.

⚠️ **And the outward half is exactly where the ADR-307 cliff sits** (ADR-463 D4.a): a connection that reads is an ADR-401 peripheral; a connection that writes outward is consequential action. **Not to be freelanced.**

## 5. The shape this points to (direction — wants ratification, not a build)

**An agent is a folder.** Not a dict with a folder bolted beside it for the member's half.

```
agents/{slug}/
  AGENT.md          ← the character. Frontmatter (based_on, model?) + prose body.
                      The market convention; our own §9 law; ADR-411 D6's shape.
  skills/*.md       ← SKILL.md-shaped. Instructions, not engines. Composed into
                      the posture on demand. Vendor-free by construction.
  avatar.png        ← already works (2026-07-16)
```

- **Kernel agents ship as folder CONTENT, not as a dict.** Same read path as a member's. The kernel seeds; the member owns. `KERNEL_AGENTS` stops being a schema and becomes a *default corpus* — the ADR-450 rule ("recipes are data… when agent-composed arrives it composes BESIDE kernel recipes") at its fifth instance.
- **The cliff moves nowhere, because it was never in the file**: `tools` stays kernel-resolved through `based_on` (§3 receipt 3); `authority` stays unrepresentable; the parser keeps rejecting; the gate keeps branching on `caller_identity`.
- **Skills return without the render service** — as instructions. ADR-118's legs 1+2 without leg 3, which is what ADR-118 said we already had.
- **Connections wait on direction (MCP client) + the cliff**, with auth already solved.

**What this buys, concretely**: a member can *read* their agent. Today "who is Lisa?" is answerable only by someone with the repo open. That is the same failure as `models[0]` — a fact about the member's colleague, held somewhere the member cannot look.

## 6. What I am NOT claiming

- **Not that the registry was wrong to exist.** It made the chooser ask *who*, which is the whole re-cut. This is about where the character *lives*, not whether the roster is right.
- **Not that this is free.** `KERNEL_AGENTS` is read by the chooser, the hiring card, the posture builder, D4.a, and 140 gate checks. A folder-shaped kernel agent is a real migration with a real seeding question (ADR-414 says genesis seeds nothing — so where do kernel agents *live* before a member touches them? **This is the open question, and it is the one worth ratifying first.**)
- **Not that skills are next.** Scout's tools have never run; Designer has never been felt. **The evidence gap (§6.1 of the debt ledger — nine commits, one clicked) outranks the next abstraction.**

## 7. One-line statement

**Skills and connections are not legacy to route around — they are conventions this codebase adopted first (ADR-118: "no yarnnn-specific terminology where Claude conventions exist") and lost when ADR-417 retired the *compute environment*, not the convention; and the upstream error is that our kernel agents are the one thing in the system that isn't a file, defended by an argument about authority that the receipts refute — the gate has never heard of an agent manifest, `caller_identity` is stamped by the runtime, and `posture` is prose with exactly one consumer, so keeping the character in a Python dict buys zero safety and costs the market's convention, our own §9 format law, and the member's ability to read who their colleague is.**
