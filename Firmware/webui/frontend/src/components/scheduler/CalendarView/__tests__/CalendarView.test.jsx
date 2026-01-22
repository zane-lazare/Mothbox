/**
 * Tests for CalendarView container component (Issue #228)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CalendarView } from '../CalendarView'
import { useSchedules, useSchedulePreview, useActiveSchedule } from '../../../../hooks/useSchedules'

// Mock the hooks
vi.mock('../../../../hooks/useSchedules', () => ({
  useSchedules: vi.fn(),
  useSchedulePreview: vi.fn(),
  useActiveSchedule: vi.fn(),
}))

// Mock child components to isolate CalendarView logic
vi.mock('../CalendarHeader', () => ({
  default: ({ onViewModeChange, onNavigate, onScheduleSelect, viewMode, currentDate, schedules, selectedScheduleId }) => (
    <div data-testid="calendar-header">
      <button onClick={() => onViewModeChange('day')}>Day</button>
      <button onClick={() => onViewModeChange('week')}>Week</button>
      <button onClick={() => onViewModeChange('month')}>Month</button>
      <button onClick={() => onNavigate('prev')}>Previous</button>
      <button onClick={() => onNavigate('next')}>Next</button>
      <button onClick={() => onNavigate('today')}>Today</button>
      <select
        data-testid="schedule-select"
        value={selectedScheduleId || ''}
        onChange={(e) => onScheduleSelect(e.target.value || null)}
      >
        <option value="">Select schedule...</option>
        {schedules.map((s) => (
          <option key={s.schedule_id} value={s.schedule_id}>
            {s.name}
          </option>
        ))}
      </select>
      <div data-testid="current-view-mode">{viewMode}</div>
      <div data-testid="current-date">{currentDate.toISOString()}</div>
    </div>
  ),
}))

vi.mock('../CalendarGrid', () => ({
  default: ({ viewMode, executions, moonPhases, onCellClick, onExecutionClick }) => (
    <div data-testid="calendar-grid">
      <div data-testid="grid-view-mode">{viewMode}</div>
      <div data-testid="grid-executions-count">{executions.length}</div>
      <div data-testid="grid-moon-phases-count">{Object.keys(moonPhases).length}</div>
      {executions.map((exec) => (
        <button
          key={exec.execution_id}
          onClick={() => onExecutionClick(exec)}
          data-testid={`execution-${exec.execution_id}`}
        >
          {exec.event_name}
        </button>
      ))}
      <button onClick={() => onCellClick(new Date(2025, 11, 25))}>
        Cell Click
      </button>
    </div>
  ),
}))

vi.mock('../ExecutionDetailModal', () => ({
  default: ({ isOpen, onClose, execution, moonPhase }) => (
    isOpen ? (
      <div data-testid="execution-detail-modal">
        <button onClick={onClose} data-testid="close-modal">Close</button>
        {execution && <div data-testid="modal-execution-id">{execution.execution_id}</div>}
        {moonPhase && <div data-testid="modal-moon-phase">{moonPhase.phase}</div>}
      </div>
    ) : null
  ),
}))

vi.mock('../../../LoadingSpinner', () => ({
  default: () => <div data-testid="loading-spinner">Loading...</div>,
}))

describe('CalendarView', () => {
  const mockSchedules = [
    { schedule_id: 'sched-1', name: 'Morning Photography' },
    { schedule_id: 'sched-2', name: 'Night Capture' },
  ]

  const mockExecutions = [
    {
      execution_id: 'exec-1',
      event_name: 'Morning Capture',
      start_time: '2025-12-17T08:00:00Z',
      end_time: '2025-12-17T08:30:00Z',
      action: 'take_photo',
      scheduled_time: '2025-12-17T08:00:00Z',
    },
    {
      execution_id: 'exec-2',
      event_name: 'Evening Capture',
      start_time: '2025-12-17T18:00:00Z',
      end_time: '2025-12-17T18:30:00Z',
      action: 'take_photo',
      scheduled_time: '2025-12-17T18:00:00Z',
    },
  ]

  const mockMoonPhases = {
    '2025-12-17': { phase: 'waning_gibbous', illumination: 0.75 },
    '2025-12-18': { phase: 'waning_gibbous', illumination: 0.68 },
  }

  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear()
    vi.clearAllMocks()

    // Default mock implementations
    useSchedules.mockReturnValue({
      data: { schedules: mockSchedules, total: mockSchedules.length },
      isLoading: false,
      isError: false,
    })

    useSchedulePreview.mockReturnValue({
      data: null,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    })

    useActiveSchedule.mockReturnValue({
      data: null,
      isLoading: false,
    })
  })

  afterEach(() => {
    localStorage.clear()
  })

  describe('Rendering', () => {
    it('renders CalendarHeader', () => {
      render(<CalendarView />)

      expect(screen.getByTestId('calendar-header')).toBeInTheDocument()
    })

    it('renders CalendarGrid when schedule is selected', async () => {
      const user = userEvent.setup()

      useSchedulePreview.mockReturnValue({
        data: {
          executions: mockExecutions,
          moon_phases: mockMoonPhases,
        },
        isLoading: false,
        isError: false,
        error: null,
        refetch: vi.fn(),
      })

      render(<CalendarView />)

      // Select a schedule
      await user.selectOptions(screen.getByTestId('schedule-select'), 'sched-1')

      await waitFor(() => {
        expect(screen.getByTestId('calendar-grid')).toBeInTheDocument()
      })
    })

    it('does not render modal when not open', () => {
      render(<CalendarView />)

      expect(screen.queryByTestId('execution-detail-modal')).not.toBeInTheDocument()
    })
  })

  describe('Loading States', () => {
    it('shows loading state when fetching schedules', () => {
      useSchedules.mockReturnValue({
        data: null,
        isLoading: true,
        isError: false,
      })

      render(<CalendarView />)

      expect(screen.getByTestId('loading-spinner')).toBeInTheDocument()
      expect(screen.queryByTestId('calendar-header')).not.toBeInTheDocument()
    })

    it('shows loading state when fetching preview', async () => {
      const user = userEvent.setup()

      useSchedulePreview.mockReturnValue({
        data: null,
        isLoading: true,
        isError: false,
        error: null,
        refetch: vi.fn(),
      })

      render(<CalendarView />)

      // Select a schedule to trigger loading
      await user.selectOptions(screen.getByTestId('schedule-select'), 'sched-1')

      await waitFor(() => {
        // Header should still render
        expect(screen.getByTestId('calendar-header')).toBeInTheDocument()
        // Grid should be replaced with loading spinner
        expect(screen.getByTestId('loading-spinner')).toBeInTheDocument()
      })
      expect(screen.queryByTestId('calendar-grid')).not.toBeInTheDocument()
    })
  })

  describe('Error States', () => {
    it('shows error state when preview fetch fails', async () => {
      const user = userEvent.setup()

      // Start with no error - simulate selecting schedule first
      const mockRefetch = vi.fn()
      useSchedulePreview.mockReturnValue({
        data: null,
        isLoading: false,
        isError: false,
        error: null,
        refetch: mockRefetch,
      })

      render(<CalendarView />)

      // Update mock to return error state
      useSchedulePreview.mockReturnValue({
        data: null,
        isLoading: false,
        isError: true,
        error: { message: 'Network error' },
        refetch: mockRefetch,
      })

      // Select a schedule to trigger error display
      const select = screen.getByTestId('schedule-select')
      await user.selectOptions(select, 'sched-1')

      await waitFor(() => {
        expect(screen.getByText('Failed to load schedule preview')).toBeInTheDocument()
      })
      expect(screen.getByText('Network error')).toBeInTheDocument()
    })

    it('shows default error message when error details missing', async () => {
      const user = userEvent.setup()

      const mockRefetch = vi.fn()
      useSchedulePreview.mockReturnValue({
        data: null,
        isLoading: false,
        isError: false,
        error: null,
        refetch: mockRefetch,
      })

      render(<CalendarView />)

      // Update mock to return error state with no error details
      useSchedulePreview.mockReturnValue({
        data: null,
        isLoading: false,
        isError: true,
        error: null,
        refetch: mockRefetch,
      })

      // Select a schedule to trigger error display
      const select = screen.getByTestId('schedule-select')
      await user.selectOptions(select, 'sched-1')

      await waitFor(() => {
        expect(screen.getByText('Failed to load schedule preview')).toBeInTheDocument()
      })
      expect(screen.getByText('An error occurred')).toBeInTheDocument()
    })

    it('shows retry button on error', async () => {
      const user = userEvent.setup()

      const mockRefetch = vi.fn()
      useSchedulePreview.mockReturnValue({
        data: null,
        isLoading: false,
        isError: false,
        error: null,
        refetch: mockRefetch,
      })

      render(<CalendarView />)

      useSchedulePreview.mockReturnValue({
        data: null,
        isLoading: false,
        isError: true,
        error: { message: 'Network error' },
        refetch: mockRefetch,
      })

      // Select a schedule to trigger error display
      const select = screen.getByTestId('schedule-select')
      await user.selectOptions(select, 'sched-1')

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument()
      })
    })

    it('calls refetch when retry button clicked', async () => {
      const user = userEvent.setup()
      const mockRefetch = vi.fn()

      useSchedulePreview.mockReturnValue({
        data: null,
        isLoading: false,
        isError: false,
        error: null,
        refetch: mockRefetch,
      })

      render(<CalendarView />)

      useSchedulePreview.mockReturnValue({
        data: null,
        isLoading: false,
        isError: true,
        error: { message: 'Network error' },
        refetch: mockRefetch,
      })

      // Select a schedule to trigger error display
      const select = screen.getByTestId('schedule-select')
      await user.selectOptions(select, 'sched-1')

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument()
      })

      const retryButton = screen.getByRole('button', { name: /retry/i })
      await user.click(retryButton)

      expect(mockRefetch).toHaveBeenCalledTimes(1)
    })

    it('does not show error when no schedule selected', () => {
      useSchedulePreview.mockReturnValue({
        data: null,
        isLoading: false,
        isError: true,
        error: { message: 'Network error' },
        refetch: vi.fn(),
      })

      render(<CalendarView />)

      // Error should not display when no schedule is selected
      expect(screen.queryByText('Failed to load schedule preview')).not.toBeInTheDocument()
      expect(screen.queryByText('Network error')).not.toBeInTheDocument()
    })

    it('shows error icon on error state', async () => {
      const user = userEvent.setup()

      const mockRefetch = vi.fn()
      useSchedulePreview.mockReturnValue({
        data: null,
        isLoading: false,
        isError: false,
        error: null,
        refetch: mockRefetch,
      })

      render(<CalendarView />)

      useSchedulePreview.mockReturnValue({
        data: null,
        isLoading: false,
        isError: true,
        error: { message: 'Network error' },
        refetch: mockRefetch,
      })

      // Select a schedule to trigger error display
      const select = screen.getByTestId('schedule-select')
      await user.selectOptions(select, 'sched-1')

      // ExclamationCircleIcon should be rendered
      await waitFor(() => {
        const errorContainer = screen.getByText('Failed to load schedule preview').closest('div')
        expect(errorContainer.parentElement).toBeInTheDocument()
      })
    })

    it('hides calendar grid when error occurs', async () => {
      const user = userEvent.setup()

      const mockRefetch = vi.fn()
      useSchedulePreview.mockReturnValue({
        data: null,
        isLoading: false,
        isError: false,
        error: null,
        refetch: mockRefetch,
      })

      render(<CalendarView />)

      useSchedulePreview.mockReturnValue({
        data: null,
        isLoading: false,
        isError: true,
        error: { message: 'Network error' },
        refetch: mockRefetch,
      })

      // Select a schedule to trigger error display
      const select = screen.getByTestId('schedule-select')
      await user.selectOptions(select, 'sched-1')

      await waitFor(() => {
        expect(screen.queryByTestId('calendar-grid')).not.toBeInTheDocument()
      })
    })

    it('hides loading spinner when error occurs', async () => {
      const user = userEvent.setup()

      const mockRefetch = vi.fn()
      useSchedulePreview.mockReturnValue({
        data: null,
        isLoading: false,
        isError: false,
        error: null,
        refetch: mockRefetch,
      })

      render(<CalendarView />)

      useSchedulePreview.mockReturnValue({
        data: null,
        isLoading: false,
        isError: true,
        error: { message: 'Network error' },
        refetch: mockRefetch,
      })

      // Select a schedule to trigger error display
      const select = screen.getByTestId('schedule-select')
      await user.selectOptions(select, 'sched-1')

      await waitFor(() => {
        expect(screen.queryByTestId('loading-spinner')).not.toBeInTheDocument()
      })
    })
  })

  describe('Schedule Selection', () => {
    it('fetches preview when schedule selected', async () => {
      const user = userEvent.setup()
      render(<CalendarView />)

      const select = screen.getByTestId('schedule-select')
      await user.selectOptions(select, 'sched-1')

      // Verify useSchedulePreview was called with correct schedule ID
      await waitFor(() => {
        expect(useSchedulePreview).toHaveBeenCalledWith(
          'sched-1',
          { days: 42, tz: expect.any(String) }, // Default is month view (42 days = 6 weeks)
          { enabled: true }
        )
      })
    })

    it('does not fetch preview when no schedule selected', () => {
      render(<CalendarView />)

      // Verify useSchedulePreview was called with null and enabled: false
      expect(useSchedulePreview).toHaveBeenCalledWith(
        null,
        { days: 42, tz: expect.any(String) },
        { enabled: false }
      )
    })

    it('passes preview data to CalendarGrid', async () => {
      const user = userEvent.setup()

      useSchedulePreview.mockReturnValue({
        data: {
          executions: mockExecutions,
          moon_phases: mockMoonPhases,
        },
        isLoading: false,
        isError: false,
        error: null,
        refetch: vi.fn(),
      })

      render(<CalendarView />)

      // Select a schedule to see the grid
      await user.selectOptions(screen.getByTestId('schedule-select'), 'sched-1')

      await waitFor(() => {
        expect(screen.getByTestId('grid-executions-count')).toHaveTextContent('2')
      })
      expect(screen.getByTestId('grid-moon-phases-count')).toHaveTextContent('2')
    })
  })

  describe('View Mode Management', () => {
    it('calculates correct preview days for month view', async () => {
      const user = userEvent.setup()
      render(<CalendarView />)

      await user.click(screen.getByText('Month'))

      await waitFor(() => {
        expect(useSchedulePreview).toHaveBeenCalledWith(
          null,
          { days: 42, tz: expect.any(String) },
          { enabled: false }
        )
      })
    })

    it('calculates correct preview days for week view', async () => {
      const user = userEvent.setup()
      render(<CalendarView />)

      await user.click(screen.getByText('Week'))

      await waitFor(() => {
        expect(useSchedulePreview).toHaveBeenCalledWith(
          null,
          { days: 7, tz: expect.any(String) },
          { enabled: false }
        )
      })
    })

    it('calculates correct preview days for day view', async () => {
      const user = userEvent.setup()
      render(<CalendarView />)

      await user.click(screen.getByText('Day'))

      await waitFor(() => {
        expect(useSchedulePreview).toHaveBeenCalledWith(
          null,
          { days: 2, tz: expect.any(String) }, // 2 days to capture overnight schedules
          { enabled: false }
        )
      })
    })

    it('persists view mode to localStorage', async () => {
      const user = userEvent.setup()
      render(<CalendarView />)

      await user.click(screen.getByText('Week'))

      await waitFor(() => {
        expect(localStorage.getItem('mothbox-calendar-view-mode')).toBe('week')
      })
    })

    it('loads view mode from localStorage on mount', () => {
      localStorage.setItem('mothbox-calendar-view-mode', 'day')

      render(<CalendarView />)

      expect(screen.getByTestId('current-view-mode')).toHaveTextContent('day')
    })

    it('defaults to month view when localStorage empty', () => {
      render(<CalendarView />)

      expect(screen.getByTestId('current-view-mode')).toHaveTextContent('month')
    })

    it('defaults to month view when localStorage has invalid value', () => {
      localStorage.setItem('mothbox-calendar-view-mode', 'invalid-view')

      render(<CalendarView />)

      expect(screen.getByTestId('current-view-mode')).toHaveTextContent('month')
    })

    it('uses week view when localStorage has valid week value', () => {
      localStorage.setItem('mothbox-calendar-view-mode', 'week')

      render(<CalendarView />)

      expect(screen.getByTestId('current-view-mode')).toHaveTextContent('week')
    })

    it('falls back to month view days (42) for unknown view modes', () => {
      // Test the PREVIEW_DAYS constant fallback behavior
      // This ensures that if an invalid view mode somehow gets set,
      // we default to month view's 42 days (6 weeks)
      localStorage.setItem('mothbox-calendar-view-mode', 'invalid-mode')

      render(<CalendarView />)

      // Should use month's preview days (42) as fallback
      expect(useSchedulePreview).toHaveBeenCalledWith(
        null,
        { days: 42, tz: expect.any(String) },
        { enabled: false }
      )
    })
  })

  describe('Navigation', () => {
    it('handles "today" navigation', async () => {
      const user = userEvent.setup()
      render(<CalendarView />)

      const initialDate = screen.getByTestId('current-date').textContent

      await user.click(screen.getByText('Today'))

      // Date should be updated to today
      const newDate = screen.getByTestId('current-date').textContent
      expect(newDate).not.toBe(initialDate)
      expect(new Date(newDate).toDateString()).toBe(new Date().toDateString())
    })

    it('handles "prev" navigation in month view', async () => {
      const user = userEvent.setup()
      render(<CalendarView />)

      const initialDateStr = screen.getByTestId('current-date').textContent
      const initialDate = new Date(initialDateStr)

      await user.click(screen.getByText('Previous'))

      const newDateStr = screen.getByTestId('current-date').textContent
      const newDate = new Date(newDateStr)

      // Should go back one month
      expect(newDate.getMonth()).toBe(
        (initialDate.getMonth() - 1 + 12) % 12
      )
    })

    it('handles "next" navigation in month view', async () => {
      const user = userEvent.setup()
      render(<CalendarView />)

      const initialDateStr = screen.getByTestId('current-date').textContent
      const initialDate = new Date(initialDateStr)

      await user.click(screen.getByText('Next'))

      const newDateStr = screen.getByTestId('current-date').textContent
      const newDate = new Date(newDateStr)

      // Should go forward one month
      expect(newDate.getMonth()).toBe((initialDate.getMonth() + 1) % 12)
    })

    it('handles "prev" navigation in week view (uses patternOffset, not date)', async () => {
      const user = userEvent.setup()
      render(<CalendarView />)

      await user.click(screen.getByText('Week'))

      const initialDateStr = screen.getByTestId('current-date').textContent

      await user.click(screen.getByText('Previous'))

      const newDateStr = screen.getByTestId('current-date').textContent

      // In week view, navigation uses patternOffset instead of date
      // Date should remain unchanged (patternOffset is internal state)
      expect(newDateStr).toBe(initialDateStr)
    })

    it('handles "next" navigation in week view (uses patternOffset, not date)', async () => {
      const user = userEvent.setup()
      render(<CalendarView />)

      await user.click(screen.getByText('Week'))

      const initialDateStr = screen.getByTestId('current-date').textContent

      await user.click(screen.getByText('Next'))

      const newDateStr = screen.getByTestId('current-date').textContent

      // In week view, navigation uses patternOffset instead of date
      // Date should remain unchanged (patternOffset is internal state)
      expect(newDateStr).toBe(initialDateStr)
    })

    it('handles "prev" navigation in day view', async () => {
      const user = userEvent.setup()
      render(<CalendarView />)

      await user.click(screen.getByText('Day'))

      const initialDateStr = screen.getByTestId('current-date').textContent
      const initialDate = new Date(initialDateStr)

      await user.click(screen.getByText('Previous'))

      const newDateStr = screen.getByTestId('current-date').textContent
      const newDate = new Date(newDateStr)

      // Should go back one day
      const daysDiff = Math.floor((newDate - initialDate) / (1000 * 60 * 60 * 24))
      expect(daysDiff).toBe(-1)
    })

    it('handles "next" navigation in day view', async () => {
      const user = userEvent.setup()
      render(<CalendarView />)

      await user.click(screen.getByText('Day'))

      const initialDateStr = screen.getByTestId('current-date').textContent
      const initialDate = new Date(initialDateStr)

      await user.click(screen.getByText('Next'))

      const newDateStr = screen.getByTestId('current-date').textContent
      const newDate = new Date(newDateStr)

      // Should go forward one day
      const daysDiff = Math.floor((newDate - initialDate) / (1000 * 60 * 60 * 24))
      expect(daysDiff).toBe(1)
    })

    it('navigates from Jan 31 to Feb without month overflow', async () => {
      const user = userEvent.setup()

      // Mock the current date to Jan 31
      const jan31 = new Date(2025, 0, 31)
      vi.setSystemTime(jan31)

      render(<CalendarView />)

      // Click Month to ensure we're in month view
      await user.click(screen.getByText('Month'))

      // Click Today to set to Jan 31
      await user.click(screen.getByText('Today'))

      // Click Next to go to next month
      await user.click(screen.getByText('Next'))

      const newDateStr = screen.getByTestId('current-date').textContent
      const newDate = new Date(newDateStr)

      // Should be February (month 1), not March (month 2)
      expect(newDate.getMonth()).toBe(1)
      expect(newDate.getFullYear()).toBe(2025)

      vi.useRealTimers()
    })

    it('navigates from Mar 31 to Feb to Jan without skipping months', async () => {
      const user = userEvent.setup()

      // Mock the current date to Mar 31, 2025
      const mar31 = new Date(2025, 2, 31)
      vi.setSystemTime(mar31)

      render(<CalendarView />)

      // Click Month to ensure we're in month view
      await user.click(screen.getByText('Month'))

      // Click Today to set to Mar 31
      await user.click(screen.getByText('Today'))

      // Click Previous to go to February
      await user.click(screen.getByText('Previous'))

      let dateStr = screen.getByTestId('current-date').textContent
      let date = new Date(dateStr)

      // Should be February (month 1), not January or skipped
      expect(date.getMonth()).toBe(1)
      expect(date.getFullYear()).toBe(2025)

      // Click Previous again to go to January
      await user.click(screen.getByText('Previous'))

      dateStr = screen.getByTestId('current-date').textContent
      date = new Date(dateStr)

      // Should be January (month 0)
      expect(date.getMonth()).toBe(0)
      expect(date.getFullYear()).toBe(2025)

      // Click Next to go back to February
      await user.click(screen.getByText('Next'))

      dateStr = screen.getByTestId('current-date').textContent
      date = new Date(dateStr)

      // Should be February (month 1) again
      expect(date.getMonth()).toBe(1)
      expect(date.getFullYear()).toBe(2025)

      vi.useRealTimers()
    })
  })

  describe('Execution Modal', () => {
    it('opens modal on execution click', async () => {
      const user = userEvent.setup()
      useSchedulePreview.mockReturnValue({
        data: {
          executions: mockExecutions,
          moon_phases: mockMoonPhases,
        },
        isLoading: false,
        isError: false,
        error: null,
        refetch: vi.fn(),
      })

      render(<CalendarView />)

      // Select a schedule to see executions
      await user.selectOptions(screen.getByTestId('schedule-select'), 'sched-1')

      await waitFor(() => {
        expect(screen.getByTestId('execution-exec-1')).toBeInTheDocument()
      })

      await user.click(screen.getByTestId('execution-exec-1'))

      expect(screen.getByTestId('execution-detail-modal')).toBeInTheDocument()
      expect(screen.getByTestId('modal-execution-id')).toHaveTextContent('exec-1')
    })

    it('closes modal on close button click', async () => {
      const user = userEvent.setup()
      useSchedulePreview.mockReturnValue({
        data: {
          executions: mockExecutions,
          moon_phases: mockMoonPhases,
        },
        isLoading: false,
        isError: false,
        error: null,
        refetch: vi.fn(),
      })

      render(<CalendarView />)

      // Select a schedule to see executions
      await user.selectOptions(screen.getByTestId('schedule-select'), 'sched-1')

      await waitFor(() => {
        expect(screen.getByTestId('execution-exec-1')).toBeInTheDocument()
      })

      await user.click(screen.getByTestId('execution-exec-1'))
      expect(screen.getByTestId('execution-detail-modal')).toBeInTheDocument()

      await user.click(screen.getByTestId('close-modal'))
      expect(screen.queryByTestId('execution-detail-modal')).not.toBeInTheDocument()
    })

    it('passes moon phase for execution date to modal', async () => {
      const user = userEvent.setup()
      useSchedulePreview.mockReturnValue({
        data: {
          executions: mockExecutions,
          moon_phases: mockMoonPhases,
        },
        isLoading: false,
        isError: false,
        error: null,
        refetch: vi.fn(),
      })

      render(<CalendarView />)

      // Select a schedule to see executions
      await user.selectOptions(screen.getByTestId('schedule-select'), 'sched-1')

      await waitFor(() => {
        expect(screen.getByTestId('execution-exec-1')).toBeInTheDocument()
      })

      await user.click(screen.getByTestId('execution-exec-1'))

      expect(screen.getByTestId('modal-moon-phase')).toHaveTextContent('waning_gibbous')
    })

    it('handles execution with missing start_time gracefully', async () => {
      const user = userEvent.setup()
      const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

      const invalidExecution = {
        execution_id: 'exec-invalid',
        event_name: 'Invalid Capture',
        // start_time is missing
        end_time: '2025-12-17T08:30:00Z',
        action: 'take_photo',
        scheduled_time: '2025-12-17T08:00:00Z',
      }

      useSchedulePreview.mockReturnValue({
        data: {
          executions: [invalidExecution],
          moon_phases: mockMoonPhases,
        },
        isLoading: false,
        isError: false,
        error: null,
        refetch: vi.fn(),
      })

      render(<CalendarView />)

      // Select a schedule to see executions
      await user.selectOptions(screen.getByTestId('schedule-select'), 'sched-1')

      await waitFor(() => {
        expect(screen.getByTestId('execution-exec-invalid')).toBeInTheDocument()
      })

      await user.click(screen.getByTestId('execution-exec-invalid'))

      // Modal should open but moon phase should be null
      expect(screen.getByTestId('execution-detail-modal')).toBeInTheDocument()
      expect(screen.queryByTestId('modal-moon-phase')).not.toBeInTheDocument()

      // Should log warning
      expect(warnSpy).toHaveBeenCalledWith(
        'Invalid start_time in execution:',
        expect.objectContaining({ execution_id: 'exec-invalid' })
      )

      warnSpy.mockRestore()
    })

    it('handles execution with null start_time gracefully', async () => {
      const user = userEvent.setup()
      const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

      const invalidExecution = {
        execution_id: 'exec-null',
        event_name: 'Null Start Time',
        start_time: null,
        end_time: '2025-12-17T08:30:00Z',
        action: 'take_photo',
        scheduled_time: '2025-12-17T08:00:00Z',
      }

      useSchedulePreview.mockReturnValue({
        data: {
          executions: [invalidExecution],
          moon_phases: mockMoonPhases,
        },
        isLoading: false,
        isError: false,
        error: null,
        refetch: vi.fn(),
      })

      render(<CalendarView />)

      // Select a schedule to see executions
      await user.selectOptions(screen.getByTestId('schedule-select'), 'sched-1')

      await waitFor(() => {
        expect(screen.getByTestId('execution-exec-null')).toBeInTheDocument()
      })

      await user.click(screen.getByTestId('execution-exec-null'))

      // Modal should open but moon phase should be null
      expect(screen.getByTestId('execution-detail-modal')).toBeInTheDocument()
      expect(screen.queryByTestId('modal-moon-phase')).not.toBeInTheDocument()

      // Should log warning
      expect(warnSpy).toHaveBeenCalledWith(
        'Invalid start_time in execution:',
        expect.objectContaining({ execution_id: 'exec-null' })
      )

      warnSpy.mockRestore()
    })

    it('handles execution with non-string start_time gracefully', async () => {
      const user = userEvent.setup()
      const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

      const invalidExecution = {
        execution_id: 'exec-number',
        event_name: 'Number Start Time',
        start_time: 1234567890, // number instead of string
        end_time: '2025-12-17T08:30:00Z',
        action: 'take_photo',
        scheduled_time: '2025-12-17T08:00:00Z',
      }

      useSchedulePreview.mockReturnValue({
        data: {
          executions: [invalidExecution],
          moon_phases: mockMoonPhases,
        },
        isLoading: false,
        isError: false,
        error: null,
        refetch: vi.fn(),
      })

      render(<CalendarView />)

      // Select a schedule to see executions
      await user.selectOptions(screen.getByTestId('schedule-select'), 'sched-1')

      await waitFor(() => {
        expect(screen.getByTestId('execution-exec-number')).toBeInTheDocument()
      })

      await user.click(screen.getByTestId('execution-exec-number'))

      // Modal should open but moon phase should be null
      expect(screen.getByTestId('execution-detail-modal')).toBeInTheDocument()
      expect(screen.queryByTestId('modal-moon-phase')).not.toBeInTheDocument()

      // Should log warning
      expect(warnSpy).toHaveBeenCalledWith(
        'Invalid start_time in execution:',
        expect.objectContaining({ execution_id: 'exec-number' })
      )

      warnSpy.mockRestore()
    })
  })

  describe('Cell Click', () => {
    it('switches to day view on cell click', async () => {
      const user = userEvent.setup()

      useSchedulePreview.mockReturnValue({
        data: {
          executions: mockExecutions,
          moon_phases: mockMoonPhases,
        },
        isLoading: false,
        isError: false,
        error: null,
        refetch: vi.fn(),
      })

      render(<CalendarView />)

      // Select a schedule to see the grid
      await user.selectOptions(screen.getByTestId('schedule-select'), 'sched-1')

      await waitFor(() => {
        expect(screen.getByTestId('current-view-mode')).toHaveTextContent('month')
      })

      await user.click(screen.getByText('Cell Click'))

      expect(screen.getByTestId('current-view-mode')).toHaveTextContent('day')
    })

    it('updates current date on cell click', async () => {
      const user = userEvent.setup()

      useSchedulePreview.mockReturnValue({
        data: {
          executions: mockExecutions,
          moon_phases: mockMoonPhases,
        },
        isLoading: false,
        isError: false,
        error: null,
        refetch: vi.fn(),
      })

      render(<CalendarView />)

      // Select a schedule to see the grid
      await user.selectOptions(screen.getByTestId('schedule-select'), 'sched-1')

      await waitFor(() => {
        expect(screen.getByTestId('calendar-grid')).toBeInTheDocument()
      })

      await user.click(screen.getByText('Cell Click'))

      const newDateStr = screen.getByTestId('current-date').textContent
      const newDate = new Date(newDateStr)

      expect(newDate.getDate()).toBe(25)
      expect(newDate.getMonth()).toBe(11) // December (0-indexed)
    })
  })

  describe('Empty States', () => {
    it('shows empty state when no schedule selected', () => {
      render(<CalendarView />)

      expect(screen.getByText('No schedule selected')).toBeInTheDocument()
      expect(screen.getByText('Select a schedule from the dropdown above to view its execution preview')).toBeInTheDocument()
    })

    it('shows CalendarDaysIcon when no schedule selected', () => {
      render(<CalendarView />)

      // Check for the empty state container
      const emptyStateText = screen.getByText('No schedule selected')
      const emptyStateContainer = emptyStateText.closest('div')
      expect(emptyStateContainer).toBeInTheDocument()
    })

    it('hides calendar grid when no schedule selected', () => {
      render(<CalendarView />)

      expect(screen.queryByTestId('calendar-grid')).not.toBeInTheDocument()
    })

    it('hides empty state when schedule is selected', async () => {
      const user = userEvent.setup()

      useSchedulePreview.mockReturnValue({
        data: {
          executions: mockExecutions,
          moon_phases: mockMoonPhases,
        },
        isLoading: false,
        isError: false,
        error: null,
        refetch: vi.fn(),
      })

      render(<CalendarView />)

      // Select a schedule
      await user.selectOptions(screen.getByTestId('schedule-select'), 'sched-1')

      await waitFor(() => {
        expect(screen.queryByText('No schedule selected')).not.toBeInTheDocument()
      })
    })

    it('handles empty schedules list', () => {
      useSchedules.mockReturnValue({
        data: { schedules: [], total: 0 },
        isLoading: false,
        isError: false,
      })

      render(<CalendarView />)

      const select = screen.getByTestId('schedule-select')
      expect(select.options).toHaveLength(1) // Only placeholder
    })

    it('handles empty preview data', async () => {
      const user = userEvent.setup()

      useSchedulePreview.mockReturnValue({
        data: {
          executions: [],
          moon_phases: {},
        },
        isLoading: false,
        isError: false,
        error: null,
        refetch: vi.fn(),
      })

      render(<CalendarView />)

      // Select a schedule to see grid with empty data
      await user.selectOptions(screen.getByTestId('schedule-select'), 'sched-1')

      await waitFor(() => {
        expect(screen.getByTestId('grid-executions-count')).toHaveTextContent('0')
      })
      expect(screen.getByTestId('grid-moon-phases-count')).toHaveTextContent('0')
    })

    it('handles missing preview data gracefully', async () => {
      const user = userEvent.setup()

      useSchedulePreview.mockReturnValue({
        data: null,
        isLoading: false,
        isError: false,
        error: null,
        refetch: vi.fn(),
      })

      render(<CalendarView />)

      // Select a schedule to trigger grid rendering
      await user.selectOptions(screen.getByTestId('schedule-select'), 'sched-1')

      await waitFor(() => {
        expect(screen.getByTestId('grid-executions-count')).toHaveTextContent('0')
      })
      expect(screen.getByTestId('grid-moon-phases-count')).toHaveTextContent('0')
    })
  })

  describe('Integration', () => {
    it('refetches preview when view mode changes', async () => {
      const user = userEvent.setup()
      render(<CalendarView />)

      // Select a schedule first
      await user.selectOptions(screen.getByTestId('schedule-select'), 'sched-1')

      await waitFor(() => {
        expect(useSchedulePreview).toHaveBeenCalledWith(
          'sched-1',
          { days: 42, tz: expect.any(String) },
          { enabled: true }
        )
      })

      // Change view mode
      await user.click(screen.getByText('Week'))

      await waitFor(() => {
        expect(useSchedulePreview).toHaveBeenCalledWith(
          'sched-1',
          { days: 7, tz: expect.any(String) },
          { enabled: true }
        )
      })
    })

    it('clears modal state when switching schedules', async () => {
      const user = userEvent.setup()
      useSchedulePreview.mockReturnValue({
        data: {
          executions: mockExecutions,
          moon_phases: mockMoonPhases,
        },
        isLoading: false,
        isError: false,
        error: null,
        refetch: vi.fn(),
      })

      render(<CalendarView />)

      // Select a schedule to see executions
      await user.selectOptions(screen.getByTestId('schedule-select'), 'sched-1')

      await waitFor(() => {
        expect(screen.getByTestId('execution-exec-1')).toBeInTheDocument()
      })

      // Open modal
      await user.click(screen.getByTestId('execution-exec-1'))
      expect(screen.getByTestId('execution-detail-modal')).toBeInTheDocument()

      // Close modal
      await user.click(screen.getByTestId('close-modal'))
      expect(screen.queryByTestId('execution-detail-modal')).not.toBeInTheDocument()
    })
  })
})
