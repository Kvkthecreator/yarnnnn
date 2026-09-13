# Supabase Auth email templates

Rendered by `api/scripts/render_supabase_auth_templates.py` from the one house shell
(`api/services/email_shell.py`, ADR-498 D2 / ADR-650 D8). **Edit the renderer, not these files** —
the ADR-650 gate holds them in sync. Supabase reads templates from the dashboard, not from this
tree: after a change, paste each file's contents into **Authentication → Emails → Templates**
(the matching template name below) and set its **Subject**.

| Dashboard template | File | Subject |
|---|---|---|
| Confirm sign up | `confirm-signup.html` | Confirm your yarnnn account |
| Invite user | `invite.html` | You've been invited to yarnnn |
| Magic Link | `magic-link.html` | Your sign-in link for yarnnn |
| Change Email Address | `change-email.html` | Confirm your new email for yarnnn |
| Reset Password | `reset-password.html` | Reset your yarnnn password |
| Reauthentication | `reauthentication.html` | Your yarnnn verification code |

Two are not reached by the product today: *Invite user* fires only from the dashboard's own
Invite button (the product's workspace invite is `services/workspace_invites.py`, sent over the
Resend API), and *Reauthentication* has no door (no in-app password-change surface). They are
rendered so that nothing Supabase can send is unbranded.

Sender identity and SMTP live on the same page (SMTP Settings); the state is recorded in
`docs/database/ACCESS.md`.
