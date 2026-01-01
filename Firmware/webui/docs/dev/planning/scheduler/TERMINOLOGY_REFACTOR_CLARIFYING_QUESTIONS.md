# Scheduler Terminology Refactor - Clarifying Questions

**Issue**: #296
**Related Documents**:
- [Development Guide](../guides/scheduler/SCHEDULER_TERMINOLOGY_REFACTOR_DEV_GUIDE.md)
- [Planning Document](./SCHEDULER_TERMINOLOGY_REFACTOR.md)

**Purpose**: This document captures clarifying questions identified during review of the refactor documentation. Each question should be answered before implementation proceeds.

**Status Legend**:
- ⬜ Unanswered
- 🟡 In Discussion
- ✅ Answered

---

## 1. Trigger Architecture & Data Model

### Q1.1 ✅ RecurringDaysTrigger Missing
The planning doc (lines 104-110) describes a `RecurringDaysTrigger` type:
```python
RecurringDaysTrigger:
    every_n_days: int            # e.g., 3 for every 3 days
    time: str                    # "HH:MM" format
    start_date: str | None       # When to start counting
```
The dev guide makes NO mention of this trigger type.

**Question**: Should `RecurringDaysTrigger` be implemented, or was it removed from scope?

**Answer**: **Include in this refactor.** RecurringDaysTrigger should be implemented as described in the planning doc. It provides a user-friendly way to schedule "every N days" patterns without requiring expert cron knowledge.

---

### Q1.2 ✅ Trigger Type Storage
The dev guide shows `trigger_from_dict()` checking `data.get("trigger_type")`, but current trigger classes (IntervalTrigger, SolarTrigger, etc.) don't have a `trigger_type` field internally.

**Question**: Should each trigger class have a `trigger_type: str` field with a default value, or should `trigger_type` only exist during serialization?

**Answer**: ~~**Include `trigger_type` in serialization only, not as a class field.**~~ **UPDATED: Include `trigger_type` as class field with default.** Each trigger class has `trigger_type: str = "type_name"` as a field (e.g., `trigger_type: str = "interval"`). This makes serialization clean (`trigger.trigger_type`) and avoids `isinstance()` checks. The earlier answer was for the old architecture where Schedule held the trigger type. See Q20.2 for the correction.

---

### Q1.3 ✅ Trigger Union Type Identification
When iterating routines in `cron_bridge.py`, we need to determine which trigger type each routine has.

**Question**: Should we use `isinstance()` checks, or rely on a `trigger_type` attribute on each trigger class?

**Answer**: **Use `trigger_type` from serialized dict, NOT `isinstance()` checks.** The cron bridge works with dicts (from JSON), not class instances. The `trigger_type` field in the dict is the canonical discriminator: `routine["trigger"]["trigger_type"]` determines which converter function to call.

---

### Q1.4 ✅ MoonPhaseTrigger `offset_days` Field
The dev guide includes an `offset_days` field in MoonPhaseTrigger examples that is NOT in the planning doc.

**Question**: Should MoonPhaseTrigger have the `offset_days` field?

**Answer**: **Yes, keep `offset_days`.** It's useful for scenarios like "day before full moon" or "2 days after new moon". The field already exists in the current implementation.

---

### Q1.5 ✅ Time Window Solar References
The dev guide shows TimeWindow with solar event strings:
```json
"time_window": {
  "start_time": "sunrise",
  "end_time": "sunset"
}
```

**Question**: Can `TimeWindow.start_time/end_time` use solar event strings ("sunrise", "sunset"), or only fixed times ("22:00")?

**Answer**: **Yes, TimeWindow supports solar event strings.** This is existing functionality (see `nightly_moth_survey.json` line 42: `"start_time": "sunset"`). Essential for ecological surveys (e.g., "from sunset to sunrise"). No change needed.

---

## 2. Schedule & Routine Structure

### Q2.1 ✅ Schedule-level Date Constraints Removal
The guide removes `start_date`, `end_date`, and `days_of_week` from Schedule. However, this functionality may still be needed.

**Question**: Should date constraints move to per-routine triggers, be handled via TimeWindow, or be removed entirely?

**Answer**: **Remove from Schedule, keep in triggers where applicable.** `days_of_week` already exists on each trigger type - keep it there. `start_date`/`end_date` are removed from Schedule. Seasonal constraints can be handled by manually activating/deactivating schedules, or added to triggers in a future enhancement.

---

### Q2.2 ✅ `is_active` Field Retention
The planning doc shows only `enabled` for Schedule, but the dev guide retains both `enabled` and `is_active`.

**Question**: Should `is_active` be removed as part of this refactor, or retained?

**Answer**: **Keep both `enabled` and `is_active`.** They represent distinct concepts:
- `enabled` = user intent ("I want this schedule to be usable")
- `is_active` = runtime state ("This schedule is currently generating cron jobs")

A schedule can be enabled but not active. Only one schedule can have `is_active=True` at a time.

---

### Q2.3 ✅ Deployment Fields Retention
The dev guide shows `deployment_id` and `create_deployment` fields on Schedule, but the planning doc's simplified model doesn't include them.

**Question**: Should deployment-related fields be retained in Schedule or removed?

**Answer**: **Defer to late in implementation cycle.** Keep the fields in the schema for now, but don't prioritize deployment integration. Can be fully implemented or removed based on timeline.

---

### Q2.4 ✅ `total_duration_minutes` Property
The current Schedule has a `total_duration_minutes` property summing all pattern durations. With independent triggers per routine, the concept of "total duration" becomes unclear.

**Question**: Is this property still needed? If so, what should it calculate (max duration, sum, something else)?

**Answer**: **Remove from Schedule.** With per-routine triggers running at different times, "total duration" is meaningless. Each routine has its own `duration_minutes` (computed from max action offset).

---

### Q2.5 ✅ Routine `category` and `tags` Fields
EventPattern currently has `category` ("user" | "built-in") and `tags` fields used for filtering in the pattern library.

**Question**: Should Routine keep these fields, or remove them since the pattern library is being removed?

**Answer**: **Remove `category` and `tags` from Routine.** These were for the pattern library (filtering, categorization). Pattern library is being removed. Built-in vs user distinction moves to Schedule level (identified by storage location: `presets_builtin/schedules/`).

---

### Q2.6 ✅ Routine ID Generation Strategy
The dev guide suggests auto-generating `routine_id` if empty (UUID), but built-in examples show human-readable IDs like "attract-on-dusk".

**Question**: Should `routine_id` be:
- A) Auto-generated UUID if empty
- B) Always required (no auto-generation)
- C) Human-readable for built-in, UUID for user-created

**Answer**: **A) Auto-generate UUID if not provided.** Consistent with current `pattern_id` behavior. Human-readable IDs in built-in schedules are allowed but optional. UUIDs ensure uniqueness without coordination.

---

## 3. Auto-Generated Names

### Q3.1 ✅ Name Generation for Empty Actions
The dev guide shows `_generate_name()` returning "Empty" for empty actions list.

**Question**: Is this intended for validation to catch, or should empty routines with "Empty" name be allowed?

**Answer**: **Return "Empty Routine", but validation should reject.** A routine with zero actions is invalid and should fail validation. The "Empty Routine" name is a fallback that makes the validation error clearer.

---

### Q3.2 ✅ Duplicate Action Names in Summary
When actions contain duplicates like `["takephoto", "takephoto", "takephoto"]`:

**Question**: Should `_summarize_actions()` return:
- A) `"Photo"` (deduplicated)
- B) `"3 Actions"` (count only)
- C) `"3x Photo"` (count with type)

**Answer**: **C) Use count with type: "3x Photo".** Most informative for users.

---

### Q3.3 ✅ Sensor Trigger Description
The `_describe_trigger()` examples cover most trigger types but don't explicitly mention sensor triggers.

**Question**: What should the description format be for sensor triggers? (e.g., "on motion", "when light > 500")?

**Answer**: **Use human-readable condition format.** Examples (using Mothbox-available sensors):
- `"when light below 100"` for light threshold
- `"when temperature above 25"` for temperature threshold
- `"when humidity below 50"` for humidity threshold

**Note**: Mothbox does not have motion sensing capabilities. Examples should use available sensors: light, temperature, humidity.

---

### Q3.4 ✅ Fallback for Failed Name Generation
Edge case: both `name` is `None` AND `_generate_name()` returns empty string.

**Question**: What should `get_display_name()` return? Options:
- A) `"Unnamed Routine"`
- B) `"Routine {routine_id[:8]}"`
- C) Raise an error

**Answer**: **B) Return "Routine {routine_id[:8]}".** Always produces a valid, unique-ish name. Using first 8 chars of UUID is readable while maintaining uniqueness.

---

### Q3.5 ✅ Empty String vs Null Name Behavior
If `Routine.name` is explicitly set to `""` (empty string, not `None`), the code `if self.name:` is falsy.

**Question**: Should empty string trigger auto-generation, or be treated as an intentional (invalid) name?

**Answer**: **Treat empty string as "not set" - trigger auto-generation.** Empty string is effectively the same as `None` for name purposes. Normalize to `None` in `__post_init__` if empty string provided.

---

## 4. Validation Rules

### Q4.1 ✅ Empty Routines Array
**Question**: Can a schedule exist with zero routines (empty array)? If yes, what happens on activation?

**Answer**: **Invalid - reject in validation.** A schedule with no routines is useless. `validate_schedule()` should require at least one routine.

---

### Q4.2 ✅ Routine Count Limits
Currently `MAX_PATTERNS_PER_SCHEDULE = 10`.

**Question**: Should this:
- A) Be renamed to `MAX_ROUTINES_PER_SCHEDULE` with same limit
- B) Be renamed with a different limit
- C) Keep constant name for backwards compatibility, only update error messages

**Answer**: **A) Rename to `MAX_ROUTINES_PER_SCHEDULE`, keep limit at 10.** Clean break, no backwards compat needed.

---

### Q4.3 ✅ Routine ID Uniqueness Scope
**Question**: Must `routine_id` be:
- A) Unique within a schedule only
- B) Globally unique (like UUIDs)
- C) Duplicates allowed

**Answer**: **A) Unique within a schedule only.** UUIDs are practically unique globally anyway, but validation only needs to check within-schedule uniqueness.

---

### Q4.4 ✅ Cross-Routine GPIO State Validation
Example: Routine 1 turns UV on at dusk, Routine 2 turns UV off every 30 minutes.

**Question**: Should validation detect potential GPIO state conflicts across routines, or is that considered valid user intent?

**Answer**: **Detect and show as warnings (not blocking errors).** Validation should detect when a routine might turn off what another routine turned on. Show warnings in the preview timeline. User can acknowledge and proceed - it may be intentional.

---

### Q4.5 ✅ Trigger Type Combination Constraints
**Question**: Can a schedule have routines with any combination of trigger types? Are there constraints like:
- A) Maximum 1 cron trigger per schedule
- B) No mixing solar + interval
- C) No constraints - any combination allowed

**Answer**: **C) No constraints - any combination allowed.** The whole point of per-routine triggers is enabling mixed combinations like solar + interval + solar. No artificial limits.

---

## 5. Cron Bridge & Conflict Detection

### Q5.1 ✅ Multi-Trigger RTC Waketime Calculation
When a schedule has multiple routines with different trigger types (e.g., solar + interval + solar):

**Question**: How should RTC waketime be calculated?
- A) Earliest waketime across all routines
- B) Priority rules based on trigger type
- C) Each routine calculates independently

**Answer**: **A) Earliest waketime across all routines.** The Pi needs to wake before the first scheduled action. Calculate next execution time for each routine, use the minimum.

---

### Q5.2 ✅ Partial Cron Generation Failure
**Question**: If one routine's cron generation fails but others succeed, should:
- A) The entire schedule activation fail
- B) Only the failing routine be skipped (with warning)
- C) Return partial success with error details

**Answer**: **A) Entire schedule activation should fail.** A schedule should be all-or-nothing. Partial activation could leave the system in an inconsistent state. Return the specific error so user can fix it.

---

### Q5.3 ✅ Cross-Routine Conflict Detection Algorithm
Routines can have different trigger types (interval vs solar) that produce different execution times.

**Question**: How should conflicts be detected across routines? Should we:
- A) Calculate all execution times for all routines, then check for overlaps
- B) Only detect conflicts within the same routine
- C) Use a shared time calculation utility

**Answer**: **A) Calculate all execution times for all routines, then check for overlaps.** This includes both time collision detection (two routines executing simultaneously) and GPIO state conflict detection (warnings). Show conflicts in the preview timeline.

---

### Q5.4 ✅ Conflict Detection Window
Solar triggers use 7 days, moon phase uses 30 days for pre-calculation.

**Question**: When checking conflicts across multiple routines with different trigger types, what should the preview window be?
- A) Use the longest required window (30 days)
- B) Use a fixed window for consistency (e.g., 7 days)
- C) Configurable per-routine

**Answer**: **B) Use 7 days as default for conflict detection.** 30 days is too long for routine preview. Moon phase schedules that need longer preview can use the explicit preview endpoint with custom `days` parameter.

---

### Q5.5 ✅ Sensor Trigger Implementation Status
The current `cron_bridge.py` shows sensor triggers are stubbed (not implemented).

**Question**: Should this refactor:
- A) Maintain the stub (out of scope)
- B) Implement sensor triggers fully
- C) Remove sensor trigger type entirely

**Answer**: **Keep stub, develop as pre-conditions.** Sensor triggers should be included in this implementation as pre-conditions: "only execute scheduled action IF sensor condition is met at execution time". The real-time monitoring daemon for true event-driven triggers is a future enhancement. Document this clearly.

---

## 6. Built-in Schedules

### Q6.1 ✅ Existing Built-in Files Disposition
The `presets_builtin/schedules/` directory contains 10 existing schedule files using the old format (schedule-level triggers, `event_patterns`).

**Question**: Should these:
- A) Be replaced with new format files
- B) Be updated in-place to new format
- C) Coexist with new files (different names)
- D) Be removed entirely

**Answer**: **A) Replace with 2 new format files.** Create:
1. `overnight-moth-survey.json` - UV at dusk, photos overnight, UV off at dawn
2. `daytime-pollinator.json` - Photos during daylight hours

Remove the 10 existing files. Less is more for built-in templates.

---

### Q6.2 ✅ Built-in Schedule Loading Mechanism
**Question**: How are built-in schedules loaded and made available to users? Is there a preset manager service that needs updating?

**Answer**: Built-in schedules are loaded by `scheduler_service.py` from `presets_builtin/schedules/`. The service reads JSON files and returns them via `GET /schedules/builtin`. No separate preset manager - direct file loading with caching.

---

### Q6.3 ✅ Schema Version for New Format
Current built-in schedules use `"schema_version": "2.0"`.

**Question**: Should the new routine-based schedules use:
- A) `"3.0"` (breaking change indicator)
- B) `"2.1"` (minor version bump)
- C) `"2.0"` (structure change handled by validation)

**Answer**: **A) Use "3.0" to clearly indicate breaking change.** The structure is fundamentally different (trigger moved to routine). `"3.0"` signals to any tooling that this is incompatible with `"2.0"`.

---

### Q6.4 ✅ Missing Fields in Built-in Examples
Dev guide examples don't include `schema_version`, `created_at`, `modified_at`, `modified_by`, `is_active`.

**Question**: Should built-in schedule JSON files include these fields, or are they runtime-only?

**Answer**: **Include `schema_version` and `created_at` in JSON files.** Other fields (`modified_at`, `modified_by`, `is_active`) are runtime-only and should not be in the built-in JSON files.

---

## 7. API & Breaking Changes

### Q7.1 ✅ API Versioning Strategy
**Question**: Should the refactored API be versioned?
- A) Yes, use `/api/v2/scheduler/...`
- B) No, this is a breaking release (frontend updates atomically)
- C) No versioning, but provide deprecation warnings

**Answer**: **B) No versioning - this is a breaking release.** The scheduler is pre-release with no external consumers (confirmed via codebase analysis). Frontend and backend are in the same repo and deploy together.

---

### Q7.2 ✅ Backwards Compatibility Layer
**Question**: Should the backend support BOTH old (`event_patterns`) and new (`routines`) formats during a transition period?

**Answer**: **No backwards compatibility layer.** No existing user schedules (confirmed). Built-in schedules will be rewritten. Frontend updates atomically with backend. Clean break to new format.

---

### Q7.3 ✅ Deprecation Period Duration
If backwards compatibility is provided:

**Question**: How long should old fields/formats remain supported?
- A) One release cycle
- B) Until a specific date
- C) Permanent (no removal)
- D) N/A - no backwards compatibility

**Answer**: **D) N/A - no backwards compatibility needed.**

---

### Q7.4 ✅ Frontend-Backend Deployment Coordination
**Question**: Must frontend and backend deploy atomically, or can they be deployed independently?

**Answer**: **Atomic deployment.** Both are in the same repo and built together. The breaking schema change requires simultaneous frontend/backend updates.

---

### Q7.5 ✅ `/patterns/builtin` Endpoint Fate
Currently `GET /api/scheduler/ui/patterns/builtin` returns built-in event patterns.

**Question**: Should this endpoint:
- A) Be removed (breaking change)
- B) Return 410 Gone with migration guidance
- C) Be renamed to `/routines/builtin`
- D) Extract routines from built-in schedules (maintain functionality, new terms)

**Answer**: **A) Remove the endpoint.** Pattern library is being removed. Built-in schedules are accessed via `GET /schedules/builtin`. No need for a separate "routines" endpoint since routines are embedded in schedules.

---

### Q7.6 ✅ `/patterns/validate` Endpoint Changes
Currently `POST /api/scheduler/ui/patterns/validate` validates EventPattern structure.

**Question**: Should this:
- A) Become `POST /routines/validate`
- B) Accept both old and new formats
- C) Require additional parameters (lat/lon/tz) for trigger validation

**Answer**: **Remove the endpoint.** Routines are always validated as part of Schedule validation. Standalone routine validation is not useful since routines aren't created independently. `POST /schedules` and `PUT /schedules/{id}` already validate.

---

## 8. Frontend Components

### Q8.1 ✅ TriggerSelector vs TriggerForm Naming
The codebase already has `TriggerForm.jsx` that performs trigger type selection + delegating to specialized forms. The dev guide proposes creating `TriggerSelector`.

**Question**: Should we:
- A) Rename `TriggerForm` to `TriggerSelector`
- B) Keep `TriggerForm` name as-is
- C) Create new `TriggerSelector` and deprecate `TriggerForm`

**Answer**: **B) Keep `TriggerForm` name as-is.** The component already exists and works. No need to rename just for terminology. Focus on moving it into `RoutineEditor`.

---

### Q8.2 ✅ Trigger UI Location After Refactor
Currently trigger selection is in `ScheduleEditor`. With per-routine triggers:

**Question**: Should trigger selection UI:
- A) Move into `RoutineEditor`
- B) Stay in `ScheduleEditor` managing per-routine triggers
- C) Both components use `TriggerForm` in different contexts

**Answer**: **A) Move TriggerForm into RoutineEditor.** Each routine has its own trigger, so trigger configuration belongs in the routine editor. RoutineEditor becomes: trigger selection → action list.

---

### Q8.3 ✅ Built-in Schedule Selector Location
The PatternLibrary is being replaced with a "simple built-in schedule selector".

**Question**: Where should this new component be created?
- A) In `ScheduleEditor/` as a new component
- B) In a new `BuiltinSchedules/` directory
- C) Inline within `ScheduleEditor.jsx`

**Answer**: **A) In `ScheduleEditor/` as a new component.** Create `BuiltinScheduleSelector.jsx` in the ScheduleEditor directory. Keep it simple - just shows the 2 built-in options with a "clone and customize" action.

---

### Q8.4 ✅ Component Renaming Strategy
For renaming `PatternEditor/` → `RoutineEditor/`:

**Question**: Should we:
- A) Use `git mv` to preserve history
- B) Delete and recreate (cleaner but loses history)

**Answer**: **A) Use `git mv` to preserve history.** History is valuable for understanding why code exists. Use `git mv PatternEditor RoutineEditor`, then update internal references.

---

### Q8.5 ✅ RoutineEditor Props Interface
Current `PatternEditor` uses `{ pattern, onSave, onCancel }` (uncontrolled). Dev guide shows `{ routine, onChange }` (controlled).

**Question**: Which pattern should `RoutineEditor` use?
- A) Controlled: `onChange` called on every change
- B) Uncontrolled: `onSave` called only when user clicks save
- C) Support both patterns

**Answer**: **A) Controlled with `onChange`.** Since routines are edited inline (not in a modal), changes should flow up to ScheduleEditor immediately. This enables the schedule-level timeline to update in real-time as user edits routines.

---

### Q8.6 ✅ RoutineSelector Purpose
After removing PatternLibrary, what should `RoutineSelector` (renamed from `EventPatternSelector`) do?

**Question**: Should it:
- A) Allow adding/editing a single routine inline
- B) Show built-in complete schedules for quick start
- C) Still have tabs but simplified
- D) Be removed entirely

**Answer**: **D) Remove entirely.** The concept of "selecting a pattern" no longer applies. Users create routines inline in the schedule editor. Built-in schedules are a separate concept (full schedule cloning, not pattern selection).

---

## 9. State Management

### Q9.1 ✅ ScheduleEditor State Structure
Currently `ScheduleEditor` manages state for `trigger`, `patternSelection`, `dateRange`.

**Question**: After refactor, how should state be restructured?
- A) `routines: [{ trigger, actions }]` array at ScheduleEditor level
- B) Single routine editor that ScheduleEditor wraps multiple times
- C) Other structure (describe)

**Answer**: **A) `routines` array at ScheduleEditor level.** ScheduleEditor manages the full schedule state including `routines: [{ routine_id, name, trigger, actions }, ...]`. Each routine renders as a collapsible card with inline editing.

---

### Q9.2 ✅ Date Constraints in New Model
After removing schedule-level dates:

**Question**: Should there be ANY date constraints in the new model?
- A) Per-routine date ranges
- B) Only via TimeWindow in triggers
- C) No date constraints at all

**Answer**: **B) Only via TimeWindow in triggers.** TimeWindow already supports date-like constraints (days_of_week). Seasonal constraints are handled by manually activating/deactivating schedules. Keep it simple.

---

## 10. Testing

### Q10.1 ✅ Test Migration Strategy
**Question**: Should tests be:
- A) Updated atomically in one phase
- B) Updated incrementally as components are refactored
- C) Focus on integration tests first, then unit tests

**Answer**: **B) Updated incrementally, following TDD.** Write new tests FIRST for new code (TDD), update existing tests as components are refactored. Maintain coverage throughout.

---

### Q10.2 ✅ E2E Test Updates
Playwright tests (`scheduler-scenarios.spec.js`, etc.) test current pattern library workflow.

**Question**: Should these:
- A) Be updated to test new built-in schedule selector
- B) Be rewritten entirely for the new model
- C) Be temporarily disabled during refactor

**Answer**: **Hybrid approach (documented in dev guide):**
- **Pre-phase**: Run existing E2E tests, mark pattern-library tests as `skip`
- **During**: Write new E2E tests for new workflows FIRST (TDD), update skipped tests as components complete
- **Post-phase**: Remove obsolete tests, ensure all new workflows have coverage

---

### Q10.3 ✅ Coverage Target
The project has an 85% minimum coverage requirement.

**Question**: What coverage must be maintained during/after refactor?
- A) Same 85% minimum
- B) Higher target for scheduler modules specifically
- C) Coverage can temporarily drop during transition

**Answer**: **A) Maintain 85% minimum throughout.** No exceptions. TDD approach should naturally maintain coverage since tests are written first.

---

### Q10.4 ✅ Test Fixture Format
Test fixtures use the current EventPattern format.

**Question**: Should fixtures be:
- A) Updated to new format immediately
- B) Supported via backwards-compat aliases temporarily
- C) Regenerated from scratch

**Answer**: **A) Updated to new format immediately.** No backwards compat means fixtures must use new format. Update factories and fixtures in the schema refactor phase.

---

## 11. Documentation

### Q11.1 ✅ Planning Doc Contradiction
The planning doc says both:
- "Existing saved schedules migrate correctly" (line 435)
- "No migration needed - the scheduler is new" (line 331)

**Question**: Which is correct? Is migration needed or not?

**Answer**: **No migration needed.** Remove the contradictory line from the planning doc. There are no existing user schedules to migrate.

---

### Q11.2 ✅ User Guide Rewrite Scope
The User Guide has 68+ occurrences of "event pattern" terminology.

**Question**: Is updating the User Guide in scope for this refactor, or a separate task?

**Answer**: **In scope for this refactor (same PR/issue).** Documentation is part of the Definition of Done. Update User Guide as part of Phase 8 (Documentation & Cleanup).

---

### Q11.3 ✅ API Documentation Source of Truth
Three API docs exist: `scheduler.md`, `scheduler-ui.md`, and the refactor guide.

**Question**: Which is authoritative post-refactor? Should they be consolidated?

**Answer**: **Consolidate into `scheduler.md` as single source of truth.** Remove `scheduler-ui.md` (merge relevant content into main doc). The refactor dev guide is a one-time planning doc, not ongoing API reference.

---

## 12. Backwards Compatibility

### Q12.1 ✅ Alias Duration
The dev guide shows temporary aliases:
```python
PatternAction = Action
EventPattern = Routine
```

**Question**: How long should these aliases be maintained?
- A) One release cycle
- B) Until all external code is migrated
- C) Permanent for backwards compatibility
- D) Remove immediately (no aliases)

**Answer**: **D) No aliases needed.** No external consumers exist (confirmed via codebase analysis). Clean break without aliases.

---

### Q12.2 ✅ Old Format Schedule Reading
The guide says "no migration needed" because no schedules exist yet.

**Question**: Should `Schedule.from_dict()` defensively handle old format if an old schedule file somehow exists?

**Answer**: **No defensive handling.** If an old format file somehow exists, it should fail loudly with a clear schema version error. This surfaces problems immediately rather than silently mis-parsing data.

---

### Q12.3 ✅ Error Message Terminology Transition
**Question**: Should error messages change from "pattern" to "routine" immediately, or maintain old terminology during transition?

**Answer**: **Change immediately to "routine".** No transition period. Clean break.

---

## 13. Edge Cases

### Q13.1 ✅ GPIO State Across Routine Failures
Example: Routine A turns UV on at dusk. Routine B turns UV off at dawn. Routine A fails, Routine B succeeds.

**Question**: Could this leave lights in wrong state? Should there be safeguards?

**Answer**: **Yes, this could leave lights in wrong state. Show as warning, not blocking error.** The conflict detection system should identify this as a GPIO state dependency and warn users. However, since cron jobs execute independently, we cannot guarantee atomicity. Document this limitation.

---

### Q13.2 ✅ Action Offset Semantics
Currently action offsets are "relative to pattern start" (t=0 when pattern triggers).

**Question**: With per-routine triggers, are offsets still "relative to routine start" (t=0 when routine triggers)?

**Answer**: **Yes, offsets remain "relative to routine start".** When a routine's trigger fires, t=0 begins. Action offsets are minutes from that trigger time. No change to the concept, just the terminology (pattern → routine).

---

### Q13.3 ✅ Cron Expression Action Offsets
Expert mode cron triggers currently don't support action offsets (line 1121 note).

**Question**: Should offsets be supported in expert cron mode by generating multiple time-shifted cron entries?

**Answer**: **Keep current behavior - no offset support in expert cron mode.** Expert mode users are expected to understand cron. If they need offsets, they can create multiple cron entries manually or use a different trigger type.

---

### Q13.4 ✅ Overlapping Time Windows Across Routines
When an interval trigger has a time window ("22:00" to "06:00") and a solar trigger fires at "dusk" (within that window):

**Question**: Should conflict detection flag potential overlaps, or only flag actual execution time collisions?

**Answer**: **Flag actual execution time collisions only.** Time window overlap is not inherently a problem - only flag when two routines would actually execute at the same time (within some tolerance, e.g., 1 minute).

---

### Q13.5 ✅ Schedule-wide Time Constraints Location
Example requirement: "Only run this schedule in summer months"

**Question**: Where should schedule-wide seasonal/date constraints live now that schedule-level dates are removed?

**Answer**: **Handle via manual activation/deactivation.** Users activate their "summer survey" schedule in May and deactivate in September. Future enhancement could add schedule-level date ranges, but for now keep it simple.

---

## Decision Log

| Question | Decision | Date | Decided By |
|----------|----------|------|------------|
| Q1.1 | Include RecurringDaysTrigger | 2025-12-31 | Team |
| Q1.2-Q1.5 | Serialization-only trigger_type, solar TimeWindow supported | 2025-12-31 | Team |
| Q2.1-Q2.6 | Remove schedule dates, keep is_active, defer deployment, remove tags | 2025-12-31 | Team |
| Q3.1-Q3.5 | Auto-name formats defined | 2025-12-31 | Team |
| Q4.1-Q4.5 | Validation rules, GPIO warnings not blocking | 2025-12-31 | Team |
| Q5.1-Q5.5 | Conflict detection algorithm, sensor pre-conditions | 2025-12-31 | Team |
| Q6.1-Q6.4 | Replace with 2 built-ins, schema 3.0 | 2025-12-31 | Team |
| Q7.1-Q7.6 | No versioning, no backwards compat, remove pattern endpoints | 2025-12-31 | Team |
| Q8.1-Q8.6 | Keep TriggerForm name, inline editing, controlled props | 2025-12-31 | Team |
| Q9.1-Q9.2 | Routines array state, TimeWindow only for dates | 2025-12-31 | Team |
| Q10.1-Q10.4 | TDD approach, hybrid E2E strategy, 85% coverage | 2025-12-31 | Team |
| Q11.1-Q11.3 | No migration, User Guide in scope, consolidate API docs | 2025-12-31 | Team |
| Q12.1-Q12.3 | No aliases, no defensive handling, immediate terminology | 2025-12-31 | Team |
| Q13.1-Q13.5 | GPIO warnings, offsets from routine start, time collision detection | 2025-12-31 | Team |

---

## User Stories for Conflict Detection

### US1: Time Collision Detection
> **As a** researcher setting up a moth survey,
> **I want** the scheduler to warn me when two routines would execute at the exact same time,
> **So that** I don't have conflicting camera/GPIO operations.

**Acceptance Criteria**:
- [ ] Preview shows overlapping executions highlighted in red
- [ ] Validation endpoint returns conflict details
- [ ] User can proceed with warning (not blocking)

### US2: GPIO State Conflict Detection
> **As a** researcher using UV attract lights,
> **I want** the scheduler to warn me if my routines might leave lights in an unexpected state,
> **So that** I don't accidentally leave UV lights on all night or off when expected on.

**Acceptance Criteria**:
- [ ] Validation detects when a routine might turn off what another turned on
- [ ] Warning shows which GPIO states may conflict
- [ ] Warnings shown in preview timeline
- [ ] User can acknowledge and proceed (not blocking)

### US3: Cross-Routine Dependency (Future Enhancement - Not in scope)
> **As an** advanced user,
> **I want** to define explicit dependencies between routines,
> **So that** "UV off at dawn" only executes if "UV on at dusk" succeeded.

---

## Frontend UX Decisions

### Routine List Display
- **Collapsed state**: Show auto-generated name + trigger type badge
- **Expanded state**: Full TriggerForm + ActionList with inline editing

### Schedule-Level Timeline
- Show all routine executions on a unified timeline
- Highlight conflicts (time collisions in red, GPIO warnings in yellow)

### Add Routine Flow (Inline Wizard)
1. Click [+ Add Routine]
2. Select trigger type (dropdown)
3. Configure trigger parameters
4. Add actions
5. Done (no explicit save - controlled component)

---

## Notes

- All Round 1 questions have been answered as of 2025-12-31
- Round 2 questions added 2026-01-01 from documentation review
- Implementation can proceed following the phased approach in the dev guide
- Dev guide should be updated with explicit Pre/During/Post phase sections for E2E testing

---

## Round 2: Documentation Review Questions (2026-01-01)

These questions were identified during review of the implementation guides prior to implementation.

---

## 13. Data Model Structure

### Q13.1 ✅ Actions Within Routines vs Standalone Actions

The refactor needs to decide whether actions can exist both within routines AND as standalone items at the schedule level, or only within routines.

**Context**: The original use case is "at 2100 turn on UV, between 2200-0500 take photos every 15min, at 0600 turn off UV". This could be modeled as:
- **Model A**: Three routines (each with trigger + action(s))
- **Model B**: Two standalone actions + one routine

**Question**: Should actions only exist within routines, or both within routines and standalone?
- A) Actions only within Routines (simpler schema, single validation/cron path)
- B) Actions both in Routines and standalone at Schedule level (more expressive, dual paths)

**Answer**: **A) Actions only within Routines.** This provides:
- Single validation code path
- Single cron generation code path
- Uniform data model (everything is a Routine)
- Smaller error surface

**UI Requirement**: The frontend must streamline the "Add Action" workflow so users don't feel the burden of creating a routine wrapper for single actions. For example:
- "Quick Add Action" button that auto-creates a routine with one action
- Routine cards that display as simple action cards when they contain only one action
- Auto-generated routine names based on trigger + action (e.g., "Attract On at Dusk")

This decision supersedes the archived ONE_TIME_ACTIONS approach which added `one_time`, `fixed_time`, `solar_event` fields directly on actions.

---

## 14. Cron Generation Performance

### Q14.1 ✅ Cron Generation Performance Strategy

The documentation mentions "~60,000 entries over 5 years" and "~6MB crontab" but doesn't address performance considerations.

**Context**: Writing 60K cron entries to the system crontab could be slow or hit limitations.

**Question**: How should cron generation handle performance?
- A) Write all entries at once via `crontab -` pipe
- B) Batch writes with progress feedback
- C) Use a separate cron file (e.g., `/etc/cron.d/mothbox-schedule`)
- D) Store entries in SQLite and use a dispatcher script

**Considerations**:
- Memory usage during pre-computation
- Write time to crontab
- System crontab size limits (if any)
- User feedback during activation

**Answer**: **A) Keep current approach (atomic write via python-crontab).** The existing implementation already uses `python-crontab` which buffers in memory and writes atomically. 60K entries (~6MB) writes in <1 second on Pi hardware. Memory usage (~12MB for entry objects) is acceptable for Pi 4/5.

**Additional recommendation**: Add progress feedback during the *computation* phase (calculating 5 years of solar/moon times), not the write phase. Consider a WebSocket progress event or polling endpoint for long activations.

---

### Q14.2 ✅ Calculate Execution Times Helper Implementations

The Reference doc shows `calculate_execution_times()` dispatching to helpers like `_calculate_interval_times()`, `_calculate_solar_times()`, etc., but implementations are not provided.

**Question**: Should these helper implementations be:
- A) Documented in the Backend guide with skeleton code
- B) Left as implementation details (current approach)
- C) Extracted to a separate "Cron Algorithms" reference doc

**Answer**: **B) Left as implementation details.** The Backend doc already provides the dispatch pattern, `datetime_to_cron()` conversion, and `CronEntry` structure. The helper implementations are mechanical given the trigger field definitions - an implementer can derive them from the trigger schemas without additional documentation.

---

## 15. TimeWindow Edge Cases

### Q15.1 ✅ Overnight Time Windows

TimeWindow can specify overnight ranges like `"22:00"` to `"06:00"`.

**Question**: How should overnight windows be handled?
- A) Detect when end < start and treat as overnight (already implemented?)
- B) Require explicit `is_overnight: true` flag
- C) Document the current behavior without changes

**Related**: What happens if start and end are the same time (24-hour window or zero-length)?

**Answer**: **C) Document the current behavior without changes.** The codebase already detects overnight windows automatically when `end < start` (see `cron_bridge.py:253-255`, `schedule_conflict.py:497-499`). No code changes needed.

**For same-time edge case**: Add validation to reject `start_time == end_time` as invalid (ambiguous: zero-length or 24-hour?). If a user wants "all day", they should omit the time window entirely.

---

### Q15.2 ✅ Solar Events at Extreme Latitudes

At polar latitudes, sunrise/sunset may not occur on certain days (polar day/night).

**Question**: How should solar triggers handle locations where the solar event doesn't occur?
- A) Skip that day silently
- B) Log warning and skip
- C) Use nearest valid time (e.g., solar noon for missing sunrise)
- D) Fail validation if location is in polar region

**Answer**: **B) Log warning and skip.** When a solar event doesn't occur on a specific date (polar day/night), log a warning with the date and skip that day's entry. The `solar_time.py` library already returns `None`/raises `ValueError` for these cases - the cron generation code should catch this and log appropriately.

**Note**: This is unlikely to affect real-world Mothbox deployments, which are typically in temperate/tropical regions. Polar researchers would need to use fixed-time triggers instead of solar triggers during polar day/night periods.

---

## 16. Pre-Condition Runtime Evaluation

### Q16.1 ✅ Pre-Condition Execution Mechanism

Q&A says pre-conditions are "sensor checks before execution" but the runtime mechanism is unclear.

**Question**: How are pre-conditions evaluated at execution time?
- A) Wrapper script checks sensor before running action
- B) Action script itself checks and exits early
- C) Separate pre-check cron entry before action entry
- D) Not implemented in this refactor (stub only)

**Follow-up**: If (D), should this be explicitly documented as "future enhancement"?

**Answer**: **A) Wrapper script checks sensor before running action.** Implement a `check_and_run.py` wrapper that:
1. Parses pre-condition parameters (sensor type, operator, threshold)
2. Calls existing `check_precondition()` from `sensor_reader.py`
3. If met: executes the wrapped command
4. If not met: logs "Pre-condition not met, skipping" and exits cleanly

Cron generation appends the wrapper when `routine.pre_condition` is set:
```
python3 /opt/mothbox/check_and_run.py --sensor light --op below --threshold 100 -- python3 TakePhoto.py
```

---

### Q16.2 ✅ Pre-Condition Failure Logging

When a pre-condition is not met and actions are skipped:

**Question**: How should this be logged/reported?
- A) Log to system journal only
- B) Log to Mothbox application log
- C) Record in a "skipped executions" table for UI visibility
- D) No logging (silent skip)

**Answer**: **B) Log to Mothbox application log.** The `check_and_run.py` wrapper logs using Python's `logging` module (already used throughout the codebase). Log entry format:
```
INFO: Pre-condition met (light=45 < 100), executing: python3 TakePhoto.py
WARNING: Pre-condition NOT met (light=250 >= 100), skipping: python3 TakePhoto.py
```
This provides debugging visibility without adding database complexity. A future enhancement could add UI visibility for skipped executions.

---

## 17. Frontend Name Generation

### Q17.1 ✅ Auto-Generated Name Source of Truth

Backend has `Routine.get_display_name()` and Frontend has `getAutoGeneratedName()`. Both generate names from trigger/actions.

**Question**: Should frontend:
- A) Mirror backend logic exactly (risk of drift)
- B) Always use backend-provided `display_name` field (add to API response)
- C) Generate locally for preview, use backend value after save
- D) Keep current approach, accept potential drift

**Answer**: **C) Generate locally for preview, use backend value after save.** Frontend generates names for immediate preview during editing. After save, the API response includes a `display_name` field computed by `Routine.get_display_name()`. The UI updates to show the backend's authoritative name. Minor drift during editing is acceptable since the saved value is always consistent.

---

## 18. Built-in Schedule Operations

### Q18.1 ✅ Clone Workflow

Docs mention users can "clone and customize" built-in schedules but the workflow is unclear.

**Question**: How does cloning work?
- A) Frontend copies data, POSTs to `POST /schedules` as new schedule
- B) Backend endpoint `POST /schedules/{id}/clone` handles duplication
- C) Frontend shows "use as template" which pre-fills the editor

**Follow-up**: Does cloning clear `is_builtin` flag? Generate new `schedule_id`?

**Answer**: **A) Frontend copies data, POSTs to `POST /schedules` as new schedule.** This is **already implemented** in `useSchedulePatterns.js`:
- `useDuplicateSchedule()` - clones any schedule with a new name
- `useScheduleFromTemplate()` - creates from built-in template with customizations

Both hooks:
1. Fetch source schedule
2. Remove read-only fields (`id`, `schedule_id`, `created_at`, `modified_at`, `category`)
3. Apply new name/customizations
4. POST to `createSchedule()` - backend generates new UUID

No changes needed for this refactor.

---

### Q18.2 ✅ Built-in Schedule Immutability

Built-in schedules are stored in `presets_builtin/schedules/`.

**Question**: Can users modify built-in schedules?
- A) No - UI prevents editing, only clone allowed
- B) Yes - modifications saved to user storage, shadowing built-in
- C) Yes - built-in files are modified in place (not recommended)

**Answer**: **A) No - UI prevents editing, only clone allowed.** This is **already implemented**:
- `PUT /schedules/{id}` returns 403 Forbidden for built-in schedules
- `DELETE /schedules/{id}` returns 403 Forbidden for built-in schedules
- Backend uses `is_builtin_schedule()` check in service layer
- Users must clone (via `useScheduleFromTemplate()`) to customize

No changes needed for this refactor.

---

## 19. API Response Consistency

### Q19.1 ✅ Error Response Schema

The Backend doc shows different error response formats:
- Simple: `{"error": "message"}`
- Complex: `{"error": "message", "errors": [...], "warnings": [...]}`

**Question**: Should we standardize on a single error response schema?

**Proposed Standard**:
```json
{
  "success": false,
  "error": "Human-readable summary",
  "errors": [{"type": "...", "message": "...", "field": "..."}],
  "warnings": [{"type": "...", "message": "..."}]
}
```

**Answer**: **Keep current contextual approach.** The codebase already uses appropriate formats for different contexts:
- Simple errors: `{"error": "message"}`
- Validation: `{"valid": false, "error": "...", "errors": [...]}`
- Bulk operations: `{"success": [...], "failed": [...], "errors": {...}}`

Enforcing a single rigid schema would add complexity without clear benefit. The scheduler refactor should follow existing patterns for each endpoint type.

---

### Q19.2 ✅ Success Response with Warnings

When a schedule saves successfully but has GPIO state warnings:

**Question**: What HTTP status code should be returned?
- A) 201 Created with warnings in body
- B) 207 Multi-Status
- C) 200 OK with `"has_warnings": true` flag

**Answer**: **A) 201 Created with warnings in body.** The schedule saved successfully (201), so the HTTP status reflects that. Warnings are informational, not errors. Response includes a `warnings` array that frontend can display as non-blocking alerts:
```json
{
  "schedule_id": "abc123",
  "name": "Nightly Survey",
  "warnings": [{"type": "gpio_conflict", "message": "..."}]
}
```
Frontend checks `response.warnings?.length > 0` to show warning toast/banner.

---

## 20. Documentation Maintenance

### Q20.1 ✅ Line Number References

Backend doc references specific line numbers (e.g., "lines 170-222") which will become stale.

**Question**: Should we:
- A) Remove line number references
- B) Replace with class/function name references
- C) Keep them, accept they'll need updating
- D) Use code search patterns instead (e.g., "search for `class PatternAction`")

**Answer**: **C) Keep them, accept they'll need updating.** The implementation guides are active during development and archived after completion (Phase 8). Line numbers provide precision during implementation. Post-refactor, the guides are archived and line numbers become irrelevant. No action needed.

---

### Q20.2 ✅ Trigger Type Field Inconsistency

Q1.2 answer says "Include `trigger_type` in serialization only, not as a class field."

But Backend doc shows:
```python
@dataclass
class RecurringDaysTrigger:
    trigger_type: str = "recurring_days"  # <-- This IS a class field
```

**Question**: Which is correct?
- A) Q1.2 is correct - remove `trigger_type` from class definitions
- B) Backend doc is correct - keep `trigger_type` as class field with default
- C) Hybrid - optional class field that defaults correctly

**Answer**: **B) Backend doc is correct - keep `trigger_type` as class field with default.** In the new architecture:
- Schedule has no trigger (only `enabled`/`is_active`)
- Routine has `trigger: Trigger` (union type)
- Each trigger class should have `trigger_type` as a field with default (e.g., `trigger_type: str = "interval"`)

This makes serialization clean (`trigger.trigger_type`) and avoids `isinstance()` checks. Q1.2's answer was written for the old architecture where `trigger_type` was on Schedule - it should be updated to reflect that trigger classes themselves need the discriminator field.

---

### Q20.3 ✅ Archive Structure

Phase 8 mentions archiving planning docs but doesn't define the structure.

**Question**: Where should archived docs go?
- A) `webui/docs/dev/planning/scheduler/archived/`
- B) `webui/docs/dev/archived/scheduler/`
- C) `webui/docs/archived/`
- D) Delete rather than archive (git history preserves)

**Answer**: **A) `webui/docs/dev/planning/scheduler/archived/`.** Move completed planning docs into an `archived/` subdirectory within their current location. This preserves organizational structure while clearly marking them as historical reference. This directory already exists with ONE_TIME_ACTIONS_* docs. Files to archive post-implementation:
- `SCHEDULER_TERMINOLOGY_REFACTOR.md` (original proposal)
- `TERMINOLOGY_REFACTOR_CLARIFYING_QUESTIONS.md` (this Q&A doc)

---

## 21. Implementation Approach

### Q21.1 ✅ Implementation Start Point

**Question**: Given the current state, which phase should implementation start with?
- A) Phase 1 (Backend Schema) - docs are most complete here
- B) Phase 4 (Backend Tests) - TDD approach, write tests first
- C) Phase 5 (Built-in Schedules) - quick win, validates schema design
- D) Start with resolving Round 2 questions first

**Answer**: **B) TDD approach, but documentation needs updating first.**

**Gap identified**: The Testing doc (`SCHEDULER_TERMINOLOGY_REFACTOR_TESTING.md`) describes a TDD workflow with Pre/During/Post phases, but the Backend and Frontend docs' checklists don't integrate TDD steps. The checklists say "All tests pass" but don't say "write tests first."

**Before implementation begins**, update the implementation docs to integrate TDD:

1. **Update `SCHEDULER_TERMINOLOGY_REFACTOR_INDEX.md`** (or remove if stale):
   - Restructure phases to reflect TDD workflow
   - Or add note that it's superseded by individual guides

2. **Update Backend doc checklists** to include TDD steps:
   ```
   ### Step 1: Rename Action Class
   - [ ] Write unit tests for Action class (test_action_creation, test_action_to_dict)
   - [ ] Run tests (should fail - class doesn't exist yet)
   - [ ] Rename PatternAction → Action
   - [ ] Run tests (should pass)
   ```

3. **Update Frontend doc checklists** similarly

4. **Add E2E skeleton checklist** at start of implementation:
   ```
   ### Pre-Implementation (E2E Skeletons)
   - [ ] Create e2e/scheduler-terminology-refactor.spec.js
   - [ ] Write skeleton test: create schedule with multiple trigger types
   - [ ] Write skeleton test: auto-generated routine names display
   - [ ] Write skeleton test: schedule preview shows timeline
   - [ ] Run E2E tests (should fail - expected)
   ```

**Implementation order after doc updates**:
1. Write E2E skeleton tests
2. Follow Backend doc steps with integrated TDD checklists
3. Follow Frontend doc steps with integrated TDD checklists
4. Verify E2E tests pass

---

### Q21.2 ✅ Inline Documentation Updates

**Question**: Should documentation be updated during implementation or deferred to Phase 8?
- A) Update inline as gaps are discovered
- B) Defer all doc updates to Phase 8
- C) Update implementation guides inline, defer user-facing docs to Phase 8

**Answer**: **C) Update implementation guides inline, defer user-facing docs to Phase 8.**

- **Inline updates**: Backend, Frontend, Testing docs, Q&A doc - update as gaps/decisions are discovered during implementation
- **Deferred updates**: SCHEDULER_USER_GUIDE.md, API docs (scheduler.md, cron-bridge.md), CLAUDE.md scheduler section - batch update after implementation is stable

This keeps developer docs accurate while avoiding premature user doc updates that may need revision.

---

## Round 2 Decision Log

| Question | Decision | Date | Decided By |
|----------|----------|------|------------|
| Q13.1 | A - Actions only within Routines + UI streamlining | 2026-01-01 | Team |
| Q14.1 | A - Keep atomic write, add computation progress | 2026-01-01 | Team |
| Q14.2 | B - Leave as implementation details | 2026-01-01 | Team |
| Q15.1 | C - Document existing behavior, validate same-time | 2026-01-01 | Team |
| Q15.2 | B - Log warning and skip | 2026-01-01 | Team |
| Q16.1 | A - Wrapper script (check_and_run.py) | 2026-01-01 | Team |
| Q16.2 | B - Mothbox application log | 2026-01-01 | Team |
| Q17.1 | C - Local preview, backend value after save | 2026-01-01 | Team |
| Q18.1 | A - Frontend copies (already implemented) | 2026-01-01 | Team |
| Q18.2 | A - Immutable (already implemented) | 2026-01-01 | Team |
| Q19.1 | Keep contextual approach | 2026-01-01 | Team |
| Q19.2 | A - 201 Created with warnings in body | 2026-01-01 | Team |
| Q20.1 | C - Keep, will be archived | 2026-01-01 | Team |
| Q20.2 | B - Keep trigger_type as class field | 2026-01-01 | Team |
| Q20.3 | A - planning/scheduler/archived/ | 2026-01-01 | Team |
| Q21.1 | B - TDD, update docs first | 2026-01-01 | Team |
| Q21.2 | C - Impl guides inline, user docs deferred | 2026-01-01 | Team |

---

*Document created: 2025-12-31*
*Last updated: 2026-01-01 (Round 2 questions added)*
