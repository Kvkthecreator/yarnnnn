"""Data export skill — structured data → CSV/JSON via Python stdlib."""

import csv
import io
import json


async def render_data(input_data: dict, output_format: str) -> tuple[bytes, str]:
    """
    Export structured data to CSV or JSON.

    input_data:
      CSV: {"headers": [str, ...], "rows": [[val, ...], ...]}
      JSON: {"data": any} (or entire input exported as-is)
    output_format: "csv" or "json"
    Returns: (file_bytes, content_type)
    """
    if output_format == "csv":
        headers = input_data.get("headers", [])
        rows = input_data.get("rows", [])
        if not headers:
            raise ValueError("CSV export requires 'headers' array")

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(headers)
        writer.writerows(rows)

        # UTF-8 with BOM for Excel compatibility
        content = b"\xef\xbb\xbf" + buf.getvalue().encode("utf-8")
        return content, "text/csv"

    elif output_format == "json":
        data = input_data.get("data", input_data)
        content = json.dumps(data, indent=2, ensure_ascii=False, default=str)
        return content.encode("utf-8"), "application/json"

    else:
        raise ValueError(f"Unsupported data export format: {output_format}")
