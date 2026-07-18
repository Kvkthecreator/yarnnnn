"""
PROBE (Hat-B) — the APPLY GAP, measured, not predicted.

DESIGN-SYSTEMS.md §5 parks the open question: a correct apply can land 5.7KB of
valid CSS and leave a deck looking almost unchanged, because the kernel chrome
themes through FIVE custom properties (--ink --paper --muted --accent --radius)
and a real design system defines ~40. This probe turns "whose names win" from a
debate into a histogram.

It flattens the REAL YARNNN export (the same bytes the live import consumed) and
classifies every custom property the skin DEFINES against what the kernel
CONSUMES, into the four buckets §5 question 1 needs:

  (a) DIRECT HIT   — the skin defines one of the kernel's five names → it bites.
  (b) ALIAS        — the skin defines a name that is plausibly the-same-thing-as
                     a kernel var (a palette/ink/radius synonym) → an import-time
                     adapter could bridge it with zero skin authorship.
  (c) EXTRA-THEMEY  — a color/type/space token the kernel COULD consume if the
                     contract were wider, but doesn't today.
  (d) UNCONSUMABLE — component/util scaffolding (`--c-*` internal palette steps,
                     things that only a Button.jsx would read) → dead in an
                     artifact no matter how wide the contract goes.

The (a)+(b) vs (c) vs (d) split is the design input: mostly (a)+(b) → an adapter
is the whole fix and the five-var contract stays; heavy (c) → the contract is too
narrow. Pure measurement — no writes, reads the export off disk.

Run:  cd api && python probe_design_system_coverage.py
"""

from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SRC = os.path.expanduser("~/Downloads/YARNNN Design System")
FOLDER = "/workspace/design-system/yarnnn"

# The widened contract the kernel chrome consumes (DESIGN-SYSTEMS.md §5 Move 1;
# grepped from studio.py STUDIO_KERNEL_CSS v9 + the layout skins). --yw/--yh are
# per-block inline sizing tokens, not skin-themable; excluded on purpose. Derived
# live below so the probe cannot drift from the kernel it measures.
def _kernel_consumed_vars() -> set[str]:
    """Every `var(--NAME` the kernel + layout skins read — the live contract."""
    from services import studio

    blobs = [studio.STUDIO_KERNEL_CSS, studio._SHARED_CSS]
    blobs += [lay.get("skin", "") for lay in studio.STUDIO_LAYOUTS.values()]
    consumed = set(re.findall(r"var\(\s*--([a-zA-Z0-9-]+)", "\n".join(blobs)))
    # --yw/--yh ride inline per block; --radius is the legacy fallback inside the
    # radius-scale var()s, not a skin slot. Everything else is a real theme slot.
    return consumed - {"yw", "yh", "radius"}


KERNEL_VARS = _kernel_consumed_vars()

# (b) ALIAS heuristics — a defined name a trivial adapter could map onto a kernel
# var. Deliberately conservative: a human confirms before any adapter ships. The
# point is to SIZE the alias bucket, not to auto-map.
ALIAS_HINTS = {
    "ink": ("ink", "fg", "foreground", "text", "black", "on-", "-900", "-950"),
    "paper": ("paper", "bg", "background", "surface", "canvas", "cream", "white", "-50", "-100"),
    "muted": ("muted", "subtle", "secondary", "dim", "gray", "grey", "-400", "-500", "-600"),
    "accent": ("accent", "brand", "primary", "orange", "yarn", "highlight", "cta"),
    "radius": ("radius", "round", "corner", "rounded"),
}

# (d) UNCONSUMABLE — scaffolding no artifact reads. Internal palette-step scales
# and component-only tokens. Named as prefixes.
UNCONSUMABLE_PREFIXES = ("c-", "shadow", "z-", "ease", "duration", "leading", "tracking")


def read_source_tree() -> dict:
    out: dict[str, str | None] = {}
    for root, _dirs, names in os.walk(SRC):
        for n in names:
            p = os.path.join(root, n)
            rel = os.path.relpath(p, SRC)
            try:
                out[rel] = open(p, encoding="utf-8").read()
            except (UnicodeDecodeError, OSError):
                out[rel] = None
    return out


# A single var maps 1:1 onto a kernel var; a SCALE FAMILY (--text-xs … --text-5xl,
# --radius-sm … --radius-pill, --space-4 … --space-32, --ink-02 … --ink-90) does
# NOT — the kernel has ONE --radius slot, not five, so a family can only be
# consumed if the contract grows a slot for it. Family stems are (c), never (b);
# folding them out of (b) keeps the alias count honest (an adapter bridges
# synonyms, not scales).
FAMILY_STEMS = ("text-", "radius-", "space-", "ink-", "section-", "weight-",
                "glass-", "glow-", "surface-", "app-")


def classify(name: str) -> str:
    if name in KERNEL_VARS:
        return "a"  # direct hit — paints today
    low = name.lower()
    if any(low.startswith(p) for p in UNCONSUMABLE_PREFIXES):
        return "d"
    if any(low.startswith(f) for f in FAMILY_STEMS):
        return "c"  # a scale/family member: needs a contract slot, not an adapter
    for _kernel, hints in ALIAS_HINTS.items():
        if any(h in low for h in hints):
            return "b"  # a 1:1 synonym an import-time adapter can bridge
    return "c"  # extra-themey (a color/type/space token the kernel could take)


def main() -> int:
    if not os.path.isdir(SRC):
        print(f"source folder not found: {SRC}")
        return 1

    from services.design_systems import flatten_css, plan_import

    text = {k: v for k, v in read_source_tree().items() if v is not None}
    plan = plan_import(text, folder_name=os.path.basename(SRC))

    def read_from_disk(abs_path: str):
        rel = abs_path[len(FOLDER):].lstrip("/")
        return text.get(rel)

    css, sources, _warns = flatten_css(plan["entry"], read_from_disk, FOLDER)

    print("=" * 76)
    print("APPLY-GAP COVERAGE — the real YARNNN skin vs the kernel's five vars")
    print("=" * 76)
    print(f"flattened skin: {len(css)} bytes from {len(sources)} sources")
    print(f"kernel consumes: {sorted('--' + v for v in KERNEL_VARS)}")
    print()

    # Every custom property the skin DEFINES (`--name: value;`), and every one it
    # REFERENCES (`var(--name)`), so we can see internal wiring vs surface.
    defined = sorted(set(re.findall(r"(--[a-zA-Z0-9-]+)\s*:", css)))
    referenced = set(re.findall(r"var\(\s*(--[a-zA-Z0-9-]+)", css))

    buckets: dict[str, list[str]] = {"a": [], "b": [], "c": [], "d": []}
    for full in defined:
        buckets[classify(full[2:])].append(full)

    labels = {
        "a": "DIRECT HIT   (paints today)",
        "b": "ALIAS-ABLE   (an import-time adapter bridges it — no skin authorship)",
        "c": "EXTRA-THEMEY (a color/type/space token; only bites if the contract widens)",
        "d": "UNCONSUMABLE (component/util scaffolding; dead in an artifact)",
    }
    for key in ("a", "b", "c", "d"):
        rows = buckets[key]
        print(f"[{key}] {labels[key]}  — {len(rows)}")
        for full in rows:
            internal = " (used internally)" if full in referenced else ""
            print(f"      {full}{internal}")
        print()

    total = len(defined)
    hit = len(buckets["a"])
    bridgeable = len(buckets["a"]) + len(buckets["b"])
    print("-" * 76)
    print(f"total custom properties defined by the skin: {total}")
    print(f"  paints today (a):            {hit:>3}  ({100*hit//max(total,1)}%)")
    print(f"  bridgeable via adapter (a+b): {bridgeable:>3}  ({100*bridgeable//max(total,1)}%)")
    print(f"  would need a wider contract (c): {len(buckets['c']):>3}")
    print(f"  never consumable (d):        {len(buckets['d']):>3}")
    print()
    print("READ THIS: if (a+b) covers the palette/type/radius the eye reads, an")
    print("adapter is the whole fix and the five-var contract stays. If (c) holds the")
    print("colors that actually differentiate the brand, the contract is too narrow.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
