# Positioning — The Judgment-Seat Psychographic, Not an Occupation List

**Date:** 2026-06-08
**Hat:** B (external-developer surface — strategic discourse capture). This is an
analysis/finding, not canon. It *recommends* a positioning frame for operator
(KVK) ratification; it does not edit `ESSENCE.md` / `NARRATIVE.md` /
`GTM_POSITIONING.md`. If ratified, those land the change.
**Origin:** the 2026-06-08 moat→GTM→activation discourse
(`moat-architecture-audit-2026-06-08.md`), pushed by the operator from
*occupation-framing* to *psychographic + use-case throughput* — explicitly
asking for the YARNNN analog of Claude Code's / Cowork's / Manus's single
cross-cutting throughput.
**Status:** Proposed positioning frame. Supersedes the ICP framing in
`docs/working_docs/strategy/GTM_POSITIONING.md` v3.0 (2026-04-01), which is two
months stale (pre-ADR-216 orchestration-vs-judgment, pre-ADR-282 ground-truth
rename, pre-ADR-310/312, pre the judgment-seat reframe) and still leads with
"five domain experts, $19/mo, your AI team."

---

## 0. The question this resolves

The moat audit proved the architecture earns the moat (four load-bearing
properties enforced at the write path / gate / topology). But the moat is a
*retention/defensibility* property — it tells a builder why to trust the thing
for the long haul. It is **not an acquisition or activation property**: no
stranger wakes up wanting "attributed parent-pointered revisions." A startup
dies of the activation problem long before it enjoys the moat.

So the binding question became: **who is the user, stated as a throughput that
cross-cuts diverse occupations** — the way Claude Code's throughput cross-cuts
diverse engineers? The operator's correction was sharp and correct: stop framing
the lead by **occupation** (trader vs author — still a job title), frame it by
**psychographic + use-case** (the behavioral relationship to the work).

The operator's stretch set (deliberately diverse occupations):
A&R at a music label · IT product manager · solo founder building a web app ·
alpha trader · international partnerships manager at a global fashion brand.

The test: **is there one throughput under all five?**

---

## 1. The discipline — what Claude Code's throughput actually is

Claude Code did not win "software engineers." It won a **psychographic doing a
use-case**:

> *A person who has a durable, structured working substrate they live inside, who
> is tired of an AI that talks **about** their work and wants one that operates
> **on** it — under their review, leaving a trail they can read.*

The occupation (engineer) and the substrate (repo) are incidental. The
**relationship to the work** is the throughput — which is why it generalizes:
Cowork is the same throughput over docs/slides instead of repos; Manus is the
same throughput over arbitrary web tasks. The throughput is the unit; the domain
is a skin.

YARNNN needs its own one-sentence throughput at the same altitude.

---

## 2. The finding — your architecture already named the throughput

The throughput is **FOUNDATIONS Axiom 8 (ground-truth substrate), read as a human
psychographic instead of an architecture axiom.** Axiom 8's three structural
properties — *consequence-bearing · substrate-grounded · calibratable* — are
exactly the behavioral signature of the user.

Run the operator's five-occupation stretch against Axiom 8:

| Occupation | The recurring judgment they make | Their working substrate | Consequence they personally bear (ground truth) | Calibratable over tenure? |
|---|---|---|---|---|
| **A&R / label** | "Sign this artist? Push this track? Allocate this budget?" | roster notes, track evals, streaming/market signals, deal terms | streams, chart movement, deal ROI — *winces when a pass becomes a hit elsewhere* | yes — taste calibrates against hit-vs-passed |
| **IT product manager** | "Ship this? Prioritize this? Accept this tradeoff?" | PRDs, decision logs, incident history, stakeholder context | adoption, incident rate, roadmap-vs-reality drift | yes — calibrates against shipped-vs-predicted |
| **Solo founder (web app)** | "Build this next? Respond to this user how? Spend here?" | spec, decision log, user feedback, metrics | retention, conversion, churn — *every wrong call costs runway* | yes — calibrates against what moved the metric |
| **Alpha trader** | "Take this position? Within risk?" | signals, positions, risk envelope, P&L | P&L — the cleanest, fastest wince | yes — money-truth, the canonical instance |
| **Intl partnerships mgr (fashion)** | "Pursue this partner? On these terms? In this market?" | partner dossiers, deal pipeline, regional context, past-deal outcomes | deal closed/stalled, partnership revenue, brand-fit fallout | yes — calibrates against which partnerships compounded |

**All five are the same psychographic.** Every row is: *a person who holds
recurring, consequential, judgment-heavy decisions over an accumulating body of
domain context, who personally bears the outcome, and whose judgment should get
sharper as the substrate densifies.* That is not five ICPs. **It is one
psychographic, and Axiom 8 already defined it** — the architecture *is* the
throughput; it was just written in kernel vocabulary.

> This is provable from the architecture (the table above is a derivation, not a
> survey). What is **not** yet proven is anything about how these people *behave
> as buyers* — see §6 hedges.

---

## 3. The throughput, in human terms

The one-sentence throughput (the YARNNN analog of Claude Code's):

> **"You hold a recurring, high-stakes judgment over an accumulating body of work
> you can't afford to get wrong — and you want a seat that holds your standing
> intent, makes those calls the way you would, learns from what actually
> happened, and leaves a trail you can audit."**

Compressed to a one-liner:

> **"An agent that doesn't do your tasks — it holds your judgment seat."**

This cross-cuts A&R → PM → founder → trader → partnerships *cleanly*, because the
throughput is not the domain (music/software/trading/fashion) and not the
occupation — it is the **psychographic relationship: recurring consequential
judgment over accumulating substrate.** Whoever feels *that* is the user,
regardless of title.

### Why "judgment seat" and not "accumulated intelligence"

The stale GTM v3.0 reached for a psychographic ("intelligence-hungry
professional — needs accumulated domain intelligence") and landed on the
*substrate* half. That is the weaker half: "accumulated intelligence" is what
every inferred-context incumbent also promises (OpenAI Memory, Copilot, Glean),
and it commoditizes as retrieval saturates. The **judgment seat** is the half
incumbents structurally cannot offer — it requires a persona-bearing role that
applies *the operator's* discipline and is calibrated against ground truth over
tenure (THESIS Commitment 2; ADR-216 orchestration-vs-judgment; the moat audit
§3.1). Lead with the seat; the substrate is what makes the seat get better.

---

## 4. The activation split — fast vs slow ground truth (NOT trader vs author)

The earlier discourse nearly made a wrong decision: "lead archetype = trader vs
author." This psychographic reframe **dissolves that question.** Trader and
author are not two lead candidates — they are two instances of one psychographic,
and so are all five occupations. The autonomous-execution vs substrate-continuity
split (from `alpha-author-discourse-2026-05-15.md`) is not a *who* split. It is a
**speed-of-ground-truth** split:

| Ground-truth speed | The wince comes back in… | Instances | Activation wedge (the felt first-session win) |
|---|---|---|---|
| **Fast** | minutes → weeks | alpha trader · solo founder on metrics · partnerships mgr with a live pipeline | *"Bring a real decision you're facing this week. Watch the seat reason it against your declared rules. See the outcome reconcile."* |
| **Slow** | months | A&R pre-release · author pre-audience · PM on long-arc bets | *"Bring the body of work you already have. The seat audits it for the drift / contradiction / gap you can't see yourself."* |

The activation consequence:

- **You market the psychographic** ("a seat that holds your judgment") — universal.
- **You onboard through a fast-ground-truth instance** — because it lets a
  stranger *feel the loop close* in one session. The slow instances cannot do
  this; their first month produces no reconciled outcome.
- **You let the slow-ground-truth instances expand the TAM later** — once the
  activation story is proven on the fast instances.

Crucially, the fast wedge is **not trader-specific** — it is *fast-ground-truth-
specific*. "Bring a real decision; watch it get judged against your rules; see it
reconcile" works for the founder's "should I ship X" and the partnerships lead's
"should I pursue Y" exactly as well as the trader's "should I take this
position." Trader is merely the cleanest *built* instance today.

---

## 5. The strategic consequences (named, for decision)

1. **The bundle unit has been wrong.** Bundles have been chosen per-occupation
   (trader, author, commerce, defi, prediction). The unit that matters for
   activation is **per-ground-truth-speed**. The next bundle should be chosen by
   "what gives the next-cleanest *fast*-ground-truth activation for a *broader*
   domain," not "what occupation is interesting." Founder-on-metrics and
   partnerships-on-pipeline are both fast-ground-truth and far broader TAM than
   trader.

2. **The lead is a two-part statement, psychographic-first:**
   - *Marketing throughput (universal):* "an agent that holds your judgment seat,
     not one that does your tasks."
   - *Activation instance (fast-ground-truth):* onboard through the instance
     where the loop closes visibly in one session.

3. **The two active bundles (trader + author) are hedging the fast/slow bet.**
   That hedge costs focus pre-traction. The fast instances activate cleaner;
   resolve whether the *lead* wedge is the cleanest fast instance (trader today,
   founder-on-metrics for broader TAM) rather than splitting attention across
   one fast + one slow.

4. **This supersedes the occupation-list ICP in GTM_POSITIONING v3.0 and the
   "solo consultants with recurring client obligations" entry-wedge in
   NARRATIVE.md** — both are occupation framings the psychographic move retires.

---

## 6. Honest hedges (do not skip)

- **The psychographic is proven; the buyer-behavior is a bet.** That all five
  occupations satisfy Axiom 8 is derivable from the architecture (§2 is a proof).
  That *fast*-ground-truth instances activate strangers better than slow ones,
  and that this psychographic converts at all, are **hypotheses about human
  behavior with zero real-user data behind them.** The moat audit's caveat holds:
  the architecture has been stress-tested to death; the activation path has been
  tested only by *proxy operators*, which is not a confused stranger.

- **Volume risk in the psychographic itself.** "People who make recurring
  high-stakes judgments over accumulating substrate" is a **premium, low-volume**
  psychographic — senior people, not the mass market. Good for willingness-to-pay
  and switching cost; **bad for top-of-funnel volume.** This is the *opposite* of
  Claude Code's psychographic (huge, because every engineer has a repo). The five
  occupations prove **range, not volume.** The open question this raises: is there
  a *fast-ground-truth, high-volume* instance of this psychographic (the
  founder-on-metrics one is the closest — far more numerous than traders)? That
  might be the real lead wedge, not trader.

- **Self-selection in the demo.** A fast-ground-truth first-session win requires
  the stranger to *bring a real decision they're facing this week*. That is a
  high-intent ask — it filters for people already in the psychographic, which is
  good for conversion quality and bad for casual top-of-funnel. The wedge is a
  qualifier, not a hook; the hook (the throughput sentence) has to do the
  top-of-funnel work alone.

---

## 7. Recommendation

Ratify the throughput sentence (§3) as the canonical psychographic, and the
fast/slow-ground-truth split (§4) as the activation logic. If ratified:

- **`ESSENCE.md`** — already substrate-first (v13.0); add the judgment-seat
  *psychographic* as the human-facing expression of Axiom 8 (currently ESSENCE
  states the *property*, not the *who*).
- **`NARRATIVE.md` / `GTM_POSITIONING.md`** — retire the occupation-list ICP
  ("solo consultants," "five domain experts") and lead with the throughput +
  fast-ground-truth wedge. GTM_POSITIONING v3.0 is stale enough to warrant a
  full v4 rewrite against current canon (ADR-216 / 282 / 310 / 312), not a patch.
- **Bundle roadmap** — pick bundle #3 by activation-cleanliness × TAM (a broad
  fast-ground-truth domain), not by domain interest (§5.1).

Companion: `moat-architecture-audit-2026-06-08.md` (the moat receipts this
positioning stands on; recommendation #3 there — "decide consciously: autonomy
vs accountable compounding judgment" — is answered by this doc: the external
noun is **the judgment seat**).

---

## Appendix — the throughput, three lengths (for surface reuse)

- **One-liner:** *An agent that holds your judgment seat, not one that does your tasks.*
- **Throughput sentence:** *You hold a recurring, high-stakes judgment over an accumulating body of work you can't afford to get wrong — and you want a seat that holds your standing intent, makes those calls the way you would, learns from what actually happened, and leaves a trail you can audit.*
- **Stretch proof (range, not volume):** *A&R deciding which artist to sign. A PM deciding what to ship. A founder deciding where to spend runway. A trader deciding whether to take a position. A partnerships lead deciding which deal to pursue. Different jobs — one relationship to the work.*
