"""ADR-660 gate — the interface speaks Korean.

    D1  the roster and the catalogs agree
    D2  one resolution chain: account → device cookie → Accept-Language → English;
        a guess is never written down
    D3  the provider is scoped — the root layout stays static, and no unscoped
        route mounts a translated component
    D4  the catalogs hold: parity, placeholders, "it is Korean", every call
        resolves, and coverage only ratchets down
    D5  no language instruction reaches the lane frame

Script-shaped: run it and READ THE COUNT (`pytest` collects nothing from it).

    cd api && python3 test_adr660_the_interface_speaks_korean.py

Static by necessity — the subject is the web tree. What reading cannot prove (the
switch actually re-renders, the account preference follows a member to a second
device) is the click-pass in ADR-660 §9, not this file. Each arm was proven RED
by editing the shipped file in place and restoring it in place.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

API = Path(__file__).resolve().parent
REPO = API.parent
WEB = REPO / "web"
sys.path.insert(0, str(API))

from test_voice_no_kernel_nouns_in_copy import _jsx_text_line_numbers  # noqa: E402

PASS = FAIL = 0


def check(name: str, cond, note: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name}" + (f" — {note}" if note else ""))


def flatten(node, prefix="") -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in node.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            out.update(flatten(value, path))
        else:
            out[path] = value
    return out


def read(rel: str) -> str:
    return (WEB / rel).read_text(encoding="utf-8")


def strip_comments(src: str) -> str:
    """Block and whole-line comments only. A `//` mid-line is left alone — a
    stripper that cuts `//…` to end-of-line eats the URL it is hunting."""
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return "\n".join(line for line in src.splitlines() if not line.lstrip().startswith("//"))


# ── D1 — the roster and the catalogs agree ───────────────────────────────────
print("D1 — roster")
config = read("i18n/config.ts")
roster = re.search(r"LOCALES\s*=\s*\[([^\]]*)\]", config)
LOCALES = re.findall(r'"([a-z]{2}(?:-[A-Z]{2})?)"', roster.group(1)) if roster else []
default = re.search(r'DEFAULT_LOCALE:\s*Locale\s*=\s*"([a-z-]+)"', config)
DEFAULT = default.group(1) if default else ""
on_disk = sorted(p.stem for p in (WEB / "messages").glob("*.json"))
check("the roster names at least English and Korean", {"en", "ko"} <= set(LOCALES), f"LOCALES={LOCALES}")
check("every roster locale has a catalog, and no catalog is off the roster",
      sorted(LOCALES) == on_disk, f"roster={sorted(LOCALES)} disk={on_disk}")
check("every roster locale has an endonym",
      all(re.search(rf"\b{loc}:\s*\"[^\"]+\"", config) for loc in LOCALES))

CATALOGS = {loc: flatten(json.loads(read(f"messages/{loc}.json"))) for loc in on_disk}
BASE = CATALOGS.get(DEFAULT, {})

# ── D4 — the catalogs hold ────────────────────────────────────────────────────
print("D4 — catalogs")
check("the default catalog is not empty", len(BASE) > 0)

# ⚠️ `\w` MATCHES HANGUL in Python. `{count, plural, other {다른 멤버 #명}}` read
# `다른` as a second ICU argument, so a legitimate Korean plural whose body opens
# with a word registered as argument DRIFT against its English twin. A real ICU
# argument is ASCII-identifier-shaped and is followed by `}` or `,` — anchor on
# that instead of on "some word characters after a brace".
ICU_ARG = re.compile(r"\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*[,}]")
HANGUL = re.compile(r"[가-힣]")
# Names that do not translate. A value made ONLY of these (plus punctuation,
# digits and ICU arguments) is allowed to carry no Hangul.
# `Blogger`, `Supervisor` and `Reach` are the product's OWN app names, which
# D6 keeps in Latin script the way the product's name is: they name a thing in
# the workspace, not a common noun ("블로거" would read as a person who blogs).
# A key ending `Placeholder` shows a literal FORMAT — a URL shape, an email
# shape, a header name, an example path. Translating one would teach the member
# a shape the field does not accept, so those keys are exempt from the Hangul
# rule (filtered below, not listed here).
UNTRANSLATED_OK = {"yarnnn", "yarnnn.com", "Google", "GitHub", "Notion", "Slack", "MCP", "AI",
                   "Blogger", "Supervisor", "Reach",
                   # `Freddie` survives only as a display-resolved attribution
                   # prefix on historical revisions (the seat is retired,
                   # ADR-632); `Free` is a served plan name.
                   "Freddie", "Free", "YARNNN",
                   # A FILENAME a client fetches, not a word: translating it
                   # would send a developer to a path that does not exist.
                   "llms.txt"}

for loc, flat in CATALOGS.items():
    if loc == DEFAULT:
        continue
    missing = sorted(set(BASE) - set(flat))
    orphan = sorted(set(flat) - set(BASE))
    check(f"[{loc}] parity — no key missing", not missing, f"{len(missing)} missing, e.g. {missing[:3]}")
    check(f"[{loc}] parity — no orphan key", not orphan, f"{len(orphan)} orphan, e.g. {orphan[:3]}")
    drift = [k for k in flat if k in BASE and set(ICU_ARG.findall(flat[k])) != set(ICU_ARG.findall(BASE[k]))]
    check(f"[{loc}] every key carries the same ICU arguments as {DEFAULT}", not drift, f"e.g. {drift[:3]}")

if "ko" in CATALOGS:
    not_korean = []
    for key, value in CATALOGS["ko"].items():
        if HANGUL.search(value):
            continue
        residue = ICU_ARG.sub("", value)
        for name in sorted(UNTRANSLATED_OK, key=len, reverse=True):
            residue = residue.replace(name, "")
        if re.search(r"[A-Za-z]{2,}", residue):
            not_korean.append(key)
    not_korean = [k for k in not_korean if not k.endswith("Placeholder")]
    check("[ko] every value is Korean, or only names that do not translate",
          not not_korean, f"{len(not_korean)} English values, e.g. {not_korean[:3]}")

# ⭐ And the INVERSE. A pass that writes one plural arm for both locales ships
# Korean counters inside English sentences ("2개 of the tools…", "5명 · 3석
# billed") — 25 of them, once. Argument parity cannot see it: the arguments are
# identical, it is the TEXT that is in the wrong language. Caught by rendering
# both catalogs, or by this.
# ⭐ AND the plural arms. English needs `one` and `other`; Korean has no plural
# form and takes `other` alone. A pass that writes the KOREAN shape once and
# copies it to both locales renders "1 people", "1 sources", "1 words" — 13 of
# them, once, and every other arm of this gate stayed green over it (the key
# exists, the arguments match, the value is in the right language). Only the
# DEFAULT locale is held: `other`-only is correct Korean.
plural_no_one = sorted(
    k for k, v in BASE.items()
    if "plural" in v and re.search(r"\bone\s*\{", v) is None
)
check(f"[{DEFAULT}] every plural carries a `one` arm — `other` alone renders \"1 people\"",
      not plural_no_one, f"{len(plural_no_one)}, e.g. {plural_no_one[:3]}")

english_with_hangul = sorted(k for k, v in BASE.items() if HANGUL.search(v))
check(f"[{DEFAULT}] no value carries Korean text — a shared plural arm is the usual cause",
      not english_with_hangul,
      f"{len(english_with_hangul)}, e.g. {english_with_hangul[:3]}")

# Every call resolves. A missing key renders its own path in production, silently.
SCOPED_DIRS = ["app", "components", "lib", "contexts"]
# ⚠️ 2026-09-20 — this matched a DOUBLE-quoted namespace only. The repo writes
# both (`useTranslations('chat')` is the prevailing style under components/),
# so 17 of 22 bindings never bound and the key arm below checked NOTHING in the
# files that had just been translated: green over unread work. Both quote
# styles, both here and at the call site.
USE = re.compile(
    r"const\s+(\w+)\s*=\s*(?:await\s+)?(?:useTranslations|getTranslations)\("
    r"\s*(?:\"([^\"]*)\"|'([^']*)')?\s*\)"
)
unresolved: list[str] = []
calls = 0
translated_files: set[Path] = set()
for top in SCOPED_DIRS:
    for path in (WEB / top).rglob("*.ts*"):
        if "node_modules" in path.parts or path.suffix not in (".ts", ".tsx"):
            continue
        src = strip_comments(path.read_text(encoding="utf-8", errors="ignore"))
        bindings = [(var, dq or sq) for var, dq, sq in USE.findall(src)]
        if not bindings:
            continue
        translated_files.add(path)
        namespaces = [ns for _, ns in bindings]
        # ⚠️ ONE FILE CAN BIND ONE NAME TO SEVERAL NAMESPACES — a page whose
        # Suspense fallback and inner component each hold their own `t`, a pane
        # whose helper components each scope themselves. A regex cannot see
        # which `t` is in scope at a given line (that needs the component tree),
        # so a key RESOLVES when it exists under ANY namespace that name is
        # bound to IN THIS FILE. Narrower than per-call attribution, and it
        # still catches what matters: a key that exists under NONE of them.
        by_var: dict[str, list[str]] = {}
        for var, ns in bindings:
            by_var.setdefault(var, []).append(ns)
        for var, var_namespaces in by_var.items():
            # `t(…)` AND its methods: `t.rich(…)` embeds components, `t.has(…)`
            # / `t.raw(…)` read the same catalog. Requiring a bare `t(` left a
            # broken `t.rich` key green (found 2026-09-20, the settings pane).
            for dq_key, sq_key in re.findall(
                rf"(?<![\w.]){re.escape(var)}(?:\.(?:rich|has|raw|markup))?\("
                rf"\s*(?:\"([^\"]+)\"|'([^']+)')",
                src,
            ):
                key = dq_key or sq_key
                calls += 1
                candidates = [f"{ns}.{key}" if ns else key for ns in var_namespaces]
                if not any(c in BASE for c in candidates):
                    unresolved.append(f"{path.relative_to(WEB)} → {candidates[0]}")
        # A module-level roster holds KEYS (`labelKey: "panes.account"`), worded at render.
        for key in re.findall(r"\b\w*[kK]ey:\s*\"([a-z][\w]*(?:\.[\w]+)+)\"", src):
            calls += 1
            if not any((f"{ns}.{key}" if ns else key) in BASE for ns in namespaces):
                unresolved.append(f"{path.relative_to(WEB)} → (roster key) {key}")
check("the scan found translation calls to resolve", calls > 0, "zero calls — the arm is reading nothing")
check("every t(…) and every roster key resolves in the default catalog",
      not unresolved, f"{len(unresolved)} unresolved, e.g. {unresolved[:3]}")

# A DYNAMIC key — `t(`${step.name}.doing`)` — is invisible to the scan above: a
# missing one renders its own path in production, silently. The two rosters that
# build keys from data are checked against the catalogs directly, both ways, so
# neither a new verb nor a deleted message can drift out of sight.
tool_src = strip_comments(read("components/chat-surface/toolLabels.ts"))
tool_verbs = dict(re.findall(r"^  ([A-Za-z_]+): (true|false),", tool_src, re.M))
check("the tool-verb roster reads something", len(tool_verbs) > 10, f"{len(tool_verbs)} verbs")
verb_drift: list[str] = []
for name, takes_subject in tool_verbs.items():
    forms = ["doing", "did"] + (["withSubject"] if takes_subject == "true" else [])
    for loc, flat in CATALOGS.items():
        for form in forms:
            if f"chat.tools.{name}.{form}" not in flat:
                verb_drift.append(f"[{loc}] missing chat.tools.{name}.{form}")
    if takes_subject == "false" and f"chat.tools.{name}.withSubject" in BASE:
        verb_drift.append(f"orphan chat.tools.{name}.withSubject — the code never asks for it")
for key in BASE:
    if key.startswith("chat.tools.") and key.split(".")[2] not in tool_verbs:
        verb_drift.append(f"{key} names no verb in toolLabels.ts")
check("every tool verb's messages exist in every catalog, and none is orphaned",
      not verb_drift, f"{len(verb_drift)}, e.g. {verb_drift[:3]}")
seed_drift = [
    f"[{loc}] missing chat.lane.seedTarget.{k}"
    for k in ("selection", "page", "block")
    for loc, flat in CATALOGS.items()
    if f"chat.lane.seedTarget.{k}" not in flat
]
check("every seed-target shape the composer can build is named", not seed_drift, f"{seed_drift}")

# ── D3 — the provider is scoped ───────────────────────────────────────────────
print("D3 — scope")
root_layout = strip_comments(read("app/layout.tsx"))
check("the root layout imports nothing from next-intl or the locale resolver",
      not re.search(r"from\s+[\"'](next-intl|@/i18n|@/components/i18n)", root_layout))
# FOUR scopes since 2026-09-21. `app/admin` joined not because the console is
# translated — it is a Hat-B instrument and its chrome stays English — but
# because it mounts `FeedbackProvider`, whose confirm shell IS member-facing
# copy. A shared component's MOUNTS decide where a scope is needed, never the
# route's own audience.
SCOPES = [
    "app/(authenticated)/layout.tsx",
    "app/auth/login/layout.tsx",
    "app/mcp/auth/layout.tsx",
    "app/admin/layout.tsx",
]
for rel in SCOPES:
    check(f"{rel} mounts the scope", "<IntlScope>" in strip_comments(read(rel)))

# ── The FIFTH scope is per-PAGE, not per-layout (the marketing pass) ────────
# `/` and `/ko` each wrap their body in `<MarketingIntlScope locale=…>`, which
# takes the locale as an ARGUMENT instead of resolving it from a cookie. That
# is what keeps a marketing route statically prerendered: the four layout
# scopes above all read request state, and a cookie read would drop every
# marketing page from `○` to `ƒ` — measured, and the invariant ADR-660 D3 was
# built to protect.
#
# So a page carrying its own `<MarketingIntlScope>` IS scoped, and the mount
# check must see that or it reports a false positive on the very route that is
# doing the right thing. It is checked by CONTENT, not by path: a page that
# renders a translated component without providing the scope still fails.
PAGE_SCOPE = "<MarketingIntlScope"
scope_dirs = [(WEB / rel).parent for rel in SCOPES]


def resolve_import(spec: str, importer: Path) -> Path | None:
    base = (WEB / spec[2:]) if spec.startswith("@/") else (importer.parent / spec) if spec.startswith(".") else None
    if base is None:
        return None
    for candidate in (base.with_suffix(".tsx"), base.with_suffix(".ts"), base / "index.tsx", base / "index.ts"):
        if candidate.exists():
            return candidate.resolve()
    return None


translated_resolved = {p.resolve() for p in translated_files}
unscoped_mounts: list[str] = []
routes_seen = 0
for path in (WEB / "app").rglob("*.tsx"):
    if any(scope in path.parents or scope == path.parent for scope in scope_dirs):
        continue
    routes_seen += 1
    src = strip_comments(path.read_text(encoding="utf-8", errors="ignore"))
    if PAGE_SCOPE in src:
        continue  # the page provides its own provider — see PAGE_SCOPE above
    if re.search(r"from\s+[\"']next-intl", src):
        unscoped_mounts.append(f"{path.relative_to(WEB)} imports next-intl")
    for spec in re.findall(r"from\s+[\"']([^\"']+)[\"']", src):
        target = resolve_import(spec, path)
        if target in translated_resolved:
            unscoped_mounts.append(f"{path.relative_to(WEB)} → {target.relative_to(WEB.resolve())}")
check("the scan saw unscoped routes", routes_seen > 0)

# The marketing scope, asserted positively — a `continue` above is only honest
# if the thing it skips really is a provider that keeps the page static.
_mkt = strip_comments(read("components/marketing/MarketingIntlScope.tsx"))
check("the marketing scope takes its locale as an argument, never from a cookie",
      "locale: Locale" in _mkt and "resolveLocale" not in _mkt and "getLocale" not in _mkt,
      "a request read here would drop every marketing route from static to dynamic")
check("the marketing scope pins `now` and `timeZone`",
      "now=" in _mkt and "timeZone=" in _mkt,
      "left to the request config, the provider opts the route into dynamic rendering")
for _rel in ("app/page.tsx", "app/ko/page.tsx"):
    check(f"{_rel} provides the marketing scope",
          PAGE_SCOPE in strip_comments(read(_rel)))
# The shared chrome renders on marketing pages that stay English by ruling, so
# it is OUTSIDE every scope there. A hook in it throws at render (D8's shape).
# ⭐ A rostered path with no route is a 404 reachable from the Korean page's own
# nav — driven and confirmed once, in one click from header, footer and hero.
# The roster is what every link passes through, so it must never run ahead of
# the routes it promises.
_loc_src = read("lib/marketing/locale.ts")
_roster = re.findall(r'"(/[^"]*)"', _loc_src.split("TRANSLATED_PATHS = [")[1].split("]")[0])
check("the roster names something", bool(_roster))
_missing = [
    p for p in _roster
    if not (WEB / "app" / "ko" / (p.strip("/") or "") / "page.tsx").exists()
]
check("every rostered path HAS its /ko route (a roster ahead of the routes is a 404)",
      not _missing, f"rostered with no app/ko route: {_missing}")

# ⭐ The toggle must RENDER, not merely exist. It was first gated on a `path`
# prop that only the two landing pages passed, so the control was invisible on
# the other 11 marketing pages — a visitor on /pricing had no way to reach
# Korean at all. A component nothing renders is the same as a component that
# does not exist (the "wiring is not a door" shape).
_hdr = strip_comments(read("components/landing/LandingHeader.tsx"))
check("the language toggle is unconditional in the header",
      "MarketingLanguageToggle" in _hdr and "{path && (" not in _hdr,
      "gated on a prop most pages do not pass, so it renders nowhere")
check("the header defaults its path, so every page can offer the language",
      'path = "/"' in _hdr)
# The marketing toggle shows "the other language", which is only a coherent
# control while there are exactly TWO. A third locale must turn it into a
# menu; this arm makes that day name the file instead of shipping a toggle
# that silently hides a language.
check("the marketing toggle's two-language assumption still holds",
      len(LOCALES) == 2,
      f"{len(LOCALES)} locales — MarketingLanguageToggle must become a menu")

for _rel in ("components/landing/LandingHeader.tsx", "components/landing/LandingFooter.tsx"):
    check(f"{_rel} words itself by PROPS, not a hook",
          "next-intl" not in strip_comments(read(_rel)),
          "it also renders on untranslated marketing pages, where a hook throws")
check("no route outside a scope mounts a translated component", not unscoped_mounts,
      f"would throw at render: {unscoped_mounts[:3]}")

# ── D2 — one chain, and a guess is never written down ─────────────────────────
print("D2 — resolution")
resolve_src = strip_comments(read("i18n/resolve.ts"))
body = resolve_src[resolve_src.find("export async function resolveLocale"):]
order = [body.find("user_metadata"), body.find("cookieStore.get("), body.find("negotiateLocale(")]
check("the chain reads account, then cookie, then Accept-Language",
      all(i >= 0 for i in order) and order == sorted(order), f"offsets={order}")
writers = []
for top in ("app", "components", "lib", "i18n"):
    for path in (WEB / top).rglob("*.ts*"):
        if "node_modules" in path.parts:
            continue
        src = strip_comments(path.read_text(encoding="utf-8", errors="ignore"))
        if re.search(r"document\.cookie\s*=", src) and "LOCALE_COOKIE" in src:
            writers.append(str(path.relative_to(WEB)))
check("exactly one module writes the locale cookie", writers == ["components/i18n/locale-cookie.ts"], f"writers={writers}")
for rel in ("middleware.ts", "lib/supabase/middleware.ts"):
    check(f"{rel} never records a negotiated locale",
          not re.search(r"NEXT_LOCALE|LOCALE_COOKIE|negotiateLocale", strip_comments(read(rel))))

# ── D5 — what an agent writes is not the interface ────────────────────────────
print("D5 — the lane frame")
for rel in ("services/lane_runner.py", "services/standing_work.py", "services/derive_turn.py"):
    src = (API / rel).read_text(encoding="utf-8")
    check(f"{rel} reads no member locale",
          not re.search(r"user_metadata.{0,40}locale|accept[-_]language|NEXT_LOCALE", src, re.I))

# ── The deploy resolves from the npm lock ─────────────────────────────────────
print("Deploy parity")
pkg = json.loads(read("package.json"))
lock = json.loads(read("package-lock.json"))
declared = pkg.get("dependencies", {}).get("next-intl")
check("next-intl is declared", bool(declared))
check("next-intl is in package-lock.json — the lockfile the deploy installs from",
      "node_modules/next-intl" in lock.get("packages", {}))
check("no pnpm lockfile rides along (it would switch the deploy's package manager)",
      not (WEB / "pnpm-lock.yaml").exists())

# ── D4 — coverage only ratchets down ──────────────────────────────────────────
print("D4 — coverage")
# Lines of literal, member-facing copy still in components a scope renders. A
# METER, not a proof: it counts what it can see (JSX text + copy-bearing props).
# A pass lowers the ceiling in the commit that lowers the count; nothing raises it.
# 2026-09-21 — the full-coverage pass. 1005 → 972 → 898 → 875 → 262.
#
# ⚠️ WHAT THIS NUMBER IS NOW. 226 of these 262 lines are FALSE POSITIVES inside
# files that are fully translated: the meter marks JSX-text continuation lines,
# and Prettier wraps a long `t('…', { … })` call across several, so it counts
# JS identifiers and date-format options as if they were prose. Reflowing real
# code onto one line to satisfy a meter would be the tail wagging the dog.
#
# The other 36 are the SIX files that stay English by operator ruling (see
# SCOPELESS_BY_RULING above, plus `/mcp/authorize` and `/auth/callback`, whose
# entry routes were left unscoped deliberately).
#
# So the honest reading is: coverage is DONE, and this ceiling now guards
# against NEW literal copy rather than measuring remaining work. A future pass
# that adds a surface should still see it fall.
LITERAL_COPY_CEILING = 258  # 2026-09-21 — ratcheted with the Supervisor's duplicate start list (ADR-658 am.4)
COPY_PROP = re.compile(r"\b(placeholder|title|aria-label|label|alt|subtitle|description)=\"[^\"]*[A-Za-z]{2,}[^\"]*\"")
INLINE_TEXT = re.compile(r">([^<>{}]*[A-Za-z]{2,}[^<>{}]*)</")
METERED = [WEB / "app" / "(authenticated)", WEB / "app" / "auth", WEB / "app" / "mcp", WEB / "components"]
NOT_MEMBER_FACING = {"landing", "marketing", "admin", "ui"}

# ⚠️ STAYS ENGLISH BY RULING (operator, 2026-09-21). These components are mounted
# by routes OUTSIDE every `IntlScope` — `/invite/{token}`, `/s/{token}`,
# `/mcp/authorize`, `/auth/callback`, `/blog` — and the operator ruled those four
# entry routes stay English rather than pay the prerender cost of a scope each
# (D3's tradeoff, declined here). `useTranslations` THROWS outside a scope, so
# translating any of them ships a runtime crash on a signed-out entry path that
# tsc, the build and every other arm pass cleanly.
#
# Their lines are a PERMANENT FLOOR under the ceiling: a pass must not chase them.
# If a future ruling scopes those routes, delete this set in the same commit.
SCOPELESS_BY_RULING = {
    "components/authoring/NewArtifactModal.tsx",
    "components/workspace/WorkspacePicker.tsx",
    "components/shared/Working.tsx",
    "components/blog/BlogPostList.tsx",
}


def literal_copy_lines(path: Path) -> int:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    continuation = _jsx_text_line_numbers(raw)
    count = 0
    for lineno, line in enumerate(raw.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith(("//", "*", "/*", "import ")):
            continue
        if lineno in continuation and re.search(r"[A-Za-z]{2,}", re.sub(r"\{[^{}]*\}", "", stripped)):
            count += 1
        elif INLINE_TEXT.search(line) or COPY_PROP.search(line):
            count += 1
    return count


measured = 0
files_with_copy = 0
for top in METERED:
    for path in top.rglob("*.tsx"):
        if NOT_MEMBER_FACING & set(path.relative_to(WEB).parts):
            continue
        n = literal_copy_lines(path)
        measured += n
        files_with_copy += 1 if n else 0
print(f"    literal copy: {measured} lines across {files_with_copy} files (ceiling {LITERAL_COPY_CEILING})")
check("the meter reads something", measured > 0, "zero — the meter is blind, not the app translated")
scopeless_translated = [
    rel for rel in sorted(SCOPELESS_BY_RULING)
    if re.search(r"from\s+[\"']next-intl", strip_comments(read(rel)))
]
check("a component mounted outside every scope imports no translation hook — it would throw at render",
      not scopeless_translated, f"{scopeless_translated}")
check("literal member-facing copy is at or under its ceiling",
      measured <= LITERAL_COPY_CEILING, f"{measured} > {LITERAL_COPY_CEILING}")
check("the ceiling is tight — lower it in the commit that lowers the count",
      LITERAL_COPY_CEILING - measured <= 25, f"slack {LITERAL_COPY_CEILING - measured}")

print()
print(f"  {PASS} passed, {FAIL} failed")
print()
print("✓ all ADR-660 checks passed" if not FAIL else "✗ ADR-660 gate RED")
