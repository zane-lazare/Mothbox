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
  // Rendering Tests
  // ==========================================================================

  describe('Rendering', () => {
    it('renders schedule name', () => {
      const schedule = {
        schedule_id: 'sched-1',
        name: 'Summer Moth Survey',
        description: 'Nightly captures',
        trigger: { trigger_type: 'fixed_time', time_of_day: '21:00' },
      }
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
      const schedule = {
        schedule_id: 'sched-1',
        name: 'Summer Moth Survey',
        description: 'Nightly captures',
        trigger: { trigger_type: 'fixed_time', time_of_day: '21:00' },
      }
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
      const schedule = {
        schedule_id: 'sched-1',
        name: 'Summer Moth Survey',
        trigger: { trigger_type: 'fixed_time', time_of_day: '21:00' },
      }
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
      const schedule = {
        schedule_id: 'sched-1',
        name: 'Summer Moth Survey',
        trigger: { trigger_type: 'fixed_time', time_of_day: '21:00' },
      }
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
      const schedule = {
        schedule_id: 'sched-1',
        name: 'Summer Moth Survey',
        trigger: { trigger_type: 'fixed_time', time_of_day: '21:00' },
      }
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
  // Trigger Summaries
  // ==========================================================================

  describe('Trigger Summaries', () => {
    it('renders interval trigger summary', () => {
      const schedule = {
        schedule_id: 'sched-1',
        name: 'Interval Schedule',
        trigger: {
          trigger_type: 'interval',
          interval_minutes: 60,
          time_window: { start_time: '21:00', end_time: '05:00' },
        },
      }
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
      const schedule = {
        schedule_id: 'sched-1',
        name: 'Solar Schedule',
        trigger: {
          trigger_type: 'solar',
          solar_event: 'sunset',
          offset_minutes: 30,
        },
      }
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
      const schedule = {
        schedule_id: 'sched-1',
        name: 'Solar Schedule',
        trigger: {
          trigger_type: 'solar',
          solar_event: 'sunrise',
          offset_minutes: -15,
        },
      }
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
      const schedule = {
        schedule_id: 'sched-1',
        name: 'Solar Schedule',
        trigger: {
          trigger_type: 'solar',
          solar_event: 'sunset',
          offset_minutes: 0,
        },
      }
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
      const schedule = {
        schedule_id: 'sched-1',
        name: 'Moon Phase Schedule',
        trigger: {
          trigger_type: 'moon_phase',
          moon_phase: 'full',
          time_of_day: '20:00',
        },
      }
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
      const schedule = {
        schedule_id: 'sched-1',
        name: 'Fixed Time Schedule',
        trigger: {
          trigger_type: 'fixed_time',
          time_of_day: '21:00',
        },
      }
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
      const schedule = {
        schedule_id: 'sched-1',
        name: 'Sensor Schedule',
        trigger: {
          trigger_type: 'sensor',
          sensor_type: 'light',
          comparison: 'lt',
          threshold: 100,
        },
      }
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
  })

  // ==========================================================================
  // Action Buttons
  // ==========================================================================

  describe('Action Buttons', () => {
    const schedule = {
      schedule_id: 'sched-1',
      name: 'Test Schedule',
      trigger: { trigger_type: 'fixed_time', time_of_day: '21:00' },
    }

    it('renders Edit button', () => {
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
    const schedule = {
      schedule_id: 'sched-1',
      name: 'Test Schedule',
      trigger: { trigger_type: 'fixed_time', time_of_day: '21:00' },
    }

    it('disables and shows "Loading..." on Edit button when isEditing is true', () => {
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
      const editButton = screen.getByRole('button', { name: /loading/i })
      expect(editButton).toBeDisabled()
      expect(editButton).toHaveTextContent('Loading...')
    })

    it('disables and shows "Loading..." on Activate button when isActivating is true', () => {
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
      const activateButton = screen.getByRole('button', { name: /loading/i })
      expect(activateButton).toBeDisabled()
      expect(activateButton).toHaveTextContent('Loading...')
    })

    it('disables and shows "Loading..." on Deactivate button when isDeactivating is true', () => {
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
      const deactivateButton = screen.getByRole('button', { name: /loading/i })
      expect(deactivateButton).toBeDisabled()
      expect(deactivateButton).toHaveTextContent('Loading...')
    })

    it('disables and shows "Loading..." on Delete button when isDeleting is true', () => {
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
      const deleteButton = screen.getByRole('button', { name: /loading/i })
      expect(deleteButton).toBeDisabled()
      expect(deleteButton).toHaveTextContent('Loading...')
    })

    it('disables all buttons when multiple loading states are true', () => {
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
      const schedule = {
        schedule_id: 'sched-1',
        name: 'Test Schedule',
        trigger: { trigger_type: 'fixed_time', time_of_day: '21:00' },
      }
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
      const schedule = {
        schedule_id: 'sched-1',
        name: 'Test Schedule',
        trigger: { trigger_type: 'fixed_time', time_of_day: '21:00' },
      }
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
      const schedule = {
        schedule_id: 'sched-1',
        name: 'Test Schedule',
        trigger: { trigger_type: 'fixed_time', time_of_day: '21:00' },
      }
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
