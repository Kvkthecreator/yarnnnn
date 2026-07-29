"""
The transactional email shell — one house style for every message yarnnn sends
(ADR-498 D2).

## Why this module exists

Every sender re-inlined its own HTML. `notifications.py` had a house style
(system font stack, 600px column, `#111` pill CTA, muted footer); the invite
email had none at all — bare `<p>` and a raw blue `<a>`, so a member's FIRST
contact with yarnnn was the least branded thing the product sends. Adding a
styled invite by hand would have made a sixth private variant.

This module is the single shell. A sender supplies *content*; the shell owns
the frame — wordmark, column, type scale, button, footer.

## Constraints this deliberately respects

**Email is not the web.** No external stylesheet, no `<style>` block that
survives Gmail reliably, no flexbox/grid, no web font, no CSS variable. Every
rule is inlined on the element that needs it, layout is a table, and the palette
is fixed hex — the design system's *tokens* cannot be referenced (a client that
strips `:root` would render an unstyled page). So this mirrors the design
system's INTENT (near-black ink, generous whitespace, one accent, quiet
metadata) in the only vocabulary mail clients honor.

**Dark mode is a suggestion.** `color-scheme` + `prefers-color-scheme` are
respected by Apple Mail and (partially) Gmail, ignored elsewhere. The light
palette is therefore the base and must stand alone; the dark block only
*improves* it where supported. Never encode meaning in colour alone.

**Pointer-only (ADR-202).** An email carries a pointer into the product, never
a content replacement. The shell offers one primary CTA.
"""

from __future__ import annotations

from typing import Optional

# The palette. Fixed hex, not tokens — see the module docstring.
_INK = "#111111"          # primary text / button fill (the brand's near-black)
_BODY = "#3f3f46"         # body copy — softer than ink, still AA on white
_MUTED = "#71717a"        # metadata, footer
_HAIRLINE = "#e4e4e7"     # rules
_CANVAS = "#fafafa"       # page behind the card
_CARD = "#ffffff"
_FONT = (
    "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, "
    "'Helvetica Neue', Arial, sans-serif"
)


def render_email(
    *,
    heading: str,
    body_html: str,
    cta_label: Optional[str] = None,
    cta_url: Optional[str] = None,
    footnote_html: Optional[str] = None,
    footer_html: Optional[str] = None,
    preheader: Optional[str] = None,
) -> str:
    """Wrap content in the house shell.

    Args:
        heading: the one-line title (plain text — escaped by the caller if it
            can contain user input).
        body_html: the message body. Use ``<p style="...">`` via `paragraph()`.
        cta_label / cta_url: the single primary action. Both or neither.
        footnote_html: small print under the CTA (e.g. validity window).
        footer_html: below the rule (e.g. an unsubscribe pointer).
        preheader: the inbox preview line. Hidden in the body — without it,
            clients scrape the first visible text, which is usually the
            wordmark and reads as a blank preview.
    """
    cta_block = ""
    if cta_label and cta_url:
        # A table-wrapped anchor: Outlook ignores padding on inline <a>, so the
        # cell provides the box and the anchor provides the hit target.
        cta_block = f"""
        <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:28px 0 0 0;">
          <tr>
            <td align="center" bgcolor="{_INK}" style="border-radius:8px;">
              <a href="{cta_url}"
                 style="display:inline-block;padding:12px 24px;font-family:{_FONT};font-size:15px;font-weight:600;color:#ffffff;text-decoration:none;border-radius:8px;">
                {cta_label}
              </a>
            </td>
          </tr>
        </table>"""

    footnote_block = (
        f'<p style="margin:16px 0 0 0;font-family:{_FONT};font-size:13px;'
        f'line-height:1.5;color:{_MUTED};">{footnote_html}</p>'
        if footnote_html
        else ""
    )

    footer_block = (
        f"""
        <tr>
          <td style="padding:0 32px 32px 32px;">
            <div style="border-top:1px solid {_HAIRLINE};margin:28px 0 0 0;"></div>
            <p style="margin:16px 0 0 0;font-family:{_FONT};font-size:12px;line-height:1.6;color:{_MUTED};">
              {footer_html}
            </p>
          </td>
        </tr>"""
        if footer_html
        else ""
    )

    preheader_block = (
        f'<div style="display:none;max-height:0;overflow:hidden;opacity:0;'
        f'mso-hide:all;">{preheader}</div>'
        if preheader
        else ""
    )

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="supported-color-schemes" content="light dark">
<style>
  /* Only ever ADDITIVE — the inlined light palette stands alone where this
     block is stripped (most clients). Never put layout or meaning here. */
  @media (prefers-color-scheme: dark) {{
    .y-canvas {{ background:#09090b !important; }}
    .y-card {{ background:#18181b !important; border-color:#27272a !important; }}
    .y-heading, .y-mark {{ color:#fafafa !important; }}
    .y-body {{ color:#d4d4d8 !important; }}
    .y-muted {{ color:#a1a1aa !important; }}
    .y-rule {{ border-color:#27272a !important; }}
  }}
</style>
</head>
<body class="y-canvas" style="margin:0;padding:0;background:{_CANVAS};">
{preheader_block}
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="y-canvas" style="background:{_CANVAS};">
  <tr>
    <td align="center" style="padding:40px 16px;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
             class="y-card"
             style="max-width:520px;background:{_CARD};border:1px solid {_HAIRLINE};border-radius:14px;">
        <tr>
          <td style="padding:32px 32px 0 32px;">
            <p class="y-mark" style="margin:0 0 24px 0;font-family:{_FONT};font-size:19px;font-weight:600;letter-spacing:-0.02em;color:{_INK};">
              yarnnn
            </p>
            <h1 class="y-heading" style="margin:0 0 12px 0;font-family:{_FONT};font-size:21px;line-height:1.35;font-weight:600;letter-spacing:-0.01em;color:{_INK};">
              {heading}
            </h1>
            {body_html}
            {cta_block}
            {footnote_block}
          </td>
        </tr>
        {footer_block}
      </table>
    </td>
  </tr>
</table>
</body>
</html>"""


def paragraph(html: str) -> str:
    """A body paragraph in the house type scale."""
    return (
        f'<p class="y-body" style="margin:0 0 12px 0;font-family:{_FONT};'
        f'font-size:15px;line-height:1.6;color:{_BODY};">{html}</p>'
    )


__all__ = ["render_email", "paragraph"]
