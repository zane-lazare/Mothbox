# Scheduler Terminology Refactor - Testing Strategy

**Purpose**: TDD workflow, test fixtures, E2E strategy for the refactor.

**Prerequisites**: Read [Overview](./SCHEDULER_TERMINOLOGY_REFACTOR_OVERVIEW.md) for context.

**Related Guide**: [TDD Workflow](../TDD_WORKFLOW.md)

---

## Table of Contents

1. [TDD Approach with E2E Phases](#tdd-approach-with-e2e-phases)
2. [Unit Tests to Update](#unit-tests-to-update)
3. [Complete Test Fixtures](#complete-test-fixtures)
4. [E2E Test Transition Strategy](#e2e-test-transition-strategy)
5. [New Tests to Add](#new-tests-to-add)

---

## TDD Approach with E2E Phases

This refactor follows a hybrid TDD approach with explicit Pre/During/Post phases for E2E testing.

### Pre-Implementation Phase (E2E Tests Written First)

**Goal**: Define expected behavior before code changes

1. **Write skeleton E2E tests** that describe the complete user workflow:

```javascript
// e2e/scheduler-terminology-refactor.spec.js
test.describe('Scheduler Terminology Refactor', () => {
  test('user can create schedule with multiple trigger types', async ({ page }) => {
    // Navigate to scheduler
    await page.goto('/scheduler');

    // Create new schedule
    await page.click('[data-testid="create-schedule"]');
    await page.fill('[data-testid="schedule-name"]', 'Overnight Moth Survey');

    // Add solar trigger routine (dusk)
    await page.click('[data-testid="add-routine"]');
    await page.selectOption('[data-testid="trigger-type"]', 'solar');
    await page.selectOption('[data-testid="solar-event"]', 'dusk');
    await page.click('[data-testid="add-action"]');
    await page.selectOption('[data-testid="action-name"]', 'attract_on');

    // Add interval trigger routine (photos every 15min)
    await page.click('[data-testid="add-routine"]');
    await page.selectOption('[data-testid="trigger-type"]', 'interval');
    await page.fill('[data-testid="interval-minutes"]', '15');
    // ... add photo actions

    // Add solar trigger routine (dawn)
    await page.click('[data-testid="add-routine"]');
    await page.selectOption('[data-testid="trigger-type"]', 'solar');
    await page.selectOption('[data-testid="solar-event"]', 'dawn');
    await page.click('[data-testid="add-action"]');
    await page.selectOption('[data-testid="action-name"]', 'attract_off');

    // Save and verify
    await page.click('[data-testid="save-schedule"]');
    await expect(page.locator('[data-testid="schedule-saved"]')).toBeVisible();
  });

  test('auto-generated routine names display correctly', async ({ page }) => {
    await page.goto('/scheduler');
    await page.click('[data-testid="overnight-moth-survey"]');

    await expect(page.locator('[data-testid="routine-name"]').first())
      .toContainText('Attract On at Dusk');
  });

  test('schedule preview shows timeline with all routines', async ({ page }) => {
    // Test preview timeline shows events from all routines
  });

  test('conflict warnings display in preview', async ({ page }) => {
    // Test GPIO state conflict warnings show in yellow
    // Test time collision warnings show in red
  });
});
```

2. **These tests will fail initially** - this is expected and correct
3. **Do not skip or comment out** - keep them running to track progress

### During-Implementation Phase (Unit + Integration Tests)

**Goal**: Validate each component as it's built

1. **Write unit tests for each schema change** before implementing:

```python
# Tests/unit/test_schedule_schema.py
class TestAction:
    """Tests for renamed Action class (formerly PatternAction)."""

    def test_action_creation(self):
        action = Action(action_type="gpio", action_name="attract_on")
        assert action.action_type == "gpio"

    def test_action_to_dict(self):
        action = Action(action_type="gpio", action_name="attract_on")
        d = action.to_dict()
        assert d["action_type"] == "gpio"

class TestRoutine:
    """Tests for Routine class with embedded trigger."""

    def test_routine_with_solar_trigger(self):
        routine = Routine(
            routine_id="test",
            name=None,
            trigger=SolarTrigger(solar_event="dusk"),
            actions=[Action(action_type="gpio", action_name="attract_on")]
        )
        assert routine.trigger.solar_event == "dusk"

    def test_auto_generated_name_solar_attract(self):
        routine = Routine(
            routine_id="test",
            name=None,
            trigger=SolarTrigger(solar_event="dusk"),
            actions=[Action(action_type="gpio", action_name="attract_on")]
        )
        assert routine.get_display_name() == "Attract On at Dusk"
```

2. **Run tests after each change**:

```bash
# After each file edit
pytest Tests/unit/test_schedule_schema.py -v -x

# Check coverage regularly
pytest Tests/unit/test_schedule_schema.py --cov=webui/backend/lib/schedule_schema
```

3. **Maintain 85% coverage threshold** throughout implementation

### Post-Implementation Phase (E2E Validation)

**Goal**: Confirm complete user workflows work end-to-end

1. **All E2E tests from Pre-phase should now pass**

2. **Add additional E2E tests** for edge cases discovered during implementation:

```javascript
test('handles schedule with no routines gracefully', async ({ page }) => {
  // Error case discovered during implementation
});

test('preserves schedule state after page refresh', async ({ page }) => {
  // Persistence verification
});
```

3. **Run full test suite**:

```bash
# Backend
pytest Tests/ -v

# Frontend
cd webui/frontend && npm test

# E2E
cd webui/frontend && npm run test:e2e
```

4. **Verify no regressions**:
   - All existing scheduler tests pass
   - All new terminology tests pass
   - Coverage ≥85%

---

## Unit Tests to Update

### test_schedule_schema.py (1662 lines, 26+ classes)

| Old Test Class | New Test Class | Changes |
|----------------|----------------|---------|
| `TestPatternAction` | `TestAction` | Rename class references |
| `TestEventPattern` | `TestRoutine` | Add trigger tests |
| `TestValidatePatternAction` | `TestValidateAction` | Rename |
| `TestValidateEventPattern` | `TestValidateRoutine` | Add trigger validation |
| `TestScheduleFromDictFrontendFormat` | Update | Change `event_patterns` to `routines` |

**Key fixture updates**:

```python
# Old
@pytest.fixture
def sample_pattern_action():
    return PatternAction(action_type="gpio", action_name="attract_on")

@pytest.fixture
def sample_event_pattern(sample_pattern_action):
    return EventPattern(
        pattern_id="test-pattern",
        name="Test Pattern",
        actions=[sample_pattern_action]
    )

# New
@pytest.fixture
def sample_action():
    return Action(action_type="gpio", action_name="attract_on")

@pytest.fixture
def sample_routine(sample_action):
    return Routine(
        routine_id="test-routine",
        name="Test Routine",
        trigger=SolarTrigger(solar_event="dusk"),
        actions=[sample_action]
    )
```

### test_cron_bridge.py (96 tests)

Update to test per-routine triggers:

```python
def test_schedule_with_multiple_trigger_types():
    """Schedule with solar + interval + solar routines generates correct cron."""
    schedule = Schedule(
        name="Mixed Triggers",
        routines=[
            Routine(trigger=SolarTrigger(solar_event="dusk"), actions=[...]),
            Routine(trigger=IntervalTrigger(interval_minutes=15), actions=[...]),
            Routine(trigger=SolarTrigger(solar_event="dawn"), actions=[...]),
        ]
    )
    result = schedule_to_cron(schedule, latitude=40.0, longitude=-74.0)

    # Should have entries for all three routines
    assert len(result.entries) > 0
    # Solar entries should have date-specific cron
    # Interval entries should have time-based cron
```

### test_schedule_conflict_lib.py (1860 lines, 12 classes)

Update `generate_routine_executions()` tests for per-routine triggers.

### test_scheduler_service.py (2497 lines, 35+ classes)

Update fixtures and activation tests.

---

## Complete Test Fixtures

Add these fixtures to `Tests/conftest.py` or `Tests/unit/test_schedule_schema.py`:

```python
from webui.backend.lib.schedule_schema import (
    Action, Routine, Schedule, TimeWindow,
    SolarTrigger, IntervalTrigger, FixedTimeTrigger,
    MoonPhaseTrigger, RecurringDaysTrigger, SensorTrigger, CronTrigger,
)


# =============================================================================
# Trigger Fixtures (all 7 types)
# =============================================================================

@pytest.fixture
def solar_trigger():
    """SolarTrigger fixture."""
    return SolarTrigger(
        solar_event="dusk",
        offset_minutes=0,
    )


@pytest.fixture
def interval_trigger():
    """IntervalTrigger with time window fixture."""
    return IntervalTrigger(
        interval_minutes=15,
        time_window=TimeWindow(start_time="22:00", end_time="06:00"),
    )


@pytest.fixture
def fixed_time_trigger():
    """FixedTimeTrigger fixture."""
    return FixedTimeTrigger(
        time="09:00",
    )


@pytest.fixture
def moon_phase_trigger():
    """MoonPhaseTrigger fixture."""
    return MoonPhaseTrigger(
        phases=["full", "new"],
        time_window=TimeWindow(start_time="22:00", end_time="04:00"),
    )


@pytest.fixture
def recurring_days_trigger():
    """RecurringDaysTrigger fixture."""
    return RecurringDaysTrigger(
        every_n_days=3,
        time="21:00",
        start_date=None,  # Starts from today
    )


@pytest.fixture
def sensor_trigger():
    """SensorTrigger fixture (used as pre_condition)."""
    return SensorTrigger(
        sensor_type="light",
        comparison="lt",
        threshold=100,
    )


@pytest.fixture
def cron_trigger():
    """CronTrigger fixture (expert mode)."""
    return CronTrigger(
        cron_expression="0 */2 * * *",  # Every 2 hours
    )


# =============================================================================
# Routine Fixtures (one for each trigger type)
# =============================================================================

@pytest.fixture
def routine_solar(solar_trigger):
    """Routine with SolarTrigger."""
    return Routine(
        routine_id="test-solar",
        name=None,  # Auto-generated: "Attract On at Dusk"
        trigger=solar_trigger,
        actions=[Action(action_type="gpio", action_name="attract_on")],
    )


@pytest.fixture
def routine_interval(interval_trigger):
    """Routine with IntervalTrigger."""
    return Routine(
        routine_id="test-interval",
        name=None,  # Auto-generated: "Flash + Photo every 15min"
        trigger=interval_trigger,
        actions=[
            Action(action_type="gpio", action_name="flash_on", offset_minutes=0),
            Action(action_type="camera", action_name="takephoto", offset_minutes=1),
            Action(action_type="gpio", action_name="flash_off", offset_minutes=2),
        ],
    )


@pytest.fixture
def routine_fixed_time(fixed_time_trigger):
    """Routine with FixedTimeTrigger."""
    return Routine(
        routine_id="test-fixed",
        name=None,  # Auto-generated: "Backup at 09:00"
        trigger=fixed_time_trigger,
        actions=[Action(action_type="service", action_name="backup")],
    )


@pytest.fixture
def routine_recurring_days(recurring_days_trigger):
    """Routine with RecurringDaysTrigger."""
    return Routine(
        routine_id="test-recurring",
        name=None,  # Auto-generated: "GPS Sync every 3 days"
        trigger=recurring_days_trigger,
        actions=[Action(action_type="service", action_name="gps_sync")],
    )


@pytest.fixture
def routine_with_precondition(interval_trigger, sensor_trigger):
    """Routine with pre_condition (sensor check before executing)."""
    return Routine(
        routine_id="test-precondition",
        name="Photo if Dark",
        trigger=interval_trigger,
        actions=[Action(action_type="camera", action_name="takephoto")],
        pre_condition=sensor_trigger,  # Only run if light < 100
    )


# =============================================================================
# Schedule Fixtures
# =============================================================================

@pytest.fixture
def schedule_overnight_survey(routine_solar, routine_interval):
    """Complete overnight moth survey schedule."""
    return Schedule(
        schedule_id="test-overnight",
        name="Test Overnight Survey",
        routines=[
            routine_solar,
            routine_interval,
            Routine(
                routine_id="test-dawn",
                name=None,
                trigger=SolarTrigger(solar_event="dawn"),
                actions=[Action(action_type="gpio", action_name="attract_off")],
            ),
        ],
    )


# =============================================================================
# Factory Functions (for dynamic test data)
# =============================================================================

def make_routine(
    trigger_type: str,
    actions: list[dict] | None = None,
    **trigger_kwargs
) -> Routine:
    """Factory function to create routines with any trigger type."""
    trigger_classes = {
        "solar": SolarTrigger,
        "interval": IntervalTrigger,
        "fixed_time": FixedTimeTrigger,
        "moon_phase": MoonPhaseTrigger,
        "recurring_days": RecurringDaysTrigger,
        "sensor": SensorTrigger,
        "cron": CronTrigger,
    }

    trigger_cls = trigger_classes[trigger_type]
    trigger = trigger_cls(**trigger_kwargs)

    if actions is None:
        actions = [{"action_type": "gpio", "action_name": "attract_on"}]

    return Routine(
        routine_id=f"test-{trigger_type}",
        name=None,
        trigger=trigger,
        actions=[Action(**a) for a in actions],
    )
```

**Usage in tests**:

```python
def test_all_trigger_types_serialize(
    routine_solar, routine_interval, routine_fixed_time, routine_recurring_days
):
    """All trigger types should serialize correctly."""
    for routine in [routine_solar, routine_interval, routine_fixed_time, routine_recurring_days]:
        d = routine.to_dict()
        restored = Routine.from_dict(d)
        assert restored.routine_id == routine.routine_id


def test_factory_creates_valid_routines():
    """Factory function creates valid routines."""
    solar_routine = make_routine("solar", solar_event="dusk")
    assert solar_routine.trigger.solar_event == "dusk"

    interval_routine = make_routine("interval", interval_minutes=30)
    assert interval_routine.trigger.interval_minutes == 30
```

---

## E2E Test Transition Strategy

During the refactor, some E2E tests will need to be temporarily skipped while components are renamed.

### Test Marking Strategy

```javascript
// e2e/scheduler-refactor.spec.js

// Mark obsolete tests to skip
test.skip('pattern library workflow', async ({ page }) => {
  // This test is obsolete - pattern library removed
  // DELETE after refactor complete
});

// Mark tests that need selector updates
test.fixme('schedule creation workflow', async ({ page }) => {
  // Needs update: data-testid="add-pattern" → data-testid="add-routine"
});

// New test for refactored workflow
test('create schedule with multiple routines', async ({ page }) => {
  await page.goto('/scheduler');
  await page.click('[data-testid="create-schedule"]');
  await page.fill('[data-testid="schedule-name"]', 'Test Schedule');

  // Add first routine (solar trigger)
  await page.click('[data-testid="add-routine"]');
  await page.selectOption('[data-testid="trigger-type-0"]', 'solar');
  await page.selectOption('[data-testid="solar-event-0"]', 'dusk');
  await page.click('[data-testid="add-action-0"]');
  await page.selectOption('[data-testid="action-name-0-0"]', 'attract_on');

  // Add second routine (interval trigger)
  await page.click('[data-testid="add-routine"]');
  await page.selectOption('[data-testid="trigger-type-1"]', 'interval');
  await page.fill('[data-testid="interval-minutes-1"]', '15');

  // Save and verify
  await page.click('[data-testid="save-schedule"]');
  await expect(page.locator('[data-testid="schedule-saved"]')).toBeVisible();
});
```

### Selector Conventions

#### Schedule-Level Selectors

| Component | data-testid Pattern | Notes |
|-----------|---------------------|-------|
| Create schedule button | `create-schedule` | Opens new schedule form |
| Schedule name input | `schedule-name` | Text input |
| Schedule description | `schedule-description` | Textarea |
| Save schedule button | `save-schedule` | Submit button |
| Cancel schedule button | `cancel-schedule` | Discard changes |
| Schedule saved indicator | `schedule-saved` | Success toast/message |
| Activate schedule button | `activate-schedule` | Triggers activation |
| Deactivate schedule button | `deactivate-schedule` | Stops schedule |
| Delete schedule button | `delete-schedule-{id}` | Confirm before delete |

#### Routine List Selectors

| Component | data-testid Pattern | Notes |
|-----------|---------------------|-------|
| Routine list container | `routine-list` | Wrapper for all routines |
| Routine list empty state | `routine-list-empty` | Shown when no routines |
| Routine list loading | `routine-list-loading` | Skeleton state |
| Routine list error | `routine-list-error` | Error with retry |
| Add routine button | `add-routine` | Opens new routine form |

#### RoutineCard Selectors

| Component | data-testid Pattern | Notes |
|-----------|---------------------|-------|
| Routine card | `routine-card` | Collapsible card wrapper |
| Routine card (by index) | `routine-{index}` | Zero-indexed position |
| Routine card loading | `routine-card-loading` | Skeleton state |
| Routine card error | `routine-card-error` | Error state |
| Routine name display | `routine-name` | Auto-generated or custom |
| Delete routine button | `delete-routine-{index}` | Remove from list |

#### NewRoutineCard Selectors

| Component | data-testid Pattern | Notes |
|-----------|---------------------|-------|
| New routine card | `new-routine-card` | Inline wizard wrapper |
| Save routine button | `save-routine` | Complete inline wizard |
| Cancel new routine | `cancel-new-routine` | Discard draft |

#### TriggerSelector Selectors

| Component | data-testid Pattern | Notes |
|-----------|---------------------|-------|
| Trigger type dropdown | `trigger-type` | Top-level select |
| Trigger type (by routine) | `trigger-type-{routineIndex}` | When in list context |
| Trigger badge | `trigger-badge` | Type indicator badge |

#### Trigger Form Selectors (by type)

| Trigger Type | Component | data-testid Pattern |
|--------------|-----------|---------------------|
| **Interval** | Minutes input | `interval-minutes` / `interval-minutes-{idx}` |
| **Interval** | Time window start | `time-window-start-{idx}` |
| **Interval** | Time window end | `time-window-end-{idx}` |
| **Solar** | Event select | `solar-event` / `solar-event-{idx}` |
| **Solar** | Offset minutes | `solar-offset-{idx}` |
| **Fixed Time** | Time input | `fixed-time` / `fixed-time-{idx}` |
| **Moon Phase** | Phase checkboxes | `moon-phase-{phase}` (full, new, etc.) |
| **Recurring Days** | Every N days | `every-n-days` |
| **Recurring Days** | Time input | `trigger-time` |
| **Recurring Days** | Start date | `start-date` |
| **Cron** | Expression input | `cron-expression` / `cron-expression-{idx}` |

#### PreConditionForm Selectors

| Component | data-testid Pattern | Notes |
|-----------|---------------------|-------|
| Pre-condition toggle | `pre-condition-toggle` | Enable/disable |
| Pre-condition toggle (by routine) | `pre-condition-toggle-{routineIndex}` | In list context |
| Sensor type select | `pre-condition-sensor` | light, temperature, etc. |
| Condition select | `pre-condition-op` | above, below, equals |
| Threshold input | `pre-condition-threshold` | Numeric value |

#### ActionList Selectors

| Component | data-testid Pattern | Notes |
|-----------|---------------------|-------|
| Action container | `action-{routineIndex}-{actionIndex}` | Per-action wrapper |
| Action type select | `action-type-{routineIndex}-{actionIndex}` | gpio, camera, etc. |
| Action name select | `action-name-{routineIndex}-{actionIndex}` | attract_on, takephoto, etc. |
| Action offset input | `action-offset-{routineIndex}-{actionIndex}` | Minutes from trigger |
| Add action button | `add-action` / `add-action-{routineIndex}` | Append action |
| Delete action button | `delete-action-{routineIndex}-{actionIndex}` | Remove action |

#### DayTimeline Selectors

| Component | data-testid Pattern | Notes |
|-----------|---------------------|-------|
| Day timeline container | `day-timeline` | Full timeline |
| Day timeline empty | `day-timeline-empty` | No executions state |
| Execution marker | `execution-marker` | Clickable time chip |
| Execution marker (specific) | `execution-{routineId}-{time}` | Unique per execution |
| Conflict indicator | `conflict-{executionId}` | Red (time) or yellow (gpio) |

#### ActivationProgress Selectors

| Component | data-testid Pattern | Notes |
|-----------|---------------------|-------|
| Activation progress | `activation-progress` | Progress bar wrapper |
| Activation error | `activation-error` | Error state display |
| Progress bar | `activation-progress-bar` | Visual progress |
| Phase label | `activation-phase` | Current phase text |

#### Built-in Schedule Selectors

| Component | data-testid Pattern | Notes |
|-----------|---------------------|-------|
| Built-in schedule card | `builtin-schedule-{id}` | overnight-moth-survey, etc. |
| Clone button | `clone-schedule-{id}` | Copy for customization |

#### CalendarView Selectors

| Component | data-testid Pattern | Notes |
|-----------|---------------------|-------|
| View mode toggle | `view-mode-{mode}` | day, week, month |
| Previous button | `calendar-prev` | Navigate back |
| Next button | `calendar-next` | Navigate forward |
| Today button | `calendar-today` | Jump to current date |

### When to Transition Tests

1. After `RoutineEditor` component is renamed and working
2. After `TriggerSelector` component is added
3. After API endpoints are updated
4. Run `npm run test:e2e -- --grep "refactor"` to test only refactor-related tests

---

## New Tests to Add

### Auto-Generated Name Tests

```python
class TestRoutineAutoName:
    """Test auto-generated routine names."""

    def test_solar_dusk_attract_on(self):
        routine = Routine(
            routine_id="test",
            name=None,
            trigger=SolarTrigger(solar_event="dusk"),
            actions=[Action(action_type="gpio", action_name="attract_on")]
        )
        assert routine.get_display_name() == "Attract On at Dusk"

    def test_interval_photo_cycle(self):
        routine = Routine(
            routine_id="test",
            name=None,
            trigger=IntervalTrigger(interval_minutes=15),
            actions=[
                Action(action_type="gpio", action_name="flash_on"),
                Action(action_type="camera", action_name="takephoto"),
                Action(action_type="gpio", action_name="flash_off"),
            ]
        )
        assert routine.get_display_name() == "Flash + Photo every 15min"

    def test_explicit_name_preserved(self):
        routine = Routine(
            routine_id="test",
            name="My Custom Name",
            trigger=SolarTrigger(solar_event="dusk"),
            actions=[Action(action_type="gpio", action_name="attract_on")]
        )
        assert routine.get_display_name() == "My Custom Name"

    def test_recurring_days_name(self):
        routine = Routine(
            routine_id="test",
            name=None,
            trigger=RecurringDaysTrigger(every_n_days=3, time="21:00"),
            actions=[Action(action_type="service", action_name="gps_sync")]
        )
        assert routine.get_display_name() == "GPS Sync every 3 days at 21:00"

    def test_empty_actions_fallback(self):
        routine = Routine(
            routine_id="test",
            name=None,
            trigger=SolarTrigger(solar_event="dusk"),
            actions=[]
        )
        assert "Empty" in routine.get_display_name()

    def test_duplicate_actions_count_format(self):
        """Duplicate actions should use 'Nx Action' format."""
        routine = Routine(
            routine_id="test",
            name=None,
            trigger=IntervalTrigger(interval_minutes=15),
            actions=[
                Action(action_type="camera", action_name="takephoto"),
                Action(action_type="camera", action_name="takephoto"),
                Action(action_type="camera", action_name="takephoto"),
            ]
        )
        assert routine.get_display_name() == "3x Photo every 15min"

    def test_sensor_precondition_description(self):
        """Sensor pre-conditions should describe the condition."""
        routine = Routine(
            routine_id="test",
            name=None,
            trigger=IntervalTrigger(interval_minutes=15),
            actions=[Action(action_type="camera", action_name="takephoto")],
            pre_condition=SensorTrigger(
                sensor_type="light",
                condition="below",
                threshold=100
            )
        )
        # Pre-condition description is separate from display name
        display = routine.get_display_name()
        assert "Photo" in display
        assert "15min" in display
```

### Trigger Deserialization Tests

```python
class TestTriggerFromDict:
    """Test trigger deserialization."""

    def test_interval_trigger(self):
        data = {"trigger_type": "interval", "interval_minutes": 15}
        trigger = trigger_from_dict(data)
        assert isinstance(trigger, IntervalTrigger)
        assert trigger.interval_minutes == 15

    def test_solar_trigger(self):
        data = {"trigger_type": "solar", "solar_event": "dusk", "offset_minutes": 30}
        trigger = trigger_from_dict(data)
        assert isinstance(trigger, SolarTrigger)
        assert trigger.solar_event == "dusk"
        assert trigger.offset_minutes == 30

    def test_recurring_days_trigger(self):
        data = {"trigger_type": "recurring_days", "every_n_days": 7, "time": "09:00"}
        trigger = trigger_from_dict(data)
        assert isinstance(trigger, RecurringDaysTrigger)
        assert trigger.every_n_days == 7

    def test_unknown_trigger_raises(self):
        data = {"trigger_type": "unknown"}
        with pytest.raises(ValueError, match="Unknown trigger_type"):
            trigger_from_dict(data)
```

### Mixed Trigger Schedule Tests

```python
class TestScheduleWithMixedTriggers:
    """Test schedule with different trigger types per routine."""

    def test_overnight_moth_survey_pattern(self):
        """The primary use case: UV at dusk, photos every 15min, UV off at dawn."""
        schedule = Schedule(
            name="Overnight Moth Survey",
            routines=[
                Routine(
                    routine_id="uv-on",
                    name=None,
                    trigger=SolarTrigger(solar_event="dusk"),
                    actions=[Action(action_type="gpio", action_name="attract_on")]
                ),
                Routine(
                    routine_id="photos",
                    name=None,
                    trigger=IntervalTrigger(
                        interval_minutes=15,
                        time_window=TimeWindow(start_time="22:00", end_time="06:00")
                    ),
                    actions=[
                        Action(action_type="gpio", action_name="flash_on"),
                        Action(action_type="camera", action_name="takephoto", offset_minutes=1),
                        Action(action_type="gpio", action_name="flash_off", offset_minutes=2),
                    ]
                ),
                Routine(
                    routine_id="uv-off",
                    name=None,
                    trigger=SolarTrigger(solar_event="dawn"),
                    actions=[Action(action_type="gpio", action_name="attract_off")]
                ),
            ]
        )

        valid, error = validate_schedule(schedule)
        assert valid is True
        assert error is None
        assert len(schedule.routines) == 3

    def test_schedule_serialization_roundtrip(self):
        """Schedule with mixed triggers survives to_dict/from_dict."""
        schedule = Schedule(
            name="Test",
            routines=[
                Routine(
                    routine_id="r1",
                    trigger=SolarTrigger(solar_event="dusk"),
                    actions=[Action(action_type="gpio", action_name="attract_on")]
                ),
                Routine(
                    routine_id="r2",
                    trigger=IntervalTrigger(interval_minutes=15),
                    actions=[Action(action_type="camera", action_name="takephoto")]
                ),
            ]
        )

        d = schedule.to_dict()
        restored = Schedule.from_dict(d)

        assert len(restored.routines) == 2
        assert restored.routines[0].trigger.trigger_type == "solar"
        assert restored.routines[1].trigger.trigger_type == "interval"
```

### Validation Tests

```python
class TestRecurringDaysValidation:
    """Test RecurringDaysTrigger validation."""

    def test_valid_trigger(self):
        trigger = RecurringDaysTrigger(every_n_days=3, time="21:00")
        valid, error = validate_recurring_days_trigger(trigger)
        assert valid is True

    def test_every_n_days_too_low(self):
        trigger = RecurringDaysTrigger(every_n_days=0, time="21:00")
        valid, error = validate_recurring_days_trigger(trigger)
        assert valid is False
        assert "between 1 and 365" in error

    def test_every_n_days_too_high(self):
        trigger = RecurringDaysTrigger(every_n_days=400, time="21:00")
        valid, error = validate_recurring_days_trigger(trigger)
        assert valid is False

    def test_invalid_time_format(self):
        trigger = RecurringDaysTrigger(every_n_days=3, time="9:00")  # Missing leading zero
        valid, error = validate_recurring_days_trigger(trigger)
        assert valid is False
        assert "HH:MM" in error

    def test_invalid_start_date(self):
        trigger = RecurringDaysTrigger(every_n_days=3, time="21:00", start_date="not-a-date")
        valid, error = validate_recurring_days_trigger(trigger)
        assert valid is False
        assert "ISO 8601" in error


class TestRoutineIdUniqueness:
    """Test routine ID uniqueness validation."""

    def test_unique_ids_pass(self):
        schedule = Schedule(
            name="Test",
            routines=[
                Routine(routine_id="r1", trigger=SolarTrigger(solar_event="dusk"), actions=[...]),
                Routine(routine_id="r2", trigger=SolarTrigger(solar_event="dawn"), actions=[...]),
            ]
        )
        valid, error = validate_routine_ids_unique(schedule)
        assert valid is True

    def test_duplicate_ids_fail(self):
        schedule = Schedule(
            name="Test",
            routines=[
                Routine(routine_id="same", trigger=SolarTrigger(solar_event="dusk"), actions=[...]),
                Routine(routine_id="same", trigger=SolarTrigger(solar_event="dawn"), actions=[...]),
            ]
        )
        valid, error = validate_routine_ids_unique(schedule)
        assert valid is False
        assert "Duplicate" in error
```

---

## Running Tests

### Backend Tests

```bash
# All unit tests
pytest Tests/unit/ -v

# Specific test file
pytest Tests/unit/test_schedule_schema.py -v

# With coverage
pytest Tests/unit/test_schedule_schema.py --cov=webui/backend/lib/schedule_schema

# Stop on first failure
pytest Tests/unit/ -v -x
```

### Frontend Tests

```bash
cd webui/frontend

# All tests
npm test

# Watch mode
npm test -- --watch

# Coverage
npm test -- --coverage
```

### E2E Tests

```bash
cd webui/frontend

# All E2E tests
npm run test:e2e

# Interactive mode
npm run test:e2e:ui

# Only refactor-related tests
npm run test:e2e -- --grep "refactor"
```

---

## Success Criteria

- [ ] All `TestPatternAction` → `TestAction` renames complete
- [ ] All `TestEventPattern` → `TestRoutine` renames complete
- [ ] Trigger fixtures for all 7 types created
- [ ] Routine fixtures for all trigger types created
- [ ] `make_routine()` factory function working
- [ ] All auto-name tests passing
- [ ] All trigger deserialization tests passing
- [ ] Mixed trigger schedule tests passing
- [ ] RecurringDaysTrigger validation tests passing
- [ ] E2E selector updates complete
- [ ] Coverage ≥85% maintained

---

## Related Documentation

- [Index](./SCHEDULER_TERMINOLOGY_REFACTOR_INDEX.md) - Navigation hub
- [Overview](./SCHEDULER_TERMINOLOGY_REFACTOR_OVERVIEW.md) - Architecture context
- [Backend Implementation](./SCHEDULER_TERMINOLOGY_REFACTOR_BACKEND.md)
- [Frontend Implementation](./SCHEDULER_TERMINOLOGY_REFACTOR_FRONTEND.md)
- [Reference](./SCHEDULER_TERMINOLOGY_REFACTOR_REFERENCE.md) - Patterns, API spec
- [TDD Workflow Guide](../TDD_WORKFLOW.md) - General TDD workflow
