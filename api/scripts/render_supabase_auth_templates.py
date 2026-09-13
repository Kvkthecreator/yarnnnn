"""Render the Supabase Auth email templates from the one house shell (ADR-650 D8).

Supabase Auth sends six mails of its own — confirm sign-up, invite, magic
link, change email, reset password, reauthentication — from templates held in
the dashboard (Authentication → Emails → Templates), not in this tree. Left at
their defaults they are the least branded thing a new member sees, and the
first (the ADR-498 lesson, again). This script renders all six through
`services/email_shell.render_email` — the same frame every mail yarnnn sends
wears — into `supabase/templates/auth/`, which is the SOURCE OF TRUTH for what
is pasted into the dashboard. The ADR-650 gate holds the files in sync with
this renderer, so a template edit lands here first and the paste follows.

Variables are Go-template placeholders Supabase fills at send time:
  {{ .ConfirmationURL }}  the action link (verify → redirect_to)
  {{ .Email }}            the recipient's address
  {{ .NewEmail }}         change-email only
  {{ .Token }}            the 6-digit code (reauthentication)
They pass through the shell untouched (they are content, not format args).

Run from api/:  python3 -m scripts.render_supabase_auth_templates
"""

from __future__ import annotations

import sys

# Run BY PATH, the interpreter puts api/scripts/ first on sys.path, where the
# `operator/` probe package shadows the stdlib `operator` module — and the
# very next stdlib import (pathlib → re → functools → collections) dies on it.
# Drop that entry before anything else is imported; `-m` never adds it.
if sys.path and sys.path[0].rstrip("/").endswith("scripts"):
    sys.path.pop(0)

from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.email_shell import paragraph, render_email  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "supabase" / "templates" / "auth"

_URL = "{{ .ConfirmationURL }}"
_FALLBACK = (
    "If the button doesn't work, open this link: "
    f'<a href="{_URL}" style="color:inherit;word-break:break-all;">{_URL}</a>'
)


def _code_block(token: str) -> str:
    return (
        '<p style="margin:8px 0 16px 0;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;'
        f'font-size:28px;font-weight:600;letter-spacing:0.2em;color:#111111;">{token}</p>'
    )


# (file stem, dashboard template name, subject, render kwargs)
TEMPLATES: list[tuple[str, str, str, dict]] = [
    (
        "confirm-signup", "Confirm sign up", "Confirm your yarnnn account",
        dict(
            preheader="One click to confirm {{ .Email }} and open your workspace.",
            heading="Confirm your email",
            body_html=paragraph(
                "You signed up for yarnnn with <strong>{{ .Email }}</strong>. Confirm the "
                "address and your workspace opens: a shared workspace where every file "
                "records who changed it."
            ),
            cta_label="Confirm email", cta_url=_URL, footnote_html=_FALLBACK,
            footer_html="If you didn't sign up, you can ignore this email — nothing happens without the click.",
        ),
    ),
    (
        "invite", "Invite user", "You've been invited to yarnnn",
        dict(
            preheader="An account was created for {{ .Email }}.",
            heading="You're invited",
            body_html=paragraph(
                "Someone at yarnnn created an account for <strong>{{ .Email }}</strong>. "
                "Accept the invitation to set a password and open your workspace."
            ),
            cta_label="Accept invitation", cta_url=_URL, footnote_html=_FALLBACK,
            footer_html="If you weren't expecting this, you can ignore this email.",
        ),
    ),
    (
        "magic-link", "Magic Link", "Your sign-in link for yarnnn",
        dict(
            preheader="Your one-time sign-in link.",
            heading="Sign in to yarnnn",
            body_html=paragraph(
                "Here is the one-time link you asked for. It signs in "
                "<strong>{{ .Email }}</strong> on the device that opens it."
            ),
            cta_label="Sign in", cta_url=_URL, footnote_html=_FALLBACK,
            footer_html="If you didn't request this link, ignore this email. The link only works once.",
        ),
    ),
    (
        "change-email", "Change Email Address", "Confirm your new email for yarnnn",
        dict(
            preheader="Confirm the change to {{ .NewEmail }}.",
            heading="Confirm your new address",
            body_html=paragraph(
                "You asked to change the email on your yarnnn account from "
                "<strong>{{ .Email }}</strong> to <strong>{{ .NewEmail }}</strong>. "
                "Confirm to complete the change."
            ),
            cta_label="Confirm new email", cta_url=_URL, footnote_html=_FALLBACK,
            footer_html="If you didn't request this, ignore this email — the change won't happen without the click.",
        ),
    ),
    (
        "reset-password", "Reset Password", "Reset your yarnnn password",
        dict(
            preheader="Choose a new password.",
            heading="Reset your password",
            body_html=paragraph(
                "A password reset was requested for <strong>{{ .Email }}</strong>. "
                "Open the link to choose a new one."
            ),
            cta_label="Reset password", cta_url=_URL, footnote_html=_FALLBACK,
            footer_html="If you didn't ask for this, ignore this email — your password stays as it is.",
        ),
    ),
    (
        "reauthentication", "Reauthentication", "Your yarnnn verification code",
        dict(
            preheader="Your verification code.",
            heading="Your verification code",
            body_html=paragraph("Enter this code to confirm it's you:") + _code_block("{{ .Token }}"),
            footer_html="The code expires shortly. If you didn't request it, ignore this email.",
        ),
    ),
]


def render_all() -> dict[str, str]:
    """stem → html, in memory (the gate compares this against the files)."""
    return {stem: render_email(**kw) for stem, _, _, kw in TEMPLATES}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for stem, html in render_all().items():
        (OUT / f"{stem}.html").write_text(html, encoding="utf-8")
    rows = "\n".join(
        f"| {name} | `{stem}.html` | {subject} |" for stem, name, subject, _ in TEMPLATES
    )
    (OUT / "README.md").write_text(
        "# Supabase Auth email templates\n\n"
        "Rendered by `api/scripts/render_supabase_auth_templates.py` from the one house shell\n"
        "(`api/services/email_shell.py`, ADR-498 D2 / ADR-650 D8). **Edit the renderer, not these files** —\n"
        "the ADR-650 gate holds them in sync. Supabase reads templates from the dashboard, not from this\n"
        "tree: after a change, paste each file's contents into **Authentication → Emails → Templates**\n"
        "(the matching template name below) and set its **Subject**.\n\n"
        "| Dashboard template | File | Subject |\n|---|---|---|\n" + rows + "\n\n"
        "Two are not reached by the product today: *Invite user* fires only from the dashboard's own\n"
        "Invite button (the product's workspace invite is `services/workspace_invites.py`, sent over the\n"
        "Resend API), and *Reauthentication* has no door (no in-app password-change surface). They are\n"
        "rendered so that nothing Supabase can send is unbranded.\n\n"
        "Sender identity and SMTP live on the same page (SMTP Settings); the state is recorded in\n"
        "`docs/database/ACCESS.md`.\n"
    )
    print(f"rendered {len(TEMPLATES)} templates → {OUT.relative_to(REPO)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
