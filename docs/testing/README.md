# YARNNN Testing Documentation

This directory contains validation and testing documentation for YARNNN features.

## Structure

```
testing/
├── README.md                    # This file
├── ADR-039-background-work.md   # Background work agents validation
├── ADR-040-semantic-matching.md # Semantic skill matching validation
└── integration/                 # End-to-end integration tests (future)
```

## Testing Philosophy

Per ADR discipline principle #6: **Implementation Implies Testing**

Each implemented ADR should have corresponding validation that covers:
1. **Unit validation** — Individual function behavior
2. **Integration validation** — Component interaction
3. **Manual test cases** — User-facing scenarios
4. **Edge cases** — Failure modes and graceful degradation

## Quick Links

- [ADR-039: Background Work Validation](./ADR-039-background-work.md)
- [ADR-040: Semantic Matching Validation](./ADR-040-semantic-matching.md)
