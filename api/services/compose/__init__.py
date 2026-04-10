"""
Compose Substrate — ADR-170.

Binding layer between the accumulating workspace filesystem and rendered output.
Converts accumulated context (domains, entities, assets) into a structured
deliverable expressed as an output folder.

Three operations:
  assembly.py  — pre-generation brief + post-generation folder build
  manifest.py  — sys_manifest.json schema, provenance tracking, staleness detection

Phase 2: pre-generation assembly (generation brief) ← current
Phase 3: post-generation assembly (section partials, output folder) ← next
Phase 4: revision routing (staleness detection, section-scoped regeneration) ← future
Phase 5: asset lifecycle (root vs derivative, cross-run continuity) ← future
"""

from services.compose.assembly import build_generation_brief
from services.compose.manifest import read_manifest, SysManifest

__all__ = ["build_generation_brief", "read_manifest", "SysManifest"]
