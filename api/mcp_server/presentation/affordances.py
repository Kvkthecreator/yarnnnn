"""Per-tool presentation affordances — data, not code (ADR-372 D1).

A tool declares an OPTIONAL affordance here; a tool with no entry is text-only
(the default, valid on every host). This is the durable layer: verbs come and
go (the ADR-543 file-native re-cut retired three), but the affordance MECHANISM
is stable. A new verb opts in with one dict entry; a removed verb drops one. No
tool body is rewired, and the vendor `_meta` shape is generated downstream
(registry + adapters), never authored here.

`history` carries the flagship affordance: the ADR-209 authored revision chain
is YARNNN's differentiator and a who-changed-what-when timeline is inherently
visual.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Affordance:
    """A tool's optional rich-rendering declaration.

    Attributes:
        widget:      registry id (→ a `ui://` resource in registry.WIDGETS).
        fallback:    always "text" — the text path is never removed (ADR-372 D4).
        interactive: True if the widget may call back into tools over the MCP Apps
                     bridge (ADR-372 D6 — callbacks are the same gated tool).
    """

    widget: str
    fallback: str = "text"
    interactive: bool = False


#: tool name → affordance. A tool absent from this map is text-only — but as of
#: ADR-533 D4 that absence must be DECLARED in TEXT_ONLY below, not merely
#: implied, so a new verb cannot silently ship with no rendering story.
AFFORDANCES: dict[str, Affordance] = {
    # ADR-543: the renamed read verbs keep their widgets (history was trace's,
    # search was recall's) — the rendering story survives the ontology re-cut.
    "history": Affordance(widget="history-timeline", fallback="text", interactive=True),
    "search": Affordance(widget="search-results", fallback="text", interactive=False),
    # ADR-533 D4 — the file verbs.
    # `save`: the widget exists for the CONFLICT (stale_write / base_required).
    # Someone else holding the head is the one outcome the user must act on, and
    # a chat host renders it as a paragraph they skim past.
    "save": Affordance(widget="save-receipt", fallback="text", interactive=False),
    # `open`: renders the file's IDENTITY (whose version, when, how many
    # revisions) — never its content. The content is the host's to render; the
    # attribution is what a plain storage connector cannot show.
    "open": Affordance(widget="file-header", fallback="text", interactive=False),
}

#: tool name → why it is deliberately text-only (ADR-533 D4).
#:
#: An entry here is a DECISION, not an omission. `test_adr533_participant_contract`
#: asserts every rostered verb is in AFFORDANCES *or* here — so the choice is
#: always recorded, and "we never got to it" cannot masquerade as "text is right".
#: Moving a verb from here to AFFORDANCES is the whole cost of adding a widget.
TEXT_ONLY: dict[str, str] = {
    # ADR-584 — the answer's whole job is to change what the MODEL says next
    # (name the workspace before writing; state a `fallback` binding out loud).
    # A widget renders for the human and is invisible to the reader who has to
    # act on it, so the one verb whose audience is the model is the last one
    # that should be put behind glass.
    "whoami": (
        "The result orients the MODEL, not the human — which workspace it is "
        "standing in, and whether that is the one the operator chose. Its value "
        "is in the model's next sentence, so it must be text the model reads, "
        "never an iframe the user looks at."
    ),
    "share": (
        "The result is a link plus a reach level — one line the host relays "
        "verbatim. A widget for a URL is ceremony: it adds an iframe the user "
        "must look at to read something the sentence already said."
    ),
    "list": (
        "The result is a file tree — paths the host itself renders better as "
        "text the model can quote and open. An iframe listing would trap the "
        "paths behind glass; the whole point of list is that every line is an "
        "openable reference."
    ),
    # ADR-545 — the write-side completions. Each returns a one-line receipt
    # (what changed / where it went / the tombstone id) that the model relays
    # in its own sentence; a widget would add an iframe to read a line.
    "edit": (
        "The result is a replacement count and a path — one line the model "
        "narrates. The change itself is visible via history's diffs, where "
        "the timeline widget already renders it."
    ),
    "delete": (
        "The result is a tombstone receipt — one line. The reversible-removal "
        "story belongs in the model's sentence, not behind glass."
    ),
    "move": (
        "The result is from→to — one line the model narrates. Nothing to "
        "render that the sentence doesn't already say."
    ),
}


def affordance_for(tool_name: str) -> Affordance | None:
    """Return the affordance for a tool, or None (text-only)."""
    return AFFORDANCES.get(tool_name)


def text_only_reason(tool_name: str) -> str | None:
    """Why this tool is deliberately text-only, or None if it has a widget."""
    return TEXT_ONLY.get(tool_name)
