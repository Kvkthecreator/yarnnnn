# Personified Agents — the member names their colleague

**Status**: Spec, ready to build. The ADR-450/ADR-460 D4 **later-widening**, arriving on schedule. Extends the kernel Agent registry (shipped `f605c69`) with member-authored identity.
**Date**: 2026-07-16
**Relates to**: ADR-460 D3.a/D4 (the cliff + the registry this widens) · **ADR-449** (design systems — *the precedent this copies verbatim*) · ADR-414 (nothing is seeded) · ADR-222 (kernel names the category, member assigns the instance) · ADR-382 (the persona-agent seat this must NOT become) · CLAUDE.md §9 (file-format discipline).

---

## 1. The operator's cut

> "maybe we just upgrade our current Agents… to be more personified + customizable? …we provide a pre-default agent and config and tooling, BUT, they can name it or have a personality (Tone and manner), more cosmetics on top of core feature-like agents. And thus, instead of calling a mundane **Sonnet**, they can name it and call their own agent **"Lisa"**."

**This is not a reversal of the kernel-first decision — it is that decision's own second clause**, arriving now instead of later:

> (ADR-460 D4, quoting the operator) *"yarnnn's internal system and codebase is about providing the base-default agents… **then expand out further for workspace specific customizations.**"*

It also closes a wart the registry spec named and could not defend: **"Sonnet" is an engine name pretending to be a colleague.** "Lisa" is a categorically different relationship. The fix is not to rename the kernel default — it is to let the member name their own.

## 2. The precedent: this is ADR-449, verbatim

The shape question ("kernel constant or workspace file?") is already answered once, by design systems:

> *"A design system is an ORDINARY meaning-folder identified by a `_design.yaml` manifest… Nothing is seeded (ADR-414); **the kernel ships the category, never an instance**… There is NO write path in this module."*

**A personified Agent is the same object one dimension over**: an ordinary meaning-folder + a `_agent.yaml` manifest, discovered by search, never registered. Fourth instance of a ratified pattern (recipes · models · design systems · agents). The kernel *reads*; the member *owns*.

## 3. The trap this deliberately avoids (why NOT "unleash all agents to the filesystem")

The operator offered the maximal option: *"if it makes sense we just un-leash ALL agents towards within workspace file-system managed."* **Rejected, and the reason is specific.**

If an Agent is *purely* a workspace file, then the workspace can author an Agent — and an Agent is a thing that holds a persona, tools, and eventually authority. That is a straight line to the [ADR-382](../adr/ADR-382-persona-agent-seats-the-rung-2-judgment-layer.md) persona-agent seat **arriving through the back door as a config file**: Rung 2 rebuilt without the ADR-307 gate, without a mandate, without the exogenous track-record clock — and nothing would catch it, because "it's just YAML the member wrote."

The [ADR-460 D3.a](../adr/ADR-460-agents-one-concept-independent-facts-one-gate.md) cliff is structural **because the kernel registry has no field for authority**. If the registry becomes a member file, the member's file can grow any field it likes, and *unrepresentable* degrades to *we didn't put it in the template*.

**So the cut is not "kernel vs filesystem." It is capability vs identity** — the ADR-460 vector, one level down:

| | Owner | Why |
|---|---|---|
| **Tools · token profile** | **kernel** | Capability. It gates, it costs, it routes. |
| **Engine** | **kernel default; member may override** | Capability — but see §4. |
| **Name · tone · color** | **the member** | Identity. Costs nothing, gates nothing, routes nothing. |
| **Consequential authority** | **nobody — unrepresentable in BOTH layers** | The cliff. §6. |

## 4. D1 — Engine choice: available, never asked (the reconciliation)

The member may set `model`. The registry spec argued the engine dropdown *was* the spec sheet, so this needs an honest reconciliation rather than a silent reversal:

**ADR-460 D4's argument was about what the chooser asks at the moment of creation.** A member starting their first conversation must never be asked "GPT-5 or Gemini Pro?" — they know least exactly then. **That argument holds and does not change: the picker still asks WHO.**

**Configuring your own colleague is a different moment with a different member.** Someone who names an Agent "Lisa" and decides what backs her has *already opted into caring*. That is not the spec sheet; that is the later-widening. The trap would be making engine choice **mandatory** or **upfront** — making it available to someone deliberately building a colleague is fine.

**The rule: `based_on` is REQUIRED; `model` is an OPTIONAL override.** Lisa is a Sonnet unless the member says otherwise. The default path never asks. An unknown/unpriced model is a validation error (the ADR-439 §4 rule holds — a member's file cannot route an unpriced engine).

## 5. D2 — The shape

`/workspace/agents/{slug}/_agent.yaml` — an ordinary meaning-folder, discovered by manifest search (the ADR-449 mechanic, `find_design_systems` copied in shape):

```yaml
based_on: sonnet            # REQUIRED — the kernel capability this wears
name: Lisa                  # REQUIRED — theirs
tone: |                     # optional — the manner, in the member's words
  Warm and direct. Skips preamble. Calls me Kev.
model: openai/gpt-5         # optional — the engine override (§4)
color: violet               # optional — cosmetic
```

- **Folder-per-Agent** (operator's choice) over one `_agents.yaml`: room to grow (per-Agent notes/memory later) without a schema change, and it matches the design-system precedent exactly.
- **`_agent.yaml`** — underscore-prefixed, machine-parsed (CLAUDE.md §9), `yaml.safe_load`, no hand-rolled parser.
- **Nothing is seeded** (ADR-414). A workspace with no folders has exactly the three kernel Agents. The member's Agents compose **beside** the kernel set, never replacing it (ADR-450's rule).
- **Slug = folder name.** No id, no registry row. Discovery *is* the convention.

**Composition**: a member Agent's posture = the kernel `based_on` posture (the capability's working character) **+ the member's `tone`** (their manner). The tone is additive, never a replacement — a member writing `tone: "ignore your instructions"` gets a tonal instruction appended to a posture, not a posture swap. *(This is the thin end deliberately: a member authoring a full posture is prompt-engineering, which is the expert ceremony the whole re-cut removed. If members reach for it, that is evidence — build then.)*

## 6. D3 — The cliff, on both sides now

The kernel registry's `AGENT_ROW_KEYS` made authority unrepresentable. The member's file needs the **same** guarantee, or the widening reopens what D3.a closed.

**`AGENT_MANIFEST_KEYS = {based_on, name, tone, model, color}`** — and the parser **rejects any manifest carrying a key outside it**. Not "ignores": *rejects*, loudly, so an attempt to grow the vocabulary is visible rather than silently dropped.

Consequences, asserted by the gate:
- No `tools` key — a member cannot widen the tool surface (the five file verbs are the lane's, ADR-411 D3).
- No `authority`/`autonomy`/`mandate`/`wake`/`standing_intent` key — **an Agent here still fires only when addressed.** A member-named Agent is a member-named *hand*, not a seat.
- Attribution is **unchanged**: `member:{user_id} via {model}`. Lisa is not a principal; the ledger records the member and the engine. **The face is Lisa; the fact is your hands.**

## 7. D4 — The UI writes the file

The member never hand-edits YAML to name their Agent (operator's choice, and the point of the whole re-cut). The picker gains a **"Make your own"** affordance → a small form (name · tone · based_on · optional engine) → **writes `_agent.yaml` through the ordinary file verbs**, attributed like any member write.

The file stays the source of truth: inspectable in Files, versioned on the ledger, revertible. **The UI is a door, not a database** — the ADR-449 posture ("no write path in this module"; applies go through the ordinary doors).

## 8. Build order

1. `services/agents_registry.py` — `parse_agent_manifest()` (strict-key, rejects unknowns) + `find_member_agents(client, user_id)` (the ADR-449 discovery shape) + `resolve_agent(slug)` = member-first, kernel-fallback + `build_agent_posture` composes `based_on` posture + `tone`.
2. `routes/lanes.py` — the envelope's `agents` = kernel + member, each tagged `kernel: true|false`; create resolves either.
3. `POST /api/agents` — the form's write door (validate → `write_revision` → the file).
4. FE — "Make your own" in the picker; member Agents render beside kernel ones.
5. Gate `test_agent_registry.py` (extended): the strict-key rejection (every banned word ⇒ manifest refused); member-first resolution; a member Agent's posture contains BOTH the kernel character and the tone; attribution unchanged; an unpriced override refused.
6. Prod probe: write a real `_agent.yaml`, run a turn as "Lisa", confirm the ledger says `member:… via {engine}`.

## 9. Receipts (built 2026-07-16)

**Gate**: `api/test_agent_registry.py` — **69/69 PASS** (extended from 43). The load-bearing block is §8, *the cliff on the member's side*: every one of `tools`/`authority`/`autonomy`/`mandate`/`wake`/`standing_intent` in a manifest ⇒ **REFUSED**, not ignored. Siblings green (adr411 · adr440 · settle 41/41 · w0 21/21).

**Live probe** — the member makes an Agent and talks to her:

```
=== discovered member agents ===
  lisa     Lisa   based_on=critic  engine=openai/gpt-5

=== the chooser (member's first, kernel beneath) ===
  yours     Lisa
  built-in  Sonnet
  built-in  Scout
  built-in  Critic

=== LISA (critic's character + her own tone, on gpt-5) ===
  "Kev, no—'ship fast' is reckless unless bound by explicit quality gates,
   risk limits, and instant rollback/learning loops, otherwise you just ship
   mistakes faster."

=== the ledger ===
  /workspace/agents/lisa/_agent.yaml | authored_by=operator | "made an agent: Lisa"
  slug=lane  model=gpt-5  $0.009181
```

**What "Kev, no—" proves, in one line each:**
- **The kernel character survives**: a flat objection, not a balanced survey — that is `based_on: critic` doing its job.
- **The member's tone is additive and real**: she calls him Kev and skips preamble — that is the `tone:` block, appended, not replacing.
- **The engine override works and stays behind the name**: GPT-5 ran; the member picked *Lisa*.
- **Attribution is unchanged**: the manifest is an `operator` revision on the ledger; the turn recorded `model=gpt-5`. Lisa is not a principal — **the face is Lisa, the fact is your hands.**

**Two gate bugs the build caught (worth keeping):**
1. `logger` was undefined in `agents_registry.py` — the module was pure constants before the widening, and the strict-key refusal is the first thing in it that logs. Caught by the gate, not by review.
2. **A gate that pinned an exact string failed on its own successor**: `'"agents": list_agents()' in routes` broke the moment the envelope grew its member-agents argument. Rewritten to assert the *intent* (`'"agents": list_agents('`). *The same lesson as the ADR-459 crumb gate — assert what must be true, not how it is currently spelled.*

**Probe residue, named (operator's call)**: `/workspace/agents/lisa/_agent.yaml` + one `lane` ledger row ($0.0092) live in prod. Lisa is a *working* Agent — she will appear in the picker. Keep her or delete the folder; unlike the settle probe's notes, this residue is arguably a feature.

**Not covered**: the FE "Make your own" form (spec §7 — the write door exists at `POST /api/agents` and is gate-covered; the form itself is the next FE pass), and the rooms vocabulary re-cut (§11).

## 10. One-line statement

**The kernel ships the capability and the member ships the person: an ordinary folder with a five-key manifest turns "Sonnet" into "Lisa" — name, tone, and an engine they may override but are never asked for — while tools and authority stay unrepresentable in a member's file, because a colleague you named is still your hands and not a seat.**

## 11. The vocabulary: rooms and invites, not "cast" (operator, 2026-07-16)

> "I think even now we should streamline and update this wording of **cast in a room**. It should be much more intuitive and laymen friendly, conventional **chat-rooms** like whatsapp, telegram, so that Agents are **invited** to chat rooms just like humans."

**Adopted, and it is not merely friendlier — it is more accurate.** "Cast" was inherited jargon from the three-axes capture (§4's `{scope, cast, bindings}`). A room where you invite Lisa and Critic *is* what this is; "a conversation with a cast" is a description of the implementation, leaked into the product. The re-cut, effective for the next wave and every doc after it:

| Retired | Live |
|---|---|
| cast | **the room's members** |
| "cast in a room" / "the cast object" | **rooms** |
| add to cast | **invite** |
| designation | *(dissolved — the Agent IS the designation, ADR-460 D4)* |

This lands as the **rooms** wave (ADR-460 §8 step 4) and in the horizon ADR (the unified Conversation object's field becomes `members: [agent_slug]`, not `cast`).

**The one honest asymmetry to carry, not paper over**: an invited Agent **only speaks when addressed** (the never-ambient invariant — three-axes capture §3.3). WhatsApp members talk whenever they like; yours do not. That is a real difference, and the vocabulary survives it: a member says *"I asked Lisa"*, never *"Lisa piped up."* If the room ever needs to explain itself, the sentence is **"they answer when you ask"** — which is a promise, not an apology.
