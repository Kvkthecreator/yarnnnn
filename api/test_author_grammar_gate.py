"""Gate — the signature grammar is enforced at the write door.

CANON-LOCK-2026-07-30 §9.1 surfaced live ledger rows whose author strings
sit outside the ADR-209/411 attribution taxonomy (free-text
"<email> via <model>" forms from the pre-ADR-411 lane era). "Every change
signed by whoever made it" is the product subhead, which makes the
signature grammar product surface: the door must reject what it cannot
parse, not retain it.

This gate FALSIFIES with the exact malformed strings observed in
production (2026-07-30 probe receipts), not just happy-path shapes — a
gate that only asserts valid forms pass would have been green while the
malformed rows landed.

Run: python3 -m pytest api/test_author_grammar_gate.py  (or pytest from api/)
"""

import pytest

from services.authored_substrate import (
    VALID_AUTHOR_PREFIXES,
    is_valid_author,
    write_revision,
)


# The exact author strings found in the production ledger on 2026-07-30.
LIVE_MALFORMED = [
    "kvkthecreator@gmail.com via Claude Sonnet",
    "probe via Claude Sonnet",
]

# One representative of every live taxonomy class (ADR-209 + ADR-411 D4).
LIVE_VALID = [
    "operator",
    "operator-proxy:eval-suite",
    "yarnnn:claude-sonnet",
    "yarnnn:mcp:chatgpt",
    "agent:alpha-trader",
    "specialist:researcher",
    "freddie:ai:freddie-sonnet-v8",
    "system:bundle-fork",
    "dispatcher:p4-budget-exhausted",
    "member:2abf3f96-118b-4987-9d95-40f2d9be9a18 via gemini/gemini-2.5-pro",
]


class TestIsValidAuthor:
    def test_every_live_class_passes(self):
        for author in LIVE_VALID:
            assert is_valid_author(author), f"live taxonomy form rejected: {author!r}"

    def test_the_production_malformed_forms_are_rejected(self):
        for author in LIVE_MALFORMED:
            assert not is_valid_author(author), (
                f"malformed production form accepted: {author!r} — the defect "
                "the 2026-07-30 probe found would recur"
            )

    def test_empty_and_bare_prefix_junk_rejected(self):
        assert not is_valid_author("")
        assert not is_valid_author("somebody")
        assert not is_valid_author("email@example.com")

    def test_prefix_table_is_the_single_source(self):
        # Completeness assertion: every prefix the gate exercises exists in
        # the live table, so a taxonomy change forces this gate to be re-read.
        exercised = {"operator", "operator-proxy:", "yarnnn:", "agent:",
                     "specialist:", "freddie:", "system:", "dispatcher:", "member:"}
        assert exercised == set(VALID_AUTHOR_PREFIXES), (
            "VALID_AUTHOR_PREFIXES changed — update this gate's LIVE_VALID "
            "coverage in the same commit"
        )


class TestWriteDoorEnforcement:
    def test_write_revision_rejects_malformed_before_touching_db(self):
        # db_client=None: if validation didn't fire first, the call would
        # AttributeError on the client — a ValueError proves the door
        # rejected the signature before any DB interaction.
        for author in LIVE_MALFORMED:
            with pytest.raises(ValueError, match="attribution taxonomy"):
                write_revision(
                    None,
                    user_id="00000000-0000-0000-0000-000000000000",
                    path="/workspace/operation/gate-probe.md",
                    content="x",
                    authored_by=author,
                    message="gate probe",
                )

    def test_write_revision_still_requires_nonempty(self):
        with pytest.raises(ValueError):
            write_revision(
                None,
                user_id="00000000-0000-0000-0000-000000000000",
                path="/workspace/operation/gate-probe.md",
                content="x",
                authored_by="",
                message="gate probe",
            )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
