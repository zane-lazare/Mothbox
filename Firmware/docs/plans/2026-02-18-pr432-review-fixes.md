# PR #432 Review Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Address 4 code review recommendations from PR #432 (sensor pre-condition UI).

**Architecture:** Small targeted fixes to PreConditionForm (same-time validation, error state) and test files (edge cases, mock cleanup). All changes are in the `feat/271-sensor-precondition-ui` branch.

**Tech Stack:** React 18, Vitest, @testing-library/react, Tailwind CSS

---

### Task 1: Remove unused `routineIndex` from RoutineCard mock

**Files:**
- Modify: `webui/frontend/src/components/scheduler/ScheduleEditor/__tests__/RoutineCard.test.jsx:43`

**Step 1: Fix the mock**

Change line 43 from:
```jsx
  default: vi.fn(({ preCondition, onChange, routineIndex, disabled }) => ( // eslint-disable-line no-unused-vars
```
to:
```jsx
  default: vi.fn(({ preCondition, onChange, disabled }) => (
```

**Step 2: Run tests to verify nothing breaks**

Run: `cd webui/frontend && npx vitest run src/components/scheduler/ScheduleEditor/__tests__/RoutineCard.test.jsx`
Expected: All 35 tests PASS

**Step 3: Run ESLint to verify no warnings**

Run: `cd webui/frontend && npx eslint src/components/scheduler/ScheduleEditor/__tests__/RoutineCard.test.jsx`
Expected: Clean (no warnings or errors)

**Step 4: Commit**

```bash
git add webui/frontend/src/components/scheduler/ScheduleEditor/__tests__/RoutineCard.test.jsx
git commit -m "fix: remove unused routineIndex from RoutineCard test mock (#271)"
```

---

### Task 2: Add cooldown edge case tests

**Files:**
- Modify: `webui/frontend/src/components/scheduler/ScheduleEditor/__tests__/PreConditionForm.test.jsx`

**Step 1: Write 3 failing tests**

Add inside the existing `describe('Cooldown', () => { ... })` block, after the last test (`it('includes cooldown_minutes in default pre-condition'`):

```jsx
    it('shows error for non-numeric cooldown input', () => {
      render(
        <PreConditionForm preCondition={preConditionWithCooldown} onChange={mockOnChange} routineIndex={0} />
      )
      const cooldownInput = screen.getByTestId('pre-condition-cooldown')
      fireEvent.change(cooldownInput, { target: { value: 'abc' } })

      expect(screen.getByTestId('pre-condition-cooldown-error')).toBeInTheDocument()
      expect(mockOnChange).not.toHaveBeenCalled()
    })

    it('shows error for empty cooldown input', () => {
      render(
        <PreConditionForm preCondition={preConditionWithCooldown} onChange={mockOnChange} routineIndex={0} />
      )
      const cooldownInput = screen.getByTestId('pre-condition-cooldown')
      fireEvent.change(cooldownInput, { target: { value: '' } })

      expect(screen.getByTestId('pre-condition-cooldown-error')).toBeInTheDocument()
      expect(mockOnChange).not.toHaveBeenCalled()
    })

    it('accepts decimal cooldown values within range', () => {
      render(
        <PreConditionForm preCondition={preConditionWithCooldown} onChange={mockOnChange} routineIndex={0} />
      )
      const cooldownInput = screen.getByTestId('pre-condition-cooldown')
      fireEvent.change(cooldownInput, { target: { value: '5.5' } })

      expect(screen.queryByTestId('pre-condition-cooldown-error')).not.toBeInTheDocument()
      expect(mockOnChange).toHaveBeenCalledWith({
        ...preConditionWithCooldown,
        cooldown_minutes: 5.5,
      })
    })
```

**Step 2: Run tests to verify they pass** (these test existing behavior, so they should pass immediately)

Run: `cd webui/frontend && npx vitest run src/components/scheduler/ScheduleEditor/__tests__/PreConditionForm.test.jsx`
Expected: All tests PASS (including 3 new ones — the validation logic already exists)

**Step 3: Commit**

```bash
git add webui/frontend/src/components/scheduler/ScheduleEditor/__tests__/PreConditionForm.test.jsx
git commit -m "test: add cooldown edge case tests for PreConditionForm (#271)"
```

---

### Task 3: Add same-time validation to PreConditionForm

**Files:**
- Modify: `webui/frontend/src/components/scheduler/ScheduleEditor/PreConditionForm.jsx`
- Modify: `webui/frontend/src/components/scheduler/ScheduleEditor/__tests__/PreConditionForm.test.jsx`

**Step 1: Write 3 failing tests**

Add a new `describe('Time window validation')` block inside the `describe('Time window')` block, after the `it('updates end time')` test:

```jsx
    it('shows error when start and end times are the same', () => {
      const withTimeWindow = {
        ...preConditionBase,
        time_window: { start_time: '21:00', end_time: '21:00' },
      }
      render(
        <PreConditionForm preCondition={withTimeWindow} onChange={mockOnChange} routineIndex={0} />
      )
      expect(screen.getByTestId('pre-condition-tw-error')).toHaveTextContent(
        'Start and end times cannot be the same'
      )
    })

    it('clears error when times are changed to be different', () => {
      const withSameTime = {
        ...preConditionBase,
        time_window: { start_time: '21:00', end_time: '21:00' },
      }
      const { rerender } = render(
        <PreConditionForm preCondition={withSameTime} onChange={mockOnChange} routineIndex={0} />
      )
      expect(screen.getByTestId('pre-condition-tw-error')).toBeInTheDocument()

      rerender(
        <PreConditionForm
          preCondition={{ ...preConditionBase, time_window: { start_time: '21:00', end_time: '06:00' } }}
          onChange={mockOnChange}
          routineIndex={0}
        />
      )
      expect(screen.queryByTestId('pre-condition-tw-error')).not.toBeInTheDocument()
    })

    it('renders time window with empty times without error', () => {
      const withEmptyTimes = {
        ...preConditionBase,
        time_window: { start_time: '', end_time: '' },
      }
      render(
        <PreConditionForm preCondition={withEmptyTimes} onChange={mockOnChange} routineIndex={0} />
      )
      expect(screen.getByTestId('pre-condition-tw-start')).toBeInTheDocument()
      expect(screen.getByTestId('pre-condition-tw-end')).toBeInTheDocument()
      expect(screen.queryByTestId('pre-condition-tw-error')).not.toBeInTheDocument()
    })
```

**Step 2: Run tests to verify they fail**

Run: `cd webui/frontend && npx vitest run src/components/scheduler/ScheduleEditor/__tests__/PreConditionForm.test.jsx`
Expected: 3 new tests FAIL (no `pre-condition-tw-error` element exists yet)

**Step 3: Implement same-time validation**

In `PreConditionForm.jsx`, add the validation logic. Import `TIME_ERRORS` from errorMessages:

Change line 4 from:
```jsx
import { NUMERIC_ERRORS } from './errorMessages'
```
to:
```jsx
import { NUMERIC_ERRORS, TIME_ERRORS } from './errorMessages'
```

Add a computed error check inside the component body, after the `handleCooldownChange` function (after line 113):

```jsx
  // Validate same start/end time
  const timeWindowError =
    preCondition?.time_window?.start_time &&
    preCondition?.time_window?.end_time &&
    preCondition.time_window.start_time === preCondition.time_window.end_time
      ? TIME_ERRORS.START_AFTER_END
      : null
```

Note: We reuse `TIME_ERRORS.START_AFTER_END` ("Start time must be before end time") which is close enough. However, the test expects "Start and end times cannot be the same". Let's add a new error message instead.

In `errorMessages.js`, add to `TIME_ERRORS` (after line 82):

```js
  SAME_START_END: 'Start and end times cannot be the same',
```

Then in `PreConditionForm.jsx`, use `TIME_ERRORS.SAME_START_END`:

```jsx
  const timeWindowError =
    preCondition?.time_window?.start_time &&
    preCondition?.time_window?.end_time &&
    preCondition.time_window.start_time === preCondition.time_window.end_time
      ? TIME_ERRORS.SAME_START_END
      : null
```

Add the error display in the JSX. After the time window inputs `</div>` (after line 275), before the closing `</div>` of the `pl-6` block:

```jsx
          {/* Time window validation error */}
          {timeWindowError && (
            <p className="pl-6 text-sm text-red-600 dark:text-red-400" data-testid="pre-condition-tw-error">
              {timeWindowError}
            </p>
          )}
```

**Step 4: Run tests to verify they pass**

Run: `cd webui/frontend && npx vitest run src/components/scheduler/ScheduleEditor/__tests__/PreConditionForm.test.jsx`
Expected: All tests PASS

**Step 5: Run full PreConditionForm + RoutineCard + NewRoutineCard tests**

Run: `cd webui/frontend && npx vitest run src/components/scheduler/ScheduleEditor/__tests__/PreConditionForm.test.jsx src/components/scheduler/ScheduleEditor/__tests__/RoutineCard.test.jsx src/components/scheduler/ScheduleEditor/__tests__/NewRoutineCard.test.jsx`
Expected: All tests PASS

**Step 6: Run ESLint**

Run: `cd webui/frontend && npx eslint src/components/scheduler/ScheduleEditor/PreConditionForm.jsx src/components/scheduler/ScheduleEditor/errorMessages.js`
Expected: Clean

**Step 7: Commit**

```bash
git add webui/frontend/src/components/scheduler/ScheduleEditor/PreConditionForm.jsx \
       webui/frontend/src/components/scheduler/ScheduleEditor/errorMessages.js \
       webui/frontend/src/components/scheduler/ScheduleEditor/__tests__/PreConditionForm.test.jsx
git commit -m "feat: add same-time validation to PreConditionForm time window (#271)"
```
