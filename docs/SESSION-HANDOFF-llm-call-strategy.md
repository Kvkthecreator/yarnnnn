# Session handoff — 2026-08-12 (the LLM-call strategy arc, ADR-556…559)

`origin/main` @ `57eada1`. Everything below is **pushed**; the working tree's
only changes belong to another lane (see §5).

> **Why this file has a suffix.** `docs/SESSION-HANDOFF.md` is a concurrent
> lane's live handoff (the ADR-549/554/555 arrival arc). Overwriting it would
> have destroyed their record — the exact class of loss their own note warns
> about. Two lanes, two handoffs; delete this one in the commit that absorbs it.

## 1. What the session was

The operator asked for an audit of the chat surface and "our LLM calling
strategy," wanting members to be able to pick a model. That question sat on
three layers of unexamined machinery, so it became four ADRs:

| Commit | ADR | What |
|---|---|---|
| `83e8f97` | 556 | machinery is not a picker — `SYSTEM_CALLS`, keyed by call type |
| `513f19b` | 557 | the router chokepoint + transport/product flag split |
| `6eb2c30` | — | `probe_router_transport.py` — the transport, verified live |
| `af5339f`·`ac5f19e` | 558 | chat asks which engine; agents are personified |
| `afb66c2`·`57eada1` | 559 | engine registry: currency · retirement · availability |

## 2. The three defects found, all of which had shipped

1. **The wake funnel's cheap tier never ran once.** `tier_2_decision` called
   `chat_completion` with a `user_id`/`caller` API that never existed on any
   wrapper. Born broken at `37426c5` — every call raised `TypeError` into a bare
   `except` and failed open to `escalate`, so **every idle tick became a full
   Sonnet wake at `max_rounds=20`** for the funnel's entire life.
2. **`route_completion` never checked its own flag.** `MODEL_ROUTER_ENABLED` was
   a convention each caller had to remember; radar forgot, and a flag-off sweep
   **reached Gemini over the network**.
3. **`repurpose` read `response.text` off a `-> str`** — a registered primitive
   that would `AttributeError` on every live call.

All three were invisible to imports, types, and every existing gate. That is
why the new gates **execute** rather than grep.

## 3. Findings that outlived their ADRs

- **`MODEL_ROUTER_ENABLED` is ON in prod** — ADR-439's status line said
  otherwise and cost most of a session. Corrected in that ADR with receipts.
  Anthropic + OpenAI + Gemini keys are live on **both** API and Scheduler
  (proven by radar's nightly Gemini sweep running from the Scheduler).
- **All 65 live lanes pinned `claude-sonnet-4-6`**, 56 of them bound Studio
  lanes. Found by querying the DB *before* editing the roster dict — deleting
  the row would have orphaned the workspace.
- **Reasoning models spend `max_tokens` thinking before emitting text.** At
  `max_tokens=10`, GPT-5 returns empty content with `finish_reason: length`. At
  the real 4096 lane budget: gpt-5 **2560 tokens (63%)**, gemini-2.5-pro 1726,
  gemini-2.5-flash 1450.

## 4. OWED — carry into the next session

**A. Lane token-profile re-measurement — DONE 2026-08-12.**
Probe ran clean: 43 pass · 0 FAIL · 1 info (DeepSeek "Insufficient Balance",
§4.C). C6 green — gpt-5/gemini-pro/flash all still speak at 4096; the
`OBSERVED_REASONING_AT_4096` figures did not need to move. The Sonnet-5-specific
measurement (count_tokens on identical corpora + a live lane-shaped ask through
`route_completion` on both Sonnets):
- tokenizer ratio **x1.35–1.47 (mean x1.39)** — heavier than the ~30% assumed;
  4096 is ~2940 Sonnet-4.6-equivalent tokens.
- live ask: both `finish_reason=stop`; Sonnet 5 used 890/4096 (22%). No
  truncation, no empty reply. **The budget holds on evidence**; the figures are
  recorded at the `_LANE_MAX_TOKENS` comment (parity raise would be ~5700).

**B. Click-passes.**
1. **The greyed-engine door — DONE 2026-08-12, in prod, full observed loop.**
   DeepSeek was served `available: true` post-deploy (the refusal map is
   process-local; the 07:31 restart wiped it — by design). Drove the loop as
   the operator: door offered DeepSeek → lane created → one message →
   "Insufficient Balance" refusal → reopened door → **DeepSeek shown disabled,
   `opacity-45`, "provider unavailable", `aria-disabled=true`** — not hidden.
   Lane archived after. Three findings from the pass, none blocking:
   - the door does NOT refetch availability on open — within one page session a
     member can keep picking a just-refused engine (fresh state needs a reload);
   - the failed turn shows the **raw litellm exception string** to the member
     (`litellm.BadRequestError: DeepseekException - {...}`) — operator words on
     member glass;
   - that error bubble is **not persisted** — after reload the member sees
     their message with no reply and no explanation at all.
2. **The engine picker** (ADR-558) — partially seen during the pass (brand
   marks render; "last used" chip appears and is correctly suppressed while the
   engine is dark). Still owed: cast-join verification (colleague joins via the
   cast, not at the door).

**C. DeepSeek's account is unfunded.** Now handled gracefully (greyed with a
reason) rather than fixed. Fund it or leave it dark — no code change either way.

## 5. Landmarks for whoever picks this up

- **The working tree is NOT clean, and that is correct.** `web/package.json` +
  lock (ProseMirror deps) and `web/lib/authoring/flow/sanitize.ts` belong to
  **ADR-560** (`5c72f23`), a concurrent lane. Left untouched; every commit in
  this arc used `git commit --only`.
- **`test_agent_registry` is 166/170 at HEAD** — four FE-side failures,
  pre-existing, verified byte-identical with this session's work stashed.
- **The Sonnet 5 rate mirror reads x1.50 on purpose.** ADR-559 D1.a: the table
  carries standing list price, never a promo rate. **Do not "fix" it.**
- **`LANE_MODELS` is the turn-time whitelist.** Deleting a row breaks every lane
  pinned to it; superseded engines carry `retired: True` and keep their rate row.
- **ADR-439's ordering check was replaced, not repaired**, after breaking three
  times on invariant-preserving changes. It now *executes* the invariant. If you
  refactor the unpriced guard it should stay green — if it goes red, a billable
  call really is escaping.
