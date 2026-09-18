"""
Voice & Tone guard — no kernel vocabulary in operator-facing copy.

Enforces the VOICE-AND-TONE.md spec (docs/design/VOICE-AND-TONE.md) at the one
place it can be enforced mechanically: the deterministic strings shown to a
real operator. The operator never read our ADRs or our YAML filenames; surfacing
"ADR-207" or "_recurrences.yaml" in rendered copy is an unambiguous leak.

This is the PROGRESSIVE-VALIDATE-AND-EXPAND mechanism: the guard defines the
standard, the ALLOWLIST is the known-baseline of pre-existing violations, and
each copy-pass PR shrinks the allowlist. The guard is green at baseline (every
current violation is allowlisted) and turns red the moment a NEW leak is added
or an allowlisted line drifts — so the surface ratchets toward clean and never
regresses. Same shape as test_adr209_no_filename_versioning.py.

SCOPE — only RENDERED operator-facing strings:
  - web/: JSX text + string-literal props (NOT // or /* */ comments, NOT imports).
  - backend copy sites: the files that SERVE prose the UI renders verbatim —
    the surface roster (kernel_surfaces: launcher titles + summaries), the
    reach sentences (reach_status.describe), the notification kinds
    (notifications), the account emails (account_email), narrative — string
    literals only. The agent-facing half of reach_status (frame_paragraph)
    is allowlisted by fragment: it is a prompt, not copy.
Code comments, ADR docs, prompt text, and test files are OUT of scope by design
(they are not shown to operators). `web/app/admin/` is out of scope too: the
admin console is the platform operator's own instrument and reads the record
in its own column names; the retired-vocabulary ratchet holds that surface.

Usage:
    cd api && python test_voice_no_kernel_nouns_in_copy.py
    (pytest-compatible: pytest api/test_voice_no_kernel_nouns_in_copy.py)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# =============================================================================
# Phase 1 banned patterns — UNAMBIGUOUS leaks (no legitimate operator-facing use)
# =============================================================================
# Phase 1 intentionally covers only the two zero-false-positive classes:
#   (1) ADR-NNN references, (2) raw machine `_*.yaml` filenames.
# Kernel-noun matching (recurrence / wake / substrate / capital action) is fuzzier
# (some appear in legitimate compound UI words) and lands in Phase 2 with its own
# allowlist once the spec's glossary replacements are wired. Start narrow + correct.

BANNED = [
    (re.compile(r"ADR-\d+"), "ADR reference in operator copy — delete it (the operator never read our ADRs)"),
    (re.compile(r"_[a-z_]+\.yaml"), "raw machine YAML filename in operator copy — operators act via chat/cockpit, never edit YAML"),
]

# =============================================================================
# Phase 2 banned patterns — KERNEL NOUNS (the glossary, VOICE-AND-TONE.md §4)
# =============================================================================
# Fuzzier than Phase 1 — these words have a plain operator replacement (§4) but
# can also appear in legitimate compound terms, so each is word-boundary-anchored
# and case-insensitive. Phase 2 ships with a BASELINE allowlist (the current
# leaks) so the guard stays green; each copy-pass PR deletes allowlist entries
# as it cleans a surface. The glossary replacement is in the reason string.

BANNED_PHASE2 = [
    (re.compile(r"\brecurrenc(e|es)\b", re.I), "kernel noun 'recurrence' → 'scheduled work' / 'a schedule' (glossary)"),
    (re.compile(r"\bwake(s|d)?\b", re.I), "kernel noun 'wake' → 'ran' / 'checked in' / 'responded' (glossary)"),
    (re.compile(r"\bsubstrate\b", re.I), "kernel noun 'substrate' → 'your files' / 'saved a note' (glossary)"),
    (re.compile(r"\bcapital action(s)?\b", re.I), "kernel noun 'capital action' → 'spend' / 'an order' (glossary)"),
    (re.compile(r"\boccupant\b", re.I), "kernel noun 'occupant' → 'your agent' (glossary)"),
    (re.compile(r"\bprimitive(s)?\b", re.I), "kernel noun 'primitive' → name the action plainly (glossary)"),
]

# =============================================================================
# Phase 3 banned patterns — THE SECOND GENERATION (2026-09-15)
# =============================================================================
# Phase 2 went to zero in June; by September the copy had regrown a NEW
# vocabulary the list never named: the launcher said "model-pinned helper
# conversations — isolated lanes", Files said "Raw substrate browser" (a Phase 2
# word, in a served file the guard never scanned), the members pane said
# "principal grants … author substrate", the bell said "awaiting a witness".
# Same ratchet: word-boundary, case-insensitive, an allowlist that only shrinks.
# The replacement is in the reason string (VOICE-AND-TONE.md §3).

BANNED_PHASE3 = [
    (re.compile(r"\bmodel-pinned\b", re.I), "'model-pinned' → say what the chat is for, not how it is bound"),
    (re.compile(r"\blanes?\b", re.I), "kernel noun 'lane' → 'chat' / 'conversation'"),
    (re.compile(r"\bcommons\b", re.I), "kernel noun 'commons' → 'workspace'"),
    (re.compile(r"\bprincipals?\b", re.I), "kernel noun 'principal' → 'member' / 'you' / the name"),
    (re.compile(r"\bartifacts?\b", re.I), "kernel noun 'artifact' → 'file' / 'deck' / 'post' / 'image'"),
    (re.compile(r"\battributed\b", re.I), "'attributed' → 'under your name' / 'signed'"),
    (re.compile(r"\bdeclarations?\b", re.I), "kernel noun 'declaration' → 'instructions' / 'standing work'"),
    (re.compile(r"\bwitness(es|ed)?\b", re.I), "kernel noun 'witness' → 'approval' / 'your OK'"),
    (re.compile(r"\bverdicts?\b", re.I), "kernel noun 'verdict' → 'decision'"),
    (re.compile(r"\brasteriz(e|ed|ing)\b", re.I), "'rasterize' → 'download as a PNG' / 'save a PNG copy'"),
    (re.compile(r"\bre-?scaffold(ed|ing)?\b", re.I), "'scaffold' → 'set up again' / say what is left"),
    (re.compile(r"\bno-op\b", re.I), "'no-op' → 'does nothing'"),
    (re.compile(r"\baperture\b", re.I), "kernel noun 'aperture' → 'what it can reach' / 'which tools'"),
]

# -----------------------------------------------------------------------------
# Phase 4 (2026-09-18) — the RETIRED SEAT, and the machine a member stands on.
#
# Receipt: the Chat pane's not-enabled empty state read "Chat colleagues aren't
# available on this deployment yet. Your conversation with Freddie is unaffected
# — summon it from the chat button." Both halves were wrong to a member: it
# named the machine ("this deployment", VOICE §3 row 21 bans it) and sent them
# to summon Freddie — a seat ADR-632 RETIRED. The To do queue shipped the same
# ghost: `verdictGiverLabel` returned the literal 'Freddie' for every non-human
# reviewer, so "Freddie approved" rendered on /reach and /notifications.
#
# Phases 1-3 could not catch either. They ban kernel NOUNS; these are a dead
# PERSON and an infrastructure word. A name outlives its deletion in copy
# precisely because no gate reads copy for names — the ADR deletes the seat, the
# sentence keeps the colleague. What CLAUDE.md's retirement list names is banned
# here the moment it is retired. The `freddie:` ATTRIBUTION PREFIX is untouched:
# it is a historical signature, resolved at display, and lives in comments and
# slug comparisons that this guard's rendered-context filter already rejects.
BANNED_PHASE4 = [
    (re.compile(r"\bfreddie\b", re.I), "retired seat 'Freddie' (ADR-632) → 'your agent' / name the live agent"),
    (re.compile(r"\bsteward\b", re.I), "retired seat 'steward' (ADR-632) → 'your agent'"),
    (re.compile(r"\bdeployment\b", re.I), "'deployment' → never shown; say 'here' / 'for your workspace' (VOICE §3)"),
]

# =============================================================================
# What counts as "rendered operator-facing string" in a web file
# =============================================================================
# A line is in-scope iff it is NOT a comment/import AND it contains a quoted
# string literal or JSX text. We approximate JSX-text + string-prop by requiring
# the banned token to sit inside quotes OR between > and < (JSX text), which is
# what the harvest showed the real leaks look like. This deliberately excludes
# `// ADR-207` and `import … // ADR-347` comment lines (the 650+ false positives).

_COMMENT_LINE = re.compile(r"^\s*(//|\*|/\*|\*/)")

# Shapes used by the returned-label rule below.
_TAILWINDISH = re.compile(
    r"\b(text-|bg-|border-|flex|px-|py-|rounded|gap-|w-|h-|grid|items-|justify-)"
)
# A single Capitalized word counts: a retired seat's NAME is one word, and
# 'Freddie' alone was the whole defect. Loosening it costs nothing — this rule
# only ADMITS a line for matching; a violation still needs a banned token, and
# no banned token is an identifier like 'FencedCode'.
_SENTENCE_LABEL = re.compile(r"^[A-Z][A-Za-z]+(\s+[A-Za-z][A-Za-z'’,.!—-]*)*[.!]?$")

# 2026-09-18 — MULTI-LINE JSX TEXT. The rules below are line-local: they match
# `>text<` on ONE line, or a copy-bearing prop. Prettier wraps any sentence
# longer than the print width, so a two-line <p> put its words on lines that
# contain NO angle bracket and NO quote — invisible to every phase. That is how
# "Your conversation with Freddie is unaffected" survived the 2026-09-15 sweep
# of the very pane it shipped in, and the falsification of Phase 4 came back
# green on all three arms until this was added.
#
# Deliberately narrow: state opens ONLY on a PROSE element whose tag closes at
# end-of-line, and shuts on the next line containing any `<`. A TS generic or an
# arrow type also ends a line with `>`, so an unscoped state machine runs away
# into plain code (measured: 5,985 lines, almost all identifiers). Scoped to
# these tags it is 892 lines, all genuine copy.
_PROSE_OPEN = re.compile(
    r"<(p|h[1-6]|span|li|dd|dt|label|strong|em|button|figcaption|blockquote)"
    r"(\s[^<>]*)?>\s*$"
)


def _jsx_text_line_numbers(text: str) -> set[int]:
    """1-indexed lines that are continuation text inside a prose element."""
    out: set[int] = set()
    open_state = False
    in_block_comment = False
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        # A `{/* … */}` block inside a prose element is COMMENT, and its inner
        # lines start with neither `<` nor `{` — without this they read as text
        # (measured: WorkspaceDeleteCard's ADR-578 note inside an <li>).
        if in_block_comment:
            if "*/" in stripped:
                in_block_comment = False
            continue
        if "{/*" in stripped or stripped.startswith("/*"):
            if "*/" not in stripped:
                in_block_comment = True
            continue
        if _COMMENT_LINE.match(line):
            continue
        if open_state:
            if stripped and not stripped.startswith("<") and not stripped.startswith("{"):
                out.add(lineno)
            if "<" in stripped:
                open_state = False
            continue
        if _PROSE_OPEN.search(stripped):
            open_state = True
    return out

# A line is CODE (not copy) if it's a path/constant assignment or a config call —
# these legitimately reference YAML paths the operator never sees. The token
# living in such a line is plumbing, not copy.
_CODE_NOT_COPY = re.compile(
    r"""
      ^\s*(export\s+)?const\s+[A-Z0-9_]+\s*=        # const PATH_GLOB = '...'
    | (PATH|GLOB|_PATH|ROUTE|SLUG|KEY)\b\s*[:=]      # ...PATH = / PATH:
    | \bwriteShape\s*\(                              # writeShape('autonomy', 'governance/_..')
    | \bimport\b                                     # import lines
    """,
    re.VERBOSE,
)

# Copy contexts: JSX text, or a known copy-bearing prop / field / throw.
_COPY_PROP = re.compile(
    r"""
      \b(tagline|title|description|label|placeholder|consequence|
         emptyBody|message|tooltip|heading|subtitle|cta|hint|body|text)\b
        \s*[:=]\s*["'`]                              # prop: "  /  prop="
    | \bthrow\s+new\s+Error\s*\(\s*["'`]             # throw new Error("...")
    | \btoast(\.\w+)?\s*\(\s*["'`]                   # toast("...") / toast.error("...")
    """,
    re.VERBOSE,
)


def _is_rendered_string_context(line: str, token: str) -> bool:
    """True iff `token` appears in OPERATOR-FACING copy on this line.

    Excludes comment lines + code-constant/path-assignment lines (false
    positives from the first run: `const AUTONOMY_YAML_PATH = ...`). Includes
    JSX text + known copy-bearing props (tagline/title/description/…) + thrown
    error / toast strings.
    """
    if _COMMENT_LINE.match(line):
        return False
    if _CODE_NOT_COPY.search(line):
        return False
    tok = re.escape(token)
    # Route-slug false positive: `navigateToSurface("recurrence", …)` / `href="/recurrence"`
    # pass a ROUTE NAME, not copy. The visible label on the same line (if any) is a
    # separate string the matcher still sees; only the slug token is excluded.
    if re.search(r'navigateToSurface\s*\(\s*["\']' + tok, line):
        return False
    if re.search(r'href=[{"\']?[^"\'`]*/' + tok + r'\b', line):
        return False
    # Property-access false positive: `{occupant.x}` / `watch.recurrence` render
    # the VALUE of a field whose NAME contains the token — the operator never sees
    # the word itself. Exclude when the token is preceded by `.` or is the object
    # root of a `{token.…}` / `{obj.token …}` member expression inside JSX braces.
    if re.search(r"\." + tok + r"\b", line):
        # the token is a property name (e.g. `.recurrence`, `.occupant`) — data, not copy
        if not re.search(r"[\"'`][^\"'`]*" + tok, line):  # …unless it ALSO appears inside a quote
            return False
    # JSX text: ...>some text TOKEN text<...  (but a bare {expr} is not literal text)
    m = re.search(r">[^<]*" + tok + r"[^<]*<", line)
    if m:
        # if the token sits inside a {…} JSX expression, it's interpolated data
        seg = m.group(0)
        if re.search(r"\{[^}]*" + tok + r"[^}]*\}", seg):
            pass  # interpolated — fall through to the prop check, don't accept as JSX text
        else:
            return True
    # copy-bearing prop / throw / toast carrying a string on this line
    if _COPY_PROP.search(line):
        return True
    # 2026-09-18 — a RETURNED LABEL. A helper that maps an id to the words on
    # screen (`verdictGiverLabel`, `runStatusLine`, PROBLEM_COPY lookups) puts
    # member-facing copy in a `return`, which is neither JSX text nor a
    # copy-bearing prop. That is how the To do queue returned the literal
    # 'Freddie' for every non-human reviewer while this guard stayed green.
    # Kept precise: a Sentence-shaped literal (leading capital, 2+ words) on a
    # return line, minus class-name shapes — 13 hits product-wide, all copy.
    if "return" in line:
        for m2 in re.finditer(r"['\"]([^'\"]{3,80})['\"]", line):
            value = m2.group(1)
            if _TAILWINDISH.search(value):
                continue
            if not _SENTENCE_LABEL.match(value.strip()):
                continue
            if re.search(tok, value, re.I):
                return True
    return False


# =============================================================================
# Files in scope
# =============================================================================

WEB_GLOBS = ["**/*.tsx", "**/*.ts"]
WEB_EXCLUDE_DIRS = {"node_modules", ".next", "dist", "build"}
# The admin console (`web/app/admin/`) is the platform operator's instrument,
# not a member surface: its column headers name the record's own tables.
WEB_EXCLUDE_PREFIXES = (("app", "admin"),)

# Backend files that SERVE operator-facing prose the UI renders verbatim.
BACKEND_COPY_FILES = [
    # freddie_chat_surfacing.py left this list with the steward (ADR-632).
    # daily_update_email.py left this list when ADR-593 D6 deleted the module.
    # daily_pnl_email.py deliberately NOT added in its place: its flagged
    # strings are docstrings + the machine-written sent-marker body, not
    # rendered operator copy — adding it would spend allowlist entries on
    # false positives. Its rendered email HTML lives in build_html, which a
    # future precision pass can scope in.
    REPO_ROOT / "api" / "services" / "notifications.py",
    REPO_ROOT / "api" / "services" / "narrative.py",
    # 2026-09-15 — the served roster: every launcher title + summary is a
    # string in this file, and "Raw substrate browser" shipped from it for
    # months while the guard sat green over web/ alone.
    REPO_ROOT / "api" / "services" / "kernel_surfaces.py",
    # The member face of reach (`describe`) — the Reads/Writes/Chat/Agents
    # rows on Reach and the connection page. The agent face in the same file
    # (`frame_paragraph`, `_row_line`) is a prompt and is allowlisted below.
    REPO_ROOT / "api" / "services" / "reach_status.py",
    # The account emails (ADR-650): subject, preheader, body.
    REPO_ROOT / "api" / "services" / "account_email.py",
]


def _web_files():
    web = REPO_ROOT / "web"
    for g in WEB_GLOBS:
        for p in web.glob(g):
            if any(part in WEB_EXCLUDE_DIRS for part in p.parts):
                continue
            rel = p.relative_to(web).parts
            if any(rel[: len(pre)] == pre for pre in WEB_EXCLUDE_PREFIXES):
                continue
            yield p


# =============================================================================
# ALLOWLIST — the known baseline of pre-existing violations (the progress meter).
# Each entry: "relative/path::substring-of-the-violating-line". A violation is
# allowed iff its line contains the substring. SHRINK this list as copy passes
# land — a removed entry that is still violated turns the guard red.
#
# Phase 1 baseline (2026-06-24) — populated empirically below by the first run.
# =============================================================================

# Phase 1 shipped with an EMPTY allowlist (all four leaks were fixed at intro).
# 2026-09-15: the served roster joined the scan; its one Phase-1 hit is a
# substrate path in a `substrate_paths` list — data the roster carries, never
# a rendered string.
ALLOWLIST: list[str] = [
    "api/services/kernel_surfaces.py::\"/workspace/_program.yaml\",",

    # --- 2026-09-18 baseline: exposed by the MULTI-LINE JSX TEXT fix ---------
    # These shipped before the guard could see wrapped prose (see
    # _jsx_text_line_numbers). They are PRE-EXISTING copy, not new: the ratchet
    # convention of §5 is that a detector improvement lands with its baseline
    # allowlisted and each later pass deletes entries. Highest-value first when
    # swept: the marketing pages (/invest is the bulk), then Studio's "artifact"
    # → the medium, then the three dormant-pane strings.
    "web/components/authoring/StudioDesignTab.tsx::? // ADR-546 D3 — the span NAMES itself. A h",
    "web/components/authoring/StudioDesignTab.tsx::: // ADR-546 D5 — the registry's word or not",
    "web/components/authoring/StudioShareExport.tsx::: 'A deck prints one slide per page. Markdow",
]

# Phase 2 baseline — the kernel-noun leaks present when Phase 2 was introduced.
# Each entry "relative/path::line-substring". SHRINK as copy passes land.
ALLOWLIST_PHASE2: list[str] = [
    # EMPTY (2026-06-24). The full Phase-2 sweep is complete — every operator
    # surface AND the marketing pages (/about, /invest) have been plain-language'd
    # to one voice (operator decision: same standard everywhere). The guard now
    # enforces a zero-baseline: ANY kernel-noun leak in operator-or-marketing copy
    # turns CI red. Both phases ship with an empty allowlist.

    # --- 2026-09-18 baseline: exposed by the MULTI-LINE JSX TEXT fix ---------
    # These shipped before the guard could see wrapped prose (see
    # _jsx_text_line_numbers). They are PRE-EXISTING copy, not new: the ratchet
    # convention of §5 is that a detector improvement lands with its baseline
    # allowlisted and each later pass deletes entries. Highest-value first when
    # swept: the marketing pages (/invest is the bulk), then Studio's "artifact"
    # → the medium, then the three dormant-pane strings.
    "web/app/invest/page.tsx::walled; the agent category is exploding but ",
    "web/app/invest/page.tsx::delegation dial, and the attributed substrat",
    "web/app/invest/page.tsx::Memory startups have the opposite problem: s",
    "web/app/invest/page.tsx::Authored substrate with attribution enforced",
    "web/app/invest/page.tsx::calibration flow back into the substrate. Li",
    "web/app/invest/page.tsx::Supabase), platform integrations, the author",
    "web/components/queue/QueueBody.tsx::Decided by <span className=\"font-medium\">{oc",
    "web/components/workspace-concepts/SourcesCard.tsx::every wake — it shapes what your agent notic",
]


# Phase 3 baseline (2026-09-15). The introducing pass swept the launcher, the
# Desktop, the bell, Chat, Reach, Notifications, Standing work, the queue, the
# members pane, the connection pages, the account emails and the served kinds.
# What remains is listed here so the guard ships green; each later pass deletes
# entries as it cleans a surface. A deleted entry that is still violated turns
# red — the surface only ratchets toward clean.
ALLOWLIST_PHASE3: list[str] = [
    # reach_status.py — the AGENT face (the lane frame's reach section), a
    # prompt composed by lane_runner, never rendered to a member (ADR-644).
    "api/services/reach_status.py::by PROPOSAL",
    "api/services/reach_status.py::the files into the commons",
    "api/services/reach_status.py::where you read them normally",
    "api/services/reach_status.py::save it to the commons with WriteFile",
    # The developer-facing OpenAPI description (a spec, read by integrators).
    "web/lib/openapi.ts::description: \"The attributed revision",
    # The account_email module docstring quotes ADR-593 — prose about the code.
    "api/services/account_email.py::no principal exists yet to hold a pref",
    # OWED — the marketing pages. The June ruling was "same standard
    # everywhere"; these four regrew. A marketing pass deletes these lines.
    "web/app/how-it-works/page.tsx::Studio is where artifacts take s",
    "web/app/invest/page.tsx::The loop closes against groun",
    "web/app/developers/page.tsx::Build on <span className=",
    "web/components/landing/AppShowcase.tsx::Every app comes with its own col",

    # --- 2026-09-18 baseline: exposed by the MULTI-LINE JSX TEXT fix ---------
    # These shipped before the guard could see wrapped prose (see
    # _jsx_text_line_numbers). They are PRE-EXISTING copy, not new: the ratchet
    # convention of §5 is that a detector improvement lands with its baseline
    # allowlisted and each later pass deletes entries. Highest-value first when
    # swept: the marketing pages (/invest is the bulk), then Studio's "artifact"
    # → the medium, then the three dormant-pane strings.
    "web/app/page.tsx::ever sees itself. A shared workspace where e",
    "web/app/s/[token]/page.tsx::A shared, attributed workspace — every chang",
    "web/app/privacy-architecture/page.tsx::what kind of principal is asking. Connected ",
    "web/app/invest/page.tsx::agent reads and writes, and every change is ",
    "web/app/invest/page.tsx::cross-principal, version-controlled memory —",
    "web/app/invest/page.tsx::to every room. Accountable judgment over tha",
    "web/app/invest/page.tsx::The composition is unoccupied: the memory ca",
    "web/app/invest/page.tsx::delegation dial, and the attributed substrat",
    "web/app/invest/page.tsx::read; actions with no attributed trail; impr",
    "web/app/invest/page.tsx::stays episodic — every artifact generated fr",
    "web/app/invest/page.tsx::An owned workspace where every change is att",
    "web/app/invest/page.tsx::The owned, attributed workspace is the syste",
    "web/app/developers/page.tsx::revision chain you can walk. A connection is",
    "web/app/developers/page.tsx::and every write lands attributed. Documented",
    "web/components/settings/ManageConnectionSubsurface.tsx::Snapshots land as attributed observation fil",
    "web/components/subscription/ByokSection.tsx::Run your team&rsquo;s chat lanes on your org",
    "web/components/authoring/StudioDesignTab.tsx::and every artifact can wear it.",
    "web/components/authoring/StudioSurface.tsx::Couldn’t load {relPath(artifactPath)}. The a",
    "web/components/authoring/StudioSurface.tsx::: `Worn by ${wornBy[s.manifest_path]} ${worn",
    "web/components/authoring/StudioSurface.tsx::No artifacts wear this yet. Apply it from an",
    "web/components/authoring/NewDesignSystemModal.tsx::A design system is the look your artifacts w",
    "web/components/notifications/ActivityLedger.tsx::every attributed act across the workspace (f",
    "web/components/workspace-concepts/WorkspaceCreatePane.tsx::A separate commons with its own files, membe",
    "web/components/workspace-concepts/SourcesCard.tsx::No sources declared — this watch is a delibe",
]

# Phase 4 ships at ZERO. The two sites its receipt names are fixed in the same
# commit, so there is no baseline to allowlist — an entry added here is a
# retired name that reached a member's screen, and needs the same argument as
# raising any other ceiling.
ALLOWLIST_PHASE4: list[str] = [
    # narrative.py — NOT copy. `freddie` here is the session_messages.role
    # slug (migration 167's CHECK constraint) and the docstring describing the
    # ADR-209 authored_by taxonomy. CLAUDE.md keeps `freddie:` alive precisely
    # as a display-resolved ATTRIBUTION PREFIX on historical revisions: the
    # stored signature on a 2026-06 row cannot be rewritten, and the FE maps it
    # to a label. A data value, not a sentence shown to a member.
    'api/services/narrative.py::"user", "assistant", "system", "freddie"',
    'api/services/narrative.py::{"user", "assistant", "system", "freddie"',
    'api/services/narrative.py::"ChatGPT (via MCP)" / "Claude" / "Freddie" / "You" distinctly',
    # The two HISTORICAL-ATTRIBUTION labelers. CLAUDE.md keeps `freddie:` alive
    # as "a display-resolved attribution prefix on historical revisions": both
    # of these are keyed on that PREFIX, so they name who actually signed a
    # 2026-06 revision. Relabelling them would misattribute real history, which
    # is the opposite of what the substrate is for. This is the line: a label
    # for a PAST signature stays; a label for a LIVE actor does not (the queue's
    # `verdictGiverLabel` mapped a live `ai:` identity and was fixed, and
    # decisions.ts::identityLabel did the same with no callers and was deleted).
    "web/components/workspace-concepts/RevisionFootnote.tsx::if (authoredBy.startsWith('freddie:')) return 'Freddie';",
    "web/lib/workspace/attribution.ts::      return 'Freddie';",
]


def _allowlisted(rel_path: str, line: str, allow: list[str]) -> bool:
    for entry in allow:
        if "::" not in entry:
            continue
        ap, frag = entry.split("::", 1)
        if rel_path.endswith(ap) and frag in line:
            return True
    return False


def find_violations(include_phase2: bool = True) -> list[tuple[str, int, str, str]]:
    """Returns (rel_path, lineno, line, reason) for every non-allowlisted hit."""
    violations: list[tuple[str, int, str, str]] = []
    pattern_sets = [(BANNED, ALLOWLIST)]
    if include_phase2:
        pattern_sets.append((BANNED_PHASE2, ALLOWLIST_PHASE2))
        pattern_sets.append((BANNED_PHASE3, ALLOWLIST_PHASE3))
        pattern_sets.append((BANNED_PHASE4, ALLOWLIST_PHASE4))
    targets = list(_web_files()) + [f for f in BACKEND_COPY_FILES if f.exists()]
    for path in targets:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        rel = str(path.relative_to(REPO_ROOT))
        is_py = path.suffix == ".py"
        jsx_text = set() if is_py else _jsx_text_line_numbers(text)
        for lineno, line in enumerate(text.splitlines(), 1):
            # python comment-line skip
            if is_py and line.lstrip().startswith("#"):
                continue
            for patterns, allow in pattern_sets:
                for pat, reason in patterns:
                    m = pat.search(line)
                    if not m:
                        continue
                    token = m.group(0)
                    if is_py:
                        # for .py narration files, require the token inside a quote
                        # (measured from the MATCH, not the first substring hit —
                        # `"substrate_paths": …  # substrate` is a comment, not copy)
                        in_str = any(
                            q in line[:m.start()] and q in line[m.end():]
                            for q in ('"', "'")
                        )
                        if not in_str:
                            continue
                        # Exclude metadata dict KEYS — `meta["occupant"] = …` /
                        # `"occupant":` — these are internal data fields, not copy.
                        if re.search(r'\[\s*["\']' + re.escape(token) + r'["\']\s*\]', line):
                            continue
                        if re.search(r'["\']' + re.escape(token) + r'["\']\s*:', line):
                            continue
                    else:
                        if lineno not in jsx_text and not _is_rendered_string_context(line, token):
                            continue
                    if _allowlisted(rel, line, allow):
                        continue
                    violations.append((rel, lineno, line.strip(), reason))
    return violations


def test_no_kernel_nouns_in_operator_copy():
    violations = find_violations()
    if violations:
        msg = ["Operator-facing copy contains kernel vocabulary (VOICE-AND-TONE.md):"]
        for rel, lineno, line, reason in violations:
            msg.append(f"  {rel}:{lineno} — {reason}")
            msg.append(f"      {line[:140]}")
        msg.append("")
        msg.append("Fix the copy (see docs/design/VOICE-AND-TONE.md §4 glossary), OR — if it is")
        msg.append("genuinely pre-existing and not yet swept — add it to ALLOWLIST in this file.")
        raise AssertionError("\n".join(msg))


if __name__ == "__main__":
    vs = find_violations()
    if not vs:
        print("✅ voice guard: 0 violations (clean or fully allowlisted)")
        sys.exit(0)
    print(f"⚠️  voice guard: {len(vs)} violations not yet allowlisted\n")
    # Emit them in ALLOWLIST-entry shape so seeding the baseline is copy-paste.
    print("# --- suggested ALLOWLIST seed (paste into ALLOWLIST, then sweep down) ---")
    for rel, lineno, line, reason in vs:
        # pick a stable fragment: the banned token + a little context
        frag = line[:60].replace('"', '\\"')
        print(f'    "{rel}::{frag[:40]}",  # {reason[:40]}')
    print(f"\n# total: {len(vs)}")
    sys.exit(1)
