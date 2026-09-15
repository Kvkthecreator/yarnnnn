"""Gate: the public docs do not contradict the product (2026-09-16).

WHY THIS EXISTS. `docs/gitbook/` is what a prospective member reads before they
trust us with anything. It was last synced 2026-03-22 and drifted for roughly six
months with nothing to notice: a first-time-visitor pass on 2026-09-15 found the
docs promising a free tier one person larger than the pricing page, describing a
"workspace steward" retired by ADR-632, and naming two apps (Docs, Studio) that
had been renamed. Three shipped, Dock-pinned apps had no page at all.

Prose cannot be typechecked, and nobody re-reads 30 files on a schedule. So this
holds the three things that actually rotted, each derived from live code rather
than restated:

  1. RETIRED VOCABULARY stays out. A term the product deleted must not describe
     the product. (The ratchet idiom of test_retired_vocabulary_ratchet.py.)
  2. EVERY DOCK APP HAS A PAGE, derived from the frontend's own default Dock —
     so the NEXT app to ship is red until it is documented, which is exactly the
     gap Blogger/Images/Reach fell through.
  3. PRICING FACTS match `billing_tiers.py`, not a number someone typed once.

Run: python3 -B test_gitbook_docs_current.py   (script-shaped — read the count)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GITBOOK = REPO / "docs" / "gitbook"

_passed = 0
_failed = 0


def check(label: str, ok: bool) -> None:
    global _passed, _failed
    if ok:
        _passed += 1
        print(f"PASS  {label}")
    else:
        _failed += 1
        print(f"FAIL  {label}")


PAGES = sorted(GITBOOK.rglob("*.md"))
# The changelog is a HISTORICAL record: "Images went internal (Jul 28)" is true
# of July and must stay sayable. Everything else describes the product in the
# present tense and is held to the present tense.
HISTORICAL = {"changelog.md", "versioning.md"}
LIVE_PAGES = [p for p in PAGES if p.name not in HISTORICAL]

check(f"found public doc pages ({len(PAGES)})", len(PAGES) >= 25)
check(f"found present-tense pages to hold ({len(LIVE_PAGES)})", len(LIVE_PAGES) >= 20)


# ── 1. Retired vocabulary ───────────────────────────────────────────────────
# Each entry: the term, and why it is retired. A term is matched case-insensitively
# on a word boundary so "Studio" does not hide inside "studio.md" links we removed.
RETIRED: dict[str, str] = {
    "freddie": "the steward seat is retired (ADR-632)",
    "workspace steward": "the steward seat is retired (ADR-632)",
    "radar": "the app is DELETED, not paused (ADR-592)",
    "thinker": "the agent roster is Editor/Designer/Blogger (ADR-596+)",
    "researcher": "the agent roster is Editor/Designer/Blogger (ADR-596+)",
    "recurrence": "recurrences retired (ADR-603 D5)",
    "monthly allowance": "the allowance layer is retired (ADR-490 §1③)",
}
#: A line that DENIES a retired thing is correct prose, not a relapse — "there is
#: no monthly allowance on any plan" is exactly what the docs should say, and a
#: blunt substring check reddens it. Only a line that ASSERTS the thing counts.
_DENIAL = re.compile(
    r"\b(no|not|never|retired|removed|deleted|gone|isn't|doesn't|used to|no longer)\b",
    re.IGNORECASE,
)

for term, why in RETIRED.items():
    pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
    hits = [
        f"{p.relative_to(GITBOOK)}:{i}"
        for p in LIVE_PAGES
        for i, line in enumerate(p.read_text().splitlines(), 1)
        if pattern.search(line) and not _DENIAL.search(line)
    ]
    check(
        f"no page says {term!r} — {why}" + (f" [{', '.join(hits[:3])}]" if hits else ""),
        not hits,
    )

# "Studio" is a special case: the API ROUTE is still literally /api/studio, so the
# word may appear where it names that route — and nowhere else.
studio_hits = [
    f"{p.relative_to(GITBOOK)}:{i}"
    for p in LIVE_PAGES
    for i, line in enumerate(p.read_text().splitlines(), 1)
    if re.search(r"\bstudio\b", line, re.IGNORECASE) and "/api/studio" not in line
]
check(
    "the word 'Studio' appears only where it names the /api/studio route"
    + (f" [{', '.join(studio_hits[:3])}]" if studio_hits else ""),
    not studio_hits,
)


# ── 2. Every Dock app has a page — derived, never listed here ───────────────
prefs = (REPO / "web" / "lib" / "shell" / "surface-preferences.ts").read_text()
m = re.search(r"DEFAULT_KEPT_SURFACES[^=]*=\s*\[(.*?)\]", prefs, re.S)
# STRIP COMMENTS FIRST. That array documents its own DELETIONS in place —
# `// 'radar' — DELETED 2026-08-21` sits between the live entries — so a naive
# quote-scrape reads the retired slugs as current and demands docs for three
# apps that no longer exist. (The first cut of this gate did exactly that.)
dock_block = re.sub(r"//.*$", "", m.group(1), flags=re.M) if m else ""
dock = re.findall(r"['\"]([a-z-]+)['\"]", dock_block)
check(f"read the default Dock from the frontend ({len(dock)} apps)", 5 <= len(dock) <= 12)
# The retired slugs must NOT have come through — a completeness check on the
# strip itself, since a broken strip fails open into "document more apps".
check(
    "the Dock read excludes commented-out (deleted) slugs",
    not ({"docs", "radar", "strings"} & set(dock)),
)

#: Apps whose page is not under apps/ — chat has one, and so does every other
#: dock app today. An app added to the Dock with no page turns this red.
for slug in dock:
    page = GITBOOK / "apps" / f"{slug}.md"
    check(f"dock app {slug!r} has docs/gitbook/apps/{slug}.md", page.exists())

# ...and the nav lists it, or a reader never finds it.
summary = (GITBOOK / "SUMMARY.md").read_text()
missing_nav = [s for s in dock if f"apps/{s}.md" not in summary]
check(
    "SUMMARY.md links every dock app" + (f" — missing: {missing_nav}" if missing_nav else ""),
    not missing_nav,
)


# ── 3. Pricing matches the live tier config ────────────────────────────────
tiers = (REPO / "api" / "services" / "billing_tiers.py").read_text()
seats = re.search(r'"included_seats":\s*(\d+)', tiers)
seat_price = re.search(r'"additional_seat_usd":\s*([\d.]+)\s*,\s*#(?!\s*free)', tiers)
allowance_values = set(re.findall(r'"monthly_allowance_usd":\s*([\d.]+)', tiers))

check("read included_seats from billing_tiers.py", bool(seats))
check(
    "every tier's monthly allowance is 0.0 (the allowance is retired)",
    allowance_values == {"0.0"},
)

plans = (GITBOOK / "plans" / "plans.md").read_text()
if seats:
    n = int(seats.group(1))
    words = {1: "one", 2: "two", 3: "three"}.get(n, str(n))
    check(
        f"plans.md says the free tier covers {words} people (included_seats={n})",
        re.search(rf"free for {words}\b", plans, re.IGNORECASE) is not None,
    )
    # The paid boundary is the NEXT person after the included seats.
    nxt = {2: "3rd", 3: "4th"}.get(n, f"{n+1}th")
    check(
        f"plans.md names the {nxt} person as the paid boundary",
        nxt in plans,
    )

check(
    "plans.md does not advertise the usage multiplier (ADR-490: stated on no surface)",
    "1.30" not in plans and "30%" not in plans,
)
check(
    "plans.md no longer names the retired 'Starter' plan",
    not re.search(r"\bStarter\b", plans),
)

print("=" * 70)
print(f"gitbook currency gate: {_passed}/{_passed + _failed} passed, {_failed} failed")
print("=" * 70)
sys.exit(1 if _failed else 0)
