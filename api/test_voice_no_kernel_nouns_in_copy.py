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

# =============================================================================
# What counts as "rendered operator-facing string" in a web file
# =============================================================================
# A line is in-scope iff it is NOT a comment/import AND it contains a quoted
# string literal or JSX text. We approximate JSX-text + string-prop by requiring
# the banned token to sit inside quotes OR between > and < (JSX text), which is
# what the harvest showed the real leaks look like. This deliberately excludes
# `// ADR-207` and `import … // ADR-347` comment lines (the 650+ false positives).

_COMMENT_LINE = re.compile(r"^\s*(//|\*|/\*|\*/)")

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
]

# Phase 2 baseline — the kernel-noun leaks present when Phase 2 was introduced.
# Each entry "relative/path::line-substring". SHRINK as copy passes land.
ALLOWLIST_PHASE2: list[str] = [
    # EMPTY (2026-06-24). The full Phase-2 sweep is complete — every operator
    # surface AND the marketing pages (/about, /invest) have been plain-language'd
    # to one voice (operator decision: same standard everywhere). The guard now
    # enforces a zero-baseline: ANY kernel-noun leak in operator-or-marketing copy
    # turns CI red. Both phases ship with an empty allowlist.
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
    targets = list(_web_files()) + [f for f in BACKEND_COPY_FILES if f.exists()]
    for path in targets:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        rel = str(path.relative_to(REPO_ROOT))
        is_py = path.suffix == ".py"
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
                        if not _is_rendered_string_context(line, token):
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
