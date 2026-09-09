"""ADR-473 — document types + "Open With": the type→app association.

The operator's bug: the Images landing listed every Studio artifact (Test page,
Test article, a Deck, a Document). ADR-472 filtered the template PICKER but
nothing else, because nothing in the system answered "which app owns this
document type?" — and extension cannot answer it, since Studio and IMAGES both
author `.html`.

Covers:
  §1  the declaration — every layout row names its owning app
  §2  the resolver    — kind→app, and its inverse; unowned degrades (D6)
  §3  the serving     — `app` rides templates + vocabulary (D3)
  §4  EXECUTION       — the endpoints actually run and scope (the yesterday
                        lesson: a grep proves a symbol exists, never that a
                        handler can reach it)
  §5  no dual path    — the FE holds no hardcoded "which types are mine" list

Run:  python3 api/test_adr473_document_types.py   (NOT pytest — check()-gate.)
"""

import asyncio
import re
import sys
from pathlib import Path

_results: list[tuple[str, bool]] = []


def _check(label: str, cond: bool) -> None:
    _results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")


class _FakeAuth:
    user_id = "00000000-0000-0000-0000-000000000000"
    client = None


def _read(rel: str) -> str:
    return Path(__file__).resolve().parents[1].joinpath(rel).read_text()


def run() -> bool:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import services.apps.images  # noqa: F401 — registration side-effect
    import routes.studio as rs
    from services.authoring import (
        STUDIO_LAYOUTS,
        all_layouts,
        app_for_kind,
        kinds_for_app,
        resolve_arrangements,
    )

    # ── §1 The declaration ───────────────────────────────────────────────
    _check(
        "every registered layout declares an owning app",
        all(row.get("app") for row in all_layouts().values()),
    )
    _check(
        "Slides' one type is Slides' (ADR-599 D5 — deck is the one medium)",
        set(STUDIO_LAYOUTS) == {"deck"}
        and STUDIO_LAYOUTS["deck"].get("app") == "slides",
    )

    # ── §2 The resolver ──────────────────────────────────────────────────
    _check(
        "kind→app resolves both apps",
        app_for_kind("deck") == "slides" and app_for_kind("image") == "images",
    )
    _check(
        "an UNOWNED type degrades to None, never raises (D6)",
        app_for_kind("tearsheet-from-a-bundle") is None and app_for_kind(None) is None,
    )
    _check(
        "the inverse lookup partitions the types — no type in two apps",
        # ADR-505 D1/D2 via ADR-518 D1: three media across three apps —
        # Docs' document; Studio's deck + web (`article`/`page` → `web`);
        # IMAGES' image.
        kinds_for_app("slides") == {"deck"}  # ADR-599: docs deleted, web deleted
        and kinds_for_app("images") == {"image"}
        and not (kinds_for_app("slides") & kinds_for_app("images")),
    )

    # ── §3 + §4 Serving AND execution ────────────────────────────────────
    auth = _FakeAuth()
    try:
        templates = asyncio.run(rs.list_templates(auth))
        rows = {t["slug"]: t.get("app") for t in templates["templates"]}
        _check("GET /studio/templates EXECUTES and carries `app` per row", all(rows.values()))
        _check(
            "…and UNSCOPED it serves every app's types (the cross-app palette)",
            rows.get("deck") == "slides" and rows.get("image") == "images",
        )
        # ADR-646 D1 — the SERVER scopes. This assertion used to read "the
        # picker filters client-side on it", and that was the whole defense:
        # one `.filter()` in StudioSurface stood between a member and another
        # app's types, on a payload that shipped all of them.
        _scoped = {
            a: {t["slug"] for t in asyncio.run(rs.list_templates(auth, app=a))["templates"]}
            for a in ("slides", "blogger", "images")
        }
        _check(
            "…and `app=` scopes it server-side to exactly that app's types",
            _scoped["slides"] == {"deck"}
            and _scoped["blogger"] == {"post"}
            and _scoped["images"] == {"image"},
        )
        _check(
            "…the scoped palettes PARTITION — no type reachable from two apps",
            not (_scoped["slides"] & _scoped["blogger"])
            and not (_scoped["slides"] & _scoped["images"]),
        )
    except Exception as exc:  # noqa: BLE001
        _check(f"GET /studio/templates EXECUTES — raised {type(exc).__name__}: {exc}", False)
        _check("…and UNSCOPED it serves every app's types", False)
        _check("…and `app=` scopes it server-side", False)
        _check("…the scoped palettes PARTITION", False)

    try:
        vocab = asyncio.run(rs.get_vocabulary(auth))
        layouts = {l["slug"]: l.get("app") for l in vocab["layouts"]}
        _check(
            "GET /studio/vocabulary EXECUTES and serves the association (D3)",
            layouts.get("deck") == "slides" and layouts.get("image") == "images",
        )
        # ADR-646 D3 — the arrangements key read STUDIO_ARRANGEMENTS (Studio's
        # OWN table) where every sibling read the cross-app registry, so
        # Blogger's and Images' rosters never reached the client at all. `post`
        # is `mode: "paged"`, so its paged chrome mounted onto an EMPTY band
        # gallery with no error anywhere to read. Assert the relation: every
        # served layout that HAS arrangements registered gets them served.
        _arr = vocab["arrangements"]
        _expected = {s for s in layouts if resolve_arrangements(s)}
        _check(
            "…and arrangements are served CROSS-APP, for every layout that has them",
            _expected.issubset(set(_arr)) and {"deck", "post", "image"} <= set(_arr),
        )
    except Exception as exc:  # noqa: BLE001
        _check(f"GET /studio/vocabulary EXECUTES — raised {type(exc).__name__}: {exc}", False)
        _check("…and arrangements are served CROSS-APP", False)

    # The artifact list's SCOPING logic, exercised without a DB: the filter is
    # `app_for_kind(kind) != app`, so prove the decision, not the query.
    _check(
        "artifact scoping keeps only the asking app's types (D4)",
        app_for_kind("image") == "images"
        and app_for_kind("deck") != "images"
        and app_for_kind("document") != "images",
    )
    src = _read("api/routes/studio.py")
    _check(
        "the artifact list takes an `app` filter and widens its window first",
        "async def list_artifacts(auth: UserClient, app: Optional[str] = None)" in src
        and ".limit(200)" in src
        and "_DISPLAY_LIMIT" in src,
    )

    # ── §5 No dual path (the hooks discipline) ───────────────────────────
    surface = _read("web/components/authoring/StudioSurface.tsx")
    _check(
        "the FE holds NO hardcoded type list — ownership is served",
        "IMAGES_APP.templates" not in surface
        and "templates?: string[]" not in surface
        and "t.app === app.slug" in surface,
    )
    _check(
        "recents are scoped by the asking app (the operator's bug)",
        ".artifacts(app.slug)" in surface,
    )
    ftypes = _read("web/lib/file-types/index.ts")
    _check(
        "the ADR-451 `every html → Studio` hardcode is REPLACED, not supplemented",
        "registerKindApps" in ftypes
        and "appForKind" in ftypes
        and "return { surface: 'studio', param: 'file', label: 'Studio' };" not in ftypes,
    )
    _check(
        "the Finder's open verb resolves the artifact's KIND before routing",
        "extractTemplate" in _read("web/app/(authenticated)/files/page.tsx"),
    )

    # ── ADR-646 D4 (click-pass) — the picker asks the SERVED index ───────
    # Found by DRIVING the browser, which no gate had caught: passing
    # `knownKind` was necessary and NOT sufficient. Nothing populates the
    # PATH_KIND cache for a picker — only the Files surface calls
    # `rememberKind`, and it does so when it READS a file's content, while the
    # picker renders a tree it never reads. So every row resolved to an
    # unknown kind and Blogger's Open… stayed empty even after the fix.
    #
    # Two halves, both required: seed the cache from the served rows (which
    # already carry the server-lifted kind), and ask `owned` FIRST — it is the
    # kernel's own answer, and the registry route is the fallback for an app
    # with no served index or a failed fetch.
    modal = _read("web/components/authoring/OpenArtifactModal.tsx")
    _check(
        "the picker SEEDS the kind cache from the served index (nothing else does)",
        "rememberKind(a.path, a.kind)" in modal,
    )
    _check(
        "…and the served ownership set is asked BEFORE the path-derived route",
        modal.index("if (owned) return owned.has(node.path);")
        < modal.index("resolveSurfaceApplication(node.path"),
    )

    # ── ADR-646 D2 — the WRITE door enforces ownership ───────────────────
    # A scoped palette that no write door checks is a suggestion: the palette
    # is client-rendered, so nothing stopped a hand-built POST minting a
    # Blogger `post` from the Slides surface. DRIVEN, not grepped — the point
    # is the REFUSAL, and only calling it proves that.
    from fastapi import HTTPException

    def _create(template: str, app: str):
        """The create door's status for (template, app). `None` = it got PAST
        the ownership check (this harness has no DB, so an accepted call dies
        later on `auth.client`, which is the signal we want)."""
        req = rs.CreateArtifactRequest(template=template, app=app, path=f"x/{template}.html")
        try:
            asyncio.run(rs.create_artifact(req, _FakeAuth()))
            return None
        except HTTPException as e:
            return e.status_code
        except Exception:  # noqa: BLE001 — reached the DB ⇒ ownership passed
            return None

    _check(
        "the create door REFUSES a template the asking app does not own (422)",
        _create("post", "slides") == 422 and _create("deck", "blogger") == 422,
    )
    # The negative's twin: a gate that only proves refusal would also pass if
    # the door refused EVERYTHING. An owned type must get past ownership — it
    # fails later (no DB in this harness), and "not 422" is exactly that line.
    _check(
        "…and lets an OWNED type past the ownership check",
        _create("deck", "slides") != 422 and _create("post", "blogger") != 422,
    )

    # ── ADR-646 D5 — an unowned type degrades to NO app (D6), not to Slides ──
    _check(
        "an unowned kind resolves to no app — the generic viewer, never a default",
        app_for_kind("document") is None and app_for_kind("tearsheet") is None,
    )
    # Strip comments BEFORE the substring check. This went red against the
    # epitaph in the very comment explaining the deletion — the recurring
    # "a gate check that matches its own documentation" fault. Code, not prose.
    _ftypes_code = re.sub(r"/\*.*?\*/", "", ftypes, flags=re.S)
    _ftypes_code = re.sub(r"^\s*//.*$", "", _ftypes_code, flags=re.M)
    _check(
        "…and the FE holds no default-app fallback either",
        "DEFAULT_ARTIFACT_APP" not in _ftypes_code,
    )

    # ── §6 The Learn-from roster covers every app that serves the landing ──
    # ADR-646 D6 fixed `writing-a-spec` (it targeted the dead `document` kind)
    # and swept ONE app. IMAGES stayed broken for the same reason and nobody
    # saw it, because the failure mode here is SILENT: the roster is filtered
    # per app (`appForKind(t.template) === app.slug`), so an app with no
    # surviving row still renders its "Learn from…" button — the modal just
    # cannot produce anything the app owns. Images' only reachable target was
    # the app-free design system, which navigates AWAY to /chat.
    #
    # Derived, never hand-spelled: the app list comes from the layout registry
    # (the same declaration §1 checks), so registering an app without giving it
    # a Learn row turns this red instead of shipping a dead door.
    targets = re.search(
        r"const LEARN_TARGETS: LearnTarget\[\] = \[(.*?)\n\];", surface, re.S
    )
    _check("the LEARN_TARGETS roster is readable from the surface", bool(targets))
    if targets:
        rostered = set(re.findall(r"template: '([a-z-]+)'", targets.group(1)))
        # Every app that OWNS a document type serves the landing, so every one
        # of them needs a row whose template it owns.
        owning_apps = {
            (row.get("app") or "studio") for row in all_layouts().values()
        }
        uncovered = sorted(
            app for app in owning_apps
            if not (kinds_for_app(app) & rostered)
        )
        _check(
            f"every app owning a type has a Learn-from row (uncovered: {uncovered})",
            not uncovered,
        )
        # The twin: a roster naming a type NOBODY owns is the ADR-646 D6 defect
        # itself (`document` outlived the Docs app), filtered out of every app.
        orphans = sorted(t for t in rostered if app_for_kind(t) is None)
        _check(
            f"…and every rostered template is still owned (orphans: {orphans})",
            not orphans,
        )

    ok = all(c for _, c in _results)
    print()
    print(f"{'PASS' if ok else 'FAIL'}: {sum(c for _, c in _results)}/{len(_results)} checks")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
