# The envelope collapse: the other half of the CC-clean separation

**Date**: 2026-06-24
**Hat**: B → A. The fourth leg of the re-founding. The spine (`the-wake-is-a-pre-authored-ask`) made the WAKE CC-shaped (the ask). This makes the ENVELOPE CC-shaped (governance-as-CLAUDE.md + a substrate snapshot + the ask + the clock; everything else read on demand from authored substrate). ADR-360 shipped the wake half; this is the explicitly-deferred parallel deliverable named in `the-ask-framework-collapse` §0 and `spine-blast-radius` §2.
**Status**: Pre-ratification conviction. No code moved by this doc. The strip is gated on a funded fresh-state A/B probe before any deletion lands.
**Operator decision on record (2026-06-24)**: full CC-shape, with **the authored substrate replacing the envelope dumps** — Arm B = governance-block + substrate-snapshot (the `gitStatus`-analogue) + the ask + clock; everything else read on demand. The snapshot is the one curated non-governance/non-ask item, because it is the load-bearing replacement for the absent scoping-principal.

---

## 0. The thesis in one paragraph

ADR-360 proved the wake must arrive as a present-tense ask (the user-message-analogue). The envelope is the *other half of the same CC turn*: CC's standing context is **three things** — `claudeMd` (the repo's authored governing file), `gitStatus` (a snapshot of substrate state, stamped "will not update during the conversation"), `currentDate` (the clock) — and then the agent **reads everything else through tools against the live filesystem.** YARNNN's authored substrate (ADR-209) *is* that filesystem. So the CC-clean envelope is not "20 dump-sections → 3 dump-sections"; it is **governance-block (the CLAUDE.md-analogue) + a substrate-state snapshot (the `gitStatus`-analogue) + the ask + the clock**, with all detail (specs, profile, risk, mirror history, ground-truth body) read on demand from the authored substrate. The 20-section per-wake re-dump exists only because the system doesn't trust the agent to read its own substrate — the exact prosthetic CC proves unnecessary.

---

## 1. The benchmark, exactly (from `context.ts`, not from memory)

CC's entire per-conversation standing context (`getUserContext` + `getSystemContext`):

- `claudeMd` — the repo's authored governing file, read off the filesystem (`getMemoryFiles()` → `getClaudeMds()`).
- `gitStatus` — **a curated delta**, not nothing and not everything: branch, main-branch, `git status --short` (dirty paths, truncated at 2k chars), `git log --oneline -n 5` (recent commits), git user. Explicitly stamped: *"this status is a snapshot in time, and will not update during the conversation."*
- `currentDate` — `Today's date is {ISO}.`

The system prompt is 7 static cached sections (intro, system, doing-tasks, **actions** = the whole autonomy story in one paragraph, using-tools, tone, output-efficiency) + a `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` marker + a few memoized dynamics. Everything the agent needs beyond these, it reads via tools.

**The `gitStatus` insight (load-bearing for this doc):** CC doesn't pre-dump the files it'll edit. It dumps a *snapshot of what changed and what's dirty* — a pointer to where the truth lives — and reads the actual content on demand. `gitStatus` is the **scoping organ**: it tells the agent *where to look* without dumping everything.

---

## 2. The asymmetry the snapshot must cover — the absent SCOPING principal

The spine named the absent *obligation* principal (no live ask → the wake must reconstitute one). The envelope collapse hits the same asymmetry wearing a different hat: the absent **scoping** principal.

In CC, the **user message scopes the read** — the agent reads what the request points it at, and the human is the are-we-done judge. Strip YARNNN's envelope to "governance + ask + clock" alone and the agent must reconstruct *what's relevant to read* with **no scoping principal**. The failure mode is not a refusal (which the agnostic-kernel gate would catch) — it is **silent**: the agent reads the wrong things, or misses the load-bearing thing, and judges on partial substrate. It still composes; it just judges *worse*. That regression would pass the ADR-360 behavioral gate and still be a real loss.

**The `gitStatus`-analogue is the fix.** A curated substrate-state snapshot — *what changed since the last wake, what's dirty, the ground-truth head* — is the load-bearing substitute for the absent scoping-principal. It is the one item that cannot be pure on-demand, because without it the agent does not know *what to read*. Everything else genuinely can be on-demand, because the snapshot points at it.

This is why the operator's "authored substrate replaces the dumps" is exactly right **and** why full-bare (no snapshot) is a trap: the substrate replaces the *content* dumps, but the snapshot is what makes the substrate *navigable without a principal*. CC keeps `gitStatus` for the same reason; we keep its analogue.

---

## 3. The collapse boundary (every component classified)

CC structure: **system prompt = static cached; user message = governance + snapshot + ask + clock; everything else = tool-read.** Mapped onto every current YARNNN envelope/frame component:

| Component | ~tok/wake | CC analogue | Verdict |
|---|---|---|---|
| `_compute_minimal_frame` | ~3000 | system prompt (static, cached) | **KEEP** — principal-shift + action-grammar. Trim (ceiling rebloat lives here) but it stays the cached system layer. |
| **`_TRIGGER_FRAMING[reactive\|addressed]`** | **600–750** | — *(CC has no per-turn coaching)* | **DELETE.** The single biggest prosthetic. Standing-state coaching ("default is action / stand-down is the LAST option / common shapes for recurrence fires") wrapped around an already-imperative ask. This is precisely what ADR-360's ask-shaped wake made redundant — the imperative carries the directive; `getActionsSection`-analogue (the autonomy paragraph) lives in the frame. |
| IDENTITY · principles · MANDATE · AUTONOMY · PRECEDENT | varies | **CLAUDE.md** (static/cached) | **KEEP — as the governance-block.** These are the authored governing files = the CLAUDE.md-analogue. Cacheable until a revision lands (ADR-209 head_version_id is the cache key). |
| budget · expected_output · preferences | varies | part of CLAUDE.md-analogue | **KEEP in governance-block.** |
| operating_context (now/tz/market/tenure) | ~50 | `currentDate` + market clock | **KEEP — live, tiny.** The clock-analogue. |
| wake_context (source + triggering path/rev) | ~30 | (part of the user message) | **KEEP — it's part of the ask.** |
| **schedule_index · recent_execution · calibration** (mirror files) | often large | `gitStatus` is read on demand | **FOLD into the substrate-snapshot** (they ARE "what fired / what changed / how it's calibrating"), OR demote to on-demand ReadFile. The snapshot carries the *head*; the agent reads the full mirror file when judgment needs it. |
| **specs_inventory** | varies | tool-discovered | **DEMOTE to on-demand** (ListFiles `operation/specs/`). |
| operator_profile · risk · ground_truth body · program-envelope | varies | CLAUDE.md program-section / on-demand | **SPLIT:** governing constants (profile, risk floors) → governance-block; *changing* state (ground-truth body, signal files) → snapshot head + on-demand body. |
| **the ask** (recurrence_prompt / user_message / proposal) | varies | **the user message** | **KEEP — the whole point.** |

### The structural move (mirror CC's boundary)

Today: one cached frame + a **fully-rebuilt** user message every wake. After: 

```
SYSTEM (cached until deploy):    minimal_frame      (principal-shift + action-grammar)
USER (per wake):                 governance-block   (CLAUDE.md-analogue: IDENTITY+principles+MANDATE+
                                                     AUTONOMY+PRECEDENT+budget+expected_output+profile+risk;
                                                     cacheable until a governing-file revision lands)
                               + substrate-snapshot (gitStatus-analogue — §4)
                               + operating-context  (clock+market+tenure)
                               + THE ASK            (recurrence imperative / user_message / proposal)
                               — everything else read on demand from authored substrate via tools
```

The governance-block is the CLAUDE.md-analogue and *can be cached* the way CC caches `claudeMd` — its cache key is the max `head_version_id` across the governing files; it only rebuilds when the operator (or the agent, under ADR-209 attribution) revises a governing file. That kills the per-wake re-dump cost AND removes the pressure that leaks into the frame ceiling.

---

## 4. The substrate-snapshot — the `gitStatus`-analogue, designed precisely

This is the one new organ. It must be a *curated delta*, not a dump — CC's `gitStatus` is ~6 lines + a truncated short-status, not the repo. Grounded in substrate that already exists (`workspace_file_versions`, ADR-209; the existing `_get_recent_authorship_sync` in `working_memory.py` is the seed — it already groups recent revisions by `authored_by` layer; the snapshot extends it to carry *paths* so the agent knows what to read).

**Contents (the four `gitStatus` lines, YARNNN-shaped):**

1. **What changed since your last wake** (the `git status --short` + `git log` analogue). Query `workspace_file_versions` since the prior wake's timestamp (or last 24h fallback): list of `path — authored_by — message` for the most recent N revisions (cap ~15, truncate like CC's 2k char cap). This is the scoping signal: "these paths moved; read the ones your ask touches."
2. **Pulse head** (folds in `schedule_index` + `recent_execution` mirrors): one-line "your declared cadence + last fires" — the head only; full mirror file is on-demand.
3. **Ground-truth head** (the `_money_truth.md`/program ground-truth frontmatter head — the by-signal/outcome summary, NOT the body). The body reads on demand. This is the closest YARNNN has to "the state of the world the judgment is about."
4. **Calibration head** (folds in `calibration_md`): one-line "where your cadence stands vs ground truth" — the ⚠ verdict-hints only; full calibration on-demand.

Each is a **head/pointer**, not a body. The discipline mirrors `gitStatus` exactly: enough to scope the read, never the full content. Total target: the snapshot is ~10-20 lines, like CC's, vs the current multi-hundred-line mirror dumps.

**Crucially — this respects Derived Principle 19** ("the kernel does not compute for the prompt"): the snapshot is a *substrate read* (one indexed query on `workspace_file_versions` + reading the head of already-mirror-written files). The mirror files are already written mechanically per scheduler tick (`kernel_mirrors.py`); the snapshot reads their heads. No new LLM-time derivation.

---

## 5. The probe (probe-before-canon — gates the whole collapse)

**Question:** does the agent compose/judge correctly when the envelope is `governance-block + substrate-snapshot + ask + clock`, with `_TRIGGER_FRAMING` deleted and all detail demoted to on-demand reads?

**Method** (the validated ADR-360 E2E methodology): funded fresh-state `yarnnn-author` (U=`0b7a852d`), full reset (corpus content/profile/manifest + `persona/{standing_intent,judgment_log,calibration,handoffs}.md`; keep `_*` scaffolding + `entities/`), paused recurrences (no deployed-scheduler race), wake_queue cleared, fresh unique slug per run (no 60s min-interval skip).

**A/B as a toggle, not a fork** (singular implementation — one `_build_user_message` with an env/param gate, so A and B differ by exactly the strip):
- **Arm A (control):** current ~20-section envelope + `_TRIGGER_FRAMING`. Known 9/9 behavioral (ADR-360 E2E).
- **Arm B (stripped, full CC-shape):** governance-block + substrate-snapshot + ask + clock; `_TRIGGER_FRAMING` deleted; mirrors/specs/detail absent from envelope (agent must ReadFile on demand).

**PASS gate (same agnostic-kernel gate as ADR-360, plus two quality checks):**
1. **Behavioral (the ADR-360 gate):** every run composes/acts OR raises legitimate `Clarify(structural_gap)`; never silently defers / fabricates `stand_down` / exits silent.
2. **On-demand works (the new check):** when the judgment needs mirror/detail state, the agent *ReadFiles it* (proving the snapshot scoped the read correctly and on-demand is viable) — not "judged blind on partial substrate."
3. **Token delta:** meaningful reduction (the win). Measure input tokens A vs B.

**FAIL signatures to watch:** (a) silent quality regression — composes but judges on partial substrate it should have read (snapshot under-scoped); (b) read-thrashing — agent ReadFiles everything anyway (snapshot didn't replace the dump, just moved it); (c) any silent defer (the absent-coaching broke the close-contract — would mean the frame, not the framing, must carry it).

---

## 6. Sequence (each gated)

1. **Substrate-snapshot helper** — build `build_substrate_snapshot(client, user_id, since)` (the `gitStatus`-analogue, §4). Read-only, DP19-compliant. *(no canon)*
2. **A/B toggle in `_build_user_message`** — a param/env gate selecting full-envelope vs stripped. Singular implementation; the toggle is removed once the collapse lands. *(no canon)*
3. **Run A/B on funded fresh-state** — prove Arm B passes the 3-part gate + token delta. *(GATE — nothing below proceeds without this)*
4. If pass → **land the collapse**: delete `_TRIGGER_FRAMING`, demote mirrors/specs to on-demand, introduce the cached governance-block boundary (cache key = max governing-file `head_version_id`). *(code)*
5. **Frame-ceiling trim** — with `_TRIGGER_FRAMING` gone, the remaining ceiling pressure is the frame itself; move what's movable to `principles.md`. Folds in the deferred ceiling debt (11841 > 11500). *(code)*
6. **Canon cascade last** — doc-first amendments after code proves out (FOUNDATIONS DP32 / ADR-318 amendment / persona-frame doc / the envelope ADR). *(canon)*

---

## 7. What this confirms about the moat (the substrate floor is untouched)

The collapse is **envelope-and-loop only, over an intact substrate floor.** ADR-209 (`authored_substrate.py`, `workspace_files`/`_versions`/`_blobs`) and the primitives-as-tools surface are *not touched* — they are CC's filesystem + tools, already done right. In fact the collapse *strengthens* the FS-native claim: it forces the agent to actually read its substrate on demand (CC's model) instead of being spoon-fed dumps, which is the truer test that the substrate IS the agent's world. The snapshot points at the authored substrate; the agent reads it; the judgment rests on what it read. That is the cleanest expression yet of "authored substrate + FS-native = the agent's filesystem," and it is exactly the operator's instinct that the authored substrate should *replace* the envelope dumps.

---

## 8. Bottom line

ADR-360 made the wake an ask. This makes the envelope a CC turn: a cached governance-block (the CLAUDE.md-analogue), a curated substrate-snapshot (the `gitStatus`-analogue — the one organ that replaces the absent scoping-principal), the ask, and the clock — everything else read on demand from the authored substrate the moat already owns. The biggest single deletion is `_TRIGGER_FRAMING` (~600-750 tok of standing-state coaching the ask-shaped wake made redundant); the biggest structural win is caching governance instead of re-dumping it every wake, which also relieves the frame-ceiling rebloat. The risk is a *silent* quality regression (judging on under-scoped substrate), which is exactly why the snapshot exists and exactly what the A/B probe's on-demand-read check is built to catch. Subtractive over an intact floor, gated on a funded fresh-state probe, singular-implementation throughout — the same discipline that landed every step of this arc.
