# Archived Scheduler Planning Documents

**Last Updated**: 2026-01-27

This folder contains scheduler planning and development documents from the **Scheduler Terminology Refactor** project. These documents served as the planning foundation for the refactor (Issue #296) and are preserved for historical reference.

## Current Documentation

For current scheduler documentation, see:
- **[Scheduler API Reference](../../api/scheduler.md)** - REST API documentation
- **[Scheduler User Guide](../../../../SCHEDULER_USER_GUIDE.md)** - End-user guide
- **[Cron Bridge API](../../api/cron-bridge.md)** - Trigger-to-cron conversion

## Archived Documents

### Terminology Refactor Planning

| Document | Purpose |
|----------|---------|
| `SCHEDULER_TERMINOLOGY_REFACTOR.md` | Original specification for Schema 3.0 terminology changes |
| `TERMINOLOGY_REFACTOR_CLARIFYING_QUESTIONS.md` | Design decisions and Q&A during planning |

### One-Time Actions (Superseded)

These documents proposed an approach that was superseded by the routine-based model:

| Document | Original Purpose |
|----------|------------------|
| `ONE_TIME_ACTIONS_FEATURE.md` | Feature proposal for adding one-time action support |
| `ONE_TIME_ACTIONS_DEV_GUIDE.md` | Implementation guide based on the old approach |

## Why These Documents Are Archived

The Scheduler Terminology Refactor (Issue #296) is now complete. These planning documents:
- Defined the schema changes from 2.0 to 3.0
- Established the routine-based model (triggers at routine level, not schedule level)
- Guided the implementation work

Now that implementation is complete, the authoritative documentation is in the API reference and user guides.

## Related Issues

- GitHub Issue #295 - Original one-time actions issue (resolved by terminology refactor)
- GitHub Issue #296 - Terminology refactor implementation
- GitHub Issue #336 - This archival task
