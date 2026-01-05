/**
 * Tests for ScheduleCard component (Issue #266)
 *
 * ScheduleCard displays a schedule with trigger information, active status,
 * and action buttons (Edit, Activate/Deactivate, Delete).
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ScheduleCard from '../ScheduleCard'

describe('ScheduleCard', () => {
  const mockOnEdit = vi.fn()
  const mockOnActivate = vi.fn()
  const mockOnDeactivate = vi.fn()
  const mockOnDelete = vi.fn()

  beforeEach(() => {
    mockOnEdit.mockClear()
    mockOnActivate.mockClear()
    mockOnDeactivate.mockClear()
    mockOnDelete.mockClear()
  })

  // ==========================================================================
  // Helper to create Schema 3.0 schedule fixtures
  // ==========================================================================

  const createSchedule = (overrides = {}) => ({
    schedule_id: 'sched-1',
    name: 'Test Schedule',
    routines: [
      {
        routine_id: 'routine-1',
        trigger: { trigger_type: 'fixed_time', time_of_day: '21:00' },
        actions: [{ action_type: 'camera', action_name: 'takephoto' }],
      },
    ],
    ...overrides,
  })

  // ==========================================================================
  // Rendering Tests
  // ==========================================================================

  describe('Rendering', () => {
    it('renders schedule name', () => {
      const schedule = createSchedule({
        name: 'Summer Moth Survey',
        description: 'Nightly captures',
      })
      render(
        <ScheduleCard
          schedule={schedule}
          isActive={false}
          onEdit={mockOnEdit}
          onActivate={mockOnActivate}
          onDeactivate={mockOnDeactivate}
          onDelete={mockOnDelete}
        />
      )
      expect(screen.getByText('Summer Moth Survey')).toBeInTheDocument()
    })

    it('renders schedule description', () => {
      const schedule = createSchedule({
        name: 'Summer Moth Survey',
        description: 'Nightly captures',
      })
      render(
        <ScheduleCard
          schedule={schedule}
          isActive={false}
          onEdit={mockOnEdit}
          onActivate={mockOnActivate}
          onDeactivate={mockOnDeactivate}
          onDelete={mockOnDelete}
        />
      )
      expect(screen.getByText('Nightly captures')).toBeInTheDocument()
    })

    it('handles missing description gracefully', () => {
      const schedule = createSchedule({ name: 'Summer Moth Survey' })
      render(
        <ScheduleCard
          schedule={schedule}
          isActive={false}
          onEdit={mockOnEdit}
          onActivate={mockOnActivate}
          onDeactivate={mockOnDeactivate}
          onDelete={mockOnDelete}
        />
      )
      expect(screen.getByText('Summer Moth Survey')).toBeInTheDocument()
    })

    it('shows ActiveScheduleBadge when isActive is true', () => {
      const schedule = createSchedule({ name: 'Summer Moth Survey' })
      render(
        <ScheduleCard
          schedule={schedule}
          isActive={true}
          onEdit={mockOnEdit}
          onActivate={mockOnActivate}
          onDeactivate={mockOnDeactivate}
          onDelete={mockOnDelete}
        />
      )
      expect(screen.getByText('Active')).toBeInTheDocument()
    })

    it('does not show ActiveScheduleBadge when isActive is false', () => {
      const schedule = createSchedule({ name: 'Summer Moth Survey' })
      render(
        <ScheduleCard
          schedule={schedule}
          isActive={false}
          onEdit={mockOnEdit}
          onActivate={mockOnActivate}
          onDeactivate={mockOnDeactivate}
          onDelete={mockOnDelete}
        />
      )
      expect(screen.queryByText('Active')).not.toBeInTheDocument()
    })
  })

  // ==========================================================================
  // Trigger Summaries (Schema 3.0 - uses routines)
  // ==========================================================================

  describe('Trigger Summaries', () => {
    it('renders interval trigger summary', () => {
      const schedule = createSchedule({
        name: 'Interval Schedule',
        routines: [
          {
            routine_id: 'r1',
            trigger: {
              trigger_type: 'interval',
              interval_minutes: 60,
              time_window: { start_time: '21:00', end_time: '05:00' },
            },
            actions: [{ action_type: 'camera', action_name: 'takephoto' }],
          },
        ],
      })
      render(
        <ScheduleCard
          schedule={schedule}
          isActive={false}
          onEdit={mockOnEdit}
          onActivate={mockOnActivate}
          onDeactivate={mockOnDeactivate}
          onDelete={mockOnDelete}
        />
      )
      expect(screen.getByText('Every 60 min, 21:00 - 05:00')).toBeInTheDocument()
    })

    it('renders solar trigger summary', () => {
      const schedule = createSchedule({
        name: 'Solar Schedule',
        routines: [
          {
            routine_id: 'r1',
            trigger: {
              trigger_type: 'solar',
              solar_event: 'sunset',
              offset_minutes: 30,
            },
            actions: [{ action_type: 'gpio', action_name: 'attract_on' }],
          },
        ],
      })
      render(
        <ScheduleCard
          schedule={schedule}
          isActive={false}
          onEdit={mockOnEdit}
          onActivate={mockOnActivate}
          onDeactivate={mockOnDeactivate}
          onDelete={mockOnDelete}
        />
      )
      expect(screen.getByText('At sunset +30 min')).toBeInTheDocument()
    })

    it('renders solar trigger summary with negative offset', () => {
      const schedule = createSchedule({
        name: 'Solar Schedule',
        routines: [
          {
            routine_id: 'r1',
            trigger: {
              trigger_type: 'solar',
              solar_event: 'sunrise',
              offset_minutes: -15,
            },
            actions: [{ action_type: 'camera', action_name: 'takephoto' }],
          },
        ],
      })
      render(
        <ScheduleCard
          schedule={schedule}
          isActive={false}
          onEdit={mockOnEdit}
          onActivate={mockOnActivate}
          onDeactivate={mockOnDeactivate}
          onDelete={mockOnDelete}
        />
      )
      expect(screen.getByText('At sunrise -15 min')).toBeInTheDocument()
    })

    it('renders solar trigger summary with zero offset', () => {
      const schedule = createSchedule({
        name: 'Solar Schedule',
        routines: [
          {
            routine_id: 'r1',
            trigger: {
              trigger_type: 'solar',
              solar_event: 'sunset',
              offset_minutes: 0,
            },
            actions: [{ action_type: 'gpio', action_name: 'attract_on' }],
          },
        ],
      })
      render(
        <ScheduleCard
          schedule={schedule}
          isActive={false}
          onEdit={mockOnEdit}
          onActivate={mockOnActivate}
          onDeactivate={mockOnDeactivate}
          onDelete={mockOnDelete}
        />
      )
      expect(screen.getByText('At sunset')).toBeInTheDocument()
    })

    it('renders moon phase trigger summary', () => {
      const schedule = createSchedule({
        name: 'Moon Phase Schedule',
        routines: [
          {
            routine_id: 'r1',
            trigger: {
              trigger_type: 'moon_phase',
              moon_phase: 'full',
              time_of_day: '20:00',
            },
            actions: [{ action_type: 'camera', action_name: 'takephoto' }],
          },
        ],
      })
      render(
        <ScheduleCard
          schedule={schedule}
          isActive={false}
          onEdit={mockOnEdit}
          onActivate={mockOnActivate}
          onDeactivate={mockOnDeactivate}
          onDelete={mockOnDelete}
        />
      )
      expect(screen.getByText('Full Moon, at 20:00')).toBeInTheDocument()
    })

    it('renders fixed time trigger summary', () => {
      const schedule = createSchedule({
        name: 'Fixed Time Schedule',
        routines: [
          {
            routine_id: 'r1',
            trigger: {
              trigger_type: 'fixed_time',
              time_of_day: '21:00',
            },
            actions: [{ action_type: 'camera', action_name: 'takephoto' }],
          },
        ],
      })
      render(
        <ScheduleCard
          schedule={schedule}
          isActive={false}
          onEdit={mockOnEdit}
          onActivate={mockOnActivate}
          onDeactivate={mockOnDeactivate}
          onDelete={mockOnDelete}
        />
      )
      expect(screen.getByText('Daily at 21:00')).toBeInTheDocument()
    })

    it('renders sensor trigger summary', () => {
      const schedule = createSchedule({
        name: 'Sensor Schedule',
        routines: [
          {
            routine_id: 'r1',
            trigger: {
              trigger_type: 'sensor',
              sensor_type: 'light',
              comparison: 'lt',
              threshold: 100,
            },
            actions: [{ action_type: 'camera', action_name: 'takephoto' }],
          },
        ],
      })
      render(
        <ScheduleCard
          schedule={schedule}
          isActive={false}
          onEdit={mockOnEdit}
          onActivate={mockOnActivate}
          onDeactivate={mockOnDeactivate}
          onDelete={mockOnDelete}
        />
      )
      expect(screen.getByText('When light < 100')).toBeInTheDocument()
    })

    it('renders multi-routine summary with count indicator', () => {
      const schedule = createSchedule({
        name: 'Overnight Moth Survey',
        routines: [
          {
            routine_id: 'r1',
            trigger: { trigger_type: 'solar', solar_event: 'dusk', offset_minutes: 0 },
            actions: [{ action_type: 'gpio', action_name: 'attract_on' }],
          },
          {
            routine_id: 'r2',
            trigger: {
              trigger_type: 'interval',
              interval_minutes: 15,
              time_window: { start_time: 'sunset', end_time: 'sunrise' },
            },
            actions: [{ action_type: 'camera', action_name: 'takephoto' }],
          },
          {
            routine_id: 'r3',
            trigger: { trigger_type: 'solar', solar_event: 'dawn', offset_minutes: 0 },
            actions: [{ action_type: 'gpio', action_name: 'attract_off' }],
          },
        ],
      })
      render(
        <ScheduleCard
          schedule={schedule}
          isActive={false}
          onEdit={mockOnEdit}
          onActivate={mockOnActivate}
          onDeactivate={mockOnDeactivate}
          onDelete={mockOnDelete}
        />
      )
      expect(screen.getByText('At dusk (+2 more)')).toBeInTheDocument()
    })

    it('handles schedule with no routines gracefully', () => {
      const schedule = createSchedule({
        name: 'Empty Schedule',
        routines: [],
      })
      render(
        <ScheduleCard
          schedule={schedule}
          isActive={false}
          onEdit={mockOnEdit}
          onActivate={mockOnActivate}
          onDeactivate={mockOnDeactivate}
          onDelete={mockOnDelete}
        />
      )
      // Should render without crashing, empty summary
      expect(screen.getByText('Empty Schedule')).toBeInTheDocument()
    })
  })

  // ==========================================================================
  // Action Buttons
  // ==========================================================================

  describe('Action Buttons', () => {
    it('renders Edit button', () => {
      const schedule = createSchedule()
      render(
        <ScheduleCard
          schedule={schedule}
          isActive={false}
          onEdit={mockOnEdit}
          onActivate={mockOnActivate}
          onDeactivate={mockOnDeactivate}
          onDelete={mockOnDelete}
        />
      )
      expect(screen.getByRole('button', { name: /edit/i })).toBeInTheDocument()
    })

    it('calls onEdit when Edit button is clicked', async () => {
      const schedule = createSchedule()
      const user = userEvent.setup()
      render(
        <ScheduleCard
          schedule={schedule}
          isActive={false}
          onEdit={mockOnEdit}
          onActivate={mockOnActivate}
          onDeactivate={mockOnDeactivate}
          onDelete={mockOnDelete}
        />
      )
      const editButton = screen.getByRole('button', { name: /edit/i })
      await user.click(editButton)
      expect(mockOnEdit).toHaveBeenCalledTimes(1)
      expect(mockOnEdit).toHaveBeenCalledWith(schedule)
    })

    it('renders Activate button when schedule is not active', () => {
      const schedule = createSchedule()
      render(
        <ScheduleCard
          schedule={schedule}
          isActive={false}
          onEdit={mockOnEdit}
          onActivate={mockOnActivate}
          onDeactivate={mockOnDeactivate}
          onDelete={mockOnDelete}
        />
      )
      expect(screen.getByRole('button', { name: /activate/i })).toBeInTheDocument()
      expect(screen.queryByRole('button', { name: /deactivate/i })).not.toBeInTheDocument()
    })

    it('renders Deactivate button when schedule is active', () => {
      const schedule = createSchedule()
      render(
        <ScheduleCard
          schedule={schedule}
          isActive={true}
          onEdit={mockOnEdit}
          onActivate={mockOnActivate}
          onDeactivate={mockOnDeactivate}
          onDelete={mockOnDelete}
        />
      )
      expect(screen.getByRole('button', { name: /deactivate/i })).toBeInTheDocument()
      expect(screen.queryByRole('button', { name: /^activate$/i })).not.toBeInTheDocument()
    })

    it('calls onActivate when Activate button is clicked', async () => {
      const schedule = createSchedule()
      const user = userEvent.setup()
      render(
        <ScheduleCard
          schedule={schedule}
          isActive={false}
          onEdit={mockOnEdit}
          onActivate={mockOnActivate}
          onDeactivate={mockOnDeactivate}
          onDelete={mockOnDelete}
        />
      )
      const activateButton = screen.getByRole('button', { name: /activate/i })
      await user.click(activateButton)
      expect(mockOnActivate).toHaveBeenCalledTimes(1)
      expect(mockOnActivate).toHaveBeenCalledWith(schedule)
    })

    it('calls onDeactivate when Deactivate button is clicked', async () => {
      const schedule = createSchedule()
      const user = userEvent.setup()
      render(
        <ScheduleCard
          schedule={schedule}
          isActive={true}
          onEdit={mockOnEdit}
          onActivate={mockOnActivate}
          onDeactivate={mockOnDeactivate}
          onDelete={mockOnDelete}
        />
      )
      const deactivateButton = screen.getByRole('button', { name: /deactivate/i })
      await user.click(deactivateButton)
      expect(mockOnDeactivate).toHaveBeenCalledTimes(1)
      expect(mockOnDeactivate).toHaveBeenCalledWith(schedule)
    })

    it('renders Delete button', () => {
      const schedule = createSchedule()
      render(
        <ScheduleCard
          schedule={schedule}
          isActive={false}
          onEdit={mockOnEdit}
          onActivate={mockOnActivate}
          onDeactivate={mockOnDeactivate}
          onDelete={mockOnDelete}
        />
      )
      expect(screen.getByRole('button', { name: /delete/i })).toBeInTheDocument()
    })

    it('calls onDelete when Delete button is clicked', async () => {
      const schedule = createSchedule()
      const user = userEvent.setup()
      render(
        <ScheduleCard
          schedule={schedule}
          isActive={false}
          onEdit={mockOnEdit}
          onActivate={mockOnActivate}
          onDeactivate={mockOnDeactivate}
          onDelete={mockOnDelete}
        />
      )
      const deleteButton = screen.getByRole('button', { name: /delete/i })
      await user.click(deleteButton)
      expect(mockOnDelete).toHaveBeenCalledTimes(1)
      expect(mockOnDelete).toHaveBeenCalledWith(schedule)
    })
  })

  // ==========================================================================
  // Loading States
  // ==========================================================================

  describe('Loading States', () => {
    it('disables and shows "Editing..." on Edit button when isEditing is true', () => {
      const schedule = createSchedule()
      render(
        <ScheduleCard
          schedule={schedule}
          isActive={false}
          onEdit={mockOnEdit}
          onActivate={mockOnActivate}
          onDeactivate={mockOnDeactivate}
          onDelete={mockOnDelete}
          isEditing={true}
        />
      )
      const editButton = screen.getByRole('button', { name: /editing/i })
      expect(editButton).toBeDisabled()
      expect(editButton).toHaveTextContent('Editing...')
    })

    it('disables and shows "Activating..." on Activate button when isActivating is true', () => {
      const schedule = createSchedule()
      render(
        <ScheduleCard
          schedule={schedule}
          isActive={false}
          onEdit={mockOnEdit}
          onActivate={mockOnActivate}
          onDeactivate={mockOnDeactivate}
          onDelete={mockOnDelete}
          isActivating={true}
        />
      )
      const activateButton = screen.getByRole('button', { name: /activating/i })
      expect(activateButton).toBeDisabled()
      expect(activateButton).toHaveTextContent('Activating...')
    })

    it('disables and shows "Deactivating..." on Deactivate button when isDeactivating is true', () => {
      const schedule = createSchedule()
      render(
        <ScheduleCard
          schedule={schedule}
          isActive={true}
          onEdit={mockOnEdit}
          onActivate={mockOnActivate}
          onDeactivate={mockOnDeactivate}
          onDelete={mockOnDelete}
          isDeactivating={true}
        />
      )
      const deactivateButton = screen.getByRole('button', { name: /deactivating/i })
      expect(deactivateButton).toBeDisabled()
      expect(deactivateButton).toHaveTextContent('Deactivating...')
    })

    it('disables and shows "Deleting..." on Delete button when isDeleting is true', () => {
      const schedule = createSchedule()
      render(
        <ScheduleCard
          schedule={schedule}
          isActive={false}
          onEdit={mockOnEdit}
          onActivate={mockOnActivate}
          onDeactivate={mockOnDeactivate}
          onDelete={mockOnDelete}
          isDeleting={true}
        />
      )
      const deleteButton = screen.getByRole('button', { name: /deleting/i })
      expect(deleteButton).toBeDisabled()
      expect(deleteButton).toHaveTextContent('Deleting...')
    })

    it('disables all buttons when multiple loading states are true', () => {
      const schedule = createSchedule()
      render(
        <ScheduleCard
          schedule={schedule}
          isActive={false}
          onEdit={mockOnEdit}
          onActivate={mockOnActivate}
          onDeactivate={mockOnDeactivate}
          onDelete={mockOnDelete}
          isActivating={true}
          isDeleting={true}
        />
      )
      const buttons = screen.getAllByRole('button')
      buttons.forEach((button) => {
        expect(button).toBeDisabled()
      })
    })
  })

  // ==========================================================================
  // Accessibility
  // ==========================================================================

  describe('Accessibility', () => {
    it('has role="article"', () => {
      const schedule = createSchedule()
      render(
        <ScheduleCard
          schedule={schedule}
          isActive={false}
          onEdit={mockOnEdit}
          onActivate={mockOnActivate}
          onDeactivate={mockOnDeactivate}
          onDelete={mockOnDelete}
        />
      )
      expect(screen.getByRole('article')).toBeInTheDocument()
    })

    it('has aria-labelledby pointing to schedule name', () => {
      const schedule = createSchedule()
      const { container } = render(
        <ScheduleCard
          schedule={schedule}
          isActive={false}
          onEdit={mockOnEdit}
          onActivate={mockOnActivate}
          onDeactivate={mockOnDeactivate}
          onDelete={mockOnDelete}
        />
      )
      const article = screen.getByRole('article')
      const labelledBy = article.getAttribute('aria-labelledby')
      expect(labelledBy).toBeTruthy()
      const nameElement = container.querySelector(`#${labelledBy}`)
      expect(nameElement).toBeInTheDocument()
      expect(nameElement).toHaveTextContent('Test Schedule')
    })
  })

  // ==========================================================================
  // Dark Mode
  // ==========================================================================

  describe('Dark Mode', () => {
    it('has dark mode classes applied', () => {
      const schedule = createSchedule()
      render(
        <ScheduleCard
          schedule={schedule}
          isActive={false}
          onEdit={mockOnEdit}
          onActivate={mockOnActivate}
          onDeactivate={mockOnDeactivate}
          onDelete={mockOnDelete}
        />
      )
      const article = screen.getByRole('article')
      expect(article).toHaveClass('dark:bg-gray-800')
      expect(article).toHaveClass('dark:border-gray-700')
    })
  })
})
