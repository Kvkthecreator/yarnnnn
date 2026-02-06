"""
Integration Agents - AI-powered processing for external platform data.

All external data passes through these agents before storage.
Raw API data → Agent (LLM) → Structured context blocks.

See ADR-027: Integration Read Architecture
"""

from .context_import import ContextImportAgent

__all__ = ["ContextImportAgent"]
