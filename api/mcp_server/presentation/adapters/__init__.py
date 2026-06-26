"""Host adapters — neutral affordance → vendor `_meta` shape (ADR-372 D2/D5).

`mcp_apps` is PRIMARY (the open, ratified MCP Apps spec, SEP-1865). `openai` is a
thin OVERLAY adding ChatGPT-only `_meta` sugar over the primary shape. A host name
appears in code in exactly one place: its adapter file. When MCP Apps standardizes
a key OpenAI currently does its own way, the open adapter gains it and the overlay
shrinks — the blast radius of any vendor revision is one adapter file.
"""
