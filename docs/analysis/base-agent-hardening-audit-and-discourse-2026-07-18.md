# Base-agent hardening — the audit, and the discourse it forces

> **Status**: Audit (fact-found, receipts inline) + discourse (open questions surfaced, not decided). NOT an ADR. Feeds the operator's directive: *"our efforts should be in more hardening each agent type and config moreso than the models themselves."*
> **Date**: 2026-07-18
> **Scope**: the THREE base agents (Acquire/Reason/Produce → Researcher/Thinker/Designer) + the Critic posture. NOT judgment agents (Rung-2, ADR-382), NOT Freddie (management, kernel constants). This is the member-hands base tier only.
> **Method**: three parallel read-only audits, one per hardening plane (capability/skill/posture), each producing file:line receipts. The canon ceiling (ADR-463 D4.a + ADR-464 §4) was read first so the discourse stays in bounds.

---

## 0. The one-paragraph finding

Hardening was framed as "deepen each agent across three planes — capability (tools), skill (instructions), posture (character)." The audit says that frame is **wrong in two of the three planes, and the third contains a live ship-broken bug**. **Skills do not attach to base agents at all** — they are a member-only affordance by canon (ADR-464 §4), and zero skill files exist anywhere. **Capability is not shallow — it is BROKEN**: Researcher declares two tools its blurb promised (ADR-463 P2), but a live turn cannot execute either, because the tool surface is computed in one place and hardcoded in two others that disagree. **Posture is the one plane fully ours to deepen in code, and it is thin-but-parallel.** And the whole set shares the elephant: **none of it has ever been exercised by a human or an eval** — the capability bug is the proof, because a green gate asserted the tool *payload* and never a tool *call*.

**So "hardening" resolves into a sequence, not a menu**: (1) fix the capability bug — the one agent with depth can't use it; (2) run a live click pass — trust nothing gate-only; (3) *then* the real depth questions (which reads Thinker/Designer need; how thick a posture should be) become answerable from evidence instead of taste. Engine-bias stays last and evidence-gated per ADR-463 D5.

---

## 1. The canon ceiling — what each plane is ALLOWED to become

Read directly from ADR-463 (capability) + ADR-464 (skill) before auditing, so the discourse proposes within canon rather than re-opening settled boundaries.

| Plane | Ceiling (structural) | Who can deepen it |
|---|---|---|
| **Capability (tools)** | A `tools` value may name ONLY a non-consequential primitive — reads + our own primitives, derived from `permission.py::READ_ONLY_PRIMITIVES`. **Never an outward write** (ADR-463 D4.a). | Kernel (a row edit). Members cannot declare reach (`AGENT_MANIFEST_KEYS` has no `tools`). |
| **Skill (instructions)** | Kernel agents have **NO skills folder, deliberately** — the kernel corpus is code (the `DERIVE_RECIPES` pattern; a kernel skill would be a kernel edit). Skills are `agents/{slug}/skills/*.md`, discovered not registered, bounded 8 files / 12K chars (ADR-464 §4). | **Members only.** A base agent's "skill" equivalent IS its posture + capability (code). |
| **Posture (character)** | Kernel postures are code, ours to edit. Members get `tone` (additive), never full posture authoring (ADR-464 §6). | Kernel (a row edit) for base agents; members via `tone`. |
| **Engine (which model)** | Per-agent engine bias is the LAST move, **evidence-gated** on "a real output difference," not vendor symmetry (ADR-463 D5). Sonnet + Designer already share `claude-sonnet-4-6`. | Kernel, after evidence. |

**The load-bearing consequence**: the naive "give each base agent more of all three" is largely canon-blocked. Skills aren't a base lever; engine-bias needs evidence we don't have. The real base-agent surface is **capability + posture**, and one of those is currently broken.

---

## 2. Capability plane — a LIVE BUG, not a gap

### 2.1 What each agent declares

| Agent (slug) | Declared `tools` | Effective set | Receipt |
|---|---|---|---|
| Thinker (`sonnet`) | none | 5 file verbs | `agents_registry.py:91-103` |
| **Researcher (`scout`)** | `("QueryKnowledge", "WebSearch")` | **should be 7** | `agents_registry.py:122` |
| Designer (`designer`) | none | 5 file verbs | `agents_registry.py:162-181` |
| Critic (posture) | none (postures declare none; inherits `based_on: sonnet` → none) | 5 file verbs | `POSTURE_ROW_KEYS`, `:270-272` |

The five verbs baseline: `LANE_TOOL_NAMES = ("ReadFile","WriteFile","EditFile","SearchFiles","ListFiles")` — `lane_runner.py:88`.

The read-only grantable pool (the D4.a ceiling — what an agent *could* reach), from `permission.py:60-90`: entity reads (`LookupEntity`/`ListEntities`/`SearchEntities`), file reads, revision reads (`ListRevisions`/`ReadRevision`/`DiffRevisions`), `QueryKnowledge`, `GetSystemState`, `DiscoverAgents`, `list_integrations`, `WebSearch`, `ReturnVerdict`. Anything outside is consequential and fail-closed. The ceiling is a *derivation* from the gate's own set (`resolve_agent_tools` filters against `READ_ONLY_PRIMITIVES`, `agents_registry.py:333`), gate-proven to bite (`test_agent_registry.py:300-313`).

### 2.2 The bug — three places compute the tool surface, and they disagree

Researcher's tools are **wired to the model** but **not to the executor**, and its own **system prompt denies they exist**. Three defects, one root:

1. **The declared payload is correct.** `run_lane_turn[_stream]`: `_extra = resolve_agent_tools(agent, …)` → `tools = lane_tools_openai(_extra)` → passed to `route_completion(tools=tools)`. A Scout turn's payload carries 7 tools, both extras included. Gate-asserted (`test_agent_registry.py:322-326`). Handlers are real, not stubs: `QueryKnowledge` (`workspace.py:1340`, dispatched `registry.py:615`), `WebSearch` (`web_search.py:403`, dispatched `registry.py:543`).

2. **The execution guard rejects them.** In the tool loop, `lane_runner.py:555` (non-stream) and `:751` (stream): `if name not in LANE_TOOL_NAMES:` → returns `{"error": "tool_not_on_lane_surface"}`. `LANE_TOOL_NAMES` is the bare 5-verb tuple; the `_extra` names are absent. **So if the model actually calls `QueryKnowledge`, the guard refuses to dispatch it to the real, registered handler.** `_extra` is in scope at both call sites (`:471-473`, `:664`) — the guard simply checks the wrong set.

3. **The base system prompt lies.** `_CONVENTIONS_FRAME` (`lane_runner.py:252-255`): *"## Your tools — ReadFile · WriteFile · EditFile · SearchFiles · ListFiles — the complete surface. You cannot … reach external platforms."* For Scout, the frame asserts a 5-tool "complete surface" while the posture appended below (`{posture_section}`) instructs it to *"Search the workspace by meaning (QueryKnowledge) … and the web (WebSearch)."* One prompt, two contradictory tool lists.

**The whole of ADR-463 P2 ("Scout stops lying") is itself a lie in the live turn.** The gate never caught it because it asserts the *payload composition* (7 tools declared), never a *dispatched call* (does QueryKnowledge run?). This is the elephant made exact: **gate-green, never clicked.**

### 2.3 Not exercised in anger

No test or eval drives a Scout turn that calls either extra. `test_adr411_lanes.py` mocks the tool loop but only for `WriteFile`/`Schedule`/`ReadFile`, never `agent="scout"`. The eval harness (`api/eval/`) is inference-fixture-based and references neither scout nor the extras.

---

## 3. Skill plane — not a base lever at all, and never exercised

### 3.1 Base agents are structurally excluded

`lane_runner.py:349-354`: `_skills` is populated only via `find_member_agents(...)` + a `manifest_path`. A kernel slug is not in `_mine`, so `_me = None`, the `if` is false, `_skills` stays `[]`, and `find_agent_skills` is **never called** for a base agent. This is deliberate and canon (ADR-464 §4: *"kernel agents have no skills folder … a kernel skill would be a kernel edit, and the kernel corpus is code — the `DERIVE_RECIPES` pattern"*).

### 3.2 Zero skill files exist, and the discovery leg is unproven

A full-tree scan found **no `skills/*.md` anywhere** — not in source, not in the two reference-workspaces that have `agents/` dirs (`alpha-author`/`alpha-trader` carry MANDATE/IDENTITY/AUTONOMY/principles/`_*.yaml` but no `skills/`), not in fixtures. The plane lives entirely in `test_agent_registry.py §3d`, which uses **synthetic in-memory dicts** — `find_agent_skills` (the DB read a live turn depends on) has **never been exercised** against real data.

### 3.3 What this means for hardening

Skills are how a **member** teaches *their* colleague ("our house style is X"). They are not a knob for deepening Researcher/Thinker/Designer. A base agent's equivalent of "a taught skill" is **code** — its posture and its capability. So base-agent skill-hardening is a category error; the lever it points at is the posture plane (§4). Separately, the member-skill *discovery leg is unproven* and wants a live test before we tell members the feature works — but that is a member-affordance concern, not base-agent hardening.

---

## 4. Posture plane — the one fully-ours lever, thin but parallel

### 4.1 The four current postures (verbatim)

- **Thinker** (`:98-102`, 3 sentences): *"You are Thinker — the member's thinking partner. Reason carefully and say what you actually think, including when it cuts against what they hoped. Prefer the shortest honest answer over a complete one."*
- **Designer** (`:175-180`, 3 sentences): *"You are Designer — the member's maker. You build the thing itself: decks, documents, the artifact in front of you. Work in their material rather than describing what you would do; when the ask is ambiguous, make the smallest honest version and say what you assumed."*
- **Critic** (`:257-262`, 4 sentences): *"You are Critic — the member's adversary, on their side. Your job is the strongest objection, not a balanced view: find the assumption that would sink this if it were wrong. If the idea survives, say so in one line and name what would still falsify it. Never flatter."*
- **Researcher** (`:123-129`, richest): *"You are Researcher — the member's fast reader. Find what they asked for and report it plainly, with the exact source. Search the workspace by meaning (QueryKnowledge) before reading files, and the web (WebSearch) when the answer is not in the workspace. Volume is your job; do not editorialize, and say 'not here' rather than guessing."*

### 4.2 The assembly stack (where a posture actually lands)

A base-agent turn's system prompt, top to bottom (`_CONVENTIONS_FRAME`, `lane_runner.py:226-260`): base identity line → `## The commons contract` → `{filesystem_model}` → reach/authority paragraph → **`## Your tools` (hardcoded 5 verbs — the §2.2 defect #3)** → `## Format discipline` → `{mandate_section}` → **`{posture_section}`** (the agent overlay: `WHO YOU ARE` + character; member-only name line; optional `tone`; skills). A bound Studio lane appends the studio posture (the JOB) + design-system section + derive section after the character.

So the posture is a ~3-sentence overlay riding a substantial base frame. It is not the whole character — but it is the only part of the character that is *per-agent*, and it is entirely ours to edit in code.

### 4.3 Depth comparison

Thinker + Designer are the **thin parallel pair** (3 sentences, one discipline each). Critic + Researcher are **thicker** (4-5 sentences, two disciplines; Researcher is the only base posture that names its tools and encodes a search *order*, consistent with being the only one with a `tools` field). All four share the opener `"You are {Name} — the member's {role-noun}."`. The divergence is only in the how/discipline tail.

### 4.4 Member modification (bounded)

`tone` is additive — a labeled `HOW {NAME} SOUNDS` section appended under the intact base character, never a swap (`:815-817`). A member based on a posture (Lisa `based_on: critic`) wears Critic's `WHO YOU ARE` + her name + her tone. Members cannot author a full posture — the thin end by design (ADR-464 §6).

---

## 5. The discourse — what "hardening" means, given the ceiling

The audit converts the operator's directive into a sequenced set of decisions. Each is surfaced, not decided.

### D1 — The capability bug is P0, and it is not "hardening" — it is "the shipped feature is broken"
The tool surface is computed in `lane_tools_openai(_extra)` and then contradicted by two hardcoded sites (the executor guard `LANE_TOOL_NAMES`, the prompt's `## Your tools`). The Singular-Implementation fix: **one function computes the lane's tool-name set (baseline + `_extra`), and the guard, the payload, and the prompt all read it.** That kills the three-way disagreement at the root rather than patching two constants to match a third.
- *Open sub-question*: does the `## Your tools` prompt section become dynamic (list the agent's actual tools), or does it get cut (the model is told its tools via the tool payload; the prose is redundant and now wrong)? Leaning cut-or-derive, not hand-sync.

### D2 — After the fix, which READS do Thinker and Designer need?
The read-only pool (§2.1) is the whole legitimate capability surface. The sharp candidate:
- **QueryKnowledge for Thinker.** *"A thinker that cannot recall the workspace is as much a lie as pre-fix Scout was."* Reason over a commons it can't semantically search is reason with its eyes closed. This is the same argument ADR-463 P2 made for Scout, one agent over. **Strong candidate.**
- **QueryKnowledge / revision-reads for Designer?** A maker that can pull prior artifacts + their revision history before composing. Weaker — Designer mostly works in the artifact in front of it (bound lane). Needs the click pass.
- *The discipline*: ADR-463 D4.a says these are all grantable (reads). The question is not "may we" but "does the agent's job need it" — and §5 D3 says answer that from a live turn, not a guess.

### D3 — The elephant governs everything: a live click pass is the precondition
Nothing here has been felt. The capability bug existed *because* a green gate stood in for a human. Before D2 depth claims are trusted, one real turn per base agent, driven and observed:
- Thinker: a reasoning turn — does it want to recall the workspace and find it can't?
- Researcher: a research turn that *calls* QueryKnowledge + WebSearch — does it dispatch (post-D1)?
- Designer: a make turn in a bound lane — does the studio posture + character compose coherently?
- Critic: an adversarial turn — is the posture doing work?
This is Hat-B (evaluation), and its findings feed D2/D4 as evidence rather than taste.

### D4 — Posture depth is a judgment call, deferred behind the click pass
Thinker/Designer are thinner than Critic/Researcher. That *might* be correct (a thinking partner shouldn't be over-scripted) or might be under-baked. **Do not thicken postures blind.** The click pass (D3) shows where a posture fails to steer; thicken *there*, from an observed failure, not for symmetry. (This mirrors ADR-463 D5's evidence rule, applied to the posture plane.)

### D5 — Engine-bias stays last and evidence-gated (unchanged)
ADR-463 D5 already ruled this. Sonnet + Designer share an engine; a per-agent engine split needs a demonstrated output difference. **Not now**, and not part of this hardening pass.

### D6 — Skills: fix the member discovery leg separately; it is not base-agent hardening
The member-skill discovery path (`find_agent_skills` against real rows) is unproven. Worth a live test before the feature is presented as working — but it is a member-affordance item, tracked apart from base-agent depth. Base agents do not get skills (canon).

---

## 6. The sequence that falls out

1. **Fix the capability bug** (D1) — Singular Implementation: one tool-set computation, three readers. The one agent with depth can finally use it. *(Hat A, small, gate + click.)*
2. **Live click pass** (D3) — one observed turn per base agent. *(Hat B; findings recorded.)*
3. **Grant the reads the click pass proves needed** (D2) — QueryKnowledge for Thinker is the lead candidate. *(Hat A, evidence-led.)*
4. **Thicken postures where the click pass showed them failing** (D4) — never for symmetry. *(Hat A, evidence-led.)*
5. **Engine-bias** (D5) — deferred, evidence-gated. Not this pass.
6. **Member-skill discovery test** (D6) — separate track.

The through-line: **the elephant (nothing felt) is not a footnote — it is the reason the capability plane shipped broken, and it is why every depth decision below D1 waits on a real turn.** Hardening is not "add more"; it is "make the depth that exists actually work, then add only what an observed turn asks for."

---

## 7. One-line statement

**Audited across its three planes, base-agent hardening is not a menu of "deepen each" but a sequence forced by the findings: skills do not attach to base agents at all (member-only by canon, zero files exist), the capability plane is not shallow but BROKEN (Researcher declares two tools its blurb promised yet a live turn cannot execute them, because the tool surface is computed once and hardcoded to disagree in two other places, and the gate asserted the payload never a call), and posture is the one plane fully ours in code and merely thin — so hardening means: fix the capability bug (Singular Implementation, one tool-set, three readers), run the live click pass the elephant has always demanded, and only then grant the reads (QueryKnowledge for Thinker leads) and thicken the postures that an observed turn proves need it, with engine-bias staying last and evidence-gated exactly as ADR-463 D5 already ruled.**
