# YARNNN Voice & Tone — audit + target spec

**Date**: 2026-06-24
**Status**: Draft spec — derived from a CC-style rewrite of real YARNNN copy.
**Why this exists**: the agent's prose AND the product's UI copy both read denser and more jargon-laden than Claude Code — a more technical tool that nonetheless talks more plainly. This doc establishes the *target* by rewriting real YARNNN samples in CC's style, then extracting the rules those rewrites obey.

> **Scope correction (read first).** An earlier attempt (ADR-365) treated this as an *agent-prose* problem and tried a persona-frame directive; an A/B eval falsified that (a soft prompt directive doesn't move the model's free-prose register). The harvest below shows why: **the voice problem is overwhelmingly in deterministic product copy — UI labels, empty states, settings, narration, emails — not the model's free prose.** That copy is hand-authored strings we control completely. This is where the lever is.

---

## 1. The reference standard (Claude Code's communication canon)

CC's `# Communicating with the user` section (`docs/analysis/src_claudeCC/constants/prompts.ts:405`) is the bar. The load-bearing rules, paraphrased:

1. **Write for a person who lost the thread.** They don't know your codenames, abbreviations, or internal shorthand. No unexplained jargon — expand technical terms.
2. **Lead with meaning, then mechanism** (inverted pyramid). The action/answer first; the "how" after, only if needed.
3. **Flowing prose, read linearly.** No fragments, no notation dumps, no semantic backtracking (a sentence you have to re-parse).
4. **Understanding over terseness.** If the reader has to re-read or ask, you've lost more than you saved by being short.
5. **Match the reader's expertise.** Tilt concise for experts, explanatory for newcomers.

The YARNNN-specific corollary, which CC doesn't need but we do:

6. **Never surface internal nouns or doc references to the operator.** `recurrence`, `wake`, `substrate`, `aperture`, `primitive`, `ADR-NNN`, `_recurrences.yaml` are kernel vocabulary. The operator is not reading our architecture. Name the *thing*, not the *mechanism*.

---

## 2. Side-by-side rewrites (the target spec, by example)

Each is a verbatim YARNNN string (with location) → a CC-style rewrite → the rule it demonstrates.

### 2.1 — Autonomy "Bounded" consequence
`web/components/workspace-concepts/AutonomyCard.tsx:78`

> **BEFORE:** "The Reviewer will auto-execute capital actions within your declared ceiling. Substrate writes (file edits) STILL wait for your approval — only Autonomous auto-applies those. Higher-impact capital actions also wait."

> **AFTER:** "Your agent can spend on its own — up to your limit — without asking first. It still checks with you before changing any of your files, and before any spend above the limit."

*Rules:* lead with what the operator gets (it can act on its own); "capital actions" → "spend"; "substrate writes (file edits)" → "changing any of your files"; "ceiling" → "limit"; drop the ALL-CAPS shouting; one idea per sentence, read linearly.

### 2.2 — Mandate tagline
`web/components/agents/MandateTab.tsx:24`

> **BEFORE:** "Your Primary Action declaration — the external write you're moving value with, plus success criteria and guardrails. YARNNN gates task creation on this (ADR-207)."

> **AFTER:** "What you're here to get done — the real-world action that moves the needle (place an order, ship a campaign, publish a piece), plus what success looks like and the limits you won't cross. Nothing runs until you've set this."

*Rules:* "Primary Action declaration / external write you're moving value with" → "what you're here to get done / the real-world action that moves the needle" + concrete examples; "guardrails" → "the limits you won't cross"; "gates task creation" → "nothing runs until you've set this"; **delete the ADR reference entirely** — the operator never needs it.

### 2.3 — Reviewer activity empty state
`web/components/agents/ReviewerActivityPanel.tsx:195`

> **BEFORE:** "No active judgment recurrences configured. The Reviewer wakes on three triggers (per ADR-260): operator chat, proposed actions, and scheduled cron. The first two are always live; scheduled cadence is opt-in via `_recurrences.yaml`."

> **AFTER:** "Your agent isn't on a schedule yet. It already responds when you message it or when an action needs a decision — that's always on. To have it check in on its own at set times, ask it in chat to set a schedule."

*Rules:* "judgment recurrences configured" → "on a schedule"; "wakes on three triggers" → "responds when…"; **delete ADR-260 and `_recurrences.yaml`** — internal; the operator acts through chat, so point them there, not at a YAML file.

### 2.4 — Feed pulse label
`web/components/feed/InvocationCard.tsx:50`

> **BEFORE:** "reactive wake"

> **AFTER:** "responded to a change" (or simply "auto" / the triggering reason in plain words)

*Rule:* "wake" is the single most-leaked engine term. The operator sees a card; tell them *why it ran* ("you messaged it," "a proposal came in," "scheduled check," "something changed"), never the internal trigger taxonomy.

### 2.5 — Navigation header
`web/components/workspace/WorkspaceNav.tsx:101`

> **BEFORE:** "Recurrences"

> **AFTER:** "Schedule" (or "Scheduled work")

*Rule:* pick ONE operator-facing word for the concept and use it everywhere. "Recurrence" is the code noun; the product word is "schedule" / "scheduled work." (Today the product says *recurrence*, *task*, AND *scheduled action* for the same thing — pick one.)

### 2.6 — Activity filter chip
`web/components/activity/ActivityLog.tsx:362`

> **BEFORE:** "Mech"

> **AFTER:** "Automatic" (paired with "Judgment" → "Decisions")

*Rule:* never abbreviate to dev shorthand in a label. Spell it; use the word a non-engineer would.

### 2.7 — Daily-update CTA
`api/services/daily_update_email.py:239`

> **BEFORE:** "Open your book →"

> **AFTER:** "See where things stand →" (or the program-specific noun — "Open your portfolio →" for the trader)

*Rule:* poetic-but-ambiguous loses. The CTA must say what's on the other side of the click.

### 2.8 — Narration string (already shipped, the right shape)
`api/services/reviewer_chat_surfacing.py` (ADR-365 D3)

> **BEFORE:** "Wrote to Reviewer substrate on its direction."

> **AFTER (shipped):** "Saved a working note."

*Rule:* this is the model of the whole fix — a deterministic string, plain by construction. The harvest found dozens more like the BEFORE; this is the pattern to apply to all of them.

---

## 3. The rules, extracted (the spec)

A YARNNN string shown to an operator must obey all of these:

1. **No kernel nouns.** Banned from operator-facing copy: `substrate`, `recurrence`, `wake`, `aperture`, `floor` (as jargon), `primitive`, `proposal` (prefer "a decision waiting"), `occupant`, `envelope`, `mechanical`/`Mech`, any `_*.yaml` filename, any `ADR-NNN`. Each has a plain replacement (see the glossary in §4).
2. **Lead with meaning.** First clause = what it means for the operator. Mechanism, if needed, comes after.
3. **One word per concept, product-wide.** No synonym sprawl (recurrence/task/scheduled-action). Pick the operator word, use it everywhere.
4. **Point to the action, not the file.** The operator acts through chat and the cockpit, never by editing a YAML. "Ask it in chat to…" not "set it in `_recurrences.yaml`."
5. **Spell it out.** No dev abbreviations in labels ("Mech," "auto," "cfg").
6. **Empty states teach the next step.** "Empty folder" → "Nothing here yet. [what puts something here]."
7. **CTAs name the destination.** "Open your book" → "See where things stand."
8. **Prose flows.** Read once, linearly. No ALL-CAPS shouting, no run-ons stacking three mechanisms in one sentence.

---

## 4. Operator glossary (kernel noun → product word)

| Kernel / code noun | Operator-facing word |
|---|---|
| recurrence | scheduled work / a schedule |
| wake / fire | ran / checked in / responded |
| substrate / substrate write | your files / saved a note / changed a file |
| capital action | spend / an order |
| ceiling | limit |
| proposal | a decision waiting for you |
| mandate (Primary Action declaration) | what you're here to get done |
| principles | the rules your agent judges by |
| aperture | what it's looking at / its focus |
| reviewer / occupant | your agent |
| mechanical / Mech | automatic |
| domain | (the topic name itself, e.g. "Customers") |
| ADR-NNN, `_*.yaml` | *(never shown — delete)* |

---

## 5. Where this lands (the implementation surface)

This is **deterministic product copy** — hand-authored strings in `web/components/`, `web/app/`, and a handful of backend narration/email sites (`reviewer_chat_surfacing.py`, `daily_update_email.py`, `notifications.py`, `narrative.py`). It is NOT a prompt-engineering problem (ADR-365 proved the prompt directive is inert). The fix is a **copy pass** against the §3 rules + §4 glossary, surface by surface.

Recommended order (highest operator exposure first):
1. The feed / narration labels (every operator sees these constantly) — `InvocationCard.tsx`, `reviewer_chat_surfacing.py`.
2. The autonomy + mandate + principles cards (the governance the operator configures) — `AutonomyCard.tsx`, `MandateTab.tsx`, `MandateCard.tsx`, `PrinciplesCard.tsx`. **Delete all ADR references here first** — fastest, highest-embarrassment win.
3. Navigation + empty states + filter labels — `WorkspaceNav.tsx`, `ActivityLog.tsx`, empty-state strings.
4. Settings + emails — `daily_update_email.py`, connector copy.

Each surface's pass is small, mechanical, and independently shippable. Unlike the prompt directive, every one of these is a guaranteed improvement the operator sees on the next deploy.

---

## 6. Enforcement — the guard makes this progressive, not a one-time snapshot

A copy pass without enforcement rots: the next feature adds the next `ADR-NNN` tagline. Because the problem is systemic and the cleanup is progressive, the spec is enforced by a **CI guard** — `api/test_voice_no_kernel_nouns_in_copy.py`, same shape as `test_adr209_no_filename_versioning.py`.

**How it works (the ratchet):**
- The guard reads operator-facing copy — JSX text + copy-bearing props (`tagline`/`title`/`description`/`label`/`placeholder`/`consequence`/…) + thrown-error/toast strings in `web/`, plus the backend narration/email sites — and fails on banned patterns. It deliberately ignores code comments, path constants (`const X_YAML_PATH = …`), imports, and ADR docs (none are shown to operators).
- **Phase 1 (live, 2026-06-24)** bans the two zero-false-positive classes: **`ADR-NNN` references** and **raw `_*.yaml` filenames** in copy. Baseline at introduction: **0 violations** (the four found — MandateTab tagline, ReviewerActivityPanel empty state, RecurrenceList tooltip, the Reviewer card description — were fixed in the same pass, so the allowlist ships empty). Any new leak turns CI red.
- **The allowlist is the progress meter.** When a future phase bans a fuzzier class (kernel nouns: `recurrence`/`wake`/`substrate`/`capital action`) that has a large existing baseline, the offenders go in the allowlist so the guard ships green, and each copy-pass PR deletes allowlist entries as it cleans surfaces. A deleted entry that is still violated turns red — the surface can only ratchet toward clean.

**Phase 2 (live, 2026-06-24):** the kernel-noun bans from §4's glossary (`recurrence`/`wake`/`substrate`/`capital action`/`occupant`/`primitive`) are wired with a baseline allowlist. The introducing pass cleaned the **highest-exposure surfaces** (the feed pulse labels — `'reactive wake'`/`'recurrence'`/`'wake'` → `'responded to a change'`/`'scheduled'`/`'ran'`; the autonomy governance card's run-on `'Capital actions auto-execute… Substrate writes STILL wait'` → `'Your agent can spend on its own up to your limit. It still checks with you before changing any of your files'`; system-status `'Pending wakes'` → `'Waiting to run'`), dropping the baseline 47→32. The remaining **32 are allowlisted** (`ALLOWLIST_PHASE2`) across lower-exposure surfaces (settings page, nav header, marketing pages, inline-action cards) and sweep down in subsequent passes per §5. The matcher also excludes Python metadata dict-keys (`meta["occupant"]`), which are data fields, not copy.

**Phase 2 COMPLETE (2026-06-24) — whole product, zero baseline.** Every surface — in-app operator copy AND the marketing pages — has been plain-language'd to one voice. The sweep ran in six commits over the §5 order: feed/governance/system-status → nav + empty states → settings danger-zone → inline cards + tooltips → last in-app surface → marketing (`/about` + `/invest`). Baseline 47 → **0**. Both `ALLOWLIST` and `ALLOWLIST_PHASE2` ship **empty** — the guard enforces a zero-baseline, so any new kernel-noun leak anywhere in operator-or-marketing copy turns CI red.

The operator decision on marketing (2026-06-24): **same standard everywhere.** "Substrate is the asset" → "Your accumulated workspace is the asset"; the four-pillar tagline "substrate, agents, the seat, the dial" → "the workspace, the agents, the judgment, the controls"; "Substrate can't be mutated anonymously — parent-pointered, content-addressed" → "Nothing changes anonymously — every revision names who made it, what it changed, and what came before." The thesis survives; the jargon doesn't.

Along the way the matcher gained two false-positive exclusions: property-access (`{occupant.x}`/`watch.recurrence` render a field *value*, not the word) and route-slug (`navigateToSurface("recurrence")`/`href="/recurrence"` is a route *name*). Both are correctly *not* copy.

This is the answer to "systemic-wide, validate-and-expand progressively": the guard *is* the validator, the shrinking allowlist *is* the expansion meter, and green CI *is* the no-regression guarantee.
