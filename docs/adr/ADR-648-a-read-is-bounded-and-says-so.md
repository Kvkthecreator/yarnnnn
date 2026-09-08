# ADR-648 — A read is bounded and says so; history is bounded in the unit that costs

**Status**: Accepted · 2026-09-09
**Completes [ADR-647](ADR-647-the-conversation-prefix-is-cacheable.md)** (which
cut what a re-sent prompt COSTS; this bounds what enters it in the first
place). Respects [ADR-427 §8](ADR-427-binary-native-substrate-and-the-storage-seam.md) (a read answers
honestly about what it did not give you) and ADR-495 D2 (the visibility floor
is an authorization bound; these are budget bounds and never widen it).

---

## 1. The ask

> "any improvements we can do to our message handling themselves, or session
> conversation management for further efficiency gains? first, audit to see if
> against just conventional industry best practices are implemented (meaning,
> are we doing at least the standard par), and then, we can look for
> incremental gains."

Audit first, then act. The audit's answer is **mostly at par, with two gaps of
the same shape.**

## 2. The audit — where we already stood

| Practice | Status |
|---|---|
| Prompt caching, system frame | ✅ ADR-634 |
| Prompt caching, conversation prefix | ✅ ADR-647 |
| **Stable-prefix ordering** (volatile content LAST) | ✅ **already correct** |
| Breakpoint budget | ✅ 2 of Anthropic's 4 |
| Cross-turn cache reuse | ✅ 82% of consecutive calls inside the 5-min TTL |
| Tool traffic excluded from the stored transcript | ✅ deliberate (ADR-411) |
| History bounded | ⚠️ by COUNT, not size |
| Tool results bounded | ❌ **not bounded at all** |

The third row deserves note because it is the most commonly botched item in
this whole area and we had it right by construction: the frame's volatile
`posture_section` (which embeds the bound artifact's current bytes, so it
changes on every edit) sits at **position 15 of 16**, with **18 characters**
after it. Everything stable precedes everything volatile, which is exactly
what a prefix cache wants. That was not luck — it fell out of ADR-606's
"the job overlay comes last" composition rule — but it was also never asserted,
and now is.

## 3. The two gaps, and why they are one gap

**D1 — `ReadFile` had no size cap.** `ListFiles` beside it has had one since it
was written. Measured on production 2026-09-09: workspace files run to 178,206
chars (~45K tokens), **6.4% exceed 40K**, and lane calls peaked at **86,799**
prompt tokens against a **19,999** median. One read of one large file could
inject more than twice the median entire prompt. **The tail is the large read.**

**D2 — `_HISTORY_WINDOW = 20` bounds the count of messages.** Count is not what
a provider charges for: the same 20 messages are 2K tokens in one conversation
and 200K in another. The budget was **unpredictable by construction**, which is
why a "fixed" window still produced a 4.3x spread between median and max.

Both are the same error: **bounding in a unit nobody bills in.**

## 4. The decisions

**D1 — a read returns a bounded window, and the notice is the feature.**
`READ_FILE_MAX_CHARS = 100_000` (~25K tokens). Every file at p90 (34,125 chars)
returns whole; only the largest few percent clip, so **the common case is
byte-identical on the wire** — an unclipped read gains no new keys at all.

⭐⭐⭐ **The clip is not the feature; the NOTICE is.** A silently truncated read
is the worst outcome available here: the model answers confidently from a
fragment it believes is the whole file, and nothing downstream can tell. That
is the recorded `silence_is_the_most_dangerous_wrong_answer` failure — and it
was **already learned once in this very file**, for binary reads
(`_binary_file_notice`, ADR-427 §8). Re-learned for large ones.

So a clipped read carries `truncated`, `total_chars`, `returned_chars`, and a
message that **forbids the specific wrong behaviour** rather than merely
describing the clip: *"This is a PORTION of the file, not all of it — do not
answer as though you have seen the rest."*

**D1.a — the continuation is a MECHANISM, not advice.** `offset` is a real
schema parameter, and a clipped result names the exact value to pass
(`next_offset`). **Telling a model to "request more" without a parameter to do
it with is an instruction it cannot follow** — the shape of a rule that reads
as satisfied and is not. Reassembling every window reproduces the file byte for
byte (gate-asserted); a clip that loses or duplicates a byte is corruption, not
a bound.

**D2 — a second ceiling, in chars.** `_HISTORY_MAX_CHARS = 120_000` (~30K
tokens), **alongside** the 20-message count, not replacing it. Deliberately
generous: this is a tail guard against the pathological turn, not a tightening
of the normal one, and the median conversation never approaches it.

**D2.a — it drops from the FRONT, oldest first, and never from the middle.**
⚠️ **This is not a free design choice — the cache dictates it.** A prompt cache
matches on a PREFIX, so removing a message from the middle invalidates every
cached token after it. A "smarter" trim that kept one interesting old turn
would force a full re-write at 1.25x and **cost more than the tokens it
saved**. Oldest-first is the only shape that leaves the survivors contiguous.
With 82% of consecutive calls landing inside the cache TTL, this is the common
path, not a corner.

⭐ **The newest message is never dropped, even alone over the ceiling** — it is
the thing being answered. A ceiling that can eat the question is not a ceiling;
it is a bug that appears only on the largest input.

## 5. What we deliberately did NOT do

Two standard next moves were considered and rejected, and the reasons are
architectural rather than effort-shaped:

- **Conversation summarisation / compaction.** The industry-standard answer to
  a long transcript, and it fights this system's premise directly: **the
  workspace is the shared memory and the transcript is not** (ADR-408 D6).
  Summarising mints a second, lossy memory that no principal authored and no
  revision signs. If a turn's substance matters, it belongs in a file — which
  is the mechanism we already have.
- **Aggressive trimming for its own sake.** Counter-intuitive but measured:
  with 82% cache reuse, an old prefix token costs **10%** of list price, while
  trimming it **breaks the prefix and re-writes at 125%**. Below the ceiling,
  keeping history is cheaper than trimming it. **Trimming a cached prefix can
  cost more than leaving it alone.**

## 6. Verification

- `api/test_adr648_bounded_context.py` — 37 checks. Falsified three ways:
  making the clip SILENT reds 12; a middle-drop trim reds 3; removing the
  `offset` schema parameter reds 2.
- Regression: `test_adr647_history_caching` · `test_adr647_member_engine` ·
  `test_adr634` · `test_adr557` · `test_adr411` · `test_adr623` ·
  `test_adr533` · `test_adr588` · and the MCP trio (`test_adr543` ·
  `test_adr545` · `test_adr621`) — all green. The connector surface composes
  its own read (`mcp_composition`, deliberately not a call into the kernel
  handler), so it is unaffected by design rather than by luck.

### ⚠️ A gate that crashes reports nothing, and nothing looks like passing

Falsifying D1 the first time produced **no output at all**: the gate caught the
defect, then raised `KeyError` on the next line's raw `_r["returned_chars"]`
and died before printing its verdict. Every field read is now `.get()`, and the
reassembly loop is bounded so a broken clip cannot hang the run.

**Second instance the same day** — `test_adr557` had been crashing on a deleted
`services/radar.py` for seven weeks (ADR-647 §7). A gate must fail *legibly*;
one that dies mid-file is indistinguishable from one that never ran.
