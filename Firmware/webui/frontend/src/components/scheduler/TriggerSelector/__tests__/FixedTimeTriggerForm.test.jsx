import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import FixedTimeTriggerForm from '../FixedTimeTriggerForm'

describe('FixedTimeTriggerForm', () => {
  const mockOnChange = vi.fn()
  const defaultTrigger = {
    trigger_type: 'fixed_time',
    times: ['08:00'],
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('renders with initial time', () => {
      render(<FixedTimeTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      expect(screen.getByTestId('fixed-time-trigger-form')).toBeInTheDocument()
      expect(screen.getByTestId('fixed-time-input-0')).toHaveValue('08:00')
    })

    it('renders multiple times', () => {
      render(
        <FixedTimeTriggerForm
          trigger={{ ...defaultTrigger, times: ['08:00', '12:00', '18:00'] }}
          onChange={mockOnChange}
        />
      )

      expect(screen.getByTestId('fixed-time-input-0')).toHaveValue('08:00')
      expect(screen.getByTestId('fixed-time-input-1')).toHaveValue('12:00')
      expect(screen.getByTestId('fixed-time-input-2')).toHaveValue('18:00')
    })

    it('shows remove buttons for multiple times', () => {
      render(
        <FixedTimeTriggerForm
          trigger={{ ...defaultTrigger, times: ['08:00', '12:00'] }}
          onChange={mockOnChange}
        />
      )

      expect(screen.getByTestId('fixed-time-remove-0')).toBeInTheDocument()
      expect(screen.getByTestId('fixed-time-remove-1')).toBeInTheDocument()
    })

    it('hides remove button when only one time', () => {
      render(<FixedTimeTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      expect(screen.queryByTestId('fixed-time-remove-0')).not.toBeInTheDocument()
    })

    it('shows add time button', () => {
      render(<FixedTimeTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      expect(screen.getByTestId('fixed-time-add')).toBeInTheDocument()
    })
  })

  describe('Time Changes', () => {
    it('updates time at specific index', async () => {
      const user = userEvent.setup()
      render(<FixedTimeTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      const input = screen.getByTestId('fixed-time-input-0')
      // For time inputs, we test that onChange is called when input changes
      await user.clear(input)
      await user.type(input, '09:30')

      // Verify onChange was called with times array
      expect(mockOnChange).toHaveBeenCalled()
      const lastCall = mockOnChange.mock.calls[mockOnChange.mock.calls.length - 1][0]
      expect(lastCall).toHaveProperty('times')
      expect(Array.isArray(lastCall.times)).toBe(true)
    })
  })

  describe('Add Time', () => {
    it('adds new time when add button clicked', async () => {
      const user = userEvent.setup()
      render(<FixedTimeTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      await user.click(screen.getByTestId('fixed-time-add'))

      // With ID-based keys, times are now { id, value } objects
      expect(mockOnChange).toHaveBeenCalled()
      const call = mockOnChange.mock.calls[0][0]
      expect(call.trigger_type).toBe('fixed_time')
      expect(call.times).toHaveLength(2)
      expect(call.times[0]).toHaveProperty('id')
      expect(call.times[0]).toHaveProperty('value', '08:00')
      expect(call.times[1]).toHaveProperty('id')
      expect(call.times[1]).toHaveProperty('value', '12:00')
    })
  })

  describe('Remove Time', () => {
    it('removes time when remove button clicked', async () => {
      const user = userEvent.setup()
      render(
        <FixedTimeTriggerForm
          trigger={{ ...defaultTrigger, times: ['08:00', '12:00', '18:00'] }}
          onChange={mockOnChange}
        />
      )

      await user.click(screen.getByTestId('fixed-time-remove-1'))

      // With ID-based keys, times are now { id, value } objects
      expect(mockOnChange).toHaveBeenCalled()
      const call = mockOnChange.mock.calls[0][0]
      expect(call.trigger_type).toBe('fixed_time')
      expect(call.times).toHaveLength(2)
      expect(call.times[0]).toHaveProperty('value', '08:00')
      expect(call.times[1]).toHaveProperty('value', '18:00')
    })

    it('prevents removing last time', () => {
      render(<FixedTimeTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      // Remove button should not be present with only one time
      expect(screen.queryByTestId('fixed-time-remove-0')).not.toBeInTheDocument()
    })
  })

  describe('Disabled State', () => {
    it('disables all inputs when disabled prop is true', () => {
      render(
        <FixedTimeTriggerForm
          trigger={{ ...defaultTrigger, times: ['08:00', '12:00'] }}
          onChange={mockOnChange}
          disabled
        />
      )

      expect(screen.getByTestId('fixed-time-input-0')).toBeDisabled()
      expect(screen.getByTestId('fixed-time-input-1')).toBeDisabled()
      expect(screen.getByTestId('fixed-time-remove-0')).toBeDisabled()
      expect(screen.getByTestId('fixed-time-remove-1')).toBeDisabled()
      expect(screen.getByTestId('fixed-time-add')).toBeDisabled()
    })
  })

  describe('data-testid attributes', () => {
    it('has fixed-time-trigger-form on container', () => {
      render(<FixedTimeTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      expect(screen.getByTestId('fixed-time-trigger-form')).toBeInTheDocument()
    })

    it('has fixed-time-list on list container', () => {
      render(<FixedTimeTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      expect(screen.getByTestId('fixed-time-list')).toBeInTheDocument()
    })
  })
})
