# The ask-framework collapse: one ask, two timings, provenance-as-attribute

**Date**: 2026-06-24
**Hat**: B → A. The third leg of the re-founding, alongside `the-wake-is-a-pre-authored-ask-2026-06-24.md` (the spine — WHY) and `spine-blast-radius-2026-06-24.md` (HOW MUCH). This is the WHAT: the wake framework re-conceptualized to its floor.
**Status**: Pre-ratification conviction. Spine receipt-backed (`2026-06-24-spine-present-tense-ask-VALIDATION.md`); clock-delivery receipt-backed (`2026-06-24-step3-cron-imperative-VALIDATION.md`).
**Scope note**: this doc is ONLY about the wake/trigger framework. The envelope simplification (toward CC's 3-item context) is a separate, parallel deliverable, deliberately out of scope here.

---

## 0. The collapse in one sentence

Five wake sources + a recurrence subsystem reduce to **one unit (the ask) and one axis (when it's delivered: now or later)** — a provenance-tagged message queue where some messages are scheduled for the future. Everything else was implementation detail of *who authored* and *when delivered*, dressed up as distinct kinds of thing.

---

## 1. What exists today (the surface that's too big)

ADR-296 v2 defines **five wake sources** (`services/wake_sources/`): `cron_tick`, `addressed`, `proposal_arrival`, `substrate_event`, `manual_fire`. On top of `cron_tick` sits a separate **recurrence** concept (`_recurrences.yaml` — `{slug, schedule, mode, prompt}`), a per-workspace registry of named judgment scripts. The agent's wake-context machinery disambiguates "which of five sources fired" and "which named recurrence." That's the framework's cognitive surface — five nouns plus a registry.

## 2. The collapse — every source is the same noun

Once the spine holds (a wake is a present-tense imperative — the *ask*), the five sources are revealed as one thing differing only in **who authored the ask** and **when it's delivered**:

| Current source | = an ask, authored by… | …delivered |
|---|---|---|
| `addressed` | the operator | **now** |
| `manual_fire` | the operator | **now** |
| `proposal_arrival` | the world (a proposal landed) | **now** |
| `substrate_event` | the world (substrate changed) | **now** |
| `cron_tick` (recurrence) | someone earlier (operator / agent / bundle) | **later, by the clock** |

There is one noun (**ask**) and one axis (**delivery timing**). The five-source taxonomy is *provenance × timing* presented as five kinds of wake. The agent never needed "which of five sources" — it needs the **ask** and, for trust, **who sent it**.

### The two timings, named

- **Message** = an ask delivered **now**. Live arrival — the operator typed it, or the world raised it. Warranted by *presence* (someone/something is here, asking).
- **Scheduled** = an ask delivered **later**. A clock holds it and delivers it **verbatim** on its due time, optionally re-enqueuing on a cadence. Warranted by *budget* (nobody's present to authorize the spend, so the cost envelope gates it).

`message` and `scheduled` are **not two kinds of thing beside `ask`** — they are the **two delivery timings of the one thing**. The framework is literally: **asks, delivered now (messages) or later (scheduled).**

## 3. What "recurrence" becomes — nothing special

A recurrence stops being its own concept. It is **a scheduled ask that re-enqueues itself on a cadence.** "Weekly: compose the scene" = ask, timing=later, repeat=weekly. "Daily: email the digest" = ask, timing=later, repeat=daily. There is no `_recurrences.yaml`-as-judgment-prompt-registry; there is a **list of standing asks** — each an *imperative + a schedule* — indistinguishable in shape from a todo list with due dates.

This is what makes the program-agnostic janitorial recurrences you proposed (daily-digest, weekly-stale-cleanup) sit in the *same list* as a program's owed-output asks (the weekly scene, the trade-review): they're the same shape — **imperative + when** — and they all work for the same reason the probes composed (the wake is *about* a concrete act, not a situation to classify).

## 4. The two things that resist the collapse (and must survive as real distinctions)

A collapse that erased these would be wrong. Both survive — but each becomes *one attribute / one gate*, not a family of code paths. This is still net-simpler.

### 4a. Provenance survives — as an attribute on the ask, not a wake-type

Who authored the ask matters — not for "what kind of wake," but for **trust and the consequential gate**. "The operator asked me to push" ≠ "I scheduled myself to push" ≠ "a foreign MCP write proposed a push." They must bind differently against the witness dial (ADR-307/352). So:

> **Collapse source-as-wake-type; keep source-as-provenance.** Provenance moves from "which of 5 firing mechanisms" to a single field on the ask — `authored_by` (operator | agent-self | world:{event} | foreign:{actor}), exactly the ADR-209 attribution taxonomy the substrate already uses.

That is a *simplification*: provenance becomes one field the gate reads, not five branches. The agent perceives "here is an imperative; the operator typed it / you scheduled it last week / the market raised it" — and weights trust accordingly.

### 4b. The now/later asymmetry survives — at the budget gate only

A **scheduled** ask fires whether or not anyone's watching, so it must pass the budget envelope (ADR-327) before it spends. A **message** ask is presence-warranted (operator typed it; world raised it). This is not cosmetic: *later-delivery is the only timing that needs cost-gating*, because nobody's present to authorize the spend. And this is **exactly where `budget.py` already gates** — scheduled (`cron_tick`) wakes skip on budget exhaustion; message (`addressed`/reactive) wakes warn-but-fire. The model *predicts the gating that already exists*, which is strong evidence it's the right model.

## 5. The end-state framework (complete statement)

> **One unit: the ask** — an imperative + provenance (`authored_by`).
> **One axis: delivery timing** — *now* (message; presence-warranted) or *later* (scheduled; budget-gated; a clock delivers it verbatim, optionally re-enqueuing on a cadence).
> **The agent** receives the ask, sees who sent it, answers it, and stops. An unanswered ask is visible *as* an unanswered ask (it persists / re-fires) — no terminal-move verdict, no fabricated stand-down.

Drawn on a napkin: **a message queue where some messages are scheduled for the future and tagged with who sent them.** That is the CC-agnostic floor for the wake layer — the same way CC's filesystem-and-tools is the floor for the substrate layer.

### The one discipline this imposes (the whole arc, distilled)

**A scheduled ask must be an imperative at *authoring* time, because the clock cannot reason** — it delivers verbatim. "Compose this week's scene now," never "consider whether composition is warranted." This single rule is what makes the future-message model safe, and it's the rule the 6-probe arc was really about: the FAIL probes all stored *framing* ("assess the operation"); the PASS probes delivered *imperatives* ("compose the scene"). Validated under the clock: `2026-06-24-step3-cron-imperative-VALIDATION.md` (a stored imperative, delivered by `cron_tick`, no operator present, composed from empty corpus; the framing control deferred / recovered).

## 6. What this deletes vs keeps (wake layer only)

| Keep | Becomes |
|---|---|
| The 5 firing mechanisms (the plumbing that detects "an ask is due") | internal detail behind one `enqueue(ask)` — they still EXIST as detectors (a cron tick, a substrate diff, an SSE turn), they just stop being a semantic taxonomy the agent reasons over |
| `wake_queue` / `wake_drainer` / single-lane drain | the message queue — already the right shape |
| `budget.py` gate | the later-delivery cost gate (§4b) — unchanged |
| Mechanical `track-*` | not asks-to-the-agent; deterministic intake that *raises* asks (an observation → a "judge this" message). Unchanged. |

| Delete / dissolve | Why |
|---|---|
| `mode: judgment` named recurrence with a stored framing prompt | replaced by a standing ask (imperative + schedule) |
| `_recurrences.yaml` as a judgment-prompt registry | becomes a list of standing asks (= todos with due dates); program-agnostic |
| wake-source-as-taxonomy in the agent's wake-context | replaced by `authored_by` provenance + timing |
| the verdict-as-terminal-move + recovery synthesizer | an unanswered ask is self-evident; no fabricated close (covered in blast-radius doc) |

## 7. Bottom line

The wake framework collapses to its floor: **one ask, two timings, provenance as one attribute.** Five sources + a recurrence registry → a provenance-tagged message queue with scheduled delivery. The two things that genuinely matter — *who sent the ask* (trust) and *was anyone present to authorize the spend* (the budget gate) — survive as a single field and a single gate, both already present in the codebase, which is why the collapse is subtractive rather than a rewrite of behavior. "Recurrence" and "wake" stop being two confusable concepts: a wake is an ask arriving; a recurrence is an ask scheduled to arrive again. The discipline that makes it safe — *a scheduled ask is an imperative authored now, delivered verbatim later* — is the single rule the entire probe arc converged on, and it is receipt-validated under the clock. This is the napkin-simple, axiomatic, agnostic wake layer the CC benchmark pointed at; the envelope simplification (toward CC's 3-item context) is the parallel deliverable that finishes the picture.
