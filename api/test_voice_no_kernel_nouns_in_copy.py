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

# Phase 1 ships with an EMPTY allowlist (all four leaks were fixed at intro).
ALLOWLIST: list[str] = []

# Phase 2 baseline — the kernel-noun leaks present when Phase 2 was introduced.
# Each entry "relative/path::line-substring". SHRINK as copy passes land.
ALLOWLIST_PHASE2: list[str] = [
    # Phase 2 baseline (2026-06-24). The feed surface + autonomy governance card +
    # system-status were cleaned in the introducing pass; these lower-exposure
    # surfaces remain. SHRINK this list as each surface gets its copy pass (spec
    # §5 order: governance cards done → nav/empty-states → settings/marketing).
    "web/app/about/page.tsx::body: \"Fix something once and everythin",
    "web/app/(authenticated)/recurrence/page.tsx::title=\"Recurrence not found\"",
    "web/app/(authenticated)/recurrence/page.tsx::title=\"Failed to load recurrence\"",
    "web/app/(authenticated)/settings/page.tsx::<div className=\"text-xs text-muted-fore",
    "web/app/(authenticated)/settings/page.tsx::<li>Per-recurrence <code>_run_log.md</co",
    "web/app/(authenticated)/settings/page.tsx::<strong>Preserved:</strong> all recurren",
    "web/app/(authenticated)/settings/page.tsx::<li>{dangerStats?.workspace_files} works",
    "web/app/(authenticated)/settings/page.tsx::<li>All recurrences, activity history, a",
    "web/app/(authenticated)/settings/page.tsx::<li>{dangerStats?.agents} agents and all",
    "web/app/(authenticated)/notifications/page.tsx::link={<MirrorLink label=\"Open run ledge",
    "web/app/(authenticated)/notifications/page.tsx::link={<MirrorLink label=\"Open full Recu",
    "web/app/invest/page.tsx::<p className=\"text-white/60 font-medium",
    "web/app/invest/page.tsx::{ title: \"Total attribution\", desc: \"",
    "web/components/settings/WorkspaceSection.tsx::<h2 className=\"text-lg font-semibold mb",
    "web/components/activity/ActivityLog.tsx::title=\"Manage this recurrence (declarat",
    "web/components/shell/system-status/AutonomyStatusItem.tsx::<p className=\"pt-0.5\">Above the ceilin",
    "web/components/workspace/WorkspaceNav.tsx::title=\"Recurrences\"",
    "web/components/workspace/WorkspaceNav.tsx::<div className=\"px-3 py-1.5 text-sm tex",
    "web/components/tp/InlineActionCard.tsx::title: 'Run this recurrence',",
    "web/components/tp/InlineActionCard.tsx::title: 'Adjust this recurrence',",
    "web/components/tp/InlineActionCard.tsx::{ label: 'Focus area', message: 'Change ",
    "web/components/tp/InlineActionCard.tsx::{ label: 'Success criteria', message: 'U",
    "web/components/tp/InlineActionCard.tsx::{ label: 'Schedule', message: 'Change th",
    "web/components/tp/InlineActionCard.tsx::{ label: 'Delivery', message: 'Change th",
    "web/components/tp/InlineActionCard.tsx::{ label: 'Latest trends', message: 'Rese",
    "web/components/tp/InlineActionCard.tsx::{ label: 'Competitor activity', message:",
    "web/components/tp/InlineActionCard.tsx::{ label: 'Industry news', message: 'Rese",
    "web/components/tp/ToolResultCard.tsx::<div className=\"text-sm\">{description ",
    "web/components/work/RecurrenceList.tsx::title=\"See execution history for this r",
    "web/components/queue/QueueBody.tsx::Verdicts rendered by <span className=\"f",
    "web/components/workspace-concepts/SourcesCard.tsx::<span className=\"text-[10px] text-muted",
    "web/lib/schedule.ts::description: 'Fires on event — operator ",
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
                        in_str = any(
                            q in line[:line.find(token)] and q in line[line.find(token):]
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
