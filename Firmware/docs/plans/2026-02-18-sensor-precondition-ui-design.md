# Sensor Pre-Condition UI Design

**Issue**: #271 — feat(ui): Add frontend controls for sensor pre-condition configuration
**Date**: 2026-02-18
**Status**: Approved

## Context

The backend for sensor pre-conditions is complete: `SensorTrigger` dataclass, `sensor_reader.py`, `check_and_run.py`, and cron bridge integration. A `PreConditionForm` component already exists with toggle, sensor type, comparison, and threshold — but it's not wired into the routine editing UI and lacks cooldown and time window fields.

## Approach

Enhance the existing `PreConditionForm` and integrate it into `RoutineCard` and `NewRoutineCard`, nested inside the Trigger section to keep it visually subordinate.

## Design

### 1. PreConditionForm Enhancements

Add to the existing component (`ScheduleEditor/PreConditionForm.jsx`):

- **Unit label**: Dynamic suffix next to threshold — "lux" for light, "°C" for temperature
- **Cooldown input**: Number input (1-60 min), default 5. Uses `validateNumericInput`
- **Time window**: Secondary toggle "Restrict to time window" with start/end HH:MM inputs. Uses `TIME_FORMAT_REGEX` for validation. `null` when off.

Layout when expanded:
```
[x] Only run if sensor condition met
    [Light v]  [is below v]  [100] lux
    Cooldown: [5] minutes
    [ ] Restrict to time window
        [21:00] to [06:00]
```

### 2. RoutineCard Integration

- Import `PreConditionForm` into `RoutineCard.jsx`
- Render inside the Trigger `<div>` after `<TriggerSelector>` with small top margin
- `handlePreConditionChange` callback updates `routine.pre_condition` via `onUpdate`
- Pass `routine.pre_condition` as `preCondition` prop

### 3. NewRoutineCard Integration

- Same pattern: `PreConditionForm` after `<TriggerSelector>` in Trigger div
- Add `preCondition` local state (default `null`)
- Include `pre_condition` in routine object on save

### 4. Collapsed Header Badge

- When `routine.pre_condition` is truthy, render "Gated" badge in `RoutineCard` header
- Positioned between `TriggerLabel` and `ChevronDownIcon`
- Styling: `text-xs text-amber-500/70 font-medium`

### 5. Data Flow

```
PreConditionForm → null | { trigger_type, sensor_type, comparison, threshold, cooldown_minutes, time_window }
  → RoutineCard.handlePreConditionChange → onUpdate({ ...routine, pre_condition })
  → ScheduleEditor saves to backend
  → Backend validate_sensor_trigger() validates (no backend changes needed)
```

### 6. PropTypes

Update `RoutinePropType` in `propTypes.js` to include optional `pre_condition` shape.

### 7. Error Handling

- Invalid cooldown: Inline error, don't propagate
- Invalid time window: Inline error if start >= end (allow overnight spans)
- Sensor unavailability: Not handled in UI — `check_and_run.py` handles at execution time (exit code 69)

## Testing Plan

- **PreConditionForm**: ~12 new tests for cooldown validation, time window toggle/validation, unit label display
- **RoutineCard**: ~5 new tests for pre-condition rendering, badge, change propagation
- **NewRoutineCard**: ~3 new tests for state management, inclusion in saved routine
- No backend test changes needed

## Files Modified

- `webui/frontend/src/components/scheduler/ScheduleEditor/PreConditionForm.jsx` — add fields
- `webui/frontend/src/components/scheduler/ScheduleEditor/RoutineCard.jsx` — integrate
- `webui/frontend/src/components/scheduler/ScheduleEditor/NewRoutineCard.jsx` — integrate
- `webui/frontend/src/components/scheduler/ScheduleEditor/propTypes.js` — update RoutinePropType
- `webui/frontend/src/components/scheduler/ScheduleEditor/__tests__/PreConditionForm.test.jsx` — new tests
- `webui/frontend/src/components/scheduler/ScheduleEditor/__tests__/RoutineCard.test.jsx` — new tests
- `webui/frontend/src/components/scheduler/ScheduleEditor/__tests__/NewRoutineCard.test.jsx` — new tests
