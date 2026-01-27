# Scheduler Terminology Refactor - Index

**Last Updated**: 2026-01-01
**Version**: 1.1
**Issue**: [#296](https://github.com/zane-lazare/Mothbox/issues/296)

---

## Quick Reference

### Key Files

| File | Purpose |
|------|---------|
| `webui/backend/lib/schedule_schema.py` | Data classes (Routine, Action, Triggers) |
| `webui/backend/lib/cron_bridge.py` | Cron expression generation |
| `webui/backend/lib/schedule_conflict.py` | Collision detection |
| `webui/backend/lib/schedule_storage.py` | JSON file persistence |
| `webui/backend/services/scheduler_service.py` | Service layer |
| `webui/backend/routes/scheduler_ui.py` | REST API endpoints |
| `webui/frontend/src/hooks/useSchedules.js` | Schedule data fetching |
| `webui/frontend/src/components/scheduler/` | UI components |

### Terminology Changes

| Old Name | New Name |
|----------|----------|
| `EventPattern` | `Routine` |
| `PatternAction` | `Action` |
| `event_patterns` | `routines` |
| `pattern_id` | `routine_id` |
| `get_next_events()` | `preview_schedule()` |

---

## Documentation Structure

This guide is split into focused documents for efficient context management:

| Document | Purpose | When to Read |
|----------|---------|--------------|
| [Overview](./SCHEDULER_TERMINOLOGY_REFACTOR_OVERVIEW.md) | Architecture, schema changes, data structures | Start here for context |
| [Backend](./SCHEDULER_TERMINOLOGY_REFACTOR_BACKEND.md) | Backend implementation steps 1-7 | When implementing Python code |
| [Frontend](./SCHEDULER_TERMINOLOGY_REFACTOR_FRONTEND.md) | Component renames, hooks, UX | When implementing React code |
| [Testing](./SCHEDULER_TERMINOLOGY_REFACTOR_TESTING.md) | TDD workflow, fixtures, E2E | When writing tests |
| [Reference](./SCHEDULER_TERMINOLOGY_REFACTOR_REFERENCE.md) | Patterns, API spec, TimeWindow | Quick lookup during implementation |

---

## Implementation Checklist

> **TDD Workflow**: Each phase should follow the TDD approach defined in
> [Testing Strategy → TDD Approach](./SCHEDULER_TERMINOLOGY_REFACTOR_TESTING.md#tdd-approach-with-e2e-phases).
> Write tests first (expect failure), implement changes, verify tests pass.

### Phase 1: Backend Schema Refactor
- [ ] Rename `PatternAction` → `Action`
- [ ] Create `Routine` class with embedded trigger
- [ ] Add `pre_condition` field to Routine
- [ ] Update `Schedule` to use `routines` field
- [ ] Update all validate_* functions
- [ ] Add `validate_routine_ids_unique()`

### Phase 2: Cron Bridge Update
- [ ] Update `schedule_to_cron()` to iterate routines
- [ ] Add `_routine_recurring_days_to_cron()`
- [ ] Rename `get_next_events()` → `preview_schedule()`
- [ ] Add `detect_time_collisions()` function

### Phase 3: Supporting Module Updates
- [ ] Update `schedule_conflict.py` field names
- [ ] Update `schedule_storage.py` field references
- [ ] Update `scheduler_service.py` logging/caching
- [ ] Update `routes/scheduler_ui.py` API responses
- [ ] Add activate/deactivate endpoints

### Phase 4: Backend Tests
- [ ] Update test class names (TestPatternAction → TestAction, etc.)
- [ ] Add fixtures for all 7 trigger types
- [ ] Add tests for auto-generated names
- [ ] Add tests for mixed trigger schedules
- [ ] Verify 85% coverage

### Phase 5: Built-in Schedules
- [ ] Create `overnight-moth-survey.json`
- [ ] Create `daytime-pollinator.json`
- [ ] Add `/schedules/builtin` endpoint
- [ ] Test built-in schedule loading and activation

### Phase 6: Frontend Refactor
- [ ] Rename `PatternEditor/` → `RoutineEditor/`
- [ ] Rename `useEventPatterns.js` → `useRoutines.js`
- [ ] Add `TriggerSelector` component
- [ ] Add `RecurringDaysTriggerForm` component
- [ ] Add `PreConditionForm` component
- [ ] Remove PatternLibrary (replace with built-in schedules)

### Phase 7: Frontend Tests
- [ ] Rename test files to match component renames
- [ ] Update E2E selectors
- [ ] Add tests for new components
- [ ] Verify all frontend tests pass

### Phase 8: Documentation & Cleanup
- [ ] Update CLAUDE.md scheduler section
- [ ] Rewrite `webui/docs/dev/api/scheduler.md`
- [ ] Update/remove `webui/docs/dev/api/event-patterns.md`
- [ ] Update `webui/docs/dev/api/cron-bridge.md`
- [ ] Rewrite `webui/docs/SCHEDULER_USER_GUIDE.md`
- [ ] Archive planning docs (`webui/docs/dev/planning/scheduler/`)
- [ ] Archive refactor guide docs (`webui/docs/dev/guides/scheduler/`)

---

## Common Tasks

| Task | Document | Section |
|------|----------|---------|
| Rename a class | [Backend](./SCHEDULER_TERMINOLOGY_REFACTOR_BACKEND.md) | Step 1-3 |
| Add a new trigger type | [Reference](./SCHEDULER_TERMINOLOGY_REFACTOR_REFERENCE.md) | Pattern 4 |
| Write test fixtures | [Testing](./SCHEDULER_TERMINOLOGY_REFACTOR_TESTING.md) | Complete Fixtures |
| Run TDD workflow | [Testing](./SCHEDULER_TERMINOLOGY_REFACTOR_TESTING.md) | TDD Approach |
| Check API endpoints | [Backend](./SCHEDULER_TERMINOLOGY_REFACTOR_BACKEND.md) | API Updates |
| Update frontend component | [Frontend](./SCHEDULER_TERMINOLOGY_REFACTOR_FRONTEND.md) | Component Implementations |
| Update documentation | Phase 8 checklist above | Documentation & Cleanup |

---

## Related Documentation

- **TDD Workflow Guide**: `webui/docs/dev/guides/TDD_WORKFLOW.md`
- **Planning Doc**: `webui/docs/dev/planning/scheduler/SCHEDULER_TERMINOLOGY_REFACTOR.md`
- **Q&A Clarifications**: `webui/docs/dev/planning/scheduler/TERMINOLOGY_REFACTOR_CLARIFYING_QUESTIONS.md`
- **Scheduler API**: `webui/docs/dev/api/scheduler.md`
- **CLAUDE.md**: Visual Scheduler System section

---

## Success Criteria

- [ ] All backend tests pass with new terminology
- [ ] All frontend tests pass
- [ ] E2E scheduler tests pass
- [ ] Built-in schedules work out of box
- [ ] Auto-generated names display correctly
- [ ] No references to old names (`EventPattern`, `PatternAction`, `get_next_events`)
- [ ] One-time action use cases work (UV on at dusk, off at dawn)
