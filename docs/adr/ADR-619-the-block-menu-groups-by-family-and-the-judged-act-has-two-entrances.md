# ADR-619 — The block menu groups by family, and the judged act has two entrances

**Status**: Ratified + implemented 2026-08-28. Operator: *"the copy should be nested together with duplicate and copy (not separate as now). than separately, the existing Update in right menu should be deleted in full, and just replaced by the floating re-write. and yes, the re-write button on floating and the right menu's workflow itself can be identical (just another way to access it since some people may open right menu and change their mind to select rewrite)."*

**Completes**: [ADR-616](ADR-616-the-update-door-is-deleted-the-re-arrange-comes-home.md) — that deleted the toolbar door named Update; this deletes the submenu of the same name, the word's last home.
**Amends**: [ADR-613](ADR-613-the-judged-act-leaves-the-menus.md) D1 (Rewrite's reachability from this menu) · [ADR-579](ADR-579-the-verb-grammar.md) D5 (the two-tier verb housing).
**Related**: [ADR-612](ADR-612-the-judged-act-is-one-gesture-at-the-selection.md) §1 (the selection IS the target) · [ADR-462](ADR-462-the-block-context-menu-and-the-metered-badge.md) D1 (a door is a second entrance, never a second write path) · [ADR-525](ADR-525-the-enclosure-verbs.md) D5 (the text tier withholds enclosure verbs) · [ADR-471](ADR-471-the-object-layer.md) D-d (z-order)

---

## 1. Two observations, one menu

**Copy was in the wrong group.** It sat above `Paste here`, which reads as a
clipboard PAIR — but Paste's subject is *the clipboard*, while Copy, Duplicate
and Delete all take *this block* and do something to it or to a copy of it.
Pairing Copy with Paste put the odd one in and split a family of three.

**`Update ▸` held three unrelated families under a verb that named none of
them**: `Turn into` (what the block IS), `Move up/down` (document order),
`Bring forward/backward` (z-order). Every one of its rows paid a hop to reach a
label that added no information. ADR-616 had just deleted the toolbar door of
the same name for the same reason; leaving the word alive here would have kept
it in the one place it was least meaningful.

## 2. Why Rewrite comes back — and why that is not a reversal

ADR-613 D1 moved the judged verbs OUT of this menu. Reading it as "the act must
be unreachable from a menu" would be reading the remedy for the disease. What
D1 measured was a **four-hop ladder** to a committed act on an unambiguous
target; what D2 removed was the **`meter` discriminator** with nothing left to
discriminate; what D5 removed was the **second-menu route**. All three stay
removed.

The operator's reason is the one that decides it: *"some people may open right
menu and change their mind to select rewrite."* A member already in the menu
should not have to dismiss it, re-establish a selection, and find a floating
door. That is ADR-462 D1's own principle — a door is a second **entrance** —
and ADR-367 D3's fast-path/dwell split says the same thing from the other side.

The safety property is not "one door" but **one write path**. §3 D2 makes that
structural rather than promised.

## 3. Decisions

### D1 — The menu groups by FAMILY, and the Update tier is deleted

Copy joins Duplicate and Delete. It is **not** withheld on the text tier the
way those two are (ADR-525 D5: on flow they are enclosure verbs the platform
owns) — copying a paragraph is always meaningful — so it renders just above the
tier-gated pair.

`Update ▸` is deleted and its rows are **flat**. They were never a tier's worth
of cohesion, and each already carries its own honest gate (`turnIntoKinds`
non-empty; `isPaged`; `target.positioned`), so flattening costs no clarity and
removes a hop. Deleted with it: `updateOpen`, its two setters, and its entry in
the inline housing's re-clamp key.

### D2 — The two doors are ONE workflow, composed at ONE site

The floating gesture and the menu row run the same act, and that is enforced
structurally: `seedRewrite` on the surface composes the seed, and each door
supplies only the target it can see. There is exactly **one** `seedComposer('',
…)` call in the surface, and the gate pins that count.

They differ in how the target is found, deliberately:

- the **gesture** reads `gestureTarget` — the live selection rect;
- the **menu** reads its own `StudioContextTarget`.

The menu must NOT read the rect. That arrives from the runtime asynchronously,
so a row keyed on it would be inert depending on message timing — the silent
no-op class this same session fixed in the in-canvas "+ Add". The context
target is present by construction: the menu cannot open without it.

Rewrite leads the mechanical rows because it is the only row here that spends.
**ADR-462 D4's free/metered line is now drawn by POSITION** — the discriminator
that used to draw it is gone (ADR-613 D2) and does not return.

`Check this…` and `Ask about this…` stay deleted: Check left with the meter,
and Ask was deleted outright by operator ruling (ADR-613 D1), rebuildable from
the same seed machinery if ever wanted.

## 4. What this does NOT change

- **No new write path** (ADR-462 D1). The menu row calls the surface's one seed
  producer; every mechanical row calls the op it already called.
- **The floating gesture stays primary.** It is the act at the selection
  (ADR-612 §1); this is the entrance for someone already in the menu.
- **The tier housing is untouched.** `Flyout` still serves every tier that
  exists — now two (insert categories, Turn into) rather than three.
- **ADR-613's substance.** The four-hop ladder, the `meter` discriminator and
  the second-menu route stay deleted, and remain gated.

## 5. Verification

`api/test_adr619_menu_families.py`. Defends: the three unit verbs are one
contiguous family; Copy is not tier-gated while Duplicate/Delete are; no tier
named Update survives, and its state is gone from the re-clamp key; Rewrite
exists only as a caller of the shared producer; and the surface composes the
rewrite seed at exactly one site.

Two existing gates were **re-anchored, not relaxed**, and both had pinned a
spelling rather than an invariant — the failure mode this session met three
times:

- `test_adr586_one_door.py` pinned `<Flyout open={` **>= 3** with a comment
  citing the ADR-584 lesson against hand-kept counts; deleting a second tier
  then made that very number fail. It now ties the floor to the tiers that
  exist. Its inline re-clamp check spelled out `${turnOpen}|${insertOpen}|${updateOpen}`
  and now asserts the live tiers are IN the key, so a correct deletion cannot
  turn it red.
- `test_adr612_judged_gesture.py` asserted `"Rewrite…" not in block_menu` and
  `"menuRewrite" not in surface`. Both now assert the property that actually
  matters — one producer, and any menu row routing through it.
