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

  describe('Auto-Generated Descriptions', () => {
    // These tests verify the auto-generated descriptions from generateScheduleDescription()
    // which combines action names with trigger descriptions (e.g., "Take Photo every 60 min")

    it('renders interval trigger with action name', () => {
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
      // generateRoutineName returns: "Take Photo every 60 min"
      expect(screen.getByText('Take Photo every 60 min')).toBeInTheDocument()
    })

    it('renders solar trigger with action name and offset', () => {
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
      // generateRoutineName returns: "Attract On at Sunset +30min"
      expect(screen.getByText('Attract On at Sunset +30min')).toBeInTheDocument()
    })

    it('renders solar trigger with negative offset', () => {
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
      // generateRoutineName returns: "Take Photo at Sunrise -15min"
      expect(screen.getByText('Take Photo at Sunrise -15min')).toBeInTheDocument()
    })

    it('renders solar trigger with zero offset', () => {
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
      // generateRoutineName returns: "Attract On at Sunset"
      expect(screen.getByText('Attract On at Sunset')).toBeInTheDocument()
    })

    it('renders moon phase trigger with action name', () => {
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
      // generateRoutineName returns: "Take Photo on full moon"
      expect(screen.getByText('Take Photo on full moon')).toBeInTheDocument()
    })

    it('renders fixed time trigger with action name', () => {
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
      // generateRoutineName returns: "Take Photo at 21:00"
      expect(screen.getByText('Take Photo at 21:00')).toBeInTheDocument()
    })

    it('renders sensor trigger (falls back to action only since sensor not in describeTrigger)', () => {
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
      // sensor is not in describeTrigger, so only action name is shown
      expect(screen.getByText('Take Photo')).toBeInTheDocument()
    })

    it('renders multi-routine summary with comma-separated list', () => {
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
      // 3 routines: all shown with comma separation
      expect(
        screen.getByText('Attract On at Dusk, Take Photo every 15 min, Attract Off at Dawn')
      ).toBeInTheDocument()
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
  // Routine Indicators (Issue #266 - show all actions with pipe separators)
  // ==========================================================================

  describe('Routine Indicators', () => {
    it('shows routine count', () => {
      const schedule = createSchedule({
        name: 'Test Schedule',
        routines: [
          {
            routine_id: 'r1',
            trigger: { trigger_type: 'fixed_time', time_of_day: '21:00' },
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
      expect(screen.getByText('1 routine')).toBeInTheDocument()
    })

    it('shows plural routine count for multiple routines', () => {
      const schedule = createSchedule({
        name: 'Test Schedule',
        routines: [
          {
            routine_id: 'r1',
            trigger: { trigger_type: 'solar', solar_event: 'sunset' },
            actions: [{ action_type: 'gpio', action_name: 'attract_on' }],
          },
          {
            routine_id: 'r2',
            trigger: { trigger_type: 'fixed_time', time_of_day: '21:00' },
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
      expect(screen.getByText('2 routines')).toBeInTheDocument()
    })

    it('renders action dots for all actions in a single routine', () => {
      const schedule = createSchedule({
        name: 'Test Schedule',
        routines: [
          {
            routine_id: 'r1',
            trigger: { trigger_type: 'fixed_time', time_of_day: '21:00' },
            actions: [
              { action_type: 'gpio', action_name: 'flash_on' },
              { action_type: 'camera', action_name: 'takephoto' },
              { action_type: 'gpio', action_name: 'flash_off' },
            ],
          },
        ],
      })
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
      // Should have 3 action dots (2 orange for gpio, 1 blue for camera)
      const orangeDots = container.querySelectorAll('.bg-orange-400')
      const blueDots = container.querySelectorAll('.bg-blue-400')
      expect(orangeDots).toHaveLength(2)
      expect(blueDots).toHaveLength(1)
    })

    it('renders pipe separators between multiple routines', () => {
      const schedule = createSchedule({
        name: 'Test Schedule',
        routines: [
          {
            routine_id: 'r1',
            trigger: { trigger_type: 'solar', solar_event: 'sunset' },
            actions: [{ action_type: 'gpio', action_name: 'attract_on' }],
          },
          {
            routine_id: 'r2',
            trigger: { trigger_type: 'fixed_time', time_of_day: '21:00' },
            actions: [{ action_type: 'camera', action_name: 'takephoto' }],
          },
          {
            routine_id: 'r3',
            trigger: { trigger_type: 'solar', solar_event: 'sunrise' },
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
      // Should have 2 pipe separators for 3 routines
      const pipes = screen.getAllByText('|')
      expect(pipes).toHaveLength(2)
    })

    it('does not render pipe separator for single routine', () => {
      const schedule = createSchedule({
        name: 'Test Schedule',
        routines: [
          {
            routine_id: 'r1',
            trigger: { trigger_type: 'fixed_time', time_of_day: '21:00' },
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
      expect(screen.queryByText('|')).not.toBeInTheDocument()
    })

    it('shows correct colors for different action types', () => {
      const schedule = createSchedule({
        name: 'Test Schedule',
        routines: [
          {
            routine_id: 'r1',
            trigger: { trigger_type: 'fixed_time', time_of_day: '21:00' },
            actions: [
              { action_type: 'gpio', action_name: 'attract_on' },
              { action_type: 'camera', action_name: 'takephoto' },
              { action_type: 'gps_sync', action_name: 'gps_sync' },
            ],
          },
        ],
      })
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
      // Orange for GPIO, Blue for camera, Green for GPS
      expect(container.querySelectorAll('.bg-orange-400')).toHaveLength(1)
      expect(container.querySelectorAll('.bg-blue-400')).toHaveLength(1)
      expect(container.querySelectorAll('.bg-green-400')).toHaveLength(1)
    })

    it('action dots have title attributes for tooltips', () => {
      const schedule = createSchedule({
        name: 'Test Schedule',
        routines: [
          {
            routine_id: 'r1',
            trigger: { trigger_type: 'fixed_time', time_of_day: '21:00' },
            actions: [{ action_type: 'gpio', action_name: 'attract_on' }],
          },
        ],
      })
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
      const actionDot = container.querySelector('.bg-orange-400')
      expect(actionDot).toHaveAttribute('title', 'attract_on')
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
