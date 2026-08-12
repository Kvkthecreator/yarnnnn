# ADR-549 — A creation act names its object

> **Status**: Accepted (2026-08-12, operator-ratified — *"no 'temporary' approach… New Document, and thus Learn from assuming needs to also go through similar audit"*).
> **Amends**: [ADR-470](ADR-470-new-hands-over-the-workbench.md) D1 (two doors → one), D2 (the placeholder title), D3 (the untitled placement branch), D5 (moot — nothing is born unnamed) · [ADR-452](ADR-452-the-studio-landing-learn-from-as-a-creation-path.md) D2 (Learn-from's hardcoded placement)
> **Preserves**: ADR-469 entire (the name is lifted, the path is a key) · ADR-470 §5 (there is no Save, and there must not be) · ADR-440 D6 (the region fence — untouched here, see §6) · ADR-424 D1 (Documents is the home's name)
> **Derivation**: the 2026-08-11 create-surface audit (`docs/evaluations/findings/2026-08-11-create-surface-audit.md`) + the operator's `asdfadsf` receipt

---

## 1. The observation

The operator created a document through the fast door and reported the result:

```
/workspace/operation/asdfadsf/document.html
```

A folder named after a keyboard mash — permanent, attributed, indistinguishable
from real work in every listing. Then, looking at the `+ New` menu:

> *"I'm thinking if we need to streamline the Document and Name it first. It's
> confusing to me (for both Studio and Docs apps), or in fact any future
> workflow similar to this."*

Two rows for one act, distinguished by whether the member is asked a question.
`Document` and `Name it first…` do not name two different things a member could
want — they name **one thing and a toll**. That is a menu describing its own
implementation.

**The apps' own taglines already promised the opposite.** All three read *"name
it"* (`Docs`: "Name a document and start writing"; `Studio`: "Pick a shape, name
it"; `Images`: "Pick a size, name it"). The immediate door contradicted the
surface's own copy.

## 2. The alternative that was considered and refused

The operator named both options honestly:

> *"We either have a deliberate temp area and unless they save explicitly gets
> deleted (I believe this is nothing new in terms of handling, much like
> existing operating systems and programs), OR, we force the naming and location
> and just call it New."*

**The temp area is the OS-standard answer and YARNNN cannot have it.** Not
because it is worse — because *"unless they save explicitly gets deleted"*
requires an **unsaved state**, and this substrate has none. Every keystroke is
already an attributed revision (Axiom 1, second clause); there is no Save verb
anywhere in the authoring surface, and ADR-470 §5 establishes that adding one
would be **theatre, implying a volatility the substrate does not have**.

So a temp area would mean one of two things, both of which break something
load-bearing:

- **Reintroduce Save** — creating the one place in YARNNN where a revision is
  written and attributed but does not count. That is a lie about the record, and
  the record is the moat.
- **A reaper that deletes attributed revisions on a timer** — deleting work
  someone typed for an hour without naming, in a workspace whose claim is that
  nothing is lost.

`ephemeral` (ADR-119) remains a column value. This ADR does not adopt it and
does not foreclose it; it simply notes that **the untitled artifact was never a
temp file** — it was an ordinary file with a bad name, which is why ADR-470 D5
was right to call it `active` and wrong to create it at all.

## 3. Decisions

### D1 — One door. `New` asks for a name; there is no second row.

`+ New` opens the shape's creation dialog directly. The `Name it first…` row is
**deleted** — not renamed, not demoted. A creation act names its object; there
is no variant of it that does not.

Where a surface offers more than one shape, `+ New` still opens a shape menu
(Document · Deck · Web · Image) — but **every row leads to the same dialog**.
The menu chooses *what kind of thing*, never *how much you will be asked*.

### D2 — The name is REQUIRED. The location is DEFAULTED and changeable.

This is the half of the operator's Option B that is deliberately softened, and
the reason is in the receipt: **`asdfadsf` is a naming failure, not a placement
failure.** The file landed somewhere perfectly sensible.

- **Name** — required, empty, focused. `Create` is disabled until it is typed.
- **Location** — pre-filled with a sensible default, one click to change, in the
  same dialog.

**Two required fields is interrogation; one required field with a visible,
changeable default is a dialog.** ADR-470 D1 diagnosed the interrogation
correctly (*"New interrogated you before it gave you anything"*) and then
applied the wrong fix: it removed the question instead of removing the
**second** question. Word, Keynote, Figma and Pages all take exactly this shape.

### D3 — The default location is where the act is standing

The default is derived, in this order:

1. **The folder the member is in**, when the surface has one (a Files folder
   window; a Studio opened from inside a folder). *Finder's rule: the background
   of an open folder creates inside that folder* — already implemented for New
   Folder (`files/page.tsx`).
2. **Beside the source**, for a derived act (D4).
3. **The Documents home**, otherwise.

Never a hidden rule and never a hardcoded root chosen by the app.

### D4 — A derived artifact lands beside its source

Learn-from's placement was audited at the operator's instruction and was
**wrong in a way the two-door problem hid**. `StudioSurface.tsx:4028` hardcoded:

```ts
path: `operation/${slugify(sourceName)}/${target.template}.html`
```

The source's own location is **not consulted at all**. Measured:

| source | landed at | should be near |
|---|---|---|
| `operation/ai-frontier/briefs/2026-08-05-frontier.md` | `operation/2026-08-05-frontier/…` | `operation/ai-frontier/briefs/` |
| `operation/the-acme-deal/notes.md` | `operation/notes/…` | `operation/the-acme-deal/` |
| `inbound/uploads/operator/q3-report.pdf` | `operation/q3-report/…` | (an arrival — Documents is right) |

A brief derived from work filed under `ai-frontier/briefs/` landed at the **root
of Documents**, orphaned from the thing it was made from. Under D3 the default
becomes **the source's own folder**, except when the source is an arrival
(`inbound/`), which is not a home — those default to Documents.

Learn-from also now shows the **same dialog** as every other creation, with the
name **pre-filled from the source** (it has a real name — that is ADR-452 D2's
correct half) and editable. Pre-filled is not the same as unasked.

### D5 — Nothing is born with an invented name

ADR-470 D2 established that a nameless artifact keeps its skeleton's
`Untitled ‹kind›` placeholder, because writing an invented name would make the
`<h1>` look authored and freeze the later rename. That reasoning is **preserved
and becomes unreachable**: nothing is created without a name, so the placeholder
is never the artifact's identity.

`build_skeleton`'s `title=None` fallback **stays** — it is the honest default for
a skeleton in isolation and is depended on by the layout registry. What is
deleted is the *path* that reaches creation with no name.

### D6 — Existing untitled artifacts are left alone

Files named `untitled-document`, `asdfadsf`, and their kin are **real substrate
with real revisions**. No migration, no reaper, no rename-on-open prompt. They
are renamed with the verb that already exists, by the member who owns them.

Retroactively renaming attributed work would be exactly the disposal this ADR
refused in §2.

## 4. What this deletes

The point of the change is subtraction:

- `createUntitled` (`StudioSurface.tsx`) and its menu row.
- `_placed_path`'s untitled branch and the `untitled {label}` key derivation
  (`routes/studio.py`) — the named path is the only path.
- `StudioNewMenu`'s `onPickNamed` prop and the `Name it first…` row.
- The crumb-arms-on-mount behaviour that existed to make an unnamed artifact
  nameable after the fact.

## 5. Falsifiers

1. `+ New → Document` opens a dialog with an empty, focused name field; `Create`
   is disabled until something is typed.
2. There is no `Name it first…` row anywhere.
3. The dialog's destination shows **Documents** by default — never `operation`.
4. Creating from inside a folder defaults the destination to **that folder**.
5. Learn-from from `ai-frontier/briefs/x.md` defaults to
   `ai-frontier/briefs/`, with the name pre-filled from the source and editable.
6. Learn-from from an `inbound/` arrival defaults to Documents.
7. Two documents named the same thing still both exist (`notes`, `notes-2`) —
   ADR-469 D4 is untouched.
8. No creation path produces a path containing `untitled-` as a generated key.

## 6. What is deliberately not built

- **No temp area, no Save, no reaper** (§2).
- **No `ephemeral` adoption** — still reachable, still not needed.
- **No migration of existing untitled artifacts** (D6).
- **The ADR-440 D6 region fence is NOT touched.** It remains the open question
  the create-surface audit named (G2: `create_folder` honours ADR-424 D2 peer
  folders while `create_artifact` does not). This ADR makes the *grammar* one
  thing; the fence is a separate decision, and D3's folder-derived default is
  written so that relaxing the fence later widens it with no change here.
- **No New verb on Files yet** (G1). But D1–D3 are written as a **grammar, not a
  Studio behaviour**, precisely so that Files' eventual New Document inherits it
  rather than inventing a third pattern.

## 7. The one-line statement

**A creation act names its object: `New` asks for a name, defaults the location
to where the act is standing, and offers no second door — because a workspace
with no unsaved state cannot have a temporary file, only a badly named one.**
