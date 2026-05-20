"""ADR-294 — CLI surface for the OperatorProxy capability.

Two entry points:
- loop.py: interactive REPL for ad-hoc operator-voice exploration
- run_scenario.py: scripted scenario player for versioned evaluations

Both import services.operator_proxy. No bespoke proxy logic lives here.
"""
