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

    # ── 10. RENDER-TO-RASTER: the PNG is a DERIVATION, not an export ─────
    from services.images.render import RenderBackend, raster_path, set_render_backend

    class _FakeRenderer(RenderBackend):
        name = "fake"

        def __init__(self):
            self.calls = []

        def render(self, html, *, width, height):
            self.calls.append({"html": html, "width": width, "height": height})
            return b"\x89PNG\r\n\x1a\n" + b"fake"

    fake = _FakeRenderer()
    set_render_backend(fake)
    writes.clear()

    try:
        rendered = asyncio.run(ri.render(ri.RenderRequest(path=path), auth))
        _check("POST /images/render EXECUTES (no NameError in the body)", True)
    except Exception as exc:  # noqa: BLE001
        _check(f"POST /images/render EXECUTES — raised {type(exc).__name__}: {exc}", False)
        _summary()
        return False

    _check("the raster lands beside its source with a .png extension",
           rendered["path"] == raster_path(path) and rendered["path"].endswith(".png"))
    _check("…rasterized at the stage's REAL dimensions (ADR-472 D3)",
           bool(fake.calls) and fake.calls[0]["width"] == w and fake.calls[0]["height"] == h)
    _check("…and reports which engine produced it", rendered.get("engine") == "fake")

    raster = [wr for wr in writes if wr["path"].endswith(".png")]
    _check("the raster is written as BINARY (ADR-427 Category-1 substrate)",
           len(raster) == 1 and raster[0]["is_binary"])
    _check(
        "THE MOAT CLAIM: the raster is revision_kind='derivation' (ADR-423)",
        bool(raster) and raster[0].get("revision_kind") == "derivation",
    )
    _check(
        "…carrying derived_from = [the composition] (ADR-448 reference edge) — "
        "this is what lets `trace` walk an exported ad back to its source",
        bool(raster) and raster[0].get("derived_from") == [path],
    )

    # A render must never mutate the source: the composition is the SOURCE and
    # the raster a projection of it (ADR-456). A stage rewritten by its own
    # export would make the projection a second source.
    _check("rendering does NOT write the stage (no second source)",
           not any(wr["path"] == path for wr in writes))

    # 11. The unavailable-engine path answers honestly (503, not a failed write).
    class _Unavailable(RenderBackend):
        name = "none"

        def available(self):
            return False

        def render(self, html, *, width, height):
            raise AssertionError("must not be called when unavailable")

    set_render_backend(_Unavailable())
    try:
        asyncio.run(ri.render(ri.RenderRequest(path=path), auth))
        _check("an unavailable engine answers 503, not a failed write", False)
    except Exception as exc:  # noqa: BLE001
        _check("an unavailable engine answers 503, not a failed write",
               getattr(exc, "status_code", 0) == 503)

    set_render_backend(fake)
    try:
        asyncio.run(ri.render(ri.RenderRequest(path=doc_path), auth))
        _check("rendering a DOCUMENT is refused (it is not a stage)", False)
    except Exception as exc:  # noqa: BLE001
        _check("rendering a DOCUMENT is refused (it is not a stage)",
               getattr(exc, "status_code", 0) == 422)

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
