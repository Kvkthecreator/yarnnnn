# Canvas click pass — the first observed bound-canvas turn (ADR-471 C6)

> **Scenario**: the worksheet's step-4 discipline, third application — one composite make-ask against the REAL composed canvas mind (Designer character + the canvas studio posture over the real `build_skeleton("canvas")`), live `anthropic/claude-sonnet-4-6`, tools stubbed over fixtures, faithful to the runtime's contracts (full tool results; the REAL `STUDIO_LANE_MAX_TOKENS = 8192` authoring profile — see the harness-fidelity lessons below).
> **Harness**: `harness_canvas_turn.py` (this dir). Fixture: the canvas skeleton + a binary product image (`revision: img-r7`) + a QueryKnowledge note carrying the ratified launch line.
> **Ask**: "Compose the launch visual on this canvas: our launch line as the headline, the product shot from the brand folder, and an accent shape behind the headline."

## Findings applied (worksheet step 5 — only what the turns proved)

Two posture amendments in `services/studio.py` (CHANGELOG `[2026.07.20.5]`), pinned by `api/test_adr471_canvas.py` (5/5):

1. **First composition is honest WriteFile.** Both live runs chose wholesale replace for composing onto a fresh scaffold — fighting that with the patch rule produced nothing but rule-tension. Amended: one WriteFile carrying the COMPLETE document is the honest first-composition act; the patch discipline resumes after.
2. **Placeholders are replaceable; member-authored blocks never.** Both runs dropped the scaffold's placeholder kicker while composing — sensible design the old rule ("never remove ids you didn't create") read as forbidding. Amended: scaffold starter blocks may be replaced when composing; member/prior-turn blocks keep their ids, always.

## Run log

- **Run 1** (pre-amendment): 7/10 raw. Positioning ✓ all-percent ✓ cited+pinned figure ✓ z-on-overlap ✓ kernel/skin intact ✓. Apparent failures: grounding ✗ (false — see lesson 2), patch-discipline ✗ (WriteFile chosen; one content-less attempt), scaffold-kicker dropped.
- **Run 2** (fresh sample + headline dump): same profile; the dump proved the headline IS *"Start free —\<br\>upgrade when\<br\>it earns it."* — the grounding check's regex broke on `<br>`, twice. Model behavior was correct; the check was wrong. Multiple content-less WriteFile attempts (4) before the complete one.
- **Run 3** (amended posture, still 4096): 9/11 — compose rule ✓, stable ids ✓; content-less WriteFile attempts persisted (4), grounding regex still tag-blind in the h1 dump window.
- **Run 4 — CONFIRM (amended posture + the REAL 8192 authoring profile): 11/11.** One clean sequence — `QueryKnowledge` → `ListFiles` → `ReadFile`(artifact) → `ReadFile`(image) → ONE complete `WriteFile`, `derived_from` citing both sources unprompted, settled line as the headline, kicker replaced with authored content, every block positioned, z=2 on the overlapped headline.

## The two harness-fidelity lessons (the capture's real dividend)

1. **Input side (run 0 of the Designer pass, re-confirmed):** truncating stubbed tool RESULTS below the real lane's no-truncation contract makes rational behavior look broken.
2. **Output side (new, this pass):** under-provisioning `max_tokens` below the real lane's authoring profile makes the model emit **truncated tool calls** — WriteFile arriving without its `content` arg, repeatedly, which reads as a model defect and is entirely a harness artifact. Runs 1–3's "malformed WriteFile" observation dissolved to zero at the real 8192. **A harness must match the runtime's token provisioning before observing tool-call quality.**

## Verdict

The canvas mode's composed mind (Designer + canvas posture + uniform surface) **holds under observation on every axis**: everything-positioned (percent-of-frame), z where overlap is intended, text as text, raster only as cited+pinned figures, grounding via recall (the Designer-pass line carrying over), and honest first-composition. No capability addition needed. The `authored_by` param the model kept passing to WriteFile is ignored-by-schema (the runtime stamps attribution) — noted, harmless, not worth a posture line until it costs something real.
