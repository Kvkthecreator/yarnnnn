"""ADR-657 — two lanes to a connection: the curated lane and the open lane.

The five §10 bullets, each DRIVEN rather than read:

  §1  the loader REFUSES an entry with no rationale / no moat-leak verdict —
      driven by writing a defective file and calling `load_curated()` on it
  §2  the two lanes CONVERGE: a curated attach and a pasted URL land the same
      `mcp:{slug}` row shape, the same empty aperture, the same ADR-577 refusal
      (the ADR-644 "compare the faces" pattern — both faces built, then diffed)
  §3  the curated keys do NOT collide with the consumed directory's
  §4  the OPEN lane still attaches an unseeded server (ADR-635 am.2's media
      path — the regression this ADR is most likely to cause)
  §5  `reviewed_at` on every entry, and a stale date is a REPORTED finding

Script-style, like `test_adr635_attached_connectors.py`, because it drives the
attach seam offline with a fake transport. Run:

    cd api && python3 -B test_adr657_two_lanes.py
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from datetime import date, timedelta

API = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(API)
sys.path.insert(0, API)

from integrations.core.tokens import TokenManager  # noqa: E402

os.environ.setdefault("INTEGRATION_ENCRYPTION_KEY", TokenManager.generate_key())
os.environ.setdefault("OAUTH_STATE_SECRET", "test-secret")
os.environ.setdefault("API_BASE_URL", "https://api.test")

_p = _f = 0


def _check(label, ok, detail=""):
    global _p, _f
    if ok:
        _p += 1
        print(f"  ok   {label}")
    else:
        _f += 1
        print(f"  FAIL {label}{(' — ' + detail) if detail else ''}")


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# The one table this seam touches, with the live NOT NULL set (mig 244).
# ---------------------------------------------------------------------------


class _Res:
    def __init__(self, data):
        self.data = data


class _Q:
    def __init__(self, store, op="select"):
        self.store, self.op, self.filters, self.payload = store, op, [], None
        self._like = None

    def select(self, *_a, **_k):
        return self

    def eq(self, col, val):
        self.filters.append((col, val))
        return self

    def like(self, col, pat):
        self._like = (col, pat.rstrip("%"))
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def insert(self, payload):
        self.op, self.payload = "insert", payload
        return self

    def update(self, payload):
        self.op, self.payload = "update", payload
        return self

    def _match(self, row):
        for col, val in self.filters:
            if row.get(col) != val:
                return False
        if self._like and not str(row.get(self._like[0], "")).startswith(self._like[1]):
            return False
        return True

    _NOT_NULL = ("user_id", "platform", "connected_by")

    def execute(self):
        if self.op == "insert":
            row = dict(self.payload)
            row.setdefault("id", f"row-{len(self.store) + 1}")
            row.setdefault("created_at", "2026-09-18T00:00:00+00:00")
            for col in self._NOT_NULL:
                if row.get(col) is None:
                    raise AssertionError(
                        f'null value in column "{col}" of relation '
                        f'"platform_connections" violates not-null constraint')
            self.store.append(row)
            return _Res([row])
        if self.op == "update":
            hit = [r for r in self.store if self._match(r)]
            for r in hit:
                r.update(self.payload)
            return _Res(hit)
        return _Res([dict(r) for r in self.store if self._match(r)])


class _Client:
    def __init__(self):
        self.rows: list[dict] = []

    def table(self, name):
        assert name == "platform_connections", name
        return _Q(self.rows)


class _Auth:
    def __init__(self, client, user_id="u1", caller_identity="member:u1 via claude-sonnet-5"):
        self.client, self.user_id, self.caller_identity = client, user_id, caller_identity
        self.workspace_id = "ws1"
        self.freddie_caller = False


from services import attached_connectors as ac  # noqa: E402
from services import connector_curated as cc  # noqa: E402
from services import connector_directory as cd  # noqa: E402

CURATED_JSON = cc.CURATED_PATH


def _fresh_curated():
    """The shipped file, re-read. The module memoizes, so every driven case
    clears the cache first — a stale cache is how a falsification goes green."""
    cc._curated_cache = None
    return cc.load_curated()


def _drive_loader(mutate) -> tuple[bool, str]:
    """Write a MUTATED copy of the shipped file, call the real loader on it,
    and restore the original in a `finally` with an equality assert. Never a
    cp backup and never `git checkout`: the original is held in a variable."""
    original = CURATED_JSON.read_text(encoding="utf-8")
    try:
        data = json.loads(original)
        mutate(data)
        CURATED_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
        cc._curated_cache = None
        try:
            cc.load_curated()
            return False, "loader accepted it"
        except ValueError as exc:
            return True, str(exc)
        except Exception as exc:  # noqa: BLE001
            # A KeyError is NOT a refusal — it is the loader falling over where
            # it was meant to speak. A gate that crashes reports nothing, so
            # this arm fails with a name rather than taking the suite with it.
            return False, f"loader crashed instead of refusing: {type(exc).__name__}: {exc}"
    finally:
        CURATED_JSON.write_text(original, encoding="utf-8")
        assert CURATED_JSON.read_text(encoding="utf-8") == original, \
            "the shipped curated file was not restored"
        cc._curated_cache = None


# ═══════════════════════════════════════════════════════════════════════════
print("§1 the loader REFUSES an entry that does not carry its verdict (driven)")
# ═══════════════════════════════════════════════════════════════════════════
_fresh_curated()
_check("1a the shipped file loads", len(cc.curated_entries()) >= 1)

ok, why = _drive_loader(lambda d: d["entries"][0].pop("rationale"))
_check("1b an entry with NO rationale is refused", ok, why)
ok, why = _drive_loader(lambda d: d["entries"][0].update({"rationale": "   "}))
_check("1c an EMPTY rationale is refused", ok, why)
ok, why = _drive_loader(lambda d: d["entries"][0].pop("accumulates"))
_check("1d an entry with NO moat-leak verdict is refused", ok, why)
ok, why = _drive_loader(lambda d: d["entries"][0].update({"accumulates": "no"}))
_check("1e a non-boolean verdict is refused", ok, why)
ok, why = _drive_loader(lambda d: d["entries"][0].update({"accumulates": True}))
_check("1f a COMPETING COMMONS (accumulates: true) is refused admission "
       "(ADR-420 §10 Amendment)", ok, why)
ok, why = _drive_loader(lambda d: d["entries"][0].pop("reviewed_at"))
_check("1g an entry with no reviewed_at is refused", ok, why)
ok, why = _drive_loader(lambda d: d.pop("admission_criterion"))
_check("1h the FILE's own provenance is required", ok, why)
ok, why = _drive_loader(lambda d: d["entries"][0].update(
    {"url_shape": "https://{a}.x/{b}", "shape_field": "a"}))
_check("1i a shape with more than one hole is refused", ok, why)
ok, why = _drive_loader(lambda d: [d["entries"][0].pop("url_shape"),
                                   d["entries"][0].pop("url", None)])
_check("1j an entry with neither url nor url_shape is refused", ok, why)

# The mirror of the seed's own discipline, asserted so the two loaders cannot
# drift apart silently: a seed with no provenance raises too.
_seed_ok = False
try:
    cd.load_seed()
    _seed_ok = True
except ValueError:
    pass
_check("1k the CONSUMED seed still loads with its provenance", _seed_ok)

# ═══════════════════════════════════════════════════════════════════════════
print("§2 D2 — the URL SHAPE: the member fills one field, not a path")
# ═══════════════════════════════════════════════════════════════════════════
shop = cc.curated_entry("shopify") or {}


def _resolved(value):
    """resolve_url, but every outcome is DATA — a raise must fail one arm with a
    name, never end the run."""
    try:
        return cc.resolve_url("shopify", value)
    except Exception as exc:  # noqa: BLE001
        return exc


_check("2a Shopify is the one curated entry (D5)",
       bool(shop) and len(cc.curated_entries()) == 1,
       str(len(cc.curated_entries())))
_check("2b its shape is the vendor's, with one hole",
       shop.get("url_shape") == "https://{store}.myshopify.com/api/mcp",
       str(shop.get("url_shape")))
_check("2c filling the one field resolves the URL",
       _resolved("acme-supply") == "https://acme-supply.myshopify.com/api/mcp",
       str(_resolved("acme-supply")))
for bad in ("", "  ", "acme/../evil", "a b"):
    _check(f"2d an unusable store name {bad!r} is refused",
           isinstance(_resolved(bad), ValueError), str(_resolved(bad)))
_check("2e the verdict and its reason ride the entry",
       shop.get("accumulates") is False and "system of record" in str(shop.get("rationale")))
_check("2f the entry says the merchant capability is a COMMUNITY server that "
       "holds the token, and that the aperture is where they decide (D5)",
       all(s in str(shop.get("credential_note")).lower()
           for s in ("community", "token", "aperture")), str(shop.get("credential_note")))
_check("2g the category is pre-filled, so a needs-scoped skill can light up "
       "(b21c060's debt)", shop.get("category") == "Commerce")

# ═══════════════════════════════════════════════════════════════════════════
print("§3 the two lanes CONVERGE on one row shape (compare the faces)")
# ═══════════════════════════════════════════════════════════════════════════


class _Resp:
    def __init__(self, status, json_=None, headers=None, text=""):
        self.status_code, self._json, self.headers, self.text = status, json_, headers or {}, text

    def json(self):
        if self._json is None:
            raise ValueError("no json")
        return self._json


class _FakeHTTP:
    """Every server here answers anonymously, so both lanes complete inside the
    process and the two rows can actually be compared."""

    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, **k):
        return _Resp(200, {"result": {}})

    async def get(self, url, **k):
        return _Resp(404)


ac.httpx.AsyncClient = _FakeHTTP  # type: ignore[attr-defined]


async def _fake_list(server_url, envelope):
    return [{"name": "read_orders", "description": "", "inputSchema": {},
             "annotations": {"readOnlyHint": True}}]


ac.list_tools = _fake_list  # type: ignore[assignment]


async def _attach_via_route(auth, **body):
    """Drive the ROUTE, not a hand-rolled copy of it — the curated pre-fill
    lives in the route, so a gate that called `begin_attach` directly would be
    green with the pre-fill deleted."""
    from routes.attached_connectors import AttachRequest, attach as route_attach

    return await route_attach(AttachRequest(**body), auth)


def _attached(client, **body):
    """Both faces, built the same way. A route raise becomes DATA so one broken
    lane fails its own arms instead of ending the comparison."""
    try:
        res = _run(_attach_via_route(_Auth(client), **body))
    except Exception as exc:  # noqa: BLE001
        return {}, f"{type(exc).__name__}: {exc}"
    row = ac.load_row(client, "u1", res["slug"]) or {}
    return row, res


curated_client, open_client = _Client(), _Client()
crow, curated_res = _attached(
    curated_client, curated_key="shopify", shape_value="acme-supply",
    header_name="X-Shopify-Access-Token", header_value="shpat_x",
    redirect_to="/reach/connected")
orow, open_res = _attached(
    open_client, url="https://mcp.higgsfield.example/mcp",
    category="Media generation", redirect_to="/reach/connected")

_check("3a the curated attach lands mcp:{slug} on the same table",
       crow.get("platform") == "mcp:shopify", str(curated_res))
_check("3b the open attach lands mcp:{slug} on the same table",
       str(orow.get("platform")).startswith("mcp:"), str(open_res))
_check("3c the ROW SHAPE is identical — same columns, no curated-only field",
       bool(crow) and set(crow.keys()) == set(orow.keys()),
       str(set(crow.keys()) ^ set(orow.keys())))
_check("3d the METADATA shape is identical",
       bool(crow) and set(crow.get("metadata", {}).keys()) == set(orow.get("metadata", {}).keys()),
       str(set(crow.get("metadata", {}).keys()) ^ set(orow.get("metadata", {}).keys())))
_check("3e BOTH open with an EMPTY aperture — curation grants nothing",
       crow.get("metadata", {}).get("aperture") == {}
       and orow.get("metadata", {}).get("aperture") == {})
_check("3f neither row carries a verdict, a rationale or a curated flag — "
       "curation is DISCOVERY, it does not ride the authority row",
       bool(crow) and not any(k in json.dumps(crow)
                              for k in ("accumulates", "rationale", "curated")),
       json.dumps(crow)[:200])
_check("3g the curated URL is the SHAPE, filled",
       crow.get("metadata", {}).get("server_url") == "https://acme-supply.myshopify.com/api/mcp",
       str(crow.get("metadata", {}).get("server_url")))
_check("3h the curated row's CATEGORY is pre-filled by the entry, never null",
       crow.get("metadata", {}).get("category") == "Commerce",
       str(crow.get("metadata", {}).get("category")))

# ADR-577 — the SAME refusal on both lanes. Driven through the route.
class _AgentAuth(_Auth):
    def __init__(self, client):
        super().__init__(client, caller_identity="agent:analyst via claude-sonnet-5")


from fastapi import HTTPException  # noqa: E402


def _refused(**body):
    try:
        _run(_attach_via_route(_AgentAuth(_Client()), **body))
        return False
    except HTTPException as exc:
        return exc.status_code == 403 and "agent" in str(exc.detail).lower()
    except PermissionError:
        return True
    except Exception:  # noqa: BLE001 — any other raise is not a refusal
        return False


_check("3i ADR-577 refuses an AGENT caller on the curated lane",
       _refused(curated_key="shopify", shape_value="acme"))
_check("3j ADR-577 refuses an AGENT caller on the open lane",
       _refused(url="https://mcp.example.test/mcp"))

# ═══════════════════════════════════════════════════════════════════════════
print("§4 the curated keys do NOT collide with the consumed directory's")
# ═══════════════════════════════════════════════════════════════════════════
seed_keys = {e["key"] for e in cd.seed_entries()}
curated_keys = {e["key"] for e in cc.curated_entries()}
_check("4a no key appears in both lanes", not (seed_keys & curated_keys),
       str(seed_keys & curated_keys))
seed_hosts = {cd._host(e["url"]) for e in cd.seed_entries()}
curated_hosts = set()
for e in cc.curated_entries():
    u = e.get("url") or (e.get("url_shape") or "").replace(
        "{" + (e.get("shape_field") or "") + "}", "x")
    curated_hosts.add(cd._host(u))
_check("4b no HOST appears in both lanes either — a renamed key cannot hide a "
       "collision", not (seed_hosts & curated_hosts), str(seed_hosts & curated_hosts))
_check("4c the curated file is NOT the derived seed, and does not touch it",
       cc.CURATED_PATH != cd.SEED_PATH and "connector_curated" in cc.CURATED_PATH.name)
seed_src = (cc.CURATED_PATH.parent / "connector_directory.py").read_text(encoding="utf-8")
_check("4d the consumed directory does not import the curated lane — the seed "
       "stays derived, unmerged", "connector_curated" not in seed_src)

# ═══════════════════════════════════════════════════════════════════════════
print("§5 D4 — the OPEN lane still attaches an unseeded server, and SAYS what it is")
# ═══════════════════════════════════════════════════════════════════════════
media_client = _Client()
mrow, media_res = _attached(media_client, url="https://mcp.unseeded-vendor.example/mcp",
                            category="Media generation")
_check("5a an UNSEEDED server still attaches (ADR-635 am.2's media path)",
       bool(mrow) and isinstance(media_res, dict) and media_res.get("attached") is True,
       str(media_res))
_check("5b it is not in the consumed seed, and not curated",
       cd.seed_entry_for_url("https://mcp.unseeded-vendor.example/mcp") is None
       and cc.curated_entry(str(mrow.get("platform", "")).removeprefix("mcp:")) is None)
_check("5c the member's typed category still rides (b21c060 survives)",
       mrow.get("metadata", {}).get("category") == "Media generation")

MODAL = os.path.join(ROOT, "web/components/settings/FindConnectorModal.tsx")
modal_src = open(MODAL, encoding="utf-8").read()
# Comments carry every one of these words, so a substring check against the raw
# file would pass with the whole feature deleted. Strip them first, then count
# the CALLS at the deciding site.
modal_code = re.sub(r"/\*[\s\S]*?\*/", "", modal_src)
modal_code = re.sub(r"^\s*//.*$", "", modal_code, flags=re.M)

# The wiring is not the door. A falsification that set `type="hidden"` and blanked
# the placeholder left every one of these symbols intact and the box untypeable, and
# this check stayed green — so it also asserts the input a member can SEE and TYPE in.
def _paste_class(m) -> str:
    """The paste box's className, or "" when it carries none. A tag with no
    className is not hidden; a tag whose className says `hidden` is."""
    if not m:
        return ""
    found = re.search(r'className="([^"]*)"', m.group(0))
    return found.group(1) if found else ""


_pi = re.search(r"<input\b(?:(?!/>).)*value=\{pasteUrl\}(?:(?!/>).)*/>", modal_code, re.S)
_paste_input = _pi
_check("5d the paste-a-URL form still exists in CODE (deleting it is the "
       "regression this ADR is most likely to cause)",
       modal_code.count("setPasteUrl(") >= 2 and "pastedEntry(pasted)" in modal_code)
_check("5d-ii the paste box is a VISIBLE, typable url input bound to pasteUrl — "
       "wiring alone is not a door",
       bool(_paste_input)
       and 'type="url"' in _paste_input.group(0)
       and "onChange" in _paste_input.group(0)
       and 'type="hidden"' not in _paste_input.group(0)
       and "hidden" not in _paste_class(_paste_input))
_check("5e the open lane SAYS yarnnn has not examined the server",
       "has not examined this server" in modal_code
       and modal_code.count("OPEN_LANE_CAVEAT") >= 2,
       str(modal_code.count("OPEN_LANE_CAVEAT")))
_check("5f the open lane says it cannot say where the work will accumulate",
       "accumulate" in modal_code)
# The fetch and the render are counted SEPARATELY, at the deciding site in each
# case: a `.curated()` fetch whose result nothing renders is a green gate over a
# lane no member can see, and an `onClick` with no fetch renders an empty lane.
_fetches = len(re.findall(r"\.curated\(\)", modal_code))
_renders = len(re.findall(r"onClick=\{\(\) => pickCurated\(", modal_code))
_maps = len(re.findall(r"curated\.map\(", modal_code))
_check("5g the curated lane is FETCHED, MAPPED and clickable (not just imported)",
       _fetches >= 1 and _renders >= 1 and _maps >= 1,
       f"fetch={_fetches} click={_renders} map={_maps}")
_check("5h the curated attach drives curated_key, never a client-built URL",
       "curated_key: entry.key" in modal_code and "shape_value:" in modal_code)
_check("5i the credential note and the verdict's reason are rendered",
       "credential_note" in modal_code and "rationale" in modal_code)

# ═══════════════════════════════════════════════════════════════════════════
print("§6 D3 — reviewed_at on every entry, and a stale date is a FINDING")
# ═══════════════════════════════════════════════════════════════════════════
_check("6a every entry carries reviewed_at",
       all(e.get("reviewed_at") for e in cc.curated_entries()))
_check("6b nothing is stale today", cc.stale_entries() == [], str(cc.stale_entries()))
future = date.today() + timedelta(days=cc.REVIEW_INTERVAL_DAYS + 30)
stale = cc.stale_entries(today=future)
_check("6c a date past the review interval IS reported, with its key and age",
       len(stale) == 1 and stale[0]["key"] == "shopify" and stale[0]["days"] > cc.REVIEW_INTERVAL_DAYS,
       str(stale))
_check("6d the lane is small by construction (D3) — one entry, and growth is "
       "demand-gated", len(cc.curated_entries()) <= 5, str(len(cc.curated_entries())))

# The list is an authored list; if it ever gets long the ADR says so itself.
if cc.stale_entries():
    print(f"  FINDING: curated entries not examined in {cc.REVIEW_INTERVAL_DAYS} days: "
          f"{cc.stale_entries()}")

print()
print(f"ADR-657: {_p} passed, {_f} failed")
sys.exit(1 if _f else 0)
