import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import CronExpressionInput from '../CronExpressionInput'
import type { CronExpressionInputProps } from '../CronExpressionInput'
import type { CronValidationResult } from '../../../../hooks/useCronValidation'
// @ts-expect-error — cronApi.js has no type declarations (pre-migration)
import * as cronApi from '../../../../utils/cronApi'

// Mock the cronApi module
vi.mock('../../../../utils/cronApi')

const mockValidate = cronApi.validateCronExpression as ReturnType<typeof vi.fn>

describe('CronExpressionInput', () => {
  let mockOnChange: ReturnType<typeof vi.fn<(value: string) => void>>
  let queryClient: QueryClient

  beforeEach(() => {
    mockOnChange = vi.fn<(value: string) => void>()
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    })
    vi.clearAllMocks()
  })

  /**
   * Helper to render component with QueryClient wrapper
   */
  const renderComponent = (overrides: Partial<CronExpressionInputProps> = {}) => {
    const defaultProps: CronExpressionInputProps = {
      value: '',
      onChange: mockOnChange,
      ...overrides,
    }

    return render(
      <QueryClientProvider client={queryClient}>
        <CronExpressionInput {...defaultProps} />
      </QueryClientProvider>
    )
  }

  describe('Rendering', () => {
    it('renders cron input field', () => {
      renderComponent()

      expect(screen.getByLabelText('Cron expression input')).toBeInTheDocument()
      expect(screen.getByText('Cron Expression')).toBeInTheDocument()
    })

    it('displays validation success state', async () => {
      const mockResponse = {
        valid: true,
        expression: '0 * * * *',
        description: 'At minute 0 of every hour',
        next_executions: ['2024-12-26T14:00:00'],
      }

      mockValidate.mockResolvedValue(mockResponse)

      renderComponent({ value: '0 * * * *' })

      await waitFor(() => {
        expect(screen.getByLabelText('Valid expression')).toBeInTheDocument()
      })

      expect(screen.getByText('At minute 0 of every hour')).toBeInTheDocument()
    })

    it('displays validation error state', async () => {
      const mockResponse = {
        valid: false,
        expression: 'invalid',
        error: 'Invalid cron expression',
      }

      mockValidate.mockResolvedValue(mockResponse)

      renderComponent({ value: 'invalid' })

      await waitFor(() => {
        expect(screen.getByLabelText('Invalid expression')).toBeInTheDocument()
      })

      expect(screen.getByText('Invalid cron expression')).toBeInTheDocument()
    })

    it('shows loading state during validation', async () => {
      // Create a promise that never resolves to keep loading state
      let resolvePromise!: (value: CronValidationResult) => void
      const pendingPromise = new Promise<CronValidationResult>((resolve) => {
        resolvePromise = resolve
      })

      mockValidate.mockReturnValue(pendingPromise)

      renderComponent({ value: '0 * * * *' })

      // Wait for loading indicator to appear
      await waitFor(() => {
        expect(screen.getByLabelText('Validating')).toBeInTheDocument()
      })

      // Clean up
      resolvePromise({
        valid: true,
        expression: '0 * * * *',
        description: 'At minute 0 of every hour',
      })
    })

    it('displays next execution times on valid expression', async () => {
      const mockResponse = {
        valid: true,
        expression: '0 21 * * *',
        description: 'At 21:00 every day',
        next_executions: [
          '2024-12-26T21:00:00',
          '2024-12-27T21:00:00',
          '2024-12-28T21:00:00',
        ],
      }

      mockValidate.mockResolvedValue(mockResponse)

      renderComponent({ value: '0 21 * * *' })

      await waitFor(() => {
        expect(screen.getByText('Next executions:')).toBeInTheDocument()
      })

      // Check that execution times are displayed
      const executionItems = screen.getAllByRole('listitem')
      expect(executionItems).toHaveLength(3)
    })

    it('shows help text with cron format', () => {
      renderComponent()

      expect(screen.getByText(/Format: minute hour day month weekday/i)).toBeInTheDocument()
      expect(screen.getByText(/\* = any/i)).toBeInTheDocument()
    })

    it('preset buttons populate expression field', () => {
      renderComponent()

      const presetButton = screen.getByLabelText('Set expression to Every hour')
      fireEvent.click(presetButton)

      expect(mockOnChange).toHaveBeenCalledWith('0 * * * *')
    })

    it('handles empty expression gracefully', () => {
      renderComponent({ value: '' })

      const input = screen.getByLabelText('Cron expression input')
      expect(input).toHaveValue('')

      // Should not show validation icons for empty input
      expect(screen.queryByLabelText('Valid expression')).not.toBeInTheDocument()
      expect(screen.queryByLabelText('Invalid expression')).not.toBeInTheDocument()
    })

    it('respects disabled state', () => {
      renderComponent({ disabled: true })

      const input = screen.getByLabelText('Cron expression input')
      expect(input).toBeDisabled()

      const presetButton = screen.getByLabelText('Set expression to Every hour')
      expect(presetButton).toBeDisabled()
    })

    it('applies dark mode styles', () => {
      renderComponent()

      const input = screen.getByLabelText('Cron expression input')
      expect(input).toHaveClass('dark:bg-gray-800', 'dark:text-white', 'dark:border-gray-600')
    })

    it('displays human-readable description', async () => {
      const mockResponse = {
        valid: true,
        expression: '*/5 * * * *',
        description: 'Every 5 minutes',
        next_executions: ['2024-12-26T14:00:00'],
      }

      mockValidate.mockResolvedValue(mockResponse)

      renderComponent({ value: '*/5 * * * *' })

      await waitFor(() => {
        expect(screen.getByText('Every 5 minutes')).toBeInTheDocument()
      })
    })
  })

  describe('User Interaction', () => {
    it('calls onChange when input changes', () => {
      renderComponent()

      const input = screen.getByLabelText('Cron expression input')
      fireEvent.change(input, { target: { value: '0 * * * *' } })

      expect(mockOnChange).toHaveBeenCalledWith('0 * * * *')
    })

    it('highlights selected preset', () => {
      renderComponent({ value: '0 * * * *' })

      const presetButton = screen.getByLabelText('Set expression to Every hour')
      expect(presetButton).toHaveClass('bg-blue-500')
    })

    it('applies correct styling for valid expression', async () => {
      const mockResponse = {
        valid: true,
        expression: '0 * * * *',
        description: 'At minute 0 of every hour',
        next_executions: ['2024-12-26T14:00:00'],
      }

      mockValidate.mockResolvedValue(mockResponse)

      renderComponent({ value: '0 * * * *' })

      await waitFor(() => {
        const input = screen.getByLabelText('Cron expression input')
        expect(input).toHaveClass('border-green-500')
      })
    })

    it('applies correct styling for invalid expression', async () => {
      const mockResponse = {
        valid: false,
        expression: 'invalid',
        error: 'Invalid cron expression',
      }

      mockValidate.mockResolvedValue(mockResponse)

      renderComponent({ value: 'invalid' })

      await waitFor(() => {
        const input = screen.getByLabelText('Cron expression input')
        expect(input).toHaveClass('border-red-500')
      })
    })
  })

  describe('Preset Buttons', () => {
    it('renders all preset buttons', () => {
      renderComponent()

      expect(screen.getByLabelText('Set expression to Every hour')).toBeInTheDocument()
      expect(screen.getByLabelText('Set expression to Every 5 min')).toBeInTheDocument()
      expect(screen.getByLabelText('Set expression to Every 15 min')).toBeInTheDocument()
      expect(screen.getByLabelText('Set expression to Daily midnight')).toBeInTheDocument()
      expect(screen.getByLabelText('Set expression to Daily 9 PM')).toBeInTheDocument()
      expect(screen.getByLabelText('Set expression to Weekdays 9 PM')).toBeInTheDocument()
    })

    it('sets correct expression for each preset', () => {
      renderComponent()

      const presets = [
        { label: 'Every hour', expression: '0 * * * *' },
        { label: 'Every 5 min', expression: '*/5 * * * *' },
        { label: 'Every 15 min', expression: '*/15 * * * *' },
        { label: 'Daily midnight', expression: '0 0 * * *' },
        { label: 'Daily 9 PM', expression: '0 21 * * *' },
        { label: 'Weekdays 9 PM', expression: '0 21 * * 1-5' },
      ]

      presets.forEach((preset) => {
        const button = screen.getByLabelText(`Set expression to ${preset.label}`)
        fireEvent.click(button)
        expect(mockOnChange).toHaveBeenCalledWith(preset.expression)
      })
    })
  })

  describe('Field Reference', () => {
    it('displays field reference table', () => {
      renderComponent()

      expect(screen.getByText('Field reference:')).toBeInTheDocument()

      // Use more specific queries to avoid matching "weekday" when looking for "day"
      const fieldTexts = screen.getAllByText(/:/i)
      const fieldNames = fieldTexts.map(el => el.textContent)

      expect(fieldNames).toContain('minute:')
      expect(fieldNames).toContain('hour:')
      expect(fieldNames).toContain('day:')
      expect(fieldNames).toContain('month:')
      expect(fieldNames).toContain('weekday:')
    })

    it('shows correct ranges for each field', () => {
      renderComponent()

      expect(screen.getByText('0-59')).toBeInTheDocument() // minute
      expect(screen.getByText('0-23')).toBeInTheDocument() // hour
      expect(screen.getByText('1-31')).toBeInTheDocument() // day
      expect(screen.getByText('1-12')).toBeInTheDocument() // month
      expect(screen.getByText('0-6 (Sun-Sat)')).toBeInTheDocument() // weekday
    })
  })

  describe('Accessibility', () => {
    it('sets aria-invalid on invalid expression', async () => {
      const mockResponse = {
        valid: false,
        expression: 'invalid',
        error: 'Invalid cron expression',
      }

      mockValidate.mockResolvedValue(mockResponse)

      renderComponent({ value: 'invalid' })

      await waitFor(() => {
        const input = screen.getByLabelText('Cron expression input')
        expect(input).toHaveAttribute('aria-invalid', 'true')
      })
    })

    it('associates input with help text', () => {
      renderComponent()

      const input = screen.getByLabelText('Cron expression input')
      expect(input).toHaveAttribute('aria-describedby', 'cron-help cron-validation')
    })
  })

  describe('Execution Time Formatting', () => {
    it('formats execution times correctly', async () => {
      const mockResponse = {
        valid: true,
        expression: '0 21 * * *',
        description: 'At 21:00 every day',
        next_executions: ['2024-12-26T21:00:00'],
      }

      mockValidate.mockResolvedValue(mockResponse)

      renderComponent({ value: '0 21 * * *' })

      await waitFor(() => {
        expect(screen.getByText('Next executions:')).toBeInTheDocument()
      })

      // Check that at least one formatted time is displayed
      const executionItems = screen.getAllByRole('listitem')
      expect(executionItems.length).toBeGreaterThan(0)
    })
  })
})
