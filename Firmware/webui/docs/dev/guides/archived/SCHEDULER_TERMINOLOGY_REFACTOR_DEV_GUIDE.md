# Scheduler Terminology Refactor Developer Guide

> **ARCHIVED**: This guide and its linked documents are preserved for historical reference. The Scheduler Terminology Refactor (Issue #296) is now complete. For current documentation, see the [Scheduler API Reference](../api/scheduler.md) and [Scheduler User Guide](../../../SCHEDULER_USER_GUIDE.md).

## Quick Navigation

| Document | Purpose | When to Read |
|----------|---------|--------------|
| [Index](../scheduler/archived/SCHEDULER_TERMINOLOGY_REFACTOR_INDEX.md) | Navigation hub, quick reference | Start here |
| [Overview](../scheduler/archived/SCHEDULER_TERMINOLOGY_REFACTOR_OVERVIEW.md) | Architecture, schema changes | For context |
| [Backend](../scheduler/archived/SCHEDULER_TERMINOLOGY_REFACTOR_BACKEND.md) | Python implementation steps | When implementing backend |
| [Frontend](../scheduler/archived/SCHEDULER_TERMINOLOGY_REFACTOR_FRONTEND.md) | React components and hooks | When implementing frontend |
| [Testing](../scheduler/archived/SCHEDULER_TERMINOLOGY_REFACTOR_TESTING.md) | TDD workflow, fixtures | When writing tests |
| [Reference](../scheduler/archived/SCHEDULER_TERMINOLOGY_REFACTOR_REFERENCE.md) | Patterns, API spec, phases | Quick lookup |

## Why Split?

The original 3,000+ line guide was split to:
- **Reduce token usage**: Load only relevant section (~1,600-3,600 tokens) instead of full guide (~12,000 tokens)
- **Improve navigation**: Each document is self-contained for a specific phase
- **Enable parallel work**: Backend and frontend can be implemented independently

## Start Here

**For implementation context**: [SCHEDULER_TERMINOLOGY_REFACTOR_INDEX.md](../scheduler/archived/SCHEDULER_TERMINOLOGY_REFACTOR_INDEX.md)

---

**Last Updated**: 2026-01-27
**Issue**: [#296](https://github.com/zane-lazare/Mothbox/issues/296)
