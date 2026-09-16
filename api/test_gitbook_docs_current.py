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
  4. EVERY OFFERED ENGINE'S PROVIDER IS NAMED, derived from `offered_lane_models()`
     — so adding a provider to the roster reddens the docs until they say so.
  5. A UI LABEL THE DOCS SAY TO CLICK STILL EXISTS, derived from the shipped
     context menu — so renaming a menu item reddens the docs that name it.

§4 and §5 were added 2026-09-16 after an audit found the docs naming FOUR providers while
FIVE shipped: xAI/Grok had been in the roster since ADR-559 and appeared nowhere
in the public docs — including on the page that tells a member which companies
their content is sent to. That is the same omission `2e0f4cb` had just fixed in
the product's own /engines page, recurring here because §1–§3 are blind to it:
a provider added is not retired vocabulary, not an app, and not a price.

§5 came from the fix for that audit: "Get Info" was corrected on the three pages
the audit had READ, and a sweep found four more still carrying it — the menu item
was renamed to "Properties" by ADR-400 and seven pages went on telling readers to
click a thing that isn't there.

The general shape both share — a claim that was TRUE and quietly stopped being
true — is what the first three checks cannot see. Each is derived from the live
artifact (the roster, the menu), so the CODE change reddens the docs, not a
reviewer's memory.

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
    # ADR-596+: you pick an ENGINE in Chat, and the roster is Editor/Designer/
    # Blogger — "colleague" was the pre-ADR-559 picker's word for both, and the
    # FAQ was still teaching the retired mechanism ("you pick a colleague and
    # the engine rides behind the name") while the changelog said it was gone.
    # HISTORICAL pages keep it: the changelog records the picker's retirement.
    "colleague": "you pick an engine, not a character (ADR-559 D2 / ADR-596)",
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

# ── 4. Every offered engine's provider is named in the docs ────────────────
# Imported, not regex-scraped: `offered_lane_models()` already encodes the
# retired rule (ADR-559 D2 — a retired engine keeps its pinned lanes running
# but is gone from the chooser), so a member never sees one. Scraping
# LANE_MODELS would re-implement that rule and demand the docs advertise
# engines nobody can pick. One home for the rule, and this reads it.
sys.path.insert(0, str(REPO / "api"))
try:
    from services.lane_runner import offered_lane_models  # noqa: E402

    _providers = sorted({k.split("/", 1)[0] for k in offered_lane_models()})
except Exception as exc:  # pragma: no cover - import failure is the finding
    _providers = []
    check(f"imported offered_lane_models() [{type(exc).__name__}: {exc}]", False)

# Fail CLOSED on a broken read: an empty or implausible roster must not pass
# every downstream check vacuously. (test_adr646 was dead four months this way.)
check(f"read the offered engine roster ({len(_providers)} providers)", 3 <= len(_providers) <= 12)

#: provider key -> the names the docs may use for it. A member reads brands,
#: not routing keys: "Claude" names Anthropic's engine on a page about picking
#: one, "Anthropic" names the company on a page about where content goes. Both
#: satisfy the check; what must never happen is the provider going UNNAMED.
_PROVIDER_WORDS = {
    "anthropic": ("Anthropic", "Claude"),
    "openai": ("OpenAI", "GPT"),
    "gemini": ("Google", "Gemini"),
    "deepseek": ("DeepSeek",),
    "xai": ("xAI", "Grok"),
}

#: Pages that enumerate the engine roster to a member. Each one must name every
#: offered provider — a partial list on any of them is the defect this catches.
#: how-your-data-is-used.md is the load-bearing one: it tells a member which
#: companies receive their content, where an omission is a privacy claim, not a
#: stale feature list.
_ROSTER_PAGES = [
    "README.md",
    "getting-started/quickstart.md",
    "resources/faq.md",
    "concepts/how-your-data-is-used.md",
]

# The mapping must cover the roster BEFORE any page is judged: an unmapped
# provider is skipped by the per-page loop, which would pass every page
# vacuously while the docs stay silent about it. Checked once, not per page.
_unknown = [p for p in _providers if p not in _PROVIDER_WORDS]
check(
    "_PROVIDER_WORDS covers every offered provider"
    + (f" — unmapped: {_unknown}" if _unknown else ""),
    not _unknown,
)

for _rel in _ROSTER_PAGES:
    _path = GITBOOK / _rel
    if not _path.exists():
        check(f"roster page {_rel} exists", False)
        continue
    _text = _path.read_text()
    _absent = [
        p
        for p in _providers
        if p in _PROVIDER_WORDS
        and not any(re.search(rf"\b{re.escape(w)}\b", _text, re.IGNORECASE) for w in _PROVIDER_WORDS[p])
    ]
    check(
        f"{_rel} names every offered provider" + (f" — missing: {_absent}" if _absent else ""),
        not _absent,
    )


# ── 5. A UI label the docs tell a reader to click still exists ─────────────
# Same silent class as §4: "Get Info" was TRUE until ADR-400 renamed the menu
# item to "Properties", and seven pages went on instructing readers to
# right-click a menu entry that isn't there. Derived from the shipped menu, so
# the rename — not a doc edit — is what reddens this.
_menu = (REPO / "web" / "components" / "workspace" / "FileContextMenu.tsx").read_text()
_m = re.search(r"onClick=\{\(\)\s*=>\s*run\(onProperties\)\}>\s*\n\s*(\w[\w ]*)", _menu)
_label = _m.group(1).strip() if _m else ""
check(f"read the Properties menu label from the shipped menu ({_label!r})", bool(_label))

if _label:
    # The docs must name the label the menu actually carries...
    _pages_naming = [
        p.relative_to(GITBOOK).as_posix()
        for p in LIVE_PAGES
        if re.search(rf"\b{re.escape(_label)}\b", p.read_text(), re.IGNORECASE)
    ]
    check(
        f"the docs name the shipped label {_label!r} ({len(_pages_naming)} pages)",
        bool(_pages_naming),
    )
    # ...and must not instruct a click on the name it was renamed FROM.
    _stale = [
        f"{p.relative_to(GITBOOK).as_posix()}:{i}"
        for p in LIVE_PAGES
        for i, line in enumerate(p.read_text().splitlines(), 1)
        if re.search(r"\bGet Info\b", line, re.IGNORECASE)
    ]
    check(
        "no page says 'Get Info' — the menu item is 'Properties' (ADR-400)"
        + (f" [{', '.join(_stale[:3])}]" if _stale else ""),
        not _stale,
    )


# ── 6. The published verb roster matches the server's ───────────────────────
# ADR-543 retired remember/recall/trace with NO aliases and NO shims: a host
# calling them gets tool-not-found. ADR-635 D9 removed that dead list from the
# discovery card and said why — "a second copy of the verb list drifted the
# moment the server's changed". Two copies survived that sweep and kept
# publishing the retired verbs to agents for months: web/lib/openapi.ts (which
# the docs call "authoritative, always-current", and from which an agent
# GENERATES A CLIENT) and the /developers hub. Both were live and linked from
# llms.txt, the sitemap and the footer.
#
# So the roster is DATA and every published copy is checked against it. A verb
# is `_INTEROP_VERBS` + its @mcp.tool, then a row in each copy — never a
# sentence that counts things.
_SERVER_PY = REPO / "api" / "mcp_server" / "server.py"
_server_src = _SERVER_PY.read_text()

_roster: set[str] = set()
try:
    import ast

    for _node in ast.walk(ast.parse(_server_src)):
        # `_INTEROP_VERBS: tuple[...] = (...)` is an AnnAssign, not an Assign —
        # reading only Assign silently found nothing, and an empty roster made
        # the coverage checks below pass VACUOUSLY. Both shapes, and the
        # non-empty check above is what makes that unfixable-silently.
        if isinstance(_node, ast.AnnAssign):
            _targets = [_node.target]
        elif isinstance(_node, ast.Assign):
            _targets = list(_node.targets)
        else:
            continue
        if not any(isinstance(t, ast.Name) and t.id == "_INTEROP_VERBS" for t in _targets):
            continue
        for _elt in getattr(_node.value, "elts", []):
            _parts = getattr(_elt, "elts", [])
            if _parts and isinstance(_parts[0], ast.Constant):
                _roster.add(_parts[0].value)
except SyntaxError:  # pragma: no cover — a broken server.py is its own gate's job
    _roster = set()

check(f"read the interop verb roster from server.py ({len(_roster)} verbs)", len(_roster) >= 6)

# The retired verbs must appear in NO published copy. Checked by name, because
# this is the exact drift that shipped: the words, not the count.
_RETIRED_VERBS = ("remember", "recall", "trace")

if _roster:
    # The OpenAPI spec an agent generates a client from.
    _spec = (REPO / "web" / "lib" / "openapi.ts").read_text()
    # Scope to the INTEROP_VERBS literal — the file also has `name:` on its tags
    # ("read"/"write") and contact ("yarnnn"), which a file-wide scrape reads as
    # verbs and reports as a confident, wrong failure.
    _spec_block = _spec[_spec.index("INTEROP_VERBS") : _spec.index("function verbPath")]
    _spec_verbs = set(re.findall(r'^\s*name: "([a-z_]+)",$', _spec_block, re.MULTILINE))
    check(
        "openapi.ts publishes the server's verb roster"
        + (f" — spec-only={sorted(_spec_verbs - _roster)} missing={sorted(_roster - _spec_verbs)}"
           if _spec_verbs != _roster else ""),
        _spec_verbs == _roster,
    )

    # The developer hub.
    _hub = (REPO / "web" / "app" / "developers" / "page.tsx").read_text()
    _hub_verbs = set(re.findall(r'^\s*name: "([a-z_]+)",$', _hub, re.MULTILINE))
    check(
        "the /developers hub publishes the server's verb roster"
        + (f" — hub-only={sorted(_hub_verbs - _roster)} missing={sorted(_roster - _hub_verbs)}"
           if _hub_verbs != _roster else ""),
        _hub_verbs == _roster,
    )

    # No published surface may ADVERTISE a retired verb as callable. The GitBook
    # MCP page may NAME them in its "reconnect" notice, so only the two
    # machine-facing copies are held to silence.
    for _label, _src in (
        ("openapi.ts", _spec_block),
        ("/developers", _hub),
    ):
        _relapse = [
            v for v in _RETIRED_VERBS
            if re.search(rf'^\s*name: "{v}",$', _src, re.MULTILINE)
        ]
        check(
            f"{_label} advertises no retired memory verb"
            + (f" — found {_relapse}" if _relapse else ""),
            not _relapse,
        )

# The GitBook MCP tool reference must cover every verb the server serves.
_mcp_page = (GITBOOK / "api-reference" / "mcp-tools.md").read_text()
_undocumented = [
    v for v in sorted(_roster)
    if not re.search(rf"^## `{re.escape(v)}`$", _mcp_page, re.MULTILINE)
]
check(
    "mcp-tools.md documents every served verb"
    + (f" — missing: {_undocumented}" if _undocumented else ""),
    not _undocumented,
)

# Every REST group the API overview advertises must have a registered router.
_overview = (GITBOOK / "api-reference" / "overview.md").read_text()
_main_py = (REPO / "api" / "main.py").read_text()
_claimed = set(re.findall(r"\| `/api/([a-z_]+)`", _overview))
_unserved = sorted(
    g for g in _claimed
    if not re.search(rf'include_router\([a-z_]*{g}[a-z_]*\.\w*router', _main_py)
    and f'"/api/{g}' not in _main_py
)
check(
    f"every endpoint group in overview.md has a router ({len(_claimed)} claimed)"
    + (f" — unserved: {_unserved}" if _unserved else ""),
    not _unserved,
)


print("=" * 70)
print(f"gitbook currency gate: {_passed}/{_passed + _failed} passed, {_failed} failed")
print("=" * 70)
sys.exit(1 if _failed else 0)
