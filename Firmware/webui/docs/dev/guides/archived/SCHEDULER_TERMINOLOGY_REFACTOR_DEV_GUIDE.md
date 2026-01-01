# Scheduler Terminology Refactor Developer Guide

> **This guide has been split into focused documents for easier navigation and reduced token usage during implementation.**

## Quick Navigation

| Document | Purpose | When to Read |
|----------|---------|--------------|
| [Index](./SCHEDULER_TERMINOLOGY_REFACTOR_INDEX.md) | Navigation hub, quick reference | Start here |
| [Overview](./SCHEDULER_TERMINOLOGY_REFACTOR_OVERVIEW.md) | Architecture, schema changes | For context |
| [Backend](./SCHEDULER_TERMINOLOGY_REFACTOR_BACKEND.md) | Python implementation steps | When implementing backend |
| [Frontend](./SCHEDULER_TERMINOLOGY_REFACTOR_FRONTEND.md) | React components and hooks | When implementing frontend |
| [Testing](./SCHEDULER_TERMINOLOGY_REFACTOR_TESTING.md) | TDD workflow, fixtures | When writing tests |
| [Reference](./SCHEDULER_TERMINOLOGY_REFACTOR_REFERENCE.md) | Patterns, API spec, phases | Quick lookup |

## Why Split?

The original 3,000+ line guide was split to:
- **Reduce token usage**: Load only relevant section (~1,600-3,600 tokens) instead of full guide (~12,000 tokens)
- **Improve navigation**: Each document is self-contained for a specific phase
- **Enable parallel work**: Backend and frontend can be implemented independently

## Start Here

**For implementation context**: [SCHEDULER_TERMINOLOGY_REFACTOR_INDEX.md](./SCHEDULER_TERMINOLOGY_REFACTOR_INDEX.md)

---

**Last Updated**: 2025-12-31
**Issue**: [#296](https://github.com/zane-lazare/Mothbox/issues/296)
