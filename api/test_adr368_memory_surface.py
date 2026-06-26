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

    # 4 + 5. the RAW observation lands in the inbound/ lane (ADR-376/DP32 — capture,
    # never the derived understanding) — never a deterministic domain route, never
    # a locked root. The seat DERIVES into operation/ separately (the placement
    # wake). Adversarial subjects must not escape the raw lane.
    mcp_locks = CALLER_WRITE_POLICY["mcp"]  # the roots the foreign caller may NOT write
    probes = [
        None, "", "Acme Corp", "competitors", "market", "Project Zephyr",
        "some random subject", "identity", "brand", "memory", "system",
        "governance", "persona", "constitution", "contract",
    ]
    all_inbound = True
    no_locked = True
    for about in probes:
        path = m.resolve_remember_path(about, client_name="claude.ai")
        if not path.startswith("inbound/mcp/"):
            all_inbound = False
            print(f"      [!] about={about!r} -> {path} (NOT the inbound/ raw lane)")
        if any(path.startswith(root) for root in mcp_locks):
            no_locked = False
            print(f"      [!] about={about!r} -> {path} (LOCKED root)")
    results.append(_check(
        "4 every remember RAW observation lands in inbound/mcp/ lane (capture, not derived; incl. adversarial 'system'/'identity')",
        all_inbound))
    results.append(_check(
        "5 no raw path lands in a root the mcp caller is locked from",
        no_locked, f"locked roots={mcp_locks}"))

    # 6. the deterministic-domain fiction is gone (placement is judgment now)
    results.append(_check(
        "6 ADR-151 domain-routing fiction DELETED (_classify_domain / DOMAIN_KEYWORDS)",
        not hasattr(m, "_classify_domain") and not hasattr(m, "DOMAIN_KEYWORDS")))

    # 7. token-based client derivation EXISTS (the mcp:unknown fix — real client
    #    identity is in the OAuth access token, not the raw HTTP request).
    results.append(_check(
        "7 derive_client_name_from_token EXISTS (provenance reads the OAuth session)",
        hasattr(m, "derive_client_name_from_token")))

    # 8. compose_trace does NOT strip the /workspace/ prefix (the live trace bug:
    #    ListRevisions queries the canonical absolute path; a stripped path → 0).
    import inspect
    trace_src = inspect.getsource(m.compose_trace)
    results.append(_check(
        "8 compose_trace queries the ABSOLUTE path (no /workspace/-strip regression)",
        'path[len("/workspace/"):]' not in trace_src and "abs_path" in trace_src))

    # 9. the deterministic round-trip helper EXISTS and is SYMMETRIC with the
    #    write slug (Finding 1, 2026-06-26): remember(about=X) writes the raw to
    #    inbound/mcp/{client}/{slug(X)}.md, so recall/trace(subject=X) must
    #    resolve the SAME slug. The save and read sides must agree on the slug, or
    #    the round-trip silently misses. (recall resolves derived-first then the
    #    raw inbound/ file; both key on slug(X).)
    have_helpers = hasattr(m, "resolve_memory_path") and hasattr(m, "_naturalize_subject")
    symmetric = True
    if have_helpers:
        for subj in ("Acme Corp", "yarnnn-mcp-connector", "Project Zephyr", "a b/c_d"):
            write_path = m.resolve_remember_path(subj, client_name="claude.ai")  # inbound/mcp/{client}/{slug}.md
            read_slug = m._slugify(subj)                          # what resolve_memory_path keys on
            if not write_path.endswith(f"/{read_slug}.md"):
                symmetric = False
                print(f"      [!] subject={subj!r}: write={write_path} read_slug={read_slug} (asymmetric)")
    results.append(_check(
        "9 deterministic round-trip is SYMMETRIC (remember slug == recall/trace slug)",
        have_helpers and symmetric))

    # 10. recall + trace resolve DETERMINISTICALLY before any full-text search,
    #     and naturalize the subject for the fuzzy fallback so a slug doesn't
    #     AND-match prose (the live miss: 'yarnnn-mcp-connector' → zero rows).
    #     recall uses resolve_memory_path (memory-shaped); trace uses
    #     resolve_trace_path (name-match-first, ADR-372) — both deterministic
    #     before FTS, both naturalize the fuzzy fallback. (ADR-372 moved trace's
    #     deterministic+naturalize logic INTO resolve_trace_path.)
    recall_src = inspect.getsource(m.compose_recall)
    trace_resolver_src = inspect.getsource(m.resolve_trace_path)
    deterministic_first = (
        "resolve_memory_path" in recall_src and "resolve_trace_path" in trace_src
    )
    naturalized = (
        "_naturalize_subject" in recall_src and "_naturalize_subject" in trace_resolver_src
    )
    results.append(_check(
        "10 recall+trace resolve deterministically first AND naturalize the fuzzy fallback (no slug-AND-match regression)",
        deterministic_first and naturalized,
        f"deterministic={deterministic_first} naturalized={naturalized}"))

    total, passed = len(results), sum(results)
    print(f"\n{passed}/{total} ADR-368 assertions pass")
    if passed != total:
        sys.exit(1)


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    main()
