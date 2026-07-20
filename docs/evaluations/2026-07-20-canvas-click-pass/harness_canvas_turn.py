"""Canvas click pass — the first OBSERVED bound-canvas turn (ADR-471 C6, Hat B).

Live Designer engine, the REAL composed mind (Designer character + the canvas
studio posture over the REAL canvas skeleton), tools stubbed over fixtures.
Faithful tool results (no truncation — the run-0 lesson).

The ask: compose a launch visual. Observes:
  - positioning: does every authored block carry data-x/y + --y% values?
  - citation: is the product image a data-ref figure (never raw src/base64),
    pinned with data-ref-rev from the ReadFile-reported revision?
  - z: does overlap (headline over shape) carry data-z/--yz?
  - grounding: does the settled launch line land (recall, not invention)?
  - patch discipline: EditFile insertions onto the scaffold, id preservation.
"""
import asyncio, json, re, sys
from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, "/Users/macbook/yarnnn/api")

from services.studio import build_skeleton, STUDIO_LANE_MAX_TOKENS
from services.agents_registry import model_for_agent
from services.lane_runner import build_lane_conventions, lane_tools_openai, lane_tool_names
from services.model_router import route_completion

UID = "u_canvaspass"
ART_REL = "operation/launch/visual.html"
ART_FULL = f"/workspace/{ART_REL}"
IMG_FULL = "/workspace/operation/brand/product.png"

skeleton = build_skeleton("canvas", "Launch visual")
FILES = {ART_FULL: {"content": skeleton, "revision": "art-r1"},
         IMG_FULL: {"content": "", "revision": "img-r7", "binary": True}}
DECISION_NOTE = (
    "[decisions/pricing.md] Launch positioning (operator-ratified): lead with "
    "\"Start free — upgrade when it earns it.\" Never lead with cheapness. "
    "Brand accent is used sparingly; headlines lead, product shot supports."
)

class _Q:
    def __init__(self): self.path=None; self.is_like=False
    def select(self,*a,**k): return self
    def eq(self,col,val=None):
        if col=="path": self.path=val
        return self
    def like(self,*a,**k): self.is_like=True; return self
    def order(self,*a,**k): return self
    def limit(self,*a,**k): return self
    def execute(self):
        class R: data=[]
        r=R()
        if not self.is_like and self.path in FILES:
            r.data=[{"content":FILES[self.path]["content"]}]
        return r

class _Client:
    def table(self,*a,**k): return _Q()

def norm(p): return p if p.startswith("/workspace/") else f"/workspace/{p}"

def execute_stub(name, args):
    if name == "ReadFile":
        p = norm(args.get("path",""))
        f = FILES.get(p)
        if not f: return {"success": False, "error": "not_found", "path": p}
        return {"success": True, "path": p, "revision": f["revision"],
                "content": f["content"] if not f.get("binary") else "",
                **({"note": "binary image; cite by data-ref"} if f.get("binary") else {})}
    if name == "QueryKnowledge":
        return {"success": True, "results": [DECISION_NOTE]}
    if name == "SearchFiles":
        return {"success": True, "results": [
            {"path": IMG_FULL, "snippet": "(binary image — the product shot)"},
            {"path": "/workspace/decisions/pricing.md", "snippet": DECISION_NOTE}]}
    if name == "ListFiles":
        return {"success": True, "files": sorted(FILES)}
    if name == "EditFile":
        p = norm(args.get("path","")); old=args.get("old_string",""); new=args.get("new_string","")
        f = FILES.get(p)
        if not f: return {"success": False, "error": "not_found"}
        if f["content"].count(old) != 1:
            return {"success": False, "error": "old_string_not_unique_or_missing",
                    "count": f["content"].count(old)}
        f["content"] = f["content"].replace(old, new); f["revision"] = "art-r2"
        return {"success": True, "path": p, "revision": f["revision"]}
    if name == "WriteFile":
        p = norm(args.get("path",""))
        FILES.setdefault(p, {"revision": "r0"})
        FILES[p]["content"] = args.get("content",""); FILES[p]["revision"] = "art-r2"
        return {"success": True, "path": p, "revision": "art-r2", "note": "FULL REPLACE"}
    if name == "WebSearch":
        return {"success": True, "results": []}
    return {"success": False, "error": "tool_not_on_lane_surface"}

ASK = ("Compose the launch visual on this canvas: our launch line as the "
       "headline, the product shot from the brand folder, and an accent shape "
       "behind the headline. Square stage is fine.")

async def main():
    model = model_for_agent("designer")
    frame = build_lane_conventions(_Client(), UID, model=model, member_label="KVK",
                                   artifact_path=ART_REL, agent="designer")
    assert "WHO YOU ARE" in frame and "layout: canvas" in frame, "composed mind missing a limb"
    tools = lane_tools_openai(); allowed = lane_tool_names()
    print(f"model={model}  tools={len(tools)}  frame_chars={len(frame)}")

    messages=[{"role":"user","content":ASK}]; calls=[]; final=""
    for rnd in range(8):
        routed = await route_completion(model, messages, system=frame,
                                        max_tokens=STUDIO_LANE_MAX_TOKENS, tools=tools)
        if not routed.tool_calls:
            final = routed.text or ""; break
        messages.append(routed.raw_assistant_message or {"role":"assistant","content":routed.text or ""})
        for tc in routed.tool_calls:
            nm, args = tc["name"], tc["arguments"]
            res = execute_stub(nm, args) if nm in allowed else {"success":False,"error":"tool_not_on_lane_surface"}
            brief = {k:(v[:70]+"…" if isinstance(v,str) and len(v)>70 else v) for k,v in (args or {}).items()}
            calls.append((rnd+1, nm, brief, res.get("success")))
            messages.append({"role":"tool","tool_call_id":tc["id"],"content":json.dumps(res)})

    print("\n── TOOL SEQUENCE ──")
    for rnd,nm,brief,ok in calls: print(f"  r{rnd} {nm}({brief}) → {'ok' if ok else 'FAIL'}")

    art = FILES[ART_FULL]["content"]
    blocks = re.findall(r'<[a-z]+[^>]*data-block-id="([^"]+)"[^>]*>', art)
    authored = [m for m in re.finditer(r'<[a-z]+[^>]*data-block-id="(?!k1|t1)[^"]*"[^>]*>', art)]
    positioned = [m.group(0) for m in authored if 'data-x' in m.group(0) and 'data-y' in m.group(0)]
    obs = {
        "authored new blocks onto the scaffold": len(authored) > 0,
        "EVERY authored block is positioned (data-x+data-y)":
            len(authored) > 0 and len(positioned) == len(authored),
        "percent values, not px/rem (--yx:N%)":
            bool(re.search(r"--yx:\s*\d+%", art)),
        "the product image is a CITED figure (data-ref, no raw src/base64)":
            'data-ref="operation/brand/product.png"' in art
            and "base64" not in art
            and not re.search(r'src="(?!.*data-ref)http', art),
        "…pinned (data-ref-rev carries the ReadFile-reported revision)":
            'data-ref-rev="img-r7"' in art,
        "z appears where overlap was asked (accent behind headline)":
            "data-z" in art and "--yz" in art,
        "authored blocks carry stable ids (placeholders may be replaced — amended rule)":
            len(set(blocks)) == len(blocks) and len(blocks) >= 3,
        "grounded: the settled launch line is the headline (tag-tolerant)":
            re.search(r"[Ss]tart free\s*—?\s*upgrade",
                      re.sub(r"<[^>]+>", " ", art)) is not None,
        "compose discipline: ONE complete WriteFile (first composition rule)":
            sum(1 for _,n,b,_ in calls if n=="WriteFile" and "content" in b) == 1,
        "no malformed WriteFile attempts (content missing from the call)":
            not any(n=="WriteFile" and "content" not in b for _,n,b,_ in calls),
        "kernel/skin style elements intact":
            art.count("<style") == skeleton.count("<style"),
    }
    print("\n── OBSERVATIONS ──")
    for k,v in obs.items(): print(f"  {'✓' if v else '✗'} {k}")
    print(f"\n  blocks now: {blocks}")
    print("\n── HEADLINE REGION ──"); m = re.search(r"<h1.*?</h1>", art, re.S); print(m.group(0) if m else "(no h1)"); print("\n── FINAL TEXT (head) ──\n", (final or "(none)")[:400])

asyncio.run(main())
