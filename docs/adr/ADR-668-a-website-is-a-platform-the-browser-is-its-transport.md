# ADR-668 — A website is a platform; the browser is its transport

> **Status**: **Proposed** (2026-09-25) — for the operator's ruling. §7 is built with this document whatever the
> ruling (the audit's fixes that needed no ADR, each behind a gate arm proven RED); §8 waits on it, and the gate
> reads this Status line to know which of the two it is holding.
> **Date**: 2026-09-25
> **Authors**: KVK (operator — the direction quoted in the derivation) + Claude (collaborator)
> **Dimensional classification** (Axiom 0): **Substrate** — what browser work acts ON, a site, gains a home in the
> workspace · **Channel** — the trace of an act becomes portable and readable past the boundary.
> **No authority change**: no grant, no credential, no consent or scope on the server. The executor, attendance
> and the member's own site lists are ADR-662's, untouched; the run and its sharing are ADR-666's.
> **Gate**: `api/test_adr668_a_website_is_a_platform.py`.
> **Derivation**: [the browser is a transport; the site is the platform](../analysis/the-browser-is-a-transport-the-site-is-the-platform-2026-09-24.md)
> — the 2026-09-24 audit of ADR-661–667 and the extension at HEAD `678f645`, the way ADR-666 derives from the
> 09-20 analysis. Its findings are cited by number below (F1–F10); each was verified against code, not a document.

**Amends** — ADR-664 D5 (`list_integrations.websites` and the reach section name the sites the workspace works
on, derived from it — not "any"; D5 here) · ADR-666 D1 (`CONTRACT.md` is the outcome; the how is the site's —
D3) · ADR-666 D2 (a step carries `url`, and `args` minus anything secret-shaped — D4) · ADR-666 §3 (the scope
now holds at the executor too — D8) · ADR-630 D3 (one line: `metadata.sites` — D2) · ADR-667 D1 (setup by
doing gains its second half — D3). **Records** F4 against ADR-665 §3 (D6). **Preserves** — ADR-662 D5/D9/D15
(attended, immediate, the extension is the one executor) · ADR-645 D1 (no credential moves; a site skill holds
craft, never a secret) · ADR-639 (one drain, one declaration shape) · ADR-596 D1 and ADR-640 (nothing here is an
agent; a skill names no agent; no agent carries a record of its work) · ADR-666 D6 (the conversation stays
private; the run is shared) · ADR-231 (no task abstraction: a site skill is craft, a run is a trace).

## 1. The problem

The operator, 2026-09-24: *"we need to potentially separate the mechanics of internet computer use, which Claude
and his existing skills already provide, [from] the context handling per specific web pages, which are essentially
workflows and platforms … not a limiting factor for multiple LLM engine agnostic considerations … how we should
consider capturing the life cycle of this information."*

The audit's verdict: the mechanics are **already separated and engine-neutral** (F1 — five typed function tools,
carried by LiteLLM to any provider, no computer-use protocol, no screenshots, no per-site code; the model reaches
the page only through JSON arguments). They are commodity, and the code keeps them small. What is missing is not a
better browser. Take an act in the member's browser through Axiom 0 (audit §4.1):

| Dimension | The answer | Home today | Verdict |
|---|---|---|---|
| Identity — who | the member, through an agent, in their own Chrome | ADR-645 D1 · 662 D15 · 666 D1 | right |
| Trigger — when | a turn the member is in; a schedule may raise, never act | ADR-662 D9 · 666 D4 | right, until §8 is measured |
| Mechanism — how | five generic acts, provider-neutral | `primitives/browser.py`, the extension | right and complete |
| Channel — where the result goes | the run (shared) + the kept file (attributed) | ADR-666 | right, shape lossy (F5) |
| Purpose — what for | the contract: what must be true | `CONTRACT.md` | right, polluted with the how (F10) |
| **Substrate — what it acts on** | **a site** | — | **absent** |

A connection has a platform row (`platform_connections`, ADR-635: reach + a tool roster + an aperture + a landed
record); a file has a path; **a site has a string in a YAML list**. Every defect the audit measured follows from
that one absence:

1. **No site context (F2).** `BrowserRead` is `document.body.innerText` clipped to 12,000 characters and up to 250
   elements, the same for every site, every run. The second run of *keep competitor prices from
   shop.example.org* re-discovers shop.example.org from scratch. The only prose kept between runs is the previous
   run's record, and the frame tells the agent to read it only when a run **failed** — a repair instruction, not a
   learning one.
2. **The contract does two jobs (F10).** ADR-666 rejected `WORKFLOW.md` on a sound rule (a procedure on a schedule
   with no contract is the retired recurrence) and resolved it by folding the procedure *into* `CONTRACT.md`: *"what
   must be true when the run finishes* and *how to get there, in one prose file."* ADR-667's setup-by-doing then
   writes *"a contract written from the steps that worked"* — a procedure signed as a contract. The outcome check is
   buried in navigation prose, and the site knowledge is trapped in one declaration's folder where no other
   declaration on the same site, and no other workspace, can read it.
3. **No roster (F3).** The workspace cannot say *we work on shopify.com and x.com* although its own `_standing.yaml`
   files do. `list_integrations.websites` says "any site"; Reach's browser row says the same; `reach_status`
   derives nothing from the declarations.
4. **No act is classed consequential, and a superseded ADR says otherwise (F4).** ADR-665 §3: *"every act the
   executor classes consequential (send, post, submit, pay — the extension already names them per act)."* The code
   does not: `record.act` ∈ {opened, read, pressed, filled, back, failed, refused}; a fill can carry
   `submitted: true`, and that is all. ADR-666 §3 declined to build a consequence class — correct while attended,
   and the one thing the proposal queue (ADR-307, live and receipted) is already shaped to receive.
5. **The step has no address, and a run is invisible past the boundary (F5).** `runs.steps` =
   `{name, text, ok, record{act, subject, changed}, at}` — no URL, so a step cannot be replayed, audited for scope
   after the fact, or turned into site knowledge without the model re-narrating it. `runs` is exposed over no MCP
   verb, and a chat run writes no record (ADR-666 D3), so a foreign LLM cannot see what yarnnn did.
6. **The scope held at one door (F7).** `_outside_scope` refused what `BrowserOpen` named; a link followed from an
   allowed page was not checked, and the extension's gate knew only the member's lists, never the run's `sites`.
   Known and owed (ADR-666 §3); named here because it belongs at the executor, the only place that sees where the
   tab is.
7. **Drift on read (F9).** The timeout receipt said *"The desktop app did not answer in time"* — stale since ADR-662
   D15 made the extension the executor; the sentence reaches the model and the run's steps.

## 2. The decision, in one sentence

**A website is a platform the workspace works on. The browser is how the workspace reaches it — the way an MCP
server is how it reaches Notion.** The transport (hands + reach) is built and stays generic. The platform is what
remains, and every one of its parts has a home in a noun the canon already holds. Nothing below adds a table, a
grant shape, a credential, a Render service, an app or an agent.

## 3. Decisions

### D1 — A site is a platform; its parts, and where each lives

| The site's… | is a… | home | why this and not a table |
|---|---|---|---|
| **craft** — where things are, what to read, what buttons mean, what is consequential here, what never to do, what went wrong last time | **skill** (ADR-630) | `skills/sites/{host}/SKILL.md` — workspace-authored, attributed, versioned, forkable | a file is engine-agnostic, exportable, diffable, shareable across workspaces, and read on demand at zero frame cost when the site is not in play. Site knowledge in *code* (a per-site adapter in the extension) ties yarnnn to today's DOM and a maintainer; in *prose* it ties it to nothing |
| **scope** — which hosts a piece of work may open | the declaration's `sites` | `_standing.yaml` (unchanged) | a scope is per work, not per site |
| **consent** — may the agent act here at all, on this machine | the extension's lists | `chrome.storage.local` (unchanged, ADR-662 D15) | consent is the member's and the machine's, never the workspace's |
| **aperture** — which acts here are consequential | a line in the site skill + an executor floor (D6) | the skill; `extension/page.js` | ADR-635's per-tool aperture, decided where it can be seen: at the element |
| **roster** — where does this workspace work | **derived** from declarations' `sites` and the site skills that exist (D5) | `reach_status`, Reach's browser row, `list_integrations.websites` | ADR-664 D5 already named the field; it is filled from the workspace instead of from "any" |
| **trace** — what was done there | the run, with a portable step (D4) | `runs.steps` | F5's fix; the executor writes it, so it is the same for every engine |

### D2 — The site's craft is a skill: `skills/sites/{host}/SKILL.md`, offered by `metadata.sites`

A site skill is an ordinary member skill (ADR-630's `skills/` half — never the kernel mirror under
`system/skills/`), at `skills/sites/{host}/SKILL.md`, whose frontmatter names the hosts it is for:

```yaml
---
name: shop-example-org
description: How shop.example.org is laid out and worked — where the price table is, which button is Publish.
metadata:
  sites: [shop.example.org]
---
```

**Amends ADR-630 D3 by one line**: beside `metadata.apps` (the panes a skill is for) and `metadata.needs` (the
connector categories it reads through, ADR-635 D7), **`metadata.sites`** names the hosts a skill is for. It is
offered when the turn's declared `sites`, or the host of the page the agent is on, meets one (the same
subdomain grammar as `site_allowed`); withheld-and-counted otherwise; silence means not a site skill. Hidden at
presentation, never at authorization (the ADR-395 posture): any member reads any skill by `ListFiles`. A site
skill names no agent (ADR-596 D1), authorizes nothing (ADR-464 §3), and holds no secret — *what never to do* is
craft, a credential is not (ADR-645 D1).

### D3 — The contract is the outcome; the how is the site's

**Amends ADR-666 D1.** For browser work `CONTRACT.md` says **what must be true when the run finishes** — and only
that. How to get there is the site's, read from the site skills of the `sites` the declaration names. A contract
stays load-bearing (ADR-603 D5 is untouched: no schedule without one); it stops carrying a procedure that drifts
with a site's DOM and belongs to every declaration on that site, not to one.

**Amends ADR-667 D1.** Setup by doing gains its missing second half. After a chat run on a site, the Supervisor's
agent offers two things, not one: *keep doing this* (declare, as now) **and** *remember how this site works* —
write or revise `skills/sites/{host}/SKILL.md` from the run's steps (act · url · subject · changed, D4). The
second act is what makes the next run shorter than this one — the tenure claim the product makes (ESSENCE:
outputs that improve with tenure), and the first place browser work can demonstrate it: steps per run on a
site's second run against its first is measurable (§8, the instrument).

### D4 — The portable step

A step is readable by something that is neither yarnnn nor this engine. **Amends ADR-666 D2's `steps`**:

```
{ at, act, url, subject, changed, ok, args?, text }
   │    │    │      │       │      │     │      └─ the executor's sentence — what the agent was told happened
   │    │    │      │       │      │     └─ the act's arguments, minus anything that could hold a secret
   │    │    │      │       │      └─ did it succeed
   │    │    │      │       └─ measured, not claimed (the page fingerprint / the field's read-back)
   │    │    │      └─ the element's label, or the page's title
   │    │    └─ where the tab WAS when the act ended
   │    └─ opened · read · pressed · filled · back · wrote · outside · refused · failed · stopped
   └─ when
```

- **The executor writes it; the model only calls tools.** No step DSL the model must emit — the one discipline that
  keeps the trace identical across engines.
- **`url`** is built with this document (§7): the extension already knew it on open, read and press; it now says it
  on back and on a refusal (the tab's address, when the tab is what moved); the lane carries it through the receipt
  frame into `runs.steps`, the record file renders it, `RunOut` serves it. `steps` is jsonb — no migration.
- **`args`** waits on the ruling (§8): a fixed allowlist per tool — `BrowserOpen.url`, `BrowserClick.ref`,
  `BrowserFill.ref` and `submit` — and never a fill's `text`: a field can hold a password (ADR-662 D3, the same
  rule `_SUBJECT_ARGS` already keeps for the spinner).
- `text` stays for the member and the record; `url` + `act` + `subject` + `changed` are what a site skill is
  written from, what an auditor checks scope against after the fact, and what a foreign LLM reads over D7.

### D5 — The roster is derived, never stored

**Amends ADR-664 D5.** The reach section's browser sentence, Reach's browser row and `list_integrations.websites`
name **the sites this workspace works on** — the union of every declaration's `sites` and every host with a site
skill — beside the standing fact that the browser reaches any website. Derived at read time from the substrate;
no `sites` table, no `browser_platforms` row (Axiom 1: a table would be a second authority over a fact the
workspace already holds). A prompt change — it lands with a CHANGELOG entry and the ratchets (§8).

### D6 — The aperture is named, not built; F4 is recorded

ADR-665 §3's sentence — *"the extension already names them per act"* — was false when written, and the superseded
ADR now says so at its head. Consequence is a property of a site's **controls**, not of a generic verb (`BrowserClick`
is a read on one page and a Send on another), so it is decided where it can be seen, in two layers:

- **declared**, per site, in the site skill — a line naming which acts are consequential here (*Publish sends the
  post; Save keeps a draft*);
- **an executor floor** — a form submit, or a control whose label reads send · post · submit · pay · buy · delete ·
  confirm — the heuristic the extension can apply with no site knowledge, worded as a floor so a member's *"why
  did it stop before Confirm"* has an answer.

**Attended acts stay immediate** (ADR-662 D5; the queue exists for absence, ADR-307 D3). The aperture becomes
load-bearing only when nobody watches — it is ADR-666 §8's third precondition (§5), and nothing here rules §8.

### D7 — Runs are readable outside a lane: the `runs` verb

A run is shared with every member of its workspace (ADR-666 D6). It was invisible to everyone else: a foreign LLM,
or a member's other tools, could see a run only through the record `.md` — which a chat run does not write. Two
ways to close that, and **one is chosen**:

- *A record file for chat runs too.* Refused. A chat run belongs to no folder — ADR-666 D3's reason stands. A file
  for it would need an invented home, and would land a `system:standing` revision for work that is not standing,
  on every conversation that touched a browser: substrate noise with no reader.
- **A read verb over the ledger.** Built (§7). `runs` joins the interop surface (ADR-543/584: `_INTEROP_VERBS`,
  `mcp_scopes.VERB_SCOPES`) at the **`files:read`** tier — a token that may read the files may read what the agents
  did to make them — and reads through the caller's client under the connection's workspace binding (ADR-573), the
  way `list` does. Each run is served boundary-safe: who it ran as is a **display name**, never an id; the
  conversation it happened in stays private (no `lane_id` crosses, ADR-666 D6); each step is D4's portable shape.
  `wrote` is the revision id — `open` reads the file, `history` its chain. The record file stays what it is: the
  human face of a declared run.

### D8 — The scope holds at the executor

**Amends ADR-666 §3.** The run's `sites` ride the act — in the `client_tool` frame, through the page
(`hands.ts`), to the extension — and `gate()` refuses **where the tab IS**, before any consent question: an act
outside the scope is an `outside` step naming the site and carrying the tab's address, and the member is never
asked to allow a site the work may not use. The server still refuses what `BrowserOpen` names before the act
leaves it (ADR-666 D1). Two doors, both closed — a rule enforced at one of two doors is not enforced. A chat turn
carries no scope and is not scoped, as before.

- **Extension 0.1.2** performs it. `EXTENSION_MIN_VERSION` stays `0.1.0`: an older extension ignores `sites` and
  is gated exactly as it was (the server's door, and the step naming the site — ADR-666 §3's accepted attended
  posture). The floor rises when the executor's check becomes load-bearing — §8's second precondition — and not
  before: a hand-installed copy does not update itself (ADR-664 am.2), and raising the floor today would strip
  the browser from every member who installed by hand this week, silently.
- **The desktop relay.** The page passes `sites` to `browser_act`; a host that does not declare the argument
  (≤ 0.4.3) never reads it, and the act is gated as before. Forwarding it is one line in
  `src-tauri/src/hands/mod.rs`, owed with the next host cut (no Rust toolchain on the machine that wrote this).

## 4. The lifecycle — how the information is captured, and by what

```
   the site skill   skills/sites/{host}/SKILL.md    craft: HOW this site works       ← written / revised from a run's
        │  read by the turn when the site is in play (D2)                                 steps (D3 — "teach by doing",
        ▼                                                                                  ADR-665 §2.1, finally with a home)
   the declaration  {folder}/_standing.yaml + CONTRACT.md   WHAT must be true (D3) · WHERE (sites) · WHEN
        │  raises
        ▼
   the run          runs row (state · steps · revision · cost)   the TRACE, shared, live (D4) → the record file (declared
        │  writes                                                                                 runs, the human face)
        ▼                                                                                        → the `runs` verb (D7)
   the kept file    a revision, member:{id} via {model}          the PRODUCT
```

Four layers, four existing nouns, one arrow each. The contract returns to being an outcome; the how lives with the
site, where every declaration on that site, every member and — exported — every other workspace can read it.

## 5. What this does not do — the refusals, so the ADR stays narrow

- **No `sites` / `browser_platforms` table.** The roster is derived (D5).
- **No browser app, no browser agent.** ADR-665 §4 ruled the Supervisor is the surface; ADR-596/639 rule nothing is
  an agent for standing work. A site skill names no resident.
- **No per-site code in the extension.** Five acts, whatever the site. The day it grows a Shopify branch, yarnnn owns
  a scraper. Site knowledge is prose the model reads.
- **No consent or scope on the server.** Consent stays on the machine; scope stays on the declaration and is enforced
  where the tab is (D8).
- **No `WORKFLOW.md`.** The how is keyed by *site*, not by *declaration*: sites are shared across declarations and
  workspaces, declarations are not — and a site skill is craft the canon already knows how to bound, index, mirror
  and fork (ADR-630).
- **No model-authored step format.** The executor writes the receipt (D4).
- **No ruling on ADR-666 §8.** Unattended browser work needs, in order: (1) the pending act in shared state — the
  `runs` row, not `client_tools._TURNS` (F6); (2) the scope enforced at the executor — D8, now built, with the floor
  raised so an executor that cannot enforce it is not offered the tools; (3) an act aperture — consequential acts
  queue as proposals when nobody watches (D6; ADR-307 D3: the queue exists for absence); (4) a site skill, so a run
  nobody watches is not also a run discovering the page for the first time (D2). Then §8's own measurement — how
  often attended runs stall, how often a sign-in stops one — decides whether option B is worth its risk. The vault
  (the parked *access is brokered* analysis) stays parked on the same trigger.

## 6. Canon tensions, resolved

| Tension | Resolution |
|---|---|
| Axiom 1 — state lives in files | craft is a file (D2); the roster is derived from files (D5); the trace stays an act-ledger row (ADR-666 D2) |
| ADR-630 D3 — the index is scoped by app, then by reach | and now by site — the same mechanism, a third key, silence the open default |
| ADR-603 D5 — no schedule without a contract | the contract stays (D3); what leaves it is the how, which was never the contract |
| ADR-666 D3 — a chat run writes no record | held; it is read by the verb instead (D7) |
| ADR-662 D9 — attended only | held; nothing here acts unattended; §8's preconditions are named, not met |
| ADR-645 D1 — no credential moves | a site skill is craft; a secret has no home in it |
| ADR-596 D1 — no authority on a being | a skill names no agent; the offer to write one is the posture's, a judgment, not a grant |

## 7. Built with this document — the audit's no-ADR fixes, each gated

| What | Where | Driven or gated |
|---|---|---|
| F9 — the timeout receipt names the browser, not the desktop app | `services/client_tools.py` (`no_answer`) | gated; arm proven RED by restoring the old words |
| D4 — `url` on every step | `extension/background.js` (`back` says where it went; a refusal carries the tab's address), `lane_runner` receipt frame, `runs.render_record`, `routes/runs.RunOut` | **driven** — `extension/e2e/run.mjs` *each act says where the tab was when it ended*; gated through the real lane loop |
| D8 — the scope holds at the executor | `lane_runner` (`sites` on the frame), `web/lib/shell/hands.ts`, `extension/policy.js::withinScope`, `background.js::gate`, extension **0.1.2** | **driven** — e2e in Chrome for Testing 29/29 with four new arms; falsified in place (`withinScope` stubbed → two arms RED); gated |
| D7 — the `runs` verb | `mcp_scopes.VERB_SCOPES`, `mcp_composition.compose_runs` (+ `_portable_run`, `_portable_step`), `mcp_server/server.py` (roster, tool, output schema); every published copy of the roster: `docs/features/mcp/{tool-contracts,README,CONNECTING}.md`, `SERVICE-MODEL.md`, `docs/gitbook/{api-reference/mcp-tools,integrations/mcp-connector}.md`, `web/lib/openapi.ts`, the developers hub and both catalogs; the read tier's consent sentence | gated — ADR-563 16/16, ADR-543 7/7, the gitbook roster arms; **driven** on the live MCP server 2026-09-25 08:11Z from claude.ai: `whoami` lists `runs` and words the read tier with it; `runs(limit=3)` returned three of the operator's own browser runs (x.com, medium.com) in the portable shape, `url` on every step |
| ADR-666 §3, `local-hands.md`, SCHEMA-NOTES, the handoff | the owed extension-side check is closed; the step's `url` recorded | — |

## 8. What waits on the ruling (Accepted →)

1. **The site skill** (D2): `parse_skill` lifts `metadata.sites`; `_applies_to` gains the site test against the
   turn's declared `sites` and the page's host; `creating-skills` teaches the site shape.
2. **The offer** (D3): `services/apps/supervisor.py` — after a chat run on a site, offer to declare **and** to
   write or revise the site skill from the run's steps. A prompt change: `api/prompts/CHANGELOG.md` names the
   observed failure (the second run re-reads what the first learned) and the ratchets run (ADR-632 §5, ADR-630).
3. **The derived roster** (D5): `reach_status.browser_sentence` / `browser_does` and `list_integrations.websites`
   from the declarations and site skills. A prompt change, same discipline.
4. **`args` on the step** (D4) and the host's one line (D8).
5. **The instrument**: steps per run on a site's first run vs its later runs — the alpha-ops harness, before the
   aperture heuristic, unattended or a vault is argued.

The gate holds this list against the Status line: while **Proposed**, none of it is built ahead of the ruling
(`metadata.sites` is not parsed; the posture does not offer a site skill); on **Accepted**, each is asserted.

## 9. Gate

`api/test_adr668_a_website_is_a_platform.py`, script-shaped: the timeout receipt names no desktop app; the
`client_tool` frame carries `sites` for a declared run and not for a chat turn, and the receipt carries `url`
(driven through the real lane loop); the record renders a step's address; the page forwards `sites` to the
extension and the host; the extension's gate takes the scope, refuses before consent as `outside`, threads it
through both doors, and every act says where the tab was; the e2e instrument holds the arms; the manifest is at
or above 0.1.2 and the server's floor is unchanged; `runs` is rostered, scoped `files:read`, read-only, reads
through the caller's client, emits no member id or lane id, serves the portable step, and is named in every
published copy of the roster; the refusals hold (no `sites` table, no `WORKFLOW.md`, no per-site branch in the
extension); ADR-665 carries F4; ADR-666 §3 no longer owes the extension-side check; the ledger row and the
glossary entry exist; and §8 against the Status line.

## 10. Driven (2026-09-25)

`extension/e2e/run.mjs` in Chrome for Testing, extension 0.1.2 loaded unpacked: **29/29** — an open inside the
run's sites goes through; an open outside them is refused as `outside`, naming the site, with no consent
question; an act on a tab that has left the run's sites is refused where the tab is, with its address; a chat turn
is not scoped; each act says where the tab was when it ended. **Not driven**: a real run on production in a Chrome
holding 0.1.2 (the operator's own Chrome, the same trace ADR-662's ratification used) — owed in
`docs/SESSION-HANDOFF.md`. **Driven since**: the `runs` verb on the live MCP server (§7), which also showed D4's
`url` on every step of the operator's own production runs of 08:04–08:09Z that day.
