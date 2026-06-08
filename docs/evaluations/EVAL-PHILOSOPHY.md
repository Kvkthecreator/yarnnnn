# Eval Philosophy — what the eval system is fundamentally measuring

> **The conceptual frame above the mechanics.** [`EVAL-SUITE-DISCIPLINE.md`](EVAL-SUITE-DISCIPLINE.md) says *how* to write a suite (the two-axis method, read-kinds, pre-flight, prose reads). [`README.md`](README.md) says the *discipline* (criterion declaration, two hats, capture shapes). **This doc says what the whole thing is FOR** — the model of the system being evaluated, from which the suite structure and posture model derive. Read this first when the question is "what are we even testing, conceptually?"
>
> **Status**: frame proposed 2026-06-07 (operator-articulated). Captures the governing metaphor the recent architectural arc (five-root topology ADR-320, seat/occupant carve ADR-315, persona-frame collapse ADR-306/323, Hat-A/Hat-B) has been building toward. Trader specifics slot under §3 layer 4; this doc is domain-agnostic.

---

## §1 The governing metaphor: the filesystem is the repo; the Reviewer is a self-running Claude Code over it

YARNNN's whole architecture — and therefore the eval system that probes it — is organized around one mapping:

> **The workspace filesystem is the repo. The Reviewer agent is a self-running Claude Code operating on that repo, carrying standing intent across invocations.**

This is not analogy-for-flavor; it is the literal organizing principle (ADR-222 OS framing, Derived Principle 16). It explains why every separation in the system is shaped the way it is:

| Claude Code concept | YARNNN realization | Canon |
|---|---|---|
| The repo / working tree | The workspace filesystem (`workspace_files`) | ADR-106 |
| `git` (history, attribution, content-addressing) | Authored Substrate — blobs + revision chain + `authored_by` | ADR-209 |
| File permissions (`chmod` / protected paths) | Five-root topology — `governance/` `constitution/` `persona/` `operation/` `system/`; the directory IS the write-permission policy | ADR-320 |
| An invocation of Claude Code on the repo | A **wake** — cron/recurrence/addressed/substrate-event fires the agent | ADR-296 / ADR-298 |
| The runtime environment Claude Code reads at launch (cwd, clock, env) | The **Operating-Context block** — now / market-state / tenure, assembled at every wake | ADR-274 / ADR-301 |
| Claude Code's tool surface (`bash`, `read`, `write`, `grep`) | The **primitive matrix** — the agent's syscall ABI | ADR-168 / ADR-321 |
| "Claude Code the role" vs "the model instance running it" | The **seat** (published ABI) vs the **occupant** (running model) | ADR-315 |
| Anthropic's internal evals OF Claude Code | The **eval suite** (Hat-B) running the Reviewer against fixtures | this directory |
| Editing Claude Code itself (its prompt, tools, behavior) | **Hat-A** — system canon that ships to operators | CLAUDE.md §Two Hats |

So the **two hats** are not a process nicety — they are *the two sides of building a self-running coding agent*: Hat-A is editing the agent; Hat-B is the harness that runs it against situations to see if it behaves. The **seat/occupant carve** is "the role" vs "the process." The **filesystem topology** is the repo's permission model. Every recent structural decision is this metaphor being built out.

---

## §2 Where the metaphor breaks — and that break IS the product

Claude Code, as it ships, is **commissioned**: a human issues a task each invocation ("fix this bug"). It has tools and judgment *within a task*, but it holds no **standing intent** — it does not wake on its own and decide *what the repo should become*. Its "why" arrives fresh, every turn, from the human.

YARNNN's Reviewer is architecturally **Claude Code plus a standing principal-relationship across time**. That added layer is precisely what the recent personified-agent split (seat = harness mechanics; occupant = the judging mind) was carved to isolate, and it has **two parts** the prompt strategy makes explicit (`reviewer_agent.py::_compute_minimal_frame` + the wake-envelope rendering):

1. **The MANDATE — the operator's "why", held as the agent's standing intent.** `constitution/MANDATE.md`, operator-authored, in the read-only-to-the-agent `constitution/` root. The frame: *"You are the operator's installed judgment, acting on their behalf while they are away — NOT an assistant awaiting instruction."* The agent does not own the mandate's *existence* (the operator declares it); the agent owns its *pursuit*. **This is the thing Claude Code wholly lacks: a persistent principal-on-whose-behalf it acts across invocations.**

2. **`standing_intent.md` — the agent's own thread of pursuit, carried wake-to-wake.** `persona/standing_intent.md`, agent-authored, in the agent's own `persona/` root. "What I was watching for last cycle." The running memory of pursuing the mandate across wakes. Closing a wake *is* writing this (the cycle-closure contract).

**Mandate = the principal's persistent why (inherited, indexed). Standing intent = the agent's persistent thread-of-pursuit (self-authored).** Together they are the intent/judgment layer Claude Code's commission-per-task model has no place for. This layer is **the product** — "a self-running Claude Code that holds and pursues standing intent" is the thing YARNNN is, that a commissioned coding agent is not.

### §2.1 The load-bearing prompt move: index, don't assert (ADR-314)

The frame **indexes** the mandate ("read your governing files; act on what they declare") rather than **asserting** it ("the operator already told you what to do"). This single choice is why the agent behaves coherently across the full range of the metaphor's stress:

- **Mandate present + substrate supports it** → act on it (the clean case).
- **Mandate present + substrate does NOT yet support it** → *reason honestly about the gap*, do not invent the missing readiness.
- **Mandate absent (standby / bare-kernel)** → "an absent MANDATE means the operation's primary intent has not yet been established… reason honestly about that absence rather than inventing intent."

Index-not-assert is canon's answer to the question that motivated this whole frame: *what does the agent do when its mandate entices action but it isn't set up to act?* — it reads the gap and reasons honestly about it, rather than confabulating the readiness to satisfy the mandate's pull.

---

## §3 The four layers the eval system must read

The metaphor implies a layered evaluation target. Each layer is a distinct read with a distinct tool (this is the conceptual parent of EVAL-SUITE-DISCIPLINE §0's MACHINE/MIND split — §0 is layers 1–2 vs 3–4):

| Layer | What it is (Claude-Code terms) | Read tool | Status |
|---|---|---|---|
| **1. Repo mechanics** | Does the filesystem behave like a repo? (permissions, revision chain, attribution, content-addressing) | deterministic `test_*.py` (MACHINE) | well-covered (ADR-209/320 gates) |
| **2. Tool-use** | Given a task, does the agent use its primitives/syscalls correctly? (write lands at the right path, dispatch fires, no silent-wake) | deterministic `test_*.py` (MACHINE) | well-covered (pipeline E2E, silent-wake gate) |
| **3. Judgment-within-mandate** | Given a *well-formed* situation, does it reason like a mandate-holder? (size/cite/refuse the clean case) | judgment-coherence eval (MIND, action altitude — §2.1) | **partially covered** — the clean-situation cells |
| **4. Intent-ownership** | Does it **hold, pursue, and revise standing intent** across the gap between mandate-direction and substrate-reality — own its own readiness gap, surface operator-owned gaps honestly, and NOT confabulate readiness to satisfy the mandate's pull? | stewardship-coherence eval (MIND, strategy altitude — §2.3) | **the frontier — barely covered** |

**Layer 4 is the layer Claude Code lacks, the layer the personified split isolates, and the layer the eval system is least built to read.** It is where "self-improving" lives (revise the rule when ground-truth falsifies it) AND where "the gap between an enticing mandate and an unready substrate" lives (own the gap vs. passively stand down vs. dangerously confabulate). The operator's trading question — *"what does the agent do when its mandate wants trading but it isn't set up to trade?"* — is not an edge case in layer 3; **it is the defining probe of layer 4.**

### §3.1 Layer 4's three-way posture (the read that matters most)

In any layer-4 situation (mandate entices action, substrate is incomplete: stale / empty / closed / bootstrap / missing-universe), there are three responses, and distinguishing them is the highest-value read in the whole system:

- **OWN the gap** (the canon-correct move) — the agent closes its *own* readiness gap with the authority it has: author the cadence/recurrence that would refresh the stale data, write `standing_intent.md` declaring what it's watching for, and surface a **Clarify** only when the gap is genuinely the operator's to fix (broken cadence, missing universe declaration). Per `principles.md`: *"the gap the Reviewer addresses by authoring cadence + standing intent so the upstream substrate refresh happens."*
- **PASSIVELY stand down** (the named anti-pattern, a *failure*) — *"scheduler shows no heartbeat — baseline materialization still in progress, I'm waiting."* Canon: *"That is passive observation, not judgment."* The substrate-isn't-populated is *the gap to address*, not *an answer*.
- **CONFABULATE readiness** (the dangerous failure) — manufacture the missing input to satisfy the mandate's pull: fabricate a regime scalar, assume a price, treat a stale snapshot as fresh, claim a signal match that the data doesn't support. This is the failure mode the mandate's own enticement ("compound capital," "passivity is failure," "default posture: action") *creates pressure toward* — and the one that index-not-assert + anti-confabulation + the hard rules are engineered to prevent. **Reading whether the agent resists this pull is more load-bearing for trust than reading whether it sizes a clean trade correctly.**

The safety invariant under all three (DP24): **ground truth moves the mandate; operator pressure never does** — and, the corollary this frame adds: **substrate-readiness moves whether the agent acts; the mandate's enticement never manufactures the readiness.**

---

## §4 What this frame dictates for suite design

1. **A suite must declare which layer(s) it reads.** A suite that reads only layer 3 (clean-situation judgment) measures a *faithful executor*. A suite that adds layer 4 measures a *steward* — the product. Silently-layer-3-only suites under-claim what's being validated (the original confusion).

2. **Layer-4 situations are the NORM, not the edge.** The agent's lived condition is mostly "mandate wants action, substrate isn't perfectly ready" (signals are rare by design; data goes stale; markets close). A suite that only tests clean situations tests the rare case. The readiness-gap stance should be a *spine* of any agent's suite, not an appendix.

3. **Posture is `(layer × situation × phase × altitude)`, kept as a reading aid** (EVAL-SUITE-DISCIPLINE §4 — never a grading rubric). The trader posture model (`alpha-trader-autonomous-loop.criterion.md`) is the worked instance: situation × phase (bootstrap inverts steady-state) within layer 3, plus the three-way gap-stance (§3.1) for layer 4.

4. **The confabulation surface is the priority read.** For each layer-4 situation, the suite should ask: *what could the agent fabricate here to satisfy the mandate, and does it?* — mapping which fabrications are code-guarded (hard rules) vs. judgment-only (the genuinely-at-risk ones).

---

## §5 Cross-references

- [`EVAL-SUITE-DISCIPLINE.md` §0](EVAL-SUITE-DISCIPLINE.md) — the MACHINE/MIND two-axis method (this doc's layers 1–2 vs 3–4).
- [`EVAL-SUITE-DISCIPLINE.md` §2.3](EVAL-SUITE-DISCIPLINE.md) — stewardship-coherence reads (layer 4's read-kind).
- [`README.md`](README.md) — criterion-declaration discipline + two-hats vocabulary + the one-line spec.
- [`2026-06-07-trader-suite-posture-assessment.md`](2026-06-07-trader-suite-posture-assessment.md) — the trader-specific assessment that surfaced layer 4's under-coverage.
- `api/agents/reviewer_agent.py::_compute_minimal_frame` — the prompt strategy that encodes index-not-assert + the mandate/standing-intent structure.
- FOUNDATIONS Derived Principle 21 (the seat), 24 (stewardship/ownership), 25 (de-naming) + ADR-314 (frame indexes intent) + ADR-319 (ownership over tenure).
