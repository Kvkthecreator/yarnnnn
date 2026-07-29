# ADR-498 — The Invite Names the Wrong Account, and Transactional Email Gets One Shell

**Status**: Accepted (2026-07-29, operator-ratified — "on the user invite workflow, I opened this via email, but doesn't work… and separately, can you update the design considerations for the email"). Implemented same day.
**Date**: 2026-07-29
**Authors**: KVK (operator) + Claude (collaborator)
**Hat**: A
**Dimension**: Channel (Axiom 6 — the threshold surface a new member meets first)
**Relates to**: ADR-404 step 5 (member provisioning — the invite flow), ADR-386 D1 (the grant an accept mints), ADR-202 (external channels are pointers, never content replacements), ADR-431 (the connecting-member model these members populate), ADR-496/497 (the roster work that surfaced the member arc)
**Amends**: nothing. The server contract is **unchanged** — the 403 was correct.

---

## 1. Context — a correct gate presented as a dead end

Operator, opening an invite link from email: *"doesn't work"* — the console showed `Failed to load resource: 403` and the page offered nothing actionable.

**The 403 was right.** `accept_invite` binds an invite to its address:

```python
if not user_email or user_email.strip().lower() != invite["email"]:
    raise InviteError("email_mismatch", ...)
```

Live state confirmed the gate behaved correctly — the invite was `pending`, unexpired, and the invitee *does* have an account with the exact matching address. The link had simply been opened while signed in as the workspace owner, not the invitee. A different account cannot accept another person's invite; that is the whole point of the binding.

**The defect was in presentation.** Both facts — *who was invited* (the page already fetches it via `previewInvite`) and *who is signed in* (a session read) — were knowable **before** the click. Instead the page rendered an Accept button that was guaranteed to fail, then printed the raw server detail with no route forward. The invitee's first impression of a shared workspace was an error code.

This generalizes past invites:

> **When a gate's outcome is predictable from state the surface already holds, surface the state — do not let the user discover it as a failure.**

## 2. D1 — The wrong-account state is named before the click

`/invite/[token]` now reads the signed-in identity alongside the invite preview and derives `wrongAccount`, comparing trimmed + lowercased — mirroring the server's own test, so the FE can never disagree with the gate about what counts as a match.

On mismatch it replaces the Accept button (offering a button guaranteed to 403 *is* the original defect) with:

- a named diagnosis — *"this invite was sent to X, but you're signed in as Y"*, both addresses stated;
- **the way out**: sign out and return to this same invite via `/auth/login?next=/invite/{token}`, so the member lands back on the accept as the right person instead of re-opening the email.

One real bug caught while wiring this: the natural-looking `/login` does not exist in this app (the route is `/auth/login`), so the escape hatch would itself have 404'd. `getSafeNextPath` was checked to confirm `/invite/*` survives the round-trip — it rejects only off-site and `/auth/*` paths.

The server contract is untouched: `email_mismatch → 403` remains, and the gate test asserts it still does. Only its *presentation* changed.

## 3. D2 — Transactional email gets one house shell

The invite email was the least-branded thing yarnnn sends — bare `<p>` tags and a raw blue anchor — while being a member's **first** contact with the product. Meanwhile `notifications.py` carried an unshared house style (system font stack, 600px column, `#111` pill CTA, muted footer) that every other sender re-inlined by hand.

Hand-styling the invite would have created a sixth private variant. Instead `api/services/email_shell.py` is the single shell: senders supply *content*, the shell owns the frame (wordmark · column · type scale · button · footer · preheader).

Three constraints are encoded deliberately, because email is not the web:

- **No design-system tokens.** A client that strips `:root` would render an unstyled page, so the palette is fixed hex mirroring the system's *intent* (near-black ink, generous whitespace, one accent, quiet metadata) in the only vocabulary mail clients honor. Every rule is inlined; layout is a table, never flex/grid; the CTA is a table-wrapped anchor because Outlook ignores padding on inline `<a>`.
- **Dark mode is a suggestion.** `prefers-color-scheme` is honored by Apple Mail and partially by Gmail, ignored elsewhere. The light palette is the base and must stand alone; the dark block is **additive only**.
- **Pointer-only (ADR-202).** One primary CTA, no content replacement.

A `text/plain` alternative is retained — HTML-only mail is a deliverability and accessibility regression.

## 4. D3 — The mail stops setting up the failure

The invited address now appears in the **body**, not only in fine print: *"This invite was sent to X. Accept it while signed in with that address."*

D1 catches the mismatch in the app; D3 keeps the mail from causing it. Both are cheap, and the failure mode was real enough to reach the operator.

## 5. Validation

- `api/test_adr498_invite_flow.py` — **20/20**: pre-click detection, server-mirroring comparison, the button replacement, both addresses named, the escape hatch (**including that it targets `/auth/login`, not the non-existent `/login`**), the unchanged server contract, shell reuse, the deleted bare markup, preheader, text alternative, and four email-client constraints (table layout, inlined styles, additive dark mode, no external assets).
- **Executed, not just grepped**: `send_invite_email` was run with a stubbed transport — returns `True`, renders through the shell, names the bound address, embeds the correct link, and emits a text alternative.
- Rendered and screenshotted headless to confirm the layout holds; HTML parsed with zero unclosed or mismatched tags.
- `tsc --noEmit` clean; `next build` green (170/170).

**Not verified** (needs a human): the email as rendered by an actual client (Gmail/Apple Mail/Outlook each differ — the constraints above are defensive, not proof), and the wrong-account page in a live browser. A cheap end-to-end check is available: re-open the still-pending invite as the owner and confirm the new state appears instead of a 403.
