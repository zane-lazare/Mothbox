# Archived Scheduler Documents

**Archived**: 2025-12-31

This folder contains scheduler planning and development documents that have been superseded by the **Scheduler Terminology Refactor**.

## Why These Documents Are Archived

The original "one-time actions" approach proposed adding `one_time`, `fixed_time`, and `solar_event` fields to the `PatternAction` class. This was superseded by a more elegant solution:

**New approach**: Move triggers from the Schedule level to the Routine level, allowing each routine to have its own timing. This naturally supports one-time actions without special flags.

## Current Authoritative Document

See **[SCHEDULER_TERMINOLOGY_REFACTOR.md](../SCHEDULER_TERMINOLOGY_REFACTOR.md)** for the current scheduler model specification.

## Archived Documents

| Document | Original Purpose |
|----------|------------------|
| `ONE_TIME_ACTIONS_FEATURE.md` | Feature proposal for adding one-time action support |
| `ONE_TIME_ACTIONS_DEV_GUIDE.md` | Implementation guide based on the old approach |

## Related

- GitHub Issue #295 - Original one-time actions issue (resolved by terminology refactor)
- GitHub Issue #296 - Terminology refactor implementation
