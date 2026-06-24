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
  - backend narration/email sites: the handful of files that compose operator-
    facing text (reviewer_chat_surfacing, daily_update_email, notifications,
    narrative) — string literals only.
Code comments, ADR docs, prompt text, and test files are OUT of scope by design
(they are not shown to operators).

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
    # JSX text: ...>some text TOKEN text<...
    if re.search(r">[^<]*" + re.escape(token) + r"[^<]*<", line):
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

# Backend files that compose operator-facing narration/email text.
BACKEND_COPY_FILES = [
    REPO_ROOT / "api" / "services" / "reviewer_chat_surfacing.py",
    REPO_ROOT / "api" / "services" / "daily_update_email.py",
    REPO_ROOT / "api" / "services" / "notifications.py",
    REPO_ROOT / "api" / "services" / "narrative.py",
]


def _web_files():
    web = REPO_ROOT / "web"
    for g in WEB_GLOBS:
        for p in web.glob(g):
            if any(part in WEB_EXCLUDE_DIRS for part in p.parts):
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

ALLOWLIST: list[str] = [
    # populated after the first measurement run (see __main__)
]


def _allowlisted(rel_path: str, line: str) -> bool:
    for entry in ALLOWLIST:
        if "::" not in entry:
            continue
        ap, frag = entry.split("::", 1)
        if rel_path.endswith(ap) and frag in line:
            return True
    return False


def find_violations() -> list[tuple[str, int, str, str]]:
    """Returns (rel_path, lineno, line, reason) for every non-allowlisted hit."""
    violations: list[tuple[str, int, str, str]] = []
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
            for pat, reason in BANNED:
                m = pat.search(line)
                if not m:
                    continue
                token = m.group(0)
                if is_py:
                    # for .py narration files, require the token inside a quote
                    in_str = any(
                        q in line[:line.find(token)] and q in line[line.find(token):]
                        for q in ('"', "'")
                    )
                    if not in_str:
                        continue
                else:
                    if not _is_rendered_string_context(line, token):
                        continue
                if _allowlisted(rel, line):
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
