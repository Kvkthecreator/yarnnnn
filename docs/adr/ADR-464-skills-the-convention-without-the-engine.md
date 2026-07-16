# ADR-464 — Skills: the convention, without the engine that killed it

> **Status**: **Accepted + Implemented** (2026-07-16, operator-ratified). Skills only; connections are named and deferred (§6).
> **Date**: 2026-07-16
> **Authors**: KVK (operator) + Claude (collaborator)
> **Dimensional classification** (Axiom 0): **Substrate** (Axiom 1 — an agent's instructions are files the member owns) + **Mechanism** (Axiom 5 — composed into the posture at turn time, derived-never-stored). No Identity change, and deliberately **no Purpose change**: a skill teaches, it never authorizes.

**Amends**:
- [ADR-118](ADR-118-skills-as-capability-layer.md) — **revived, minus its third leg.** ADR-118's thesis was *"structured instructions (SKILL.md) + a local filesystem + a local compute environment"*. It named its own gap: *"yarnnn already has the instructions and the filesystem; **the missing primitive is the compute environment**."* ADR-417 retired the compute environment. **Legs 1 + 2 are re-affirmed here** — they were never the part that failed.
- [ADR-417](ADR-417-retire-the-render-service-generation-is-rented-not-owned.md) — **clarified, not reversed.** It retired the *engine* (`yarnnn-render`) and *asset generation*. Its scope has been misread as retiring the *convention*; §2's "no SKILL.md injection" was true of one dead path and became a claim about the whole system. Generation stays rented; instructions were never generation.
- [ADR-460](ADR-460-agents-one-concept-independent-facts-one-gate.md) **D3.a** — the cliff's location is stated precisely (§3): it is held by what the runtime *stamps* and the gate *derives*, **never by a file format**. D3.a is unweakened; this ADR shows why it was never at risk here.

**Preserves** (load-bearing, untouched): ADR-307 (the one consequential gate), ADR-449 (the meaning-folder — this is its fifth instance), ADR-414 (genesis seeds nothing), ADR-463 D4.a (the tools ceiling), CLAUDE.md §9 (format follows the consumer).

---

## 1. Context — the misreading, and its receipt

The operator's cut: *"concepts like skills and connections now should not be on legacy, but similarly how to treat conventional concepts that are more agent harness, readily available in the market… not only model agnostic (thus following similar discipline we made for the llm routing themselves), but more market-wide conventional known approaches related to SKILLS.md."*

**"Skills machinery is dead" was a misreading, and this repo's own history is the receipt.**

ADR-118 (2026-03) adopted the market convention *deliberately*:

> *"Adopt Claude Code's naming conventions (skills, SKILL.md) directly — **no yarnnn-specific terminology where Claude conventions exist**."*

and diagnosed its own missing piece exactly:

> *"Yarnnn already has the instructions (AGENT.md) and the filesystem (workspace_files). **The missing primitive is the compute environment.**"*

**ADR-417 retired the compute environment.** Leg three. The one ADR-118 said we didn't have. Its §2a even names the successor: *"when generative capability returns, it returns **rented** — a member-attached connector… never an in-house engine."*

**The convention was never disproven. It was orphaned by a decision about hosting** — and `orchestration.py`'s "no SKILL.md injection" comment (true of the deleted `RuntimeDispatch` path) hardened into a belief about the whole system.

## 2. D1 — A skill is prose, and prose has no vendor problem

**This is why the convention can return now, and it is the whole argument.**

ADR-118 needed a render service because it wanted skills to **execute** — matplotlib, PDF, a Docker image with tools in it. That is a *compute* dependency, and compute is what binds you to a vendor and a bill.

**A skill as structured instructions needs a file and a model that can read.** That is every model. There is no `provider/skill` to prefix, no resolver to write, no server to name — the ADR-463 discipline is satisfied *by construction* rather than by machinery.

> **The model-agnostic work was free here. Only compute ever bound us to a vendor, and we already stopped hosting compute.**

## 3. D2 — Where the cliff actually lives (and why a member-authored file is safe)

The registry argued against member-authored agent files:

> *"If an Agent were PURELY a member file… that is a straight line to the ADR-382 persona-agent seat arriving through the back door as a config file: Rung 2 rebuilt without the ADR-307 gate… nothing would catch it because 'it's just YAML the member wrote'."*

**Load-bearing about AUTHORITY. Wrong about FILES.** Four receipts, each verified:

1. **The gate has never heard of an agent manifest.** `_agent.yaml` / `parse_agent_manifest` / `agents_registry` appear **zero times** in `permission.py` + `workspace.py`. `_caller_class` branches on `caller_identity`.
2. **`caller_identity` is stamped by the RUNTIME from runtime facts.** `_lane_auth` computes `lane_caller_identity(auth.user_id, model)`. **No file can reach it.**
3. **Tools resolve from the KERNEL row.** `resolve_agent_tools` reads `based_on`'s kernel entry; a member's file declaring `tools` is refused by the parser *and* ignored by the resolver. Two independent defenses, neither of which is the file format.
4. **`posture` has exactly one consumer** — a prompt string. It never touches the gate, the ledger, or cost.

**Therefore**: a skill that says *"you may post to Slack and run Schedule"* is **a lie the gate refuses** — exactly as it refuses the same words typed into chat. The model can *read* the claim and cannot *act* on it.

> **Prose is not permission.** The cliff is held by what the runtime stamps and the gate derives. It was never held by keeping the character in Python.

Gate-proven (`test_agent_registry.py` §3d): a malicious skill's text reaches the prompt; the tool list stays at the five file verbs.

## 4. D3 — The shape: discovery, not registration

```
agents/{slug}/_agent.yaml     ← identity     (machine-parsed → `_` prefix, §9)
agents/{slug}/skills/*.md     ← instructions (LLM-read prose → `.md`, §9)
```

- **`skills/`, not `_skills/`** — CLAUDE.md §9: *format follows the consumer*. Prose an LLM reads is `.md`.
- **Discovery, never registration** — the ADR-449 mechanic `find_member_agents` already uses, one level down. No table, no registry row, no seeding (ADR-414).
- **The folder comes free**: the manifest discovery already carries `manifest_path`.
- **Kernel agents have no skills folder, deliberately.** The kernel corpus is **code** — the ratified `DERIVE_RECIPES` pattern (prose instructions in a kernel dict, and nobody calls it misfiled). A kernel skill would be a kernel edit. **The member's copy is a folder; the kernel's is code. Both are already-ratified patterns, and they compose beside each other (ADR-450's rule).**

**Composed last: character → name → tone → skills.** A skill is what this colleague was *taught*; it is read in the voice of who they are, never as a second identity.

## 5. D4 — Bounded, because skills ride every turn

8 files / 12K chars, **trimmed by whole skills**.

- **Why a ceiling**: a skill composes into *every* turn this agent takes. An unbounded folder is an unbounded per-turn bill — cost is the reason, not taste.
- **Why whole skills**: **half an instruction is worse than none**, because the model acts on the half it can see. A truncated *"never use the word"* is an instruction with its object cut off.
- **Why not summarize-to-fit**: that is a metered LLM call to save a prompt — paying twice to spend less.

Empty folder → empty section → **zero prompt cost** and a byte-identical turn.

## 6. What this ADR does NOT do

- **It does not build connections.** The operator is right that **auth is already resolved** (`principal_grants` scopes + roles + `narrow`/`evict`, the ADR-434 powerbox, ADR-463 D4.a's derivation-from-the-gate). What is missing is **direction**: we serve MCP *inbound* (ADR-310/368 — ChatGPT and Claude connect in); the conventional way an agent reaches *out* is **MCP client** — the ADR-404 a2a lane. **And the outward half is exactly the ADR-307 cliff** (a connection that reads is an ADR-401 peripheral; one that writes outward is consequential action). Not freelanced.
- **It does not make the kernel agents folders.** §4: the kernel corpus is code, and that is the `DERIVE_RECIPES` pattern, not an accident. The earlier analysis (`the-agent-is-a-folder`) over-reached here; the receipts corrected it.
- **It does not let a member author `posture`.** `tone` stays the thin end. A member authoring a full posture is prompt-engineering — the expert ceremony the re-cut removed. Skills are the *other* half: not "be someone else", but "here is how we do this".
- **It does not revive asset generation or the render service.** Generation stays rented (ADR-417).
- **No schema, no migration, no new env var.**

## 7. Cleanup shipped with it (Singular Implementation)

`has_asset_capabilities()` **deleted** — ADR-417's unfinished deletion. A predicate that could only return `False`, retained *"so those call sites need no change"*. Its three consumers: a dead branch appending prose instructing agents to use the **deleted** `RuntimeDispatch` primitive, and two payload fields **nothing read**. Its gate asserted a tautology; the real invariant is checked at the source (`CAPABILITIES` carries no `category=="asset"`).

**A predicate with one possible value is not an abstraction — it is a fact with a function around it.** Precisely the shape the registry already refuses for `tools` (*"a field that lies about being a choice"*).

## 8. Consequences

- **The market's convention is ours again**, at the layer where it was always free.
- **A member can teach their colleague.** "Lisa, our house style is X" stops being a sentence retyped every session and becomes a file.
- **The cliff is now *stated* rather than *assumed*** — and it is stated where it is true (the runtime + the gate), which makes the next widening arguable from receipts instead of fear.
- **The risk, named**: a member will eventually write a skill that *claims* authority, and the model will read it. That is not a hole — it is text, and the gate refuses it. The mitigation is that this is **structurally identical to a member typing the same sentence into chat**, which has always been true and has always been safe.

## 9. One-line statement

**ADR-118 adopted SKILL.md because the market had converged there and said its own missing piece was the compute environment; ADR-417 retired exactly that compute environment and the convention was buried with it by a comment — so skills return as what they always were at their portable core: prose in a member's folder, composed last into the colleague's voice, bounded because they ride every turn, and safe not because we vetted the words but because prose is not permission — the cliff is held by what the runtime stamps and the gate derives, never by a file format.**
