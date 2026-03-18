"""Chart skill — data spec → PNG/SVG via matplotlib."""

import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


async def render_chart(input_data: dict, output_format: str) -> tuple[bytes, str]:
    """
    Render a chart from data.

    input_data: {
        "chart_type": "bar"|"line"|"pie",
        "title": str,
        "labels": [str, ...],
        "datasets": [
            {"label": str, "data": [number, ...]},
            ...
        ],
        "x_label": str (optional),
        "y_label": str (optional),
    }
    output_format: "png" or "svg"
    Returns: (file_bytes, content_type)
    """
    if output_format not in ("png", "svg"):
        raise ValueError(f"Unsupported chart format: {output_format}")

    content_types = {
        "png": "image/png",
        "svg": "image/svg+xml",
    }

    chart_type = input_data.get("chart_type", "bar")
    title = input_data.get("title", "")
    labels = input_data.get("labels", [])
    datasets = input_data.get("datasets", [])

    fig, ax = plt.subplots(figsize=(10, 6))

    if chart_type == "bar":
        import numpy as np
        x = np.arange(len(labels))
        width = 0.8 / max(len(datasets), 1)
        for i, ds in enumerate(datasets):
            offset = (i - len(datasets) / 2 + 0.5) * width
            ax.bar(x + offset, ds["data"], width, label=ds.get("label", f"Series {i+1}"))
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha="right")

    elif chart_type == "line":
        for ds in datasets:
            ax.plot(labels, ds["data"], marker="o", label=ds.get("label", ""))

    elif chart_type == "pie":
        if datasets:
            ax.pie(datasets[0]["data"], labels=labels, autopct="%1.1f%%")

    ax.set_title(title)
    if input_data.get("x_label"):
        ax.set_xlabel(input_data["x_label"])
    if input_data.get("y_label"):
        ax.set_ylabel(input_data["y_label"])

    if chart_type != "pie" and datasets:
        ax.legend()

    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format=output_format, dpi=150, bbox_inches="tight")
    plt.close(fig)

    return buf.getvalue(), content_types[output_format]
