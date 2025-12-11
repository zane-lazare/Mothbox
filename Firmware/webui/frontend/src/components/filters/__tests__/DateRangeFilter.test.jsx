import { render, screen, within } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import userEvent from '@testing-library/user-event'
import React from 'react'
import { DateRangeFilter } from '../DateRangeFilter'
import { FilterProvider } from '../../../contexts/FilterContext'
import { DATE_PRESETS } from '../../../utils/filterQueryBuilder'

// Helper to render with FilterProvider
function renderWithProvider(ui) {
  return render(<FilterProvider>{ui}</FilterProvider>)
}

describe('DateRangeFilter', () => {
  describe('Rendering', () => {
    it('should render all preset buttons', () => {
      renderWithProvider(<DateRangeFilter />)

      // Check for all preset labels
      expect(screen.getByRole('button', { name: 'Today' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Last 7 Days' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Last 30 Days' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Last 90 Days' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'This Month' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Last Month' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'This Year' })).toBeInTheDocument()
    })

    it('should render preset buttons in correct count', () => {
      renderWithProvider(<DateRangeFilter />)
      const presetCount = Object.keys(DATE_PRESETS).length
      const presetGroup = screen.getByRole('group', { name: /quick select/i })
      const buttons = within(presetGroup).getAllByRole('button')
      expect(buttons).toHaveLength(presetCount)
    })

    it('should render Quick Select label', () => {
      renderWithProvider(<DateRangeFilter />)
      expect(screen.getByText('Quick Select')).toBeInTheDocument()
    })

    it('should render Custom Range label', () => {
      renderWithProvider(<DateRangeFilter />)
      expect(screen.getByText('Custom Range')).toBeInTheDocument()
    })

    it('should render start date input', () => {
      renderWithProvider(<DateRangeFilter />)
      const startInput = screen.getByLabelText('Start date')
      expect(startInput).toBeInTheDocument()
      expect(startInput).toHaveAttribute('type', 'date')
    })

    it('should render end date input', () => {
      renderWithProvider(<DateRangeFilter />)
      const endInput = screen.getByLabelText('End date')
      expect(endInput).toBeInTheDocument()
      expect(endInput).toHaveAttribute('type', 'date')
    })

    it('should not render clear button initially', () => {
      renderWithProvider(<DateRangeFilter />)
      expect(screen.queryByRole('button', { name: /clear/i })).not.toBeInTheDocument()
    })

    it('should not show Custom indicator initially', () => {
      renderWithProvider(<DateRangeFilter />)
      expect(screen.queryByText('Custom', { exact: true })).not.toBeInTheDocument()
    })
  })

  describe('Preset Button Interactions', () => {
    it('should highlight preset when clicked', async () => {
      const user = userEvent.setup()
      renderWithProvider(<DateRangeFilter />)

      const todayButton = screen.getByRole('button', { name: 'Today' })
      await user.click(todayButton)

      expect(todayButton).toHaveClass('bg-blue-600')
      expect(todayButton).toHaveAttribute('aria-pressed', 'true')
    })

    it('should set Last 7 Days preset', async () => {
      const user = userEvent.setup()
      renderWithProvider(<DateRangeFilter />)

      const button = screen.getByRole('button', { name: 'Last 7 Days' })
      await user.click(button)

      expect(button).toHaveClass('bg-blue-600')
      expect(button).toHaveAttribute('aria-pressed', 'true')
    })

    it('should set Last 30 Days preset', async () => {
      const user = userEvent.setup()
      renderWithProvider(<DateRangeFilter />)

      const button = screen.getByRole('button', { name: 'Last 30 Days' })
      await user.click(button)

      expect(button).toHaveClass('bg-blue-600')
      expect(button).toHaveAttribute('aria-pressed', 'true')
    })

    it('should set Last 90 Days preset', async () => {
      const user = userEvent.setup()
      renderWithProvider(<DateRangeFilter />)

      const button = screen.getByRole('button', { name: 'Last 90 Days' })
      await user.click(button)

      expect(button).toHaveClass('bg-blue-600')
      expect(button).toHaveAttribute('aria-pressed', 'true')
    })

    it('should set This Month preset', async () => {
      const user = userEvent.setup()
      renderWithProvider(<DateRangeFilter />)

      const button = screen.getByRole('button', { name: 'This Month' })
      await user.click(button)

      expect(button).toHaveClass('bg-blue-600')
      expect(button).toHaveAttribute('aria-pressed', 'true')
    })

    it('should set Last Month preset', async () => {
      const user = userEvent.setup()
      renderWithProvider(<DateRangeFilter />)

      const button = screen.getByRole('button', { name: 'Last Month' })
      await user.click(button)

      expect(button).toHaveClass('bg-blue-600')
      expect(button).toHaveAttribute('aria-pressed', 'true')
    })

    it('should set This Year preset', async () => {
      const user = userEvent.setup()
      renderWithProvider(<DateRangeFilter />)

      const button = screen.getByRole('button', { name: 'This Year' })
      await user.click(button)

      expect(button).toHaveClass('bg-blue-600')
      expect(button).toHaveAttribute('aria-pressed', 'true')
    })

    it('should only highlight one preset at a time', async () => {
      const user = userEvent.setup()
      renderWithProvider(<DateRangeFilter />)

      const todayButton = screen.getByRole('button', { name: 'Today' })
      const last7Button = screen.getByRole('button', { name: 'Last 7 Days' })

      await user.click(todayButton)
      expect(todayButton).toHaveAttribute('aria-pressed', 'true')

      await user.click(last7Button)
      expect(todayButton).toHaveAttribute('aria-pressed', 'false')
      expect(last7Button).toHaveAttribute('aria-pressed', 'true')
    })

    it('should show clear button after preset is selected', async () => {
      const user = userEvent.setup()
      renderWithProvider(<DateRangeFilter />)

      const todayButton = screen.getByRole('button', { name: 'Today' })
      await user.click(todayButton)

      expect(screen.getByRole('button', { name: /clear/i })).toBeInTheDocument()
    })
  })

  describe('Custom Date Input Interactions', () => {
    it('should update start date when changed', async () => {
      const user = userEvent.setup()
      renderWithProvider(<DateRangeFilter />)

      const startInput = screen.getByLabelText('Start date')
      await user.type(startInput, '2024-01-01')

      expect(startInput).toHaveValue('2024-01-01')
    })

    it('should update end date when changed', async () => {
      const user = userEvent.setup()
      renderWithProvider(<DateRangeFilter />)

      const endInput = screen.getByLabelText('End date')
      await user.type(endInput, '2024-01-31')

      expect(endInput).toHaveValue('2024-01-31')
    })

    it('should show Custom indicator when start date is set', async () => {
      const user = userEvent.setup()
      renderWithProvider(<DateRangeFilter />)

      const startInput = screen.getByLabelText('Start date')
      await user.type(startInput, '2024-01-01')

      expect(screen.getByText('Custom', { exact: true })).toBeInTheDocument()
    })

    it('should show Custom indicator when end date is set', async () => {
      const user = userEvent.setup()
      renderWithProvider(<DateRangeFilter />)

      const endInput = screen.getByLabelText('End date')
      await user.type(endInput, '2024-01-31')

      expect(screen.getByText('Custom', { exact: true })).toBeInTheDocument()
    })

    it('should show clear button when start date is set', async () => {
      const user = userEvent.setup()
      renderWithProvider(<DateRangeFilter />)

      const startInput = screen.getByLabelText('Start date')
      await user.type(startInput, '2024-01-01')

      expect(screen.getByRole('button', { name: /clear/i })).toBeInTheDocument()
    })

    it('should show clear button when end date is set', async () => {
      const user = userEvent.setup()
      renderWithProvider(<DateRangeFilter />)

      const endInput = screen.getByLabelText('End date')
      await user.type(endInput, '2024-01-31')

      expect(screen.getByRole('button', { name: /clear/i })).toBeInTheDocument()
    })

    it('should allow both start and end dates to be set', async () => {
      const user = userEvent.setup()
      renderWithProvider(<DateRangeFilter />)

      const startInput = screen.getByLabelText('Start date')
      const endInput = screen.getByLabelText('End date')

      await user.type(startInput, '2024-01-01')
      await user.type(endInput, '2024-01-31')

      expect(startInput).toHaveValue('2024-01-01')
      expect(endInput).toHaveValue('2024-01-31')
    })

    it('should clear preset when custom date is entered', async () => {
      const user = userEvent.setup()
      renderWithProvider(<DateRangeFilter />)

      const todayButton = screen.getByRole('button', { name: 'Today' })
      await user.click(todayButton)
      expect(todayButton).toHaveAttribute('aria-pressed', 'true')

      const startInput = screen.getByLabelText('Start date')
      await user.type(startInput, '2024-01-01')

      expect(todayButton).toHaveAttribute('aria-pressed', 'false')
    })
  })

  describe('Clear Button Functionality', () => {
    it('should clear preset when clear button is clicked', async () => {
      const user = userEvent.setup()
      renderWithProvider(<DateRangeFilter />)

      const todayButton = screen.getByRole('button', { name: 'Today' })
      await user.click(todayButton)

      const clearButton = screen.getByRole('button', { name: /clear/i })
      await user.click(clearButton)

      expect(todayButton).toHaveAttribute('aria-pressed', 'false')
      expect(screen.queryByRole('button', { name: /clear/i })).not.toBeInTheDocument()
    })

    it('should clear custom dates when clear button is clicked', async () => {
      const user = userEvent.setup()
      renderWithProvider(<DateRangeFilter />)

      const startInput = screen.getByLabelText('Start date')
      const endInput = screen.getByLabelText('End date')

      await user.type(startInput, '2024-01-01')
      await user.type(endInput, '2024-01-31')

      const clearButton = screen.getByRole('button', { name: /clear/i })
      await user.click(clearButton)

      expect(startInput).toHaveValue('')
      expect(endInput).toHaveValue('')
      expect(screen.queryByRole('button', { name: /clear/i })).not.toBeInTheDocument()
    })

    it('should hide Custom indicator after clearing', async () => {
      const user = userEvent.setup()
      renderWithProvider(<DateRangeFilter />)

      const startInput = screen.getByLabelText('Start date')
      await user.type(startInput, '2024-01-01')

      expect(screen.getByText('Custom', { exact: true })).toBeInTheDocument()

      const clearButton = screen.getByRole('button', { name: /clear/i })
      await user.click(clearButton)

      expect(screen.queryByText('Custom', { exact: true })).not.toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('should have proper ARIA labels on preset group', () => {
      renderWithProvider(<DateRangeFilter />)
      const presetGroup = screen.getByRole('group', { name: /quick select/i })
      expect(presetGroup).toBeInTheDocument()
    })

    it('should have proper ARIA labels on custom date group', () => {
      renderWithProvider(<DateRangeFilter />)
      const customGroup = screen.getByRole('group', { name: /custom range/i })
      expect(customGroup).toBeInTheDocument()
    })

    it('should have proper aria-pressed on preset buttons', () => {
      renderWithProvider(<DateRangeFilter />)
      const todayButton = screen.getByRole('button', { name: 'Today' })
      expect(todayButton).toHaveAttribute('aria-pressed')
    })

    it('should have aria-label on start date input', () => {
      renderWithProvider(<DateRangeFilter />)
      const startInput = screen.getByLabelText('Start date')
      expect(startInput).toHaveAttribute('aria-label', 'Start date')
    })

    it('should have aria-label on end date input', () => {
      renderWithProvider(<DateRangeFilter />)
      const endInput = screen.getByLabelText('End date')
      expect(endInput).toHaveAttribute('aria-label', 'End date')
    })

    it('should have aria-label on clear button', async () => {
      const user = userEvent.setup()
      renderWithProvider(<DateRangeFilter />)

      const todayButton = screen.getByRole('button', { name: 'Today' })
      await user.click(todayButton)

      const clearButton = screen.getByRole('button', { name: /clear/i })
      expect(clearButton).toHaveAttribute('aria-label', 'Clear date filter')
    })

    it('should have aria-label on Custom indicator', async () => {
      const user = userEvent.setup()
      renderWithProvider(<DateRangeFilter />)

      const startInput = screen.getByLabelText('Start date')
      await user.type(startInput, '2024-01-01')

      const customIndicator = screen.getByLabelText('Custom date range active')
      expect(customIndicator).toBeInTheDocument()
    })
  })

  describe('Dark Mode Styling', () => {
    it('should have dark mode classes on preset buttons', () => {
      renderWithProvider(<DateRangeFilter />)
      const todayButton = screen.getByRole('button', { name: 'Today' })
      expect(todayButton.className).toContain('dark:bg-gray-800')
      expect(todayButton.className).toContain('dark:text-gray-300')
    })

    it('should have dark mode classes on active preset button', async () => {
      const user = userEvent.setup()
      renderWithProvider(<DateRangeFilter />)

      const todayButton = screen.getByRole('button', { name: 'Today' })
      await user.click(todayButton)

      expect(todayButton.className).toContain('dark:focus:ring-offset-gray-800')
    })

    it('should have dark mode classes on date inputs', () => {
      renderWithProvider(<DateRangeFilter />)
      const startInput = screen.getByLabelText('Start date')
      expect(startInput.className).toContain('dark:bg-gray-800')
      expect(startInput.className).toContain('dark:text-gray-100')
      expect(startInput.className).toContain('dark:border-gray-600')
    })

    it('should have dark mode classes on labels', () => {
      renderWithProvider(<DateRangeFilter />)
      const quickSelectLabel = screen.getByText('Quick Select')
      expect(quickSelectLabel.className).toContain('dark:text-gray-300')
    })

    it('should have dark mode classes on clear button', async () => {
      const user = userEvent.setup()
      renderWithProvider(<DateRangeFilter />)

      const todayButton = screen.getByRole('button', { name: 'Today' })
      await user.click(todayButton)

      const clearButton = screen.getByRole('button', { name: /clear/i })
      expect(clearButton.className).toContain('dark:bg-gray-700')
      expect(clearButton.className).toContain('dark:text-gray-300')
    })

    it('should have dark mode classes on Custom indicator', async () => {
      const user = userEvent.setup()
      renderWithProvider(<DateRangeFilter />)

      const startInput = screen.getByLabelText('Start date')
      await user.type(startInput, '2024-01-01')

      const customIndicator = screen.getByText('Custom', { exact: true })
      expect(customIndicator.className).toContain('dark:text-blue-400')
    })
  })

  describe('Active State Highlighting', () => {
    it('should highlight Today preset when active', async () => {
      const user = userEvent.setup()
      renderWithProvider(<DateRangeFilter />)

      const todayButton = screen.getByRole('button', { name: 'Today' })
      await user.click(todayButton)

      expect(todayButton).toHaveClass('bg-blue-600', 'text-white')
    })

    it('should not highlight inactive presets', async () => {
      const user = userEvent.setup()
      renderWithProvider(<DateRangeFilter />)

      const todayButton = screen.getByRole('button', { name: 'Today' })
      const last7Button = screen.getByRole('button', { name: 'Last 7 Days' })

      await user.click(todayButton)

      expect(last7Button).not.toHaveClass('bg-blue-600')
      expect(last7Button).toHaveClass('bg-white', 'dark:bg-gray-800')
    })

    it('should show correct active state after switching presets', async () => {
      const user = userEvent.setup()
      renderWithProvider(<DateRangeFilter />)

      const todayButton = screen.getByRole('button', { name: 'Today' })
      const last7Button = screen.getByRole('button', { name: 'Last 7 Days' })

      await user.click(todayButton)
      expect(todayButton).toHaveClass('bg-blue-600')

      await user.click(last7Button)
      expect(todayButton).not.toHaveClass('bg-blue-600')
      expect(last7Button).toHaveClass('bg-blue-600')
    })
  })

  describe('Component Lifecycle', () => {
    it('should maintain state after re-render', async () => {
      const user = userEvent.setup()
      const { rerender } = renderWithProvider(<DateRangeFilter />)

      const todayButton = screen.getByRole('button', { name: 'Today' })
      await user.click(todayButton)

      rerender(
        <FilterProvider>
          <DateRangeFilter />
        </FilterProvider>
      )

      const todayButtonAfter = screen.getByRole('button', { name: 'Today' })
      expect(todayButtonAfter).toHaveAttribute('aria-pressed', 'true')
    })

    it('should handle rapid preset changes', async () => {
      const user = userEvent.setup()
      renderWithProvider(<DateRangeFilter />)

      const todayButton = screen.getByRole('button', { name: 'Today' })
      const last7Button = screen.getByRole('button', { name: 'Last 7 Days' })
      const last30Button = screen.getByRole('button', { name: 'Last 30 Days' })

      await user.click(todayButton)
      await user.click(last7Button)
      await user.click(last30Button)

      expect(last30Button).toHaveAttribute('aria-pressed', 'true')
      expect(todayButton).toHaveAttribute('aria-pressed', 'false')
      expect(last7Button).toHaveAttribute('aria-pressed', 'false')
    })
  })
})
