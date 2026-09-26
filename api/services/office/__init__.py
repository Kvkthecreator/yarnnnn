"""The office kernel — Word, Excel and PowerPoint files, first-class (ADR-671).

One home for everything yarnnn does to an office file:

  docx.py / xlsx.py / pptx.py   the ADDRESSED projection (what an agent reads)
                                and the in-place EDIT (what it writes), one
                                module per format so the two cannot drift
  package.py                    the OOXML zip: parts read safely, changed parts
                                written, every other part kept as it was
  edit.py                       the one edit door (EditFile, MCP `edit`)
  create.py                     writing a NEW office file from a source
                                (Markdown/HTML/CSV/a Slides deck) — ADR-395 am.2

The bytes are canonical (D1): an existing office file is patched, never rebuilt.
Which extension maps to which projector and editor is declared once, on the
format registry's rows (`services/file_formats.py`).
"""

from __future__ import annotations

from services.office import docx, pptx, xlsx  # noqa: F401  — each declares its KIND
from services.office.package import OfficeEditError, OfficeKind

__all__ = ["OfficeEditError", "OfficeKind"]
