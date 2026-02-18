# Tier 2 Frontend Infrastructure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Wire up orphaned lock cleanup, add frontend CI pipeline with coverage thresholds, and fill remaining test gaps for hooks, pages, and preset components.

**Architecture:** Six independent tasks: one backend startup fix, one CI workflow file, one vitest config change, and three test files. No cross-dependencies between tasks.

**Tech Stack:** Python/Flask (backend), GitHub Actions (CI), Vitest/React Testing Library (frontend tests)

---

## Task 1: Wire Up Lock Cleanup at Startup (#408)

**Files:**
- Modify: `webui/backend/app.py` (~line 300, after service initialization)

**Step 1: Add lock cleanup calls**

After the deployment service initialization block (around line 310), add:

```python
# Clean up orphaned lock files from previous sessions (#408)
# These functions already exist and are tested — we just need to invoke them at startup.
try:
    from webui.backend.lib.schedule_storage import cleanup_temp_files as cleanup_schedule_locks

    removed = cleanup_schedule_locks()
    if removed > 0:
        logger.info(f"Cleaned up {removed} orphaned schedule lock file(s)")
except Exception as e:
    logger.warning(f"Schedule lock cleanup failed (non-fatal): {e}")

try:
    from webui.backend.lib.deployment_sidecar import cleanup_temp_files as cleanup_deployment_locks

    removed = cleanup_deployment_locks(PHOTOS_DIR)
    if removed > 0:
        logger.info(f"Cleaned up {removed} orphaned deployment lock file(s)")
except Exception as e:
    logger.warning(f"Deployment lock cleanup failed (non-fatal): {e}")
```

Note: `PHOTOS_DIR` is already imported at line 131 (`from mothbox_paths import PHOTOS_DIR, THUMBNAIL_CACHE_DIR`).

**Step 2: Verify the app still starts**

Run: `cd /home/zane/projects/Mothbox/Firmware/webui/backend && MOTHBOX_ENV=test python3 -c "import app; print('OK')"`
Expected: No import errors (may warn about missing hardware — that's fine)

**Step 3: Lint**

Run: `ruff check webui/backend/app.py`
Expected: No new errors

**Step 4: Commit**

```bash
git add webui/backend/app.py
git commit -m "fix(backend): wire up orphaned lock cleanup at startup (#408)"
```

---

## Task 2: Add GitHub Actions CI Workflow (#406)

**Files:**
- Create: `.github/workflows/frontend-tests.yml`

**Step 1: Create the workflow file**

```yaml
name: Frontend Tests

on:
  push:
    branches: [main, dev]
    paths:
      - 'Firmware/webui/frontend/**'
      - '.github/workflows/frontend-tests.yml'
  pull_request:
    branches: [main, dev]
    paths:
      - 'Firmware/webui/frontend/**'
      - '.github/workflows/frontend-tests.yml'

defaults:
  run:
    working-directory: Firmware/webui/frontend

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        shard: [1, 2, 3, 4]
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm
          cache-dependency-path: Firmware/webui/frontend/package-lock.json

      - run: npm ci

      - name: Run tests (shard ${{ matrix.shard }}/4)
        run: npx vitest run --shard=${{ matrix.shard }}/4 --reporter=verbose

  coverage:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm
          cache-dependency-path: Firmware/webui/frontend/package-lock.json

      - run: npm ci

      - name: Run coverage
        run: npx vitest run --coverage --reporter=verbose

      - name: Upload coverage report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: coverage-report
          path: Firmware/webui/frontend/coverage/
          retention-days: 14
```

**Step 2: Verify YAML syntax**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/frontend-tests.yml'))" 2>&1 || echo "Install pyyaml or skip — YAML syntax is simple enough to verify visually"`

**Step 3: Commit**

```bash
git add .github/workflows/frontend-tests.yml
git commit -m "ci(frontend): add GitHub Actions workflow with 4-shard parallelization (#406)"
```

---

## Task 3: Add Coverage Threshold (#406)

**Files:**
- Modify: `webui/frontend/vitest.config.js:42-48`

**Step 1: Add thresholds to coverage config**

Replace lines 42-48:

```javascript
    coverage: {
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'src/setupTests.js',
      ]
    }
```

With:

```javascript
    coverage: {
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'src/setupTests.js',
      ],
      thresholds: {
        statements: 70,
        branches: 60,
        functions: 70,
        lines: 70,
      },
    }
```

**Step 2: Verify thresholds don't break current coverage**

Run: `cd /home/zane/projects/Mothbox/Firmware/webui/frontend && npx vitest run --coverage 2>&1 | tail -20`
Expected: Coverage passes (current coverage should be well above 70%)

**Step 3: Commit**

```bash
git add webui/frontend/vitest.config.js
git commit -m "test(frontend): add coverage threshold to vitest config (#406)"
```

---

## Task 4: Add Tests for useSelection and useValidateDraft (#406)

**Files:**
- Create: `webui/frontend/src/hooks/__tests__/useSelection.test.jsx`
- Create: `webui/frontend/src/hooks/__tests__/useValidateDraft.test.jsx`

### useSelection Tests

`useSelection` is a thin wrapper around `SelectionContext`. It returns the context value or throws if used outside the provider.

The `SelectionContext` provides: `isSelectMode`, `selectedPhotos` (Set), `selectedCount`, `selectedArray`, `toggleSelectMode`, `selectPhoto`, `deselectPhoto`, `togglePhoto`, `selectRange`, `selectAll`, `deselectAll`, `isSelected`.

```jsx
import { describe, it, expect } from 'vitest'
import { renderHook } from '@testing-library/react'
import React from 'react'
import useSelection from '../useSelection'
import { SelectionProvider } from '../../contexts/SelectionContext'

const wrapper = ({ children }) => (
  <SelectionProvider>{children}</SelectionProvider>
)

describe('useSelection', () => {
  it('throws when used outside SelectionProvider', () => {
    // Suppress console.error for expected error
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(() => renderHook(() => useSelection())).toThrow(
      'useSelection must be used within SelectionProvider'
    )
    spy.mockRestore()
  })

  it('returns context value when inside SelectionProvider', () => {
    const { result } = renderHook(() => useSelection(), { wrapper })
    expect(result.current).toBeDefined()
    expect(result.current.isSelectMode).toBe(false)
    expect(result.current.selectedCount).toBe(0)
    expect(typeof result.current.toggleSelectMode).toBe('function')
    expect(typeof result.current.selectPhoto).toBe('function')
    expect(typeof result.current.deselectPhoto).toBe('function')
    expect(typeof result.current.isSelected).toBe('function')
  })

  it('provides all expected context properties', () => {
    const { result } = renderHook(() => useSelection(), { wrapper })
    const expectedKeys = [
      'isSelectMode', 'selectedPhotos', 'lastClickedIndex',
      'selectedCount', 'selectedArray',
      'toggleSelectMode', 'selectPhoto', 'deselectPhoto',
      'togglePhoto', 'selectRange', 'selectAll', 'deselectAll', 'isSelected',
    ]
    expectedKeys.forEach(key => {
      expect(result.current).toHaveProperty(key)
    })
  })
})
```

### useValidateDraft Tests

This hook uses React Query and debouncing. Follow the pattern from `useSchedules.test.jsx`: mock the API module, wrap with `QueryClientProvider`, use `waitFor` for async assertions.

```jsx
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import React from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useValidateDraft } from '../useValidateDraft'
import * as schedulerApi from '../../utils/schedulerApi'

vi.mock('../../utils/schedulerApi')

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  return ({ children }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

const validRoutine = {
  trigger: { trigger_type: 'interval' },
  actions: [{ type: 'takephoto' }],
}

describe('useValidateDraft', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('returns initial state', () => {
    const { result } = renderHook(() => useValidateDraft(), {
      wrapper: createWrapper(),
    })
    expect(result.current.conflictReport).toBeNull()
    expect(result.current.isValidating).toBe(false)
    expect(result.current.isError).toBe(false)
    expect(result.current.error).toBeNull()
    expect(typeof result.current.validateDraft).toBe('function')
    expect(typeof result.current.reset).toBe('function')
  })

  it('debounces validation calls', () => {
    const { result } = renderHook(() => useValidateDraft(), {
      wrapper: createWrapper(),
    })

    act(() => {
      result.current.validateDraft([validRoutine])
    })

    // API should NOT be called immediately
    expect(schedulerApi.validateDraftRoutines).not.toHaveBeenCalled()
  })

  it('triggers validation after debounce delay', async () => {
    const mockResponse = { data: { conflicts: [], total_conflicts: 0 } }
    schedulerApi.validateDraftRoutines.mockResolvedValue(mockResponse)

    const { result } = renderHook(() => useValidateDraft(), {
      wrapper: createWrapper(),
    })

    act(() => {
      result.current.validateDraft([validRoutine])
    })

    // Advance past debounce delay (400ms)
    act(() => {
      vi.advanceTimersByTime(500)
    })

    await waitFor(() => {
      expect(schedulerApi.validateDraftRoutines).toHaveBeenCalledTimes(1)
    })
  })

  it('filters routines without trigger_type or actions', async () => {
    const mockResponse = { data: { conflicts: [], total_conflicts: 0 } }
    schedulerApi.validateDraftRoutines.mockResolvedValue(mockResponse)

    const { result } = renderHook(() => useValidateDraft(), {
      wrapper: createWrapper(),
    })

    const routines = [
      validRoutine,
      { trigger: {}, actions: [{ type: 'takephoto' }] },       // no trigger_type
      { trigger: { trigger_type: 'interval' }, actions: [] },   // no actions
      null,                                                       // null
    ]

    act(() => {
      result.current.validateDraft(routines)
    })

    act(() => {
      vi.advanceTimersByTime(500)
    })

    await waitFor(() => {
      expect(schedulerApi.validateDraftRoutines).toHaveBeenCalledTimes(1)
      const callArgs = schedulerApi.validateDraftRoutines.mock.calls[0][0]
      expect(callArgs.routines).toHaveLength(1)
    })
  })

  it('does not call API when all routines are invalid', () => {
    const { result } = renderHook(() => useValidateDraft(), {
      wrapper: createWrapper(),
    })

    act(() => {
      result.current.validateDraft([{ trigger: {}, actions: [] }])
    })

    act(() => {
      vi.advanceTimersByTime(500)
    })

    // Should not call API since no valid routines
    expect(schedulerApi.validateDraftRoutines).not.toHaveBeenCalled()
  })

  it('passes options to API call', async () => {
    const mockResponse = { data: { conflicts: [], total_conflicts: 0 } }
    schedulerApi.validateDraftRoutines.mockResolvedValue(mockResponse)

    const { result } = renderHook(
      () => useValidateDraft({ days: 3, latitude: 9.0, longitude: -79.5, timezone: 'America/Panama' }),
      { wrapper: createWrapper() }
    )

    act(() => {
      result.current.validateDraft([validRoutine])
    })

    act(() => {
      vi.advanceTimersByTime(500)
    })

    await waitFor(() => {
      const callArgs = schedulerApi.validateDraftRoutines.mock.calls[0][0]
      expect(callArgs.days).toBe(3)
      expect(callArgs.latitude).toBe(9.0)
      expect(callArgs.longitude).toBe(-79.5)
      expect(callArgs.timezone).toBe('America/Panama')
    })
  })

  it('returns conflict report after validation', async () => {
    const mockReport = {
      conflicts: [{ type: 'time_overlap', severity: 'warning' }],
      total_conflicts: 1,
    }
    schedulerApi.validateDraftRoutines.mockResolvedValue({ data: mockReport })

    const { result } = renderHook(() => useValidateDraft(), {
      wrapper: createWrapper(),
    })

    act(() => {
      result.current.validateDraft([validRoutine])
    })

    act(() => {
      vi.advanceTimersByTime(500)
    })

    await waitFor(() => {
      expect(result.current.conflictReport).toEqual(mockReport)
    })
  })

  it('handles API errors', async () => {
    schedulerApi.validateDraftRoutines.mockRejectedValue(new Error('Network error'))

    const { result } = renderHook(() => useValidateDraft(), {
      wrapper: createWrapper(),
    })

    act(() => {
      result.current.validateDraft([validRoutine])
    })

    act(() => {
      vi.advanceTimersByTime(500)
    })

    await waitFor(() => {
      expect(result.current.isError).toBe(true)
      expect(result.current.error).toBeTruthy()
    })
  })

  it('resets state when reset is called', async () => {
    const mockResponse = { data: { conflicts: [], total_conflicts: 0 } }
    schedulerApi.validateDraftRoutines.mockResolvedValue(mockResponse)

    const { result } = renderHook(() => useValidateDraft(), {
      wrapper: createWrapper(),
    })

    // Trigger validation
    act(() => {
      result.current.validateDraft([validRoutine])
    })

    act(() => {
      vi.advanceTimersByTime(500)
    })

    await waitFor(() => {
      expect(result.current.conflictReport).toBeDefined()
    })

    // Reset
    act(() => {
      result.current.reset()
    })

    await waitFor(() => {
      expect(result.current.conflictReport).toBeNull()
    })
  })

  it('cancels pending debounce on reset', () => {
    const { result } = renderHook(() => useValidateDraft(), {
      wrapper: createWrapper(),
    })

    act(() => {
      result.current.validateDraft([validRoutine])
    })

    // Reset before debounce fires
    act(() => {
      result.current.reset()
    })

    act(() => {
      vi.advanceTimersByTime(500)
    })

    expect(schedulerApi.validateDraftRoutines).not.toHaveBeenCalled()
  })

  it('handles null/undefined routines array', () => {
    const { result } = renderHook(() => useValidateDraft(), {
      wrapper: createWrapper(),
    })

    act(() => {
      result.current.validateDraft(null)
    })

    act(() => {
      vi.advanceTimersByTime(500)
    })

    expect(schedulerApi.validateDraftRoutines).not.toHaveBeenCalled()
  })
})
```

**Step 1: Create both test files**

Write the files above.

**Step 2: Run useSelection tests**

Run: `cd /home/zane/projects/Mothbox/Firmware/webui/frontend && npx vitest run src/hooks/__tests__/useSelection.test.jsx`
Expected: 3 tests PASS

**Step 3: Run useValidateDraft tests**

Run: `cd /home/zane/projects/Mothbox/Firmware/webui/frontend && npx vitest run src/hooks/__tests__/useValidateDraft.test.jsx`
Expected: 10 tests PASS

**Step 4: Commit**

```bash
git add webui/frontend/src/hooks/__tests__/useSelection.test.jsx \
        webui/frontend/src/hooks/__tests__/useValidateDraft.test.jsx
git commit -m "test(frontend): add tests for useSelection and useValidateDraft hooks (#406)"
```

---

## Task 5: Page Test Audit — GPIO and MapPage (#406)

**Findings**: The page audit found 2 untested pages: `GPIO.jsx` and `MapPage.jsx`.

**Files:**
- Create: `webui/frontend/src/pages/__tests__/GPIO.test.jsx`
- Create: `webui/frontend/src/pages/__tests__/MapPage.test.jsx`

These are basic render/smoke tests — verify the page renders without crashing, key elements are present, and loading/error states work. Follow the pattern from `Dashboard.test.jsx`.

**Important**: Both pages likely use hooks that fetch data. Mock the API modules (`utils/api.js`, `utils/schedulerApi.js`) and wrap with `QueryClientProvider`. For map-specific components, mock `react-leaflet` since it requires a DOM environment that happy-dom doesn't fully support.

**Step 1: Write basic render tests for both pages**

The implementer should:
1. Read `GPIO.jsx` and `MapPage.jsx` to understand their structure
2. Read `Dashboard.test.jsx` for the test pattern
3. Write smoke tests: renders without crash, shows expected headings/elements, handles loading state
4. Mock any API calls and heavy dependencies (leaflet/map components)

**Step 2: Run tests**

Run: `cd /home/zane/projects/Mothbox/Firmware/webui/frontend && npx vitest run src/pages/__tests__/GPIO.test.jsx src/pages/__tests__/MapPage.test.jsx`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add webui/frontend/src/pages/__tests__/GPIO.test.jsx \
        webui/frontend/src/pages/__tests__/MapPage.test.jsx
git commit -m "test(frontend): add smoke tests for GPIO and MapPage (#406)"
```

---

## Task 6: SavePresetModal Tests (#68)

**Files:**
- Create: `webui/frontend/src/components/__tests__/SavePresetModal.test.jsx`

`SavePresetModal` (287 lines) is a form modal with:
- Name input with validation (alphanumeric + underscores, 3-50 chars)
- Description textarea (optional, 200 char display)
- Workflow radio buttons (photo/liveview/both)
- Save button (disabled when name invalid or empty)
- Cancel button (resets form)
- Enter key submits
- Settings validation via `validatePresetSettings()` (only for non-photo workflows)
- Validation error display (role="alert")

**Dependencies to mock**: `validatePresetSettings` from `../../utils/presetValidation`

```jsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import SavePresetModal from '../SavePresetModal'

vi.mock('../../utils/presetValidation', () => ({
  validatePresetSettings: vi.fn(() => []),
}))

import { validatePresetSettings } from '../../utils/presetValidation'

describe('SavePresetModal', () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    onSave: vi.fn().mockResolvedValue(undefined),
    isSaving: false,
  }

  beforeEach(() => {
    vi.clearAllMocks()
    validatePresetSettings.mockReturnValue([])
  })

  it('returns null when not open', () => {
    const { container } = render(<SavePresetModal {...defaultProps} isOpen={false} />)
    expect(container.innerHTML).toBe('')
  })

  it('renders modal when open', () => {
    render(<SavePresetModal {...defaultProps} />)
    expect(screen.getByText('Save Current Settings as Preset')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('e.g., my_field_setup')).toBeInTheDocument()
    expect(screen.getByText('Cancel')).toBeInTheDocument()
    expect(screen.getByText('Save Preset')).toBeInTheDocument()
  })

  it('shows validation error for short name', async () => {
    render(<SavePresetModal {...defaultProps} />)
    const input = screen.getByPlaceholderText('e.g., my_field_setup')
    await userEvent.type(input, 'ab')
    expect(screen.getByText('Name must be at least 3 characters')).toBeInTheDocument()
  })

  it('shows validation error for invalid characters', async () => {
    render(<SavePresetModal {...defaultProps} />)
    const input = screen.getByPlaceholderText('e.g., my_field_setup')
    await userEvent.type(input, 'my preset!')
    expect(screen.getByText('Name can only contain letters, numbers, and underscores')).toBeInTheDocument()
  })

  it('accepts valid name', async () => {
    render(<SavePresetModal {...defaultProps} />)
    const input = screen.getByPlaceholderText('e.g., my_field_setup')
    await userEvent.type(input, 'valid_preset_123')
    expect(screen.queryByText(/Name must/)).not.toBeInTheDocument()
    expect(screen.queryByText(/Name can only/)).not.toBeInTheDocument()
  })

  it('save button disabled when name is empty', () => {
    render(<SavePresetModal {...defaultProps} />)
    expect(screen.getByText('Save Preset')).toBeDisabled()
  })

  it('save button enabled with valid name', async () => {
    render(<SavePresetModal {...defaultProps} />)
    await userEvent.type(screen.getByPlaceholderText('e.g., my_field_setup'), 'valid_name')
    expect(screen.getByText('Save Preset')).not.toBeDisabled()
  })

  it('calls onSave with correct data', async () => {
    render(<SavePresetModal {...defaultProps} />)
    await userEvent.type(screen.getByPlaceholderText('e.g., my_field_setup'), 'test_preset')
    await userEvent.type(screen.getByPlaceholderText('Describe when to use this preset...'), 'A test description')
    await userEvent.click(screen.getByText('Save Preset'))

    expect(defaultProps.onSave).toHaveBeenCalledWith({
      name: 'test_preset',
      description: 'A test description',
      workflow: 'both',
      from_current: true,
    })
  })

  it('selects photo workflow', async () => {
    render(<SavePresetModal {...defaultProps} />)
    await userEvent.type(screen.getByPlaceholderText('e.g., my_field_setup'), 'test_preset')
    await userEvent.click(screen.getByLabelText(/Photo/))
    await userEvent.click(screen.getByText('Save Preset'))

    expect(defaultProps.onSave).toHaveBeenCalledWith(
      expect.objectContaining({ workflow: 'photo' })
    )
  })

  it('skips settings validation for photo-only workflow', async () => {
    render(<SavePresetModal {...defaultProps} />)
    await userEvent.type(screen.getByPlaceholderText('e.g., my_field_setup'), 'test_preset')
    await userEvent.click(screen.getByLabelText(/Photo/))
    await userEvent.click(screen.getByText('Save Preset'))

    expect(validatePresetSettings).not.toHaveBeenCalled()
  })

  it('validates settings for non-photo workflow', async () => {
    render(<SavePresetModal {...defaultProps} />)
    await userEvent.type(screen.getByPlaceholderText('e.g., my_field_setup'), 'test_preset')
    // Default workflow is 'both', which triggers validation
    await userEvent.click(screen.getByText('Save Preset'))

    expect(validatePresetSettings).toHaveBeenCalled()
  })

  it('displays validation errors', async () => {
    validatePresetSettings.mockReturnValue([
      { key: 'Brightness', value: '999', message: 'Must be between -1.0 and 1.0' },
    ])

    render(<SavePresetModal {...defaultProps} />)
    await userEvent.type(screen.getByPlaceholderText('e.g., my_field_setup'), 'test_preset')
    await userEvent.click(screen.getByText('Save Preset'))

    expect(screen.getByRole('alert')).toBeInTheDocument()
    expect(screen.getByText('Brightness')).toBeInTheDocument()
    expect(defaultProps.onSave).not.toHaveBeenCalled()
  })

  it('calls onClose and resets form on cancel', async () => {
    render(<SavePresetModal {...defaultProps} />)
    await userEvent.type(screen.getByPlaceholderText('e.g., my_field_setup'), 'test_preset')
    await userEvent.click(screen.getByText('Cancel'))

    expect(defaultProps.onClose).toHaveBeenCalled()
  })

  it('shows saving state', () => {
    render(<SavePresetModal {...defaultProps} isSaving={true} />)
    expect(screen.getByText('Saving...')).toBeInTheDocument()
  })

  it('disables inputs while saving', () => {
    render(<SavePresetModal {...defaultProps} isSaving={true} />)
    expect(screen.getByPlaceholderText('e.g., my_field_setup')).toBeDisabled()
    expect(screen.getByText('Cancel')).toBeDisabled()
  })
})
```

**Step 1: Create test file**

Write the file above.

**Step 2: Run tests**

Run: `cd /home/zane/projects/Mothbox/Firmware/webui/frontend && npx vitest run src/components/__tests__/SavePresetModal.test.jsx`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add webui/frontend/src/components/__tests__/SavePresetModal.test.jsx
git commit -m "test(frontend): add tests for SavePresetModal (#68)"
```

---

## Task 7: Final Verification

**Step 1: Run all frontend tests**

Run: `cd /home/zane/projects/Mothbox/Firmware/webui/frontend && npx vitest run --reporter=verbose 2>&1 | tail -10`
Expected: All tests PASS, no regressions

**Step 2: Lint backend**

Run: `ruff check webui/backend/app.py`
Expected: Clean

**Step 3: Verify git log**

Run: `git log --oneline -6`
Expected:
```
abc123 test(frontend): add tests for SavePresetModal (#68)
def456 test(frontend): add smoke tests for GPIO and MapPage (#406)
ghi789 test(frontend): add tests for useSelection and useValidateDraft hooks (#406)
jkl012 test(frontend): add coverage threshold to vitest config (#406)
mno345 ci(frontend): add GitHub Actions workflow with 4-shard parallelization (#406)
pqr678 fix(backend): wire up orphaned lock cleanup at startup (#408)
```
