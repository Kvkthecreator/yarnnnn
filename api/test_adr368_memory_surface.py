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

    # 4 + 5. routing reaches operation/ only — never a locked root for the mcp caller
    mcp_locks = CALLER_WRITE_POLICY["mcp"]  # the roots the foreign caller may NOT write
    probes = [
        None, "", "Acme Corp", "competitors", "market", "Project Zephyr",
        "some random subject", "identity", "brand", "memory", "system",
        "governance", "persona", "constitution", "contract",
    ]
    all_operation = True
    no_locked = True
    for about in probes:
        path = m.resolve_remember_path(about)
        if not path.startswith("operation/"):
            all_operation = False
            print(f"      [!] about={about!r} -> {path} (NOT operation/)")
        if any(path.startswith(root) for root in mcp_locks):
            no_locked = False
            print(f"      [!] about={about!r} -> {path} (LOCKED root)")
    results.append(_check(
        "4 every resolve_remember_path lands under operation/ (incl. adversarial 'system'/'identity' hints)",
        all_operation))
    results.append(_check(
        "5 no resolve_remember_path lands in a root the mcp caller is locked from",
        no_locked, f"locked roots={mcp_locks}"))

    total, passed = len(results), sum(results)
    print(f"\n{passed}/{total} ADR-368 assertions pass")
    if passed != total:
        sys.exit(1)


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    main()
