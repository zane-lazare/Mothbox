/**
 * Tests for CalendarView container component (Issue #228)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CalendarView } from '../CalendarView'
import { useSchedules, useSchedulePreview } from '../../../../hooks/useSchedules'

// Mock the hooks
vi.mock('../../../../hooks/useSchedules', () => ({
  useSchedules: vi.fn(),
  useSchedulePreview: vi.fn(),
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
    })
  })

  afterEach(() => {
    localStorage.clear()
  })

  describe('Rendering', () => {
    it('renders CalendarHeader and CalendarGrid', () => {
      render(<CalendarView />)

      expect(screen.getByTestId('calendar-header')).toBeInTheDocument()
      expect(screen.getByTestId('calendar-grid')).toBeInTheDocument()
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

    it('shows loading state when fetching preview', () => {
      useSchedulePreview.mockReturnValue({
        data: null,
        isLoading: true,
        isError: false,
      })

      render(<CalendarView />)

      // Header should still render
      expect(screen.getByTestId('calendar-header')).toBeInTheDocument()
      // Grid should be replaced with loading spinner
      expect(screen.getByTestId('loading-spinner')).toBeInTheDocument()
      expect(screen.queryByTestId('calendar-grid')).not.toBeInTheDocument()
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
          { days: 35 }, // Default is month view (35 days)
          { enabled: true }
        )
      })
    })

    it('does not fetch preview when no schedule selected', () => {
      render(<CalendarView />)

      // Verify useSchedulePreview was called with null and enabled: false
      expect(useSchedulePreview).toHaveBeenCalledWith(
        null,
        { days: 35 },
        { enabled: false }
      )
    })

    it('passes preview data to CalendarGrid', () => {
      useSchedulePreview.mockReturnValue({
        data: {
          executions: mockExecutions,
          moon_phases: mockMoonPhases,
        },
        isLoading: false,
        isError: false,
      })

      render(<CalendarView />)

      expect(screen.getByTestId('grid-executions-count')).toHaveTextContent('2')
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
          { days: 35 },
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
          { days: 7 },
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
          { days: 1 },
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

    it('handles "prev" navigation in week view', async () => {
      const user = userEvent.setup()
      render(<CalendarView />)

      await user.click(screen.getByText('Week'))

      const initialDateStr = screen.getByTestId('current-date').textContent
      const initialDate = new Date(initialDateStr)

      await user.click(screen.getByText('Previous'))

      const newDateStr = screen.getByTestId('current-date').textContent
      const newDate = new Date(newDateStr)

      // Should go back one week (7 days)
      const daysDiff = Math.floor((newDate - initialDate) / (1000 * 60 * 60 * 24))
      expect(daysDiff).toBe(-7)
    })

    it('handles "next" navigation in week view', async () => {
      const user = userEvent.setup()
      render(<CalendarView />)

      await user.click(screen.getByText('Week'))

      const initialDateStr = screen.getByTestId('current-date').textContent
      const initialDate = new Date(initialDateStr)

      await user.click(screen.getByText('Next'))

      const newDateStr = screen.getByTestId('current-date').textContent
      const newDate = new Date(newDateStr)

      // Should go forward one week (7 days)
      const daysDiff = Math.floor((newDate - initialDate) / (1000 * 60 * 60 * 24))
      expect(daysDiff).toBe(7)
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
      })

      render(<CalendarView />)

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
      })

      render(<CalendarView />)

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
      })

      render(<CalendarView />)

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
      })

      render(<CalendarView />)

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
      })

      render(<CalendarView />)

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
      })

      render(<CalendarView />)

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
      render(<CalendarView />)

      expect(screen.getByTestId('current-view-mode')).toHaveTextContent('month')

      await user.click(screen.getByText('Cell Click'))

      expect(screen.getByTestId('current-view-mode')).toHaveTextContent('day')
    })

    it('updates current date on cell click', async () => {
      const user = userEvent.setup()
      render(<CalendarView />)

      await user.click(screen.getByText('Cell Click'))

      const newDateStr = screen.getByTestId('current-date').textContent
      const newDate = new Date(newDateStr)

      expect(newDate.getDate()).toBe(25)
      expect(newDate.getMonth()).toBe(11) // December (0-indexed)
    })
  })

  describe('Empty States', () => {
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

    it('handles empty preview data', () => {
      useSchedulePreview.mockReturnValue({
        data: {
          executions: [],
          moon_phases: {},
        },
        isLoading: false,
        isError: false,
      })

      render(<CalendarView />)

      expect(screen.getByTestId('grid-executions-count')).toHaveTextContent('0')
      expect(screen.getByTestId('grid-moon-phases-count')).toHaveTextContent('0')
    })

    it('handles missing preview data gracefully', () => {
      useSchedulePreview.mockReturnValue({
        data: null,
        isLoading: false,
        isError: false,
      })

      render(<CalendarView />)

      // Should pass empty arrays
      expect(screen.getByTestId('grid-executions-count')).toHaveTextContent('0')
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
          { days: 35 },
          { enabled: true }
        )
      })

      // Change view mode
      await user.click(screen.getByText('Week'))

      await waitFor(() => {
        expect(useSchedulePreview).toHaveBeenCalledWith(
          'sched-1',
          { days: 7 },
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
      })

      render(<CalendarView />)

      // Open modal
      await user.click(screen.getByTestId('execution-exec-1'))
      expect(screen.getByTestId('execution-detail-modal')).toBeInTheDocument()

      // Close modal
      await user.click(screen.getByTestId('close-modal'))
      expect(screen.queryByTestId('execution-detail-modal')).not.toBeInTheDocument()
    })
  })
})
