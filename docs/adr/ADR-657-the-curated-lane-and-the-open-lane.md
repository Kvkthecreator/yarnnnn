# ADR-657 — Two lanes to a connection: the curated lane and the open lane

> **Status**: **Accepted + Implemented** (2026-09-18) — the curated lane, the URL shape, the
> differentiated open lane and the gate ship together. Gate: `api/test_adr657_two_lanes.py` (48/48,
> 16 arms falsified RED).
> **Date**: 2026-09-18
> **Authors**: KVK (operator) + Claude (collaborator)
> **Dimensional classification** (Axiom 0): **Where** (the boundary's door — ADR-642's dimension).
> **No authority change**: every reach decision stays on grants, apertures and gates. This ADR
> decides *how a member ARRIVES at a connection*, never what the connection may then do.
>
> **Derivation**: the operator drove a 31-tool Shopify-shaped attach through the ADR-635 am.1
> click-pass, then looked for Shopify in the connector finder on production and did not find it.
> The finding: *"i don't like the simple paste a server url. its way too generic … re-think how to
> make this user friendly and intuitive … in a future proof, long standing, scalable manner."*

**Reopens** — explicitly, with the reason on the record:
- **[ADR-635](ADR-635-the-connector-directory-is-consumed-and-reach-attaches-under-the-members-grant.md) D1** — *"the connector directory is consumed from the ecosystem, never authored."* §3 argues the new fact that reopens it.
- **[ADR-420](ADR-420-engine-breadth-vs-connector-breadth.md) §10 rule 2** — *"never an AUTHORED catalog"* (as itself amended 2026-09-03). §3.

**Preserves** (load-bearing, untouched):
- **ADR-420 §10 Amendment** — the **moat-leak test**. Not preserved as decoration: §4 makes it the
  *admission criterion*, which is the whole reason this curation is not editorial taste.
- **ADR-635 D4** — the aperture is consent, per tool, and **sovereign** (ADR-635 am.1, operator
  ruling 2026-09-18: an irreversible foreign write marked `direct` APPLIES; no floor, no classifier).
  Nothing in this ADR touches what runs; it touches only how a member finds the server.
- **ADR-577 / ADR-645 D1** — a credential is a human's; an agent caller is refused; there is no
  workspace credential store and no adoption.
- **DP27** — *consumed, never built*. §3.a is careful: this ADR does not un-consume the upstream
  directory. It adds a second, smaller, differently-sourced lane beside it.

---

## 1. The problem

A member who runs a business on Shopify opens Reach → Connected → New connection, and Shopify is
not there. It is not there because the directory is **derived** from
`anthropics/knowledge-work-plugins` (55 entries; commerce is Stripe, Square, PayPal) and Shopify is
not in that upstream. Nothing is broken — the loader is behaving exactly as ADR-635 D1 requires.

Below the list sits one undifferentiated field: *"…or paste a server URL (https://…)"*.

That field is where every server the upstream does not carry must arrive. And it is the same field,
asking the same nothing, for two categorically different acts:

| The member pastes | What it is | ADR-420 §10's verdict |
|---|---|---|
| `https://api.exa.ai/mcp` | a dumb peripheral — computes, returns, stores nothing about them | **moat-safe** |
| `https://higgsfield.ai/mcp` | a **competing commons** — versioned, searchable, collaborative asset store | **leaks the moat**; never a default; *"if ever connected, it must be a deliberate, eyes-open decision to be a client of a competitor"* |

**The moat-leak test governs seeding. The paste box is how unseeded servers arrive.** So the one
governing rule the canon holds about connectors is enforced at the door nobody uses, and is silent
at the only unconstrained door. That is the defect, and it is structural rather than cosmetic.

**A second tell, already paid for.** [`b21c060`](https://github.com/) (ADR-635 am.2 click-pass) found
that a server the upstream seed does not carry attaches with `category: null`, so a `needs`-scoped
skill could never light up for it — and the fix was to ask the **member** to type the category, with
the seed's vocabulary as a datalist. That is curation debt being paid by the member, at the moment
they know least. The generic box cannot tell them what they are attaching, so it asks them.

---

## 2. What this ADR does not do

- It does **not** delete the paste box. ADR-635 am.2 rents media generation through a member's own
  attach of a vendor the seed does not carry; deleting the open lane makes `generating-media`
  unreachable and re-creates the *"withheld forever and nothing says why"* failure that commit fixed.
  Flexibility and scale are real properties and this ADR keeps them.
- It does **not** change the aperture, the credential path, or what an agent may reach. A curated
  entry and a pasted URL converge on the **same** `mcp:{slug}` row, the same per-tool aperture, the
  same ADR-577 refusal. Curation is a **discovery** act, never an authority one.
- It does **not** turn yarnnn into a marketplace (ADR-412 D3, ADR-420 D5 untouched). There is no
  ranking, no promotion, no revenue surface, no "featured".

---

## 3. The new fact that reopens D1

ADR-635 D1 was ratified on a true observation: *since ADR-420 refused a catalog (2026-07-08), the
ecosystem grew one.* The MCP registry answers search; Anthropic publishes 62 vendor endpoints. So
**discovery could be consumed**, and DP27 was enacted for it.

The new fact is narrower and it is not a reversal of that reasoning:

> **An upstream catalog has no completeness obligation to yarnnn's members.**

`anthropics/knowledge-work-plugins` is derived for *knowledge work*. It carries no commerce admin,
no merchant tooling, and there is no mechanism by which yarnnn's members' needs enter it. Shopify is
absent today and there is no reason to expect it tomorrow. A directory we cannot influence cannot be
the *sole* discovery surface for a product whose members run businesses.

D1's principle survives intact where it applies: **discovery of the ecosystem is consumed.** What
this ADR adds is that *some* connections are not discovered — they are the ones yarnnn has
deliberately made work, and the member should be able to find those by name.

### 3.a Why this is not simply "authoring a catalog again"

ADR-420 §10 rule 2 forbade an authored catalog because curation-as-taste is a service yarnnn does not
sell — *"recommendation is a thin hint, never a curation service."* This ADR does not add taste. It
adds a list whose **admission criterion is a test the canon already ratified** (§4), whose entries
each **record why they were admitted**, and which is **small by construction** (§6). The upstream
directory is unchanged, still consumed, still provenance-stamped, still the larger surface.

**The honest cost, stated rather than slipped:** a listed connector reads as an endorsement. A member
who sees Shopify in a yarnnn-curated lane will reasonably infer that yarnnn vouches for it —
including, where the merchant-admin capability comes from a community server, vouching for a third
party that will hold their merchant token. §5 is the design response; it does not make the cost zero.

---

## 4. D1 — The curated lane exists, and its admission criterion is the moat-leak test

A **curated connector** is an entry yarnnn states outright, with a name a member recognises, in a
lane of its own beside the consumed directory.

Admission is not editorial. An entry is admitted only by answering, on the record, ADR-420 §10's
governing question:

> **"Does the connector accumulate the user's work on its own side?"**
> **No → a true peripheral.** It computes and returns; the result lands in *yarnnn's* files,
> attributed. Admissible.
> **Yes → a competing commons.** NOT admissible to the curated lane. It remains reachable through
> the open lane (§7) as a deliberate, eyes-open act, which is exactly what §10 requires of it.

This makes the curated lane the **enforcement site** for a rule that has had none. Curation earns its
bytes because it is where the test is applied, not because yarnnn has opinions.

Each entry therefore carries its **verdict and its reason** as data, not prose:

```
key            shopify
title          Shopify
category       Commerce          ← pre-filled, so `needs`-scoped skills light up (b21c060's debt, paid)
url            (or: the member's own store URL, with a shape to fill — §5)
accumulates    false             ← the moat-leak verdict
rationale      "Orders, products and customers are the member's own commercial
                records, read into the commons and cited. Shopify is the system of
                record for a business the member already runs — connecting it moves
                nothing INTO Shopify that was not already there."
admitted_at    2026-09-18
admitted_by    ADR-657
```

An entry with no `rationale` is refused by the loader, exactly as a seed with no provenance is
(ADR-635 D1's discipline, carried over rather than abandoned).

---

## 5. D2 — A curated entry carries what a URL cannot

The open lane can only ask for a URL, because a URL is all it knows. A curated entry exists precisely
to carry the things that make a connection *usable*, which the generic box has no way to supply:

| What it carries | Why the paste box cannot |
|---|---|
| **Identity** — real name, the vendor's own mark | a hostname is not a name |
| **The URL shape** — e.g. `https://{store}.myshopify.com/api/mcp`, with the member filling only `{store}` | a member should not have to know a vendor's MCP path |
| **The credential step** — where the token comes from, in the vendor's own words, linked | the generic flow can only say "a server that wants a header takes it as one encrypted field" |
| **Category, pre-filled** | otherwise `category: null` and no `needs`-scoped skill lights up (b21c060) |
| **The moat-leak verdict + rationale** | the box cannot say where the member's work will accumulate |

**Endorsement is bounded in words, not implied by placement.** Where a capability is reached through
a server yarnnn does not operate, the entry says so plainly and names who holds the credential. A
curated entry states what the connection *does* and who it is *with*; it never claims the far side is
safe. (The ADR-644 discipline: a reach sentence is derived from one structure, never hand-written per
surface — the curated entry is data that structure reads, not a fifth face.)

---

## 6. D3 — The curated lane is small by construction, and says when it was last examined

The failure mode of an authored list is rot — the repo's gates keep catching stale rosters, and the
consumed seed avoids rot only because a script re-derives it and stamps repo + commit.

An authored list has no upstream to re-derive from, so it must be **small enough to re-examine by
hand** and must **carry the date it was last examined**. Concretely:

- The lane opens with **one** entry (Shopify, §8), and grows only when a member's demonstrated need
  names the next one — the ADR-420 demand gate, applied to curation instead of to mechanism.
- Each entry carries `reviewed_at`. A stale entry is a finding, and the gate reads the date.
- An entry whose far side changes shape (the vendor's endpoint moves, its auth changes) is a
  **defect**, surfaced the way ADR-635 am.1 surfaces tool drift: the member is told, in their own
  words, on the surface they already read.

---

## 7. D4 — The open lane survives, demoted and differentiated

Paste-a-URL stays, because flexibility and scale are real and ADR-635 am.2 depends on it. Two changes:

1. **It is visibly a different act.** The curated lane is the front; the open lane is named as what it
   is — attaching a server yarnnn has not examined.
2. **It stops being silent about the moat-leak test.** The open lane is where a competing commons
   legitimately arrives (§4 refuses it admission to the curated lane but not to the member). ADR-420
   §10 requires that act to be *deliberate and eyes-open*; today it is one keystroke and no sentence.
   The open lane must say, before the attach, that yarnnn has not examined this server and cannot say
   where the member's work will accumulate.

**Deliberately named and NOT built here**: probing the pasted server's `tools/list` to *derive* a
moat-leak signal before attaching (read-only verbs vs. create/project/workspace verbs). It is
attractive and it is a heuristic about a server we do not author — the same class of thing ADR-635 D4
refuses to let decide anything (`readOnlyHint` is a hint, never a decision). If it is ever built it
informs the member's sentence; it never gates the attach.

---

## 8. D5 — The first curated entry is Shopify, and it is admitted by the test

Verdict: **`accumulates: false`** — admissible.

The reasoning, on the record: a member's orders, products, customers and inventory are **their own
commercial records**, and Shopify is the system of record for a business they already run. Reading
them into the commons — attributed, cited, `derived_from` naming the source — moves accumulation
*toward* yarnnn. Nothing the member authors in yarnnn is deposited into Shopify by connecting it.
This is the opposite of the Higgsfield case, where the versioned asset and the prompt history — the
*interesting* artifact, the thing that did not exist before — accumulate on the vendor's side and
yarnnn gets back a URL.

**What the entry must say plainly** (§5): Shopify's four official MCP servers are buyer-side or
docs-side; the merchant-admin capability (products, orders, fulfilment, refunds, inventory) comes
from a **community** server wrapping the Admin API, which will hold the member's merchant token. The
entry names that, and names that the aperture is where they decide what may run (ADR-635 D4, and
am.1's ruling that their `direct` tick is sovereign).

---

## 9. Consequences

- **A second source of truth for discovery exists.** Two lanes must never disagree about a server
  that appears in both; the curated entry wins for display, and the gate asserts they do not collide
  on `key`.
- **`category: null` stops being the common case** for the servers members actually want, which is
  what `needs`-scoped skills need to be anything other than decorative.
- **The moat-leak test acquires an enforcement site** and stops being a rule that governs only a
  seed list nobody edits.
- **yarnnn accepts a maintenance obligation** it did not have. §6 is the containment; the demand gate
  is the other half. If the lane grows past what one person can re-examine, this ADR has failed and
  should be revisited rather than quietly carried.

---

## 10. Verification

Gate: `api/test_adr657_two_lanes.py` — **48 checks, 0 failed; 16 arms falsified RED** by editing
the shipped file in place and restoring it in a `finally` with an equality assert.

Where the implementation lives:

| The decision | The code |
|---|---|
| D1 — the curated source, authored, admission by the moat-leak test | `api/services/connector_curated.json` + `load_curated()` in `api/services/connector_curated.py` (refuses an entry with no `rationale`, no `accumulates`, no `reviewed_at`; refuses `accumulates: true` outright) |
| D2 — the URL shape, one hole | `resolve_url()` — one `{field}`, one value, no template language |
| D2/D5 — the category pre-filled (b21c060's debt) | `POST /connectors/attach` resolves `curated_key` → url · title · slug · **category** before the one `begin_attach` both lanes call |
| D4 — the open lane, demoted and differentiated | `OPEN_LANE_CAVEAT` in `web/components/settings/FindConnectorModal.tsx`, rendered above the paste box |
| D3 — `reviewed_at` and staleness | `stale_entries()`; the gate reports a stale entry as a finding |

The consumed seed is untouched: `connector_directory.py` does not import the curated lane, and the
gate asserts it (§4d), so the derived-and-stamped file stays derived.

- An entry with no `rationale` or no moat-leak verdict is **refused by the loader** (the ADR-635 D1
  provenance discipline, carried over) — driven, not read.
- A curated entry and a pasted URL converge on the **same** `mcp:{slug}` row shape, the same
  aperture semantics, the same ADR-577 refusal for an agent caller — asserted by driving both paths
  to one comparison, the ADR-644 "compare the faces, never trust them" pattern.
- The curated lane's `key`s do not collide with the consumed directory's.
- The open lane still attaches an unseeded server (ADR-635 am.2's media path is not broken) — the
  regression this ADR is most likely to cause, so it is asserted directly.
- `reviewed_at` is present on every entry, and a stale date is a reported finding rather than a
  silent pass.
