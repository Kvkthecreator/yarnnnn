# Prompt Changelog

The record of every change to LLM-facing content — the lane frame, the app postures, the
participant constants, the skills, the tool definitions (CLAUDE.md §Prompt change protocol).
An entry names the repeated, observed failure it fixes and the expected behavior change; a
prompt change without an entry is an unexplained instruction. Template: CLAUDE.md.

Rules, held by `api/test_prompt_changelog_discipline.py`:
- Newest first. Prepend under this header. Tags are `[YYYY.MM.DD.N]`, N counting up within the day, unique.
- This file holds the newest two calendar months. When a month leaves the window, move its
  entries verbatim into `archive/YYYY-MM.md` (newest first). Never edit an archived entry; a
  correction is a new entry here that cites the tag it corrects.
- An entry stays under 6,000 chars: what changed, why (the failure, with its receipt), expected
  behavior, the gate. The essay belongs in the ADR.

---

## [2026.09.09.1] - ADR-648: a read is bounded and says so; history bounded in chars

### Changed
- services/primitives/workspace.py: `_clip_read()` bounds ReadFile at
  `READ_FILE_MAX_CHARS = 100_000` (~25K tokens) at BOTH scopes. An unclipped
  read is byte-identical to before (no new keys). A clipped one carries
  `truncated`, `total_chars`, `returned_chars`, `next_offset` and a message
  that FORBIDS answering as though the rest was seen.
- services/primitives/workspace.py: ReadFile's schema gains `offset` (optional
  integer) and its DESCRIPTION documents the bounded window — the continuation
  is a mechanism the model can call, not advice it cannot act on.
- routes/lanes.py: `_clamp_history_chars()` adds `_HISTORY_MAX_CHARS = 120_000`
  ALONGSIDE the existing 20-message count. Drops OLDEST-FIRST, never from the
  middle (the cache matches a prefix); the newest message is never dropped.
- Expected behavior: LLM-VISIBLE for large files only. A file over ~100K chars
  now returns its first window plus an explicit notice; the agent must call
  ReadFile again with `offset=next_offset` to continue. Files at p90 (34K
  chars) and below are unchanged. Conversations under 120K chars are unchanged.

### Why now
- Measured 2026-09-09: workspace files reach 178,206 chars (~45K tokens) with
  6.4% over 40K; lane calls peaked at 86,799 prompt tokens against a 19,999
  median. ReadFile had no cap while ListFiles beside it always has. The
  20-message window bounded COUNT, which is not what a provider bills.
## [2026.09.08.2] - ADR-647 D4/D5/D8: the member's engine preference, and a dark engine says why

### Changed
- services/lane_runner.py: `resolve_member_engine()` reads the member's
  `default_engine` from `member_state` (workspace + principal scoped) and
  NARROWS it through the chooser's own two questions — still offered? available
  right now? A stale, retired, unpriced, keyless or refusing engine resolves to
  None and the app's own default stands. Total: any read failure is None.
- services/lane_runner.py: `upstream_refusal_detail()` exposes the provider's
  own refusal words, which `note_upstream_refusal` has stored since ADR-559 and
  nothing ever read.
- routes/lanes.py: the CREATION door consults the preference (explicit request >
  preference > agent default). The TURN path deliberately does not — a lane's
  engine is what actually ran and is rendered into every revision's attribution
  (ADR-460 D4).
- routes/lanes.py: the capability envelope serves `default_engine` (resolved)
  and per-engine `unavailable_detail`.
- web: the chooser marks "your default" distinctly from this browser's "last
  used", and a greyed row shows the provider's own words.
- Expected behavior: no prompt or model-instruction change. A member with a
  preference set gets it as the default engine for NEW conversations, including
  app-bound lanes which previously had no engine question at all. Existing
  lanes are untouched.

## [2026.09.08.1] - ADR-647: the conversation prefix is cacheable, not just the frame

### Changed
- services/model_router.py: `_build_messages` is now the ONE composition site for
  both router doors (`route_completion` + `route_completion_stream`), replacing
  two inline assemblies. It carries ADR-634's system-frame breakpoint plus a new
  single ephemeral breakpoint on the tail of the message list, caching the whole
  conversation prefix (prior assistant turns + every tool result).
- Anthropic only (`_prefix_is_cacheable`): OpenAI-compatible and Gemini strip the
  marker and cache automatically, so marking there is dead weight. Verified by
  executing all four LiteLLM transforms, not by reading them.
- test_adr634_prompt_caching.py §3: the "both doors" check now asserts the
  RELATION (one payload site, two callers of the builder) instead of pinning the
  old duplicated literal, which would have failed the moment the duplication it
  complained about was removed.
- Expected behavior: no change to what any model is told or how it replies. Lane
  turns of >=2 rounds bill the re-sent prefix as cache reads at 0.10x instead of
  fresh input at 1.0x. A ONE-round turn costs ~25% more (the unamortized write) —
  the same honest trade ADR-634 stated.

### Why now
- 30 days of production `execution_events` (slug `lane` = $74.63 of $75.98):
  fresh input $50.27 (67%), output $18.13, cache write $4.67, cache read $3.06.
  40% of lane calls read ZERO cache; fresh input p90 was 38K tokens against a
  ~4K frame. ADR-634's premise (the frame is the re-sent bulk) had expired.

## [2026.09.07.7] - the reach section is GENERATED from the one reach structure (ADR-644); the agent and the member read the same facts

### Changed
- `services/lane_runner.py` — the three hand-written reach branches (scoped-to-nothing · unscoped/scoped · darkened) and the `.6` outbound sentence are DELETED. The section is now `reach_status.frame_paragraph(...)`: the turn's edge for all four reach states (ADR-535 D3's fragments kept verbatim), then ONE LINE PER CONNECTION from the same structure the member's Connectors page and Reach render — *"Slack (yarnnn): you read it with platform_slack_list_channels, platform_slack_get_channel_history; you cannot send a file there — Kev can, from the Text pane (Send to Slack)"*; *"WordPress (KVKtheCreator): you cannot publish there — Kev can, from the Blogger pane (Publish)"*. A write tool composed into the live surface renders *"you can post with … (by PROPOSAL — queued for Kev)"* without anyone editing prose.
- `services/primitives/registry.py` — `list_integrations` returns the SAME rows (name · target · captures · reads · agent_writes · member_doors) and its description is rewritten: it no longer advertises the retired commerce/trading connectors or tells the model to "suggest connecting in Settings" as the answer to a send request; it says what each field means and that a send request is pointed to `member_doors`.
- Expected behavior: what the agent is told in its frame, what it finds when it calls `list_integrations`, and what the member reads on Connectors and Reach are one derivation. The frame grows by one line per connection (≈120 chars each; the ratchet holds).

### Why
Operator ruling on the first Reach click-pass: *"agents and display should reference the same status … no different from existing connectors handled by Claude, ChatGPT."* Four faces described one fact; two of them disagreed on screen within an hour of shipping. ADR-635 had already solved it for attached connectors (`attached_surface` → tools + `frame_section` + settings); ADR-644 brings first-party connections onto the same rule.

### Gate
`test_adr644_one_reach_status.py` (the four reach states driven through the generator; the tool result and the LIST route compared row for row against `reach_status`; a write tool patched into the live surface flips every face); `test_adr535_connector_visibility.py`; the ratchets `test_adr632_the_seat_retires.py` §5 + `test_adr630_skills.py`.

---

## [2026.09.07.6] - the reach section names the member's outbound door; an agent asked to send says so and points there

### Changed
- `services/lane_runner.py` — every branch of `connector_reach_section` (scoped-to-nothing · unscoped · scoped · darkened) gains one sentence, DERIVED from `services/publish.py`'s `PUBLISH_TARGETS` + `PUBLISH_VERBS`: *"You cannot send or publish anywhere. {member} can — publish to WordPress · send a file to Slack — from the file's own pane: their click, receipted beside the file. Asked to send something out, say you cannot and point them to that door."* A third tenant names its door here the day it lands; nothing is hand-listed.
- Expected behavior: asked "send this to my Slack channel", the editor still refuses (it holds no write tool — the lane composes read rosters only) but now names the Send to Slack door on the file's pane instead of sending the member to Settings.

### Why
**Observed on the first Reach click-pass (2026-09-07, operator screenshot).** In the Text pane the member asked the editor to send the open document to their Slack channel. The reply was truthful — *"my Slack access is read-only … no way to send a message out"* — and its remedy was wrong: *"worth checking Settings"*. The door exists (ADR-628 amendment 3, shipped the same morning) and it is the member's, on that very pane. The frame had no way to know it: reach prose described what the agent can READ and said nothing about what the member can SEND. ADR-638's register — name the THING — applies to the door as much as to the file.

The same screenshot exposed the mirror defect on Reach: `connector_does` claimed *"an agent's Slack post goes out only through a proposal you approve"* — derived from the capability registry, which still carries `write_slack` for the task pipeline ADR-231 deleted. Corrected to derive from the LIVE lane surface (`turn_reach_tool_names`), so both faces now say the same true thing: the agent cannot send; the member can, from the file's pane.

### Gate
`test_adr535_connector_visibility.py` (drives all four reach states); `test_adr642_reach.py` D5 (the derivation reads the live surface — a composed write tool flips the sentence; none composed says "cannot"); the size ratchets `test_adr632_the_seat_retires.py` §5 + `test_adr630_skills.py`.

---

## [2026.09.07.5] - the "scoped to no connections" clause was unreachable; the member got the darkened wording

### Changed
- `services/lane_runner.py` — the ADR-612 D3 branch guard now keys on the PLATFORMS tuple (`_reach_plats is not None and not _reach_plats`) instead of on `_reach`.
- Expected behavior: a member who scopes an agent to NO connection now gets the clause written for exactly that case — *"You have no platform reach in this workspace: {member} scoped you to no connections… they can widen your connections on your agent page"* — instead of the deployment-darkened clause, which offers *"they can paste it, or export and drop the files into the commons"* and never names the one remedy that applies. No other reach state changes; the frame's other three branches are byte-identical.

### Why
**Observed in the gate, not speculated.** `test_adr535_connector_visibility.py` was 2/21 red at baseline. Re-cutting it to drive all four documented reach states showed the two no-reach states rendering the SAME paragraph, which sent me to the guard.

The branch required `(True, ())`. `resolve_turn_reach`'s own docstring declares that state impossible — *"`(True, ())` is unreachable and deliberately so: an agent scoped to no platform has nothing to reach"* — and the function returns `(False, ())` there. So the guard asked a question that could not separate the two states it was written to separate, and the branch had never executed. The distinguishing fact is the platforms tuple: `()` scoped-to-nothing versus `None` darkened.

The prose being withheld is the honest one. A member who deliberately narrowed an agent was told connections are unreadable in general — false — and offered a workaround for a limit they themselves set and can lift in one click.

### Gate
`test_adr535_connector_visibility.py` re-cut: 35/35 (was 19/21). Its D3 section now drives all four reach states by stubbing `resolve_turn_reach`, asserting each states its OWN true edge and does not state one it lacks. The pinned literal `"cannot read through it"` is gone: ADR-615 gave the lane nine `platform_*` read tools, so that sentence became FALSE for the two reach-bearing states and the gate was red against live-correct prose. Falsified: reverting the guard re-fails the two scoped-to-nothing assertions; claiming "cannot read through" in the scoped branch re-fails the scoped-to-slack pair.

---

## [2026.09.07.4] - the cadence is read in the WORKSPACE's clock, not UTC

### Changed
- `services/skills/declaring-standing-work/SKILL.md` — the `schedule:` comment said `# UTC cron`. It has not been UTC since migration 247 (ADR-596 D4): a cron resolves against `workspaces.timezone`, UTC only as the fallback when none is declared. Corrected, and step 4 gains one line telling the agent to take a member's named time as their own clock and say which one it wrote.
- Why (observed, not speculative): production's one standing declaration read `0 13 * * *` and fired at 04:00 UTC every day. Both are correct — the workspace is `Asia/Seoul` (UTC+9) — but nothing on the declaration, the roster or the pane said so, so the two numbers looked like a bug for a fortnight. An agent following the skill would have written 13:00 meaning UTC and silently produced a 9-hour shift.
- Expected behavior: an agent writing a declaration states the clock when confirming the cadence. No change to how any schedule RESOLVES — `compute_next_run_at` was always right.
- Size: +1 line of body. Index unchanged (the `description` is untouched), so no ceiling moves.
- Gate: `test_adr630_skills.py` (index ceilings) + `test_adr639_standing_work.py` green.

---

## [2026.09.07.3] - `assembling-a-composite-document` measured null → rank 2; the declaring skill names what a slice reads

### Changed
- `services/skills/__init__.py::_INDEX_RANK` — `assembling-a-composite-document` → **2 (measured-null)**. It shipped rank 1 (unmeasured) on 2026-09-07; measured the same day. Composed index sizes move only in ORDER; no ceiling touched.
- `services/skills/declaring-standing-work/SKILL.md` — one sentence in the tuning paragraph: a connector slice captures exactly what the CONNECTION reads (the roster and the connection's card state it; a GitHub slice is issue + PR activity, not a commit log), and a file that needs what the connection does not read has no source there. `description` unchanged, so every index is byte-identical.

### Why
**The measurement** (`docs/analysis/assembling-a-composite-document-measured-2026-09-07.md`). 24-row CSV + notes; the ask names the skill's subject word for word (*"a one-page report for the all-hands where the numbers matter as much as the words"*); ARM A = live index, ARM B = the slug withheld from the kernel index in-process; n=3/arm, interleaved, each in its own folder, purged after (18 rows → 0).

```
rows_copied_fraction (pre-registered, A<B):  A 0.292/0.250/0.292 (0.278)   B 0.292/0.250/0.333 (0.292)   p = 0.500
read the skill:  A 0/3   B 0/3          provenance line (posture):  A 2/3   B 3/3
```

Both arms wrote the same document: a 3-row Q3 table under the provenance line, the quarter set against Q2 and the prior year in prose, and a standup figure explicitly marked as *not* from the metrics file. **The craft the skill teaches is the model's own.** The ask matched the description literally and the body was still read 0/3 — the Part M finding again (*the description already states the craft, so the lane conforms without reading it*). Its CONTRACT half — the provenance line — is the part that moved anything, and that now lives in `text_pane_posture` (`[2026.09.07.2]`, 3/3 vs 0/2).

Kept, not pruned: a skill is never pruned on a quality score because its failure is silent — but the failure this one guards ("the whole table copied into prose") did not occur in the untreated arm either, so it earns the measured-null rank and no more.

**The declaring skill.** Part P found that a GitHub slice cannot observe a commit-only repo: the binding reads issues + PRs. The `reads` statement is now served on the standing roster (`routes/standing_work.py::StandingSource.reads`) and the skill tells the declarer to check it before declaring — craft with its consequence, no per-connector string duplicated into prose.

### Expected behavior
Text lanes: `assembling-a-composite-document` still listed (the text index has room) but last in admission order; unbound lanes: it moves into the overflow count first if the roster grows. Declaring lanes: a member asked to keep a file current from a connector is told what the slice reads when it does not match the file's need.

---

## [2026.09.07.2] - The Text posture carries the markdown reference forms

### Changed
- `services/apps/text.py::build_text_posture` — ONE new bullet (+584 B; the posture composes at 1,933 B with an empty head): markdown refers to three things by keeping their content IN the file — an image by workspace path (`![alt](path)`, never a URL or base64), a diagram as a ```mermaid fence, and figures from a CSV as a real markdown table under a provenance line (`_From `path` · snapshot YYYY-MM-DD_`). The bullet carries the CONSEQUENCE, not just the rule (the Part R lesson): the line IS the citation, so no figure appears without its source and the next reader knows where to refresh it. It also states that an HTML citation (`data-ref`) is inert in a `.md` — the one form a lane that has seen the Studio grammar might reach for.
- `test_adr571_text_app.py` — §2d/2e assert the three forms + the refusal are composed; §2f adds the posture's first byte ceiling (2,100; measured 1,933 at ship).

### Why
**A repeated, observed failure — n=2 on one fixture plus the operator's live report.** Two bound Text runs (2026-09-07, `docs/analysis/composing-an-image-in-a-bound-lane-2026-09-07.md` postscript) asked to *"write the Q3 platform review into the bound document"* both retyped the CSV's figures (1,850 / 2,310 / 3,040) into a markdown table and cited the source file nowhere. That is EXACTLY the shape the Text toolbar's own `csvToMarkdownTable` writes — ADR-572 D18 ruled that a CSV in markdown is a SNAPSHOT — minus the provenance line D18 makes the snapshot honest with. Measured before this change: the posture named none of `mermaid` / `![` / `csv` / `snapshot`; the lane frame, the standing frame and the connector carry only `derived_from`; the `.md` grammar lived in three FE insert functions where no engine could read it. The `.html` grammar, by contrast, is a kernel constant (`PARTICIPANT_ARTIFACT_CITATION_RULE`, ADR-617 D2) handed to every write-capable surface.

**Why the posture and not a kernel constant.** ADR-606 D3: the posture is where an app says how its artifact works, and Text is the only app whose artifact is `.md`. The promotion test was run first: five connector-authored `marketing/strategy/*.md` were read for the same failure and every figure-bearing one names its sources near the figures (the connector's host already does this). No evidence for a kernel clause; a clause in every turn needs one.

**Why it is not the skill's job.** `assembling-a-composite-document` step 3 says *"name the source of every figure, inline"* and neither drive reached it (the index reaches a skill when the ask names its subject; "write the review" does not). The skill keeps the JUDGMENT (what earns a table, keep the copy small); the posture carries the SHAPE — the same partition Part Q settled for the block grammar, applied to the one app it was mis-applied to.

**The failure is silent** — a retyped figure looks perfect and drifts the moment the source moves — which is the arc's own profile for a contract rather than craft (`services/skills/__init__.py` docstring).

### Expected behavior
Bound Text lanes: a document that lifts figures from a CSV writes them under the `_From … · snapshot …_` line; asked for a diagram, the lane writes a mermaid fence rather than a table or an HTML chart; asked to place an image, it writes `![alt](workspace/path)`. Validation: driven on prod against the same fixture as the two failing runs (see the handoff Part S for the receipt). Unbound lanes, Slides/Images/Blogger: byte-identical.

---

## [2026.09.07.1] - `composing-an-image` measured bound; the index admits by evidence

### Changed
- `services/skills/composing-an-image/SKILL.md` — step 2 now carries the CONSEQUENCE of the `data-z` rule (an unstamped layer sorts by document order, so the member's layer rail has no authored value to move), not just the rule. The "Layers stacked at the same `z`" anti-pattern is REMOVED: it contradicts ADR-633 §5b, which ruled a tie legitimate (production's own artboard carries 5 distinct z across 10 layers).
- `services/skills/assembling-a-composite-document/SKILL.md` — NEW, `text`-scoped, **UNMEASURED** (rank 1). A prose document that has to carry figures: what earns a table, and keeping every number traceable to the file it came from. ⚠️ Its first draft was written against the 18-kind block grammar and was WRONG — `text_pane_posture` is a plain-prose posture (1,347 B, *"No block grammar, no Studio machinery"*), and Text owns no artifact layout at all; the block roster belongs to slides/images/blogger. Rewritten for prose against an observed failure: two bound Text runs retyped a CSV's figures into a markdown table with the source uncited, and neither reached the skill from its index line.
- `services/skills/__init__.py` — the index now admits kernel skills by EVIDENCE rank (`_INDEX_RANK` / `_index_rank`), alphabetical only as a tiebreak. The docstring's ⚠️ on `composing-an-image` is replaced with the measured result.
- `test_adr630_skills.py` — new §3a-rank (with an in-process falsification: demote `writing-a-spec` → it is evicted → restore → it returns). Two assertions in §3/§3b that read "the index lists every kernel skill" are corrected to the invariant they meant — every skill is LISTED **or** COUNTED, with the ListFiles that reaches it.

### Why
**The bound-lane probe (the Part Q owed item).** `composing-an-image` defers its token grammar to the pane posture, which composes only for an artifact-bound lane, so the earlier probe could not score it. Re-run bound (n=3/arm, one pre-registered measure — the fraction of blocks carrying all three of `data-x`/`data-y`/`data-z`):

```
ARM A (index)   1.00 / 0.00 / 0.50     read the skill 3/3
ARM B (none)    0.00 / 0.00 / 0.00     read the skill 0/3
```

Discovery is total; compliance is not. **p = 0.200 — it does NOT clear the n=3 floor of 0.100**, because trial 2 read the skill and stamped nothing. The trace says why: the agent stamps `data-z` exactly when layers OVERLAP and omits it otherwise — coherent visual reasoning, and wrong, because the rule serves the layer rail rather than the picture. **A contract skill must carry its consequence, not just its rule**; an unmotivated unconditional rule loses to visible local reasoning. That is the amendment.

**The ranking.** The index is a byte budget with a truncating tail, so something decides which skill loses its line — and it was the directory alphabet. `UNBOUND_INDEX_CEILING` has been raised TWICE to undo the result (its own comments name both occasions), and the twelfth skill reproduced it a third time by evicting `writing-a-spec`, the skill with the strongest measured evidence in the set (7/7/7 vs 1/0/2). Raising the ceiling again buys one skill and leaves the next eviction just as arbitrary. Ordering by evidence makes the budget shed measured-null rows first — and because a withheld row is a REACH loss (100% listed vs 58% via ListFiles), that is the same argument the ceilings themselves now carry. **No ceiling was raised.**

### Expected behavior
Bound Images lanes: the `data-z` rule is now motivated, so expect stamping on non-overlapping layers where the agent previously skipped it. Bound Text lanes: `writing-a-spec` and `deriving-a-design-system` are listed ahead of the craft skills, and the new composite-document skill is offered; `summarizing-sources` and `writing-updates` move into the overflow count (still mirrored, still reachable by ListFiles). Composed sizes, all under ceiling and none raised: unbound 3,819/4,000 · text 3,199 · slides 2,762 · images 1,750 · blogger 2,762.

Capture: `docs/analysis/composing-an-image-in-a-bound-lane-2026-09-07.md`.

---

## [2026.09.04.3] - What a skill is FOR: contract, not craft (measured)

### Changed
- `services/skills/creating-skills/SKILL.md` — NEW section "What makes a skill worth writing", between "What a skill is here" and "Steps". Tells an author to write for what a capable model could not work out on its own — this workspace's own shapes (the file a tool looks for by name, the attribute a renderer reads, where a number must live) — and names the test: *if the answer to "what goes wrong without this" is "the output is a bit worse", the skill is optional; if it is "the output looks right and does not work", write it.* The `description` frontmatter is UNCHANGED (296 B), so every index ceiling is byte-identical (unbound 3,947/4,000 · text 3,101 · slides 2,762 · images 1,750 · blogger 2,762).
- `services/skills/__init__.py` — module docstring gains the measurement and its consequence; the `INDEX_CEILING` comment gains the three-arm receipt.

### Why
An A/B against live production (index composed vs suppressed, one pre-registered measure per skill taken from its own SKILL.md before any data existed) split the eleven kernel skills cleanly:
- **Separate**: `writing-a-spec` (7/7/7 prescribed sections vs 1/0/2, p=0.100 — the exact-permutation floor at n=3) · `deriving-a-design-system` (15/18/17 kernel CSS variables vs 7/0, p=0.100) · `presenting-from-sources` (CSV beside the deck).
- **Null**: `reviewing-drafts`, `writing-updates`, `comparing-options`, and the three measured earlier (`summarizing-sources`, `keeping-a-file-current`, `declaring-standing-work`).

The separating skills all carry a shape the model has no prior for, and their failure is SILENT: `design_systems.py` discovers a system BY `_design.yaml`, so a folder without it is invisible while looking like a plausible folder of CSS. A skill therefore cannot be pruned on a quality score.

A second A/B tested replacing the ~3.3 KB per-skill roster with a 360-byte pointer ("list `system/skills/` and read the one that matches"). Reach fell 100% → 58% (p=0.038) and the pointer proved **indistinguishable from no index at all** (p=0.682); ARM T produced the contract only on the run where it happened to read the skill. The roster stays.

### Expected behavior
No change to any composed frame. This edit changes what a member or agent is told when they AUTHOR a skill, and records why the ceilings are set where they are (a future cut is argued against reach-rate, never byte count).

Capture: `docs/analysis/what-a-skill-is-for-contract-vs-craft-2026-09-04.md`.

---

## [2026.09.04.2] - Standing work is a kernel lane: the standing run composes through the lane module; craft is a skill (ADR-639)

### Changed
- `services/lane_runner.py` — NEW `build_standing_frame` + `_STANDING_FRAME`, beside `build_lane_conventions`: the unattended run's system prompt, composed from the SAME constants (commons contract, citation rule, mandate head) and the same character door (`build_agent_posture`), minus what a toolless run and an absent principal make false (no tools line, no reach section, no cast, no focus, no register clause, no skills index), plus the kernel JOB and the craft skill's BODY (push door — a toolless turn cannot ReadFile). Scaffold 430 bytes (ceiling 600, `test_adr639` §D1).
- `services/standing_work.py` (was `services/strings.py`) — `_STANDING_RUN_POSTURE` (~1,600 bytes composed into every prose run) and `_STANDING_PANE_FRAME` (~3,000 bytes composed into every strings-pane turn) are DELETED. What stays in code is `_STANDING_JOB` (527 bytes): the per-run facts and the OUTPUT CONTRACT (return the full file or exactly `NO_CHANGE` — the sentinel is parsed, so it is a machine contract, not craft). The run's system prompt is `build_standing_frame(...)`; it never composes a string of its own.
- `services/skills/keeping-a-file-current/SKILL.md` — NEW, `apps: [text]`. The run posture's craft as a skill: fold don't append, prune what stopped being true, preserve the member's corrections, cite each new claim inline, name a source/contract disagreement plainly, answer NO_CHANGE honestly. The standing run composes its body by binding; a Text turn on a kept file sees it in the index.
- `services/skills/declaring-standing-work/SKILL.md` — NEW, universal. The pane posture's lifecycle as a skill: the three files, the strict `_standing.yaml` grammar (with the new optional `app` key), read-it-back, contract before cadence, never invent a source URL, pause/re-source/tighten, the law (only the designated target is ever a standing writer's target).
- `services/apps/__init__.py` · `services/agents_registry.py` — the `strings` app registration and its pane posture, and the `supervisor` agent row, are DELETED (ADR-639 D4). No frame composes a Supervisor character anywhere.
- Why: the standing run composed a SECOND envelope outside the one composition site (no commons contract, no citation rule, no mandate head — lost without a decision), the skills loader had no seam into it (ADR-630 §3 named and deferred exactly this), and the craft it needed lived as Python prose whose own comment called it "job instruction all along". Supervisor was a posture string with no mechanics; ADR-610's rule (a being is someone a member MEETS) retired it once declaring became craft any resident holds.
- Expected behavior: a prose declaration's run now sees the workspace's mandate head and the citation rule, is told affirmatively that it reaches nothing live, and reads the craft from the same skill a Text turn would. Executor derives from the target's type (prose → text → Editor) — no run is ever attributed to or costumed as Supervisor. Ledger rows stamp `standing-write:` / `standing-sweep:` with `funnel_decision='standing'` (migration 251 carried the value BEFORE this deploy); the revision attributes `system:standing`, message "kept 'x.md' current (standing run, N sources)".
- Index budgets, measured at ship with the two new skills: the BOUND ceiling (3,000) HELD on every pane — text 2,779 · slides 2,762 · blogger 2,762 · images 1,750. The OPEN lane's ceiling is RAISED 3,400 → 3,800 (measured 3,735 with all eleven listed): at 3,400 the open index withheld the eleventh skill by alphabetical accident — the outcome ADR-633's amendment sized that number to prevent — and the receipt for raising is the trade itself: ~4,600 bytes of always-composed Python posture leave the frames; two discovery-grade index lines (~680 bytes) arrive in the open lane. Net prose composed per turn falls.
- Gates: `test_adr639_standing_work.py` (new) · `test_adr632_the_seat_retires.py` §5 ratchets unchanged (conventions scaffold 683/900, studio posture unchanged) · `test_adr630_skills.py` (11 kernel skills, every lane under its ceiling).

---

## [2026.09.04.1] - ADR-638 — the agent speaks the member's language

### Added
- `services/workspace_paths.py`: `PARTICIPANT_REGISTER` — the register clause, a
  new sibling of `PARTICIPANT_FILESYSTEM_MODEL` / `PARTICIPANT_FORMAT_DISCIPLINE`
  (ADR-533 D1: authored once, composed per surface).
- `services/lane_runner.py`: composed into `_CONVENTIONS_FRAME` as
  `## Talking to {member}`. Scaffold 666 → 683 chars (ceiling 900, unchanged).
- Expected behaviour: replies name the THING, not its mechanism ("I moved the
  headline down and made it bigger", never `y:58% → y:66%, z:5`); lead with what
  changed; use the member's nouns. The agent still authors the real grammar —
  only the ADDRESS is constrained (ADR-365 D5 preserved).

### Why (the observed failure — ADR-306 requires one)
120 consecutive live assistant replies: 11 named a raw tool (`ReadFile`), 6
quoted `data-*` grammar, 3 named block ids, 1 rendered a table of `y:82%` →
`y:86%`, `(z:5)` — the operator's screenshot. The discipline already existed for
tool names (`toolLabels.ts`) and paths (Documents/Downloads) but not for prose.
ADR-365 ratified and validated this rule in June 2026; it died with the steward
(ADR-632) and the lane frame never carried one.

### Validated
`scripts/operator/probe_adr638_register_ab.py`, 2 runs (3+6 trials/arm, Sonnet 5):
clause present 0.00 leaks/reply and 9/9 clean; stripped 2.08 and 1/9. Replies also
fell 177 → 63 words with no length rule asked for.

## [2026.09.03.4] - The artboard is a stack of layers (ADR-633)

### Changed
- `services/authoring.py` — four new BLOCK-scope tokens at the `artboard` grain: `opacity` (75/50/25), `blend` (multiply/screen/overlay), `lock`, `hide`. Each carries one kernel CSS rule per declared value; `normal` blend is the absence-default and is deliberately NOT declared (a declared-but-unstyled value writes an attribute that renders nothing — the ADR-461 B1 defect).
- `services/authoring.py` — `STUDIO_KERNEL_CSS_VERSION` 19 → 20. Additive (four new attribute selectors, nothing changed or removed), but the bump is REQUIRED: a stored artifact carries its kernel style element inline, so an un-bumped version leaves every existing IMAGES stage with a pane that offers opacity and a canvas with no rule to render it.
- Why: the IMAGES property model was entirely document-native — the whole registry is heading/prose/callout/table/figure and the tokens are size/align/indent/tone. There was not one layer-native property, on a surface whose purpose is composing overlapping objects. `figure` is a document's idea of a picture (a cited image with a `<figcaption>`), not a layer.
- Expected behavior: the studio posture for `image` now describes opacity/blend/lock/hide to the authoring hand, so a generated composition can set a scrim to Multiply or drop a background to 50% rather than only placing opaque rectangles. The deck posture is UNCHANGED — the grain is `artboard`, so a deck block cannot acquire a layer property by grain widening (gated: ADR-633 F4). Posture length for `image` is 17,901 bytes, inside the ADR-632 §5 studio ceiling (ratchets 73/73).
- Gate: `test_adr633_the_artboard_is_layers.py` (all checks) — asserts the narrow grain on all four rows, a kernel rule for every declared value, the absence-default convention, and that `hide` renders `display: none` (never `visibility: hidden`, which would leave the layer occupying the coordinate space a member is trying to reach through).

---

## [2026.09.03.3] - Attached connectors reach the lane; the strip is named (ADR-635)

### Changed
- `services/lane_runner.py` — the connector-reach section gains an ATTACHED SERVERS paragraph when the member holds attached connectors with a non-empty aperture: each server, its `mcp__{slug}__{tool}` names, and which run DIRECT versus by PROPOSE, with the rule that a PROPOSE call does not run (it is queued for the member) and must not be retried. Composed from `services/attached_connectors.frame_section`; absent when there is nothing attached, so every existing frame is byte-identical.
- `services/attached_connectors.py` — tool DEFINITIONS carry the server's own `inputSchema`; the description is prefixed with the server's title and suffixed with the mode ("Runs directly in this turn." / "Each call is queued as a proposal the member executes.").
- `services/skills/__init__.py` — the index withholds a skill whose `metadata.needs` names a connector category the member has not attached (counted, reachable by ListFiles — presentation only). `parse_skill` NAMES the host-specific frontmatter it strips (`allowed-tools`, `model`, `argument-hint`…) instead of dropping it silently.
- `services/skills/creating-skills/SKILL.md` — teaches `metadata.needs` and says that a pasted host skill's `allowed-tools`/`model` are ignored here.
- Why: a member can now attach any MCP server from the consumed directory (ADR-635). The model must know what it holds and how each tool behaves — a PROPOSE tool that "fails" is the queue working, not an error. Observed on the trio (ADR-535): a model handed an inventory infers reach it does not have; naming the edge is part of granting it.
- Expected behavior: with nothing attached, no frame changes. With an attached server, the lane calls its DIRECT tools as it calls `platform_*` reads, and says "queued for you" on a PROPOSE tool rather than retrying. A skill needing "Project tracker" appears once Linear/Asana/Jira is attached.
- Gate: `test_adr635_attached_connectors.py` (§6 the frame; §8 the skills); `test_adr632_the_seat_retires.py` §5 ratchets unchanged (the addition is conditional on attached rows).

---

## [2026.09.03.2] - The Images pane gets its craft, and the kernel index gets a real budget (ADR-633)

### Changed
- `services/skills/composing-an-image/SKILL.md` — NEW, `apps: [images]`. The composition craft: build the stack bottom-up with an explicit `data-z` on every layer, place by coordinate (both `data-x` and `data-y` — one without the other is not positioned), earn legibility before styling, three type sizes not five. Quality bar leads with the THUMBNAIL TEST. Anti-patterns name the document habits that were leaking onto artboards (prose blocks, centring everything, text straight onto a busy photo).
- `services/skills/{comparing-options,reviewing-drafts,summarizing-sources}/SKILL.md` — declare `apps: [text, blogger, slides]`. Their product is a written brief, critique or decision table; an artboard and a standing string have no use for them.
- `services/skills/__init__.py` — the KERNEL index is now bounded at COMPOSITION, not only by a gate. Two ceilings: `INDEX_CEILING` (3,000) for a bound pane, new `UNBOUND_INDEX_CEILING` (3,400) for open chat. Withheld lines are named with a count + `ListFiles system/skills/` — the escape hatch the member half already had.
- Why: the Images pane was offered six skills and ALL SIX were document skills (compare options, review drafts, summarize sources…). There was no skill about composing an image at all — the §1.4 document-native defect surviving in the frame after the inspector was fixed. Separately, adding a ninth skill put the unbound index at 3,239/3,000: the kernel budget was gate-asserted but composition-ignored, so the open lane could walk straight past it. A ratchet a gate asserts and composition ignores is not a ratchet.
- Why TWO ceilings rather than one raised: ADR-630 §3b states that the open surface is where a member goes for any kind of work and narrowing it hides work with no other door. Truncating it dropped `writing-a-spec` and `writing-updates` by alphabetical accident — worse than the bytes saved. A bound pane, where scoping already does the work, keeps the tight bound.
- Expected behavior: an Images lane now sees `composing-an-image` and no longer pays for three document skills — 2,415 → 1,390 bytes (−42%). Slides/Text/Blogger unchanged at 2,396/2,722/2,396. Open chat still lists all nine (3,239/3,400). A bound pane's frame cannot silently grow past its ceiling on either axis.
- Gate: `test_adr630_skills.py` 117/117 (was 107) — each lane measured against ITS OWN ceiling, plus falsifiers that a pathological 20-skill kernel self-truncates, names what it withheld, and reports a truthful count.
- Fixed in passing: two hand-pinned counts in that gate (`len(K) == 8`, `written == 8 and writes == 9`) read the ninth skill as a violation. Both now derive from the roster — a count cap pinned by hand reads GROWTH as a defect.

---

## [2026.09.03.1] - The lane frame is cacheable (ADR-634)

### Changed
- `services/model_router.py` — new `_system_payload(system, model)`; both `route_completion` and `route_completion_stream` now carry the system prompt as a cache-marked content block (`cache_control: ephemeral`) when the model supports it, else the plain string as before.
- Why: the frame is built ONCE per turn but re-sent on EVERY round of the tool loop (up to 5), so the same ~4,400 tokens were billed as fresh input up to five times. `services/anthropic.py` had carried the prompt-caching beta header all along and no live path ever sent a marked block; the ledger already normalized and priced cache tokens.
- Expected behavior: NO change to what any model is told — the frame text is byte-identical on the wire for every provider. Anthropic turns now report `cache_read_tokens`; a one-round turn costs ~25% more (the 1.25x write), a two-round turn wins, and the blend over 500 real production turns is a ~46% saving on frame bytes.
- Provider safety established by execution, not by reading source: LiteLLM preserves the marker for Anthropic (hoisting it into `system`) and STRIPS it for the OpenAI-compatible and Gemini transforms, with the prompt text intact in all three.
- Gate: `test_adr634_prompt_caching.py` 28/28 (new; run on the py3.9 venv). Falsified two ways — reverting either call site fails §3, removing the capability guard fails §1.

---

## [2026.09.02.4] - The skills index is scoped by app (ADR-630 amendment)

### Changed
- `services/skills/__init__.py` — `skills_index_section(..., app=)` filters the index by a new `metadata.apps` frontmatter key; `parse_skill` lifts it out as a tuple (the rest of `metadata` still stringifies, so a list there would have become `"['slides']"`). `read_member_skills` carries `apps` through, so a member's skill scopes exactly like a kernel one.
- `services/lane_runner.py` — passes the lane's `app` (already resolved for the posture) into the index.
- `services/skills/{presenting-from-sources,writing-a-spec,writing-updates}/SKILL.md` — declare `apps: [slides]`, `[text]`, `[text, blogger]`. The other five stay undeclared and therefore universal.
- Why: the index was identical for every lane, so a Slides pane paid ~330 bytes to advertise `writing-a-spec` and an Images pane paid for the deck skill. The frame already knows the app.
- Expected behavior: a bound pane's frame shrinks — 2,968 bytes open, 2,414 in Slides, 2,085 in Images (−18% to −29%). An unbound lane (open chat) is unchanged and still sees all eight. Withheld skills are named with their count plus `ListFiles system/skills/`, and the mirror is untouched: all eight still land in every workspace and any of them reads fine (presentation, not authorization — ADR-395).
- Gate: `test_adr630_skills.py` 104/104 (was 91) — §3b falsifies both directions (a slides pane HAS the deck skill, an images pane does NOT; an undeclared skill is offered everywhere; an unbound lane is offered everything; a member skill scopes and is withheld the same way; the hidden count matches what was withheld; `apps` parses as a tuple, and a bare string is accepted).

---

## [2026.09.02.3] - The skills index is bounded in bytes, not lines (ADR-630 amendment)

### Changed
- `services/skills/__init__.py` — `skills_index_section` now enforces its budget at composition. `INDEX_CEILING` (3,000) is restated as the KERNEL ratchet; new `MEMBER_INDEX_ALLOWANCE` (2,700) bounds member lines in bytes, admitting them while they fit and naming the remainder as a count the agent follows with `ListFiles skills/`. `MEMBER_INDEX_CAP` is now documented as a bound on the QUERY, not on the frame.
- Why: the ceiling was gated but never enforced, and was measured against the kernel index alone. The kernel sits at 2,968/3,000, so ONE realistic member skill produced a 3,228-byte index and twenty-four produced 9,222 — composed into every turn of every lane in that workspace. The gate passed because its member fixture used one-character descriptions; a description written for discovery is ~330 bytes. Production held zero member skills, so this was latent and would have fired on first use of `creating-skills`.
- Expected behavior: no change for workspaces without their own skills (the kernel index is byte-identical at 2,968). A workspace with member skills gets up to ~8 of them in the frame and a "…and N more under skills/" line for the rest, instead of an unbounded index.
- Gate: `test_adr630_skills.py` 91/91 — the member checks now measure BYTES with a discovery-grade description, assert the truncation count, and falsify both ways (400 skills cost the same as 10; one member skill is admitted, not dropped).

---

## [2026.09.02.2] - The steward's prompt layer retires (ADR-632)

### Changed
- `agents/freddie_agent.py`, `freddie_agent_sections.py`, `occupant_contract.py`, `cockpit_awareness.py`, `services/freddie_envelope.py`, `services/model_selection.py` — DELETED with the wake stack. The steward's system prompt, envelope, trigger framing, and per-shape model table no longer exist.
- `services/primitives/registry.py` — the three LLM rosters (CHAT/HEADLESS/FREDDIE_PRIMITIVES) and the `Clarify`, `GetSystemState`, `FireInvocation`, `Schedule`, `ManageHook`, `Compose`, `Mirror*` tool definitions are deleted; `PRIMITIVES` is the derived dispatch-side list.
- The live frame is unchanged: `services/lane_runner._CONVENTIONS_FRAME` + the app postures + the ADR-630 skills index. Its ratchets now live in `test_adr632_the_seat_retires.py` §5 (conventions scaffold 666 chars measured, ceiling 900; studio posture frame 10,566 measured, ceiling 11,000).
- Expected behavior: no model call fires without a member's turn or a standing declaration's schedule. Chat, panes, skills, strings, capture and interop are unaffected.

---

## [2026.09.02.1] - Skills are files (ADR-630): the frame gains an index, the recipes become SKILL.md

### Changed
- `services/skills/{slug}/SKILL.md` (new, 8): `summarizing-sources` · `writing-updates` · `writing-a-spec` (was the `prd` recipe, body verbatim) · `presenting-from-sources` (was `deck`, body verbatim + one craft line: numbers on a slide are cited data) · `reviewing-drafts` · `comparing-options` · `deriving-a-design-system` (was `design-system`, body verbatim) · `creating-skills`. Every description is third-person, what + when, ≤300 chars.
- `services/lane_runner.py`: every lane's frame gains `## Skills` — one index line per skill (kernel from code, member from one bounded query). Bodies never enter the frame; the agent reads a skill on demand. Kernel index ceilinged at `INDEX_CEILING` (3,200 chars; measured 3,0xx at ship).
- `services/skills.build_skill_section` replaces `derive_recipes.build_derive_section` — same shape; the write's `derived_from` now names the skill path beside the source, so an output cites the craft it was made under.
- `services/derive_recipes.py` DELETED.
- Expected behavior: a lane at any pane can find and follow a kind-of-work skill without a binding; a Learn-from lane composes the same body it did before; the ledger can answer "which files were made under this skill".
- Falsification: index over ceiling → gate red; a body in the index → red; a skill naming a resident → red.

---

## [2026.08.31.1] - The authoring budget must hold a thinking run AND a document

### Changed
- `services/authoring.py`: `STUDIO_LANE_MAX_TOKENS` **8192 → 32000**, with the
  measurement table inline. This ceiling is shared by EVERY bound lane
  (slides · text · images · derive recipes) via `lane_runner._studio_max_tokens`.
- `services/lane_runner.py`: `_LANE_TIMEOUT_S` raised to match the larger
  budget — a bigger ceiling means longer generations, and the old 120s cut them
  off mid-stream (observed as a socket read timeout on the first real drive).
- `services/lane_runner.py`: the round-exhaustion fallback is now a
  member-legible sentence that says the document is UNCHANGED, replacing
  `[lane turn exhausted its round budget without a final reply]` at both the
  streaming and non-streaming sites.
- `test_adr440_studio.py`: the token-profile check is re-anchored from
  `> 2048` to `>= 24576`.
- `probe_studio_deck_quality.py`: two harness defects fixed (see below).

### Expected behavior
- **A bound deck lane can complete "make me a deck" again.** It could not:
  Sonnet 5 thinks by default and thinking bills against this same ceiling, so
  at 8192 the response was cut mid-JSON. Per the write guard's own note,
  truncation "drops `content`, keeps `path`" — so `empty_content_blocked`
  correctly refused every write and the model retried into the 8-round cap.
  The member saw a bracketed internal note and an untouched document.
- Measured (max_tokens → thinking → document chars): `8192 → 8,191 → 0`
  (max_tokens, thinking ate the whole budget) · `16384 → 10,342 → 0` (still
  fails ~1 in 3) · `24576` 5/5 OK · `32000 → 14,580 → 14,544` OK. Thinking
  ranged **1,783–14,580 tokens on identical prompts**, so no ceiling derived
  from a mean is safe; worst-observed thinking + the largest document ≈ 19.5K.
- **This is a cap, not a spend** — a turn bills its actual output, and the
  measured runs finished at 8–21K.
- The prompt envelope itself was found CORRECT and is unchanged: given
  headroom the model obeys the containment law, uses only registry
  arrangements and known block kinds, writes no inline styles and no raw
  colours (ADR-583 D1), and fabricates no citations.
- The probe no longer certifies its own fixture (it now reports `NO WRITE`
  when the artifact is byte-identical to the skeleton — previously it scored
  that as `PARTIAL`), and its id check no longer fails correct decks (it
  counted ids globally, but since ADR-519 a slide carries `data-block-id`
  without `data-block`; a well-formed deck scored `25/19` and FAILED).

---

## [2026.08.28.1] - ADR-615: reach follows the principal, not the surface

### Changed
- `services/turn_reach.py`: `is_turn_reach_enabled()` defaults **ON** when
  `TURN_REACH_ENABLED` is unset (was OFF). The variable survives as an OFF
  switch; an unrecognised value reads as ON, so a typo cannot silently strip a
  capability every workspace is meant to have.
- `services/lane_runner.py` (`resolve_turn_reach`): the turn's SHAPE
  (`app` / `artifact_path` / `derive_recipe`) is **deleted from the
  signature**. Reach is decided by the member and the being alone. Absence of
  an opt-in now means everything granted at every surface, matching ADR-612 D2
  one layer up.
- `services/connectors.py` (`connector_does`): the `agents` capability row is
  flag-derived rather than hard-coded. The old sentence asserted a boundary the
  code did not draw (headless agents DO get capability-scoped `platform_*`
  tools; the ADR-577 refusal is what made the claim true downstream).

### Expected behavior
- **A desk turn now holds the 9 read-only `platform_*` tools.** Previously only
  an open chat turn did, so an Editor at a Text desk correctly reported it had
  no tool to read a repo even with every connector toggled ON. The frame prose,
  the declared payload and the execution allowlist all change together — they
  derive from one `resolve_turn_reach` call (the ADR-585 §5 rule).
- Per-being toggles become purely **subtractive**: `["slack"]` narrows to
  Slack, `[]` means the being reaches nothing (honoured at every surface), and
  absence means everything the member granted.
- **Unattended runs are unchanged and reach nothing live** —
  `run_bounded_derive_turn` is toolless by construction. A clock plus a
  credential stays structurally impossible.
- A darkened deployment (`TURN_REACH_ENABLED=0`) restores pre-585 prose in both
  the frame and the connector capability rows.

## [2026.08.26.2] - ADR-609: the member's selection is an address the colleague can act on

### Changed
- `services/primitives/workspace.py` (`EditFile` tool definition): the verb
  gains an optional `anchor` — `{block_id}` for HTML artifacts, `{start, end}`
  source offsets for prose — and `old_string` leaves the required set. The
  description teaches both modes: anchored WITH `old_string` confines the
  search to the span; anchored WITHOUT it replaces the span wholesale.
- `services/lane_runner.py` (`_seed_line`): a gesture now names the ANCHOR to
  use, not just the target's noun. Previously the line described the thing and
  the colleague had to re-find it by string search against a quoted PREFIX.
- `services/authoring.py` (`_POSTURE_FRAME`): the studio patch bullet teaches
  `anchor={'block_id': …}` for a selected block.
- `services/apps/text.py` (`build_text_posture`): the JOB gains the anchor
  instruction and states outright that the quoted excerpt is a clipped prefix
  which never tells you where the selection ends.
- `services/authoring.py` (`build_focus_line._quoted`) + `_seed_line`: the clip
  marker is idempotent — the capture side now marks its own 120-char clip, and
  a second "…" would describe this cut while implying the text ended at the
  previous one.

### Expected behavior
- Asked to rewrite a selected block or a highlighted passage, the colleague
  passes the anchor and the edit lands on exactly that region. The
  `old_string_not_found` / `old_string_not_unique` failure class — whose
  cheapest recovery was rewriting the whole file — no longer applies to the
  common gesture case.
- The colleague should no longer infer a selection's EXTENT from the quoted
  excerpt. It names the target; the anchor states its bounds.
- Unanchored calls are byte-identical: the trained Claude-Code-Edit prior is
  unchanged, and no existing caller (MCP `edit` included) passes an anchor.

---

## [2026.08.26.1] - Interop delete/move: the grain is resolved on the live tree, and named

### Changed
- `services/mcp_composition.py`: `_names_a_folder` now filters
  `lifecycle in (active, delivered)` — the same filter `compose_list` reads
  with. It asks about the LIVE tree because that is the only tree the fan-outs
  act on (`enumerate_subtree` excludes archived rows by contract). Without it,
  `delete` on an already-trashed folder resolved as a folder, fanned out over
  nothing, and returned `success: True · "0 moved to Trash"` — an incorrect
  success (ADR-373 D6) where the file grain refuses with `file_not_found`.
- `mcp_server/server.py`: the `delete` and `move` roster entries AND their tool
  docstrings now name the FOLDER grain and its sweep. Both said "a file" while
  the code fanned out over a subtree up to `MAX_FAN_OUT` (500). Because interop
  resolves the grain silently (ONE `delete`, ONE `move` — the caller does not
  choose), the verb's prose is the ONLY place the blast radius can be declared,
  which is ADR-337's safety model ("the descriptive names ARE the safety
  model"). The kernel's own `DELETE_FOLDER_TOOL` had stated its radius since it
  shipped; interop had not.
- Expected behavior: a foreign LLM (Claude Desktop, ChatGPT) pointing `delete`
  at a trashed folder now gets an honest refusal instead of a fabricated clean
  sweep; and one pointing `delete`/`move` at a live folder is told, before it
  calls, that the whole subtree travels — with the instruction to say what it
  is about to sweep and confirm for anything beyond obvious scratch. The
  `locked`/`failed` partial-report shape is now named in the prose too, so a
  partial fan is reported rather than narrated as complete.

### Gates
- `test_adr337_interop_folder_grain.py` NEW — falsified against the pre-fix
  tree, 7/7 red, now 11/11 green. It DRIVES `_names_a_folder` through a fake
  query surface (the defect was a MISSING call; a grep for an absent string
  passes for the wrong reason) and pins the GRAIN PHRASE rather than the word
  "folder" — a bare word-search passed vacuously on `move`, whose docstring
  already said "a better folder" about the destination.
- Green: 533 participant-contract · 588 interop-vocabulary · 587 handle-grammar
  · 573 stale-deferral · 512 open/save · 563 scope · 584 whoami ·
  trashed-does-not-read-back · verb-families-are-one-set · prompt ratchets
  (383 + 323, 14 passed).

## [2026.08.25.4] - ADR-579 D7: the gesture line — what the member clicked

### Changed
- `services/lane_runner.py`: `_compose_focus_section` gains the GESTURE —
  when a turn carries a typed seed (a Rewrite…/Check this…/Ask about this…
  door named its target), the frame renders one line before the focus line:
  `- The member's gesture: they clicked Rewrite on the {label} block
  (id {…}) — "{excerpt}". That is this turn's target — act on it, never a
  copy elsewhere.` Same one-site rule (ADR-606 D1), same binding-authority
  guard (a foreign-path seed is silence), same clip-honesty mark. No seed →
  frames byte-identical.
- Expected behavior: a gesture-seeded turn acts on the clicked block by id
  instead of parsing it back out of composer prose — and the member's
  composer no longer carries `(id: bkq3)` flattenings at all (the target
  rides as a typed chip, dismissible, metered marker visible).

### Gates
- `test_adr579_d7_structured_turns.py` new (falsified 4×: stamp dropped,
  guard gutted, prose flattening restored, clear-on-send broken — all red);
  522/606/607 green; ratchets green.

---

## [2026.08.25.3] - ADR-607: the steward hears the typed focus

### Changed
- `agents/freddie_agent.py::_ask_for_trigger` (addressed branch): the ADR-398
  D2 opaque-locator line is DELETED and replaced by two lines composed from
  the operator's TYPED focus (the ADR-522 shape, carried as
  `ChatRequest.focus` → `operator_focus` in the wake context):
  `_The operator is writing from: {app} — {path}_` plus the grain line
  through the SAME `build_focus_line` renderer the lanes use, with
  `actor="The operator"`. No focus → no lines (unchanged silence).
- `services/authoring.py::build_focus_line`: gains `actor` (default
  "The member" — lane copy byte-stable) and lets a declared page noun
  ("slide"/"section") survive without a template, since the steward has no
  artifact to derive one from.
- Carrier chain (supersedes the [2026.08.06.x] locator entry's pinned chain):
  `ChatRequest.focus` (routes/feed.py, `StewardFocus` model) →
  `wake_sources/addressed.stream(operator_focus=)` →
  `wake.stream_addressed_wake` → context bag `operator_focus` →
  `_ask_for_trigger`. The FE composes it from `useCurrentFocus()`
  (ChatDrawer) — the URL-param scrape is deleted.

### Expected behavior
"Tidy up this slide" addressed to Freddie from the drawer resolves the slide
the way a lane turn does; the steward's place line can now carry a grain
(viewing vs selected, heading-as-section) instead of an opaque `k=v` string.
Reactive/scheduled wakes unchanged (no operator standing anywhere).

### Gates
- `test_adr607_steward_hears_focus.py` new (falsified 4×: rendering gutted,
  locator field resurrected, actor hardcoded, scrape resurrected); prompt
  ratchets 18/18; 522/606/562/569/571 green.

---

## [2026.08.25.2] - a clipped focus excerpt says it is one

### Changed
- `services/authoring.py::build_focus_line`: the selection/block excerpt gains
  a trailing "…" when the 80-char clip actually truncated. Found by driving
  production (the ADR-606 click-pass): asked "what do I have selected?", the
  Editor asserted the clip boundary as where the member's selection ENDED
  ("cuts off right after 'first it'") — an unmarked excerpt reads as the
  whole thing.
- Expected behavior: the colleague treats a marked excerpt as the START of
  the selection, not its extent. Unclipped excerpts are byte-identical.

---

## [2026.08.25.1] - ADR-606: the pane sees what the member sees

### Changed
- `services/lane_runner.py`: the member's focus (ADR-522) renders at ONE
  kernel site (`_compose_focus_section`), after the app's job overlay, for
  every lane — bound and unbound. Previously it rendered only inside the
  studio posture, so a Strings pane's declared focus was silently dropped and
  a Text pane never rendered any (the observed failure: "rewrite this
  section" in Text could not resolve — ADR-522's own acceptance case,
  orphaned by the Docs→Text transition). New: a bound lane renders focus only
  when the declaration names the bound artifact (a foreign focus carried in
  by the shell's recency fallback is silence — the binding is the authority).
- `services/lane_runner.py`: the per-app `if/elif` job-overlay chain is
  DELETED — the kernel resolves `posture_for_app(app)` (registered by each
  app, ADR-562's door) with the studio posture as the unregistered fallback.
  Overlay CONTENT is unchanged for all four apps; the studio focus bullet
  moves from beside the outline to the kernel tail.
- `services/authoring.py`: `build_focus_line` gains the `selection` label —
  a raw text range in a prose editor renders as "The member has this text
  selected — '…'", never as a fake block.
- `services/apps/text.py`: `build_text_posture` is pure — the head is the
  kernel's once-per-turn read, its private duplicate re-read deleted.

### Expected behavior
"Tidy this up" / "rewrite this section" in the Text and Strings panes now
resolves against the member's caret section or held selection without asking.
Studio/Images behavior unchanged except the focus bullet's position in the
frame. No focus declared → frames byte-identical to before.

### Gates
- `test_adr522_focus_declaration.py` re-anchored (falsified 3×: guard gutted,
  kernel call deleted, selection branch deleted); `test_adr606_pane_sees_the_member.py`
  new (falsified 3×); `test_adr562/569/571` re-anchored; ratchets green.

---

## [2026.08.21.7] - the same act, at both grains

### Changed
- `services/folder_organize.py`: `trash_folder` / `restore_group` now call
  `archive_live_file` / `restore_live_file` — the same acts a single-file
  delete/restore uses. Each previously carried its own write.
- `services/authored_substrate.py`: `restore_live_file()` (the peer of
  `archive_live_file`) + `_head_content_form()` — the ADR-427 head-blob rule,
  once. Three near-identical private copies deleted (`routes/documents.py`,
  `services/folder_organize.py`, `services/primitives/folder.py`).
- **Fixed: a moved folder left a ghost in Trash.** `move_folder` archived the
  source MARKER, so moving a folder put an empty folder the operator never
  deleted into Trash — and `Restore` would have brought it back at the OLD
  path. The marker now tombstones-and-removes, like the files it contained.
  A move is not a deletion at EITHER grain.

### Expected behavior
Delete/restore mean one thing whoever calls them and whatever the grain. Trash
holds only what the operator actually deleted.

### Gate
- `test_trashed_file_does_not_read_back.py` 21/21 (extended: one act each, no
  private head-blob copies, a move never archives). Falsified both ways.
  Round-trip verified live at folder grain: create → DeleteFolder → in Trash →
  Restore → active; and MoveFolder leaves its source EMPTY, not archived.

---

## [2026.08.21.6] - one delete, one meaning — and Trash gets a Put Back

### Changed
- `services/authored_substrate.py`: `archive_live_file()` — THE delete act.
  `DeleteFile` and the Files route both call it, so the operator's click and an
  agent's tool call are one act with one recoverability.
- `services/primitives/workspace.py` `handle_delete_file`: ARCHIVES (row kept,
  `lifecycle='archived'`) instead of removing the live row. `delete_live_file`
  stays — still correct for MOVE, whose source row must genuinely go.
- `ReadFile` + MCP `open`: a trashed path answers **"is in Trash (moved
  {date}), as part of the folder {root}"** via `describe_if_trashed`, never
  "File not found". MCP `open` was ALSO still serving trashed content to
  foreign callers — fixed in the same edit.
- `services/primitives/folder.py`: **`Restore`** — one verb, both grains, on
  every surface (lane · chat · steward). Bound to `restore_group` /
  revert-as-write, gated like the deletes it undoes.
- `_abs()` now shares `folder_marker_path`'s grammar. It produced
  `/operation/…` where the ledger keys are `/workspace/…`, so a folder verb on
  a relative path silently matched nothing.

### Expected behavior
An LLM that deletes a file puts it in **Trash**, says so, and can put it back.
Asked where a deleted file went, it now reads a state instead of an absence —
previously it answered *"the file is still live — I read it directly"*, because
delete meant two different things depending on who asked (measured: 27 archived
rows vs 13 row-removal tombstones) and a trashed path reported "not found".

### Gate
- `test_trashed_file_does_not_read_back.py` 15/15 (extended with §6 — the
  unification), `test_verb_families_are_one_set.py` 32/32 (the `trash` family).
  Falsified; round-trip verified on live substrate, text AND binary.

---

## [2026.08.21.5] - a trashed file does not read back

### Fixed
- `services/workspace.py` `UserMemory.read` / `read_sync`: filter archived rows.
  This is the class serving `scope='workspace'` reads — the path `ReadFile`
  takes for the operator's own substrate.
- `services/primitives/workspace.py` `_exact_search`: exclude archived. Filtered
  in PYTHON, not via the shared helper — the match already occupies the query's
  one `.or_()` slot, and a second `.or_()` replaces the first rather than ANDing
  (it would have turned a substring search into "everything not archived").
- `routes/workspace.py` recent-revisions: the live-file lookup now asks whether
  the row is archived. "The revision resolves a row" is not "the file is live".
- `services/workspace_context.py`: `live_files_filter()` — the ONE spelling.
- Expected behavior: **a file the operator moved to Trash is gone from every
  read the LLM has.** `ReadFile` → `found: false`; `SearchFiles` → no hit;
  `ListFiles` already behaved. Restore still works; the chain is untouched.

  The operator trashed 20 briefs and they kept appearing in the Text app's
  Recents, opened at their URL with full content, and read back through
  `ReadFile` — so the delete looked broken when it had in fact worked (all 20
  rows `lifecycle='archived'`, chain intact). Delete is a lifecycle transition,
  not a row removal, which is what makes it restorable; the cost is that every
  read must ask, and four did not. The predicate was a hand-copied string in six
  places and absent from four, in two dialects that agree only while the column
  is fully backfilled.

### Gate
- `api/test_trashed_file_does_not_read_back.py` — asserts the BEHAVIOUR, not
  the spelling (a gate on the string would pass on the wrong dialect). Falsified
  against the original defect and against the double-`.or_()` trap.

---

## [2026.08.21.4] - the folder verbs complete the working-tree set

### Added
- `services/primitives/folder.py`: `DeleteFolder` + `MoveFolder`, bound to
  `services/folder_organize.py` — the SAME fan-out the Files surface calls.
  Registered in CHAT / HEADLESS / FREDDIE rosters, the lane surface, and the
  ADR-307 gate (path-addressed; `MoveFolder` dual-path like `MoveFile`).
- `services/mcp_composition.py`: the interop `delete` / `move` verbs now pick
  the GRAIN. One verb, two grains — a foreign caller addresses a name and the
  kernel knows whether that name is a file or a folder, so it never has to
  learn our taxonomy. The roster stays 10 verbs.
- Expected behavior: **a lane can now delete or move a whole folder.** The
  frame's `{tools_line}` derives from `lane_tool_names()`, so the prose names
  the new verbs automatically.

  Previously a member asked their lane to delete a folder and was told the
  primitives "only operate file-by-file rather than recursively wiping whole
  directory trees", and was advised to run `rm -rf` in a terminal. Both halves
  were wrong: the fan-out had shipped (`360ea4c`) and was reachable from the
  Files surface, and `rm -rf` on the repo would not have touched the files at
  all — the substrate is Postgres, not disk. ADR-337 predicted exactly this in
  the passage ruling out a `Bash` primitive: *"it is also why missing verbs
  hurt so much here — there is no shell escape hatch — which argues for
  completing the verb set, not adding the hatch."*

  **No extra gate in front of them, deliberately.** `trash_folder` writes one
  attributed archive revision per file — nothing removed, the group restorable
  as ONE unit, locked children refused and REPORTED. That is safer than the
  `rm -rf` the model reached for, and safer than `WriteFile`, which can
  truncate content and flows freely.

  Neither folder verb is an artifact verb: `DeleteFolder` leaves nothing to
  open, and `MoveFolder`'s result names a folder, which the viewer cannot
  render. Both show as labelled tool rows ("deleted a folder"), and their
  results carry the honest partial for the lane to report.

### Gate
- `api/test_verb_families_are_one_set.py` — generalized from the file-verb
  gate: declares the FAMILIES and asserts each is whole on every
  principal-facing surface, with deliberate narrowings named in code AND
  required to be explained in primitives-matrix.md. Falsified three ways.

---

## [2026.08.21.3] - the file-verb set is one set, whoever holds it

### Changed
- `services/lane_runner.py` `LANE_TOOL_NAMES`: five file verbs → **seven**
  (`DeleteFile` + `MoveFile` added). `lane_tools_openai` composes their
  registry schemas; `LANE_ARTIFACT_VERBS` gains `MoveFile` only.
- `services/lane_runner.py` `artifact_path_from`: `MoveFile` resolves
  `new_path`, not `path` — a move's result carries both and `path` is the
  SOURCE, which no longer exists once the move succeeds.
- `web/components/chat-surface/toolLabels.ts`: operator-facing spellings for
  the two new verbs ("deleting a file" / "moving a file").
- Expected behavior: **a lane can now delete and move files in the member's
  commons.** The frame's `{tools_line}` is derived from `lane_tool_names()`,
  so the prose the model reads names the seven automatically — no separate
  prompt edit, and the ADR-467 D4 three-way agreement (payload · allowlist ·
  prose) holds by construction.

  Previously a member asked their lane to delete two config files and was
  told "my available file tools do not include a file deletion primitive" —
  true of that surface and false of the system: `DeleteFile`/`MoveFile`
  shipped in ADR-337 and were live in `CHAT_PRIMITIVES`, in
  `FREDDIE_PRIMITIVES`, and as `delete`/`move` on the MCP interop surface. A
  foreign LLM connected over MCP could delete a file the member's own lane
  could not touch. The safety question was already settled by ADR-337: a
  delete is a VIEW change (attributed tombstone, chain retained, restore =
  ReadRevision + WriteFile), and governance-locked paths refuse.

  Uniform, never per-Agent — ADR-467 D4 holds as written.

  A deletion does NOT render an artifact card (a card is a deep link to a
  file to open; after a delete there is nothing there). It shows as a
  labelled tool row instead.

### Gate
- `api/test_verb_families_are_one_set.py` (renamed from
  `test_file_verbs_are_one_set.py` when the folder family landed) — derives
  both sides and asserts no
  surface is narrower than MCP. Falsified against the original defect.

---

## [2026.08.21.2] - a model dial is validated, not trusted

### Changed
- `services/model_selection.py`: new `accept_model_override(env_var, raw, current)`
  — the ONE validator for every `provider/model` env dial.
- `services/system_calls.py` `resolve_system_call`: `YARNNN_SYSCALL_{CALL_TYPE}`
  now routes through it.
- Expected behavior: an override naming an unknown or unpriced engine is
  IGNORED with an ERROR log; the declared model stands. A valid override
  (including a RETIRED engine — retired means un-offered, not un-routable) is
  still honoured exactly as before.

### Why (the observed defect)
Both dials accepted an arbitrary string, logged it at INFO, and handed it to a
provider SDK. A typo on a Render dashboard routed to a model that does not
exist (failing at the provider, far from the cause), and an unpriced id billed
at `_DEFAULT_RATE` — the silent cost lie ADR-439 §4 exists to prevent. Neither
shouted. It IGNORES rather than raises, following the `YARNNN_ROUNDS_*`
precedent: these resolvers run inside live wakes, and raising would turn a cost
typo into an outage. Gate: `test_model_override_validation.py` (12/12),
falsified against the real pre-fix code AND against a lazy "reject everything"
fix that would otherwise have shipped green.

## [2026.08.21.1] - the engine label carries its version; a tool argument stops naming a retired engine

### Changed
- `services/lane_runner.py` `LANE_MODELS`: every label now carries its version
  (`Claude Sonnet` → `Claude Sonnet 5`, `Gemini Flash` → `Gemini 3.5 Flash Lite`,
  `DeepSeek` → `DeepSeek V4 Flash`, `Grok` → `Grok 4.6`, …). The retired dated
  Haiku is `Claude Haiku 4.5 (dated)` and retired `gemini-2.5-flash` is
  `Gemini 2.5 Flash`.
- Expected behavior: the lane conventions frame opens `"You are Claude Sonnet 5"`
  rather than `"You are Claude Sonnet"` — the model is told which model it is.
  Attribution strings become `Kevin via Claude Sonnet 5`.
- `services/primitives/dispatch_specialist.py`: the `model` argument is REMOVED
  from the `DispatchSpecialist` tool schema, and from the handler.
- Expected behavior: the steward can no longer name a sub-call engine. The
  engine is `SYSTEM_CALLS["specialist_dispatch"]`, dialled by
  `YARNNN_SYSCALL_SPECIALIST_DISPATCH`. (The tool is dormant — `VALID_SPECIALIST_ROLES`
  is empty — so no live behaviour changes today.)

### Why (the observed defects, not speculative ones)
**The label.** `LANE_MODELS.label` is not picker chrome. It is written into every
revision's attribution string (`principal_display.model_display`) and it is what
the model is told it is (`_CONVENTIONS_FRAME`: `"You are {model_label}"`). Two
rows displayed **the same string**: retired `anthropic/claude-sonnet-4-6` and
live `anthropic/claude-sonnet-5` were both "Claude Sonnet". A member reading
their own history could not tell which engine authored a revision — an
incorrect-success in the ledger, on a product whose stated invariant is that
every change is signed by whoever made it. The FE mirror had also silently
drifted: `claude-haiku-4-5-20251001` read "Claude Haiku" there and
"Claude Haiku (4.5)" on the server, so one id rendered two names depending on
which path drew it. `web/lib/workspace/__tests__/lane-model-labels.test.mjs`
now gates cover / verbatim-match / label-uniqueness / version-present, and each
assertion was falsified against the real pre-fix state.

**The tool argument.** Its schema description instructed the model to pass
`'claude-haiku-4-5-20251001'` — retired since ADR-559 — and the value flowed
straight to `chat_completion_with_tools(model=…)` with neither the `LANE_MODELS`
membership check nor the ADR-439 §4 billing gate that every other routed path
enforces, so an unpriced engine would have priced silently at the Sonnet
default. This is the identical door `routes/images.py` closed on
`ComposeRequest.model`, closed the same way: an engine follows its declared
home, never a caller-supplied id.

## [2026.08.20.1] - whoami gets a trigger, not just a listing (ADR-584)

### Changed
- `mcp_server/server.py` `_build_interop_instructions()`: the proactive-trigger
  paragraph now routes a "which workspace am I connected to" question to
  `whoami`, and says why a listing cannot answer it (a listing shows what is IN
  a workspace, never WHICH one it is; the reference grammar is identical in all
  of them). One sentence, inside the existing paragraph — no new section.
- Expected behavior: a connected host asked where it is standing calls `whoami`
  instead of enumerating files.

### Why (the observed failure, not a speculative one)
Probed 2026-08-20 on a live ChatGPT connection. Asked "what workspace am I
connected to", it answered from a `list` — reporting a bare
`yarnnn://workspace/` root and a file count, which names no workspace at all.
`whoami` shipped at `17c8d21` and was deployed, but the word appeared **zero
times** in the instructions builder body: it reached the host only through the
verb table derived from `_INTEROP_VERBS`. The table says a verb EXISTS; the
trigger paragraph is what says WHEN to reach for one, and it covered `open`,
`search`, and `save` only. The one question `whoami` was built to answer was
the one question nothing routed to it.

Gate: `test_adr584_connector_names_its_workspace.py` D1.a — anchored on the
trigger paragraph specifically, because the pre-existing D1 check ("whoami" in
instructions) passed on the derived table the whole time this was broken.
Falsified against the exact shipped shape.

---

## [2026.08.19.2] - The component library + the colour-law recut (ADR-583)

### Changed
- `services/authoring.py` `_POSTURE_FRAME`: (1) the token-law paragraph is
  RECUT — the absolute invariant is "never a raw colour/face/radius; every
  themable property through the design-system slots", and bespoke GEOMETRY is
  freed, homed in component files (the blanket reading of "never inline
  style" was forbidding the composition the operator asked for). (2) New
  "## Components (the workspace library)" section: a component is a
  `*.component.html` workspace file cited like a CSV/image (pinned; edit the
  SOURCE), with the authoring contract (one root, scoped style, slots,
  no script, no inner block ids) and the reverse-engineer act (a screenshot
  or source component shown to the lane becomes a library file).
- `services/authoring.py` `STUDIO_BLOCKS["component"]`: markup/description
  re-cut from the inline card to a citation — the taught grammar now teaches
  citing the library, never pasting card markup.
- Expected behavior: asked for a component (or shown one to reproduce), the
  lane authors a library FILE and cites it, instead of improvising inline
  card markup per artifact. Addresses the observed failure from the operator's
  discourse: component requests were answered with pre-drafted skeletons; the
  grounded/reverse-engineered path had no taught act.

## [2026.08.19.1] - The composed family grows (ADR-581 D4)

### Changed
- `services/authoring.py`: five `STUDIO_BLOCKS` rows added — `stat`,
  `comparison`, `timeline`, `person` (composed: tier=object, cites=none) and
  `logo-row` (cites=picture). The lane's `_blocks_grammar` roster grows five
  lines per bound app (the posture derives from the registry; no posture text
  edited). The stat's teaching markup shows the delta colouring through the
  existing `data-mark` palette marks rather than a new mechanism.
- Expected behavior: a Studio-bound lane can now author the deck-native
  composed kinds directly (previously it improvised them as `component`/
  `metrics` compositions or plain divs the kernel could not draw); a logo
  strip is authored as CITED marks, never pasted images. Addresses the
  observed failure ADR-581 §1 measured: NEW on a deck offered 8 prose kinds
  against 3 composed, and decks were carried by text orientations.

## [2026.08.18.1] - RepurposeOutput deleted (ADR-579 D9)

### Changed
- `services/primitives/repurpose.py`: DELETED — the primitive was broken
  (`NameError` on `tw` after the paid LLM call), had zero FE consumers since
  ADR-185 (closed refused), and is doctrinally refused by ADR-333 D5 (a second
  production pass over finished content). Registry import, `CHAT_PRIMITIVES`
  entry, and dispatch row removed; the `repurpose` system-call row and the
  `/recurrences/{slug}/repurpose` route deleted with it.
- `agents/cockpit_awareness.py`: the not-in-your-surface roster no longer
  names RepurposeOutput (it no longer exists to withhold).
- Expected behavior: the chat model can no longer call a primitive that
  crashed after spending; no live surface loses anything (zero callers).
  Repurposing re-enters later as ADR-579 D8's NEW-from-sources lane act.

## [2026.08.15.1] - The Text app's job overlay (ADR-571)

### Changed
- `services/apps/text.py` (NEW module): `build_text_posture` — the JOB
  overlay for a text-bound lane, composed under the resident's character
  (character first, job second — the lane_runner order). No new character
  text and NO new posture row: Editor is the app's NAME for the designer
  resident (`register_app("text", resident="designer", name="Editor")` —
  the Docs/"Writer" shape, ADR-562), because Editor's character IS the
  writing character; only the name differs.
- `services/lane_runner.py`: one branch — `lane_meta.app == "text"` selects
  the overlay above.
- Expected behavior: a lane bound to a `.md` is told its job is THIS prose
  document — read the head fresh, refine conversationally, write whole and
  plain (no HTML, no block ids, no `data-*`), cite `derived_from` when
  authoring from a source, and never rewrite the document to change a
  sentence. **Why it is needed rather than nice**: without the branch the
  lane falls through to `build_studio_posture`, which lifts `data-template`
  from the artifact — an `.md` has none, so it silently resolves to
  `document` and the colleague is handed an HTML-BLOCK contract for a
  markdown file. Observed hazard, named in ADR-570's scoping; the same
  reason radar and strings each carry a branch.

---

## [2026.08.14.1] - Keeper's character + the strings desk/run postures (ADR-569)

### Changed
- `services/agents_registry.py`: `KERNEL_POSTURES` gains `keeper` — the
  Strings app's resident (a POSTURE over Produce, `based_on: designer`; the
  Critic shape, so the axiom-derived three-operation base roster stays
  closed). New character text: custodian of maintained files — fidelity over
  novelty, preserve member corrections, never invent, name source/contract
  disagreements plainly.
- `services/strings.py` (NEW module): two job overlays, both composed under
  the resident's character (character first, job second — the lane_runner
  order). `_KEEPER_RUN_POSTURE` — the standing prose run (the radar report
  posture's shape: full revised file or exact NO_CHANGE, fold-don't-append,
  preserve corrections, cite sources inline, never pad). `_KEEPER_DESK_FRAME`
  — the bound-lane desk job (ADR-567 D4's mechanism, one more branch in
  `build_lane_conventions`): teaches the D1 law (only the DESIGNATED target
  is a standing writer's target), the three files, the strict `_string.yaml`
  grammar (target/schedule/sources/shape), read-back after machine config,
  never-invent-sources, and shape-violation repair; state block read fresh
  per turn.

### Expected behavior
- A lane bound with `app='strings'` speaks as Keeper and manages the string's
  lifecycle (author CONTRACT.md + _string.yaml, tend the designated file)
  instead of receiving Studio's authoring posture — the same defect class
  ADR-567 D4 fixed for radar, prevented at birth here.
- A prose (md) string's scheduled run folds fresh source material into the
  file under CONTRACT.md, honoring member edits and returning NO_CHANGE
  honestly. Not a repeated-failure fix: these are new surfaces shipping with
  their app (the radar precedent, 2026-08-04). Steward frame untouched —
  size ratchets unaffected (run to prove, not because they bind).

## [2026.08.13.3] - The frame names the room (ADR-495 D3 addressing)

### Changed
- `services/lane_runner.py`: new `_CAST_SECTION` + `_build_cast_section`,
  composed into `_CONVENTIONS_FRAME` between format discipline and the
  mandate. Lists the OTHER participants (never the speaker), species-blind,
  in join order. `build_lane_conventions` and `run_lane_turn_stream` take
  `cast` + `responder_reason`.
- `services/addressing.py` (NEW): `@handle` parsing + `select_responder`.
  Matches display name AND slug, case-insensitively.
- `routes/lanes.py`: the responder comes from ADDRESSING, not `cast_agents[0]`.
  Assistant rows now persist `agent_slug` + `responder_reason`.

### Expected behavior
- **The observed failure this fixes:** a cast of {member, Thinker, Lisa} where
  the member typed "@lisa can you hear me" and THINKER replied "there's no
  agent by that name active in this session or workspace that I can see."
  That was TRUE from inside the prompt — the frame named exactly two entities,
  itself and the member, so the Agent correctly reported its own context. It
  was not a hallucination; the injection point did not exist.
- An Agent now knows who else is in the conversation and is told explicitly
  that it must not answer as them or invent what they said.
- `@name` routes the turn to that cast member. An unrecognized handle is NEVER
  fuzzy-matched — it falls through to the ladder, because a typo silently
  addressing the wrong colleague is worse than not routing.
- **A cast of one composes byte-identically to before** (asserted:
  `solo == none`), so every solo conversation is unchanged.
- Never-ambient holds: addressing selects WHICH Agent answers a human act; it
  never causes a turn. Still exactly one reply per turn (ADR-495 D3).

---

## [2026.08.13.2] - GenerateImage places by meaning, like every other write

### Changed
- `services/primitives/generate_image.py` (`GENERATE_IMAGE_TOOL`): the schema
  gains an OPTIONAL `folder`, and the description now opens with the same law
  `WriteFile` states — the path is the meaning; authored images live in the
  Documents home or a meaning-named folder. Omitted → Documents.
- `services/primitives/generate_image.py` (`_resolve_path`): replaces the
  hardcoded `/workspace/uploads/generated/`. Traversal is neutralised
  PER SEGMENT so a real nested folder survives while `..` cannot escape.
- `services/primitives/permission.py` + `workspace.py::_resolve_gate_paths`:
  `GenerateImage` joins the ADR-307 uniform gate as a path-addressed verb,
  composing its destination through the HANDLER's own resolver.

### Expected behavior
- The model now CHOOSES where a generated image lands and can put it beside
  the work it serves. Previously every image went to one app-named folder no
  envelope ever mentioned, so the model could not predict or state its own
  output path — it had a `filename` and no way to express a destination.
- The observed failure this fixes: images filed into `uploads/`, the
  pre-ADR-395 legacy root, which the Finder hides unless it holds legacy
  files. Authored work (attributed `member:`) was landing in the ARRIVALS
  zone on a "the path is the badge" theory ADR-555 D1 overturned.
- A governance-locked destination now DENYs before the handler runs. Nothing
  else changes: a call with no `folder` behaves as before except for landing
  in Documents rather than the legacy root.

---

## [2026.08.13.1] - An app may call its resident by its own name (Docs → Writer)

### Changed
- `services/agents_registry.py` (`build_agent_posture`): new `as_name` parameter.
  When set, the WHO-YOU-ARE section gains one line naming the app's label for
  the resident and stating it OVERRIDES the character's own name. Absent → the
  section is byte-identical to before (Studio · IMAGES · every chat lane).
- `services/apps/docs.py`: `register_app("docs", resident="designer", name="Writer")`
  — consuming the `name` field ADR-562 left declared and unread.
- `services/lane_runner.py` (`build_lane_conventions`): resolves the app from the
  bound artifact's own `data-template` and passes its name through. Also hoists
  the artifact read to ONE round-trip (it was read twice for one commit).

### Expected behavior
- In Docs the colleague introduces itself as **Writer**; in Studio and IMAGES it
  remains **Designer**. Same character, same engine, same capability — only the
  name differs, because Docs is the capture medium and the name fits it.
- The rename is stated as an override rather than an alias. Observed failure it
  answers: the character text opens "You are Designer —" and the colleague
  INTRODUCES ITSELF by that name (2026-08-13 click-pass screenshot: *"I'm
  Designer — your maker in this workspace"*). A bare "also called X" leaves two
  names live and the model uses the one it read first.
- Cost: +1 line (~150 chars) on bound Docs lanes only. Zero elsewhere.

---

## [2026.08.12.1] - An unbound lane learns what the member is looking at

### Changed
- `services/lane_runner.py` (`build_lane_conventions`): when the lane is
  UNBOUND and the turn carries an ADR-522 focus declaration, the posture gains
  one situational line — the member's open file, with the rule that unnamed
  file work targets it in place, never a copy elsewhere. The focus wire was
  threaded end-to-end since ADR-522 and rendered only inside the bound lane's
  studio posture; a general chat lane received the declaration and said
  nothing about it.
- Observed failure (not speculative): the fundraiser-copy incident, 2026-08-12
  — a chat lane asked to add test blocks to the member's open document
  duplicated it into a new `fundraiser/` tree; the member watched an unchanged
  canvas. (The FE half: `useCurrentFocus` returned null when the chat window
  itself was foregrounded — fixed in `web/lib/shell/useSurfaceFocus.tsx` with
  the desk fallback, same commit.)
- Expected behavior: a lane asked for document changes while the member has a
  file open edits THAT file by default; bound lanes unchanged (the studio
  posture already carries path + focus).

## [2026.08.10.1] - The connector's widgets render what the server actually sends

### Changed
- `services/mcp_composition.py` (`compose_save`): the success payload now echoes
  **`derived_from`** — the citations that were ACTUALLY RECORDED on the revision
  (the post-parse set), never the caller's raw argument. `save` has accepted,
  parsed and written the provenance edge to the ledger since ADR-533 D3, but
  never returned it, so the one thing that distinguishes an attributed commons
  from a folder of files was invisible at the moment of writing. Absent when
  nothing was cited — never an empty key.
  - The echo is deliberately the parsed set: a malformed citation is dropped
    rather than made fatal (a bad reference must not cost the user their write),
    so echoing the input would report an edge that may not exist.
- **Expected behavior**: a host that cites sources on `save` now gets them back
  and can say *what this document was made from*; the save-receipt widget renders
  it. No change to what is written — only to what is reported.

### Fixed
- `widgets/src/search-results`: the widget rendered **`confidence` nowhere**, and
  rendered `explanation` only on the EMPTY path — so `ambiguous` (where the
  server explicitly writes *"consider asking the user which they mean"*) looked
  identical on screen to a confident hit. Both now render beside the results.
- `widgets/src/save-receipt`: the conflict card said "save again" without naming
  the **`base_revision`** the retry must carry, though the server returns it on
  both conflict errors. A guard is only reassuring if you can see what it wants.
- **Observed failure this addresses** (not speculative): driving the live
  connector from ChatGPT on 2026-08-10, `search` returned `confidence:
  "ambiguous"` twice; the host asked the user to disambiguate off the STRUCTURED
  payload while the card beside it showed a flat ranked list. The signal survived
  to the model and died at the glass.

### Gate
- New `api/test_mcp_widget_render_completeness.py` (15 assertions, falsified):
  asserts the RENDER, not the declaration — a type that names a field proves
  nothing about whether a reader sees it. Includes a build-is-the-mount check
  (the served resource reads the `dist/` bundle, not the source) and a standing
  guard against a backtick inside the CSS template literal, a trap that bit
  three times in the ADR-546 arc and once here.
- **Not done, deliberately**: no widget was added for any text-only verb.
  Text-only is valid on every host (ADR-372 D1) and five verbs are text-only BY
  DECISION with reasons recorded (ADR-533 D4 / ADR-545). Reversing that needs
  evidence from a write click-pass and an amendment, not a widget PR.

---

## [2026.08.09.1] - ADR-538: a chart cites DATA, and motion is CSS-only

### Changed
- `services/studio.py` (the Studio substrate posture — the lane's authoring
  teaching): the "you can CREATE visual assets" bullet no longer tells the AI
  hand to author **charts** as SVGs. It kept saying *"author charts, diagrams,
  icons… as .svg files… then cite them"*, which is exactly the model ADR-538 D2
  withdrew — an authored SVG chart goes stale the moment a number moves, and
  the two live instances proved it (data only in `alt` prose, empty pin).
  - **Removed** from the SVG bullet: `charts`. Diagrams/icons/illustrations stay
    (they have no data source to project — ADR-538 D1's `media` class).
  - **Added**: a chart bullet — write the numbers as a `.csv`, then cite it
    (`data-ref-kind="chart"`, `data-chart="bar|line|donut"`); the projection
    draws it, so the chart stays true when the data changes.
  - **Added**: a motion bullet — *"Motion is CSS only, never `<script>`"*, with
    the reason stated (a script does not run in the viewer or in a shared link,
    so a component that needs one is invisible to readers).
- **Expected behavior**: asked for a chart, the lane writes a CSV and cites it
  instead of hand-drawing an SVG; asked for an animated component, it reaches
  for `data-motion` / CSS instead of a `<script>` the reader's mount will strip.
- **Observed failure this addresses** (not speculative): 15 live artifacts hold
  `chart` blocks; 0 cite a `.csv`; the two real ones cite unpinned SVGs whose
  numbers exist only in `alt` text.
- Gate: `api/test_adr538_block_classification.py` §5 asserts all three (the lane
  is told charts cite data, is told motion is CSS-only, and is NOT told to
  author an SVG chart).

---

## [2026.08.06.1] - ADR-522: the focus declaration — one bullet naming where the member stands

### Changed
- `services/studio.py`: new `build_focus_line(focus, template)` + a `focus`
  parameter on `build_studio_posture`. When the shell declares what the member
  is looking at, the posture gains **one bullet** as a sibling of the outline,
  before the first `- PATCH` line:
  - `- The member is viewing slide 4.` (on screen, nothing selected)
  - `- The member has selected slide 4.` (picked, not merely shown)
  - `- The member has the prose block selected — "Our pricing has…".`
  - `- The member is writing under the heading "Pricing".` (flow only)
- `services/lane_runner.py`: `focus` threaded through
  `build_lane_conventions` + both runners to the posture. Rides the same
  per-turn overlay as the artifact head — both are readings of the bound
  artifact (what it IS, where the member IS in it).
- `routes/lanes.py`: new `LaneFocus` model + optional `focus` on
  `LaneTurnRequest`. Read off the REQUEST, never off `lane_meta`: the durable
  binding says which artifact, the transient focus says where in it.

### Why this is an addition (the ADR-306 bar)
An **observed, repeated failure**, not a speculative one: a live Studio session
where the operator wrote "tidy up this slide" with a deck open, a slide on the
stage, and nothing selected — the agent could not act and had to ask *which
slide*. The audit found the gap was structural (the lane wire had no field for
view context and never had), so no amount of prompt prose could have fixed it.
The deictic asks natural to an authoring surface — "this slide", "this
section", "this block" — were all unanswerable.

### Cost
One line, ~15 tokens, only when an app declares focus. **Absent → the posture
is byte-identical to pre-ADR-522** (verified: the no-focus posture composes
unchanged, and the focus posture is exactly one line longer).

### Expected behavior
The lane resolves deictic reference without a clarifying round-trip: "tidy up
this slide" acts on the slide on screen; "rewrite this section" acts on the
heading the caret sits under. Page numbers are **1-indexed** for the member
(the state is 0-indexed — the `pageNoun` / `askAboutSelection` precedent).

### Not a return of ADR-446 D5
That decision cut selection→chat because auto-seeding appended prose to the
MEMBER'S composer on every click — visible spam they had to delete. This is a
server-rendered line in the system posture, once per turn, which the member
never sees and never cleans up.

---

## [2026.08.04.1] - ADR-516: the layout tokens leave the lane's grammar

### Changed
- `services/studio.py`: `valign` + `pad` rows deleted from `STUDIO_TOKENS`.
  The served vocabulary and `_tokens_grammar()`'s posture prose both shrink
  by two rows — an ADR-306-shaped ablation, not an addition. Layout on pages
  and containers is bounded inline-CSS presets through the one Studio op
  (`setContainerLayout`, ADR-516 D1); the lane already speaks `padding` and
  `justify-content` from pretraining, so the private synonyms were prompt tax.
  Kernel rules for the attributes remain (legacy inert names, ADR-511 D8).
- Observed failure class: the two-language pane — the same member intent
  ("give this thing breathing room") reached a token on the page grain and
  literal CSS one rung down on the container grain (2026-08-04 audit).
- Expected behavior: the lane authors slide/band spacing as ordinary inline
  style; it stops emitting `data-valign`/`data-pad` (which nothing offers or
  teaches anymore); artifacts carrying them still render.
- Gates: `python3 test_adr453_property_layer.py` (registry cut + legacy-rules-
  remain assertions) + `test_adr466_mode_native.py` (ADR-516 D1–D5 block).

## [2026.08.03.3] - DuplicateFile (ADR-514 D1): duplicate is a derivation

### Changed
- `services/primitives/workspace.py`: new **`DuplicateFile`** tool + handler. The
  description teaches the two properties that distinguish it from a clone: the
  copy CITES its source (`derived_from`, so `trace` walks back) and the free
  `-copy` name is resolved server-side, not probed by the caller. States its
  limits in-schema: files only (no folders), any extension, binaries by blob
  reference.
- `services/primitives/registry.py`: registered in HANDLERS + CHAT_PRIMITIVES.
- `services/primitives/permission.py`: added to `_PATH_ADDRESSED_QUEUEABLE` so
  the ADR-320 topology gate resolves its path — a duplicate into a locked root
  DENYs exactly like a write.
- Expected behavior: an LLM caller asked to "make a copy of X" now has a verb
  for it, and the copy is attributed to a parent instead of appearing as an
  origin-less file. Previously there was NO kernel duplicate — the only
  implementations were two browser-side copies in Studio (`.html`-only, capped
  at 5, TOCTOU-racy, recording no origin); both are deleted.
- Gates: `python3 test_adr514_duplicate_verb.py` (21 checks, falsified against a
  removed `derived_from`); `test_adr337_file_verbs.py` 36/36 (its exact-set
  assertion on the path-addressed verbs widened four → five, deliberately).

---

## [2026.08.03.2] - The save verb (ADR-512 §8a): the write half of exact-version

### Changed
- `mcp_server/server.py`: new **`save`** tool — attributed overwrite of one named
  file. The docstring + instructions TEACH the contract: read-before-write
  (base_revision from open required for existing files; omitted only to create),
  stale_write means re-open-merge-resave (never blind retry), writes land signed
  as the connector principal.
- `services/mcp_composition.py::compose_save` — enforces base_required/not_found
  before any write; dispatches through execute_primitive (no second write door);
  returns the new head so follow-up saves chain.
- `services/primitives/workspace.py::handle_write_file` — gains the optional
  ADR-406 CAS rider (`expected_parent_version_id` → um.write) and maps
  StaleWriteError to a structured `stale_write` carrying the intervening head's
  attribution. Existing callers byte-identical (rider defaults None).
- Expected behavior: a foreign host can now complete the full co-work loop
  (open → edit in its own context → save with base) with the exact-version
  guarantee running both directions. Gate: `python3 test_adr512_save_verb.py`
  (11 checks); ADR-406's own gate re-run green (5/5).

---

## [2026.08.03.1] - The arrival arc (ADR-513 + ADR-465 B/C/F): `share` verb joins the connector

### Changed
- `mcp_server/server.py`: new **`share`** tool (ADR-465 D5/Phase F) — mints a share
  link via `create_share` (one transport, three origins) and RELAYS it (no outbound
  send, ADR-404). `access: member|viewer` picks the grant shape; instructions teach
  it as the fifth verb. Narrative weight `material` (a membership act).
- Context the host should know: the link is now PUBLICLY readable (ADR-513 — the
  artifact + its attribution walk render for anyone with the link; joining stays
  auth-gated), so "share this with X" genuinely works from inside a foreign LLM.
- Expected behavior: hosts can complete the share loop end-to-end (recall/open →
  share → relay link). Gate: `python3 test_adr465_share_as_view.py` (15 checks).

---

## [2026.08.02.1] - The file is the unit of interop (ADR-512): `open` verb + connector re-frame

### Changed
- `mcp_server/server.py` (`instructions` block + module docstring): the connector's
  self-description re-cut from "the user's durable, attributed memory" to **"the
  user's shared, attributed workspace"** — the memory identity contradicted ESSENCE
  §What-YARNNN-Is-Not ("not a memory feature") and the v19 canon lock (the ICP's
  mental model is shared files, not ambient memory). Observed failure: the surface
  taught every foreign LLM the ontology the canon retired 2026-07-30.
- `mcp_server/server.py`: new **`open`** tool (registered name `open`, symbol
  `open_file`) — the deterministic path/handle read (ADR-512 D4): content + head
  attribution + recent revision summary in one server-composed round. Read-only
  annotated; output schema declared. Instructions teach it as the exact-version
  read that `recall` (search) is not, and tell the host to open a pasted
  `yarnnn://workspace/…` reference before reasoning about the file.
- `services/mcp_composition.py`: `compose_open` + the ADR-512 D5 handle grammar
  (`parse_file_reference` / `format_file_reference`, `yarnnn://workspace/{path}`).
- `services/primitives/registry.py`: stale comment corrected (claimed InferContext
  survived "via MCP remember_this" — both deleted; live surface is
  open/remember/recall/trace).
- Expected behavior: hosts holding a file reference read the exact file instead of
  semantic-searching for it (the exact-version guarantee); remember/recall/trace
  behavior unchanged (ADR-512 is additive; renames are evidence-gated). Gate:
  `python3 test_adr512_open_verb.py` (10 checks).

---

