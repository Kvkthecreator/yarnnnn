"""ADR-368 regression gate — the memory-first interop surface.

Structural + routing invariants for the remember / recall / trace surface.
Pure-Python where possible (no `mcp` package — that ships only on the MCP
Render service); the live round-trip is covered by probe_mcp_memory_surface.py.

Asserts:
  1. The topology-incoherent five-target enum is DELETED.
  2. The work_on_this drivers are DELETED.
  3. The memory-verb compositions EXIST.
  4. remember routing reaches operation/ ONLY — never a locked root.
  5. resolve_remember_path never returns a path the mcp caller is locked from.
"""

import sys


def _check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}")
    return bool(ok)


def main():
    results = []
    from services import mcp_composition as m
    from services.workspace_paths import CALLER_WRITE_POLICY

    # 1. the enum classifier is gone
    results.append(_check(
        "1 classify_memory_target DELETED (the five-target enum)",
        not hasattr(m, "classify_memory_target")))

    # 2. work_on_this drivers gone
    results.append(_check(
        "2 work_on_this drivers DELETED (compose_subject_context/compose_active_candidates)",
        not hasattr(m, "compose_subject_context") and not hasattr(m, "compose_active_candidates")))

    # 3. the memory-verb compositions exist
    results.append(_check(
        "3 memory-verb compositions EXIST (resolve_remember_path/compose_recall/compose_trace)",
        all(hasattr(m, n) for n in ("resolve_remember_path", "compose_recall", "compose_trace", "dispatch_remember_this"))))

    # 4 + 5. the dump lands in the memory INBOX (capture, not placement) — never
    # a deterministic domain route, never a locked root. Placement is the
    # Reviewer's job (ADR-368 D5).
    mcp_locks = CALLER_WRITE_POLICY["mcp"]  # the roots the foreign caller may NOT write
    probes = [
        None, "", "Acme Corp", "competitors", "market", "Project Zephyr",
        "some random subject", "identity", "brand", "memory", "system",
        "governance", "persona", "constitution", "contract",
    ]
    all_inbox = True
    no_locked = True
    for about in probes:
        path = m.resolve_remember_path(about)
        if not path.startswith("operation/memory/"):
            all_inbox = False
            print(f"      [!] about={about!r} -> {path} (NOT the memory inbox)")
        if any(path.startswith(root) for root in mcp_locks):
            no_locked = False
            print(f"      [!] about={about!r} -> {path} (LOCKED root)")
    results.append(_check(
        "4 every remember DUMP lands in operation/memory/ inbox (capture, not placement; incl. adversarial 'system'/'identity')",
        all_inbox))
    results.append(_check(
        "5 no dump path lands in a root the mcp caller is locked from",
        no_locked, f"locked roots={mcp_locks}"))

    # 6. the deterministic-domain fiction is gone (placement is judgment now)
    results.append(_check(
        "6 ADR-151 domain-routing fiction DELETED (_classify_domain / DOMAIN_KEYWORDS)",
        not hasattr(m, "_classify_domain") and not hasattr(m, "DOMAIN_KEYWORDS")))

    total, passed = len(results), sum(results)
    print(f"\n{passed}/{total} ADR-368 assertions pass")
    if passed != total:
        sys.exit(1)


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    main()
