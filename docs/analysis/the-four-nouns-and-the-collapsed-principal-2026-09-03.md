# The four nouns and the collapsed principal — where the landscape converges, and what yarnnn is betting

**Date**: 2026-09-03
**Hat**: B (external-developer surface — discourse capture). No code, no canon edits.
Any canon consequence is a later, separate act.
**Origin**: the 2026-09-03 discourse, opened by the operator on the ADR-630/631/632
arc: *"around the concepts of plugins and skills and agents, plugins seem like
roll-ups, scaffolding of skills and connectors in a folder convention, and thus an
upper-level consideration of multiple skills, which seems somewhat analogous to
agents. My thesis is that the AI landscape — Claude and Anthropic as the main
leaders in it — are also somewhat deliberating, and thus not yet hard-fixed on what
is and is not an agent."* Then: *extrapolate how the landscape will prevail, and
what that means for yarnnn.*
**Succeeds**: [what-kind-of-agent-the-taxonomy-that-keeps-dissolving-2026-07-16.md](what-kind-of-agent-the-taxonomy-that-keeps-dissolving-2026-07-16.md)
— that doc established yarnnn's INTERNAL answer (*there is no kind, only
configuration*, reached twice by different routes). This one is the EXTERNAL
comparison: how that answer sits against the ecosystem's, and what converges.
**Composes with**: FOUNDATIONS DP27 (transports are commodity — the prior, see §2),
[grants-and-reach.md](../architecture/grants-and-reach.md) (the reach grant),
[lane-frame.md](../architecture/lane-frame.md), [connectors.md](../architecture/connectors.md).
**Status**: hardened discourse capture. §6 carries a falsifier and a review trigger.

---

## 1. Method, and what is verified vs. inferred

The ecosystem claims below were established two ways, and the difference matters:

- **Direct inspection** of a live plugin install on the developer machine —
  `~/.claude/plugins/cache/claude-plugins-official/chrome-devtools-mcp/1.8.0`.
  This is primary evidence: the artifact itself, not a description of it.
- **Documentation fetches** (code.claude.com/docs, platform.claude.com/docs) via a
  research subagent, for the frontmatter field lists and runtime semantics.

**Explicitly weak**: the ship timeline. It rests on third-party write-ups, not
official changelogs. Only the **ordering** is used in the argument below; the months
are not load-bearing and are not restated here.

---

## 2. The prior this doc must not re-claim

**FOUNDATIONS DP27 (ADR-335, 2026-06-11) already called transport convergence**,
three months before this discourse:

> Transport (deliberately commodity — REST/RSS/CSV/MCP, a swappable driver class
> **consumed from the ecosystem, never built as a catalog**) … judgment is
> **substrate-aware and transport-blind**.

And it received its receipt: *"discharged by receipt 2026-06-18: GitHub's remote MCP
server accepted standard OAuth Bearer through the in-kernel client; the ADR-076 ghost
is dead."*

So "MCP wins, connectors commoditize" is **not a finding of this doc**. It is a
prediction yarnnn already made and already collected on. What is new here is the
*shape of the rest of the stack* — which layers converged, which did not, and the
asymmetry that explains the difference (§4).

---

## 3. What was actually found

### 3.1 The plugin is a namespace, not an actor

The operator's structural claim — that a plugin is a roll-up of skills + connectors
— is **confirmed**. A plugin may contain `skills/`, `agents/`, `commands/`,
`hooks/`, `.mcp.json`, `.lsp.json`, `monitors/`, `bin/`, `settings.json`. It is a
strict superset of what a subagent is.

The analogy to an agent is **falsified**. A plugin has no runtime semantics: no
context window, no model, no identity, no attribution. Its only runtime trace is a
namespace prefix (`/plugin-name:skill-name`) — visible in this session's own skill
listing as `chrome-devtools-mcp:a11y-debugging`. Its components load and function;
the container never runs.

This is the distinction the operator's thesis conflated, and it is one yarnnn has
already paid to learn. ADR-600, verbatim:

> three dicts with identical row shapes and one shared resolution namespace were
> never a type distinction — they were a **VISIBILITY FLAG modelled as three
> containers**, and modelling a property of a being as the identity of its container
> means the agent changes identity when the property changes.

A container answers *what is bundled*. An agent answers *what is addressed*. Treating
the first as the second is the general form of the ADR-600 defect, which cost "two
silently-dead planners, a vacuous pricing ratchet, and a cast door that contradicted
its own roster."

### 3.2 One payload, four manifests — the primary evidence

The single most informative artifact found. That one plugin tree carries:

| Manifest | For |
|---|---|
| `.claude-plugin/plugin.json` | Claude Code |
| `.cursor-plugin/plugin.json` | Cursor |
| `gemini-extension.json` | Gemini |
| `server.json` (MCP schema, `2025-12-11`) | the MCP registry |

The `mcpServers` block is **byte-identical across all three vendor manifests**
(`npx chrome-devtools-mcp@1.8.0`). The diffs are packaging metadata — a logo, an
author, a homepage. Cursor renames the thing entirely ("devtools-for-agents").

**Reach converged on a shared spec; packaging forked into per-vendor wrappers around
identical bytes.** That is the signature of a settled substrate under an unsettled
ontology — and it is the operator's Claim B, evidenced rather than asserted.

### 3.3 What the skills actually carry

The six skills in that plugin declare `name` + `description` **only**. No model, no
tools, no identity.

This matters because Claude Code's skill frontmatter *permits* far more —
`allowed-tools`, `disallowed-tools`, `model`, `effort`, `context: fork`, `agent`,
`permissionMode`, and others. The portable Agent Skills spec permits six fields
(`name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools`);
a seventh is a hard validation error on upload to claude.ai or the API.

So the same filename denotes **two different objects** depending on surface. And the
plugin actually shipped uses the portable subset — the stricter discipline followed
in practice even where the format permits otherwise.

### 3.4 The correction that survived the first draft

An earlier reading of this held that a Claude Code skill "carries reach," in direct
contradiction of ADR-630's *prose is not permission*. **That reading was too strong
and is corrected here**:

- **Subagent** `tools:` + `model:` — **persistent identity**. The subagent *is* that
  allowlist and that engine, every time it is addressed.
- **Skill** `allowed-tools:` + `model:` — **turn-scoped grant**, cleared after the
  turn. Closer to `sudo` than to a role.

The point survives in weakened form, and §5.3 states why it still favours yarnnn's
ruling — but the ecosystem is **not** putting standing authority in prose, and this
doc must not claim it does.

### 3.5 "Agent" denotes four structurally different objects

| Surface | "Agent" is |
|---|---|
| Claude Code | a `.md` file: system prompt + tool allowlist + model + isolated context |
| Claude Agent SDK | an `AgentDefinition` object in Python/TS |
| Managed Agents API | a REST resource with server-side state and a hosted sandbox |
| claude.ai / Desktop | a conversation partner — not a configuration object at all |

Not confusion; four live bets on where the agent boundary sits. But the word does no
disambiguating work, which is why the vendor's own materials ship disambiguation
tables (the bundled `claude-api` skill warns that Tool Runner and Agent SDK "sound
alike but are different packages," and separates four ways to build an agent along
*who supplies the harness* × *who supplies the deployment*).

### 3.6 The ordering, which is the part that argues

Only the order is used: **MCP → CLI → subagents → hooks → skills + plugins →
skills absorbing commands.**

Two things fall out.

**Plugins arrived last**, after subagents, hooks and skills already existed as loose
concepts. That is a packaging layer **retrofitted over an accumulated pile**, not a
container designed first and filled after. A plugin can bundle those five things not
because they are one kind of thing, but because they were the five things that
existed when the wrapper shipped.

**Skills then absorbed commands** — the ecosystem collapsing two nouns that turned
out to be one. That is the same correction ADR-631 made (retiring *being*, retiring
*desk*), reached from canon rather than after shipping both.

---

## 4. The asymmetry that explains all of it

Four layers, four states:

| Layer | State | Evidence |
|---|---|---|
| **Reach** (MCP) | converged, cross-vendor | one `mcpServers` block, byte-identical across 4 manifests |
| **Craft** (skills) | spec exists, implementations diverge | 6 portable fields vs. ~20 in Claude Code; a 7th is an upload error |
| **Identity** (agents) | not converged | 4 surfaces, 4 structurally different objects |
| **Governance** | **no noun at all** | reach is folded into whichever object is nearest |

The ordering is not accidental. **A layer converges when the cost of not converging
is borne by the vendor, and stays fragmented when it is borne by the user.**

- **Reach** had to converge: every vendor needed every connector, and N×M
  integrations is a cost vendors pay directly. (DP27 predicted this — §2.)
- **Craft** is converging because a skill is inert text — cheap to standardize, no
  runtime commitment. The portable spec is six fields precisely because six fields is
  what can be agreed without deciding what an agent *is*.
- **Identity** has not converged because it is where product differentiation lives.
- **Governance** has no noun because **nobody has yet been forced to pay** for its
  absence.

### 4.1 The collapsed principal

Every one of these systems assumes a **collapsed principal**: the human who installs
the plugin, grants the tool, reads the output, and is accountable for the action is
one person at one terminal. That assumption does enormous silent work — it is why
`allowed-tools` can sit in a `SKILL.md` at all. The installer *is* the grantor, so
prose-borne permission is bounded by an install decision.

It breaks under three pressures, and only under all three at once:

1. **Multi-principal** — more than one human in the same workspace.
2. **Unattended** — the actor runs when nobody is watching.
3. **Consequential** — the action leaves the sandbox and touches the world.

Any one is survivable. All three together are not, because *"who authorized this?"*
can no longer be answered from the session.

**The collapsed principal is an assumption, not a design.** Nobody chose it; it is
what a local single-operator CLI gives you for free. Assumptions nobody chose are
precisely the ones that break without warning.

---

## 5. What this means for yarnnn

### 5.1 Two of the four nouns have no counterpart

yarnnn answers four questions with four nouns:

| Noun | Question | Ecosystem counterpart |
|---|---|---|
| **agent** | who is speaking | subagent (roughly) |
| **app** | what capability + grammar | none — the job is split across plugin/subagent |
| **skill** | how is this work done | skill (converging) |
| **grant · declaration · gate** | may this happen, and when | **none** |

Two caveats against overstating this. The `app` gap is **organizational, not
structural** — plugins do the packaging job, just cut differently; `register_app`
carrying identity-only ("no authority, no tool grant — an app pins a colleague, it
cannot widen one") is good discipline, not a moat. The governance gap is the real
one.

**And "governance" is itself two nouns in yarnnn, which this doc must not merge.**
`grants-and-reach.md` opens by disambiguating them:

> the **reach grant** (`principal_grants` — who may reach the workspace) … the
> **autonomy grant** (`governance/` — how far an *agent's decisions* bind, ADR-366)
> shares nothing but the word.

### 5.2 The three commitments that should age well

1. **Authority is unrepresentable, not merely unset.** ADR-460 D3.a: there is no
   field on an agent row for consequential authority, and *"a session that adds an
   authority field here has violated ADR-460"*, gate-enforced. The opposite of the
   ecosystem's move, which is to add fields to the nearest object.

2. **A declaration names the app; the agent is derived** (ADR-603 D2). Authority
   attaches to **work**, not to actors. Re-pairing an agent re-points every
   declaration with zero data movement, and no field anywhere names an agent as the
   holder of standing power.

3. **Reach is derived from the principal, not from configuration.** The lane frame
   states it to the model directly: *"Your reach is exactly the member's grant:
   anything they could not write, you cannot."*

### 5.3 Why the yarnnn cut is defensible even after the §3.4 correction

The two systems separate craft from reach on **different axes**: yarnnn by
**writability** (`memory/` freely writable, the `_autonomy.yaml` + `_budget.yaml`
sidecars LOCKED, in the same home); Claude Code by **duration** (turn-scoped grants).

Both are real separations. Duration-scoping assumes **reader = grantor** — true for a
local CLI operator, false for a multi-principal attributed commons. A turn-scoped
grant still means a file that travels can widen what its reader may do; scoping bounds
the blast radius in time without changing the direction of authority.

Different threat models, defensibly different rulings. But only one can be right about
the general case.

### 5.4 The named risks

**R1 — generalizing from n=1.** `standing_declarations.py` says it out loud:
*"Building a general engine before a SECOND instance exists would abstract from one
example, which is how the wrong axis gets picked."* `DECLARATION_KEYS` is seven keys
over exactly one implementation (Strings). The restraint is correct; the risk is
**asymmetric in time**. If an ecosystem governance noun lands before yarnnn's second
declaration instance exists, the abstraction gets chosen under external pressure
rather than from evidence — and there is no third option at that point.

**R2 — convergence arrives as a compatibility ask, not an architecture ask.** Nobody
will propose "add authority to your agent rows." Someone will ask to import a plugin,
or to accept `allowed-tools` for portability, or to support a standard skill carrying
`model:`. Each is individually reasonable.

The `HOME_ALIASES` precedent is the right instinct — resolve the participant's
told-vocabulary at one chokepoint rather than refusing it ("RESOLVE, never refuse:
the participant used the vocabulary we handed it"). The governance equivalent is
**strip-and-re-derive at a single seam**: an imported artifact's authority claims are
discarded and re-derived from grants, never honored as written. Worth having before
it is asked for.

**R3 — boundaries cost prose, and prose is what gets ratcheted.** Every boundary
needs stating somewhere, and every statement is billed on every turn. The frame is
byte-ceilinged (ADR-630's two index budgets; ADR-634 now caches it rather than
shrinking it), and CLAUDE.md carries its own ratchet — breached at 52.7K during the
ADR-632 arc, since ablated back to 45.1K under the 50K ceiling, which is the
discipline working rather than a standing defect. The ecosystem resolves the same
tension by **collapsing nouns**
(skills absorbing commands). yarnnn resolves it by ablating prose while keeping nouns
distinct (DP22, ADR-306). That is the harder path, and it has a budget.

---

## 6. The bet, its falsifier, and the review trigger

### The bet

yarnnn is architected for the **multi-principal + unattended + consequential** world
that the ecosystem is currently packaging its way toward without naming. If that world
arrives, the four-noun separation is a structural advantage that is very hard to
retrofit — governance-as-retrofit attaches authority to whatever object is nearest,
and the nearest hook today is a turn-scoped tool grant growing into a standing one.

If that world does not arrive — if the durable value stays in collapsed-principal,
single-operator tooling — then the separation is expensive discipline buying an option
nobody exercises.

### The falsifier

Stated as an observable question, in the shape of the W0 falsifiers:

> **Q: Have multi-principal + unattended + consequential agents become common while
> governance is still expressed as turn-scoped tool grants attached to craft or
> identity artifacts?**
>
> If **yes** — the pressures arrived, and the ecosystem absorbed them *without* needing
> a governance noun. Then the collapsed principal was more durable than this analysis
> claims, and the four-noun separation is over-engineering. The thesis in §5 is wrong.
>
> If **no, because a governance noun appeared** — the prediction holds, and the open
> question becomes only whether yarnnn's cut or the ecosystem's is better. §5.3.
>
> If **no, because the three pressures have not co-occurred** — the bet is unresolved,
> not vindicated. Do not read delay as confirmation.

Two counter-observations that would also weaken the bet, recorded so they are not
quietly ignored:

- The portable Agent Skills spec **drops** `allowed-tools` from its six fields in a
  future revision — evidence the ecosystem is separating craft from reach on
  yarnnn's axis without needing the noun.
- A vendor ships multi-principal workspaces where authority is derived from the
  *caller's* grant rather than from installed configuration — the §5.2.3 invariant
  arrived from outside.

### The review trigger

Re-read this document when **any** of these occurs:

1. **A second standing-declaration instance ships** (R1's trigger — the point at which
   ADR-603 D2's rule meets evidence rather than one example).
2. **An ecosystem governance noun appears** — any first-class object whose subject is
   *may this happen*, distinct from craft, identity, and packaging.
3. **A compatibility ask lands** that would import authority claims from an external
   artifact (R2's trigger — the strip-and-re-derive seam becomes due).

Absent a trigger, this document is discourse capture and nothing is owed.

---

## 7. What this doc does NOT decide

No canon edits. No ADR. No vocabulary change — "plugin" deliberately does not enter
the GLOSSARY, and the four nouns are unchanged. The `app`/plugin comparison in §5.1 is
an observation, **not** a proposal to rename or restructure anything.

The one thing worth carrying forward as a candidate claim, if yarnnn ever states a
public architectural thesis as the landscape converges:

> **Authority attaches to work, never to actors.**

ADR-460 D3.a, ADR-603 D2 and ADR-596 D2 all say it from different angles, and it has
no counterpart anywhere in the ecosystem surveyed here. It currently lives in a module
docstring that describes itself as deliberately thin.
