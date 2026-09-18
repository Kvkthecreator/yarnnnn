"""The curated lane — a small, authored list whose admission criterion is the
moat-leak test (ADR-657 D1–D3).

This is the OTHER lane, beside `connector_directory.py`. It does not merge into
the consumed seed and never edits it: `connector_directory_seed.json` stays
DERIVED from `anthropics/knowledge-work-plugins` and provenance-stamped
(ADR-635 D1, DP27), and this file stays authored — which is the whole point.

WHY AN AUTHORED LIST IS ADMISSIBLE AT ALL (ADR-657 §3)
ADR-420 §10 rule 2 forbade an authored catalog because curation-as-taste is a
service yarnnn does not sell. This list adds no taste. Its admission criterion
is a test the canon already ratified:

    ADR-420 §10 Amendment — "Does the connector accumulate the user's work on
    its own side?"
      accumulates: false → a true peripheral. It computes and returns; the
                           result lands in yarnnn's files, attributed. ADMITTED.
      accumulates: true  → a competing commons. NOT admissible here. It stays
                           reachable through the OPEN lane, which is exactly
                           what §10 asks of it: a deliberate, eyes-open act.

So the curated lane is the ENFORCEMENT SITE for a rule that has had none: the
rule governed seeding while the paste box was how unseeded servers actually
arrived.

THE PROVENANCE DISCIPLINE, CARRIED OVER, NOT ABANDONED
`connector_directory.load_seed()` raises when the seed lacks its upstream stamp,
because a seed with no upstream is an authored catalog. The mirror rule here:
an entry with no `rationale`, no `accumulates` verdict, or no `reviewed_at` is
REFUSED by `load_curated()`. An authored entry that does not say why it was
admitted is taste, and taste is the thing ADR-420 refused.

SMALL BY CONSTRUCTION (ADR-657 D3)
An authored list has no upstream to re-derive from, so rot is its known failure.
The containment is size plus a date: the lane opens with ONE entry, grows only
when a member's demonstrated need names the next, and every entry carries
`reviewed_at`. `stale_entries()` reports what has not been examined inside
`REVIEW_INTERVAL_DAYS`; the gate reads it, and a stale date is a FINDING rather
than a silent pass.

CURATION IS A DISCOVERY ACT, NEVER AN AUTHORITY ONE (ADR-657 §2)
A curated entry and a pasted URL converge on the same `mcp:{slug}` row, the same
per-tool aperture, the same ADR-577 refusal of an agent caller. Nothing here
touches what may run. What a curated entry carries is what a URL cannot: a real
name, the URL SHAPE the member fills one field of, the credential step in the
vendor's own words, the category pre-filled (so a `needs`-scoped skill can light
up — b21c060's debt), and the moat-leak verdict with its reason.

Entry shape (the finder reads it; `search()`-shaped fields match the consumed
directory so the two lanes render from one row shape):
  {key, title, description, url, category, source: "curated", plugins: [],
   accumulates, rationale, credential_note, credential_steps, credential_url,
   header_name, url_shape, shape_field, shape_label, shape_placeholder,
   shape_help, admitted_at, admitted_by, reviewed_at}
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

CURATED_PATH = Path(__file__).resolve().parent / "connector_curated.json"

#: The file's own provenance — an authored list still says who authored it.
_FILE_REQUIRED_KEYS = ("curated_by", "curated_at", "admission_criterion", "entries")

#: Per entry, the fields without which the entry is taste rather than a verdict.
#: `accumulates` is the moat-leak verdict, `rationale` is its reason on the
#: record, `reviewed_at` is D3's anti-rot stamp.
_ENTRY_REQUIRED_KEYS = ("key", "title", "category", "accumulates", "rationale",
                        "admitted_at", "admitted_by", "reviewed_at")

#: How long an entry may go unexamined before `stale_entries()` reports it.
REVIEW_INTERVAL_DAYS = 120

#: One field, one substitution. Deliberately not a template language: the shape
#: carries exactly one `{name}` hole and the member fills it.
_SHAPE_RX = re.compile(r"\{([a-z_]+)\}")

_curated_cache: Optional[dict] = None


def _iso_date(value: Any, label: str, key: str) -> date:
    try:
        return datetime.fromisoformat(str(value)).date()
    except (TypeError, ValueError):
        raise ValueError(f"curated entry {key!r} has an unreadable {label}: {value!r}")


def load_curated() -> dict:
    """The curated file, validated. Raises when an entry does not carry its
    moat-leak verdict, its rationale, or the date it was last examined —
    the mirror of `connector_directory.load_seed()` refusing an unstamped seed
    (ADR-657 D1)."""
    global _curated_cache
    if _curated_cache is not None:
        return _curated_cache
    data = json.loads(CURATED_PATH.read_text(encoding="utf-8"))
    missing = [k for k in _FILE_REQUIRED_KEYS if k not in data]
    if missing:
        raise ValueError(f"curated connector list lacks provenance: {missing}")
    for entry in data["entries"]:
        key = entry.get("key") or "<unkeyed>"
        gone = [k for k in _ENTRY_REQUIRED_KEYS if entry.get(k) is None]
        if gone:
            raise ValueError(
                f"curated entry {key!r} lacks {gone} — an authored entry that "
                f"does not carry its moat-leak verdict and the reason it was "
                f"admitted is taste, which ADR-420 §10 refuses"
            )
        if not isinstance(entry["accumulates"], bool):
            raise ValueError(
                f"curated entry {key!r} has a non-boolean moat-leak verdict: "
                f"{entry['accumulates']!r}"
            )
        if entry["accumulates"] is True:
            raise ValueError(
                f"curated entry {key!r} accumulates the member's work on its "
                f"own side — a competing commons is not admissible to the "
                f"curated lane (ADR-420 §10 Amendment, ADR-657 D1). It stays "
                f"reachable through the open lane."
            )
        if not str(entry["rationale"]).strip():
            raise ValueError(f"curated entry {key!r} has an empty rationale")
        if not entry.get("url") and not entry.get("url_shape"):
            raise ValueError(f"curated entry {key!r} has neither url nor url_shape")
        if entry.get("url_shape"):
            holes = _SHAPE_RX.findall(entry["url_shape"])
            if len(holes) != 1 or holes[0] != entry.get("shape_field"):
                raise ValueError(
                    f"curated entry {key!r} url_shape must carry exactly one "
                    f"{{field}} hole naming shape_field, got {holes!r}"
                )
        _iso_date(entry["reviewed_at"], "reviewed_at", key)
        _iso_date(entry["admitted_at"], "admitted_at", key)
    _curated_cache = data
    return data


def curated_entries() -> list[dict]:
    """The curated lane, in the directory's own row shape so both lanes render
    from one structure. `url` is None for a shaped entry until the member fills
    the one field — `resolve_url` does that."""
    out = []
    for e in load_curated()["entries"]:
        out.append({
            "name": e["key"],
            "key": e["key"],
            "title": e["title"],
            "description": e.get("description") or "",
            "url": e.get("url"),
            "category": e["category"],
            "source": "curated",
            "plugins": [],
            # What a URL cannot carry (ADR-657 D2).
            "accumulates": e["accumulates"],
            "rationale": e["rationale"],
            "credential_note": e.get("credential_note") or "",
            "credential_steps": e.get("credential_steps") or [],
            "credential_url": e.get("credential_url"),
            "header_name": e.get("header_name"),
            "url_shape": e.get("url_shape"),
            "shape_field": e.get("shape_field"),
            "shape_label": e.get("shape_label"),
            "shape_placeholder": e.get("shape_placeholder"),
            "shape_help": e.get("shape_help"),
            "admitted_at": e["admitted_at"],
            "admitted_by": e["admitted_by"],
            "reviewed_at": e["reviewed_at"],
        })
    return out


def curated_entry(key: str) -> Optional[dict]:
    for e in curated_entries():
        if e["key"] == (key or "").strip().lower():
            return e
    return None


def resolve_url(key: str, value: str = "") -> str:
    """The member's URL for a curated entry. A fixed-URL entry ignores `value`;
    a shaped entry substitutes the one field. Minimal by design (ADR-657 D2) —
    one hole, one value, no template language."""
    entry = curated_entry(key)
    if not entry:
        raise ValueError(f"no curated connector named {key!r}")
    if entry.get("url"):
        return entry["url"]
    field = entry["shape_field"]
    filled = (value or "").strip().strip("/")
    if not filled:
        raise ValueError(f"{entry['title']} needs your {entry.get('shape_label') or field}")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", filled):
        raise ValueError(f"that does not look like a {entry.get('shape_label') or field}")
    return entry["url_shape"].replace("{" + field + "}", filled)


def stale_entries(today: Optional[date] = None) -> list[dict]:
    """Entries not examined inside `REVIEW_INTERVAL_DAYS`. An authored list rots;
    this is the report, and it is a finding, never a silent pass (ADR-657 D3)."""
    now = today or date.today()
    out = []
    for e in load_curated()["entries"]:
        age = (now - _iso_date(e["reviewed_at"], "reviewed_at", e["key"])).days
        if age > REVIEW_INTERVAL_DAYS:
            out.append({"key": e["key"], "reviewed_at": e["reviewed_at"], "days": age})
    return out


__all__ = [
    "CURATED_PATH", "REVIEW_INTERVAL_DAYS", "load_curated", "curated_entries",
    "curated_entry", "resolve_url", "stale_entries",
]
