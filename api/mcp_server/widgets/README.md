# MCP widget bundles (ADR-372)

UI bundles served by the MCP server as `ui://` resources (the OpenAI Apps SDK /
open MCP Apps rendering path). These are **frontend artifacts** owned by the
interop face — they import nothing from the Python kernel; they render the
substrate a tool already returns (ADR-372 D3).

```
widgets/
├── dist/                     # served bundles (one self-contained .html each)
│   └── trace-timeline.html   # CHECKPOINT PLACEHOLDER — proves the _meta pipe
└── src/                      # (future) the real React sources + build
```

## Current status — checkpoint placeholder

`dist/trace-timeline.html` is the **placeholder** from the ADR-372 §5 first
implementation checkpoint: a single self-contained HTML file (no build step) that
listens on the MCP Apps bridge and renders the `trace` result's `history[]`. Its
job is to prove the pipe end-to-end — *does a rendering host pick up `_meta` and
hand us the data* — before any real UI is built. Validate this in ChatGPT
developer mode (widget renders) against claude.ai (unchanged text) before styling.

## Future — the real build

When the pipe is proven, `src/trace-timeline/` holds the React source and a build
emits to `dist/`. The registry (`presentation/registry.py`) reads `dist/` at serve
time regardless of how the file got there, so swapping the placeholder for a built
bundle is a drop-in — no server.py or registry change.
