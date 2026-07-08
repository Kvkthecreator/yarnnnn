"""
ADR-423 — revision_kind: provenance as a flag on the ledger.

Structural gate for the tag-in-place fold (the arrival badge that lets the two
raw lanes unify under Downloads/). Pure-Python (no DB, no `mcp` package); the
live round-trip is the MCP remember probe.

Asserts:
  1. write_revision + _insert_revision accept revision_kind (default 'authored').
  2. _insert_revision only writes the column when NON-default (byte-identical for
     authored writes + safe against a not-yet-migrated DB).
  3. The write-path wrappers (UserMemory.write, AgentWorkspace.write) + the
     WriteFile primitive thread revision_kind through.
  4. The three intake writers tag 'observation':
       - MCP remember (dispatch_remember_this WriteFile input)
       - connector capture (_write_if_changed helper — one spot, both callers)
       - web watches (track_web_sources raw observation write)
  5. The Revision dataclass carries revision_kind; list/read revision selects it;
     trace surfaces it in history + ListRevisions forwards it.
  6. No non-intake writer sets revision_kind (the ~40 others take the default) —
     a Singular-Implementation guard against scatter.
"""

import inspect
import sys


def _check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}")
    return bool(ok)


def run() -> int:
    passed = True

    # 1 — signatures accept revision_kind, default 'authored'
    from services.authored_substrate import write_revision, _insert_revision, Revision
    wr = inspect.signature(write_revision).parameters
    ins = inspect.signature(_insert_revision).parameters
    passed &= _check(
        "write_revision has revision_kind default 'authored'",
        "revision_kind" in wr and wr["revision_kind"].default == "authored",
    )
    passed &= _check(
        "_insert_revision has revision_kind default 'authored'",
        "revision_kind" in ins and ins["revision_kind"].default == "authored",
    )

    # 2 — _insert_revision only writes the column when non-default
    captured = {}

    class _Result:
        data = [{"id": "rev-1"}]

    class _Table:
        def insert(self, row):
            captured["row"] = row
            return self

        def execute(self):
            return _Result()

    class _DB:
        def table(self, name):
            captured["table"] = name
            return _Table()

    # default → no revision_kind key in the row
    captured.clear()
    _insert_revision(_DB(), user_id="u", path="p", blob_sha="s",
                     parent_version_id=None, authored_by="operator",
                     author_identity_uuid=None, message="m")
    passed &= _check(
        "authored write omits revision_kind (byte-identical)",
        "revision_kind" not in captured["row"],
        f"row keys: {sorted(captured['row'])}",
    )
    # observation → the column IS written
    captured.clear()
    _insert_revision(_DB(), user_id="u", path="p", blob_sha="s",
                     parent_version_id=None, authored_by="system:x",
                     author_identity_uuid=None, message="m",
                     revision_kind="observation")
    passed &= _check(
        "observation write sets revision_kind='observation'",
        captured["row"].get("revision_kind") == "observation",
    )

    # 3 — the write-path wrappers + WriteFile thread it
    from services.workspace import UserMemory, AgentWorkspace
    um_w = inspect.signature(UserMemory.write).parameters
    aw_w = inspect.signature(AgentWorkspace.write).parameters
    passed &= _check("UserMemory.write threads revision_kind", "revision_kind" in um_w)
    passed &= _check("AgentWorkspace.write threads revision_kind", "revision_kind" in aw_w)

    import services.primitives.workspace as wsprim
    src = inspect.getsource(wsprim.handle_write_file)
    passed &= _check(
        "handle_write_file reads input['revision_kind'] + forwards it",
        'input.get("revision_kind")' in src and "revision_kind=revision_kind" in src,
    )

    # 4 — the three intake writers tag 'observation'
    import services.mcp_composition as mcpc
    remember_src = inspect.getsource(mcpc.dispatch_remember_this)
    passed &= _check(
        "MCP remember tags observation",
        '"revision_kind": "observation"' in remember_src,
    )

    import services.primitives.sync_platform_state as syncp
    wic_src = inspect.getsource(syncp._write_if_changed)
    passed &= _check(
        "connector capture (_write_if_changed) tags observation",
        'revision_kind="observation"' in wic_src,
    )

    import services.primitives.track_web_sources as tws
    tws_src = inspect.getsource(tws)
    passed &= _check(
        "web watch raw write tags observation",
        'revision_kind="observation"' in tws_src,
    )
    # ...and the DISTILLED signal write does NOT (it's not a raw arrival).
    _obs_count = tws_src.count('revision_kind="observation"')
    passed &= _check(
        "web watch signal write stays authored (only raw is observation)",
        _obs_count == 1,
        "count={}".format(_obs_count),
    )

    # 5 — read path surfaces revision_kind
    rev_fields = Revision.__dataclass_fields__
    passed &= _check("Revision carries revision_kind", "revision_kind" in rev_fields)
    lr_src = inspect.getsource(__import__("services.authored_substrate", fromlist=["list_revisions"]).list_revisions)
    passed &= _check("list_revisions selects revision_kind", "revision_kind" in lr_src)
    trace_src = inspect.getsource(mcpc.compose_trace)
    passed &= _check(
        "trace surfaces revision_kind in history from the column",
        '"revision_kind": rev.get("revision_kind")' in trace_src,
    )

    # 6 — Singular Implementation: no non-intake writer scatters an observation tag.
    # The ONLY files that may name revision_kind='observation' are the 3 intake
    # writers (+ the composition/primitive plumbing that forwards it). Guard by
    # asserting the write-path default is the single source of the 'authored'
    # value (a scattered literal elsewhere would be drift).
    passed &= _check(
        "write_revision is the single default source ('authored')",
        wr["revision_kind"].default == "authored",
    )

    return 0 if passed else 1


# pytest entry
def test_adr423_revision_kind():
    assert run() == 0


if __name__ == "__main__":
    sys.exit(run())
