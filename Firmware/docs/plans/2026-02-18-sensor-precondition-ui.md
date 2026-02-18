# Sensor Pre-Condition UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Wire the existing `PreConditionForm` into the routine editing UI and enhance it with cooldown, time window, and unit labels.

**Architecture:** Enhance `PreConditionForm` with new fields (cooldown, time window, unit labels), integrate it into `RoutineCard` and `NewRoutineCard` inside the Trigger section, add a "Gated" badge to collapsed RoutineCard headers, and update `RoutinePropType`.

**Tech Stack:** React 18, Vitest, @testing-library/react, Tailwind CSS, PropTypes

**Design doc:** `docs/plans/2026-02-18-sensor-precondition-ui-design.md`

---

### Task 1: Add unit labels to PreConditionForm

**Files:**
- Modify: `webui/frontend/src/components/scheduler/ScheduleEditor/PreConditionForm.jsx:95-149`
- Test: `webui/frontend/src/components/scheduler/ScheduleEditor/__tests__/PreConditionForm.test.jsx`

**Step 1: Write the failing tests**

Add to `PreConditionForm.test.jsx` inside a new `describe('Unit labels')` block:

```jsx
describe('Unit labels', () => {
  it('shows "lux" unit when sensor type is light', () => {
    const preCondition = {
      trigger_type: 'sensor',
      sensor_type: 'light',
      comparison: 'lt',
      threshold: 100,
    }
    render(
      <PreConditionForm preCondition={preCondition} onChange={mockOnChange} routineIndex={0} />
    )
    expect(screen.getByText('lux')).toBeInTheDocument()
  })

  it('shows "°C" unit when sensor type is temperature', () => {
    const preCondition = {
      trigger_type: 'sensor',
      sensor_type: 'temperature',
      comparison: 'gt',
      threshold: 25,
    }
    render(
      <PreConditionForm preCondition={preCondition} onChange={mockOnChange} routineIndex={0} />
    )
    expect(screen.getByText('°C')).toBeInTheDocument()
  })

  it('updates unit label when sensor type changes', () => {
    const preCondition = {
      trigger_type: 'sensor',
      sensor_type: 'light',
      comparison: 'lt',
      threshold: 100,
    }
    const { rerender } = render(
      <PreConditionForm preCondition={preCondition} onChange={mockOnChange} routineIndex={0} />
    )
    expect(screen.getByText('lux')).toBeInTheDocument()

    rerender(
      <PreConditionForm
        preCondition={{ ...preCondition, sensor_type: 'temperature' }}
        onChange={mockOnChange}
        routineIndex={0}
      />
    )
    expect(screen.getByText('°C')).toBeInTheDocument()
    expect(screen.queryByText('lux')).not.toBeInTheDocument()
  })
})
```

**Step 2: Run tests to verify they fail**

Run: `cd webui/frontend && npx vitest run src/components/scheduler/ScheduleEditor/__tests__/PreConditionForm.test.jsx`

Expected: 3 FAIL — "Unable to find an element with the text: lux" / "°C"

**Step 3: Implement unit labels**

In `PreConditionForm.jsx`, add a unit label map and render it after the threshold input:

```jsx
// Add at top of file, after DEFAULT_PRE_CONDITION
const SENSOR_UNITS = {
  light: 'lux',
  temperature: '°C',
}
```

In the JSX, after the threshold `<input>` (line ~149), add:

```jsx
{/* Unit label */}
<span className="text-xs text-gray-500 dark:text-gray-400" data-testid="pre-condition-unit">
  {SENSOR_UNITS[preCondition?.sensor_type] || ''}
</span>
```

**Step 4: Run tests to verify they pass**

Run: `cd webui/frontend && npx vitest run src/components/scheduler/ScheduleEditor/__tests__/PreConditionForm.test.jsx`

Expected: ALL PASS

**Step 5: Commit**

```bash
git add webui/frontend/src/components/scheduler/ScheduleEditor/PreConditionForm.jsx \
       webui/frontend/src/components/scheduler/ScheduleEditor/__tests__/PreConditionForm.test.jsx
git commit -m "feat(ui): add unit labels to PreConditionForm (#271)"
```

---

### Task 2: Add cooldown input to PreConditionForm

**Files:**
- Modify: `webui/frontend/src/components/scheduler/ScheduleEditor/PreConditionForm.jsx`
- Modify: `webui/frontend/src/components/scheduler/ScheduleEditor/__tests__/PreConditionForm.test.jsx`

**Step 1: Write the failing tests**

Add to `PreConditionForm.test.jsx` inside a new `describe('Cooldown')` block:

```jsx
describe('Cooldown', () => {
  const preConditionWithCooldown = {
    trigger_type: 'sensor',
    sensor_type: 'light',
    comparison: 'lt',
    threshold: 100,
    cooldown_minutes: 5,
  }

  it('renders cooldown input when enabled', () => {
    render(
      <PreConditionForm preCondition={preConditionWithCooldown} onChange={mockOnChange} routineIndex={0} />
    )
    expect(screen.getByTestId('pre-condition-cooldown')).toBeInTheDocument()
    expect(screen.getByTestId('pre-condition-cooldown')).toHaveValue(5)
  })

  it('does not render cooldown when disabled', () => {
    render(
      <PreConditionForm preCondition={null} onChange={mockOnChange} routineIndex={0} />
    )
    expect(screen.queryByTestId('pre-condition-cooldown')).not.toBeInTheDocument()
  })

  it('updates cooldown value', () => {
    render(
      <PreConditionForm preCondition={preConditionWithCooldown} onChange={mockOnChange} routineIndex={0} />
    )
    const cooldownInput = screen.getByTestId('pre-condition-cooldown')
    fireEvent.change(cooldownInput, { target: { value: '15' } })

    expect(mockOnChange).toHaveBeenCalledWith({
      ...preConditionWithCooldown,
      cooldown_minutes: 15,
    })
  })

  it('shows error for cooldown below 1', () => {
    render(
      <PreConditionForm preCondition={preConditionWithCooldown} onChange={mockOnChange} routineIndex={0} />
    )
    const cooldownInput = screen.getByTestId('pre-condition-cooldown')
    fireEvent.change(cooldownInput, { target: { value: '0' } })

    expect(screen.getByTestId('pre-condition-cooldown-error')).toBeInTheDocument()
    expect(mockOnChange).not.toHaveBeenCalled()
  })

  it('shows error for cooldown above 60', () => {
    render(
      <PreConditionForm preCondition={preConditionWithCooldown} onChange={mockOnChange} routineIndex={0} />
    )
    const cooldownInput = screen.getByTestId('pre-condition-cooldown')
    fireEvent.change(cooldownInput, { target: { value: '61' } })

    expect(screen.getByTestId('pre-condition-cooldown-error')).toBeInTheDocument()
    expect(mockOnChange).not.toHaveBeenCalled()
  })

  it('includes cooldown_minutes in default pre-condition', () => {
    render(
      <PreConditionForm preCondition={null} onChange={mockOnChange} routineIndex={0} />
    )
    const toggle = screen.getByTestId('pre-condition-toggle-0')
    fireEvent.click(toggle)

    expect(mockOnChange).toHaveBeenCalledWith(
      expect.objectContaining({ cooldown_minutes: 5 })
    )
  })
})
```

**Step 2: Run tests to verify they fail**

Run: `cd webui/frontend && npx vitest run src/components/scheduler/ScheduleEditor/__tests__/PreConditionForm.test.jsx`

Expected: 6 FAIL

**Step 3: Implement cooldown**

In `PreConditionForm.jsx`:

1. Update `DEFAULT_PRE_CONDITION` to include `cooldown_minutes: 5`

2. Add `cooldownError` state:
```jsx
const [cooldownError, setCooldownError] = useState(null)
```

3. Add cooldown change handler:
```jsx
const handleCooldownChange = (newCooldown) => {
  const validated = validateNumericInput(newCooldown, 1, SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES)
  if (validated === null) {
    setCooldownError(NUMERIC_ERRORS.INVALID_COOLDOWN(SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES))
    return
  }
  setCooldownError(null)
  onChange({ ...preCondition, cooldown_minutes: validated })
}
```

4. Import `SCHEDULE_LIMITS` from `./constants` (add to existing import).

5. Clear `cooldownError` in `handleToggle` alongside `thresholdError`.

6. Add JSX after the sensor/comparison/threshold row:
```jsx
{/* Cooldown */}
<div className="flex items-center gap-2 text-sm">
  <span className="text-gray-400">Cooldown:</span>
  <input
    type="number"
    min={1}
    max={60}
    value={preCondition?.cooldown_minutes ?? 5}
    onChange={(e) => handleCooldownChange(e.target.value)}
    disabled={disabled}
    aria-label="Cooldown minutes"
    className="w-16 rounded-md border border-gray-300 dark:border-gray-600
               bg-white dark:bg-gray-800 px-2 py-1 text-gray-900 dark:text-white text-center
               focus:ring-2 focus:ring-blue-500 focus:border-transparent
               disabled:opacity-50 disabled:cursor-not-allowed"
    data-testid="pre-condition-cooldown"
  />
  <span className="text-xs text-gray-500 dark:text-gray-400">minutes</span>
</div>
{cooldownError && (
  <p className="text-sm text-red-600 dark:text-red-400" data-testid="pre-condition-cooldown-error">
    {cooldownError}
  </p>
)}
```

**Step 4: Run tests to verify they pass**

Run: `cd webui/frontend && npx vitest run src/components/scheduler/ScheduleEditor/__tests__/PreConditionForm.test.jsx`

Expected: ALL PASS

**Step 5: Commit**

```bash
git add webui/frontend/src/components/scheduler/ScheduleEditor/PreConditionForm.jsx \
       webui/frontend/src/components/scheduler/ScheduleEditor/__tests__/PreConditionForm.test.jsx
git commit -m "feat(ui): add cooldown input to PreConditionForm (#271)"
```

---

### Task 3: Add time window toggle to PreConditionForm

**Files:**
- Modify: `webui/frontend/src/components/scheduler/ScheduleEditor/PreConditionForm.jsx`
- Modify: `webui/frontend/src/components/scheduler/ScheduleEditor/__tests__/PreConditionForm.test.jsx`

**Step 1: Write the failing tests**

Add to `PreConditionForm.test.jsx` inside a new `describe('Time window')` block:

```jsx
describe('Time window', () => {
  const preConditionBase = {
    trigger_type: 'sensor',
    sensor_type: 'light',
    comparison: 'lt',
    threshold: 100,
    cooldown_minutes: 5,
  }

  it('renders time window toggle when pre-condition is enabled', () => {
    render(
      <PreConditionForm preCondition={preConditionBase} onChange={mockOnChange} routineIndex={0} />
    )
    expect(screen.getByTestId('pre-condition-time-window-toggle')).toBeInTheDocument()
    expect(screen.getByTestId('pre-condition-time-window-toggle')).not.toBeChecked()
  })

  it('shows time inputs when time window toggle is checked', () => {
    const withTimeWindow = {
      ...preConditionBase,
      time_window: { start_time: '21:00', end_time: '06:00' },
    }
    render(
      <PreConditionForm preCondition={withTimeWindow} onChange={mockOnChange} routineIndex={0} />
    )
    expect(screen.getByTestId('pre-condition-time-window-toggle')).toBeChecked()
    expect(screen.getByTestId('pre-condition-tw-start')).toHaveValue('21:00')
    expect(screen.getByTestId('pre-condition-tw-end')).toHaveValue('06:00')
  })

  it('hides time inputs when time window is null', () => {
    render(
      <PreConditionForm preCondition={preConditionBase} onChange={mockOnChange} routineIndex={0} />
    )
    expect(screen.queryByTestId('pre-condition-tw-start')).not.toBeInTheDocument()
    expect(screen.queryByTestId('pre-condition-tw-end')).not.toBeInTheDocument()
  })

  it('enables time window with defaults when toggle checked', () => {
    render(
      <PreConditionForm preCondition={preConditionBase} onChange={mockOnChange} routineIndex={0} />
    )
    const toggle = screen.getByTestId('pre-condition-time-window-toggle')
    fireEvent.click(toggle)

    expect(mockOnChange).toHaveBeenCalledWith({
      ...preConditionBase,
      time_window: { start_time: '21:00', end_time: '06:00' },
    })
  })

  it('removes time window when toggle unchecked', () => {
    const withTimeWindow = {
      ...preConditionBase,
      time_window: { start_time: '21:00', end_time: '06:00' },
    }
    render(
      <PreConditionForm preCondition={withTimeWindow} onChange={mockOnChange} routineIndex={0} />
    )
    const toggle = screen.getByTestId('pre-condition-time-window-toggle')
    fireEvent.click(toggle)

    expect(mockOnChange).toHaveBeenCalledWith({
      ...preConditionBase,
      time_window: null,
    })
  })

  it('updates start time', () => {
    const withTimeWindow = {
      ...preConditionBase,
      time_window: { start_time: '21:00', end_time: '06:00' },
    }
    render(
      <PreConditionForm preCondition={withTimeWindow} onChange={mockOnChange} routineIndex={0} />
    )
    const startInput = screen.getByTestId('pre-condition-tw-start')
    fireEvent.change(startInput, { target: { value: '22:30' } })

    expect(mockOnChange).toHaveBeenCalledWith({
      ...preConditionBase,
      time_window: { start_time: '22:30', end_time: '06:00' },
    })
  })

  it('updates end time', () => {
    const withTimeWindow = {
      ...preConditionBase,
      time_window: { start_time: '21:00', end_time: '06:00' },
    }
    render(
      <PreConditionForm preCondition={withTimeWindow} onChange={mockOnChange} routineIndex={0} />
    )
    const endInput = screen.getByTestId('pre-condition-tw-end')
    fireEvent.change(endInput, { target: { value: '07:00' } })

    expect(mockOnChange).toHaveBeenCalledWith({
      ...preConditionBase,
      time_window: { start_time: '21:00', end_time: '07:00' },
    })
  })
})
```

**Step 2: Run tests to verify they fail**

Run: `cd webui/frontend && npx vitest run src/components/scheduler/ScheduleEditor/__tests__/PreConditionForm.test.jsx`

Expected: 7 FAIL

**Step 3: Implement time window**

In `PreConditionForm.jsx`:

1. Add time window toggle handler:
```jsx
const handleTimeWindowToggle = (e) => {
  const isEnabled = e.target.checked
  if (isEnabled) {
    onChange({ ...preCondition, time_window: { start_time: '21:00', end_time: '06:00' } })
  } else {
    onChange({ ...preCondition, time_window: null })
  }
}

const handleTimeWindowChange = (field, value) => {
  onChange({
    ...preCondition,
    time_window: { ...preCondition.time_window, [field]: value },
  })
}
```

2. Add JSX after cooldown section (still inside the `enabled && preCondition` block):
```jsx
{/* Time window toggle */}
<div className="flex items-center gap-3 text-sm">
  <input
    type="checkbox"
    id={`pre-condition-tw-toggle-${routineIndex}`}
    checked={!!preCondition?.time_window}
    onChange={handleTimeWindowToggle}
    disabled={disabled}
    className="rounded border-gray-600 disabled:opacity-50"
    data-testid="pre-condition-time-window-toggle"
  />
  <label
    htmlFor={`pre-condition-tw-toggle-${routineIndex}`}
    className="text-gray-400 cursor-pointer"
  >
    Restrict to time window
  </label>
</div>

{/* Time window fields */}
{preCondition?.time_window && (
  <div className="pl-6 flex items-center gap-2 text-sm">
    <input
      type="time"
      value={preCondition.time_window.start_time || '21:00'}
      onChange={(e) => handleTimeWindowChange('start_time', e.target.value)}
      disabled={disabled}
      aria-label="Time window start"
      className="rounded-md border border-gray-300 dark:border-gray-600
                 bg-white dark:bg-gray-800 px-2 py-1 text-gray-900 dark:text-white
                 focus:ring-2 focus:ring-blue-500 focus:border-transparent
                 disabled:opacity-50 disabled:cursor-not-allowed"
      data-testid="pre-condition-tw-start"
    />
    <span className="text-gray-400">to</span>
    <input
      type="time"
      value={preCondition.time_window.end_time || '06:00'}
      onChange={(e) => handleTimeWindowChange('end_time', e.target.value)}
      disabled={disabled}
      aria-label="Time window end"
      className="rounded-md border border-gray-300 dark:border-gray-600
                 bg-white dark:bg-gray-800 px-2 py-1 text-gray-900 dark:text-white
                 focus:ring-2 focus:ring-blue-500 focus:border-transparent
                 disabled:opacity-50 disabled:cursor-not-allowed"
      data-testid="pre-condition-tw-end"
    />
  </div>
)}
```

**Step 4: Run tests to verify they pass**

Run: `cd webui/frontend && npx vitest run src/components/scheduler/ScheduleEditor/__tests__/PreConditionForm.test.jsx`

Expected: ALL PASS

**Step 5: Commit**

```bash
git add webui/frontend/src/components/scheduler/ScheduleEditor/PreConditionForm.jsx \
       webui/frontend/src/components/scheduler/ScheduleEditor/__tests__/PreConditionForm.test.jsx
git commit -m "feat(ui): add time window toggle to PreConditionForm (#271)"
```

---

### Task 4: Update RoutinePropType for pre_condition

**Files:**
- Modify: `webui/frontend/src/components/scheduler/ScheduleEditor/propTypes.js:236-241`

**Step 1: Update RoutinePropType**

Add `pre_condition` to the `RoutinePropType` shape. Import `TimeWindowPropType` (already defined in same file).

```js
export const PreConditionPropType = PropTypes.shape({
  trigger_type: PropTypes.string,
  sensor_type: PropTypes.string,
  comparison: PropTypes.string,
  threshold: PropTypes.number,
  cooldown_minutes: PropTypes.number,
  time_window: TimeWindowPropType,
})

export const RoutinePropType = PropTypes.shape({
  routine_id: PropTypes.string,
  name: PropTypes.string,
  trigger: TriggerPropType,
  actions: PropTypes.arrayOf(RoutineActionPropType),
  pre_condition: PreConditionPropType,
})
```

**Step 2: Commit**

```bash
git add webui/frontend/src/components/scheduler/ScheduleEditor/propTypes.js
git commit -m "feat(ui): add PreConditionPropType to RoutinePropType (#271)"
```

---

### Task 5: Integrate PreConditionForm into RoutineCard

**Files:**
- Modify: `webui/frontend/src/components/scheduler/ScheduleEditor/RoutineCard.jsx`
- Modify: `webui/frontend/src/components/scheduler/ScheduleEditor/__tests__/RoutineCard.test.jsx`

**Step 1: Write the failing tests**

Add a mock for PreConditionForm at the top of `RoutineCard.test.jsx`, after the existing mocks:

```jsx
// Mock PreConditionForm to simplify tests
vi.mock('../PreConditionForm', () => ({
  default: vi.fn(({ preCondition, onChange, routineIndex, disabled }) => (
    <div data-testid="mock-pre-condition-form">
      <span data-testid="pre-condition-status">
        {preCondition ? 'enabled' : 'disabled'}
      </span>
      <button
        onClick={() =>
          onChange({
            trigger_type: 'sensor',
            sensor_type: 'light',
            comparison: 'lt',
            threshold: 100,
            cooldown_minutes: 5,
          })
        }
        disabled={disabled}
        data-testid="enable-pre-condition"
      >
        Enable Pre-Condition
      </button>
      <button
        onClick={() => onChange(null)}
        disabled={disabled}
        data-testid="disable-pre-condition"
      >
        Disable Pre-Condition
      </button>
    </div>
  )),
}))
```

Add a new `describe('pre-condition integration')` block:

```jsx
describe('pre-condition integration', () => {
  it('renders PreConditionForm inside trigger section when expanded', async () => {
    const user = userEvent.setup()
    render(<RoutineCard {...defaultProps} defaultExpanded={true} />)

    expect(screen.getByTestId('mock-pre-condition-form')).toBeInTheDocument()
  })

  it('passes routine.pre_condition to PreConditionForm', () => {
    const routineWithPreCondition = {
      ...defaultRoutine,
      pre_condition: {
        trigger_type: 'sensor',
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      },
    }
    render(
      <RoutineCard
        {...defaultProps}
        routine={routineWithPreCondition}
        defaultExpanded={true}
      />
    )
    expect(screen.getByTestId('pre-condition-status')).toHaveTextContent('enabled')
  })

  it('calls onUpdate with pre_condition when pre-condition changes', async () => {
    const user = userEvent.setup()
    const onUpdate = vi.fn()
    render(
      <RoutineCard {...defaultProps} onUpdate={onUpdate} defaultExpanded={true} />
    )

    await user.click(screen.getByTestId('enable-pre-condition'))

    expect(onUpdate).toHaveBeenCalledWith({
      ...defaultRoutine,
      pre_condition: {
        trigger_type: 'sensor',
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      },
    })
  })

  it('shows "Gated" badge when routine has pre_condition', () => {
    const routineWithPreCondition = {
      ...defaultRoutine,
      pre_condition: {
        trigger_type: 'sensor',
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
      },
    }
    render(
      <RoutineCard {...defaultProps} routine={routineWithPreCondition} />
    )
    expect(screen.getByText('Gated')).toBeInTheDocument()
  })

  it('does not show "Gated" badge when routine has no pre_condition', () => {
    render(<RoutineCard {...defaultProps} />)
    expect(screen.queryByText('Gated')).not.toBeInTheDocument()
  })
})
```

**Step 2: Run tests to verify they fail**

Run: `cd webui/frontend && npx vitest run src/components/scheduler/ScheduleEditor/__tests__/RoutineCard.test.jsx`

Expected: 5 FAIL

**Step 3: Implement integration**

In `RoutineCard.jsx`:

1. Add import:
```jsx
import PreConditionForm from './PreConditionForm'
```

2. Add handler after `handleActionsChange`:
```jsx
const handlePreConditionChange = useCallback(
  (newPreCondition) => {
    onUpdate({
      ...routine,
      pre_condition: newPreCondition,
    })
  },
  [onUpdate, routine]
)
```

3. In the header section (between `TriggerLabel` and `ChevronDownIcon`), add the "Gated" badge:
```jsx
<TriggerLabel trigger={routine.trigger} />
{routine.pre_condition && (
  <span className="text-xs text-amber-500/70 font-medium">Gated</span>
)}
<ChevronDownIcon ... />
```

4. In the expanded body, after `<TriggerSelector>`, add PreConditionForm:
```jsx
<TriggerSelector
  trigger={routine.trigger}
  onChange={handleTriggerChange}
  disabled={disabled}
/>
<PreConditionForm
  preCondition={routine.pre_condition || null}
  onChange={handlePreConditionChange}
  routineIndex={index}
  disabled={disabled}
/>
```

**Step 4: Run tests to verify they pass**

Run: `cd webui/frontend && npx vitest run src/components/scheduler/ScheduleEditor/__tests__/RoutineCard.test.jsx`

Expected: ALL PASS

**Step 5: Commit**

```bash
git add webui/frontend/src/components/scheduler/ScheduleEditor/RoutineCard.jsx \
       webui/frontend/src/components/scheduler/ScheduleEditor/__tests__/RoutineCard.test.jsx
git commit -m "feat(ui): integrate PreConditionForm into RoutineCard (#271)"
```

---

### Task 6: Integrate PreConditionForm into NewRoutineCard

**Files:**
- Modify: `webui/frontend/src/components/scheduler/ScheduleEditor/NewRoutineCard.jsx`
- Modify: `webui/frontend/src/components/scheduler/ScheduleEditor/__tests__/NewRoutineCard.test.jsx`

**Step 1: Write the failing tests**

Add a mock for PreConditionForm at the top of `NewRoutineCard.test.jsx`, after existing mocks:

```jsx
// Mock PreConditionForm
vi.mock('../PreConditionForm', () => ({
  default: vi.fn(({ preCondition, onChange, routineIndex, disabled }) => (
    <div data-testid="mock-pre-condition-form">
      <span data-testid="pre-condition-status">
        {preCondition ? 'enabled' : 'disabled'}
      </span>
      <button
        onClick={() =>
          onChange({
            trigger_type: 'sensor',
            sensor_type: 'light',
            comparison: 'lt',
            threshold: 100,
            cooldown_minutes: 5,
          })
        }
        disabled={disabled}
        data-testid="enable-pre-condition"
      >
        Enable Pre-Condition
      </button>
      <button
        onClick={() => onChange(null)}
        disabled={disabled}
        data-testid="disable-pre-condition"
      >
        Disable Pre-Condition
      </button>
    </div>
  )),
}))
```

Add a new `describe('pre-condition integration')` block:

```jsx
describe('pre-condition integration', () => {
  it('renders PreConditionForm', () => {
    render(<NewRoutineCard {...defaultProps} />)
    expect(screen.getByTestId('mock-pre-condition-form')).toBeInTheDocument()
  })

  it('initializes with no pre-condition', () => {
    render(<NewRoutineCard {...defaultProps} />)
    expect(screen.getByTestId('pre-condition-status')).toHaveTextContent('disabled')
  })

  it('includes pre_condition in saved routine when set', async () => {
    const user = userEvent.setup()
    const onComplete = vi.fn()
    render(<NewRoutineCard {...defaultProps} onComplete={onComplete} />)

    // Enable pre-condition
    await user.click(screen.getByTestId('enable-pre-condition'))

    // Add an action
    await user.click(screen.getByText('Add Action'))

    // Save
    await user.click(screen.getByTestId('save-routine'))

    expect(onComplete).toHaveBeenCalledWith(
      expect.objectContaining({
        pre_condition: {
          trigger_type: 'sensor',
          sensor_type: 'light',
          comparison: 'lt',
          threshold: 100,
          cooldown_minutes: 5,
        },
      })
    )
  })

  it('saves routine without pre_condition when not set', async () => {
    const user = userEvent.setup()
    const onComplete = vi.fn()
    render(<NewRoutineCard {...defaultProps} onComplete={onComplete} />)

    // Add an action (no pre-condition)
    await user.click(screen.getByText('Add Action'))

    // Save
    await user.click(screen.getByTestId('save-routine'))

    const savedRoutine = onComplete.mock.calls[0][0]
    expect(savedRoutine.pre_condition).toBeNull()
  })
})
```

**Step 2: Run tests to verify they fail**

Run: `cd webui/frontend && npx vitest run src/components/scheduler/ScheduleEditor/__tests__/NewRoutineCard.test.jsx`

Expected: 4 FAIL

**Step 3: Implement integration**

In `NewRoutineCard.jsx`:

1. Add import:
```jsx
import PreConditionForm from './PreConditionForm'
```

2. Add state:
```jsx
const [preCondition, setPreCondition] = useState(null)
```

3. Add handler:
```jsx
const handlePreConditionChange = useCallback((newPreCondition) => {
  setPreCondition(newPreCondition)
}, [])
```

4. Include `pre_condition` in the routine object in `handleSave`:
```jsx
const routine = {
  routine_id: generateUUID(),
  name: '',
  trigger,
  actions,
  pre_condition: preCondition,
}
```

5. Render `PreConditionForm` after `TriggerSelector` inside the Trigger div:
```jsx
<TriggerSelector
  trigger={trigger}
  onChange={handleTriggerChange}
  disabled={disabled}
/>
<PreConditionForm
  preCondition={preCondition}
  onChange={handlePreConditionChange}
  routineIndex={0}
  disabled={disabled}
/>
```

**Step 4: Run tests to verify they pass**

Run: `cd webui/frontend && npx vitest run src/components/scheduler/ScheduleEditor/__tests__/NewRoutineCard.test.jsx`

Expected: ALL PASS

**Step 5: Commit**

```bash
git add webui/frontend/src/components/scheduler/ScheduleEditor/NewRoutineCard.jsx \
       webui/frontend/src/components/scheduler/ScheduleEditor/__tests__/NewRoutineCard.test.jsx
git commit -m "feat(ui): integrate PreConditionForm into NewRoutineCard (#271)"
```

---

### Task 7: Run full test suite and lint

**Step 1: Run all scheduler tests**

Run: `cd webui/frontend && npx vitest run src/components/scheduler/ScheduleEditor/__tests__/`

Expected: ALL PASS

**Step 2: Run ruff and ESLint**

Run: `cd webui/frontend && npx eslint src/components/scheduler/ScheduleEditor/PreConditionForm.jsx src/components/scheduler/ScheduleEditor/RoutineCard.jsx src/components/scheduler/ScheduleEditor/NewRoutineCard.jsx src/components/scheduler/ScheduleEditor/propTypes.js`

Expected: No errors

**Step 3: Final commit (if any lint fixes needed)**

```bash
git add -A && git commit -m "style: fix lint issues for pre-condition UI (#271)"
```
