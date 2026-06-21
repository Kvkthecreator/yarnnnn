"""ADR-351 Phase 1 gate — tool-aware streaming LLM call + addressed-path wiring.

Asserts the load-bearing invariants of the in-flight invocation-rendering
backend, with the Anthropic SDK fully mocked (no real API calls):

  1. chat_completion_with_tools_stream() returns a ChatResponse IDENTICAL in
     shape to the blocking chat_completion_with_tools() — content blocks,
     stop_reason, text, tool_uses, and usage (incl. cache metrics for the
     ADR-291 cost ledger). The whole Reviewer loop depends on this contract.
  2. on_text_delta fires once per reasoning chunk, in order.
  3. A flaky on_text_delta NEVER breaks the cycle (best-effort relay).
  4. The streaming call drains correctly with NO subscriber (final message
     still assembles) — the reactive/scheduled paths never pass a callback.
  5. invoke_reviewer's addressed trigger routes to the STREAMING call and
     reactive/scheduled route to the BLOCKING call — no dual call on the
     addressed path (ADR-351 §4 + §6 Phase 3 deferral).
  6. wake.py relays a text_delta phase as its own SSE event type; feed.py
     forwards it.

Run: pytest test_adr351_streaming_tools.py -q
"""
from __future__ import annotations

import asyncio
import inspect
from types import SimpleNamespace

import pytest

import services.anthropic as anthropic_mod
from services.anthropic import (
    ChatResponse,
    chat_completion_with_tools,
    chat_completion_with_tools_stream,
)


# --------------------------------------------------------------------------
# Fakes: mimic the Anthropic SDK's streaming + blocking surfaces minimally.
# --------------------------------------------------------------------------

def _fake_message(text_blocks: list[str], tool_uses: list[dict], stop_reason: str):
    """Build a fake anthropic Message with content blocks + usage."""
    content = []
    for t in text_blocks:
        content.append(SimpleNamespace(type="text", text=t))
    for tu in tool_uses:
        content.append(SimpleNamespace(
            type="tool_use", id=tu["id"], name=tu["name"], input=tu["input"],
        ))
    usage = SimpleNamespace(
        input_tokens=11,
        output_tokens=22,
        cache_creation_input_tokens=3,
        cache_read_input_tokens=7,
    )
    return SimpleNamespace(content=content, stop_reason=stop_reason, usage=usage, model="fake")


class _FakeStream:
    """Async context manager mimicking client.messages.stream(...)."""

    def __init__(self, chunks: list[str], final_message):
        self._chunks = chunks
        self._final = final_message

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    @property
    def text_stream(self):
        async def _gen():
            for c in self._chunks:
                yield c
        return _gen()

    async def get_final_message(self):
        return self._final


class _FakeMessages:
    def __init__(self, chunks, final_message, blocking_message):
        self._chunks = chunks
        self._final = final_message
        self._blocking = blocking_message
        self.stream_kwargs = None
        self.create_kwargs = None

    def stream(self, **kwargs):
        self.stream_kwargs = kwargs
        return _FakeStream(self._chunks, self._final)

    async def create(self, **kwargs):
        self.create_kwargs = kwargs
        return self._blocking


class _FakeClient:
    def __init__(self, messages):
        self.messages = messages


@pytest.fixture
def patched_client(monkeypatch):
    """Patch get_anthropic_client to return a controllable fake."""
    chunks = ["Let me ", "check the ", "signals."]
    final = _fake_message(
        text_blocks=["Let me check the signals."],
        tool_uses=[{"id": "tu_1", "name": "ReadFile", "input": {"path": "x"}}],
        stop_reason="tool_use",
    )
    blocking = _fake_message(
        text_blocks=["blocking text"],
        tool_uses=[{"id": "tu_b", "name": "ReturnVerdict", "input": {"verdict": "ok"}}],
        stop_reason="tool_use",
    )
    msgs = _FakeMessages(chunks, final, blocking)
    monkeypatch.setattr(anthropic_mod, "get_anthropic_client", lambda: _FakeClient(msgs))
    return msgs, chunks


# --------------------------------------------------------------------------
# 1 — identical ChatResponse contract
# --------------------------------------------------------------------------

def test_streaming_returns_identical_chatresponse_shape(patched_client):
    msgs, chunks = patched_client

    resp = asyncio.run(chat_completion_with_tools_stream(
        messages=[{"role": "user", "content": "hi"}],
        system="sys",
        tools=[{"name": "ReadFile"}],
    ))

    assert isinstance(resp, ChatResponse)
    # text concatenated from content blocks (same as _parse_response)
    assert resp.text == "Let me check the signals."
    assert resp.stop_reason == "tool_use"
    # tool_uses extracted
    assert [t.name for t in resp.tool_uses] == ["ReadFile"]
    assert resp.tool_uses[0].input == {"path": "x"}
    # usage incl. cache metrics preserved for ADR-291 ledger
    assert resp.usage["input_tokens"] == 11
    assert resp.usage["output_tokens"] == 22
    assert resp.usage["cache_creation_input_tokens"] == 3
    assert resp.usage["cache_read_input_tokens"] == 7
    # raw content blocks present (the truncation guard inspects these)
    assert any(getattr(b, "type", None) == "tool_use" for b in resp.content)


def test_signature_is_blocking_plus_on_text_delta():
    s_stream = set(inspect.signature(chat_completion_with_tools_stream).parameters)
    s_block = set(inspect.signature(chat_completion_with_tools).parameters)
    assert s_stream - s_block == {"on_text_delta"}


# --------------------------------------------------------------------------
# 2 — on_text_delta fires per chunk, in order
# --------------------------------------------------------------------------

def test_on_text_delta_fires_per_chunk_in_order(patched_client):
    msgs, chunks = patched_client
    seen: list[str] = []

    async def cb(chunk: str) -> None:
        seen.append(chunk)

    asyncio.run(chat_completion_with_tools_stream(
        messages=[{"role": "user", "content": "hi"}],
        system="sys",
        tools=[{"name": "ReadFile"}],
        on_text_delta=cb,
    ))
    assert seen == chunks


# --------------------------------------------------------------------------
# 3 — a flaky callback never breaks the cycle
# --------------------------------------------------------------------------

def test_flaky_callback_does_not_break_cycle(patched_client):
    msgs, chunks = patched_client

    async def boom(_chunk: str) -> None:
        raise RuntimeError("relay died")

    # Must still return a valid ChatResponse despite the callback raising.
    resp = asyncio.run(chat_completion_with_tools_stream(
        messages=[{"role": "user", "content": "hi"}],
        system="sys",
        tools=[{"name": "ReadFile"}],
        on_text_delta=boom,
    ))
    assert resp.text == "Let me check the signals."
    assert resp.stop_reason == "tool_use"


# --------------------------------------------------------------------------
# 4 — drains with no subscriber
# --------------------------------------------------------------------------

def test_drains_with_no_subscriber(patched_client):
    msgs, chunks = patched_client
    resp = asyncio.run(chat_completion_with_tools_stream(
        messages=[{"role": "user", "content": "hi"}],
        system="sys",
        tools=[{"name": "ReadFile"}],
        on_text_delta=None,
    ))
    # final message still assembled even though nobody listened
    assert resp.text == "Let me check the signals."
    # tools forwarded into the stream call
    assert msgs.stream_kwargs is not None
    assert "tools" in msgs.stream_kwargs


# --------------------------------------------------------------------------
# 5 — addressed routes to streaming; reactive/scheduled route to blocking
# --------------------------------------------------------------------------

def test_addressed_path_uses_streaming_call_source():
    """Source-level guard: the streaming call is reachable ONLY from the
    addressed branch, and the blocking call ONLY from the else branch.
    Asserts against the source so a future refactor that drops the trigger
    discrimination (re-introducing a dual blocking call on the addressed
    path, the ADR-351 §4 violation) trips the gate."""
    src = inspect.getsource(__import__("agents.reviewer_agent", fromlist=["x"]))
    assert "chat_completion_with_tools_stream(" in src, "addressed path lost the streaming call"
    assert 'if trigger == "addressed":' in src, "trigger discrimination removed"
    # the blocking call survives for the non-addressed branch
    assert "chat_completion_with_tools(" in src
    # the streaming call must be on the addressed side of the branch:
    addressed_idx = src.index('if trigger == "addressed":')
    stream_idx = src.index("chat_completion_with_tools_stream(", addressed_idx)
    else_idx = src.index("else:", addressed_idx)
    assert stream_idx < else_idx, "streaming call is not inside the addressed branch"


# --------------------------------------------------------------------------
# 6 — wake.py + feed.py relay text_delta as a distinct SSE type
# --------------------------------------------------------------------------

def test_wake_relays_text_delta_as_distinct_sse_type():
    src = inspect.getsource(__import__("services.wake", fromlist=["x"]))
    assert 'phase == "text_delta"' in src
    assert '"type": "text_delta"' in src


def test_feed_forwards_text_delta_event():
    src = inspect.getsource(__import__("routes.feed", fromlist=["x"]))
    assert 'etype == "text_delta"' in src
    assert "'phase': 'text_delta'" in src


# --------------------------------------------------------------------------
# 7 — Phase 2 frontend source-guards (the web package has no JS test runner,
#     so these guard the load-bearing FE invariants from the Python gate —
#     same pattern as the wake/feed source-guards above. tsc --noEmit is the
#     companion type gate, run separately in web/.)
# --------------------------------------------------------------------------

import os

_WEB = os.path.join(os.path.dirname(__file__), "..", "web")


def _read_web(rel: str) -> str:
    with open(os.path.join(_WEB, rel), encoding="utf-8") as fh:
        return fh.read()


def test_frontend_handles_text_delta_with_streaming_reviewer_bubble():
    src = _read_web("contexts/NarrativeContext.tsx")
    # the text_delta phase is handled (Phase 2 progressive render)
    assert "phase === 'text_delta'" in src
    # a streaming REVIEWER bubble is inserted (role:'reviewer' → reviewer-bubble)
    assert "role: 'reviewer'" in src


def test_frontend_tool_name_label_map_is_deleted():
    """ADR-351 D4: the per-tool guess map ('Reviewer is reading substrate…'
    et al.) must be gone — it was a stand-in for narration that now streams
    from the persona itself. This is the exact copy the operator disliked."""
    src = _read_web("contexts/NarrativeContext.tsx")
    assert "Reviewer is reading substrate" not in src
    assert "Reviewer is checking history" not in src
    assert "Reviewer is checking system state" not in src
    # the consent-line guard (ADR-338 DP28): no raw primitive name leaks into
    # the transient status as `Reviewer is using {tool}`
    assert "Reviewer is using ${tool}" not in src


def test_reviewer_role_is_first_class_in_role_union():
    src = _read_web("types/index.ts")
    assert '| "reviewer"' in src


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
