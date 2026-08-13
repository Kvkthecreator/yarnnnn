"""ADR-568 — the capability resolver, and image generation from chat. The ratchet.

Run: python3 test_adr568_capability_resolver.py   (from api/)

Carries §8's falsifiers verbatim. Each one names the failure that motivated it:

  D1 RESOLVER    — generation is a CAPABILITY the kernel serves, not a vendor
     welded into a primitive. Before ADR-463 the same defect in search meant
     "give Scout web search" silently made Gemini call Claude.

  D2 HONESTY     — the price came from an env-var guess ($0.08) and a missing
     key produced a placeholder PNG on a SUCCESSFUL call. Both are invisible
     failures: the first leaks margin, the second surfaces only at the glass.

  D3 CEILING     — `GenerateImage` is CONSEQUENTIAL. The ADR-467 D4.a subset
     check is restated, never satisfied by smuggling a spending verb into
     READ_ONLY_PRIMITIVES.
"""

from __future__ import annotations

import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

FAILS: list[str] = []
N = 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global N
    N += 1
    if cond:
        print(f"  ok   {label}")
    else:
        FAILS.append(label)
        print(f"  FAIL {label}" + (f"\n         {detail}" if detail else ""))


from services.capabilities import (  # noqa: E402
    GenerationUnavailable,
    generation_availability,
    generation_server,
    serve_generation,
)
from services.lane_runner import (  # noqa: E402
    LANE_ARTIFACT_VERBS,
    LANE_SURFACE_EXTRA,
    lane_tool_names,
    lane_tools_openai,
)
from services.primitives.permission import READ_ONLY_PRIMITIVES  # noqa: E402
from services.telemetry import image_generation_cost_usd  # noqa: E402

_SAVED = {k: os.environ.get(k)
          for k in ("IMAGES_GENERATION_ENGINE", "GEMINI_API_KEY", "IMAGES_GENERATION_MODEL")}


def _env(**kw) -> None:
    for k, v in kw.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


try:
    print("1. D1 — generation is a kernel-resolved capability")

    _env(IMAGES_GENERATION_ENGINE=None, GEMINI_API_KEY="probe-key", IMAGES_GENERATION_MODEL=None)
    check("the default server is gemini", generation_server() == "gemini",
          generation_server())

    # THE FALSIFIER THAT MATTERS: an unknown server must be LOUD. Silently
    # stubbing would let a deployment believe it had switched vendors while
    # every image came back a placeholder.
    _env(IMAGES_GENERATION_ENGINE="bogus")
    raised = False
    try:
        serve_generation()
    except ValueError as exc:
        raised = "IMAGES_GENERATION_ENGINE" in str(exc)
    except Exception:
        pass
    check("an unknown server RAISES, naming the env var", raised,
          "a silent stub here is the whole defect this resolver prevents")

    # The stub is reachable only by EXPLICIT selection — never as a fallback.
    _env(IMAGES_GENERATION_ENGINE="stub")
    from services.apps.images.generate import StubBackend

    check("stub is reachable when explicitly named",
          isinstance(serve_generation(), StubBackend))

    print("\n2. D2.a — the price comes from a table, not a guess")

    check("gemini-2.5-flash-image is priced",
          image_generation_cost_usd("gemini-2.5-flash-image") is not None)
    check("an unknown generation model is UNPRICED (None, not a default)",
          image_generation_cost_usd("no-such-image-model") is None,
          "a plausible default is worse than an honest absence (ADR-548)")

    # The env override is DELETED — it was the promo-rate hazard by another name.
    # ⚠️ Parsed with `ast`, not grepped: a source grep cannot tell CODE from a
    # COMMENT, and this suite has been bitten by an assertion matching its own
    # explanatory prose. Only a real string LITERAL in the parsed tree counts.
    import ast

    gen_tree = ast.parse(pathlib.Path("services/apps/images/generate.py").read_text())
    literals = {n.value for n in ast.walk(gen_tree)
                if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    check("no per-image cost env var survives in the driver's CODE",
          not any("COST_USD" in s for s in literals),
          "an env-var price nobody re-reads is how a table silently rots")

    print("\n3. D2.b — a missing key REFUSES; it never placeholders")

    _env(IMAGES_GENERATION_ENGINE=None, GEMINI_API_KEY=None)
    ok, why = generation_availability()
    check("no key → unavailable, reason no_provider_key",
          not ok and why == "no_provider_key", f"got {ok}/{why}")

    refused = False
    try:
        serve_generation()
    except GenerationUnavailable as exc:
        refused = exc.reason == "no_provider_key"
    check("...and serve_generation RAISES rather than returning a stub", refused,
          "returning StubBackend here is the pre-568 defect: success on a placeholder")

    # An unpriced model darkens the engine the same way a missing key does.
    _env(GEMINI_API_KEY="probe-key", IMAGES_GENERATION_MODEL="no-such-image-model")
    ok, why = generation_availability()
    check("an unpriced model darkens the engine (reason unpriced)",
          not ok and why == "unpriced", f"got {ok}/{why}")

    _env(IMAGES_GENERATION_MODEL=None)
    ok, why = generation_availability()
    check("with a key and a price, generation is available", ok and why is None,
          f"got {ok}/{why}")

    print("\n4. D3 — the surface, and the RESTATED D4.a ceiling")

    check("GenerateImage is on the lane surface", "GenerateImage" in lane_tool_names())
    check("...and carries a schema in the declared payload",
          "GenerateImage" in [t["function"]["name"] for t in lane_tools_openai()])
    check("...and is an ARTIFACT verb (the member sees what was made)",
          "GenerateImage" in LANE_ARTIFACT_VERBS)

    # ⚠️ THE ONE THAT MATTERS. A spending, revision-landing verb must NOT be in
    # the read-only set. Putting it there would make the old subset assertion
    # pass while removing the primitive from the ADR-307 gate — defeating a
    # gate in order to pass it.
    check("GenerateImage is NOT read-only (it still passes the ADR-307 gate)",
          "GenerateImage" not in READ_ONLY_PRIMITIVES,
          "smuggling it into READ_ONLY_PRIMITIVES silences the permission gate")

    # The restated ceiling: classified, not merely read-only.
    for _t in LANE_SURFACE_EXTRA:
        check(f"surface extra {_t!r} is classified (read OR artifact verb)",
              _t in READ_ONLY_PRIMITIVES or _t in LANE_ARTIFACT_VERBS)

    print("\n5. cross-vendor composition — the product point")

    # A lane pinned to a NON-Gemini engine still reaches a Gemini-served
    # generator. If this ever couples, D1 is wrong.
    from services.lane_runner import LANE_MODELS

    _env(GEMINI_API_KEY="probe-key")
    non_gemini = [m for m in LANE_MODELS if not m.startswith("gemini/")]
    check("the roster has non-Gemini engines to compose from", bool(non_gemini))
    check("the generation server is independent of any lane engine",
          generation_server() == "gemini" and "gemini/" not in generation_server(),
          "the caller must never learn who served (ADR-463 D2)")

    cap_src = pathlib.Path("services/capabilities.py").read_text()
    check("serve_generation takes no model/engine argument from the caller",
          "def serve_generation():" in cap_src,
          "a caller-supplied engine would re-weld the vendor to the call site")

    print("\n6. the write actually LANDS — driven, not inspected")

    # ⚠️ THE SHAPE THAT SHIPPED BROKEN. Sections 1-5 were all green while every
    # chat-initiated generation 403'd: they read the resolver and the surface,
    # and never DROVE the write. Image bytes always take the BINARY lane (a PNG
    # never utf-8-decodes), and that lane uploads to the private `workspace-cas`
    # bucket, which carries NO storage.objects policy by design (migration 219 —
    # "service-role only"). The lane hands primitives the MEMBER's JWT client
    # (ADR-467), so passing it through reached the bucket as `authenticated` and
    # came back 42501, AFTER the vendor had already been paid.
    #
    # Asserted by EXECUTION with the seams stubbed, so it fails if a future edit
    # reverts the swap — a source grep for "service" would pass on a comment.
    import asyncio
    import types

    import services.authored_substrate as _AS
    import services.capabilities as _CAP
    import services.supabase as _SB
    import services.telemetry as _TEL

    _seen: dict = {}
    _SERVICE, _JWT = object(), object()
    _saved = (_AS.write_revision, _TEL.record_execution_event, _SB.get_service_client,
              _CAP.serve_generation)

    class _FakeBackend:
        def generate(self, *, prompt, width, height):
            # NUL byte -> genuinely undecodable, i.e. the real binary lane.
            return {"data": b"\x89PNG\r\n\x1a\n\x00\xff", "content_type": "image/png",
                    "model": "gemini-2.5-flash-image"}

    def _fake_write(db_client, **kw):
        _seen["write_client"] = db_client
        _seen["authored_by"] = kw.get("authored_by")
        _seen["path"] = kw.get("path")
        return "rev-probe"

    def _fake_record(client, **kw):
        _seen["ledger_client"] = client
        _seen["cost"] = kw.get("cost_override_usd")
        _seen["principal_id"] = kw.get("principal_id")
        return "evt-probe"

    try:
        _AS.write_revision = _fake_write
        _TEL.record_execution_event = _fake_record
        _SB.get_service_client = lambda: _SERVICE
        _CAP.serve_generation = lambda: _FakeBackend()

        from services.primitives.generate_image import handle_generate_image

        _auth = types.SimpleNamespace(
            client=_JWT, user_id="u-probe", principal_id="p-probe",
            workspace_id="ws-probe",
        )
        _res = asyncio.get_event_loop().run_until_complete(
            handle_generate_image(_auth, {"prompt": "a red bicycle",
                                          "filename": "red-bicycle"})
        )

        check("the binary write uses the SERVICE client, never the member JWT",
              _seen.get("write_client") is _SERVICE
              and _seen.get("write_client") is not _JWT,
              "the workspace-cas bucket 403s an `authenticated` principal (mig 219)")
        check("...and attribution still reads as the MEMBER",
              _seen.get("authored_by") == "member:u-probe",
              "the service client is a reach mechanism, never an attribution one")
        check("the rented call is METERED before the write can fail",
              bool(_seen.get("cost")),
              "an unrecorded rented call is unbilled spend (ADR-396 one-meter)")
        check("spend attributes to the asking principal",
              _seen.get("principal_id") == "p-probe")
        check("the call reports success with a revision id",
              _res.get("success") and _res.get("revision_id") == "rev-probe")
    finally:
        (_AS.write_revision, _TEL.record_execution_event, _SB.get_service_client,
         _CAP.serve_generation) = _saved

finally:
    for k, v in _SAVED.items():
        _env(**{k: v})

print()
if FAILS:
    print(f"{N - len(FAILS)}/{N} checks passed")
    print("FAILURES:")
    for f in FAILS:
        print(f"  - {f}")
    sys.exit(1)
print(f"{N}/{N} checks passed")
print("ADR-568 gate GREEN")
