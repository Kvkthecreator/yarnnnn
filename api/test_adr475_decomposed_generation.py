"""ADR-475 — decomposed generation: the composition EXECUTES and PAINTS.

WHY THIS GATE IS SHAPED THIS WAY. Two lessons are encoded here, both paid for:

1. **A gate that greps proves a symbol exists, never that a handler reaches
   it** (the 2026-07-20 prod break: function-scoped imports, every gate green,
   two endpoints 500ing with NameError). So this gate CALLS `compose()` — the
   real endpoint body, through a fake substrate.

2. **A composition can be structurally perfect and render as nothing.** The
   first composed ad (ADR-472 D6's forcing function) placed all five layers
   correctly and painted two of them at ZERO HEIGHT: the kernel measure rule
   is `height: var(--yh, auto)`, and `auto` on an absolutely-positioned EMPTY
   element is 0px. Browser-measured, both ways:

       without h → background 756x0   subject 454x51   (invisible)
       with h    → background 756x396 subject 454x229  (correct)

   So this gate asserts the ZERO-HEIGHT INVARIANT directly: every non-text
   layer carries `h`. A "the markup has all five layers" assertion passes on
   the broken version — which is exactly the read-test-that-passes-on-empty
   failure this codebase has been bitten by before.

Run:  python3 api/test_adr475_decomposed_generation.py   (NOT pytest — check()-gate.)
"""

import asyncio
import re
import sys
from pathlib import Path

_results: list[tuple[str, bool]] = []


def _check(label: str, cond: bool) -> None:
    _results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")


class _FakeTable:
    """The two reads the compose handler makes, and nothing else."""

    def __init__(self, store: dict):
        self._store = store
        self._path = None

    def select(self, *_a, **_k):
        return self

    def eq(self, col, val):
        if col == "path":
            self._path = val
        return self

    def limit(self, *_a):
        return self

    def execute(self):
        row = self._store.get(self._path)
        return type("R", (), {"data": [row] if row else []})()


class _FakeClient:
    def __init__(self, store: dict):
        self._store = store

    def table(self, _name):
        return _FakeTable(self._store)


class _FakeAuth:
    user_id = "00000000-0000-0000-0000-000000000000"

    def __init__(self, store: dict):
        self.client = _FakeClient(store)


def run() -> bool:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

    from services.images import STAGE_SLUG, resolve_dimensions, stage_root_attrs
    from services.images.decompose import _coerce, heuristic_plan
    from services.images.generate import StubBackend, compose_layers
    from services.studio import STUDIO_ARTIFACT_REGION, build_skeleton

    # ── Build a real stage the way POST /studio/artifacts does ───────────
    w, h = resolve_dimensions(preset_slug="ad")
    stage_html = build_skeleton(STAGE_SLUG, "Gate stage").replace(
        f'<html data-template="{STAGE_SLUG}">',
        f'<html data-template="{STAGE_SLUG}" {stage_root_attrs(w, h)}>',
        1,
    )
    path = f"{STUDIO_ARTIFACT_REGION}gate-ad/image.html"
    store = {path: {"path": path, "content": stage_html}}

    # Record every write so the N+1 revision claim is checked, not assumed.
    writes: list[dict] = []

    import services.authored_substrate as sub

    def _fake_write(_db, *, user_id, path, content=None, content_bytes=None,
                    authored_by, message, **kw):
        writes.append({
            # WHICH CLIENT reached the write. The pre-2026-07-21 gate ignored
            # this and passed 43/43 against code that 403'd in production on
            # every binary leaf: a binary revision uploads to the PRIVATE
            # `workspace-cas` bucket and a member JWT is refused there. The
            # client is now part of the assertion surface.
            "client": _db,
            "path": path, "author": authored_by, "message": message,
            "is_binary": content_bytes is not None,
            "content": content, "content_type": kw.get("content_type"),
            # Captured explicitly: the derivation assertions below would pass
            # vacuously on a dict that never carried these keys.
            "revision_kind": kw.get("revision_kind"),
            "derived_from": kw.get("derived_from"),
        })
        return f"rev-{len(writes):03d}"

    sub.write_revision = _fake_write

    # The SERVICE client — a distinct sentinel object, so "which client did
    # this write use?" is answerable by identity rather than by inspection.
    class _ServiceClient:
        """Stands in for get_service_client(). Identity is the whole point."""

    service_client = _ServiceClient()

    import services.supabase as _supa

    _supa.get_service_client = lambda: service_client

    # The metering ledger, recorded the same way and for the same reason: the
    # live smoke lost $0.16 of rented generation to `42501 new row violates
    # row-level security policy` because this call site passed the member's
    # client to a service-role-only table.
    ledger: list[dict] = []

    import services.telemetry as _tel

    def _fake_ledger(_client, **kw):
        ledger.append({"client": _client, **kw})
        return "evt-1"

    _tel.record_execution_event = _fake_ledger

    import routes.images as ri

    auth = _FakeAuth(store)
    req = ri.ComposeRequest(
        path=path, brief="a launch ad for our vitamin C serum: bright, clinical"
    )

    # ── 1. THE HANDLER EXECUTES ──────────────────────────────────────────
    try:
        result = asyncio.run(ri.compose(req, auth))
        _check("POST /images/compose EXECUTES (no NameError in the body)", True)
    except Exception as exc:  # noqa: BLE001
        _check(
            f"POST /images/compose EXECUTES — raised {type(exc).__name__}: {exc}",
            False,
        )
        _summary()
        return False

    _check("…and reports the layers it composed", result.get("layers", 0) >= 4)
    _check("…and reports the raster leaves it generated", result.get("generated", 0) >= 1)

    # ── 2. N+1 REVISIONS: per-object provenance needs per-object writes ──
    binary = [wr for wr in writes if wr["is_binary"]]
    text = [wr for wr in writes if not wr["is_binary"]]
    _check("every generated leaf lands as its OWN binary revision", len(binary) >= 1)
    _check("…with an image content_type (ADR-427 Category-1 substrate)",
           all(wr["content_type"] == "image/png" for wr in binary))
    _check("the stage lands as exactly ONE text revision", len(text) == 1)
    _check("the leaf is written BEFORE the stage that cites it",
           bool(binary) and writes.index(binary[0]) < writes.index(text[0]))

    composed = text[0]["content"] if text else ""

    # ── 3. THE ZERO-HEIGHT INVARIANT (the first ad's finding) ────────────
    # This is the assertion that would have caught the real defect. Every
    # non-text layer must carry BOTH measures, or it renders at 0px.
    frame = re.search(r'<section[^>]*class="slide".*?</section>', composed, re.DOTALL)
    inner = frame.group(0) if frame else ""
    non_text = re.findall(r'<(?:div|figure)[^>]*data-role="[^"]*"[^>]*>', inner)
    _check("the composition emitted non-text layers (surface/subject)", len(non_text) >= 2)
    _check(
        "EVERY non-text layer carries data-h — a positioned empty box is 0px "
        "without it (browser-measured: 756x0 vs 756x396)",
        bool(non_text) and all('data-h="' in tag for tag in non_text),
    )
    _check(
        "…and the matching --yh property (the marker/value pair, never one alone)",
        bool(non_text) and all("--yh:" in tag for tag in non_text),
    )
    # Text layers must NOT be pinned — a wrapped headline would clip.
    text_tags = re.findall(r'<(?:h1|h2|h3|p)[^>]*data-role="[^"]*"[^>]*>', inner)
    _check(
        "text layers do NOT carry data-h (their content is their height)",
        bool(text_tags) and not any('data-h="' in tag for tag in text_tags),
    )

    # ── 4. THE OBJECT-MODEL THESIS (ADR-468 D2) ──────────────────────────
    _check("raster lands as a CITATION (data-ref), never inline bytes",
           "data-ref=" in inner and "base64" not in inner)
    _check("…pinned to the leaf's head revision (data-ref-rev)", "data-ref-rev=" in inner)
    _check("every generated leaf carries its generation provenance (ADR-468 D4)",
           "data-gen-prompt=" in inner and "data-gen-model=" in inner)
    _check("every object is NAMED (data-role — the plan IS the tree)",
           inner.count("data-role=") >= 4)
    _check("text is REAL TEXT, never generated raster type (D2)",
           bool(re.search(r'<h1[^>]*data-role="headline"[^>]*>[^<]+</h1>', inner)))
    _check("a CSS-expressible surface rents NOTHING (the routing rule)",
           'data-surface="css"' in inner)

    # ── 4b. THE GROUND (ADR-475 §12, found by the first live ad) ─────────
    from services.images.compose import _ground_of
    from services.images.decompose import _coerce

    # The exact failure: a dark full-bleed background with light-page ink →
    # dark-on-dark, every layer placed perfectly and unreadable.
    dark = _coerce([{"role": "bg", "kind": "surface",
                     "style": "background:#0A0A0F", "x": 0, "y": 0, "w": 100, "h": 100}])
    _check("a dark full-bleed surface derives ground='dark' (luminance, not a list)",
           _ground_of(dark) == "dark")
    _check("a light full-bleed surface stays light (absence = light default)",
           _ground_of(_coerce([{"role": "bg", "kind": "surface",
                                "style": "background:#ffffff", "x": 0, "y": 0,
                                "w": 100, "h": 100}])) == "")
    _check("a small dark SHAPE is an object, not the ground (full-bleed only)",
           _ground_of(_coerce([{"role": "chip", "kind": "surface",
                                "style": "background:#000", "x": 10, "y": 10,
                                "w": 20, "h": 8}])) == "")
    _check("an EXPLICIT ground declaration beats the luminance guess",
           _ground_of(_coerce([{"role": "bg", "kind": "surface", "ground": "dark",
                                "style": "background:#ffffff", "x": 0, "y": 0,
                                "w": 100, "h": 100}])) == "dark")

    # The structural bug the replay caught: my ground edit fused the subject-
    # prompt guard into an `else`, so a surface with no `ground` token fell
    # through the subject branch and was DROPPED. A surface must survive
    # regardless of ground.
    _check("a surface with NO ground token still survives _coerce (the fused-else bug)",
           len(_coerce([{"role": "d", "kind": "surface", "style": "background:#7C6DFA",
                         "x": 10, "y": 38, "w": 18, "h": 1}])) == 1)

    # ── 5. THE FRAME SURVIVES (composition replaces contents, not the stage) ──
    _check("the stage's real dimensions survive composition (ADR-472 D3)",
           f'data-w="{w}"' in composed and f'data-h="{h}"' in composed)
    _check("…and the frame keeps its arrangement", 'data-arrange="free"' in inner)
    _check("the scaffold's placeholder is REPLACED, not appended to",
           "The visual statement." not in inner)

    # ── 6. THE COERCER ENFORCES THE INVARIANT STRUCTURALLY ───────────────
    # A model that ignores the prompt must still produce a painting layer.
    coerced = _coerce([
        {"role": "bg", "kind": "surface", "style": "background:red", "x": 0, "y": 0, "w": 100},
        {"role": "hero", "kind": "subject", "prompt": "a bottle", "x": 10, "y": 10, "w": 50},
        {"role": "title", "kind": "text", "text": "Hi", "tag": "h1"},
    ])
    _check("_coerce BACKFILLS h on a model plan that omitted it",
           all("h" in l for l in coerced if l["kind"] in ("surface", "subject")))
    _check("…and leaves text layers unpinned",
           all("h" not in l for l in coerced if l["kind"] == "text"))
    _check("_coerce clamps out-of-range geometry to the kernel's bounds",
           _coerce([{"role": "x", "kind": "surface", "x": 4000, "w": 9000}])[0]["x"] == 95)
    _check("_coerce drops a subject with no prompt (not a renderable leaf)",
           _coerce([{"role": "x", "kind": "subject"}]) == [])
    _check("_coerce drops an unknown kind rather than composing it",
           _coerce([{"role": "x", "kind": "sculpture"}]) == [])

    # ── 7. ESCAPING — markup crosses principals (ADR-373 commons) ────────
    hostile = compose_layers(
        [{"role": "h", "kind": "text", "tag": "p", "text": '<script>x</script>"'}], {}
    )
    _check("member copy is escaped into the markup (multi-principal substrate)",
           "<script>" not in hostile and "&lt;script&gt;" in hostile)
    hostile_prompt = compose_layers(
        [{"role": "s", "kind": "subject", "prompt": 'a "quoted" subject'}],
        {"s": ("p.png", "r1", {"data": b"", "content_type": "image/png",
                               "model": "stub", "prompt": 'a "quoted" subject'})},
    )
    _check("a generated leaf's prompt is escaped in data-gen-prompt",
           '&quot;quoted&quot;' in hostile_prompt)

    # ── 8. THE STUB IS A HONEST DRIVER ───────────────────────────────────
    b = StubBackend()
    a1 = b.generate(prompt="p", width=64, height=64)
    a2 = b.generate(prompt="p", width=64, height=64)
    a3 = b.generate(prompt="q", width=64, height=64)
    _check("the stub is deterministic (same prompt → same bytes → CAS dedup)",
           a1["data"] == a2["data"])
    _check("…and prompt-derived (different subjects are visibly different)",
           a1["data"] != a3["data"])
    _check("…and emits a REAL png (the renderer will read these bytes)",
           a1["data"].startswith(b"\x89PNG\r\n\x1a\n"))

    # ── 9. THE GUARDS ────────────────────────────────────────────────────
    try:
        asyncio.run(ri.compose(ri.ComposeRequest(path=path, brief="  "), auth))
        _check("an empty brief is REFUSED (422)", False)
    except Exception as exc:  # noqa: BLE001
        _check("an empty brief is REFUSED (422)", getattr(exc, "status_code", 0) == 422)

    doc_path = f"{STUDIO_ARTIFACT_REGION}a-doc/document.html"
    store[doc_path] = {"path": doc_path, "content": '<html data-template="document">'}
    try:
        asyncio.run(ri.compose(ri.ComposeRequest(path=doc_path, brief="x"), auth))
        _check("composing onto a DOCUMENT is refused (geometry would be inert)", False)
    except Exception as exc:  # noqa: BLE001
        _check("composing onto a DOCUMENT is refused (geometry would be inert)",
               getattr(exc, "status_code", 0) == 422)

    try:
        asyncio.run(ri.compose(
            ri.ComposeRequest(path="/workspace/governance/x.html", brief="x"), auth))
        _check("composing outside the artifact region is refused (403)", False)
    except Exception as exc:  # noqa: BLE001
        _check("composing outside the artifact region is refused (403)",
               getattr(exc, "status_code", 0) == 403)

    # ── 9b. THE PRIVILEGED-CLIENT BOUNDARY (the 2026-07-21 live smoke) ───
    # Two writes structurally require the SERVICE client. Both were shipped
    # with the member's client, both 403'd in production, and the gate was
    # green throughout because it asserted markup shape against a fake DB.
    # These checks are the ones that would have caught it.
    binary_writes = [wr for wr in writes if wr["is_binary"]]
    _check(
        "the binary LEAF is written with the SERVICE client — a member JWT is "
        "403'd by the private workspace-cas bucket (ADR-427 D4)",
        bool(binary_writes) and all(wr["client"] is service_client for wr in binary_writes),
    )
    stage_writes = [wr for wr in writes if not wr["is_binary"]]
    _check(
        "…while the STAGE keeps the member's client (their revision, their grant)",
        bool(stage_writes) and all(wr["client"] is not service_client for wr in stage_writes),
    )

    # The ledger only fires on a COSTED call, so exercise a priced backend.
    from services.images.generate import GenerationBackend, get_backend, set_backend

    class _CostedBackend(GenerationBackend):
        name = "costed"

        def generate(self, *, prompt, width, height, cutout=False):
            return {"data": b"\x89PNG\r\n\x1a\nx", "content_type": "image/png",
                    "model": "test-engine", "prompt": prompt, "cost_usd": 0.08}

    # First establish the FREE case honestly: the stub run above generated a
    # leaf and must have ledgered nothing (zero-cost rows are noise, not
    # honesty). Asserted from the ledger as it stands, before the costed run.
    free_ledger_rows = len(ledger)

    prior_backend = get_backend()
    set_backend(_CostedBackend())
    ledger.clear()
    writes.clear()
    store[path] = {"path": path, "content": stage_html}  # reset to the scaffold
    asyncio.run(ri.compose(ri.ComposeRequest(path=path, brief="a serum bottle"), auth))
    set_backend(prior_backend)

    _check("a COSTED generation writes a ledger row (ADR-396 one meter)", len(ledger) == 1)
    _check(
        "…with the SERVICE client — execution_events is service-role-only "
        "(RLS 42501; the live smoke lost $0.16 of unrecorded spend here)",
        bool(ledger) and ledger[0]["client"] is service_client,
    )
    _check("…carrying the real per-call cost, not a token estimate",
           bool(ledger) and ledger[0].get("cost_override_usd") == 0.08)
    _check("…attributed to the principal who asked (ADR-373/445)",
           bool(ledger) and ledger[0].get("principal_id"))
    _check("a FREE (stub) generation ledgers NOTHING — zero-cost rows are noise",
           free_ledger_rows == 0)

    # Render-to-raster REMOVED (2026-07-22): the server render path (a headless
    # browser rasterizing the composition) never ran in production — the Render
    # container has no Chrome, so /images/render only ever 503'd. Export is a
    # CLIENT-SIDE fast-follow (the browser rasterizes the stage it already
    # displays); the composition stays the traceable source either way. See
    # ADR-475 §13. No server render endpoint, seam, or gate remains.

    return _summary()


def _summary() -> bool:
    passed = sum(1 for _, ok in _results if ok)
    total = len(_results)
    print(f"\n{'PASS' if passed == total else 'FAIL'}: {passed}/{total} checks")
    for label, ok in _results:
        if not ok:
            print(f"  ✗ {label}")
    return passed == total


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
