"""ADR-475 vendor commit — the Gemini driver + the metered leaf.

EXECUTING gate (the ADR-472 lesson: gates that grep text miss function-scoped
imports and runtime NameErrors — these checks CALL the code). No network: the
HTTP layer is patched; the live smoke is a separate one-shot.

What it pins:
  1. GeminiBackend parses the REST response (inlineData → bytes + type +
     provenance + cost) and honors the per-leaf contract.
  2. The cut-out discipline is prompt-engineered (white-ground isolation);
     a plain leaf is not.
  3. Aspect mapping picks the model's nearest supported ratio.
  4. Failure shapes RAISE (non-200; 200 with no image part) — the orchestrator
     skips the leaf, never fakes it.
  5. Default resolution is env-driven: key present → gemini; forced or keyless
     → stub. set_backend still overrides (tests, future vendors).
  6. compose_stage ledgers ONE execution_events row per costed leaf
     (cost_override_usd = the rented figure); the free stub ledgers nothing.

Run:  cd api && python3 test_adr475_gemini_driver.py
Exit code is authoritative (0 = pass).
"""

from __future__ import annotations

import base64
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

_results: list[tuple[str, bool]] = []


def _check(label: str, cond: bool) -> None:
    _results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")


class _FakeResp:
    def __init__(self, status_code: int, payload: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text or str(payload)

    def json(self):
        return self._payload


def run() -> bool:
    import services.images.generate as gen
    from services.images.generate import GeminiBackend, StubBackend

    png = b"\x89PNG-fake-bytes"
    ok_payload = {
        "candidates": [
            {"content": {"parts": [
                {"text": "here you go"},
                {"inlineData": {"mimeType": "image/png", "data": base64.b64encode(png).decode()}},
            ]}}
        ]
    }

    # ── 1 + 2: parse + provenance + cutout discipline ────────────────────
    be = GeminiBackend(api_key="k", model="gemini-test-model", cost_usd=0.05)
    with patch("httpx.post", return_value=_FakeResp(200, ok_payload)) as p:
        asset = be.generate(prompt="a red bicycle", width=600, height=600, cutout=True)
    sent = p.call_args.kwargs["json"]
    sent_text = sent["contents"][0]["parts"][0]["text"]
    _check(
        "parses inlineData → bytes + content_type + model + prompt + cost",
        asset["data"] == png
        and asset["content_type"] == "image/png"
        and asset["model"] == "gemini-test-model"
        and asset["prompt"] == "a red bicycle"
        and asset["cost_usd"] == 0.05,
    )
    _check(
        "cutout is prompt-engineered (white-ground isolation, no text)",
        "white background" in sent_text and "No text" in sent_text,
    )
    with patch("httpx.post", return_value=_FakeResp(200, ok_payload)) as p2:
        be.generate(prompt="a wide banner", width=1200, height=628, cutout=False)
    plain_text = p2.call_args.kwargs["json"]["contents"][0]["parts"][0]["text"]
    _check(
        "a plain (non-cutout) leaf carries no isolation instruction",
        "white background" not in plain_text and "No text" in plain_text,
    )
    _check(
        "the request asks for IMAGE modality with an aspect hint",
        sent["generationConfig"]["responseModalities"] == ["IMAGE"]
        and sent["generationConfig"]["imageConfig"]["aspectRatio"] == "1:1"
        and p2.call_args.kwargs["json"]["generationConfig"]["imageConfig"]["aspectRatio"]
        == "16:9",
    )

    # ── 3: aspect mapping ────────────────────────────────────────────────
    _check(
        "aspect maps to the nearest supported ratio",
        be._aspect(800, 800) == "1:1"
        and be._aspect(1200, 628) == "16:9"
        and be._aspect(600, 900) == "3:4"
        and be._aspect(540, 960) == "9:16",
    )

    # ── 4: failure shapes RAISE ──────────────────────────────────────────
    raised_http = raised_empty = False
    with patch("httpx.post", return_value=_FakeResp(429, text="quota")):
        try:
            be.generate(prompt="x", width=64, height=64)
        except RuntimeError:
            raised_http = True
    with patch("httpx.post", return_value=_FakeResp(200, {"candidates": [{"content": {"parts": [{"text": "safety"}]}}]})):
        try:
            be.generate(prompt="x", width=64, height=64)
        except RuntimeError:
            raised_empty = True
    _check("non-200 raises (the orchestrator skips the leaf)", raised_http)
    _check("200 with no image part raises (safety/text-only)", raised_empty)

    # ── 5: env-driven default resolution ─────────────────────────────────
    def _resolve(env: dict) -> object:
        with patch.dict(os.environ, env, clear=False):
            for k in ("IMAGES_GENERATION_ENGINE", "GEMINI_API_KEY"):
                if k not in env:
                    os.environ.pop(k, None)
            gen._BACKEND = None
            return gen.get_backend()

    saved_engine = os.environ.get("IMAGES_GENERATION_ENGINE")
    saved_key = os.environ.get("GEMINI_API_KEY")
    try:
        got_gemini = _resolve({"GEMINI_API_KEY": "k"})
        got_forced = _resolve({"GEMINI_API_KEY": "k", "IMAGES_GENERATION_ENGINE": "stub"})
        got_keyless = _resolve({})
    finally:
        for k, v in (("IMAGES_GENERATION_ENGINE", saved_engine), ("GEMINI_API_KEY", saved_key)):
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        gen._BACKEND = None
    _check("key present → the rented driver is the default", isinstance(got_gemini, GeminiBackend))
    _check("IMAGES_GENERATION_ENGINE=stub forces the stub even with a key", isinstance(got_forced, StubBackend))
    _check("no key → the offline stub (gates stay green with no network)", isinstance(got_keyless, StubBackend))

    # ── 6: compose_stage ledgers one row per costed leaf ─────────────────
    from services.images.compose import compose_stage

    class _CostedBackend(StubBackend):
        name = "costed"

        def generate(self, *, prompt, width, height, cutout=False):
            a = super().generate(prompt=prompt, width=width, height=height, cutout=cutout)
            a["cost_usd"] = 0.08
            a["model"] = "gemini-test-model"
            return a

    layers = [
        {"role": "headline", "kind": "text", "text": "Hi", "tag": "h1"},
        {"role": "hero", "kind": "subject", "prompt": "a hero", "x": 10, "y": 10, "w": 50, "h": 40},
        {"role": "logo", "kind": "subject", "prompt": "a logo", "x": 70, "y": 70, "w": 20, "h": 20},
    ]
    stage_html = '<html><body><section class="slide"><h1>ph</h1></section></body></html>'

    gen.set_backend(_CostedBackend())
    try:
        with patch("services.authored_substrate.write_revision", return_value="rev-1"), \
             patch("services.telemetry.record_execution_event") as ledger:
            out = compose_stage(
                MagicMock(),
                user_id="u1",
                stage_path="/workspace/operation/ad/image.html",
                layers=layers,
                width=1200,
                height=628,
                authored_by="operator",
                stage_html=stage_html,
            )
        calls = ledger.call_args_list
        _check(
            "one ledger row per costed leaf (2 subjects → 2 rows, text free)",
            len(calls) == 2 and out["generated"] == 2,
        )
        _check(
            "the row carries the rented figure + model + the images slug",
            all(
                c.kwargs["cost_override_usd"] == 0.08
                and c.kwargs["model"] == "gemini-test-model"
                and c.kwargs["slug"] == "images-generate"
                and c.kwargs["mode"] == "mechanical"
                for c in calls
            ),
        )
        with patch("services.authored_substrate.write_revision", return_value="rev-1"), \
             patch("services.telemetry.record_execution_event") as ledger2:
            gen.set_backend(StubBackend())
            compose_stage(
                MagicMock(),
                user_id="u1",
                stage_path="/workspace/operation/ad/image.html",
                layers=layers,
                width=1200,
                height=628,
                authored_by="operator",
                stage_html=stage_html,
            )
        _check("the free stub ledgers nothing (zero-cost rows are noise)", ledger2.call_count == 0)
    finally:
        gen._BACKEND = None

    ok = all(c for _, c in _results)
    print()
    print(f"{'PASS' if ok else 'FAIL'}: {sum(c for _, c in _results)}/{len(_results)} checks")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
