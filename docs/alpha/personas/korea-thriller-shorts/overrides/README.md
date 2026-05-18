# korea-thriller-shorts persona overrides

> ADR-230 D6 + ADR-283 D5: persona-specific overrides directory for the `korea-thriller-shorts` workspace. Files placed here are applied as Step 4 of `activate_persona.py` after the bundle fork, with `authored_by="operator:alpha-korea-thriller-shorts"` per ADR-209 attribution.

## Purpose

The alpha-author bundle ships **medium-agnostic** templates at `docs/programs/alpha-author/reference-workspace/`. The `korea-thriller-shorts` workspace is one specific operator instance running that bundle — short-form AI-video-gen authoring (Higgsfield et al.) for the same Korean-modern Thomas-Crown-Joker universe as `netflix-script-author`.

This workspace is the **third dogfood instance of alpha-author**, intentionally chosen to stress-test the bundle at a different shape than the first two:

- **Different format**: AI-video-gen shot prompts, not screenplay or prose.
- **Different cadence**: ship multiple shorts per week (AI-video-gen iteration is fast), not the 12-18mo screenplay arc and not the quarterly founder-corpus tempo.
- **Different output shape**: prompts + generated takes, where the generation itself is part of the authorial discipline.
- **Shared canon, separate workspace**: same Jaewon, same universe as netflix-script-author — entity files mirrored across both workspaces.

If alpha-author works for founder corpus (yarnnn-author) + long-arc screenplay (netflix-script-author) + short-form AI-video-gen (korea-thriller-shorts), the bundle's medium-agnosticism claim is durable. If it works for two of three, the architecture needs amendment.

## What's here (authored 2026-05-18 per ADR-283 step 6 dogfood)

Files mirror substrate paths they override. `activate_persona.py` Step 4 walks every `.md` and writes it to the matching `/workspace/` path with `authored_by="operator:alpha-korea-thriller-shorts"` per ADR-209.

| Override | Bundle template overridden | Why differs |
|---|---|---|
| `context/_shared/MANDATE.md` | `docs/programs/alpha-author/reference-workspace/context/_shared/MANDATE.md` | AI-video-gen-shot-prompt Primary Action; shoot-ready criterion; canon-sync discipline with netflix-script-author; synthetic stress-test framing |
| `context/authored/_voice.md` | `docs/programs/alpha-author/reference-workspace/context/authored/_voice.md` | Single voice (prompt-writer), character-canon-aware; shot-spec format; AI-video-gen-specific anti-patterns (no "mysterious figure", no adjective stacks, no "in the style of"); per-tool syntax accepted; visual stress-state translation rules for Jaewon |
| `context/authored/_editorial.md` | `docs/programs/alpha-author/reference-workspace/context/authored/_editorial.md` | Shoot-ready criterion as load-bearing audit; per-tool editorial criteria (Higgsfield/Sora/Runway/Veo); sync-discipline with netflix-script-author; long-arc-specific cadence |
| `context/authored/_entities.md` | `docs/programs/alpha-author/reference-workspace/context/authored/_entities.md` | Shared-canon vs visual-canon distinction; sync discipline with netflix-script-author; cross-workspace canon-drift as failure mode |
| `context/authored/entities/jaewon.md` | *(mirror — same file in netflix-script-author overrides)* | Identical content to netflix-script-author. When canon evolves, both update via PR. |

## Source material

Premise SHARED with netflix-script-author (same operator prompt from 2026-05-18 session: *"thomas-crown affair inspired series, modern Korea, crypto/BTC heist, affluent mastermind layered through proxies, Joker-thematic..."*).

Format ADDED by operator request 2026-05-18: short-form authoring for AI-video-gen tools (Higgsfield was the named example). Format-specific voice + editorial + entity-substrate authored by Claude on operator's behalf with the synthetic-stress-test framing explicit in MANDATE.

`entities/jaewon.md` copied verbatim from `docs/alpha/personas/netflix-script-author/overrides/context/authored/entities/jaewon.md` as starting shared canon. Future canon evolution syncs across both workspaces via PR discipline (see `_entities.md` sync section).

## Activation flow

1. `activate_persona.py --persona korea-thriller-shorts` is run.
2. Step 2: `initialize_workspace(program_slug=None)` ensures YARNNN agent row + kernel skeleton (idempotent).
3. Step 3: `_fork_reference_workspace(...)` copies bundle templates into `/workspace/` (ADR-226 three-tier idempotency).
4. **Step 4: this directory's files apply as overrides** — each `.md` writes to the matching path with `authored_by="operator:alpha-korea-thriller-shorts"` per ADR-230 D6.
5. Step 5: specialist agent rows ensured.
6. Step 6: platform connect (skipped — `platform.kind=none`).

After activation, the Reviewer reads this substrate (including the mirrored Jaewon entity) at every pre-ship-audit.

## Override evolution

When operator's stance evolves, changes happen in TWO places:

1. The workspace at `/workspace/` via chat-authored edits.
2. The override file here via PR — so next `activate_persona.py` run + future workspace resets land on updated stance.

**For shared-canon entities specifically**: changes happen across BOTH this workspace's override directory AND `docs/alpha/personas/netflix-script-author/overrides/context/authored/entities/{slug}.md`. Both PRs in the same change set. Re-run `activate_persona.py` for both personas to land the sync.

## Graduation path

If shorts get used for real distribution (pilot pitches, marketing reels, social distribution), the MANDATE's synthetic-stress-test framing graduates to real-project. Override file gets revised; `_signal.md` gains external_outcomes per ADR-283 step 2. Architecture supports graduation without rebuilding.

## Triangulation with sibling personas

Three alpha-author personas now exist (post-2026-05-18 dogfood scaffolding):

| Persona | Format | Cadence | Audience-state |
|---|---|---|---|
| yarnnn-author | Founder corpus (essays, posts, IR memos) | Multiple per week, compounding over years | Post-audience (existing YARNNN audience + new growth) |
| netflix-script-author | Long-arc screenplay (scenes, beats, series bible) | Daily iteration, single artifact over 12-18mo | Pre-audience (no production interest yet) |
| korea-thriller-shorts | AI-video-gen shot prompts (shorts) | Multiple per week, fast iteration | Pre-audience (no distribution target yet) |

The bundle's claim to medium-agnosticism rests on supporting all three simultaneously without architectural amendment. The dogfood goal is to validate the claim (or surface the gaps).
