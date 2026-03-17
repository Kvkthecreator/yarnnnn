"""Render handlers — each handler converts structured input to a binary file."""

from .document import render_document
from .presentation import render_presentation
from .spreadsheet import render_spreadsheet
from .chart import render_chart

HANDLERS = {
    "document": render_document,
    "presentation": render_presentation,
    "spreadsheet": render_spreadsheet,
    "chart": render_chart,
}
