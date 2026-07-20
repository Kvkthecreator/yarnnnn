"""Designer click pass — the first OBSERVED bound-Studio turn (Hat B, worksheet step 4).

The model is LIVE (Designer's real engine via the router); the frame is the REAL
composed mind (build_lane_conventions: Designer character + studio posture over
the REAL deck skeleton); tools execute against an in-memory fixture store — no
DB, no metering, no workspace touched.

The ask exercises the whole job at once:
  - grounding: "check what the workspace knows about pricing first"
    → does Designer reach for QueryKnowledge (newly uniform, ADR-467 D4)?
  - patch discipline: a one-headline change → EditFile, not WriteFile?
  - co-editing truth: does it ReadFile before editing (posture: re-read first)?
  - preservation: data-block-id + measures (data-x/y, style --yx/--yy) + the
    style elements must survive the edit untouched.
"""
import asyncio, json, re, sys
from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, "/Users/macbook/yarnnn/api")

from services.studio import build_skeleton
from services.agents_registry import model_for_agent
from services.lane_runner import build_lane_conventions, lane_tools_openai, lane_tool_names
from services.model_router import route_completion

UID = "u_clickpass"
ART_REL = "operation/q3-pricing/deck.html"
ART_FULL = f"/workspace/{ART_REL}"

# ── Fixture: the REAL skeleton + a positioned, member-authored headline ──────
skeleton = build_skeleton("deck", "Q3 Pricing Update")
skeleton = skeleton.replace(
    '<h2 data-block="heading" data-block-id="t2">First point</h2>',
    '<h2 data-block="heading" data-block-id="t2" data-x="6" data-y="4" '
    'style="--yx:6rem;--yy:4rem">Our new pricing is cheaper than before '
    'and has several tiers for different kinds of users</h2>',
)
FILES = {ART_FULL: skeleton}
DECISION_NOTE = (
    "[decisions/pricing.md] Pricing decision (ADR-396, ratified 2026-07-01): "
    "three tiers — Free $0 / Starter $19/mo / Pro $49/mo, metered balance "
    "underneath. Positioning line, operator-ratified: lead with "
    "\"Start free — upgrade when it earns it.\" Never lead with cheapness."
)

# ── Stub supabase client: serves the fixture artifact, empty everything else ──
class _Q:
    def __init__(self):
        self.path = None
        self.is_like = False
    def select(self, *a, **k): return self
    def eq(self, col, val=None):
        if col == "path":
            self.path = val
        return self
    def like(self, *a, **k):
        self.is_like = True
        return self
    def order(self, *a, **k): return self
    def limit(self, *a, **k): return self
    def execute(self):
        class R: data = []
        r = R()
        if not self.is_like and self.path in FILES:
            r.data = [{"content": FILES[self.path]}]
        return r

class _Client:
    def table(self, *a, **k): return _Q()

# ── Stub tool executor over the fixture store ────────────────────────────────
def norm(p):
    return p if p.startswith("/workspace/") else f"/workspace/{p}"

def execute_stub(name, args):
    if name == "ReadFile":
        p = norm(args.get("path", ""))
        return {"success": p in FILES, "path": p,
                "content": FILES.get(p, ""), **({} if p in FILES else {"error": "not_found"})}
    if name == "QueryKnowledge":
        return {"success": True, "results": [DECISION_NOTE]}
    if name == "SearchFiles":
        return {"success": True, "results": [
            {"path": "/workspace/decisions/pricing.md", "snippet": DECISION_NOTE}]}
    if name == "ListFiles":
        return {"success": True, "files": sorted(FILES)}
    if name == "EditFile":
        p = norm(args.get("path", ""))
        old, new = args.get("old_string", ""), args.get("new_string", "")
        if p not in FILES:
            return {"success": False, "error": "not_found"}
        if FILES[p].count(old) != 1:
            return {"success": False, "error": "old_string_not_unique_or_missing",
                    "count": FILES[p].count(old)}
        FILES[p] = FILES[p].replace(old, new)
        return {"success": True, "path": p, "revision": "r2"}
    if name == "WriteFile":
        p = norm(args.get("path", ""))
        FILES[p] = args.get("content", "")
        return {"success": True, "path": p, "revision": "r2", "note": "FULL REPLACE"}
    if name == "WebSearch":
        return {"success": True, "results": []}
    return {"success": False, "error": "tool_not_on_lane_surface"}

ASK = ("On the second slide, tighten the headline so it lands our pricing "
       "decision — check what the workspace already knows about pricing "
       "before you write.")

async def main():
    model = model_for_agent("designer")
    frame = build_lane_conventions(
        _Client(), UID, model=model, member_label="KVK",
        artifact_path=ART_REL, agent="designer",
    )
    tools = lane_tools_openai()
    allowed = lane_tool_names()
    print(f"model={model}  tools={len(tools)}  frame_chars={len(frame)}")
    assert "WHO YOU ARE" in frame and "Studio: you are authoring one artifact" in frame, \
        "composed mind missing a limb"

    messages = [{"role": "user", "content": ASK}]
    calls = []
    final_text = ""
    for rnd in range(6):
        routed = await route_completion(
            model, messages, system=frame, max_tokens=2048, tools=tools)
        if not routed.tool_calls:
            final_text = routed.text or ""
            break
        messages.append(routed.raw_assistant_message
                        or {"role": "assistant", "content": routed.text or ""})
        for tc in routed.tool_calls:
            nm, args = tc["name"], tc["arguments"]
            res = execute_stub(nm, args) if nm in allowed else {
                "success": False, "error": "tool_not_on_lane_surface"}
            calls.append((rnd + 1, nm, args if nm != "WriteFile" else {"path": args.get("path"), "content": f"<{len(args.get('content',''))} chars>"}, res.get("success")))
            # The REAL lane does NOT truncate tool results (_stringify_tool_result
            # is a plain json.dumps) — the first harness run capped at 6000 and
            # corrupted the read mid-stylesheet; the model rationally spun on
            # SearchFiles hunting content it couldn't see. Faithful now.
            messages.append({"role": "tool", "tool_call_id": tc["id"],
                             "content": json.dumps(res)})

    print("\n── TOOL SEQUENCE ──")
    for rnd, nm, args, ok in calls:
        brief = {k: (v[:80] + "…" if isinstance(v, str) and len(v) > 80 else v)
                 for k, v in (args or {}).items()}
        print(f"  r{rnd} {nm}({brief}) → {'ok' if ok else 'FAIL'}")

    art = FILES[ART_FULL]
    obs = {
        "grounded_first (QueryKnowledge/SearchFiles before any edit)":
            any(n in ("QueryKnowledge", "SearchFiles") for _, n, _, _ in calls)
            and (min((i for i, (_, n, _, _) in enumerate(calls) if n in ("QueryKnowledge", "SearchFiles")), default=99)
                 < min((i for i, (_, n, _, _) in enumerate(calls) if n in ("EditFile", "WriteFile")), default=98)),
        "re-read before editing (ReadFile precedes the edit)":
            min((i for i, (_, n, _, _) in enumerate(calls) if n == "ReadFile"), default=99)
            < min((i for i, (_, n, _, _) in enumerate(calls) if n in ("EditFile", "WriteFile")), default=98),
        "PATCHED not rewrote (EditFile, zero WriteFile)":
            any(n == "EditFile" for _, n, _, _ in calls)
            and not any(n == "WriteFile" for _, n, _, _ in calls),
        "block id t2 preserved": 'data-block-id="t2"' in art,
        "measures preserved (data-x/y + --yx/--yy exact)":
            'data-x="6" data-y="4"' in art and "--yx:6rem;--yy:4rem" in art,
        "style elements untouched": art.count("<style") == skeleton.count("<style"),
        "headline actually changed": "cheaper than before" not in art,
        "recalled positioning landed (start free / earns it)":
            bool(re.search(r"[Ss]tart free", art)),
    }
    print("\n── OBSERVATIONS ──")
    for k, v in obs.items():
        print(f"  {'✓' if v else '✗'} {k}")
    print("\n── NEW HEADLINE ──")
    m = re.search(r'data-block-id="t2"[^>]*>(.*?)</h2>', art, re.S)
    print(" ", (m.group(1).strip() if m else "(t2 not found!)"))
    print("\n── FINAL TEXT (head) ──\n", (final_text or "(none)")[:500])

asyncio.run(main())
