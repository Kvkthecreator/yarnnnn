"""Print the six Supabase Auth templates for pasting into the dashboard.

WHY THIS EXISTS. The templates are rendered into `supabase/templates/auth/` by
`render_supabase_auth_templates.py`, but Supabase reads templates from the
DASHBOARD, not from this tree — and the Management API needs a personal access
token, which this repo deliberately does not hold (only the service key, which
governs data, not project configuration). So the paste is a human action, and it
has been owed since 2026-09-12 with the templates sitting ready the whole time.

The friction was never the typing; it was opening six files, matching each to a
dashboard template name nobody remembers, and finding the right Subject line.
This prints all six in dashboard order, each with its name, subject, and body,
so the job is scroll-and-copy.

Run from the repo root (or anywhere):
    python3 api/scripts/print_auth_templates.py            # all six
    python3 api/scripts/print_auth_templates.py --list     # just the checklist
    python3 api/scripts/print_auth_templates.py magic-link # one by slug

Dashboard: Authentication → Emails → Templates
https://supabase.com/dashboard/project/noxgqcwynkzqabljjyon/auth/templates
"""

from __future__ import annotations

import sys

# Run BY PATH, the interpreter puts api/scripts/ first on sys.path, where the
# `operator/` probe package shadows the stdlib `operator` module — and the very
# next stdlib import (pathlib → re → functools → collections) dies on it. Drop
# that entry before anything else is imported; `-m` never adds it.
#
# This bit THIS script on its first run (2026-09-16), which is the whole reason
# the cleanup item exists: the guard is a per-file tax every new script in this
# directory must remember to pay, and the one that forgets fails at import.
if sys.path and sys.path[0].rstrip("/").endswith("scripts"):
    sys.path.pop(0)

from pathlib import Path  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
TEMPLATES = REPO / "supabase" / "templates" / "auth"

DASHBOARD_URL = (
    "https://supabase.com/dashboard/project/noxgqcwynkzqabljjyon/auth/templates"
)

#: (dashboard template name, file slug, subject). Order matches the dashboard's
#: own tab order, so pasting top-to-bottom needs no hunting.
TEMPLATES_IN_ORDER: tuple[tuple[str, str, str], ...] = (
    ("Confirm sign up", "confirm-signup", "Confirm your yarnnn account"),
    ("Invite user", "invite", "You've been invited to yarnnn"),
    ("Magic Link", "magic-link", "Your sign-in link for yarnnn"),
    ("Change Email Address", "change-email", "Confirm your new email for yarnnn"),
    ("Reset Password", "reset-password", "Reset your yarnnn password"),
    ("Reauthentication", "reauthentication", "Your yarnnn verification code"),
)

RULE = "=" * 78


def _body(slug: str) -> str:
    path = TEMPLATES / f"{slug}.html"
    if not path.exists():
        raise SystemExit(
            f"missing {path}\nRun: cd api && python3 -m scripts.render_supabase_auth_templates"
        )
    return path.read_text().rstrip()


def print_checklist() -> None:
    print(f"\nDashboard: {DASHBOARD_URL}\n")
    print("Paste in this order (Subject is set on the same screen as the body):\n")
    for i, (name, slug, subject) in enumerate(TEMPLATES_IN_ORDER, 1):
        print(f"  {i}. {name:<22} subject: {subject}")
    print(
        "\nReset Password is the one that now matters most: the product grew a real\n"
        "reset door on 2026-09-15, so that mail can actually fire.\n"
    )


def print_one(name: str, slug: str, subject: str, index: int, total: int) -> None:
    print(f"\n{RULE}")
    print(f"  [{index}/{total}]  {name}")
    print(f"  Subject:  {subject}")
    print(f"  Source:   supabase/templates/auth/{slug}.html")
    print(f"{RULE}\n")
    print(_body(slug))
    print()


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if not a.startswith("-")]
    flags = {a for a in argv[1:] if a.startswith("-")}

    if "--list" in flags or "-l" in flags:
        print_checklist()
        return 0

    selected = TEMPLATES_IN_ORDER
    if args:
        wanted = {a.rstrip(".html") for a in args}
        selected = tuple(t for t in TEMPLATES_IN_ORDER if t[1] in wanted)
        if not selected:
            known = ", ".join(slug for _, slug, _ in TEMPLATES_IN_ORDER)
            print(f"no template matched {args}\nknown slugs: {known}", file=sys.stderr)
            return 1

    print_checklist()
    for i, (name, slug, subject) in enumerate(selected, 1):
        print_one(name, slug, subject, i, len(selected))

    print(RULE)
    print(f"  {len(selected)} template(s) above. Dashboard: {DASHBOARD_URL}")
    print(RULE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
