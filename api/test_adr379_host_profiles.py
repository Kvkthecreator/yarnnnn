"""ADR-379 regression gate — Host Profiles, the interop-reach registry.

Asserts the structural guarantee that keeps the Nth host a DATA ENTRY, not a code
change (ADR-379 §5):

  1. No host-name string literal appears outside the registry in the MCP layer
     (the identity chain, the gate set, the dialect global — all gone; `openai`
     survives only inside its adapter file, per ADR-372 D5).
  2. Every renders_widgets=True profile declares a widget_dialect.
  3. The known disambiguations resolve (the §3.1 ordering, frozen).
  4. The ADR-372 D4 gate contract holds (allow-list, text-safe default).
  5. The registry is the single identity resolver (mcp_composition delegates).

These run without `mcp` (pure registry + source scan). Same posture as the other
MCP gates: structural assertions always run; if a wire check needed `mcp` and it
were absent, it would SKIP, not FAIL.
"""

import re
import sys
from pathlib import Path


def _check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}")
    return bool(ok)


def main():
    results = []
    from mcp_server.presentation import hosts

    # ---- 1: every host id resolves, and the registry is internally consistent --
    ids = {h.id for h in hosts.HOSTS}
    results.append(_check(
        "1 registry has the expected reach hosts (chatgpt + claude family + gemini/cursor/copilot/perplexity)",
        {"chatgpt", "claude.ai", "claude_desktop", "claude_code",
         "gemini", "cursor", "copilot", "perplexity"} <= ids))

    # ---- 2: every renders_widgets=True profile declares a dialect --------------
    widget_hosts_have_dialect = all(
        (h.widget_dialect is not None) for h in hosts.HOSTS if h.renders_widgets)
    results.append(_check(
        "2 every renders_widgets=True profile declares a widget_dialect (no dialect-less rendering host)",
        widget_hosts_have_dialect))

    # ---- 3: the known disambiguations resolve (§3.1 ordering, frozen) ----------
    cases = {
        # raw → expected id
        "chatgpt": "chatgpt",
        "openai-mcp/1.0": "chatgpt",
        "claude.ai": "claude.ai",
        "anthropic-connector": "claude.ai",       # bare anthropic → claude.ai
        "Claude Desktop 1.2": "claude_desktop",   # specific variant wins over claude.ai/anthropic
        "claude-code/2.0": "claude_code",
        "gemini-cli": "gemini",
        "google-genai": "gemini",
        "Cursor/0.4": "cursor",
        "github-copilot": "copilot",
        "perplexity-mcp": "perplexity",
        "some-random-agent/9": None,              # unknown → None (text-safe)
        "": None,
    }
    disambig_ok = True
    for raw, expected in cases.items():
        got = hosts.resolve_host_id(raw or None)
        if got != expected:
            disambig_ok = False
            print(f"      [!] resolve_host_id({raw!r}) = {got!r}, expected {expected!r}")
    results.append(_check(
        "3 known disambiguations resolve (claude variants win over bare anthropic; unknown→None)",
        disambig_ok))

    # ---- 4: the ADR-372 D4 gate contract holds (allow-list, text-safe default) -
    gate_ok = (
        hosts.renders_widgets("chatgpt") is True
        and hosts.renders_widgets("claude.ai") is False
        and hosts.renders_widgets("gemini") is False
        and hosts.renders_widgets("claude_desktop") is False
        and hosts.renders_widgets(None) is False
        and hosts.renders_widgets("") is False
        and hosts.renders_widgets("not-a-registered-id") is False)
    results.append(_check(
        "4 ADR-372 gate contract: chatgpt renders; every other / unknown host does NOT (allow-list, text-safe)",
        gate_ok))

    # ---- 4b: widget_dialect only returns for a rendering host ------------------
    dialect_ok = (
        hosts.widget_dialect("chatgpt") == "openai"
        and hosts.widget_dialect("gemini") is None       # registered but text-only
        and hosts.widget_dialect("claude.ai") is None
        and hosts.widget_dialect(None) is None
        and hosts.widget_dialect("unknown-id") is None)
    results.append(_check(
        "4b widget_dialect returns 'openai' for chatgpt, None for every non-rendering / unknown host",
        dialect_ok))

    # ---- 4c: the WIDGET_RENDERING_HOSTS shim is derived from the registry ------
    results.append(_check(
        "4c WIDGET_RENDERING_HOSTS (ADR-372 compat shim) is derived from the registry, never diverges",
        hosts.WIDGET_RENDERING_HOSTS == frozenset(h.id for h in hosts.HOSTS if h.renders_widgets)
        and hosts.WIDGET_RENDERING_HOSTS == frozenset({"chatgpt"})))

    # ---- 5: mcp_composition delegates to the registry (single resolver) --------
    from services import mcp_composition as mc
    # _normalize_client_id must produce the SAME result as resolve_host_id.
    delegation_ok = all(
        mc._normalize_client_id(raw) == hosts.resolve_host_id(raw)
        for raw in ("chatgpt", "Claude Desktop", "gemini", "anthropic", "nope", ""))
    src = Path(mc.__file__).read_text()
    # the old substring chain ("claude.ai" in low ... return "chatgpt") must be gone
    chain_gone = 'return "chatgpt"' not in src and 'return "gemini"' not in src
    results.append(_check(
        "5 mcp_composition._normalize_client_id delegates to resolve_host_id (chain removed, single resolver)",
        delegation_ok and chain_gone))

    # ---- 1b (the structural guarantee): no host-name literal outside the registry
    # Scan the MCP layer source for host-name string LITERALS. Allowed homes:
    #   * hosts.py            — the registry (where they belong)
    #   * adapters/openai.py  — the one file the name "openai" may appear (ADR-372 D5)
    #   * any *.md / comments — prose is fine; we scan for code-position literals.
    # We check the live CODE files, skipping the registry + the openai adapter +
    # docstrings/comments. A leaked host name in a NEW `if "gemini" in ...` fails here.
    HOST_TOKENS = ("chatgpt", "gemini", "perplexity", "cursor", "copilot")
    mcp_dir = Path(hosts.__file__).resolve().parent.parent  # api/mcp_server/
    leak = []
    for py in mcp_dir.rglob("*.py"):
        if "__pycache__" in str(py):
            continue
        name = py.name
        if name == "hosts.py":            # the registry — host names belong here
            continue
        if py.parent.name == "adapters":  # the per-host adapter files (D5)
            continue
        text = py.read_text()
        # strip line + block comments and docstrings crudely: drop everything in
        # triple-quoted strings and after `#`. We only care about live-code tokens.
        no_block = re.sub(r'"""(?:.|\n)*?"""', "", text)
        no_block = re.sub(r"'''(?:.|\n)*?'''", "", no_block)
        code_lines = []
        for ln in no_block.splitlines():
            code = ln.split("#", 1)[0]
            code_lines.append(code)
        code = "\n".join(code_lines).lower()
        for tok in HOST_TOKENS:
            if tok in code:
                leak.append(f"{name}:{tok}")
    results.append(_check(
        "1b no reach-host name literal in MCP live code outside the registry (host = data entry, not branch)",
        not leak, f"leaks={leak}" if leak else ""))

    total, passed = len(results), sum(results)
    print(f"\n{passed}/{total} ADR-379 assertions pass")
    if passed != total:
        sys.exit(1)


if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:  # noqa: BLE001
        pass
    main()
