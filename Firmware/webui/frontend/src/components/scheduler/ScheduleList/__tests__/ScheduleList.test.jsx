import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

// Mock dependencies BEFORE imports
vi.mock('../../../../hooks/useSchedules', () => ({
  useSchedules: vi.fn(),
  useActiveSchedule: vi.fn(),
  useUpdateSchedule: vi.fn(),
}))

vi.mock('../ScheduleCard', () => ({
  default: ({ schedule, isActive, onView, onToggleEnabled, isTogglingEnabled }) => (
    <div data-testid={`schedule-card-${schedule.schedule_id}`} role="listitem">
      <h3>{schedule.name}</h3>
      <span data-testid={`active-status-${schedule.schedule_id}`}>{isActive ? 'active' : 'inactive'}</span>
      <span data-testid={`toggling-status-${schedule.schedule_id}`}>{isTogglingEnabled ? 'toggling' : 'idle'}</span>
      <button onClick={() => onView(schedule)}>View</button>
      {onToggleEnabled && (
        <button onClick={() => onToggleEnabled(schedule)}>
          {schedule.enabled === false ? 'Enable' : 'Disable'}
        </button>
      )}
    </div>
  ),
}))

vi.mock('../../../LoadingSpinner', () => ({
  default: () => <div data-testid="loading-spinner">Loading...</div>,
}))

vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

import {
  useSchedules,
  useActiveSchedule,
  useUpdateSchedule,
} from '../../../../hooks/useSchedules'
import toast from 'react-hot-toast'
import { ScheduleList } from '../ScheduleList'

describe('ScheduleList', () => {
  const mockSchedules = [
    {
      schedule_id: 'schedule-1',
      name: 'Morning Schedule',
      description: 'Runs in the morning',
    },
    {
      schedule_id: 'schedule-2',
      name: 'Evening Schedule',
      description: 'Runs in the evening',
    },
    {
      schedule_id: 'schedule-3',
      name: 'Night Schedule',
      description: 'Runs at night',
    },
  ]

  const mockOnViewSchedule = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()

    // Default mock implementations
    useSchedules.mockReturnValue({
      data: { schedules: mockSchedules },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    })

    useActiveSchedule.mockReturnValue({
      data: { active_schedule: null },
    })

    useUpdateSchedule.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    })
  })

  describe('Loading State', () => {
    it('should show loading spinner when isLoading is true', () => {
      useSchedules.mockReturnValue({
        data: null,
        isLoading: true,
        error: null,
        refetch: vi.fn(),
      })

      render(<ScheduleList onViewSchedule={mockOnViewSchedule} />)

      expect(screen.getByTestId('loading-spinner')).toBeInTheDocument()
      expect(screen.queryByRole('list')).not.toBeInTheDocument()
    })

    it('should center the loading spinner', () => {
      useSchedules.mockReturnValue({
        data: null,
        isLoading: true,
        error: null,
        refetch: vi.fn(),
      })

      const { container } = render(<ScheduleList onViewSchedule={mockOnViewSchedule} />)
      const loadingContainer = container.querySelector('[data-testid="loading-spinner"]').parentElement

      expect(loadingContainer).toHaveClass('flex', 'justify-center', 'items-center')
    })
  })

  describe('Error State', () => {
    it('should show error message when error occurs', () => {
      const mockError = new Error('Failed to load schedules')
      useSchedules.mockReturnValue({
        data: null,
        isLoading: false,
        error: mockError,
        refetch: vi.fn(),
      })

      render(<ScheduleList onViewSchedule={mockOnViewSchedule} />)

      expect(screen.getByText(/failed to load schedules/i)).toBeInTheDocument()
      expect(screen.queryByRole('list')).not.toBeInTheDocument()
    })

    it('should show retry button in error state', () => {
      useSchedules.mockReturnValue({
        data: null,
        isLoading: false,
        error: new Error('Network error'),
        refetch: vi.fn(),
      })

      render(<ScheduleList onViewSchedule={mockOnViewSchedule} />)

      expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument()
    })

    it('should call refetch when retry button is clicked', async () => {
      const user = userEvent.setup()
      const mockRefetch = vi.fn()

      useSchedules.mockReturnValue({
        data: null,
        isLoading: false,
        error: new Error('Network error'),
        refetch: mockRefetch,
      })

      render(<ScheduleList onViewSchedule={mockOnViewSchedule} />)

      const retryButton = screen.getByRole('button', { name: /retry/i })
      await user.click(retryButton)

      expect(mockRefetch).toHaveBeenCalledTimes(1)
    })

    it('should style error message with red text', () => {
      useSchedules.mockReturnValue({
        data: null,
        isLoading: false,
        error: new Error('Network error'),
        refetch: vi.fn(),
      })

      render(<ScheduleList onViewSchedule={mockOnViewSchedule} />)

      const errorMessage = screen.getByText(/failed to load schedules/i)
      expect(errorMessage).toHaveClass('text-red-600')
    })
  })

  describe('Empty State', () => {
    it('should show empty state message when no schedules', () => {
      useSchedules.mockReturnValue({
        data: { schedules: [] },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      })

      render(<ScheduleList onViewSchedule={mockOnViewSchedule} />)

      expect(screen.getByText(/no schedules yet/i)).toBeInTheDocument()
      expect(screen.queryByRole('list')).not.toBeInTheDocument()
    })

    it('should show icon in empty state', () => {
      useSchedules.mockReturnValue({
        data: { schedules: [] },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      })

      render(<ScheduleList onViewSchedule={mockOnViewSchedule} />)

      // Check for Calendar icon
      const emptyStateContainer = screen.getByText(/no schedules yet/i).parentElement
      expect(emptyStateContainer.querySelector('svg')).toBeInTheDocument()
    })

    it('should center empty state with gray text', () => {
      useSchedules.mockReturnValue({
        data: { schedules: [] },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      })

      render(<ScheduleList onViewSchedule={mockOnViewSchedule} />)

      const emptyStateContainer = screen.getByText(/no schedules yet/i).parentElement
      expect(emptyStateContainer).toHaveClass('text-center')

      const message = screen.getByText(/no schedules yet/i)
      expect(message).toHaveClass('text-gray-500')
    })
  })

  describe('List Rendering', () => {
    it('should render ScheduleCard for each schedule', () => {
      render(<ScheduleList onViewSchedule={mockOnViewSchedule} />)

      expect(screen.getByTestId('schedule-card-schedule-1')).toBeInTheDocument()
      expect(screen.getByTestId('schedule-card-schedule-2')).toBeInTheDocument()
      expect(screen.getByTestId('schedule-card-schedule-3')).toBeInTheDocument()
    })

    it('should use grid layout with responsive columns', () => {
      const { container } = render(<ScheduleList onViewSchedule={mockOnViewSchedule} />)

      const grid = container.querySelector('[role="list"]')
      expect(grid).toHaveClass('grid', 'grid-cols-1', 'md:grid-cols-2', 'lg:grid-cols-3', 'gap-4')
    })

    it('should pass isActive=true to active schedule card', () => {
      useActiveSchedule.mockReturnValue({
        data: { active_schedule: { schedule_id: 'schedule-2' } },
      })

      render(<ScheduleList onViewSchedule={mockOnViewSchedule} />)

      expect(screen.getByTestId('active-status-schedule-1')).toHaveTextContent('inactive')
      expect(screen.getByTestId('active-status-schedule-2')).toHaveTextContent('active')
      expect(screen.getByTestId('active-status-schedule-3')).toHaveTextContent('inactive')
    })

    it('should pass isActive=false when no active schedule', () => {
      useActiveSchedule.mockReturnValue({
        data: { active_schedule: null },
      })

      render(<ScheduleList onViewSchedule={mockOnViewSchedule} />)

      expect(screen.getByTestId('active-status-schedule-1')).toHaveTextContent('inactive')
      expect(screen.getByTestId('active-status-schedule-2')).toHaveTextContent('inactive')
      expect(screen.getByTestId('active-status-schedule-3')).toHaveTextContent('inactive')
    })
  })

  describe('View Action', () => {
    it('should call onViewSchedule callback when view is clicked', async () => {
      const user = userEvent.setup()

      render(<ScheduleList onViewSchedule={mockOnViewSchedule} />)

      const viewButton = screen.getAllByRole('button', { name: /view/i })[0]
      await user.click(viewButton)

      expect(mockOnViewSchedule).toHaveBeenCalledWith(mockSchedules[0])
    })
  })

  describe('Toggle Enabled Action', () => {
    it('should call update mutation when enable/disable is toggled', async () => {
      const user = userEvent.setup()
      const mockUpdate = vi.fn()

      useUpdateSchedule.mockReturnValue({
        mutate: mockUpdate,
        isPending: false,
      })

      render(<ScheduleList onViewSchedule={mockOnViewSchedule} />)

      // Default mock schedule has enabled=true, so button is "Disable"
      const disableButton = screen.getAllByRole('button', { name: /disable/i })[0]
      await user.click(disableButton)

      expect(mockUpdate).toHaveBeenCalledWith(
        { id: 'schedule-1', data: { enabled: false } },
        expect.objectContaining({
          onSuccess: expect.any(Function),
          onError: expect.any(Function),
        })
      )
    })

    it('should show success toast on successful enable', async () => {
      const user = userEvent.setup()
      let onSuccessCallback

      const mockUpdate = vi.fn((variables, callbacks) => {
        onSuccessCallback = callbacks.onSuccess
      })

      useUpdateSchedule.mockReturnValue({
        mutate: mockUpdate,
        isPending: false,
      })

      // Schedule with enabled=false
      useSchedules.mockReturnValue({
        data: { schedules: [{ ...mockSchedules[0], enabled: false }] },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      })

      render(<ScheduleList onViewSchedule={mockOnViewSchedule} />)

      const enableButton = screen.getByRole('button', { name: /enable/i })
      await user.click(enableButton)

      // Simulate success
      onSuccessCallback()

      expect(toast.success).toHaveBeenCalledWith('Schedule enabled')
    })

    it('should show error toast on toggle failure', async () => {
      const user = userEvent.setup()
      let onErrorCallback

      const mockUpdate = vi.fn((variables, callbacks) => {
        onErrorCallback = callbacks.onError
      })

      useUpdateSchedule.mockReturnValue({
        mutate: mockUpdate,
        isPending: false,
      })

      render(<ScheduleList onViewSchedule={mockOnViewSchedule} />)

      const disableButton = screen.getAllByRole('button', { name: /disable/i })[0]
      await user.click(disableButton)

      // Simulate error
      const mockError = new Error('Update failed')
      onErrorCallback(mockError)

      expect(toast.error).toHaveBeenCalledWith('Failed to update schedule: Update failed')
    })
  })

  describe('Accessibility', () => {
    it('should have role="list" on schedule container', () => {
      render(<ScheduleList onViewSchedule={mockOnViewSchedule} />)

      expect(screen.getByRole('list')).toBeInTheDocument()
    })

    it('should have role="listitem" on each ScheduleCard', () => {
      render(<ScheduleList onViewSchedule={mockOnViewSchedule} />)

      const listItems = screen.getAllByRole('listitem')
      expect(listItems).toHaveLength(3)
    })
  })
})
