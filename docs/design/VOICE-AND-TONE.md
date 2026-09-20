# Voice & tone — how the product speaks to a member

**Status**: living spec. First cut 2026-06-24 (the ADR-365 harvest); recut 2026-09-15 after the copy
regrew a second vocabulary. **Guard**: `api/test_voice_no_kernel_nouns_in_copy.py` — three phases,
one allowlist per phase, each only ever shrinks.
**Sibling**: how an *agent* speaks is `PARTICIPANT_REGISTER` (ADR-638), structure rules, A/B-validated.
This document is the other half: the deterministic strings the product itself renders.

> The lever is deterministic copy. ADR-365's A/B showed a prompt directive does not move free prose;
> the June harvest showed the jargon lived overwhelmingly in hand-authored UI strings, and the
> September recut found it had grown back there — in files the guard never scanned. Every string
> below is ours to write; none of it needs a model.

---

## 1. The standard

Write the way macOS writes to a person who has never opened Terminal. Concretely:

1. **Say what they can do here, not how it is built.** *"Every file in your workspace, with its history"*,
   never *"Raw substrate browser — every file in the workspace, with revision history."*
2. **Their words.** The nouns on their screen: chat, agent, document, deck, post, image, file, folder,
   connection, workspace. Never ours: lane, artifact, substrate, principal, grant, declaration, proposal, queue,
   witness, verdict, kernel, commons, aperture, capture, receipt-as-jargon. The map is §3.
3. **One idea per sentence. Full stops, not dashes.** A pane subtitle is one or two short sentences.
   No semicolons, no em-dash chains, no parentheticals stacking a second mechanism.
4. **Second person, present tense.** *"Nothing goes out until you approve it."*
5. **Say the consequence, then the reason, only if the reason changes what they do.**
6. **Empty states name the next step.** *"Nothing yet. To-dos, activity, and balance warnings show up here."*
7. **Buttons and links name the destination.** *"Show all activity"*, never *"The whole timeline"*.
8. **Errors say what happened and what to do.** *"Couldn't disconnect Slack. Nothing changed."*
9. **No internal references.** No ADR numbers, no `_name.yaml`, no table names, no tool names, no
   "deployment", "router", "lane", "turn".
10. **One word per concept, product-wide.** The word chosen in §3 is the word everywhere; a synonym
    is a defect (the June audit found *recurrence*, *task* and *scheduled action* for one thing).

Sentence-case labels, no trailing period on a one-line fragment (a launcher summary, a fact row),
periods on sentences. Brand is `yarnnn`, lowercase, as the wordmark spells it.

## 2. Slot budgets — copy fits the slot it renders in

A string that truncates with "…" has failed regardless of its words. Every slot below has a render
site and a budget; the budget is measured, not guessed.

| Slot | Render site | Budget | Receipt |
|---|---|---|---|
| Launcher summary | `web/components/shell/Launcher.tsx` — `truncate text-xs`, one line | **≤ 312 px at 12 px system font** (a 390 px phone: 390 − 2 border − 32 padding − 12 gap − 32 icon). Desktop is 434 px. In practice ≤ ~48 characters. | 2026-09-15: all 14 served summaries measured with `canvas.measureText` at the app's font stack; longest 298 px (*"This workspace's name, members, billing, and usage"*). The old Files line measured 420 px. |
| Pane subtitle | `PaneHeader` in `web/components/settings/SettingsPaneShell.tsx` — wraps | Two short sentences, ≤ ~130 characters | The Connected subtitle went from 4 clauses and two semicolons to three sentences. |
| Fact row (Reads · Writes · Chat · Agents) | Reach card + connection page, `<dd>` wraps | One or two sentences; a fragment if one clause | Served by `describe()` in `api/services/reach_status.py`. |
| Empty state | dashed box | Title ≤ 4 words + one sentence naming what puts something here | |
| Tooltip (`title=`) | native | One sentence, no dash | |
| Toast / error | `useFeedback` | One sentence: what happened, then what to do | |
| Dock tooltip | served `title` | The surface's name only | |

A new surface's summary is written to the launcher budget first; if it cannot say what the surface is
for in 48 characters, the surface's name is wrong, not the budget.

## 3. The word map — kernel noun → member word

The left column is banned from rendered copy (the guard's three phases); the right column is the one
word used everywhere. Where the product had already chosen a word, that choice stands — consistency
outranks preference.

| Ours | Theirs | Notes |
|---|---|---|
| lane, thread, model-pinned helper conversation | **chat** (the item), **conversation** (what happens in it) | "New chat", "Archive chat" |
| engine | **engine** | Kept: chosen in June, shown in four places, gate-pinned (ADR-585 D5). Not "model". |
| agent, colleague, resident, helper, system agent | **agent** | "Your agents, and the ones you can hire" |
| substrate, commons, operation, the record | **workspace**, **your files** | |
| artifact | **file**, or the medium: **deck**, **post**, **image**, **document** | |
| revision, revision chain, revertible | **version**, **history**, **can be undone** | Files UI still says "revision" in places — see §6 owed |
| attributed, signed | **under your name** | "signed" is acceptable in a receipt line |
| platform, connector, integration, credential | **connection** (the link), the app's name (Slack, Notion) | "New connection" everywhere; an MCP server is "a server" only where a URL is pasted |
| capture, observation file, intake lane, yield | **reads**, **what it brought in**, **saved in Downloads** | |
| proposal, queue, witness, verdict, autonomy setting | **decision**, **To do** (the pane), **your approval**, **decided by** | "X needs your approval before this runs" |
| standing declaration, contract, cadence | **standing work** (the pane, kept), **instructions** (the file), **on a schedule** | |
| principal, grant, evict, revoke | **member**, **access**, **remove** | "Anything not allowed is hidden" |
| capital, external write, substrate write (queue families) | **Spending**, **Outbound messages**, **Workspace changes** | |
| aperture, scope (verb) | **which tools**, **what it can reach**, **choose** | |
| turn, deployment, model router, lanes enabled | *(never shown)* — "Chat isn't available here yet" | |
| rasterize, stage, artboard, derivation | **download as a PNG**, **save a PNG copy next to this file** | |
| surface (noun), launcher (as jargon) | the surface's **name**; **Launcher** (a proper noun, the grid icon) | "Search, or paste a file path" |
| recurrence, wake, occupant, primitive, capital action, ceiling | scheduled work · ran · your agent · *(name the act)* · spend · limit | Phase 2 (June), unchanged |
| ADR-NNN, `_name.yaml`, table names | *(never shown — delete)* | Phase 1 (June), unchanged |

## 4. Where the copy lives

Most of it is in `web/components/` and `web/app/(authenticated)/`. Four backend files **serve** prose
the UI renders verbatim, and those are the ones a web-only grep misses:

| Served from | What | Rendered at |
|---|---|---|
| `api/services/kernel_surfaces.py` | every launcher title + `summary` | Launcher rows, Dock tooltips |
| `api/services/reach_status.py` → `describe()` | the Reads · Writes · Chat · Agents rows per connection | Reach → Connected cards; the connection page. **The only place a reach sentence may be written** (ADR-644). `frame_paragraph` in the same file is the agent's prompt, not copy. |
| `api/services/connectors.py` → `CONNECTOR_CAPTURE_BINDINGS[…]["reads"]` | the "Reads" fact per platform | same |
| `api/services/notifications.py` → `NOTIFICATION_KINDS` | each notification kind's label, description, email note | User Settings → Notifications |
| `api/services/account_email.py` | subject, preheader, body of the account emails | the member's inbox |

Frontend string tables worth knowing: `web/lib/proposal-labels.ts` (the act labels and the dial line
the bell shows), `web/components/chat-surface/toolLabels.ts` (what a running tool says it is doing),
`web/components/queue/QueueBody.tsx` (`FAMILY_META`), `web/components/notifications/StandingWork.tsx`
(`PROBLEM_COPY`, `runStatusLine`), `web/components/workspace-concepts/WorkspaceMembersCard.tsx`
(`ROLE_META`, the access modes).

## 5. Enforcement — the guard

`api/test_voice_no_kernel_nouns_in_copy.py` scans rendered string contexts (JSX text, copy-bearing
props, thrown errors, toasts) under `web/` plus the served-prose files in §4, and fails on any banned
pattern that is not allowlisted. It also reads every VALUE in `web/messages/*.json`, every locale
(ADR-660 D4): copy that moves into a catalog leaves each JSX context above, and a guard that did not
follow it would go green over an emptying codebase. A catalog key is never rendered and never matched.
Three phases:

- **Phase 1** (2026-06-24): `ADR-NNN` and `_name.yaml` in copy. Zero-false-positive classes.
- **Phase 2** (2026-06-24): recurrence · wake · substrate · capital action · occupant · primitive.
- **Phase 3** (2026-09-15): model-pinned · lane · commons · principal · artifact · attributed · declaration ·
  witness · verdict · rasterize · scaffold · no-op · aperture.

**The allowlist is the progress meter.** A phase ships green with its baseline allowlisted; each pass
deletes entries as it cleans a surface; a deleted entry that is still violated turns red. Phase 3's
baseline after the introducing sweep: four marketing lines (owed) and two developer-facing strings.

Scope rulings made 2026-09-15: the served roster and the reach sentences are IN (the June guard sat
green over `web/` while "Raw substrate browser" shipped from a Python file for months);
`web/app/admin/` is OUT (the platform operator's own console, reading the record's column names —
the retired-vocabulary ratchet holds it); `kernel` is not a pattern (it fires only on data:
surface keys, tier values, owner fields). The in-string test measures from the regex match, not the
first substring hit — `"substrate_paths": …  # substrate` is a comment.

A new pattern earns its place with a receipt: a string that shipped, on a surface a member saw.

## 6. The passes

### 2026-06-24 — phases 1 and 2, whole product to zero
Six commits over feed/governance → nav + empty states → settings → inline cards → marketing.
The operator ruled *same standard everywhere*, marketing included. Baseline 47 → 0.

### 2026-09-15 — the second generation, and the launcher fits
Trigger: the operator's two screenshots — the launcher truncating every row's summary with "…", and
the Reach cards reading *"only when you send a file to Slack from the Text pane (Send to Slack) — your
click, receipted beside the file, never scheduled"*. The guard was red at baseline (8 admin-console
hits) and had never scanned the file the launcher summaries come from.

Swept, highest exposure first: the 16 roster summaries (all measured under the phone budget); the
Launcher chrome; the Desktop first-run and returning states; the bell (balance warning, empty state,
the dial line); the user menu; Chat (rail, empty states, errors, "lane" → "chat"); Reach (three
subtitles, both empty states, the footer, the AI-connections note, every served sentence in
`describe()`, the three capture "reads" lines); Notifications (three subtitles); Standing work (both
dictionaries, header, empty state); the decision queue (families, empty state, "Decided by");
Workspace Settings and User Settings subtitles and the notification explainer; the members pane
("principal grants" → "access"); the connection pages (Capture → *What it reads*, Yield → *What it
brought in*); the finder; the attached-server page; Text (landing, editor notes, the Editor empty
state); Slides/Blogger/Images (taglines, template descriptions, share/export tooltips, "artifact" →
the medium); Files (version history tooltips); Agents (Craft → Skills, the door to Reach); the served
notification kinds; the joined/removed account emails.

Gates re-anchored to the fact instead of the phrase: ADR-628 and ADR-644 ("never captures" →
"never reads"), ADR-338 ("Nothing awaiting your decision" → "Nothing to decide"). The phrases the
gates still pin are facts, not wording: the door's name (*Send to Slack*), *your click*, *cannot send*,
the ADR-585 D5 disclosure (*engine · you picked · pasting*).

**Owed** (the next pass, in this order):
1. Marketing: the four Phase-3 allowlist lines in `web/app/{how-it-works,invest,developers}` and
   `web/components/landing/AppShowcase.tsx`.
2. Files: "revision" → "version" across `RevisionHistoryPanel`, `PaneActivityRail`, `NodeDetailsPanel`,
   `TextEditor` Properties; "Get Info" stays.
3. The Launcher's two dormant rows (`setup`, `program`) render in flat search with nowhere to go
   (`navigableSurfaces` filters on `route !== ''`, and theirs is undefined). A row a member cannot open
   is a dead door: drop them from search or give them one.
4. `web/lib/utils.ts::TOOL_DISPLAY_NAMES` disagrees with `toolLabels.ts` — one table.
5. StudioPublish and SendToSlack tooltips ("your click, your account"), `StudioDesignTab` ("type ramp"),
   the WordPress not-launched lines, `WorkspaceDangerZone` descriptions ("re-scaffolded"),
   `WorkspaceDeleteCard` ("purge"), `SourcesCard` ("no-op", "attests") — a dormant pane.
6. `AgentsSurface` "Runs on" renders a raw model id; use the engine label.
7. The Reach sidebar group label *The boundary*; the Notifications group *Operate*. Small, but a
   member reads them.

### 2026-09-18 — the retired seat, and the three shapes the guard could not see

Trigger: the operator's screenshot of the Chat pane's not-enabled state — *"Chat colleagues aren't
available on this deployment yet. Your conversation with Freddie is unaffected — summon it from the
chat button."* Two defects in one sentence: it named the machine (§3 row 21 bans "deployment") and
sent a member to summon **Freddie**, a seat ADR-632 retired. An empty state pointing at someone who
no longer exists reads as a broken product.

Fixed, all rendered copy: the Chat empty state (now *"Chat isn't available yet"* + what turns it on,
per §1.6); the To do queue's `verdictGiverLabel`, which returned the literal `'Freddie'` for **every**
non-human reviewer, so *"Freddie approved"* shipped on `/reach` and `/notifications` (now *"Your
agent"*, the §3 word, and the three dead `?? 'Freddie'` guards that rode on it are gone);
`decisions.ts::identityLabel`, which mapped a live `ai:` identity to "Freddie" and had **zero
callers** — deleted, not relabelled.

**The line on `freddie:`** — CLAUDE.md keeps it as a display-resolved attribution prefix on
historical revisions, and that stands: `RevisionFootnote` and `attribution.ts` name who actually
signed a past revision, and rewriting them would misattribute real history. A label for a PAST
signature stays; a label for a LIVE actor does not.

**Phase 4** (`freddie` · `steward` · `deployment`) ships at zero: a retired seat's NAME is not a
kernel noun, so phases 1–3 structurally could not catch it. What the retirement list names is banned
here the moment it is retired.

**Three detector holes found while falsifying it** — the first falsification came back green on all
three arms, which is the finding, not the fix:
1. **Multi-line JSX text.** The rules were line-local (`>text<` on ONE line, or a copy-bearing prop).
   Prettier wraps any sentence past the print width, so a two-line `<p>` put its words on lines with
   no bracket and no quote — invisible to *every phase*. This is how "Freddie" survived the
   2026-09-15 sweep **of the very pane it shipped in**. Fixed with a state machine scoped to prose
   elements (an unscoped one runs away into TS generics: 5,985 lines vs 892, all copy).
2. **A returned label.** A helper mapping an id to words (`verdictGiverLabel`) is copy in a `return`
   — neither JSX text nor a prop. Note the near-miss: the first version required 2+ words and so
   could not see `'Freddie'`, a one-word name, which was the entire defect.
3. **A `{/* … */}` block inside a prose element** read as text (3 false positives).

The multi-line fix exposed **35 pre-existing violations** the guard had never been able to see —
24 Phase-3, 8 Phase-2, 3 Phase-1, concentrated in `/invest` and Studio. Baselined per §5 so the
detector improvement lands without a 35-site copy rewrite; they are now **owed item 0**, ahead of
the marketing line above, because they are the same marketing pages with a bigger true count.

## 7. Korean (ADR-660 D6)

The catalog is `web/messages/ko.json`; its English source is `en.json`, key for key.

- **`해요체` throughout** — the polite-informal register Korean product interfaces have converged on.
  Never `합쇼체` (it reads as a terms-of-service page), never `반말`.
- **A control is a noun or a bare stem** — `저장`, `삭제`, `로그인` — not a sentence. A sentence is for
  what happened or what to do next: `다시 시도해 주세요.`
- **Loanwords where Korean software already uses them** — `워크스페이스`, `에이전트`, `파일`, `이메일`.
  The product's name and brand names stay in Latin script.
- **§3 applies in translation.** A kernel noun does not come back as its transliteration; translate the
  member word in the right-hand column, not the left.
- **An error names the control as it is labelled.** The English reset hint said *"choose Reset password"*
  over a button labelled *"Forgot your password?"*; a faithful translation would have carried the
  mismatch. Both languages now name the button the member can actually see.
- **Slot budgets (§2) are measured in the rendered language.** Korean is usually shorter than English
  per idea and wider per glyph; check the slot, do not assume.

