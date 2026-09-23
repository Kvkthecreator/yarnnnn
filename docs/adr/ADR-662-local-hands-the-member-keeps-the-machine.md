# ADR-662 — Local hands: the agent works in an app while the member keeps the machine

> **Status**: **Proposed** (2026-09-23, draft for operator review — NOT ratified). The implementation ADR that
> ADR-661 §5.4 and §8 step 6 require, carrying §6's four conditions at birth. Nothing here is built; one
> throwaway spike was driven (§3) and only its findings are kept.
> **Date**: 2026-09-23
> **Authors**: KVK (operator) + Claude (collaborator)
> **Dimensional classification** (Axiom 0): **Identity** (who acts: the member, through an instrument, in their
> presence) + **Channel** (a client-local executor for a lane tool). **No authority change**: no grant shape, no
> credential, no kernel mechanism.
> **Gate** (planned, written with the implementation): `api/test_adr662_local_hands.py`. Until then ADR-661's
> §6.4 tripwire stays ARMED — it now retires only on an **Accepted** local-hands ADR (§8), so this draft does
> not disarm it.
>
> **Origin** — the operator, in order:
> - *"one of the core intentions of expanding mac OS was … to accommodate computer use first class within yarnnn."*
> - *"the computer use i expected was … claude cowork computer use, which seems to navigate my computer AND i can
>   still use it (clicks, etc.)"* — the ruling that shaped everything below (§4 D1).
> - *"the models will need to evolve even if for now they are anthropic"* — the engine roster keeps changing (D7).
> - On outward acts and on focus-only commands: *"most autonomous approach as possible. details … i delegate to
>   you."* — D2 and D5.
> - The industry reference the operator pointed at (2026-09-23): Anthropic's Cowork computer use
>   (support.claude.com article 14128542, and the Claude desktop app's Settings ▸ System ▸ Computer use), with
>   *"Chrome browser and office suite like programs"* as the first priority — D1, D2, D11, D12.

**Preserves**: ADR-661 §6 in full (the four conditions) · ADR-645 D1/D2 (a lane IS the member's hands; no
credential moves) · ADR-615/639 (the unattended derive turn is toolless by construction) · ADR-209 D1 (one write
path) · Axiom 9 Clause B (every invocation emits an entry) · ADR-642 (three reach mechanisms, closed).

**Amends**: ADR-661 §5.1 (two claims the spike and the canon sweep proved wrong, §2) · ADR-628 D5 for local
hands only (D5) · ADR-467 D4 / ADR-568 D3 (a lane tool gated by engine capability and by client, D6–D7).

---

## 1. What it is

A member at their Mac asks their agent to finish a job in another app — reply in Outlook, fill a form, tidy a
document. The agent works **in that one app, in the background**: the member keeps their pointer, their
keyboard and whatever they were doing. Every step is said back in plain words and lands in the workspace's
record as *Kevin via Claude*. It is not a general desktop agent, not remote, and never unattended.

ADR-661's line holds and is the product: **a lab's agent clicks; ours clicks and signs.**

---

## 2. Two corrections to ADR-661 §5.1

§5.1 argued four of ADR-395 am.1 §8.7's five sandbox costs do not apply to a local act. Two of its claims are
wrong, and the design has to carry both:

1. **"Nothing leaves the machine it is already on" — false.** The model must SEE the app, so screenshots of the
   member's screen go to the model provider on every step, including whatever other people's words are in that
   window. What stays true: nothing goes to a sandbox vendor, and nothing lands in the commons unless the member
   writes it there. D1's allowed-apps scope and D3's no-retention rule exist because of this correction.
2. **"Sandbox output is untrusted input" does not apply — false; it applies at full strength.** An email or web
   page on screen is authored by a third party and can carry instructions aimed at the model (prompt injection).
   D5 carries the consequence.

The canon sweep also found ADR-661 §7.4 (*"no new grant shape"*) and §8 / `capabilities/default.json` (*"a
per-act permission the member grants"*) in tension. Resolved in D4: consent is layered, and none of it is a
`principal_grants` row.

---

## 3. The spike — driven, then thrown away (2026-09-23)

A Swift host helper and a Python loop drove TextEdit with Anthropic's `computer_toolset_20260801`, two engines ×
three tasks. **The first build posted to the global event tap (it would have moved the member's real cursor)
and was rejected before it ran** — that is D1's origin. The rebuild acts only through Accessibility.

| Task | Opus 5 | Sonnet 5 |
|---|---|---|
| Write a note | ✅ 3 rounds · 9.5s · 13k in | ✅ 4 rounds · 8.3s · 23k in |
| Title bold + larger | ❌ 25 rounds, gave up · 235k in | ❌ 25 rounds, gave up · 597k in |
| Delete one sentence | ✅ 22 rounds · 137s · 216k in | ✅ 25 rounds · 106s · 370k in |

Total ≈ 1.45M input tokens, ≈ $5.

**The background model works.** From Opus's third task on, Google Chrome was frontmost at every check while
TextEdit was edited correctly — the member was using the machine. With nobody touching it, frontmost app and
pointer were identical before and after (first task: `Claude → Claude`, pointer `502,21 → 502,21`). Window
capture by window id works while the window is occluded.

**What it found**, each now a decision:

- ⭐⭐⭐ **A background app has no key window, so every command that acts on "the current focus" does nothing** —
  menu commands (Select All, Bold, Undo, Copy/Paste) AND the app's own Bold button in its window. The AX press
  returns success; the selection stayed `82/0` before and after. Both engines failed the formatting task for this
  platform reason, not for want of skill. → **D2's ladder.**
- ⭐⭐⭐ **A receipt of delivery is not a receipt of effect.** "Pressed the "bold" checkbox" was true as an act and
  false as an outcome; nothing told the model, so it looped for 25 rounds. → **D3.**
- ⭐⭐ **Undo is a menu command, so it is gone in the background.** Both engines reached for ⌘Z after a mistake
  and were refused. → **D4b, host-side undo.**
- ⭐⭐ **An unpruned loop is expensive.** Every screenshot stays in context: a stuck task reached 597k input
  tokens. → **D8.**
- A hidden app (⌘H, or launched hidden) has no on-screen window, like a minimized one. Unhiding without
  activating works and does not take focus (measured).
- Spike defect, not a finding: ⌘←, ⇧⌘↓, ⌥← were refused as "menu commands"; they are text navigation and can be
  done directly on the selection. It inflated task 3's rounds.

---

## 4. Decisions

### D1 — Background, never takeover; the apps the member allows

The host **never posts to the global event tap, never moves the pointer, never types where the member types.**
It acts only in apps the member has **allowed**, through each app's Accessibility tree, scoped to that app's
windows; coordinates outside them are refused. It sees those windows only (capture by window id — works
occluded; a minimized window is refused with a sentence; a hidden app is unhidden without activating). yarnnn
itself is never captured.

**Allowed apps, asked once per app.** The first time a job needs an app, the member is asked; the answer is
remembered on that machine until revoked. This is the industry shape — Cowork asks *"before accessing each
application"* — and it replaces the first draft's one-app-per-job (operator, 2026-09-23: *"yes widen allowed apps (no need
one app per job)"*): a job routinely crosses apps (a link in Mail opens Chrome). An app nobody allowed stays unreachable,
which is what keeps the scope real.

**Denied apps.** A member-kept list whose requests are refused automatically, plus categories denied by
default that stay denied under D5: investment, trading and cryptocurrency apps (Cowork's default), banking,
password managers and Keychain Access, System Settings, Terminal, and yarnnn itself.

Where Accessibility is thin (custom-drawn UIs, canvases, some Electron apps) the act is **refused, never
escalated** to cursor takeover.

### D2 — The act ladder, fully autonomous

Each act takes the first rung that can express it:

1. **Accessibility** — press a control, set a field's text, place the caret, select a range, choose from a
   popup, scroll a scroll area. Background, exact, element-named.
2. **The app's scripting dictionary** (Apple Events) — formatting, menu-level commands, app objects (a Mail
   message, an Outlook draft, a Numbers cell). Background and exact, where the app publishes one.
3. **A focus borrow** — for a focus-only command neither rung can express. Taken **without asking** (operator:
   most autonomous) but **only while the member is idle** — no keyboard or mouse input for about 2 s, the
   industry behaviour (*"generally waits if you're in the middle of typing"*) — so no keystroke of theirs can
   land in the target app. The host brings the app forward, performs the one command (bounded at about 1 s),
   returns focus to the app the member was in, and verifies. Input arriving mid-borrow aborts it and the act is
   retried later in the turn. The receipt says a borrow happened.
4. **Full control** — for an app that cannot be driven in the background at all. In **Background** mode (the
   default) the host asks once per session before taking the screen, as Cowork does; in **Full control** mode
   (a member setting, D12) it takes the screen, pointer and keyboard without asking again, hides other apps
   while it works, and restores them when it stops. This is the ONE place the host may post to the global event
   tap, and only in that mode, with the member's standing choice.

The member's clipboard is theirs: copy/cut/paste are never used; text is set directly.

### D3 — Receipts state the effect, read back

Every act is verified by reading the state back (the field's value, the selection, the control's value, the
script's result) and the line says what changed — or *"no change observed"*, which the model is told in the
same words. An act whose effect cannot be read back runs only if the host can describe it truthfully as
unverified; one it cannot describe **does not run** (ADR-661 §6.2).

The lines ride the turn's ONE narrative entry (the ADR-399 shape — a turn's tool calls already persist inside
its entry), attributed `member:{user_id} via {model}`. For example:
*"In Outlook: opened Dana's email · typed a reply (84 words) · pressed Send."*

**Screenshots are never persisted.** The commons is shared; a member's screen is not. They are transient turn
content, as ADR-585 D3 rules for turn reach.

### D4 — Consent is layered; no new grant shape

- **The machine**: macOS grants Accessibility, Screen Recording, and Automation per target app. The member grants
  these once; they are tied to the app's code signature (D10).
- **The apps**: the member allows each app once (D1). The allowed set is the scope — an allowed region, as
  DP36's scopes are allowed paths — kept on the machine, never in the commons.
- **The disclosure**: the consent sentence names where screenshots go (*"screenshots of Outlook go to
  Anthropic"*), as ADR-585 D5 requires for any engine.

Nothing lands in `principal_grants`; ADR-661 §7.4 holds.

**D4b — host-side undo.** Before each text or value edit the host keeps the element's prior value. The agent
can revert its own step (replacing the ⌘Z it cannot use), and the member can revert any receipted step.

### D5 — The agent may complete outward acts

Operator ruling: the agent may press Send, Submit, Pay. This **amends ADR-628 D5** (*"no publish from chat"*)
for local hands only — publishing through yarnnn's own outbound machinery stays exactly as ADR-628 rules.

The risk it accepts, stated plainly: a message or page on screen can instruct the model, and a steered agent
can now send. Anthropic's own guidance recommends human confirmation before consequential acts; the operator
chose autonomy. What bounds it:
- only apps the member allowed (D1) — a hostile page can reach no app they did not allow, and never a
  default-denied one (banking, trading, password managers). ⚠️ With several apps allowed, a page in Chrome CAN
  steer an act in Outlook; the allowed-apps scope is wider than the first draft's one-app scope, and this is its cost;
- the provider's prompt-injection classifier on screenshots stays **on**;
- the frame rule: text inside a screenshot is content, never instruction;
- the member sees each step live and can stop (§6.3);
- every act is receipted, and text edits can be reverted (D3, D4b).

**Revisit trigger**: the first observed act the member did not intend, or a member asking to confirm before
sending.

### D6 — Transport: a lane tool with a client-local executor

The lane turn stays ONE streamed request (`api/routes/lanes.py`). When the model calls the local-hands tool, the
server emits a `client_tool` frame and awaits an in-process future keyed by turn and call id; the shell executes
and posts the result to `POST /api/lanes/{id}/tool-results/{call_id}`, and the same turn continues. One lane
runner, one attribution stamp, one receipt path.

- **Fails closed**: a closed window, a stopped turn or a server recycle ends the act.
- **Only the originating shell can answer**: the frame carries a per-turn nonce the result must echo.
- **Only shell turns are offered the tool**: a turn from the web or another device never is. "Attended" here
  means present *at that machine*.
- **Constraint recorded**: the future lives in memory — correct on today's single worker and single instance
  (`render.yaml`); a second instance needs it keyed somewhere shared.

This is not ADR-413 D2's forbidden shape: the ENGINE is the model's tool loop, and the desktop is the
environment it acts on — no session is serialized into a completion.

### D7 — Engines by capability, never by name

The engine roster keeps changing (operator). Computer use is a **capability on the `LANE_MODELS` entry**, like
`vision` today: `computer: <adapter id>` or absent. Adding a capable model is one registry line.

The host speaks one small **provider-neutral vocabulary** (see the window, act at a point, set text, send a
key to the app, run a script). Each provider's computer-use protocol is an **adapter in `model_router.py`**, the
one transport home, translating that protocol into the vocabulary. The first adapter is Anthropic's
`computer_toolset_20260801` (GA, no beta header; the screenshot rides inside `tool_result`, which echoes
`toolset_name`).

⚠️ The lane's tool messages are strings today and images ride a separate user message
(`lane_runner.py:1756-1827`); the installed LiteLLM (1.83.9) knows only `computer_20241022`/`_20250124`, and
production's is unpinned (`litellm>=1.80.0`). The adapter needs image-in-tool-result through the router — verify
the deployed LiteLLM before choosing between passing through it and an Anthropic path inside the router.

### D8 — Cost is bounded by design

- **Prune**: keep only the last few screenshots in context (the API's context editing).
- **Bound**: a local-hands turn has its own round and spend bound, named and visible — `_LANE_MAX_ROUNDS = 8` is
  far too low (a job is dozens of acts) and a silent ceiling is the wrong one.
- **Stop when stuck**: N consecutive rounds with no verified change (D3) end the turn and say so.
- **Metered**: screenshot tokens land on the one ledger with a rate row (ADR-413 D1).

### D9 — Attended only

Local hands exist only in a member's lane turn from the shell (ADR-615: attendance is presence). The unattended
derive turn stays toolless by construction (ADR-661 §6.1); no standing declaration can reach this tool.

### D11 — The cheapest reliable path first

Industry order (Cowork): *"1. Connectors… 2. Browser… 3. Screen interaction."* yarnnn's version:

1. **The kernel and the member's connectors.** A job on a document's CONTENTS is a file job — yarnnn reads and
   writes `.docx`/`.xlsx`/`.pptx` itself (ADR-395 am.2) — and a job a connector covers runs through turn reach.
   No screen involved.
2. **The browser, through a browser channel.** Cowork uses *"your own Chrome browser through Claude in Chrome"*,
   an extension — page structure, not pixels, and it works on background tabs.
3. **The screen**, by the D2 ladder — for work that must happen live in an app.

**The two first-priority targets** (operator):
- **Chrome.** Phase 1 drives it by the D2 ladder — Chrome exposes page content to Accessibility, to be measured
  in spike round 2. Phase 2 is a yarnnn Chrome extension paired with the shell over native messaging, the
  industry route. To verify before relying on it: recent Chrome refuses the remote-debugging port on a person's
  default profile, which rules out driving it that way.
- **The Office suite.** Word, Excel, PowerPoint and Outlook for Mac publish scripting dictionaries — rung 2 is
  exactly what fixes the spike's formatting failure — and expose their windows to Accessibility. Content edits
  prefer the file (path 1); the screen path is for live work: an Outlook reply, an open workbook.

### D12 — The settings surface, on the machine

Modelled on the Claude desktop app's Settings ▸ System ▸ Computer use, in the shell's settings (device-local:
the grants are per machine, so they are not workspace settings):

- **Enable computer use** — off until the member turns it on.
- **How the agent uses the apps you allow** — **Background** (default) or **Full control** (D2 rung 4).
- **Restore hidden apps when it finishes** — for Full control.
- **Allowed apps** and **Denied apps** — lists, with the default-denied categories shown (D1).
- **Accessibility · Screen Recording · Automation** — each shown as granted or not, with the button that opens
  the matching macOS pane.

### D10 — macOS first, and signing is a prerequisite

macOS only, **15 or later** — Cowork's floor for background operation (ADR-661 §7.6: screen capture and
synthetic input are the most platform-divergent APIs there are).
The Accessibility, Screen Recording and Automation grants attach to the **code signature**; an ad-hoc-signed
build loses them on every rebuild. **The Apple Developer ID is therefore a prerequisite for this capability, not
only for distribution.**

---

## 5. The canon tensions, resolved

| Tension (found by the sweep) | Resolution |
|---|---|
| ADR-628 D5 *"no publish from chat"* vs. sending from Outlook | D5 amends it for local hands, by operator ruling, with the risk named; default-denied categories stay denied |
| ADR-395 §8.7 cost 5 waved off by ADR-661 §5.1 | §2 correction 2; D5's bounds |
| lane-frame §6 refuses a screenshot channel | That refusal is of yarnnn's OWN panes, where addressable ids exist; another app has no addressable alternative. Screenshots here are the environment, transient (D3), never a context channel |
| ADR-413 D2, no stateful session through the tool loop | D6: the desktop is the environment, not an engine |
| ADR-413 D1, inputs only as substrate projections | Screen content is transient turn content, as ADR-585 D3 rules for turn reach |
| ADR-467 D4 / ADR-568 D3, one uniform lane surface | Amended: a tool may be gated by engine capability (D7) and by client (D6); `vision` is the precedent |
| DP23 / ADR-307, the gate queues | Local acts are attended and immediate; the queue exists for absence (ADR-307 D3's own reason). No per-call modal is added (ADR-635 §3 holds) |
| ADR-661 §7.4 vs. "per-act grant" | D4: layered consent, no grant row |
| PARTICIPANT_REGISTER "skip narrating what you will do" vs. §6.3 visibility | Visibility is the host's live step list and the receipts, not the model's prose. The register stands |

---

## 6. What this ADR does NOT do

- Build anything. §7 orders it.
- Take the member's cursor or keyboard, except in Full control mode the member chose (D2 rung 4).
- Touch the member's clipboard (D2).
- Persist a screenshot (D3).
- Add a grant shape, a credential, a Render service or a reach mechanism.
- Scope Windows (ADR-661 §7.6).
- Adopt the remote sandbox (ADR-395 am.1 §8.7 stands).

---

## 7. Build order

1. **Developer ID** (operator) — D10's prerequisite.
2. **Host** (`src-tauri`): the D2 ladder behind Tauri commands; capability roster entries with explicit scopes
   (ADR-661 §7j: a permission is not a capability); the Accessibility, Screen Recording and Automation prompts.
3. **Transport** (D6): the `client_tool` frame, the result route, the nonce, fail-closed.
4. **Adapter + capability** (D7), after verifying the deployed LiteLLM.
5. **Receipts, undo, cost bounds** (D3, D4b, D8).
6. **The driven trace** (ADR-661 §6.4 / ADR-577 §7): a real job in a real app, through the real path, producing
   the real receipt — then ratify.

---

## 8. Gate

Planned `api/test_adr662_local_hands.py`, each arm proven RED in place:

- the host posts nothing to the global event tap and never activates an app outside a borrow;
- a borrow requires idle input and restores the prior frontmost app;
- every act kind has a receipt sentence and a read-back;
- the derive turn stays toolless;
- the tool is offered only to shell turns, and only on engines with the capability;
- no screenshot is written to the substrate;
- the clipboard API is never called.

**Changed now, with this draft**: ADR-661's §6.4 tripwire retires only on a local-hands ADR whose Status is
**Accepted** — a Proposed draft must not disarm the guard it exists to satisfy.

---

## 9. Open questions for ratification

Answered from the industry reference (2026-09-23): the idle threshold and borrow bound (D2: ~2 s idle, ~1 s
borrow, measured in round 2) · which apps first (D11: Chrome and the Office suite) · the permission model
(D1: allowed apps, asked once) · the settings surface (D12).

Still open:

1. **The live step list's home.** The reference is silent. Proposed: the steps in the chat lane (they are the
   record), a small always-on-top host panel with Stop (the member is looking at another app), and a global stop
   shortcut; macOS shows its own screen-recording indicator.
2. **The deployed LiteLLM version** (D7) — read it from the API's build log before choosing the adapter path.

**Ruled (operator, 2026-09-23): no tier limits, and first-class.** *"we should first surface the desktop features
as first class, no need to limit per tiers."* Unlike Cowork (Pro/Max only), local hands and the desktop shell
are available on every plan, and they are a surfaced product capability, not a hidden beta. What "surfaced"
builds — the shell's settings section, an entry from the web product, a download page — is its own step, and a
public download waits on the Developer ID (D10). A workspace-owner switch for members is not built; revisit if
an owner asks.
