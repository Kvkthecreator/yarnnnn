# The App is an AI-Native Program — agents, skills and a surface, scaffolded as one thing

*A workspace where you can post someone to something. The boundary is soft by decision, not by omission.*

> **Status**: Analysis (2026-09-16). **No ADR rides this document.** It records a discourse — the operator's thesis, worked from first principles, with the prior rulings it collides with named rather than deferred to. It is the conceptual frame an implementation ADR would later cite; it decides nothing about mechanism, schema or surface.
> **Authors**: KVK (operator) + Claude (collaborator)
> **Hat**: A (system canon). Vocabulary: operator, member, workspace, substrate, agent, skill, surface, reach, grant.
> **Method**: first-principles, from the member's chair forward. The operator's explicit instruction mid-discourse was to **stop reasoning from prior ADRs**, on the grounds that precedent was impeding the derivation. That instruction is honored in §§2–7: the frame is derived, not inherited. §8 then does the collision check the instruction deferred — because a frame that cannot say which prior rulings it reopens is not yet hardened.
> **Origin**: a real member. The operator's sister, being onboarded as a beta tester, said: *"all this is cool, but what would be cooler is if it could help me manage my photos for work."* Every claim below is answerable to that sentence.

---

## 1. The sentence this document exists to answer

> *"All this is cool, but what would be cooler is if it could help me manage my photos for work."*

Unpack "cool." She recognized generality and found it worthless. That is not a lukewarm review — it is a precise diagnosis:

> **She could see it could do anything, which meant she could not see what it did.**

An empty workspace with a chat box is a blank page with extra steps. She already has ChatGPT. What she does not have is something that shows up already knowing what her problem looks like.

**Generality reads as emptiness.** That is the onboarding problem stated exactly, and it is not a feature gap. No amount of capability fixes it, because the failure is not that the system cannot do the work — it is that nothing tells her what work it is for.

---

## 2. What an app is to a person who is not technical

An app is not a program to her. **An app is a promise about what a space is for.**

Opening Lightroom does not hand her capabilities. It hands her a *claim*: this place is about photos, here is where they live, here is what you do to them, here is what "organized" means here. The value is that **someone already decided.** She does not want a tool that can become anything. She wants one that already became something.

So "app" is not a friendlier word for a config file. It is the moment the product stops saying *"you can do anything"* and starts saying *"here is what this is for."*

### 2.1 Why a skill alone cannot do this

The cheap answer to her request is a skill — craft prose, one file, no new machinery. It is the wrong answer, and the reason is instructive:

> **A skill is invisible. It works by being silently more competent.**

She would upload photos, ask for help, get a better answer than expected, and have no idea why — nor any idea what else to ask for. She would never discover the second thing it could do. **Invisible competence does not onboard anyone**; it makes one interaction go slightly better.

An app is a **visible claim**. It tells her what to expect before she asks. That is the whole onboarding function: not capability, but *legibility of capability*.

This is why the app framing is load-bearing rather than cosmetic. It is the only form in which capability is discoverable to someone who does not already know what to ask for.

---

## 3. The landscape gap this is aimed at

The frame the operator named: this is an attempt to scaffold the **who / what / where / when** of a landscape where nobody else has all three of filesystem, surface and resident agent.

| Player | Has | Structurally cannot |
|---|---|---|
| **Claude — artifacts, coworking** | real outputs, real collaboration | no *place*. An artifact lives in a conversation; when the chat ends its home is scrollback. Nothing accumulates, because there is nowhere to accumulate into. |
| **ChatGPT — apps, plugins** | reach into other systems | stateless in the way that matters. A plugin does a thing and returns. It keeps nothing, knows nothing of last time, owns no ground. A function call in an app costume. |
| **Agent frameworks** | capability | no residence. They can act, but there is nowhere they *are*. |

The common gap: **all of them treat work as transactional.** Something is asked, something is returned, and the world does not change except in whatever external system got poked. There is no substrate where the work of working settles.

yarnnn has the three things none of them have together — **a filesystem that accumulates attributed work, surfaces that make it visible, and agents that are somewhere.** So the question is not *"how do we build apps like they have."* It is:

> **What is the native unit of work for a system that has all three?**

### 3.1 The four dimensions

The operator's who/what/where/when, taken literally. Each is a thing the landscape cannot answer:

- **Who** — an agent with a persisting identity that accumulates judgment about *this specific work* and can be addressed. Not a session, not a system prompt. Someone. Nobody else has this because nobody else has anywhere for a persistent identity to live.
- **What** — the work itself as a durable thing rather than a request. Not "summarize this" but "the client delivery for this shoot": an object with a state that survives the conversation. Artifacts are the closest and are still outputs, not ongoing concerns.
- **Where** — the files, the surfaces, the reach. Plural and shifting. There is no "where" in a chat product at all.
- **When** — rhythm. Due, overdue, recurring, dormant. Nobody has this because nothing is standing.

These are **not four declarations.** They are four dimensions any ongoing work has. An app is a coherent answer to all four at once — and that is what makes it an app rather than a prompt, a folder, or a task.

---

## 4. The program metaphor, and what it corrects

The operator's framing: *think of an app as essentially a program — much like a .exe with a folder associated to it.*

The metaphor corrects a real error. An earlier pass in this discourse modelled an app as four declarations (structure, properties, craft, view). That is a **document format** — it sits there and describes. A program does not describe; **a program runs.** It has an entry point. It does something when invoked.

> **An app that cannot run is not a program. It is a config file with ambitions.**

The four declarations are not the app. They are the **brief the agent works from**: structure is where to look, properties are what to notice, craft is how to do it well, view is how to show the state.

### 4.1 The mapping, held honestly

| Program | Here |
|---|---|
| The binary | The declaration of what this does |
| Its working directory | The region it works over |
| Runtime / interpreter | The agent + the file verbs |
| Being launched | Someone opens it, or a rhythm comes due |
| Its window | The surface |
| Its documents | The files, which outlive it |
| Installing it | Placing it in a workspace |
| **Uninstalling it** | **Deleting the declaration — the documents stay** |

That last row is where the metaphor earns its keep. **Deleting Photoshop does not delete your PSDs.** The program is separable from the work — here not as a promise, but as a fact of where each thing lives.

### 4.2 What the metaphor adds

- **A program has an entry point.** Not just "here is what exists" but "here is what happens when this is invoked." The four-declaration model had craft (*how* to do things well) and no invocation (*that* things happen). Different, and a program needs both.
- **Programs run on data they did not create.** Photoshop opens a JPEG from a camera it never heard of. This is the deep fit: an app reads files that already exist, placed by whoever. The program does not own the format — it *handles* it. Which is why an app can be derived from work already underway, and why two apps can read the same files for different purposes without conflict.
- **Programs are copied.** If an app is a file, distribution is already solved: sharing is sharing a file, forking is copying one, versioning is the substrate's job. You do not build an app store; you have one, because you have a filesystem.

### 4.3 Where the metaphor misleads — two bounds

**A .exe is opaque; this cannot be.** The value of the substrate is legibility. An app that is a black box you invoke surrenders the one property that makes it trustworthy. So: **a program in behavior, a document in form** — readable, editable, diffable. Closer to a shell script than a compiled binary, and deliberately so: a script is a program you can read, which is exactly the object wanted.

**Installing carries the wrong safety model.** Installing a real program means granting it your machine. Here an app must not be able to grant itself anything: reach sits outside the app, decided by the person. Otherwise "install this app" becomes a security question a non-technical person has to answer — the thing that makes app stores frightening. So: **programs in structure, not in authority.**

---

## 5. The resident — management, not launch

The operator's correction: *the launch (or better wording to my interpretation, management) is done by the dedicated Agent within an APP created by the user.*

The wording matters. **"Launch" is an event** — a moment, from outside, with a before and after. **"Management" is continuous** — there is no launch moment, because it is always the case that someone is looking after this.

Those are different objects. A thing that runs when clicked is a tool. **A thing that has someone minding it is a post.**

### 5.1 Radar folded in

The operator scoped the radar concept into this. Structurally, radar is: **watch a domain, notice what changed, judge what is worth raising, surface it.** A standing posture, not a task.

An app's agent inheriting that posture stops the app being *"a thing that does work when asked"* and makes it *"a thing that is on top of a domain."*

The load-bearing half is the **raising**. Radar's real function is not the watching — it is that it **tells you something you did not ask about.** That is the difference between a tool you must remember to use and a thing that earns its place. A model without it gives the app no mechanism to ever speak first.

**Why this shape is available here and nowhere else:** every act by every principal already lands in the attributed ledgers. An agent posted to a region does not need to be told what happened — it can see. There is no event system to build, no webhooks, no polling. **Noticing is reading.** In a product where state lives behind an API, "watch this domain" means building a change-feed; here it is the ambient condition.

### 5.2 The two risks of a standing posture

**An agent with nothing to say, saying something anyway.** The failure mode of a standing watcher is surfacing noise to prove it is alive. The person then learns to ignore it, and the app is worse than nothing — a source of interruption they have trained themselves past. The hard part of radar was never noticing; it is **the discipline to stay quiet.** That is a judgment problem, not a mechanism problem, and *"most of the time it says nothing"* must be a design goal rather than an embarrassment.

**Residents compound.** Six apps is six agents, all watching, all entitled to speak. Whether that feels like being staffed or being surveilled is not obvious. It may argue for few apps per workspace, or for raising to be pooled rather than each agent holding its own voice. Neither risk is a reason not to build; both only appear in use, so both are worth designing against rather than discovering.

---

## 6. Soft boundaries — the accepted risk

The operator's ruling, recorded verbatim because it is a decision and not an observation:

> *"The users' continuous intent and feedback will naturally soft-evolve and harden an app. The freedom of that exposure and continuity is a risk we're actively willing to take between app boundaries and their fundamental value."*

This reverses an assumption held earlier in the discourse — that an app is scoped to a region and declares its reach up front. That assumption is wrong, and the reason is that **real work is not folder-shaped.** Work spans some files here, a connected service there, a rhythm, a set of people. None of those is "its folder."

> **The region is a consequence of the work, not a container chosen in advance.**

The same holds for reach. What a piece of work reaches for changes as the work changes; a fixed reach list is a guess made at the worst possible time — before anything has happened.

So both the region and the reach are **emergent and revisable**. The app is defined by the work; the work determines what it touches. This inverts the naive model, which had the boundary first and the work inside it.

**What hardens an app is use.** Continuous intent and feedback — the member working, correcting, and being served — is what settles a boundary. An app is soft when new and harder with tenure, and that gradient is the design, not a transitional state.

### 6.1 What this costs, stated plainly

If the region and the reach are not fixed, **nothing can be scoped in advance** — not permissions, not what the agent watches, not what it may touch. That is honest to the work and genuinely difficult, because *"this agent may reach whatever this work needs"* is not a sentence that can be safely implemented.

Something must still pin it, and **it cannot be the app.** The only candidate is the person, continuously: the app grows its reach by **asking**, and each ask is a small moment of trust. Slower, and possibly the only version that is safe — possibly also the version that feels good rather than alarming.

**This is the accepted risk, ruled on.** It is recorded here so that a future session does not rediscover soft boundaries as a defect and harden them into a declaration.

---

## 7. The unit, stated

Composing §§2–6 — the operator's own summary is that the app-builder scaffolds **agents, skills and display (surface)**, plug-in-like, with inputs and outputs handled, which is what makes it *a program that IS AI-native*:

> **An app is an AI-native program: a named piece of ongoing work, scaffolded from an agent, the skills it works by, and a surface that shows its state — reaching whatever the work needs, on whatever rhythm the work has. It accumulates. It is made of files, so it is legible, versioned, forkable and portable. Its boundaries are discovered as the work is done, and hardened by use rather than declared before it starts. It holds no authority; its agent acts under the member's reach. Deleting it dismisses the agent and leaves every file untouched.**

### 7.1 What makes it AI-native rather than an app with AI in it

Three properties, none of which a conventional app can have:

1. **The runtime is judgment.** A conventional program executes deterministic instructions. This one executes an agent working with file verbs. Its instruction set is *what an agent can do with files* — which makes the ceiling countable, and makes every unmet request a measurable kernel gap rather than a guess.
2. **It can be derived from work already done.** Every other product's app is a container the work must fit — the schema precedes the content. Here files exist first, and the app is a *reading* of them. An app can therefore be proposed from what already happened, which no schema-first architecture can do.
3. **Being wrong is free.** An app is a reading, not a migration. Change it, delete it, keep two — the files never move. Every other product makes app-adoption a commitment; here it is a reading, and readings are cheap to change. **That is what makes "build an app" safe to say to a non-technical person.**

### 7.2 Three origins

An app comes into being three ways, and the ordering by importance is not the ordering by visibility:

- **Derived** — someone works for a while; a proposal appears. *This looks like recurring client work — want me to make it a thing?* The origin the architecture uniquely enables, and the right answer to "people do not want to build anything."
- **Chosen** — at signup: what kind of work? A starting shape. The only origin available at minute zero, when there is nothing to derive from. **The onboarding answer.**
- **Authored** — described in conversation, or edited afterward. The builder proper, and the **least** important of the three despite being the thing the idea is named after.

**The builder as a surface someone visits is the smallest part of this.** Derivation needs no builder; the catalog needs no builder. The builder is the escape hatch that makes the other two safe — if a derived app is slightly wrong, it must be fixable, or the derivation will not be trusted.

### 7.3 The positioning claim

Everyone else is building **better assistance** — smarter responses, more reach, nicer outputs. That is a capability race the model vendors win by default, and a better model lifts every competitor at once.

This builds **a place where work lives and someone tends it.** The differentiator is not answer quality; it is continuity, accumulation, and someone whose job is this. Those are properties of having a substrate, not of having a model — and a better model does not give anyone else a filesystem, a history, or a resident.

---

## 8. The collision check — what this reopens

§§2–7 were derived without precedent, per the operator's instruction. That instruction bought a clean derivation; it did not repeal the record. A frame that cannot name which prior rulings it reopens is not hardened, so this section does the check the derivation deferred.

**Nothing below weakens the frame.** Two of the three are *already true*, and the third is a ruling whose own stated reason no longer applies.

### 8.1 Already true — the skills layer

The skill half of the scaffold exists and is marketplace-compatible by construction. ADR-630 adopted the public Agent Skills convention verbatim: `name` + `description` frontmatter, body under 500 lines, progressive disclosure. `parse_skill` (`api/services/skills/__init__.py`) strips host-specific frontmatter (`allowed-tools`, `model`, `tools`, `argument-hint`) and **names the strip**; ADR-635 D7 added `metadata.needs`, which maps the ecosystem's `~~category` placeholder, so a public skill written for "a project tracker" drops in unchanged.

A member can paste a public skill today and it works. Two gaps, both small: **no import door** (no affordance — the file must be written) and **no skills pane** (ADR-630 D3 scoped it out).

⚠️ **One measured ceiling worth carrying**: ADR-630 counted that only **5 of Anthropic's 19 public skills** are pure work verbs achievable with file verbs, recall, search and image generation. The rest are format- or code-bound. "The marketplace" is a smaller usable set than the headline suggests.

⚠️ **The verb is compose, never fine-tune.** ADR-630 D2 records the migrated kernel skills as *verbatim*. Portability is the point: a skill mutated on import stops being the marketplace's skill and becomes a fork we own. The workspace declares *around* a skill (`metadata.apps`, `metadata.needs`) and never inside its body.

### 8.2 Already true — the substrate under it

The binary substrate is **not** the blocker the July analysis (`the-app-seam-first-party-viewer-vs-third-party-principal-2026-07-10.md`) named. ADR-427 Phases 1–3 landed 2026-07-20: binary is content-addressed, attributed, versioned and revertible. **That analysis is stale on this point** and should not be cited as a gate.

Agents can also *see* images: `image_part_for_tool_result` (`api/services/lane_runner.py`) appends real pixels beside a `ReadFile` result, and its docstring names the exact prior failure — an agent that "could describe the file it was looking at and never see it."

So a resident agent that looks at files, judges them, and files them is **mechanically available now**. The scaffold's "what" and "where" have substrate under them.

### 8.3 The one real collision — ADR-435

The surface half of the scaffold is the expensive half, and it was deliberately torn out.

`api/services/composition_resolver.py` is 354 live lines, and bundle `SURFACES.yaml` files still exist. But the components they resolve against are gone, in two stages: ADR-435 (`683ced2`, 2026-07-10) deleted `web/components/library/programs/` — every program-section component — and `web/components/library/registry.tsx` (`LIBRARY_COMPONENTS` / `dispatchComponent`), which ADR-435 explicitly **preserved** as shared with WorkDetail, was deleted later in `e18e178`. Three files remain in `web/components/library/`: `BundleBanner.tsx`, `ProgramLifecycleDrawer.tsx`, `README.md`. **The resolver resolves into an empty room.**

⚠️ Worth noting for a later session: the dispatch registry died as *collateral* in an agent-hardening commit, not by a ruling of its own. Whatever ADR-435 decided about composition, nothing decided that.

ADR-435's argument, stated precisely: Home was the *single composition surface in a registry of substrate mirrors* — an exception the taxonomy could not name. Two resolutions were available, **name it** (promote `composition` to a validated register) or **remove it**; the operator directed removal, and the ADR records the accepted cost: *"there is no composed glance-dashboard."*

But its reason was that the composition was **"in practice, a glorified redirect"** — its slots echoed surfaces that already existed. That is not an argument against composition. It is an argument against *that* composition.

> **ADR-435 killed composition for being empty. This frame is the case where it would not be.**

An app's surface composes over a region and a rhythm that no other surface shows. Nothing else can display it, so it redirects to nothing.

**What an implementation ADR must therefore do:** reopen ADR-435's explicitly rejected option — promote composition to a real, validated class — with the reason on the record. It must also decide the **component vocabulary** a member's composition may reference, which is the whole product surface: too small and nothing composes; too large and it is a page builder, which is the feature race the app-seam analysis warns against.

### 8.4 One constraint that binds, and is not in tension

An agent is identity ⊕ character ⊕ engine and nothing else (ADR-596); authority lives on grants and gates. A resident agent therefore **cannot carry special authority** by virtue of being an app's resident.

This is not a problem for the frame — it is §4.3's "programs in structure, not in authority" and §6.1's "the person pins it," arrived at independently from the member's chair and from the axioms. **Two derivations, one answer**, which is the strongest evidence in this document that the frame is sound.

---

## 9. What is open

Named so a later session does not mistake an open question for a settled one.

1. **What makes two pieces of work one app rather than two?** If boundaries are emergent, something must still make an app cohere, or a workspace is one undifferentiated blob of concerns and "app" means nothing. The working intuition is that it is **the who** — one app is one agent's remit; two things are one app if it would be strange for two different people to handle them. That is a human intuition rather than a structural rule, which may be exactly right for a product whose point is mapping to how people think about their work. **Unsettled, and it is the load-bearing definition of the core object.**
2. **Does an app's agent have its own character, or is it the same agent wearing a job?** A dedicated identity builds a relationship with *the one who handles the photos* — strong, and probably right. It also multiplies identities and sharpens §5.2's crowding.
3. **What is the smallest version that still reads as *managed*?** Acting only when asked is a tool with a nice name; only raising things is a notifier. The minimum is probably "does the recurring thing unasked, and says when something is off" — a guess, and better checked against a person than reasoned about.
4. **Which origin ships first.** Derived is most differentiated but needs work to derive from; chosen is the onboarding win but risks being templates; authored is most flexible and least likely to be used. Different first users; they cannot all be built at once.
5. **Are the four declarations (structure · properties · craft · view) the right brief?** Worth trying to break against three deliberately unlike scenarios — ideally one that is not document-shaped, and one where the work is mostly deciding rather than producing.
6. **Property extraction is a bounded kernel cost.** Properties a model can judge by looking are unlimited and need no code. Properties needing an extractor (EXIF, PDF fields, media duration) are finite and need building. Apps should declare freely and be told what is not yet available — which makes the roadmap **demand-measured**: count which unavailable extractors the most apps asked for. The same logic applies to the instruction set: an app needing a verb that does not exist is a located kernel gap.
7. **The word writes a check.** "App" imports expectations about installing, opening and closing that are wrong here — but every accurate word (post, standing work, tended concern) is a word nobody uses. Shipping "app" is probably right because it is the only word that gets someone to try it; the misunderstanding it imports is small and corrects on first contact. **Deliberate, not backed into.**
8. **Generic apps are worse than none.** A first app that is a folder structure and a prompt is something a member can already do in Finder. The first ones must do something they could not, or the framing costs credibility rather than building it.

---

## 10. The one-line statement

**An app is an AI-native program — an agent, the skills it works by, and a surface that shows its state, scaffolding a named piece of ongoing work whose region and reach are discovered by doing the work and hardened by use rather than declared in advance; it is made of files, so it is legible, versioned, forkable and free to be wrong; it holds no authority of its own; and it exists because a general substrate is invisible to someone who does not yet know what to ask for, while a program with someone minding it is a promise they can read at a glance.**

---

## 11. The data question — measured, and the one wall that was real

> **Added 2026-09-16, after §§1–10.** The frame above is silent on a question a member asks
> immediately: *can an app be data-heavy?* Her photos are files; a pipeline, a client list, an
> inventory are rows. §9.6 sized "property extraction" as a bounded kernel cost and stopped
> there. This section drives the question instead of reasoning about it, and **corrects two
> claims made earlier in the same session** — both of which were wrong in the direction of
> pessimism, and one of which hid a live defect.

### 11.1 Why this could not be answered by reading

The substrate's own numbers, over every live workspace:

| Kind | Files | Max chars | Avg chars |
|---|---|---|---|
| `md` | 573 | 34,902 | 3,697 |
| other | 352 | 178,206 | 17,885 |
| **`csv`** | **5** | **372** | **196** |

Five CSVs, the largest 372 characters. **The data path had never been driven.** Every ceiling
over it was therefore unproven in *both* directions — nothing had shown it held, and nothing had
shown it failed. That is the exact condition in which a gate is green because nothing exercises
it, and the only instrument that settles it is a real run.

### 11.2 The probe

`api/scripts/operator/probe_data_heavy_lane.py` — a 5,000-row sales pipeline (287,762 chars)
written into a live workspace, and three questions that **cannot** be answered from a partial
read:

1. **Row count** — needs the whole file.
2. **A tail fact** — a nonsense client name planted at ~92% depth, appearing exactly once.
3. **An aggregate** — the sum of one column across 1,010 matching rows.

Scored against ground truth computed in Python from the same bytes the file was written from —
never against the transcript, never against the lane's claim about its own work. The scorer was
falsified before the turn was spent: it passes a perfect answer, fails a partial one, and
catches a right-count/wrong-needle answer. (The fixture seed is chosen so the planted row's
stage is not `won`, or Q2 would pass on Q3's prose alone.)

### 11.3 What it found — the predictions were wrong

The session's prior answer predicted four walls, led by the read cap, and expected a lane that
reads ~35% of the file and answers confidently. **Every part of that was wrong.** The receipts:

```
1. ReadFile(pipeline.csv)                → truncated, 100,000/287,762, next_offset=100000
2. ReadFile(pipeline.csv, offset=100000) → truncated, 100,000/287,762, next_offset=200000
3. ReadFile(pipeline.csv, offset=200000) →  87,762 chars, next_offset=None   ← read to the END
4. (no tool calls)   finish_reason='length'   text=''
```

| Predicted | Measured |
|---|---|
| Read cap (`READ_FILE_MAX_CHARS = 100_000`) is the binding wall | **Not binding.** ADR-648's `_clip_read` notice did its job; the lane paginated three times and read **100%** of the file. |
| History ceiling (`_HISTORY_MAX_CHARS = 120_000`) is the harder wall | **Never reached.** 288KB of reads, no clamp. |
| Search's `limit(80)` blocks the work | Not exercised — the lane went to `ReadFile`, correctly. |
| Four walls | **One**, and not one of the four. |

**The substrate carried the data fine. The turn could not carry the answer.** Having read
everything, the model spent its entire `_LANE_MAX_TOKENS = 4096` output budget computing and
was cut off: `finish_reason='length'`, `text=''`.

### 11.4 The defect this uncovered

`success=True`, `rounds=4`, `tokens_out=4438`, **and an empty message**. No error, no hedge,
nothing to distinguish it from a hang — after a wait and a real bill. Reproduced twice,
identically.

`RoutedCompletion.finish_reason` had been captured by the router since it was written and read
by nobody (`grep -rn finish_reason services/lane_runner.py routes/lanes.py` → no matches). The
round-cap fallback sitting a few lines below could not catch it: that branch fires when the
`for` loop *exhausts*, and this turn broke out of round 4 of 8.

Refusing to emit a truncated answer is *correct*. The silence is the defect — right mechanism,
lying words. Fixed in `9005b23` (one helper, both turn loops; gate
`api/test_truncated_answer_speaks.py` 11/11, proven RED in five arms).

⭐ **The shape worth carrying forward: the failure got worse the better the agent behaved.** A
lane that lazily reads one window has budget left to answer. The one that diligently reads
everything spends its context and dies silently. **Diligence was punished** — and it was
punished invisibly, which is why five CSVs totalling under 2KB could never have revealed it.

### 11.5 What this means for the frame

§7.1 claims the app's runtime is judgment, and that *"every unmet request is a measurable kernel
gap rather than a guess."* This is that claim working exactly as advertised — the gap is now
located, and it is **not** where reading suggested:

> **The gap is not that an agent cannot see the data. It is that the agent is being asked to do
> the arithmetic.**

Summing 1,010 numbers is not judgment. It is computation the substrate should perform and hand
back as one line. A projection verb over a shaped file — filter, project, sort, limit, returning
rows plus a matched-vs-returned count — removes the wall by **not putting the data in the window
at all**: 5,000 rows in, twelve rows out, budget intact for the answer. It stays inside Axiom 1
(pure computation over the head revision; no table, no second store, no schema registry), and
the shape declaration it would validate against already exists in `_standing.yaml`.

Row-grain *write* (an append that does not rewrite whole content) is the sibling gap and is
**deliberately deferred**: it is the only one that touches `write_revision`, and nothing has
failed on it yet. Naming it here so a later session does not mistake the deferral for an
oversight.

### 11.6 What this adds to §9 (the open questions)

- **§9.6 was sized too small.** "Property extraction is a bounded kernel cost" is true and
  incomplete: the *instruction set* has the same demand-measured shape, and the first located
  entry is a projection verb, not an extractor.
- **A data-heavy app cannot be the first app.** §9.8 warns that the first apps must do something
  a member could not already do. A CRM is exactly what a non-technical member *expects* an app
  to be, and — until the projection verb exists — it is the one shape that fails. Worth knowing
  before it is chosen as a demo.
- **A new open question: what does an app declare about the shape it reads?** Not for permission
  (§6 ruled boundaries emergent) but for *legibility* — if a member reorganises a folder in
  chat, nothing today knows those files were load-bearing for an app's reading of them. The
  substrate already has the sibling machinery (`derived_from` edges power the Files
  delete-confirm's *"N files were made from this"*). There is no equivalent for *"an app reads
  this shape."* Unsettled.

### 11.7 The method note

Nothing in §11 was derivable from the source. The read cap and the history ceiling are both
plainly documented, both looked like the binding constraint, and neither was. The actual wall
was a constant whose own comment says *"raise further against felt truncation, not
speculation"* — and the felt truncation, when it finally arrived, arrived as **silence**, which
is the one symptom that comment could never have been acted on from.

> **Driving the path found what reading it could not — including a defect that had nothing to do
> with the question being asked.**
