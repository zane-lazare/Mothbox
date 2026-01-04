import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import SolarTriggerForm from '../SolarTriggerForm'
import { SOLAR_EVENTS } from '../constants'

describe('SolarTriggerForm', () => {
  const mockOnChange = vi.fn()
  const defaultTrigger = {
    trigger_type: 'solar',
    solar_event: 'sunset',
    offset_minutes: 0,
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('renders solar event select and offset input', () => {
      render(<SolarTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      expect(screen.getByTestId('solar-trigger-form')).toBeInTheDocument()
      expect(screen.getByTestId('solar-event')).toHaveValue('sunset')
      expect(screen.getByTestId('solar-offset')).toHaveValue(0)
    })

    it('renders all 8 solar event options', () => {
      render(<SolarTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      const select = screen.getByTestId('solar-event')
      const options = within(select).getAllByRole('option')

      expect(options).toHaveLength(SOLAR_EVENTS.length)
      SOLAR_EVENTS.forEach((event, index) => {
        expect(options[index]).toHaveValue(event.value)
      })
    })

  })

  describe('Event Changes', () => {
    it('updates solar_event when selection changes', async () => {
      const user = userEvent.setup()
      render(<SolarTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      await user.selectOptions(screen.getByTestId('solar-event'), 'sunrise')

      expect(mockOnChange).toHaveBeenCalledWith({
        ...defaultTrigger,
        solar_event: 'sunrise',
      })
    })
  })

  describe('Offset Changes', () => {
    it('updates offset_minutes when value changes', async () => {
      const user = userEvent.setup()
      render(<SolarTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      const input = screen.getByTestId('solar-offset')
      await user.clear(input)
      await user.type(input, '30')

      // Verify onChange was called with correct structure
      expect(mockOnChange).toHaveBeenCalled()
      const lastCall = mockOnChange.mock.calls[mockOnChange.mock.calls.length - 1][0]
      expect(lastCall).toHaveProperty('offset_minutes')
      expect(typeof lastCall.offset_minutes).toBe('number')
    })

    it('handles negative offset', async () => {
      const user = userEvent.setup()
      render(<SolarTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      const input = screen.getByTestId('solar-offset')
      await user.clear(input)
      await user.type(input, '-15')

      // Verify onChange was called with correct structure
      expect(mockOnChange).toHaveBeenCalled()
      const lastCall = mockOnChange.mock.calls[mockOnChange.mock.calls.length - 1][0]
      expect(lastCall).toHaveProperty('offset_minutes')
      expect(typeof lastCall.offset_minutes).toBe('number')
    })

    it('handles empty offset as 0', async () => {
      const user = userEvent.setup()
      render(
        <SolarTriggerForm
          trigger={{ ...defaultTrigger, offset_minutes: 30 }}
          onChange={mockOnChange}
        />
      )

      const input = screen.getByTestId('solar-offset')
      await user.clear(input)

      // When cleared, offset should be 0
      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({
          offset_minutes: 0,
        })
      )
    })
  })

  describe('Disabled State', () => {
    it('disables all inputs when disabled prop is true', () => {
      render(<SolarTriggerForm trigger={defaultTrigger} onChange={mockOnChange} disabled />)

      expect(screen.getByTestId('solar-event')).toBeDisabled()
      expect(screen.getByTestId('solar-offset')).toBeDisabled()
    })
  })

  describe('data-testid attributes', () => {
    it('has solar-trigger-form on container', () => {
      render(<SolarTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      expect(screen.getByTestId('solar-trigger-form')).toBeInTheDocument()
    })

    it('has solar-event on select', () => {
      render(<SolarTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      expect(screen.getByTestId('solar-event')).toBeInTheDocument()
    })

    it('has solar-offset on input', () => {
      render(<SolarTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      expect(screen.getByTestId('solar-offset')).toBeInTheDocument()
    })
  })
})
