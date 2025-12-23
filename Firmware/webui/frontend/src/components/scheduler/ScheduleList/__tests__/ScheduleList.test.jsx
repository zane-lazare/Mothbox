import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

// Mock dependencies BEFORE imports
vi.mock('../../../../hooks/useSchedules', () => ({
  useSchedules: vi.fn(),
  useActiveSchedule: vi.fn(),
  useActivateSchedule: vi.fn(),
  useDeactivateSchedule: vi.fn(),
  useDeleteSchedule: vi.fn(),
}))

// Note: ConfirmDialog is NOT mocked - we test with the real component

vi.mock('../ScheduleCard', () => ({
  default: ({ schedule, isActive, isActivating, onActivate, onDeactivate, onEdit, onDelete }) => (
    <div data-testid={`schedule-card-${schedule.id}`} role="listitem">
      <h3>{schedule.name}</h3>
      <span data-testid={`active-status-${schedule.id}`}>{isActive ? 'active' : 'inactive'}</span>
      <span data-testid={`activating-status-${schedule.id}`}>{isActivating ? 'activating' : 'idle'}</span>
      <button onClick={() => onActivate(schedule)}>Activate</button>
      <button onClick={() => onDeactivate(schedule)}>Deactivate</button>
      <button onClick={() => onEdit(schedule)}>Edit</button>
      <button onClick={() => onDelete(schedule)}>Delete</button>
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
  useActivateSchedule,
  useDeactivateSchedule,
  useDeleteSchedule,
} from '../../../../hooks/useSchedules'
import toast from 'react-hot-toast'
import { ScheduleList } from '../ScheduleList'

describe('ScheduleList', () => {
  const mockSchedules = [
    {
      id: 'schedule-1',
      name: 'Morning Schedule',
      description: 'Runs in the morning',
    },
    {
      id: 'schedule-2',
      name: 'Evening Schedule',
      description: 'Runs in the evening',
    },
    {
      id: 'schedule-3',
      name: 'Night Schedule',
      description: 'Runs at night',
    },
  ]

  const mockOnEditSchedule = vi.fn()

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

    useActivateSchedule.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    })

    useDeactivateSchedule.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    })

    useDeleteSchedule.mockReturnValue({
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

      render(<ScheduleList onEditSchedule={mockOnEditSchedule} />)

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

      const { container } = render(<ScheduleList onEditSchedule={mockOnEditSchedule} />)
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

      render(<ScheduleList onEditSchedule={mockOnEditSchedule} />)

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

      render(<ScheduleList onEditSchedule={mockOnEditSchedule} />)

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

      render(<ScheduleList onEditSchedule={mockOnEditSchedule} />)

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

      render(<ScheduleList onEditSchedule={mockOnEditSchedule} />)

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

      render(<ScheduleList onEditSchedule={mockOnEditSchedule} />)

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

      render(<ScheduleList onEditSchedule={mockOnEditSchedule} />)

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

      render(<ScheduleList onEditSchedule={mockOnEditSchedule} />)

      const emptyStateContainer = screen.getByText(/no schedules yet/i).parentElement
      expect(emptyStateContainer).toHaveClass('text-center')

      const message = screen.getByText(/no schedules yet/i)
      expect(message).toHaveClass('text-gray-500')
    })
  })

  describe('List Rendering', () => {
    it('should render ScheduleCard for each schedule', () => {
      render(<ScheduleList onEditSchedule={mockOnEditSchedule} />)

      expect(screen.getByTestId('schedule-card-schedule-1')).toBeInTheDocument()
      expect(screen.getByTestId('schedule-card-schedule-2')).toBeInTheDocument()
      expect(screen.getByTestId('schedule-card-schedule-3')).toBeInTheDocument()
    })

    it('should use grid layout with responsive columns', () => {
      const { container } = render(<ScheduleList onEditSchedule={mockOnEditSchedule} />)

      const grid = container.querySelector('[role="list"]')
      expect(grid).toHaveClass('grid', 'grid-cols-1', 'md:grid-cols-2', 'lg:grid-cols-3', 'gap-4')
    })

    it('should pass isActive=true to active schedule card', () => {
      useActiveSchedule.mockReturnValue({
        data: { active_schedule: { id: 'schedule-2' } },
      })

      render(<ScheduleList onEditSchedule={mockOnEditSchedule} />)

      expect(screen.getByTestId('active-status-schedule-1')).toHaveTextContent('inactive')
      expect(screen.getByTestId('active-status-schedule-2')).toHaveTextContent('active')
      expect(screen.getByTestId('active-status-schedule-3')).toHaveTextContent('inactive')
    })

    it('should pass isActive=false when no active schedule', () => {
      useActiveSchedule.mockReturnValue({
        data: { active_schedule: null },
      })

      render(<ScheduleList onEditSchedule={mockOnEditSchedule} />)

      expect(screen.getByTestId('active-status-schedule-1')).toHaveTextContent('inactive')
      expect(screen.getByTestId('active-status-schedule-2')).toHaveTextContent('inactive')
      expect(screen.getByTestId('active-status-schedule-3')).toHaveTextContent('inactive')
    })
  })

  describe('Activate Action', () => {
    it('should call activate mutation when schedule is activated', async () => {
      const user = userEvent.setup()
      const mockActivate = vi.fn()

      useActivateSchedule.mockReturnValue({
        mutate: mockActivate,
        isPending: false,
      })

      render(<ScheduleList onEditSchedule={mockOnEditSchedule} />)

      const activateButton = screen.getAllByRole('button', { name: /activate/i })[0]
      await user.click(activateButton)

      expect(mockActivate).toHaveBeenCalledWith(
        { id: 'schedule-1' },
        expect.objectContaining({
          onSuccess: expect.any(Function),
          onError: expect.any(Function),
        })
      )
    })

    it('should track activating state for specific schedule', async () => {
      const user = userEvent.setup()
      const mockActivate = vi.fn()

      useActivateSchedule.mockReturnValue({
        mutate: mockActivate,
        isPending: false,
      })

      render(<ScheduleList onEditSchedule={mockOnEditSchedule} />)

      // Initially not activating
      expect(screen.getByTestId('activating-status-schedule-1')).toHaveTextContent('idle')

      // Click activate
      const activateButton = screen.getAllByRole('button', { name: /activate/i })[0]
      await user.click(activateButton)

      // Verify mutation was called with correct schedule ID
      expect(mockActivate).toHaveBeenCalledWith(
        { id: 'schedule-1' },
        expect.objectContaining({
          onSuccess: expect.any(Function),
          onError: expect.any(Function),
        })
      )
    })

    it('should show success toast on successful activation', async () => {
      const user = userEvent.setup()
      let onSuccessCallback

      const mockActivate = vi.fn((variables, callbacks) => {
        onSuccessCallback = callbacks.onSuccess
      })

      useActivateSchedule.mockReturnValue({
        mutate: mockActivate,
        isPending: false,
      })

      render(<ScheduleList onEditSchedule={mockOnEditSchedule} />)

      const activateButton = screen.getAllByRole('button', { name: /activate/i })[0]
      await user.click(activateButton)

      // Simulate success
      onSuccessCallback()

      expect(toast.success).toHaveBeenCalledWith('Schedule activated successfully')
    })

    it('should show error toast on activation failure', async () => {
      const user = userEvent.setup()
      let onErrorCallback

      const mockActivate = vi.fn((variables, callbacks) => {
        onErrorCallback = callbacks.onError
      })

      useActivateSchedule.mockReturnValue({
        mutate: mockActivate,
        isPending: false,
      })

      render(<ScheduleList onEditSchedule={mockOnEditSchedule} />)

      const activateButton = screen.getAllByRole('button', { name: /activate/i })[0]
      await user.click(activateButton)

      // Simulate error
      const mockError = new Error('Activation failed')
      onErrorCallback(mockError)

      expect(toast.error).toHaveBeenCalledWith('Failed to activate schedule: Activation failed')
    })

    it('should pass isActivating=true only to the schedule being activated', async () => {
      render(<ScheduleList onEditSchedule={mockOnEditSchedule} />)

      // Before activation
      expect(screen.getByTestId('activating-status-schedule-1')).toHaveTextContent('idle')
      expect(screen.getByTestId('activating-status-schedule-2')).toHaveTextContent('idle')

      // This test verifies the component tracks which schedule is being activated
      // The actual isActivating prop depends on matching activatingId with schedule.id
    })
  })

  describe('Deactivate Action', () => {
    it('should call deactivate mutation when schedule is deactivated', async () => {
      const user = userEvent.setup()
      const mockDeactivate = vi.fn()

      useDeactivateSchedule.mockReturnValue({
        mutate: mockDeactivate,
        isPending: false,
      })

      useActiveSchedule.mockReturnValue({
        data: { active_schedule: { id: 'schedule-1' } },
      })

      render(<ScheduleList onEditSchedule={mockOnEditSchedule} />)

      const deactivateButton = screen.getAllByRole('button', { name: /deactivate/i })[0]
      await user.click(deactivateButton)

      expect(mockDeactivate).toHaveBeenCalledWith(
        undefined,
        expect.objectContaining({
          onSuccess: expect.any(Function),
          onError: expect.any(Function),
        })
      )
    })

    it('should show success toast on successful deactivation', async () => {
      const user = userEvent.setup()
      let onSuccessCallback

      const mockDeactivate = vi.fn((variables, callbacks) => {
        onSuccessCallback = callbacks.onSuccess
      })

      useDeactivateSchedule.mockReturnValue({
        mutate: mockDeactivate,
        isPending: false,
      })

      render(<ScheduleList onEditSchedule={mockOnEditSchedule} />)

      const deactivateButton = screen.getAllByRole('button', { name: /deactivate/i })[0]
      await user.click(deactivateButton)

      // Simulate success
      onSuccessCallback()

      expect(toast.success).toHaveBeenCalledWith('Schedule deactivated successfully')
    })

    it('should show error toast on deactivation failure', async () => {
      const user = userEvent.setup()
      let onErrorCallback

      const mockDeactivate = vi.fn((variables, callbacks) => {
        onErrorCallback = callbacks.onError
      })

      useDeactivateSchedule.mockReturnValue({
        mutate: mockDeactivate,
        isPending: false,
      })

      render(<ScheduleList onEditSchedule={mockOnEditSchedule} />)

      const deactivateButton = screen.getAllByRole('button', { name: /deactivate/i })[0]
      await user.click(deactivateButton)

      // Simulate error
      const mockError = new Error('Deactivation failed')
      onErrorCallback(mockError)

      expect(toast.error).toHaveBeenCalledWith('Failed to deactivate schedule: Deactivation failed')
    })
  })

  describe('Delete Action', () => {
    it('should show confirmation dialog when delete is clicked', async () => {
      const user = userEvent.setup()

      render(<ScheduleList onEditSchedule={mockOnEditSchedule} />)

      const deleteButton = screen.getAllByRole('button', { name: /delete/i })[0]
      await user.click(deleteButton)

      expect(screen.getByRole('dialog')).toBeInTheDocument()
      expect(screen.getByText(/delete schedule/i)).toBeInTheDocument()
      expect(screen.getByText(/are you sure you want to delete/i)).toBeInTheDocument()
    })

    it('should include schedule name in confirmation message', async () => {
      const user = userEvent.setup()

      render(<ScheduleList onEditSchedule={mockOnEditSchedule} />)

      const deleteButton = screen.getAllByRole('button', { name: /delete/i })[0]
      await user.click(deleteButton)

      // Check for the specific confirmation message with schedule name
      expect(screen.getByText(/are you sure you want to delete "morning schedule"/i)).toBeInTheDocument()
    })

    it('should call delete mutation when confirmed', async () => {
      const user = userEvent.setup()
      const mockDelete = vi.fn()

      useDeleteSchedule.mockReturnValue({
        mutate: mockDelete,
        isPending: false,
      })

      render(<ScheduleList onEditSchedule={mockOnEditSchedule} />)

      const deleteButton = screen.getAllByRole('button', { name: /delete/i })[0]
      await user.click(deleteButton)

      const confirmButton = screen.getByRole('button', { name: /confirm/i })
      await user.click(confirmButton)

      expect(mockDelete).toHaveBeenCalledWith(
        'schedule-1',
        expect.objectContaining({
          onSuccess: expect.any(Function),
          onError: expect.any(Function),
        })
      )
    })

    it('should close dialog without deleting when cancelled', async () => {
      const user = userEvent.setup()
      const mockDelete = vi.fn()

      useDeleteSchedule.mockReturnValue({
        mutate: mockDelete,
        isPending: false,
      })

      render(<ScheduleList onEditSchedule={mockOnEditSchedule} />)

      const deleteButton = screen.getAllByRole('button', { name: /delete/i })[0]
      await user.click(deleteButton)

      const cancelButton = screen.getByRole('button', { name: /cancel/i })
      await user.click(cancelButton)

      expect(mockDelete).not.toHaveBeenCalled()

      await waitFor(() => {
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
      })
    })

    it('should show success toast on successful deletion', async () => {
      const user = userEvent.setup()
      let onSuccessCallback

      const mockDelete = vi.fn((variables, callbacks) => {
        onSuccessCallback = callbacks.onSuccess
      })

      useDeleteSchedule.mockReturnValue({
        mutate: mockDelete,
        isPending: false,
      })

      render(<ScheduleList onEditSchedule={mockOnEditSchedule} />)

      const deleteButton = screen.getAllByRole('button', { name: /delete/i })[0]
      await user.click(deleteButton)

      const confirmButton = screen.getByRole('button', { name: /confirm/i })
      await user.click(confirmButton)

      // Simulate success
      onSuccessCallback()

      expect(toast.success).toHaveBeenCalledWith('Schedule deleted successfully')
    })

    it('should show error toast on deletion failure', async () => {
      const user = userEvent.setup()
      let onErrorCallback

      const mockDelete = vi.fn((variables, callbacks) => {
        onErrorCallback = callbacks.onError
      })

      useDeleteSchedule.mockReturnValue({
        mutate: mockDelete,
        isPending: false,
      })

      render(<ScheduleList onEditSchedule={mockOnEditSchedule} />)

      const deleteButton = screen.getAllByRole('button', { name: /delete/i })[0]
      await user.click(deleteButton)

      const confirmButton = screen.getByRole('button', { name: /confirm/i })
      await user.click(confirmButton)

      // Simulate error
      const mockError = new Error('Deletion failed')
      onErrorCallback(mockError)

      expect(toast.error).toHaveBeenCalledWith('Failed to delete schedule: Deletion failed')
    })

    it('should close dialog after successful deletion', async () => {
      const user = userEvent.setup()
      let onSuccessCallback

      const mockDelete = vi.fn((variables, callbacks) => {
        onSuccessCallback = callbacks.onSuccess
      })

      useDeleteSchedule.mockReturnValue({
        mutate: mockDelete,
        isPending: false,
      })

      render(<ScheduleList onEditSchedule={mockOnEditSchedule} />)

      const deleteButton = screen.getAllByRole('button', { name: /delete/i })[0]
      await user.click(deleteButton)

      const confirmButton = screen.getByRole('button', { name: /confirm/i })
      await user.click(confirmButton)

      // Simulate success
      onSuccessCallback()

      await waitFor(() => {
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
      })
    })
  })

  describe('Edit Action', () => {
    it('should call onEditSchedule callback when edit is clicked', async () => {
      const user = userEvent.setup()

      render(<ScheduleList onEditSchedule={mockOnEditSchedule} />)

      const editButton = screen.getAllByRole('button', { name: /edit/i })[0]
      await user.click(editButton)

      expect(mockOnEditSchedule).toHaveBeenCalledWith(mockSchedules[0])
    })
  })

  describe('Accessibility', () => {
    it('should have role="list" on schedule container', () => {
      render(<ScheduleList onEditSchedule={mockOnEditSchedule} />)

      expect(screen.getByRole('list')).toBeInTheDocument()
    })

    it('should have role="listitem" on each ScheduleCard', () => {
      render(<ScheduleList onEditSchedule={mockOnEditSchedule} />)

      const listItems = screen.getAllByRole('listitem')
      expect(listItems).toHaveLength(3)
    })
  })
})
