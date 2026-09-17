"""Action-feedback layer gate — docs/design/ACTION-FEEDBACK.md.

Script-style (python3 test_action_feedback_layer.py from api/).

WHY THIS GATE WAS REWRITTEN (2026-09-17). The first version asserted a dozen
NAMED sites stayed migrated. Two of its anchors were deleted by later refactors
(AgentRunDisplay.tsx 2026-08-26 by 083d25d, ConnectedIntegrationsSection.tsx
2026-09-08 by ADR-645), so it crashed at `_read` and reported NOTHING for 22
days and 184 commits. And even green it could not have failed on the defect
that prompted the rewrite — a multi-select delete on Files that ran a bare
`for` loop of `api.documents.delete` with no pending toast — because that site
was not one of the dozen it knew about.

A gate hardcoding a set cannot fail on what it omits. So §2 DERIVES its census:
the mutating methods come from `web/lib/api/client.ts` (every `request(...)`
whose options carry method POST/PUT/PATCH/DELETE), and every call site of every
one of them must either ride `runAction` or be named in IN_SURFACE — the
canon's deliberately-excluded lane, each entry carrying its reason. Silence is
the failure mode: a NEW silent verb fails on arrival, with no edit to this file.

The lanes it holds:
  1. The toast corridor is TOP-RIGHT, always-mounted, motion-aware.
  2. DERIVED: every mutating api call rides runAction, or is a named exemption.
  3. The native dialog trio stays dead.
  4. Copy-flip micro-feedback rides the one duration token.
  5. The canon carries the ruling.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

API = Path(__file__).resolve().parent
WEB = API.parent / "web"
CLIENT = WEB / "lib/api/client.ts"

_passed = 0
_failed = 0


def _assert(cond: bool, msg: str) -> None:
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"  PASS  {msg}")
    else:
        _failed += 1
        print(f"  FAIL  {msg}")


def _read(rel: str) -> str:
    return (WEB / rel).read_text(encoding="utf-8")


def _strip_comments(src: str) -> str:
    """Drop // and /* */ comments so a check can never pass (or fail) on prose
    — the assert-the-composition-not-the-comment lesson. This gate's OWN prose
    names the very call shapes it bans, so stripping is load-bearing here."""
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    src = re.sub(r"(?m)^\s*//.*$", "", src)
    src = re.sub(r"(?m)\s//(?![:/]).*$", "", src)  # trailing //, spare URLs
    return src


# ---------------------------------------------------------------------------
# The exemption register — the canon's "in-surface banner" lane, NOT a
# rubber stamp. ACTION-FEEDBACK.md's lane table says a toast auto-dismisses,
# so unresolved state that must SURVIVE until acted on belongs in its surface
# with role="alert". Each entry is `("path", "method", "why")`. An entry that
# stops matching a real call site fails §2c — the register cannot rot into a
# blanket amnesty the way the old named-site list did.
# ---------------------------------------------------------------------------
IN_SURFACE: list[tuple[str, str, str]] = [
    # Continuous persistence, not a discrete verb — the canon excludes "a long
    # save with its own progress bar" explicitly.
    ("components/text/TextEditor.tsx", "workspace.editFile",
     "the debounced autosave — continuous, owns saving/saveError/savedAt + the 409 banner"),
    ("components/authoring/StudioSurface.tsx", "studio.writeArtifact",
     "the queued CAS autosave — continuous, owns its 409 re-apply path"),
    # Fire-and-forget cursor write-through; not operator-initiated.
    ("components/shell/AttentionCenter.tsx", "memberState.put",
     "the attention cursor write-through — a read side-effect, never a member's verb"),
    # Upload partial-failure is named in the canon's "deliberately NOT migrated" ledger.
    ("components/workspace/UploadButton.tsx", "documents.upload",
     "partial-batch upload notice — must survive until read (canon: upload partial failures)"),
    # OAuth outcomes are named in the canon's ledger too.
    ("app/mcp/authorize/page.tsx", "mcp.completeAuthorize",
     "the OAuth outcome banner — must survive the redirect, canon-excluded"),
    ("app/invite/[token]/page.tsx", "workspace.acceptInvite",
     "a full-page accept flow — the outcome IS the page, not a transient notice"),
    ("app/s/[token]/ShareClient.tsx", "workspace.acceptShare",
     "a full-page accept flow — the outcome IS the page, not a transient notice"),
    # The editor's own create-and-navigate flow: the new document is the receipt.
    ("components/text/NameDocumentModal.tsx", "workspace.editFile",
     "create-then-navigate — the opened document is the outcome"),
    ("components/workspace-concepts/WorkspaceCreatePane.tsx", "workspace.create",
     "create-then-navigate — the opened workspace is the outcome"),
    # LIBRARY MODULES. Not React, so they hold no hook and CANNOT report — the
    # calling component owns the feedback. These two are exempt because the
    # layer is unreachable from them, not because the act is quiet: each named
    # caller below rides runAction, and that is what the member sees.
    #   write.ts      ← content-shapes/{sources,expected-output}.ts
    #                   ← SourcesCard.tsx / the contract editor (both report)
    #   rasterExport  ← StudioSurface.tsx (reports)
    # If either grows a caller that does NOT report, the gate cannot catch it —
    # so a new caller of these two is reviewed by hand.
    ("lib/content-shapes/write.ts", "workspace.editFile",
     "a non-React library helper — the calling component owns the report"),
    ("components/workspace/viewers/rasterExport.ts", "images.exportPng",
     "a non-React library helper — the calling component owns the report"),
]


def _mutating_methods() -> dict[str, set[str]]:
    """DERIVE the mutating surface from the client. A method is mutating when
    its `request(...)` options carry a POST/PUT/PATCH/DELETE method. Returns
    {"namespace.method": {verbs}}.

    Parsed structurally (namespace at 2-space indent, method at 4) rather than
    by a hardcoded name list — that is the whole point of the rewrite."""
    lines = CLIENT.read_text(encoding="utf-8").split("\n")
    ns_re = re.compile(r"^  ([A-Za-z_][A-Za-z0-9_]*)\s*:\s*\{")
    decl_re = re.compile(r"^    ([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(?:async\s*)?[<(]")
    verb_re = re.compile(r'method:\s*"(POST|PUT|PATCH|DELETE)"')
    ns: str | None = None
    meth: str | None = None
    out: dict[str, set[str]] = {}
    for line in lines:
        m = ns_re.match(line)
        if m:
            ns, meth = m.group(1), None
            continue
        d = decl_re.match(line)
        if d and ns:
            meth = d.group(1)
        v = verb_re.search(line)
        if v and ns and meth:
            out.setdefault(f"{ns}.{meth}", set()).add(v.group(1))
    return out


def _product_files() -> list[Path]:
    files: list[Path] = []
    for sub in ("components", "app", "hooks", "lib", "contexts"):
        root = WEB / sub
        if not root.exists():
            continue
        for f in root.rglob("*.ts"):
            files.append(f)
        for f in root.rglob("*.tsx"):
            files.append(f)
    return [f for f in files if ".next" not in f.parts and "node_modules" not in f.parts]


_WRAPPER = re.compile(r"(runAction|reportAction)\(")
_WRAPPER_ARROW = re.compile(r"(runAction|reportAction)\(\s*(?:async\s*)?\(\s*\)\s*=>\s*$")


def _rides_run_action(text: str, idx: int) -> bool:
    """Is the call at `idx` inside a runAction(...) wrapper?

    TWO shapes, and the check must see both — the second one cost a false RED
    on the very fix this gate was written for:

      a) the one-liner  `runAction(() => api.x.y(...), {...})`
      b) the batch form `runAction(async () => { for (...) { await api.x.y() } })`

    For (b) a naive scan back to the nearest brace stops INSIDE the loop body
    and never sees the opener, so a correctly-wrapped batch reads as silent.
    So: check the call's own statement for (a), then walk OUTWARD through
    enclosing scopes — at each unmatched `{`, ask whether that scope was opened
    as a runAction callback. Brace-based only; a `;` inside a loop body is not
    a scope boundary.

    `reportAction` is TextEditor's local alias of the same hook value (the
    canon sanctions aliasing where a bare `runAction` would shadow)."""
    own_statement = text[max(0, idx - 400):idx].rsplit(";", 1)[-1]
    if _WRAPPER.search(own_statement):
        return True
    depth = 0
    i = idx - 1
    while i >= 0:
        c = text[i]
        if c == "}":
            depth += 1
        elif c == "{":
            if depth == 0:
                if _WRAPPER_ARROW.search(text[max(0, i - 200):i]):
                    return True
            else:
                depth -= 1
        i -= 1
    return False


def test_corridor() -> None:
    print("\n[1] the toast corridor — top-right, always-mounted, motion-aware")
    code = _strip_comments(_read("contexts/FeedbackContext.tsx"))
    _assert("top-[4.25rem] right-4" in code,
            "the stack renders top-right below the top bar (operator ruling 2026-08-22)")
    _assert("fixed bottom-4 right-4" not in code, "the bottom-right default is gone")
    m = re.search(r"function ToastViewport.*?createPortal", code, flags=re.DOTALL)
    _assert(bool(m) and "toasts.length === 0" not in (m.group(0) if m else ""),
            "the viewport mounts EMPTY (a live region must pre-exist its first message)")
    _assert("aria-live" in code, "the viewport is a live region")
    _assert("slide-in-from-top-2" in code and "motion-reduce:animate-none" in code,
            "entrance slides from the top and respects prefers-reduced-motion")
    _assert("COPY_FEEDBACK_MS = 2000" in code,
            "the copy-flip duration token is declared here (2000ms)")


def test_every_mutation_reports() -> None:
    """THE DERIVED CHECK. Not a list of known sites — a census of every call
    site of every mutating client method."""
    print("\n[2] every mutating api call reports (derived census)")
    methods = _mutating_methods()
    _assert(len(methods) >= 70,
            f"the mutating surface is derived from client.ts, not hardcoded ({len(methods)} methods)")

    exempt_pairs = {(p, m) for p, m, _ in IN_SURFACE}
    seen_exempt: set[tuple[str, str]] = set()
    silent: list[str] = []
    compliant = 0

    for f in _product_files():
        rel = f.relative_to(WEB).as_posix()
        if rel == "lib/api/client.ts":
            continue
        raw = f.read_text(encoding="utf-8", errors="ignore")
        text = _strip_comments(raw)
        for name in methods:
            for m in re.finditer(rf"api\.{re.escape(name)}\(", text):
                if (rel, name) in exempt_pairs:
                    seen_exempt.add((rel, name))
                    continue
                if _rides_run_action(text, m.start()):
                    compliant += 1
                else:
                    line = text[: m.start()].count("\n") + 1
                    silent.append(f"{rel}:{line} api.{name}")

    _assert(compliant >= 15,
            f"the compliant sites are found by the same census that finds the silent ones ({compliant})")
    _assert(not silent,
            "every mutating call rides runAction (or is a named IN_SURFACE exemption)\n"
            + "".join(f"\n          SILENT  {s}" for s in sorted(silent)))

    stale = sorted(exempt_pairs - seen_exempt)
    _assert(not stale,
            f"every IN_SURFACE exemption still matches a real call site — no rot ({stale})")


def test_native_trio_dead() -> None:
    print("\n[3] the native dialog trio stays dead")
    off_confirm: list[str] = []
    off_alert: list[str] = []
    off_prompt: list[str] = []
    for f in _product_files():
        if f.suffix != ".tsx":
            continue
        rel = f.relative_to(WEB).as_posix()
        src = _strip_comments(f.read_text(encoding="utf-8", errors="ignore"))
        if "window.confirm(" in src:
            off_confirm.append(rel)
        if "window.alert(" in src:
            off_alert.append(rel)
        if "window.prompt(" in src:
            off_prompt.append(rel)
    _assert(not off_confirm, f"no window.confirm in product surfaces ({off_confirm})")
    _assert(not off_alert, f"no window.alert in product surfaces ({off_alert})")
    _assert(off_prompt == ["components/authoring/FlowEditor.tsx"],
            f"window.prompt has exactly its ONE named survivor, owed an inline replacement ({off_prompt})")


def test_one_duration_token() -> None:
    """Copy-flip micro-feedback. DERIVED: any file importing the token must use
    it as a call argument and carry no stray literal — the old fixed list of
    six paths silently stopped covering a file the moment one was renamed."""
    print("\n[4] copy-flip micro-feedback rides the one token")
    users = []
    for f in _product_files():
        src = _strip_comments(f.read_text(encoding="utf-8", errors="ignore"))
        if "COPY_FEEDBACK_MS" in src and f.name != "FeedbackContext.tsx":
            users.append((f.relative_to(WEB).as_posix(), src))
    _assert(len(users) >= 5, f"the copy-flip sites are derived from the import ({len(users)} found)")
    for rel, src in users:
        uses_token = ", COPY_FEEDBACK_MS)" in src
        stray = re.search(r",\s*(1500|1600|2000|2500)\)", src)
        _assert(uses_token and not stray, f"{rel}: uses COPY_FEEDBACK_MS as the duration, no literal")


def test_canon_updated() -> None:
    print("\n[5] the canon carries the ruling")
    doc = (API.parent / "docs/design/ACTION-FEEDBACK.md").read_text(encoding="utf-8")
    _assert("TOP-RIGHT" in doc and "attention corridor" in doc,
            "placement ruling recorded (top-right, the attention corridor)")
    _assert("Self-act toast" in doc and "In-surface banner" in doc and "Micro-feedback" in doc,
            "the lane taxonomy is written down")
    _assert("ADR-593" in doc and "ADR-405 D4" in doc,
            "the split is tied to the notifications canon (self vs peer)")
    _assert("IN_SURFACE" in doc,
            "the canon names the exemption register, so the escape hatch is documented where the rule is")


if __name__ == "__main__":
    test_corridor()
    test_every_mutation_reports()
    test_native_trio_dead()
    test_one_duration_token()
    test_canon_updated()
    print("\n" + "=" * 60)
    print(f"Action-feedback gate: {_passed} passed, {_failed} failed")
    print("=" * 60)
    sys.exit(1 if _failed else 0)
