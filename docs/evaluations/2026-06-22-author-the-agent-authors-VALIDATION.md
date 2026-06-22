# Validation — ADR-355 (the agent authors): the reframe works; the next floor is a perception-field gap

**Date**: 2026-06-22
**Hat**: B (external developer). Workspace: yarnnn-author (`0b7a852d`), delegation `manual`, program alpha-author.
**Pairs with**: ADR-355 (the boundary reframe) + ADR-354 (the recurrence-prompt collapse that let the agent reason forward to these floors).

---

## The arc (operator-driven)

The operator asked: *"for yarnnn-author, couldn't you act on behalf of the operator since the topic is about our repo?"* — i.e. play the operator (I have real repo knowledge) and give the workspace genuine material to author from. That dissolved the "needs setup" objection and produced three nested results, each the agent correctly holding a floor.

## Probe 1 — origination under the old boundary → correct refusal

Operator-proxy seeded a real piece intent (`profile.md`: topic = the ADR-354 autonomy investigation, with source pointers) + declared a real voice (`_voice.md`). Fired `compose-piece`.

**Result** (exec_event e3c635e4): the agent refused to author and surfaced a Clarify —
> *"The MANDATE forbids me authoring content solely by AI, even with intent present."*

Not passivity — faithful obedience to MANDATE boundary line 32 (*"the operator authors; the Reviewer audits"*). **The boundary was the bug**: it capped the agent below full autonomy and contradicted ratified ADR-345 (autonomy-as-witness: the agent always works the full job) + FOUNDATIONS:240 (the agent IS the operator's judgment rendered autonomous). Also an internal bundle contradiction: piece-composition.md:47 said "the Reviewer authors the prose" while MANDATE:32 + spec:67 said operator authors.

**Operator decision**: *"it's NOT operator authors. Agent and our system should lean stronger towards full autonomy, full accountability."* → **ADR-355**. The agent authors as the operator's installed judgment; the anti-slop guarantee moves from "a human in the authoring seat" to "every shipped piece clears the floor" (a human can write slop; the floor is objective). Operator = principal + witness.

## Probe 2 — origination under the reframed boundary → the reframe WORKS, next floor held

Pushed the reframed MANDATE + piece-composition + CONVENTIONS to the live workspace (revs 7952fa8c / 7d0cf1da / 38c2df87). Re-fired `compose-piece`.

**Result** (exec_event 5ce32f01): the agent **no longer cites the authorship boundary** — the reframe worked. It moved past it and held the *next* floor —
> *"the referenced source documents (ADR-354, evaluation report, analysis) are **external to this workspace and I cannot verify them**. Per the citation-verifiability rule, I cannot author a piece whose load-bearing claims rest on unverifiable sources."*

Correct again. My `profile.md` cited sources by **repo path** (`docs/adr/ADR-354-*.md`) — those live in git, NOT in the agent's workspace substrate. The agent can't read them, so it can't verify the claims, so its floor (real-data-only / no-invented-citations, piece-composition.md:95) forbids authoring. This is the **ADR-335 perception-field principle in the author domain**, exactly parallel to the trader's "rule references fields the perception field doesn't emit" (ADR-354 D2): the intent referenced material outside the agent's perception field.

## The finding — a real perception-field gap for repo-subject author workspaces

A YARNNN-about-YARNNN author workspace's *subject is this repo*. But the alpha-author bundle's only source transport is **TrackWebSources** (RSS/Atom feeds — `kind: rss|atom`, ADR-336). **There is no repo/git/filesystem source driver.** So the workspace has no declared way to perceive the repo it is meant to write about — the repo is structurally outside its perception field.

The agent's refusal was therefore *doubly* correct: the cited sources were not just unverifiable, they were **structurally unreachable** by any source this program supports. This is not a passivity or authorship problem (both resolved) — it is a **missing perception-field driver** (a real Hat-A gap).

## What is proven

| Question | Verdict |
|---|---|
| Does the agent author under full autonomy (ADR-355)? | The boundary that blocked it is removed; the agent no longer refuses on authorship grounds (probe 2 dropped that objection). The reframe works. |
| Is the agent passive? | No — three correct floor-stops this session (trader VaR floor; author authorship boundary [now removed]; author citation-verifiability). Forward-reasoning to a real floor every time, never silent stand-down. The ADR-354 collapse is what lets it reason forward to the floor. |
| Why no authored piece yet? | Not passivity, not authorship-cap (fixed) — a **perception-field gap**: no driver makes the repo perceivable to the workspace. |

## Recommendation (Hat-A, deferred — its own design task)

A repo/filesystem source driver — an **ADR-336 sibling** (`TrackRepoSources` or a filesystem watch: a mechanical, zero-LLM, dispatcher-only primitive that distills declared repo paths into `_watch_signal.yaml` per the ADR-335 D3 observation contract). With it declared in `_sources.yaml`, a repo-subject author workspace can perceive + cite its subject, and the agent authors with verifiable citations under ADR-355. Until then, a repo-subject author workspace is a not-yet-supported case (the operator can still paste source material into substrate manually, but that is a workaround, not the architecture).

## ADR-355 shipped (this session)
Bundle: MANDATE boundary + Rule #5 + Draft/Pre-ship lifecycle reframed; piece-composition.md internal contradiction resolved; CONVENTIONS aligned. CHANGELOG [2026.06.22.2]. Conformance 18/18. Pushed to yarnnn-author live.
