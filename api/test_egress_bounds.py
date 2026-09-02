"""Egress bounds — the read path must not bill bytes nobody reads.

WHY THIS GATE EXISTS. On 2026-08-31 a single operator, sole user of the
service, moved 5.7GB of Supabase egress in one day against a 165MB database —
the whole database ~35x over — and tripped the project's quota, taking
production down (402 exceed_egress_quota, REST and auth both). The daily
curve was flat-then-spike, which is what named the cause: not a steady leak,
but a per-turn multiplier on the vision path shipped that same day.

THE MECHANISM. `create_signed_url` POSTs to /object/sign and returns a NEW JWT
in the query string on every call, so two mints of the same blob are two
different URLs. Anything that caches by URL — a browser, or a model provider
fetching an `image_url` part — sees the second as an object it has never met
and downloads the bytes again. ADR-623's history replay re-mints every image
on EVERY turn (correctly: a stored URL would rot), so an image in a ten-turn
conversation was fetched ten times.

Three checks, each falsified against the real pre-fix code.
"""
import re, sys, pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent))
ROOT = pathlib.Path(__file__).parent
passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"PASS  {name}")
    else:
        failed += 1
        print(f"FAIL  {name}  {detail}")


# ── 1. A repeat mint of the same capability reuses one URL ────────────────
import services.storage_backend as sb

calls = {"n": 0}


class _Storage:
    def create_signed_url(self, key, expires_in, opts=None):
        calls["n"] += 1
        return {"signedURL": f"https://x/{key}?token=JWT{calls['n']}"}


class _Table:
    def select(self, *a, **k): return self
    def eq(self, *a, **k): return self
    def limit(self, *a, **k): return self
    def execute(self): return type("R", (), {"data": [{"storage_key": "cas/ab/abcdef"}]})()


class _DB:
    storage = type("S", (), {"from_": lambda self, b: _Storage()})()
    def table(self, n): return _Table()


backend = sb.PostgresObjectStoreBackend(_DB())
sb._MINT_CACHE.clear()
urls = [backend.mint_serving_url("abcdef") for _ in range(10)]
check(
    "ten turns replaying one image sign it ONCE and share one URL",
    calls["n"] == 1 and len(set(urls)) == 1,
    f"signs={calls['n']} distinct={len(set(urls))}",
)

# Falsifier: with reuse disabled the pre-fix behaviour must return, or this
# check is passing for a reason other than the fix.
sb._MINT_CACHE.clear(); calls["n"] = 0
_saved, sb._MINT_REUSE_S = sb._MINT_REUSE_S, 0.0
urls_off = [backend.mint_serving_url("abcdef") for _ in range(10)]
sb._MINT_REUSE_S = _saved
check(
    "falsifier: reuse OFF reproduces ten signs / ten URLs",
    calls["n"] == 10 and len(set(urls_off)) == 10,
    f"signs={calls['n']} distinct={len(set(urls_off))}",
)

# The viewing URL and the SAVING URL are different capabilities (ADR-621) and
# must never collide in the cache.
sb._MINT_CACHE.clear()
check(
    "the download form is keyed apart from the inline form",
    sb._mint_cache_get(("cas/ab/abcdef", 3600, None)) is None
    and (sb._mint_cache_put(("cas/ab/abcdef", 3600, None), "u1") or True)
    and sb._mint_cache_get(("cas/ab/abcdef", 3600, "f.png")) is None,
)

# The cache holds capabilities, so it must stay bounded and in-process.
sb._MINT_CACHE.clear()
for i in range(sb._MINT_CACHE_MAX + 100):
    sb._mint_cache_put((f"k{i}", 3600, None), f"u{i}")
check(
    "the mint cache is bounded",
    len(sb._MINT_CACHE) <= sb._MINT_CACHE_MAX,
    f"size={len(sb._MINT_CACHE)}",
)

# ── 2. Counting must not fetch bodies ─────────────────────────────────────
# `select("*", count="exact")` ships every matching row's full content — for
# workspace_files that is the file bodies — to produce an integer.
for rel in ("routes/account.py", "services/workspace_purge.py"):
    src = (ROOT / rel).read_text()
    check(
        f"{rel}: no count-only select(\"*\")",
        'select("*", count="exact")' not in src,
        "a head-count must select a narrow column",
    )

# ── 3. Hidden tabs must not poll ──────────────────────────────────────────
WEB = ROOT.parent / "web"
POLLERS = [
    "app/(authenticated)/files/page.tsx",
    "components/workspace/RecentsView.tsx",
    "components/workspace/RecentlyAuthored.tsx",
    "components/chat-surface/LanePanel.tsx",
]
for rel in POLLERS:
    src = (WEB / rel).read_text()
    # Every setInterval callback in these files must consult visibilityState.
    bodies = re.findall(r"setInterval\(\s*\(\s*\)\s*=>\s*\{(.*?)\}\s*,", src, re.DOTALL)
    bare = re.findall(r"setInterval\(\s*(\w+)\s*,", src)
    check(
        f"{rel}: the poll is visibility-gated",
        bool(bodies) and all("visibilityState" in b for b in bodies) and not bare,
        f"bare-callback intervals={bare}",
    )

print("=" * 62)
print(f"egress bounds gate: {passed}/{passed + failed} passed, {failed} failed")
sys.exit(1 if failed else 0)
