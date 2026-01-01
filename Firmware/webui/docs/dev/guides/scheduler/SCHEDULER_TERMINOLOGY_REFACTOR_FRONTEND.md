# Scheduler Terminology Refactor - Frontend Implementation

**Purpose**: Guide for implementing React component renames, new hooks, and UI changes.

**Prerequisites**: Read [Overview](./SCHEDULER_TERMINOLOGY_REFACTOR_OVERVIEW.md) for architecture context.

**Next Steps**: [Testing Strategy](./SCHEDULER_TERMINOLOGY_REFACTOR_TESTING.md)

> **TDD Workflow**: Before implementing each component below, follow the TDD protocol in
> [Testing Strategy → TDD Approach](./SCHEDULER_TERMINOLOGY_REFACTOR_TESTING.md#tdd-approach-with-e2e-phases).
> Write tests first, run them (expect failure), implement the change, run tests again (expect pass).

---

## Table of Contents

1. [Design Reference](#design-reference)
2. [UX Architecture Decisions](#ux-architecture-decisions)
3. [UI Streamlining Requirements](#ui-streamlining-requirements)
4. [File Structure](#file-structure)
5. [Import Updates](#import-updates)
6. [Hooks Implementation](#hooks-implementation)
7. [Utility Functions](#utility-functions)
8. [Component Implementations](#component-implementations)
9. [Component States](#component-states)
10. [State Management](#state-management)
11. [Styles](#styles)
12. [CalendarView Enhancements](#calendarview-enhancements)
13. [Activation Progress UI](#activation-progress-ui)
14. [API Utilities Updates](#api-utilities-updates)
15. [E2E Test Updates](#e2e-test-updates)

---

## Design Reference

Interactive HTML mockups serve as the canonical design reference for layout, component structure, and interactions.

### Primary Mockups

| Mockup | Description | Path |
|--------|-------------|------|
| **Unified Desktop** | Full scheduler page with modal editor, timeline, conflicts | `webui/docs/dev/mockups/unified-scheduler-mockup.html` |
| **Unified Mobile** | Mobile layout with slide-up sheets, touch interactions | `webui/docs/dev/mockups/unified-scheduler-mobile-mockup.html` |

### Component Mockups

| Mockup | Description | Path |
|--------|-------------|------|
| Timeline Conflicts | Conflict highlighting (red=collision, yellow=warning) | `webui/docs/dev/mockups/day-timeline-conflicts-mockup.html` |
| Trigger Forms | All 6 trigger type configurations | `webui/docs/dev/mockups/trigger-forms-mockup.html` |
| Activation Progress | Progress states during schedule activation | `webui/docs/dev/mockups/activation-progress-mockup.html` |
| Mobile Editor | Mobile schedule editor (standalone) | `webui/docs/dev/mockups/mobile-schedule-editor-mockup.html` |

### Design Principles

The mockups demonstrate a **minimalistic design approach**:

- Reduced visual clutter - fewer borders, badges, and decorative elements
- More whitespace between sections
- Subtle, thin borders for containers
- Transparent/minimal input styling
- Small status indicators (dots instead of large badges)
- Compact execution chips in timeline

### Implementation Notes

- **Colors**: Use existing Tailwind classes from the codebase. Reference `index.css` for component utilities (`settings-*` classes) and existing scheduler components for color patterns
- **Layout**: Match the mockup layouts (grid structure, spacing, responsive breakpoints)
- **Interactions**: Implement the interaction patterns shown (expand/collapse, slide-up sheets, progress animations)

### CSS Class Mapping (from Mockups)

The mockups use specific Tailwind classes for dark mode styling. Use these exact patterns:

**Container Backgrounds:**
- Page background: `bg-gray-950`
- Card background: `bg-gray-900` or `bg-gray-900/50` (slight transparency)
- Modal overlay: `rgba(0, 0, 0, 0.6)` or `bg-black/60`

**Borders:**
- Default: `border-gray-800`
- Hover/selected: `border-gray-700`
- Dashed (drafts): `border-dashed border-gray-800`
- Focus: `focus:border-gray-600`

**Text Colors:**
- Primary (headings): `text-white`
- Secondary (body): `text-gray-300`
- Muted (labels): `text-gray-500`
- Disabled: `text-gray-600`

**Status Colors:**
- Active: `bg-green-500` (dot), `text-green-400` (text)
- Warning: `bg-yellow-500`, `text-yellow-400`, `ring-yellow-400`, `bg-yellow-950/20` (row bg)
- Error/Collision: `bg-red-500`, `text-red-400`, `ring-red-400`, `bg-red-950/20` (row bg)
- Draft: `text-yellow-500` (different shade for drafts vs warnings)

**Routine Color Dots (in mockup):**
- GPIO actions (attract/flash): `bg-orange-400`
- Camera actions: `bg-blue-400`
- HDR/special: `bg-purple-400`

**Execution Chips:**
```html
<!-- Normal chip -->
<span class="text-xs px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded">18:15</span>

<!-- Collision chip -->
<span class="text-xs px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded ring-1 ring-red-400">19:00</span>

<!-- GPIO chip -->
<span class="text-xs px-2 py-0.5 bg-orange-500/20 text-orange-400 rounded">17:23 Attract On</span>
```

**Form Inputs:**
```html
<input class="w-full bg-transparent border border-gray-800 rounded px-3 py-2 text-white text-sm focus:border-gray-600 focus:outline-none" />
<select class="w-full bg-transparent border border-gray-800 rounded px-3 py-2 text-sm text-white" />
```

**Buttons:**
```html
<!-- Primary (white) -->
<button class="px-4 py-2 bg-white text-gray-900 text-sm rounded hover:bg-gray-100">Save</button>

<!-- Secondary (text only) -->
<button class="text-sm text-gray-500 hover:text-white">Cancel</button>

<!-- Danger -->
<button class="text-sm text-red-400 hover:text-red-300">Deactivate</button>

<!-- Add button (dashed) -->
<button class="w-full py-3 border border-dashed border-gray-800 rounded text-sm text-gray-600 hover:border-gray-600 hover:text-gray-400">+ Add Routine</button>
```

**Routine Card Expand/Collapse:**
```css
.routine-body { max-height: 0; overflow: hidden; transition: max-height 0.2s ease-out; }
.routine-body.open { max-height: 800px; }
```

**Progress Bar:**
```html
<div class="h-1 bg-gray-800 rounded-full overflow-hidden">
  <div class="h-full bg-blue-500 transition-all duration-500" style="width: 35%"></div>
</div>
```

**Spinner (activating state):**
```html
<div class="w-3 h-3 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"></div>
```

### Viewing Mockups

```bash
# Desktop unified mockup
xdg-open webui/docs/dev/mockups/unified-scheduler-mockup.html

# Mobile unified mockup
xdg-open webui/docs/dev/mockups/unified-scheduler-mobile-mockup.html
```

> **TDD Protocol**: For complete frontend testing patterns, file renames, and E2E transition strategy, see:
> **[Testing Strategy](./SCHEDULER_TERMINOLOGY_REFACTOR_TESTING.md)**
>
> Key sections:
> - [E2E Test Transition Strategy](./SCHEDULER_TERMINOLOGY_REFACTOR_TESTING.md#e2e-test-transition-strategy) - Skip list, fixme markers
> - [Selector Conventions](./SCHEDULER_TERMINOLOGY_REFACTOR_TESTING.md#selector-conventions) - data-testid patterns
> - [When to Transition Tests](./SCHEDULER_TERMINOLOGY_REFACTOR_TESTING.md#when-to-transition-tests) - Timing guidance

---

## UX Architecture Decisions

Based on clarifying questions discussion, the frontend uses these patterns:

### Routine List Display

- **Collapsed state**: Show auto-generated name + trigger type badge (e.g., "Attract On at Dusk" with `[Solar]` badge)
- **Expanded state**: Full TriggerForm + ActionList with inline editing
- **Interaction**: Click anywhere on collapsed card to expand/collapse

```jsx
// RoutineCard collapsed state
<div className="routine-card collapsed" onClick={toggleExpand}>
  <span className="routine-name">{routine.get_display_name()}</span>
  <TriggerBadge trigger={routine.trigger} />
  <ChevronIcon direction={expanded ? 'up' : 'down'} />
</div>
```

### Schedule-Level Timeline

A visual timeline showing all routine executions:
- Unified view of when all routines fire
- Time collisions highlighted in **red**
- GPIO state conflicts highlighted in **yellow** (warnings only)
- Interactive: hover for details, click to jump to routine

```jsx
// CalendarView with day view as default
<CalendarView
  scheduleId={schedule.schedule_id}
  defaultViewMode="day"
  showConflicts={true}
  onExecutionClick={(execution) => scrollToRoutine(execution.routine_id)}
/>
```

### Add Routine Flow (Inline Wizard)

Simplified inline workflow, not a separate modal:

1. Click `[+ Add Routine]` button
2. New routine card expands inline at bottom of list
3. Select trigger type (dropdown)
4. Configure trigger parameters (inline forms)
5. Add actions with `[+ Add Action]` button
6. Done - no explicit save (controlled component, auto-saves on blur)

```jsx
// Inline wizard flow
<RoutineList>
  {routines.map(r => <RoutineCard routine={r} />)}

  {isAddingRoutine ? (
    <NewRoutineCard
      onComplete={(routine) => addRoutine(routine)}
      onCancel={() => setIsAddingRoutine(false)}
    />
  ) : (
    <button onClick={() => setIsAddingRoutine(true)}>
      + Add Routine
    </button>
  )}
</RoutineList>
```

---

## UI Streamlining Requirements

Based on Q13.1 clarifications, the UI prioritizes simplicity.

### Core Principles

1. **Minimal clicks**: Common workflows achievable in 3-5 clicks
2. **Progressive disclosure**: Advanced options (pre-conditions, cron) hidden by default
3. **Smart defaults**: Built-in schedules cover 80% of use cases
4. **Inline editing**: No modal dialogs for routine configuration
5. **Auto-save**: Changes save on blur

### Component Simplification

| Component | Streamlined Behavior |
|-----------|---------------------|
| TriggerSelector | Show 3 common types + "More..." expander |
| PreConditionForm | Hidden until "Add condition" clicked |
| ActionForm | Single dropdown, parameters auto-expand |
| RoutineCard | Collapsed by default |
| Built-in Schedules | Prominent placement at top |

### Mobile-First

- Touch targets 44x44px minimum
- Swipe to delete routines
- Bottom sheet for selections on mobile
- Responsive: 1 col mobile, 2 col tablet, 3 col desktop

### Accessibility

- Keyboard navigable
- ARIA labels for badges/icons
- Focus management on add/remove
- Screen reader announcements

---

## File Structure

### Files to Rename

**Directory rename: `PatternEditor/` → `RoutineEditor/`**

| Current Path | New Path |
|--------------|----------|
| `components/scheduler/PatternEditor/` | `components/scheduler/RoutineEditor/` |
| `PatternEditor/PatternEditor.jsx` | `RoutineEditor/RoutineEditor.jsx` |
| `PatternEditor/ActionList.jsx` | `RoutineEditor/ActionList.jsx` |
| `PatternEditor/ActionForm.jsx` | `RoutineEditor/ActionForm.jsx` |
| `PatternEditor/OffsetTimeline.jsx` | `RoutineEditor/OffsetTimeline.jsx` |
| `PatternEditor/constants.js` | `RoutineEditor/constants.js` |
| `PatternEditor/index.js` | `RoutineEditor/index.js` |
| `PatternEditor/__tests__/PatternEditor.test.jsx` | `RoutineEditor/__tests__/RoutineEditor.test.jsx` |
| `PatternEditor/__tests__/ActionList.test.jsx` | `RoutineEditor/__tests__/ActionList.test.jsx` |
| `PatternEditor/__tests__/ActionForm.test.jsx` | `RoutineEditor/__tests__/ActionForm.test.jsx` |
| `PatternEditor/__tests__/OffsetTimeline.test.jsx` | `RoutineEditor/__tests__/OffsetTimeline.test.jsx` |

**Hooks rename:**

| Current Path | New Path |
|--------------|----------|
| `hooks/useEventPatterns.js` | `hooks/useRoutines.js` |
| `hooks/__tests__/useEventPatterns.test.jsx` | `hooks/__tests__/useRoutines.test.jsx` |

### Files to Delete

**PatternLibrary directory (entire):**
- `components/scheduler/PatternLibrary/PatternCard.jsx`
- `components/scheduler/PatternLibrary/PatternList.jsx`
- `components/scheduler/PatternLibrary/PatternFilters.jsx`
- `components/scheduler/PatternLibrary/PatternDetailsDrawer.jsx`
- `components/scheduler/PatternLibrary/index.js`
- `components/scheduler/PatternLibrary/__tests__/PatternCard.test.jsx`
- `components/scheduler/PatternLibrary/__tests__/PatternList.test.jsx`
- `components/scheduler/PatternLibrary/__tests__/PatternFilters.test.jsx`
- `components/scheduler/PatternLibrary/__tests__/PatternDetailsDrawer.test.jsx`
- `components/scheduler/PatternLibrary/__tests__/integration.test.jsx`

**ScheduleEditor removals:**
- `components/scheduler/ScheduleEditor/EventPatternSelector.jsx`
- `components/scheduler/ScheduleEditor/__tests__/EventPatternSelector.test.jsx`
- `components/scheduler/ScheduleEditor/DateRangeSection.jsx` (schedule-level dates removed)
- `components/scheduler/ScheduleEditor/__tests__/DateRangeSection.test.jsx`

**Hooks removals:**
- `hooks/useSchedulePatterns.js`
- `hooks/__tests__/useSchedulePatterns.test.jsx`

### Files to Modify

| File | Changes Required |
|------|------------------|
| `components/scheduler/index.js` | Update exports: `PatternEditor` → `RoutineEditor`, remove `PatternLibrary` |
| `components/scheduler/ScheduleEditor/index.js` | Remove `EventPatternSelector`, `DateRangeSection` exports |
| `components/scheduler/ScheduleEditor/ScheduleEditor.jsx` | Major refactor (see below) |
| `components/scheduler/ScheduleEditor/propTypes.js` | Replace `eventPatterns` → `routines`, add `RoutinePropType` |
| `components/scheduler/ScheduleEditor/__tests__/ScheduleEditor.test.jsx` | Update field names and imports |
| `components/scheduler/ScheduleEditor/__tests__/ScheduleEditor.integration.test.jsx` | Update field names |
| `components/scheduler/ScheduleEditor/__tests__/propTypes.test.js` | Update prop type tests |
| `components/scheduler/CalendarView/ExecutionMarker.jsx` | Add `conflict` prop for highlighting |
| `components/scheduler/CalendarView/ExecutionDetailModal.jsx` | Update pattern → routine references |
| `components/scheduler/CalendarView/CalendarView.jsx` | Default to day view, integrate DayTimeline |
| `hooks/useSchedules.js` | Replace `event_patterns` → `routines` in transformations |

### ScheduleEditor.jsx - Detailed Changes

**Remove imports:**
```javascript
import EventPatternSelector from './EventPatternSelector';
import DateRangeSection from './DateRangeSection';
```

**Add imports:**
```javascript
import RoutineList from './RoutineList';
import RoutineCard from './RoutineCard';
import NewRoutineCard from './NewRoutineCard';
import TriggerSelector from './TriggerSelector';
import TriggerBadge from './TriggerBadge';
import ActivationProgress from './ActivationProgress';
import { RoutinePropType } from './propTypes';
```

**State changes:**
```javascript
// REMOVE
const [patternSelection, setPatternSelection] = useState({...});
const [dateRange, setDateRange] = useState({...});

// ADD
const [routines, setRoutines] = useState([]);
const [isAddingRoutine, setIsAddingRoutine] = useState(false);
const [isActivating, setIsActivating] = useState(false);
```

**Data structure changes:**
```javascript
// REMOVE from scheduleData
event_patterns: patternSelection.pattern ? [patternSelection.pattern] : [],
date_range: {...},

// ADD to scheduleData
routines: routines,
```

### New Files to Create

| File | Purpose |
|------|---------|
| `components/scheduler/ScheduleEditor/RoutineList.jsx` | Container for routine cards |
| `components/scheduler/ScheduleEditor/RoutineCard.jsx` | Collapsible routine display |
| `components/scheduler/ScheduleEditor/NewRoutineCard.jsx` | Inline add routine wizard |
| `components/scheduler/ScheduleEditor/TriggerSelector.jsx` | Trigger type dropdown + form |
| `components/scheduler/ScheduleEditor/TriggerBadge.jsx` | Small trigger type badge |
| `components/scheduler/ScheduleEditor/RecurringDaysTriggerForm.jsx` | "Every N days" config |
| `components/scheduler/ScheduleEditor/PreConditionForm.jsx` | Optional sensor condition |
| `components/scheduler/ScheduleEditor/ActivationProgress.jsx` | WebSocket progress display |
| `components/scheduler/CalendarView/DayTimeline.jsx` | Hourly timeline for day view |
| `utils/routineUtils.js` | Utility functions for routine display |
| `components/scheduler/ScheduleEditor/__tests__/RoutineList.test.jsx` | Tests |
| `components/scheduler/ScheduleEditor/__tests__/RoutineCard.test.jsx` | Tests |
| `components/scheduler/ScheduleEditor/__tests__/NewRoutineCard.test.jsx` | Tests |
| `components/scheduler/ScheduleEditor/__tests__/TriggerSelector.test.jsx` | Tests |
| `components/scheduler/ScheduleEditor/__tests__/TriggerBadge.test.jsx` | Tests |
| `components/scheduler/ScheduleEditor/__tests__/RecurringDaysTriggerForm.test.jsx` | Tests |
| `components/scheduler/ScheduleEditor/__tests__/PreConditionForm.test.jsx` | Tests |
| `components/scheduler/ScheduleEditor/__tests__/ActivationProgress.test.jsx` | Tests |
| `components/scheduler/CalendarView/__tests__/DayTimeline.test.jsx` | Tests |
| `utils/__tests__/routineUtils.test.js` | Tests |

---

## Import Updates

After renaming files, update all import statements. Use these commands to find affected files:

### Find All Imports to Update

```bash
# PatternEditor imports (directory moved)
rg "from.*PatternEditor|import.*PatternEditor" webui/frontend/src/

# PatternLibrary imports (being deleted)
rg "from.*PatternLibrary|import.*PatternLibrary" webui/frontend/src/

# EventPatternSelector imports (being deleted)
rg "EventPatternSelector" webui/frontend/src/

# useEventPatterns hook (being renamed)
rg "useEventPatterns" webui/frontend/src/

# useSchedulePatterns hook (being deleted)
rg "useSchedulePatterns" webui/frontend/src/

# Field name references (event_patterns → routines)
rg "event_patterns|eventPatterns" webui/frontend/src/

# PatternAction references (→ Action)
rg "PatternAction|patternAction" webui/frontend/src/
```

### All-in-One Check

```bash
# Find all old terminology in one command
rg "(PatternEditor|PatternLibrary|EventPatternSelector|useEventPatterns|useSchedulePatterns|event_patterns|eventPatterns|PatternAction|patternAction)" \
  webui/frontend/src/ \
  -t js -t jsx
```

### Verification After Refactor

```bash
# Should return no results when complete
rg "(PatternEditor|PatternLibrary|EventPatternSelector|useEventPatterns|useSchedulePatterns|event_patterns|eventPatterns)" \
  webui/frontend/src/ \
  -t js
```

---

## Hooks Implementation

### useRoutines.js

**File:** `hooks/useRoutines.js`

```javascript
/**
 * React Query hooks for Routine operations
 */

import { useMemo } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { QUERY_KEYS } from '../utils/queryKeys'
import { listBuiltinSchedules } from '../utils/schedulerApi'

const QUERY_CONFIG = {
  STALE_TIME: 5 * 60 * 1000,
}

function handleMutationError(error, operation) {
  if (import.meta.env.DEV) {
    console.error(`[Routine ${operation}]:`, error.message || error)
  }
}

/**
 * List built-in schedules
 *
 * @returns {Object} data - { schedules: [...], total }
 */
export function useBuiltinSchedules(queryOptions = {}) {
  return useQuery({
    queryKey: QUERY_KEYS.BUILTIN_SCHEDULES,
    queryFn: async () => {
      const response = await listBuiltinSchedules()
      return response.data
    },
    staleTime: QUERY_CONFIG.STALE_TIME,
    ...queryOptions,
  })
}

// Note: Routine validation happens as part of schedule validation.
// There is no separate useValidateRoutine hook - validation errors
// are returned from the schedule create/update mutations.

/**
 * Clone a built-in schedule for customization
 *
 * Built-in schedules are read-only. To customize:
 * 1. Load built-in schedule from GET /schedules/builtin
 * 2. Copy data and generate new schedule_id
 * 3. POST to /schedules as new user schedule
 */
export function useCloneBuiltinSchedule() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (builtinSchedule) => {
      // Generate new ID and mark as user schedule
      const clonedSchedule = {
        ...builtinSchedule,
        schedule_id: generateUUID(),
        name: `${builtinSchedule.name} (Copy)`,
        is_builtin: false,
      }

      const response = await fetch('/api/scheduler/ui/schedules', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify(clonedSchedule),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to clone schedule')
      }

      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SCHEDULES })
    },
    onError: (error) => handleMutationError(error, 'cloneBuiltinSchedule'),
  })
}

/**
 * Calculate total duration of a routine from action offsets
 */
export function useRoutineDuration(routine) {
  return useMemo(() => {
    if (!routine?.actions?.length) return 0
    return Math.max(...routine.actions.map(a => a.offset_minutes ?? 0))
  }, [routine])
}

export default useBuiltinSchedules
```

### queryKeys.js Updates

```javascript
// In utils/queryKeys.js

export const QUERY_KEYS = {
  // ... existing keys ...
  BUILTIN_SCHEDULES: ['scheduler', 'schedules', 'builtin'],
  ROUTINES: ['scheduler', 'routines'],
}
```

### schedulerApi.js Updates

```javascript
// In utils/schedulerApi.js

export async function listBuiltinSchedules() {
  const response = await fetch('/api/scheduler/ui/schedules/builtin')
  if (!response.ok) throw new Error('Failed to fetch built-in schedules')
  return { data: await response.json() }
}

// Note: Routine validation happens as part of schedule validation.
// There is no separate /routines/validate endpoint.
// Validation errors are returned from POST/PUT /schedules endpoints.
```

---

## Utility Functions

### routineUtils.js

**File:** `utils/routineUtils.js`

```javascript
/**
 * Utility functions for routine display and formatting
 */

const ACTION_TYPE_LABELS = {
  gpio: {
    attract_on: 'Attract On',
    attract_off: 'Attract Off',
    flash_on: 'Flash On',
    flash_off: 'Flash Off',
  },
  camera: {
    takephoto: 'Take Photo',
  },
  gps: {
    sync: 'GPS Sync',
  },
  service: {
    start: 'Start Service',
    stop: 'Stop Service',
  },
}

/**
 * Summarize actions into a short display string
 *
 * @param {Array} actions - Array of action objects
 * @returns {string} Summary like "Attract On + Take Photo" or "3 actions"
 */
export function summarizeActions(actions) {
  if (!actions?.length) return 'No actions'

  if (actions.length === 1) {
    return getActionLabel(actions[0])
  }

  if (actions.length === 2) {
    return actions.map(getActionLabel).join(' + ')
  }

  return `${getActionLabel(actions[0])} + ${actions.length - 1} more`
}

function getActionLabel(action) {
  const typeLabels = ACTION_TYPE_LABELS[action.action_type]
  if (typeLabels && typeLabels[action.action_name]) {
    return typeLabels[action.action_name]
  }
  return action.action_name
    ?.replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase()) || 'Unknown'
}

/**
 * Describe a trigger in human-readable form
 *
 * @param {Object} trigger - Trigger object
 * @returns {string} Description like "at Dusk" or "every 15 min"
 */
export function describeTrigger(trigger) {
  if (!trigger) return ''

  switch (trigger.trigger_type) {
    case 'interval':
      return `every ${trigger.interval_minutes} min`

    case 'solar':
      return `at ${capitalize(trigger.solar_event)}`

    case 'fixed_time':
      return `at ${trigger.time}`

    case 'moon_phase': {
      const phases = trigger.phases || []
      if (phases.length === 1) {
        return `on ${capitalize(phases[0])} moon`
      }
      return `on ${phases.length} moon phases`
    }

    case 'recurring_days':
      if (trigger.every_n_days === 1) {
        return `daily at ${trigger.time}`
      }
      return `every ${trigger.every_n_days} days`

    case 'cron':
      return 'cron schedule'

    default:
      return trigger.trigger_type || ''
  }
}

/**
 * Generate auto-name for a routine based on its actions and trigger
 *
 * @param {Object} routine - Routine object
 * @returns {string} Auto-generated name like "Attract On at Dusk"
 */
export function generateRoutineName(routine) {
  const actionSummary = summarizeActions(routine.actions)
  const triggerDesc = describeTrigger(routine.trigger)
  return `${actionSummary} ${triggerDesc}`.trim()
}

function capitalize(str) {
  if (!str) return ''
  return str.charAt(0).toUpperCase() + str.slice(1)
}
```

### Note on generateUUID

`generateUUID` already exists at `utils/uuid.js` - no changes needed. Import as:

```javascript
import { generateUUID } from '../../../utils/uuid'
```

---

## Component Implementations

### RoutineEditor

The RoutineEditor is a fully controlled component with no local state:

```jsx
function RoutineEditor({ routine, onChange, disabled }) {
  const handleTriggerChange = (trigger) => {
    onChange({ ...routine, trigger })
  }

  const handlePreConditionChange = (preCondition) => {
    onChange({ ...routine, pre_condition: preCondition })
  }

  const handleActionsChange = (actions) => {
    onChange({ ...routine, actions })
  }

  return (
    <div className="space-y-4">
      <TriggerSelector
        trigger={routine.trigger}
        onChange={handleTriggerChange}
        disabled={disabled}
      />

      <PreConditionForm
        preCondition={routine.pre_condition}
        onChange={handlePreConditionChange}
        disabled={disabled}
      />

      <ActionList
        actions={routine.actions}
        onActionsChange={handleActionsChange}
        disabled={disabled}
      />

      <OffsetTimeline actions={routine.actions} />
    </div>
  )
}
```

#### TDD Reference
Rename test file: `PatternEditor.test.jsx` → `RoutineEditor.test.jsx`. See [Testing → Frontend Tests](./SCHEDULER_TERMINOLOGY_REFACTOR_TESTING.md).

### TriggerSelector

```jsx
function TriggerSelector({ trigger, onChange, disabled, error }) {
  const triggerType = trigger?.trigger_type || 'interval'

  const handleTypeChange = (e) => {
    const newType = e.target.value
    onChange(createDefaultTrigger(newType))
  }

  return (
    <div className="space-y-3">
      <div>
        <label
          htmlFor="trigger-type"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
        >
          When to run
        </label>
        <select
          id="trigger-type"
          value={triggerType}
          onChange={handleTypeChange}
          disabled={disabled}
          className={`
            w-full rounded-md border px-3 py-2 text-sm
            focus:ring-2 focus:ring-blue-500 focus:border-transparent
            disabled:opacity-50 disabled:cursor-not-allowed
            ${error
              ? 'border-red-300 dark:border-red-600 bg-red-50 dark:bg-red-900/20'
              : 'border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800'
            }
          `}
          aria-invalid={!!error}
          aria-describedby={error ? 'trigger-error' : undefined}
          data-testid="trigger-type"
        >
          <option value="interval">Every N minutes</option>
          <option value="fixed_time">Fixed time</option>
          <option value="solar">Solar event</option>
          <option value="moon_phase">Moon phase</option>
          <option value="recurring_days">Every N days</option>
          <option value="cron">Cron (expert)</option>
        </select>
        {error && (
          <p id="trigger-error" className="mt-1 text-sm text-red-600 dark:text-red-400">
            {error}
          </p>
        )}
      </div>

      {triggerType === 'interval' && <IntervalTriggerForm trigger={trigger} onChange={onChange} disabled={disabled} />}
      {triggerType === 'fixed_time' && <FixedTimeTriggerForm trigger={trigger} onChange={onChange} disabled={disabled} />}
      {triggerType === 'solar' && <SolarTriggerForm trigger={trigger} onChange={onChange} disabled={disabled} />}
      {triggerType === 'moon_phase' && <MoonPhaseTriggerForm trigger={trigger} onChange={onChange} disabled={disabled} />}
      {triggerType === 'recurring_days' && <RecurringDaysTriggerForm trigger={trigger} onChange={onChange} disabled={disabled} />}
      {triggerType === 'cron' && <CronTriggerForm trigger={trigger} onChange={onChange} disabled={disabled} />}
    </div>
  )
}

function createDefaultTrigger(type) {
  switch (type) {
    case 'interval':
      return { trigger_type: 'interval', interval_minutes: 15, time_window: null }
    case 'fixed_time':
      return { trigger_type: 'fixed_time', time: '09:00', days_of_week: null }
    case 'solar':
      return { trigger_type: 'solar', solar_event: 'dusk', offset_minutes: 0 }
    case 'moon_phase':
      return { trigger_type: 'moon_phase', phases: ['full'], time_window: null }
    case 'recurring_days':
      return { trigger_type: 'recurring_days', every_n_days: 1, time: '00:00', start_date: null }
    case 'cron':
      return { trigger_type: 'cron', cron_expression: '0 * * * *' }
    default:
      return { trigger_type: 'interval', interval_minutes: 15 }
  }
}
```

#### TDD Reference
New component - create `TriggerSelector.test.jsx`. Run: `npm test -- TriggerSelector --run`

### RecurringDaysTriggerForm

```jsx
function RecurringDaysTriggerForm({ trigger, onChange, disabled }) {
  const handleEveryNDaysChange = (e) => {
    const value = parseInt(e.target.value, 10)
    if (value >= 1 && value <= 365) {
      onChange({ ...trigger, every_n_days: value })
    }
  }

  const handleTimeChange = (e) => {
    onChange({ ...trigger, time: e.target.value })
  }

  const handleStartDateChange = (e) => {
    onChange({ ...trigger, start_date: e.target.value || null })
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <label htmlFor="every-n-days" className="text-sm text-gray-700 dark:text-gray-300">
          Run every
        </label>
        <input
          id="every-n-days"
          type="number"
          min="1"
          max="365"
          value={trigger?.every_n_days || 1}
          onChange={handleEveryNDaysChange}
          disabled={disabled}
          className="w-20 rounded-md border border-gray-300 dark:border-gray-600 px-2 py-1 text-sm"
          data-testid="every-n-days"
        />
        <span className="text-sm text-gray-700 dark:text-gray-300">days</span>
      </div>

      <div className="flex items-center gap-2">
        <label htmlFor="time" className="text-sm text-gray-700 dark:text-gray-300">at</label>
        <input
          id="time"
          type="time"
          value={trigger?.time || "00:00"}
          onChange={handleTimeChange}
          disabled={disabled}
          className="rounded-md border border-gray-300 dark:border-gray-600 px-2 py-1 text-sm"
          data-testid="trigger-time"
        />
      </div>

      <div>
        <label htmlFor="start-date" className="block text-sm text-gray-700 dark:text-gray-300 mb-1">
          Starting from (optional)
        </label>
        <input
          id="start-date"
          type="date"
          value={trigger?.start_date?.split("T")[0] || ""}
          onChange={handleStartDateChange}
          disabled={disabled}
          className="rounded-md border border-gray-300 dark:border-gray-600 px-2 py-1 text-sm"
          data-testid="start-date"
        />
        <p className="mt-1 text-xs text-gray-500">If not set, starts from today</p>
      </div>
    </div>
  )
}
```

#### TDD Reference
New component - create `RecurringDaysTriggerForm.test.jsx`. Run: `npm test -- RecurringDaysTriggerForm --run`

### PreConditionForm

```jsx
function PreConditionForm({ preCondition, onChange, disabled }) {
  const [enabled, setEnabled] = useState(!!preCondition)

  const handleToggle = (e) => {
    setEnabled(e.target.checked)
    if (!e.target.checked) {
      onChange(null)
    } else {
      onChange({
        trigger_type: "sensor",
        sensor_type: "light",
        condition: "below",
        threshold: 100,
      })
    }
  }

  if (!enabled) {
    return (
      <div>
        <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 cursor-pointer">
          <input
            type="checkbox"
            checked={false}
            onChange={handleToggle}
            disabled={disabled}
            className="rounded border-gray-300"
          />
          Add sensor pre-condition
        </label>
      </div>
    )
  }

  return (
    <div className="space-y-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
      <label className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300 cursor-pointer">
        <input
          type="checkbox"
          checked={true}
          onChange={handleToggle}
          disabled={disabled}
          className="rounded border-gray-300"
        />
        Sensor pre-condition
      </label>

      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-sm text-gray-600 dark:text-gray-400">Only run when</span>
        <select
          value={preCondition?.sensor_type || "light"}
          onChange={(e) => onChange({ ...preCondition, sensor_type: e.target.value })}
          disabled={disabled}
          className="rounded-md border border-gray-300 dark:border-gray-600 px-2 py-1 text-sm"
        >
          <option value="light">Light level</option>
          <option value="temperature">Temperature</option>
          <option value="humidity">Humidity</option>
        </select>

        <select
          value={preCondition?.condition || "below"}
          onChange={(e) => onChange({ ...preCondition, condition: e.target.value })}
          disabled={disabled}
          className="rounded-md border border-gray-300 dark:border-gray-600 px-2 py-1 text-sm"
        >
          <option value="below">is below</option>
          <option value="above">is above</option>
        </select>

        <input
          type="number"
          value={preCondition?.threshold || 0}
          onChange={(e) => onChange({ ...preCondition, threshold: parseFloat(e.target.value) })}
          disabled={disabled}
          className="w-20 rounded-md border border-gray-300 dark:border-gray-600 px-2 py-1 text-sm"
        />
      </div>

      <p className="text-xs text-gray-500">
        Actions will be skipped if condition is not met at execution time.
      </p>
    </div>
  )
}
```

### TriggerBadge

```jsx
const BADGE_COLORS = {
  interval: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  solar: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  fixed_time: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  moon_phase: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  recurring_days: 'bg-teal-100 text-teal-800 dark:bg-teal-900 dark:text-teal-200',
  cron: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200',
}

const TRIGGER_LABELS = {
  interval: 'Interval',
  solar: 'Solar',
  fixed_time: 'Fixed',
  moon_phase: 'Moon',
  recurring_days: 'Days',
  cron: 'Cron',
}

function TriggerBadge({ trigger }) {
  const triggerType = trigger?.trigger_type || 'unknown'
  const colorClasses = BADGE_COLORS[triggerType] || BADGE_COLORS.cron
  const label = TRIGGER_LABELS[triggerType] || triggerType

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full ${colorClasses}`}
      data-testid="trigger-badge"
    >
      {label}
    </span>
  )
}
```

### RoutineCard

```jsx
import { generateRoutineName } from '../../../utils/routineUtils'

function RoutineCard({ routine, onChange, onDelete, disabled }) {
  const [expanded, setExpanded] = useState(false)

  const displayName = routine.name || routine.display_name || generateRoutineName(routine)

  return (
    <div
      className={`
        border rounded-lg transition-all duration-200
        ${expanded
          ? 'border-blue-300 dark:border-blue-600 shadow-md'
          : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
        }
      `}
      data-testid="routine-card"
    >
      <div
        className="flex items-center justify-between p-3 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <span className="font-medium text-gray-900 dark:text-white" data-testid="routine-name">
          {displayName}
        </span>
        <div className="flex items-center gap-2">
          <TriggerBadge trigger={routine.trigger} />
          <ChevronIcon direction={expanded ? 'up' : 'down'} />
          <button
            onClick={(e) => { e.stopPropagation(); onDelete(routine.routine_id); }}
            disabled={disabled}
            className="p-1 text-gray-400 hover:text-red-500 disabled:opacity-50"
            aria-label="Delete routine"
          >
            ×
          </button>
        </div>
      </div>

      {expanded && (
        <div className="p-4 border-t border-gray-200 dark:border-gray-700">
          <RoutineEditor
            routine={routine}
            onChange={onChange}
            disabled={disabled}
          />
        </div>
      )}
    </div>
  )
}
```

### NewRoutineCard

```jsx
import { generateUUID } from '../../../utils/uuid'

function NewRoutineCard({ onComplete, onCancel }) {
  const [draft, setDraft] = useState({
    routine_id: generateUUID(),
    name: null,
    trigger: { trigger_type: 'interval', interval_minutes: 15 },
    pre_condition: null,
    actions: [],
  })

  const handleComplete = () => {
    if (draft.actions.length === 0) return
    onComplete(draft)
  }

  return (
    <div
      className="border-2 border-blue-300 dark:border-blue-600 rounded-lg overflow-hidden"
      data-testid="new-routine-card"
    >
      <div className="flex items-center justify-between p-3 bg-blue-50 dark:bg-blue-900/20">
        <span className="font-medium text-blue-900 dark:text-blue-100">New Routine</span>
        <button
          onClick={onCancel}
          className="p-1 text-blue-600 hover:text-blue-800"
          aria-label="Cancel"
        >
          ×
        </button>
      </div>

      <div className="p-4">
        <RoutineEditor routine={draft} onChange={setDraft} />

        <div className="flex justify-end gap-2 mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={onCancel}
            className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-800"
          >
            Cancel
          </button>
          <button
            onClick={handleComplete}
            disabled={draft.actions.length === 0}
            className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            data-testid="save-routine"
          >
            Add Routine
          </button>
        </div>
      </div>
    </div>
  )
}
```

---

## Component States

### RoutineCard States

```jsx
function RoutineCard({ routine, onChange, onDelete, isLoading, error, disabled }) {
  const [expanded, setExpanded] = useState(false)

  // Loading state
  if (isLoading) {
    return (
      <div
        className="border border-gray-200 dark:border-gray-700 rounded-lg p-3 animate-pulse"
        data-testid="routine-card-loading"
      >
        <div className="flex items-center gap-3">
          <div className="h-4 w-32 bg-gray-200 dark:bg-gray-700 rounded" />
          <div className="h-5 w-16 bg-gray-200 dark:bg-gray-700 rounded-full" />
        </div>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div
        className="border border-red-300 dark:border-red-700 bg-red-50 dark:bg-red-900/20 rounded-lg p-3"
        data-testid="routine-card-error"
      >
        <div className="flex items-center gap-2 text-red-600 dark:text-red-400">
          <ExclamationIcon className="w-4 h-4" />
          <span className="text-sm">Failed to load routine</span>
          <button
            onClick={() => onChange(routine)}
            className="ml-auto text-xs underline hover:no-underline"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  // Normal render
  return (
    <div className={/* ... */}>
      {/* ... */}
    </div>
  )
}
```

### RoutineList States

```jsx
function RoutineList({
  routines,
  isLoading,
  error,
  onRetry,
  onRoutineChange,
  onRoutineDelete,
  isAddingRoutine,
  onStartAddRoutine,
  onCancelAddRoutine,
  onRoutineAdd,
  disabled,
}) {
  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-3" data-testid="routine-list-loading">
        {[1, 2, 3].map(i => (
          <div key={i} className="border border-gray-200 dark:border-gray-700 rounded-lg p-3 animate-pulse">
            <div className="flex items-center gap-3">
              <div className="h-4 w-32 bg-gray-200 dark:bg-gray-700 rounded" />
              <div className="h-5 w-16 bg-gray-200 dark:bg-gray-700 rounded-full" />
            </div>
          </div>
        ))}
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div
        className="border border-red-300 dark:border-red-700 bg-red-50 dark:bg-red-900/20 rounded-lg p-4 text-center"
        data-testid="routine-list-error"
      >
        <ExclamationIcon className="w-8 h-8 mx-auto text-red-500 mb-2" />
        <p className="text-sm text-red-600 dark:text-red-400 mb-3">
          {error.message || 'Failed to load routines'}
        </p>
        <button
          onClick={onRetry}
          className="px-3 py-1.5 text-sm bg-red-600 text-white rounded hover:bg-red-700"
        >
          Try Again
        </button>
      </div>
    )
  }

  // Empty state
  if (!routines?.length && !isAddingRoutine) {
    return (
      <div className="space-y-4">
        <div
          className="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-8 text-center"
          data-testid="routine-list-empty"
        >
          <ClockIcon className="w-12 h-12 mx-auto text-gray-400 mb-3" />
          <p className="text-gray-600 dark:text-gray-400 mb-1">No routines yet</p>
          <p className="text-sm text-gray-500">
            Add a routine to define what actions run and when
          </p>
        </div>
        <button
          onClick={onStartAddRoutine}
          disabled={disabled}
          className="w-full py-2 border-2 border-dashed border-gray-300 rounded-lg text-gray-600 hover:border-blue-400 hover:text-blue-600 disabled:opacity-50"
        >
          + Add Routine
        </button>
      </div>
    )
  }

  // Normal render
  return (
    <div className="space-y-3" data-testid="routine-list">
      {routines.map(routine => (
        <RoutineCard
          key={routine.routine_id}
          routine={routine}
          onChange={onRoutineChange}
          onDelete={onRoutineDelete}
          disabled={disabled}
        />
      ))}

      {isAddingRoutine ? (
        <NewRoutineCard onComplete={onRoutineAdd} onCancel={onCancelAddRoutine} />
      ) : (
        <button
          onClick={onStartAddRoutine}
          disabled={disabled}
          className="w-full py-2 border-2 border-dashed border-gray-300 rounded-lg text-gray-600 hover:border-blue-400 hover:text-blue-600 disabled:opacity-50"
        >
          + Add Routine
        </button>
      )}
    </div>
  )
}
```

### DayTimeline Empty State

```jsx
function DayTimeline({ date, executions, conflicts, onExecutionClick }) {
  const hours = Array.from({ length: 24 }, (_, i) => i)

  // Empty state
  if (!executions?.length) {
    return (
      <div
        className="flex flex-col items-center justify-center py-12 text-center"
        data-testid="day-timeline-empty"
      >
        <CalendarIcon className="w-12 h-12 text-gray-400 mb-3" />
        <p className="text-gray-600 dark:text-gray-400">
          No scheduled executions on this day
        </p>
      </div>
    )
  }

  // Normal render
  return (
    <div className="flex flex-col divide-y divide-gray-200 dark:divide-gray-700" data-testid="day-timeline">
      {/* ... hours ... */}
    </div>
  )
}
```

### ActivationProgress States

```jsx
function ActivationProgress({ scheduleId, onComplete, onError }) {
  const [progress, setProgress] = useState({ phase: 'starting', progress: 0 })
  const [error, setError] = useState(null)

  useEffect(() => {
    const handleProgress = (data) => {
      if (data.schedule_id === scheduleId) {
        setProgress(data)

        if (data.phase === 'complete') {
          setTimeout(() => onComplete?.(), 500)
        }

        if (data.phase === 'error') {
          setError(data.error || 'Activation failed')
          onError?.(data.error)
        }
      }
    }

    socket.on('schedule:activation_progress', handleProgress)
    return () => socket.off('schedule:activation_progress', handleProgress)
  }, [scheduleId, onComplete, onError])

  // Error state
  if (error) {
    return (
      <div
        className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4"
        data-testid="activation-error"
      >
        <div className="flex items-center gap-2 text-red-600 dark:text-red-400">
          <ExclamationIcon className="w-5 h-5" />
          <span className="font-medium">Activation failed</span>
        </div>
        <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error}</p>
      </div>
    )
  }

  // Progress state
  return (
    <div className="space-y-2" data-testid="activation-progress">
      <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div
          className="h-full bg-blue-600 transition-all duration-300"
          style={{ width: `${progress.progress}%` }}
        />
      </div>
      <p className="text-sm text-gray-600 dark:text-gray-400">
        {PHASE_LABELS[progress.phase] || progress.phase}
      </p>
    </div>
  )
}

const PHASE_LABELS = {
  starting: 'Starting...',
  calculating_solar: 'Calculating solar events...',
  calculating_moon: 'Calculating moon phases...',
  calculating_intervals: 'Calculating intervals...',
  writing_crontab: 'Writing schedule...',
  complete: 'Done!',
  error: 'Failed',
}
```

---

## State Management

### Component Hierarchy & Data Flow

```
ScheduleEditor (owns schedule state)
│
├── Schedule metadata (name, description)
│
├── RoutineList (receives routines + handlers)
│   │
│   ├── RoutineCard (receives single routine + handlers)
│   │   │
│   │   └── RoutineEditor (receives routine + onChange)
│   │       ├── TriggerSelector
│   │       ├── PreConditionForm
│   │       └── ActionList
│   │
│   └── NewRoutineCard (receives onComplete + onCancel)
│
└── ActivationProgress (receives scheduleId)
```

### State Ownership

| Component | Owns State | Receives Props |
|-----------|------------|----------------|
| `ScheduleEditor` | `schedule`, `routines`, `isAddingRoutine`, `isSaving` | `initialSchedule`, `onSave`, `onCancel` |
| `RoutineList` | (none) | `routines`, `onRoutineChange`, `onRoutineDelete`, `onRoutineAdd` |
| `RoutineCard` | `expanded` | `routine`, `onChange`, `onDelete` |
| `RoutineEditor` | (none) | `routine`, `onChange` |
| `NewRoutineCard` | `draft` | `onComplete`, `onCancel` |

### ScheduleEditor Implementation

```jsx
function ScheduleEditor({ isOpen, initialSchedule, onSave, onCancel }) {
  // Schedule metadata
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')

  // Routines array - ScheduleEditor owns this
  const [routines, setRoutines] = useState([])

  // UI state
  const [isAddingRoutine, setIsAddingRoutine] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [errors, setErrors] = useState({})

  // Initialize from prop
  useEffect(() => {
    if (initialSchedule) {
      setName(initialSchedule.name || '')
      setDescription(initialSchedule.description || '')
      setRoutines(initialSchedule.routines || [])
    } else {
      setName('')
      setDescription('')
      setRoutines([])
    }
  }, [initialSchedule])

  // Handler passed to RoutineList → RoutineCard → RoutineEditor
  const handleRoutineChange = useCallback((updatedRoutine) => {
    setRoutines(prev =>
      prev.map(r =>
        r.routine_id === updatedRoutine.routine_id ? updatedRoutine : r
      )
    )
  }, [])

  // Handler passed to RoutineList → RoutineCard
  const handleRoutineDelete = useCallback((routineId) => {
    setRoutines(prev => prev.filter(r => r.routine_id !== routineId))
  }, [])

  // Handler passed to NewRoutineCard
  const handleRoutineAdd = useCallback((newRoutine) => {
    setRoutines(prev => [...prev, newRoutine])
    setIsAddingRoutine(false)
  }, [])

  // Save handler - assembles final schedule
  const handleSave = useCallback(async () => {
    if (!validate()) return

    setIsSaving(true)
    try {
      await onSave({
        schedule_id: initialSchedule?.schedule_id || generateUUID(),
        name: name.trim(),
        description: description.trim(),
        routines,
      })
    } catch (error) {
      setErrors({ save: error.message })
    } finally {
      setIsSaving(false)
    }
  }, [name, description, routines, initialSchedule, onSave])

  return (
    <div>
      {/* Name/Description inputs */}

      <RoutineList
        routines={routines}
        onRoutineChange={handleRoutineChange}
        onRoutineDelete={handleRoutineDelete}
        isAddingRoutine={isAddingRoutine}
        onStartAddRoutine={() => setIsAddingRoutine(true)}
        onCancelAddRoutine={() => setIsAddingRoutine(false)}
        onRoutineAdd={handleRoutineAdd}
        disabled={isSaving}
      />

      {/* Save/Cancel buttons */}
    </div>
  )
}
```

### Key Patterns

| Pattern | Implementation |
|---------|----------------|
| **Lift state up** | `ScheduleEditor` owns `routines[]`, passes handlers down |
| **Controlled components** | `RoutineEditor` has no local state, calls `onChange` immediately |
| **Local UI state** | `RoutineCard.expanded`, `NewRoutineCard.draft` - not shared |
| **Immutable updates** | Always create new objects: `{ ...routine, trigger }` |
| **Callback identity** | Use `useCallback` for handlers passed as props |

---

## Styles

This project uses Tailwind CSS with minimal custom classes. New components should follow this pattern:

1. **Prefer inline Tailwind classes** for component styling
2. **Add to `@layer components`** only for reusable patterns

### Classes Referenced (Implementation Approach)

| Class Referenced | Recommendation |
|------------------|----------------|
| `.routine-card` | Use inline Tailwind (no custom class needed) |
| `.routine-card.collapsed` | Use inline Tailwind with conditional classes |
| `.routine-card.expanded` | Use inline Tailwind with conditional classes |
| `.trigger-badge` | Use inline Tailwind with color mapping |
| `.day-timeline` | Use inline Tailwind (no custom class needed) |
| `.activation-progress` | Use inline Tailwind (no custom class needed) |

### TriggerBadge Color Mapping

```jsx
const BADGE_COLORS = {
  interval: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  solar: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  fixed_time: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  moon_phase: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  recurring_days: 'bg-teal-100 text-teal-800 dark:bg-teal-900 dark:text-teal-200',
  cron: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200',
}
```

### RoutineCard Styling Example

```jsx
<div
  className={`
    border rounded-lg transition-all duration-200
    ${expanded
      ? 'border-blue-300 dark:border-blue-600 shadow-md'
      : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
    }
  `}
>
  {/* Header */}
  <div
    className="flex items-center justify-between p-3 cursor-pointer"
    onClick={toggleExpand}
  >
    ...
  </div>

  {/* Body - conditionally rendered */}
  {expanded && (
    <div className="p-4 border-t border-gray-200 dark:border-gray-700">
      ...
    </div>
  )}
</div>
```

### DayTimeline Styling Example

```jsx
<div className="flex flex-col divide-y divide-gray-200 dark:divide-gray-700">
  {hours.map(hour => (
    <div key={hour} className="flex items-stretch min-h-[3rem]">
      <span className="w-16 flex-shrink-0 py-2 text-xs text-gray-500 dark:text-gray-400">
        {hour.toString().padStart(2, '0')}:00
      </span>
      <div className="flex-1 relative py-1">
        {/* Execution markers positioned absolutely */}
      </div>
    </div>
  ))}
</div>
```

---

## Responsive Design Reference

### Existing Breakpoint Patterns

The codebase uses standard Tailwind breakpoints:

| Breakpoint | Min Width | Usage |
|------------|-----------|-------|
| `sm:` | 640px | Small tablets |
| `md:` | 768px | Tablets |
| `lg:` | 1024px | Desktops |
| `xl:` | 1280px | Large desktops |

**Grid patterns used in codebase:**
```jsx
// Gallery-style responsive grid
className="grid-cols-1 md:grid-cols-3"
className="grid-cols-2 sm:grid-cols-3 md:grid-cols-3 lg:grid-cols-4"

// Responsive flex direction
className="flex-col md:flex-row"

// Responsive visibility
className="md:hidden"        // Hide on tablet+
className="hidden md:block"  // Show only on tablet+

// Responsive padding
className="px-4 sm:px-6 lg:px-8"
```

### Touch Target Conventions

Per accessibility guidelines, all interactive elements must have minimum 44×44px touch targets:

```jsx
// Existing pattern from PhotoLightbox
className="min-h-[44px] min-w-[44px]"

// Button padding for touch targets
className="p-3"  // 12px padding = ~44px with content
```

### New Mobile Patterns from Mockups

The mobile mockups introduce these patterns **not currently in the codebase**:

**1. Slide-up Bottom Sheet:**
```jsx
// Bottom sheet container (for mobile routine editing)
<div className="fixed inset-x-0 bottom-0 bg-white dark:bg-gray-900 rounded-t-2xl shadow-xl transform transition-transform">
  {/* Handle indicator */}
  <div className="flex justify-center py-2">
    <div className="w-10 h-1 bg-gray-300 dark:bg-gray-700 rounded-full" />
  </div>
  {/* Content */}
</div>
```

**2. Collapsible Routine Cards:**
```jsx
// Collapsed by default on mobile, expanded on desktop
const [expanded, setExpanded] = useState(false)

<div className={`
  transition-all duration-200
  ${expanded ? 'max-h-[500px]' : 'max-h-[60px] overflow-hidden'}
`}>
```

**3. Tab Navigation for Mobile:**
```jsx
// List/Timeline toggle on mobile
<div className="flex border-b border-gray-200 dark:border-gray-700 md:hidden">
  <button className={activeTab === 'list' ? 'border-b-2 border-blue-500' : ''}>
    List
  </button>
  <button className={activeTab === 'timeline' ? 'border-b-2 border-blue-500' : ''}>
    Timeline
  </button>
</div>
```

**4. Compact Mobile Timeline:**
```jsx
// Narrower hour labels on mobile
<span className="w-10 md:w-12 lg:w-16 text-xs">
  {hour.toString().padStart(2, '0')}:00
</span>
```

### Scheduler-Specific Responsive Patterns

| Screen Size | Layout | Behavior |
|-------------|--------|----------|
| Mobile (<640px) | Single column, bottom sheet editor | Slide-up for editing, tabs for view switching |
| Tablet (640-1024px) | 2 columns, overlay modal | Modal editor, sidebar for list |
| Desktop (>1024px) | 3 columns, inline editing | All panels visible, expand/collapse cards |

**Reference mockups for exact styling:**
- `unified-scheduler-mobile-mockup.html` - Mobile slide-up patterns
- `unified-scheduler-mockup.html` - Desktop layout

---

## CalendarView Enhancements

The existing `CalendarView` component will be enhanced rather than replaced.

### Changes to CalendarView

1. **Default to day view** - Change initial `viewMode` from `'month'` to `'day'`
2. **Auto-navigate to next active day** - On load, find first day with executions
3. **Day view uses DayTimeline** - Replace list view with hourly timeline
4. **Conflict highlighting** - Add conflict props to `ExecutionMarker`

### Component Hierarchy

```
ScheduleEditor
├── RoutineList
│   └── RoutineCard (collapsed/expanded)
│       └── RoutineEditor
│           ├── TriggerSelector
│           ├── ActionList
│           └── OffsetTimeline  ← Keep (routine-level)
│
└── SchedulePreview
    └── CalendarView
        ├── Day view → DayTimeline  ← Default, primary
        └── Month/Week view (dots)  ← Zoom out for overview
```

#### TDD Reference
New component - create `RoutineCard.test.jsx`. Run: `npm test -- RoutineCard --run`

### DayTimeline Component

**Reference implementations:**
- `OffsetTimeline.jsx` - Existing timeline component for marker/tooltip patterns
- `day-timeline-conflicts-mockup.html` - Visual design and conflict highlighting

**Props interface:**
```typescript
interface DayTimelineProps {
  date: Date;                    // The day being displayed
  executions: Execution[];       // All executions for this day
  conflicts: Conflict[];         // Time collisions and GPIO warnings
  onExecutionClick: (exec: Execution) => void;  // Navigate to routine
}

interface Execution {
  id: string;
  routine_id: string;
  routine_name: string;
  start_time: string;            // ISO datetime
  action_type: string;
  action_name: string;
}

interface Conflict {
  executionId: string;
  type: 'time' | 'gpio';         // time=red, gpio=yellow
  message: string;
}
```

**Implementation:**

```jsx
function DayTimeline({ date, executions, conflicts, onExecutionClick }) {
  const hours = Array.from({ length: 24 }, (_, i) => i)

  const executionsByHour = useMemo(() => {
    const grouped = {}
    executions.forEach(exec => {
      const hour = new Date(exec.start_time).getHours()
      if (!grouped[hour]) grouped[hour] = []
      grouped[hour].push(exec)
    })
    return grouped
  }, [executions])

  if (!executions?.length) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center" data-testid="day-timeline-empty">
        <CalendarIcon className="w-12 h-12 text-gray-400 mb-3" />
        <p className="text-gray-600 dark:text-gray-400">No scheduled executions on this day</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col divide-y divide-gray-200 dark:divide-gray-700" data-testid="day-timeline">
      {hours.map(hour => (
        <div key={hour} className="flex items-stretch min-h-[3rem]">
          <span className="w-16 flex-shrink-0 py-2 text-xs text-gray-500 dark:text-gray-400">
            {hour.toString().padStart(2, '0')}:00
          </span>
          <div className="flex-1 relative py-1">
            {(executionsByHour[hour] || []).map(exec => {
              const minute = new Date(exec.start_time).getMinutes()
              const conflict = conflicts?.find(c => c.executionId === exec.id)

              return (
                <ExecutionMarker
                  key={exec.id}
                  execution={exec}
                  conflict={conflict}
                  style={{ left: `${(minute / 60) * 100}%` }}
                  onClick={() => onExecutionClick(exec)}
                />
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
}
```

### ExecutionMarker Conflict Props

```jsx
function ExecutionMarker({ execution, conflict, style, onClick }) {
  const conflictClass = conflict?.type === 'time'
    ? 'ring-2 ring-red-500 dark:ring-red-400'
    : conflict?.type === 'gpio'
    ? 'ring-2 ring-yellow-500 dark:ring-yellow-400'
    : ''

  return (
    <button
      className={`execution-marker ${conflictClass}`}
      style={style}
      onClick={() => onClick(execution)}
      data-testid="execution-marker"
    >
      {/* existing content */}
    </button>
  )
}
```

### CalendarView.jsx Updates

```jsx
// Change default viewMode from 'month' to 'day'
const [viewMode, setViewMode] = useState(() => {
  const stored = localStorage.getItem(VIEW_MODE_STORAGE_KEY)
  return VALID_VIEW_MODES.includes(stored) ? stored : 'day'
})

// In CalendarGrid, render DayTimeline for day view
{viewMode === 'day' && (
  <DayTimeline
    date={currentDate}
    executions={executionsForDay}
    conflicts={conflictsForDay}
    onExecutionClick={onExecutionClick}
  />
)}
```

#### TDD Reference
New component - create `DayTimeline.test.jsx`. Update `CalendarCell.test.jsx` per [Testing doc](./SCHEDULER_TERMINOLOGY_REFACTOR_TESTING.md).

---

## Activation Progress UI

Schedule activation (5-year pre-computation) can take several seconds.

### ActivationProgress Component

**Reference implementations:**
- `ExportJobProgress.jsx` - Existing progress component for state machine and styling patterns
- `activation-progress-mockup.html` - Visual design for activation-specific states

**Props interface:**
```typescript
interface ActivationProgressProps {
  scheduleId: string;            // Schedule being activated
  onComplete: () => void;        // Called when activation succeeds
  onError: (error: string) => void;  // Called on failure
}

// WebSocket event payload
interface ProgressEvent {
  schedule_id: string;
  phase: 'starting' | 'calculating_solar' | 'calculating_moon' |
         'calculating_intervals' | 'writing_crontab' | 'complete' | 'error';
  progress: number;              // 0-100
  error?: string;                // Present when phase === 'error'
}
```

**State machine:**
- `inactive` → User clicks "Activate" → `activating`
- `activating` → WebSocket progress events → Update progress bar
- `activating` → `phase: 'complete'` → `active` (success)
- `activating` → `phase: 'error'` → `failed` (show retry)

**Implementation:**

```jsx
import { useEffect, useState } from 'react'
import { socket } from '../utils/socket'

const PHASE_LABELS = {
  starting: 'Starting...',
  calculating_solar: 'Calculating solar events...',
  calculating_moon: 'Calculating moon phases...',
  calculating_intervals: 'Calculating intervals...',
  writing_crontab: 'Writing schedule...',
  complete: 'Done!',
  error: 'Failed',
}

function ActivationProgress({ scheduleId, onComplete, onError }) {
  const [progress, setProgress] = useState({ phase: 'starting', progress: 0 })
  const [error, setError] = useState(null)

  useEffect(() => {
    const handleProgress = (data) => {
      if (data.schedule_id === scheduleId) {
        setProgress(data)

        if (data.phase === 'complete') {
          setTimeout(() => onComplete?.(), 500)
        }

        if (data.phase === 'error') {
          setError(data.error || 'Activation failed')
          onError?.(data.error)
        }
      }
    }

    socket.on('schedule:activation_progress', handleProgress)
    return () => socket.off('schedule:activation_progress', handleProgress)
  }, [scheduleId, onComplete, onError])

  if (error) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4" data-testid="activation-error">
        <div className="flex items-center gap-2 text-red-600 dark:text-red-400">
          <ExclamationIcon className="w-5 h-5" />
          <span className="font-medium">Activation failed</span>
        </div>
        <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error}</p>
      </div>
    )
  }

  return (
    <div className="space-y-2" data-testid="activation-progress">
      <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div
          className="h-full bg-blue-600 transition-all duration-300"
          style={{ width: `${progress.progress}%` }}
        />
      </div>
      <p className="text-sm text-gray-600 dark:text-gray-400">
        {PHASE_LABELS[progress.phase] || progress.phase}
      </p>
    </div>
  )
}
```

### Usage in ScheduleEditor

```jsx
function ScheduleEditor({ schedule }) {
  const [isActivating, setIsActivating] = useState(false)

  const handleActivate = async () => {
    setIsActivating(true)
    await activateSchedule(schedule.schedule_id)
  }

  return (
    <div>
      {/* ... schedule editing UI ... */}

      <button
        onClick={handleActivate}
        disabled={isActivating}
        data-testid="activate-schedule"
      >
        {isActivating ? 'Activating...' : 'Activate Schedule'}
      </button>

      {isActivating && (
        <ActivationProgress
          scheduleId={schedule.schedule_id}
          onComplete={() => setIsActivating(false)}
        />
      )}
    </div>
  )
}
```

#### TDD Reference
New component - create `ActivationProgress.test.jsx`. Mock WebSocket events for testing.

---

## API Utilities Updates

**File**: `webui/frontend/src/utils/schedulerApi.js`

```javascript
export async function createSchedule(schedule) {
  const response = await fetch('/api/scheduler/ui/schedules', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrfToken(),
    },
    body: JSON.stringify({
      ...schedule,
      routines: schedule.routines,
    }),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.error || 'Failed to create schedule')
  }

  return response.json()
}

export async function fetchSchedulePreview(scheduleId, hours = 24) {
  const response = await fetch(
    `/api/scheduler/ui/schedules/${scheduleId}/preview?hours=${hours}`
  )
  return response.json()
}

export async function listBuiltinSchedules() {
  const response = await fetch('/api/scheduler/ui/schedules/builtin')
  if (!response.ok) throw new Error('Failed to fetch built-in schedules')
  return { data: await response.json() }
}

// Note: Routine validation happens as part of schedule validation.
// There is no separate /routines/validate endpoint.
// Validation errors are returned from POST/PUT /schedules endpoints.
```

---

## Success Criteria

- [ ] `PatternEditor/` directory renamed to `RoutineEditor/`
- [ ] `EventPatternSelector.jsx` removed (not renamed)
- [ ] `useEventPatterns.js` renamed to `useRoutines.js`
- [ ] Pattern library components removed
- [ ] `TriggerSelector` component implemented
- [ ] `RecurringDaysTriggerForm` component implemented
- [ ] `PreConditionForm` component implemented
- [ ] `RoutineCard` with expand/collapse implemented
- [ ] `RoutineCard` uses `display_name` from backend when available
- [ ] `TriggerBadge` component implemented
- [ ] `DayTimeline` component implemented
- [ ] `CalendarView` defaults to day view
- [ ] `ExecutionMarker` supports conflict highlighting
- [ ] `ActivationProgress` component implemented with WebSocket
- [ ] API utilities updated for new field names
- [ ] `routineUtils.js` utility functions implemented
- [ ] All frontend tests pass

---

## E2E Test Updates

For complete E2E transition strategy including test marking patterns (`test.skip`, `test.fixme`), selector conventions, and transition timing, see:

**[Testing Strategy → E2E Test Transition Strategy](./SCHEDULER_TERMINOLOGY_REFACTOR_TESTING.md#e2e-test-transition-strategy)**

### Quick Reference

| Pattern | Usage |
|---------|-------|
| `test.skip()` | Obsolete tests (pattern library removed) |
| `test.fixme()` | Tests needing selector updates |
| New tests | Write after components renamed |

### TDD Checklist

**Before implementing UI changes**:
1. Mark existing tests per [Test Marking Strategy](./SCHEDULER_TERMINOLOGY_REFACTOR_TESTING.md#test-marking-strategy)
2. Update selectors per [Selector Conventions](./SCHEDULER_TERMINOLOGY_REFACTOR_TESTING.md#selector-conventions)
3. Run: `npm run test:e2e -- --grep "scheduler"` (expect failures)

**After implementing**:
1. Remove `test.fixme()` markers
2. Delete `test.skip()` tests
3. Run: `npm run test:e2e -- --grep "scheduler"`

---

## Related Documentation

- [Index](./SCHEDULER_TERMINOLOGY_REFACTOR_INDEX.md) - Navigation hub
- [Overview](./SCHEDULER_TERMINOLOGY_REFACTOR_OVERVIEW.md) - Architecture context
- [Backend Implementation](./SCHEDULER_TERMINOLOGY_REFACTOR_BACKEND.md)
- [Testing Strategy](./SCHEDULER_TERMINOLOGY_REFACTOR_TESTING.md)
- [Reference](./SCHEDULER_TERMINOLOGY_REFACTOR_REFERENCE.md) - Patterns, API spec
