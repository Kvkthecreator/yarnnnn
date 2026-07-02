"""ADR-336 — Web/RSS Standing Watch regression gate.

Pure-local assertions (no network, no DB): feed parsing + distillation
discipline, registry surface (dispatcher-only), bundle declaration
coherence. The live binding contract test runs against the soak
workspace (see docs/evaluations/journey-anr-scout/).
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
AUTHOR_BUNDLE = REPO_ROOT / "docs" / "programs" / "alpha-author"


_RSS_FIXTURE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <title>Test Press</title>
  <item>
    <title>Artist &amp; Band sign to &lt;b&gt;Label&lt;/b&gt;</title>
    <link>https://example.com/a1</link>
    <pubDate>Wed, 11 Jun 2026 09:00:00 GMT</pubDate>
    <description><![CDATA[<p>A <b>long</b> writeup about the signing.</p>]]></description>
  </item>
  <item>
    <title>Second story</title>
    <link>https://example.com/a2</link>
    <pubDate>Wed, 11 Jun 2026 08:00:00 GMT</pubDate>
    <description>%s</description>
  </item>
</channel></rss>
""" % ("x" * 600)

_ATOM_FIXTURE = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Atom Source</title>
  <entry>
    <title>Atom entry one</title>
    <link rel="alternate" href="https://example.com/atom1"/>
    <updated>2026-06-11T09:30:00Z</updated>
    <summary>Short summary.</summary>
  </entry>
</feed>
"""


def test_parse_rss_distills_entries():
    from services.primitives.track_web_sources import parse_feed, _MAX_SUMMARY_CHARS

    entries = parse_feed(_RSS_FIXTURE)
    assert len(entries) == 2
    e = entries[0]
    # HTML stripped from title + summary; entities resolved by ET
    assert e["title"] == "Artist & Band sign to Label"
    assert e["url"] == "https://example.com/a1"
    assert e["published"].startswith("Wed, 11 Jun 2026")
    assert "<" not in e["summary"] and "long" in e["summary"]
    # Bounded distillation (ADR-153): summaries hard-capped
    assert len(entries[1]["summary"]) <= _MAX_SUMMARY_CHARS


def test_parse_atom_distills_entries():
    from services.primitives.track_web_sources import parse_feed

    entries = parse_feed(_ATOM_FIXTURE)
    assert len(entries) == 1
    assert entries[0]["title"] == "Atom entry one"
    assert entries[0]["url"] == "https://example.com/atom1"
    assert entries[0]["published"] == "2026-06-11T09:30:00Z"


def test_parse_rejects_non_feed_xml():
    from services.primitives.track_web_sources import parse_feed
    import pytest

    with pytest.raises(ValueError):
        parse_feed("<html><body>not a feed</body></html>")


def test_registered_in_handlers_dispatcher_only():
    """ADR-336 D1: TrackWebSources is HANDLERS-registered (mechanical
    dispatcher routes to it) and in NO LLM tool surface — same discipline
    as TrackUniverse/TrackRegime."""
    from services.primitives.registry import (
        HANDLERS, CHAT_PRIMITIVES, FREDDIE_PRIMITIVES, HEADLESS_PRIMITIVES,
    )

    assert "TrackWebSources" in HANDLERS
    for surface, name in (
        (CHAT_PRIMITIVES, "chat"),
        (FREDDIE_PRIMITIVES, "reviewer"),
        (HEADLESS_PRIMITIVES, "headless"),
    ):
        tool_names = {t.get("name") for t in surface if isinstance(t, dict)}
        assert "TrackWebSources" not in tool_names, (
            f"TrackWebSources must not be LLM-callable ({name} surface)"
        )


def test_alpha_author_bundle_declares_the_watch():
    """ADR-336 D2: the watch is bundle-declared (never workspace-freehand —
    ADR-335 anti-goal); recurrence pointer resolves; envelope carries the
    signal; the template ships EMPTY sources (lean shape stays valid)."""
    manifest = yaml.safe_load((AUTHOR_BUNDLE / "MANIFEST.yaml").read_text())
    abi = manifest["substrate_abi"]

    watches = abi.get("watches") or []
    w = next((x for x in watches if x.get("id") == "interest-sources"), None)
    assert w, "alpha-author does not declare the interest-sources watch"
    assert w["declaration"] == "operation/authored/_sources.yaml"
    assert w["recurrence"] == "track-sources"
    assert w["distills_to"] == "operation/authored/_watch_signal.yaml"
    # flows_na.perception replaced by the declared watch (Singular)
    assert not (abi.get("flows_na") or {}).get("perception"), (
        "flows_na.perception must be removed once the watch is declared"
    )

    # ADR-393: the standing watch is a CAPTURE (deterministic intake, run by
    # the capture lane outside the wake funnel) — it moved from
    # _recurrences.yaml to _captures.yaml verbatim; the `mode` field is
    # retired (being in _captures.yaml IS the class).
    cap = yaml.safe_load(
        (AUTHOR_BUNDLE / "reference-workspace" / "_captures.yaml").read_text()
    )
    entry = next((c for c in cap["captures"] if c["slug"] == "track-sources"), None)
    assert entry, "track-sources capture missing from bundle"
    assert "mode" not in entry, "mode field is retired (ADR-393)"
    assert "TrackWebSources(" in entry["primitive"]
    assert 'declaration="operation/authored/_sources.yaml"' in entry["primitive"]

    env_keys = {d.get("key") for d in abi.get("reviewer_wake_envelope", [])}
    assert "watch_signal" in env_keys, "watch_signal missing from wake envelope"

    template = (AUTHOR_BUNDLE / "reference-workspace" / "operation" / "authored" / "_sources.yaml").read_text()
    body = template.split("---", 2)[-1]
    assert yaml.safe_load(body).get("sources") == [], (
        "_sources.yaml template must ship EMPTY (empty = no-op; perception "
        "is a flow, never a gate)"
    )


def test_empty_declaration_is_noop_not_error():
    """Empty sources = deliberate no-op (the lean shape)."""
    from services.primitives.track_web_sources import _read_sources

    class _Res:
        def __init__(self, data): self.data = data

    class _Q:
        def __init__(self, content): self._c = content
        def select(self, *a, **k): return self
        def eq(self, *a, **k): return self
        def limit(self, *a, **k): return self
        def execute(self): return _Res([{"content": self._c}])

    class _Client:
        def __init__(self, content): self._c = content
        def table(self, name): return _Q(self._c)

    tpl = "---\ntier: authored\n---\n# header\nsources: []\n"
    assert _read_sources(_Client(tpl), "u", "operation/authored/_sources.yaml") == []
    assert _read_sources(_Client(None), "u", "operation/authored/_sources.yaml") is None
