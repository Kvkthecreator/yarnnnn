"""The apps — one module per app, each declaring what it owns (ADR-562).

An app is a module here. It declares, through the shared doors in
``services/authoring.py`` and at its own import:

    register_layouts(...)   — the document types it owns (ADR-472 D2)
    register_app(...)       — its AI configuration: the RESIDENT its bound
                              lane carries, and optionally the name that
                              resident wears inside this app (ADR-562 D2/D3)

**The kernel never imports an app.** Registration is the only direction: an
app reaches the shared machinery, never the reverse. Importing an app IS its
registration, which is why those imports are load-bearing and must not be
pruned as "unused" (see ``routes/studio.py``).

WHY THE APP'S AI CONFIG IS CODE AND NOT A WORKSPACE FOLDER
ADR-464's ruling, held verbatim: *the member's copy is a folder; the kernel's
is code*. A member's agent is ``agents/{slug}/_agent.yaml`` in their
workspace — theirs to author, discovered never registered. An app is KERNEL,
so its resident is a code declaration. Were an app's resident member-editable
substrate, a workspace could re-point Docs' colleague — the ADR-460 D3.a cliff
arriving through a config file. Same convention, different tree; that
difference IS the cliff.

WHAT AN APP ROW MAY CARRY
Identity only: who the resident is, what it is called here. No authority, no
tool grant — an app pins a colleague, it cannot widen one. The D3.a cliff
holds on this layer exactly as it holds on the agent registry.

⚠️ STUDIO IS NOT HERE, AND THAT IS DELIBERATE (ADR-562 §4).
Studio's tables live in ``services/authoring.py`` because that file is the
authoring KERNEL wearing the name of the app that arrived first:
``STUDIO_BLOCKS`` is filtered for every app by ``blocks_for_app()``, kernel
code reads ``STUDIO_LAYOUTS`` directly, and the tables are wrapped in the
ADR-447/544 grammar canon the SHARED machinery implements. Moving them would
fork that canon or invert the dependency. Studio declares through the same
``register_app`` door as Docs and IMAGES — and the door, never the file path,
is what makes app configuration uniform.

Adding an app = a module here + its two registrations + a line in the eager
import below. The gate (``test_adr562_app_owned_config.py``) asserts one
declaration per app and that every registered app names a resolvable resident.
"""

# ⚠️ EAGER REGISTRATION — importing this PACKAGE registers every app.
#
# Before ADR-562 the registrations ran only as a side-effect of importing
# `routes/studio.py`, which was adequate while the registry was read by that
# same router. It stopped being adequate the moment `create_lane` began
# resolving `app → resident`: a process that imported `routes/lanes.py` without
# `routes/studio.py` would refuse a VALID app with "Unknown app", and the
# failure would depend on router import ORDER rather than on anything real.
#
# Making the package itself the registration point removes the ordering
# question entirely: `resident_for_app` cannot be reached without
# `services.authoring`, and any caller that resolves an app imports THIS.
# A new app adds its line here — one place, checked by the gate.
from services.apps import docs as docs  # noqa: F401,E402  (registration side-effect)
from services.apps import images as images  # noqa: F401,E402  (registration side-effect)

# radar (ADR-486) is an app with a resident too — a sweep on a clock rather than
# a canvas, which changes what it DOES, not what kind of fact its colleague is.
# Its declaration lives HERE rather than in `services/radar.py` because that
# module deliberately carries no module-level `services.*` imports (every
# service reference in it is function-local, to stay cycle-free). Declaring it
# here keeps that property AND keeps every app's residency in one readable list.
from services.authoring import register_app as _register_app  # noqa: E402

_register_app("radar", resident="scout")

# strings (ADR-569) — the maintained file, kept by Keeper. Declared here for
# the same reason as radar's row: `services/strings.py` deliberately carries
# no module-level `services.*` imports (cycle-free), and every app's residency
# reads in one list. The resident is IDENTITY only (ADR-562): the engine
# follows the keeper row in KERNEL_AGENTS, never a caller-supplied model.
_register_app("strings", resident="keeper")
