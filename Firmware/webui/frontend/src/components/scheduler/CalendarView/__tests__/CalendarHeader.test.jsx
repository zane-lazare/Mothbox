import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import CalendarHeader from '../CalendarHeader'

describe('CalendarHeader', () => {
  const mockSchedules = [
    { schedule_id: 'sched-1', name: 'Morning Photography' },
    { schedule_id: 'sched-2', name: 'Night Capture' },
    { schedule_id: 'sched-3', name: 'Weekly Timelapse' },
  ]

  const defaultProps = {
    viewMode: 'month',
    currentDate: new Date(2025, 11, 17), // December 17, 2025 (month is 0-indexed)
    onViewModeChange: vi.fn(),
    onNavigate: vi.fn(),
    schedules: mockSchedules,
    selectedScheduleId: null,
    onScheduleSelect: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('renders all navigation controls', () => {
      render(<CalendarHeader {...defaultProps} />)

      // Navigation buttons
      expect(screen.getByLabelText('Previous')).toBeInTheDocument()
      expect(screen.getByText('Today')).toBeInTheDocument()
      expect(screen.getByLabelText('Next')).toBeInTheDocument()

      // View mode buttons
      expect(screen.getByText('Day')).toBeInTheDocument()
      expect(screen.getByText('Week')).toBeInTheDocument()
      expect(screen.getByText('Month')).toBeInTheDocument()
    })

    it('renders schedule dropdown with all schedules', () => {
      render(<CalendarHeader {...defaultProps} />)

      const dropdown = screen.getByLabelText('Select schedule')
      expect(dropdown).toBeInTheDocument()

      // Check for placeholder option
      expect(screen.getByText('Select a schedule...')).toBeInTheDocument()

      // Check all schedule options are present
      mockSchedules.forEach((schedule) => {
        expect(screen.getByText(schedule.name)).toBeInTheDocument()
      })
    })

    it('shows formatted date range for month view', () => {
      render(<CalendarHeader {...defaultProps} viewMode="month" />)
      expect(screen.getByText('December 2025')).toBeInTheDocument()
    })

    it('shows formatted date range for week view', () => {
      // Dec 17, 2025 is a Wednesday
      // Week should be Dec 14-20, 2025 (Sunday to Saturday)
      render(<CalendarHeader {...defaultProps} viewMode="week" />)
      expect(screen.getByText('Dec 14-20, 2025')).toBeInTheDocument()
    })

    it('shows formatted date range for day view', () => {
      render(<CalendarHeader {...defaultProps} viewMode="day" />)
      expect(screen.getByText('December 17, 2025')).toBeInTheDocument()
    })

    it('shows formatted date range spanning two months in week view', () => {
      // Dec 30, 2025 is a Tuesday
      // Week should be Dec 28 - Jan 3, 2026
      const props = {
        ...defaultProps,
        viewMode: 'week',
        currentDate: new Date(2025, 11, 30), // December 30, 2025
      }
      render(<CalendarHeader {...props} />)
      expect(screen.getByText('Dec 28 - Jan 3, 2026')).toBeInTheDocument()
    })
  })

  describe('View Mode Selection', () => {
    it('shows active state for current view mode', () => {
      render(<CalendarHeader {...defaultProps} viewMode="month" />)

      const monthButton = screen.getByText('Month')
      expect(monthButton).toHaveClass('bg-blue-500')
      expect(monthButton).toHaveClass('text-white')
      expect(monthButton).toHaveAttribute('aria-pressed', 'true')

      const dayButton = screen.getByText('Day')
      expect(dayButton).toHaveClass('bg-white')
      expect(dayButton).not.toHaveClass('bg-blue-500')
      expect(dayButton).toHaveAttribute('aria-pressed', 'false')
    })

    it('calls onViewModeChange when day button clicked', async () => {
      const user = userEvent.setup()
      render(<CalendarHeader {...defaultProps} viewMode="month" />)

      const dayButton = screen.getByText('Day')
      await user.click(dayButton)

      expect(defaultProps.onViewModeChange).toHaveBeenCalledTimes(1)
      expect(defaultProps.onViewModeChange).toHaveBeenCalledWith('day')
    })

    it('calls onViewModeChange when week button clicked', async () => {
      const user = userEvent.setup()
      render(<CalendarHeader {...defaultProps} viewMode="month" />)

      const weekButton = screen.getByText('Week')
      await user.click(weekButton)

      expect(defaultProps.onViewModeChange).toHaveBeenCalledTimes(1)
      expect(defaultProps.onViewModeChange).toHaveBeenCalledWith('week')
    })

    it('calls onViewModeChange when month button clicked', async () => {
      const user = userEvent.setup()
      render(<CalendarHeader {...defaultProps} viewMode="day" />)

      const monthButton = screen.getByText('Month')
      await user.click(monthButton)

      expect(defaultProps.onViewModeChange).toHaveBeenCalledTimes(1)
      expect(defaultProps.onViewModeChange).toHaveBeenCalledWith('month')
    })
  })

  describe('Navigation', () => {
    it('calls onNavigate with "prev" when previous button clicked', async () => {
      const user = userEvent.setup()
      render(<CalendarHeader {...defaultProps} />)

      const prevButton = screen.getByLabelText('Previous')
      await user.click(prevButton)

      expect(defaultProps.onNavigate).toHaveBeenCalledTimes(1)
      expect(defaultProps.onNavigate).toHaveBeenCalledWith('prev')
    })

    it('calls onNavigate with "next" when next button clicked', async () => {
      const user = userEvent.setup()
      render(<CalendarHeader {...defaultProps} />)

      const nextButton = screen.getByLabelText('Next')
      await user.click(nextButton)

      expect(defaultProps.onNavigate).toHaveBeenCalledTimes(1)
      expect(defaultProps.onNavigate).toHaveBeenCalledWith('next')
    })

    it('calls onNavigate with "today" when today button clicked', async () => {
      const user = userEvent.setup()
      render(<CalendarHeader {...defaultProps} />)

      const todayButton = screen.getByText('Today')
      await user.click(todayButton)

      expect(defaultProps.onNavigate).toHaveBeenCalledTimes(1)
      expect(defaultProps.onNavigate).toHaveBeenCalledWith('today')
    })
  })

  describe('Schedule Selection', () => {
    it('shows placeholder when no schedule selected', () => {
      render(<CalendarHeader {...defaultProps} selectedScheduleId={null} />)

      const dropdown = screen.getByLabelText('Select schedule')
      expect(dropdown).toHaveValue('')
    })

    it('shows selected schedule when one is selected', () => {
      render(<CalendarHeader {...defaultProps} selectedScheduleId="sched-2" />)

      const dropdown = screen.getByLabelText('Select schedule')
      expect(dropdown).toHaveValue('sched-2')
    })

    it('calls onScheduleSelect when schedule chosen from dropdown', async () => {
      const user = userEvent.setup()
      render(<CalendarHeader {...defaultProps} />)

      const dropdown = screen.getByLabelText('Select schedule')
      await user.selectOptions(dropdown, 'sched-1')

      expect(defaultProps.onScheduleSelect).toHaveBeenCalledTimes(1)
      expect(defaultProps.onScheduleSelect).toHaveBeenCalledWith('sched-1')
    })

    it('calls onScheduleSelect with null when placeholder selected', async () => {
      const user = userEvent.setup()
      render(<CalendarHeader {...defaultProps} selectedScheduleId="sched-1" />)

      const dropdown = screen.getByLabelText('Select schedule')
      await user.selectOptions(dropdown, '')

      expect(defaultProps.onScheduleSelect).toHaveBeenCalledTimes(1)
      expect(defaultProps.onScheduleSelect).toHaveBeenCalledWith(null)
    })

    it('renders empty schedule list gracefully', () => {
      render(<CalendarHeader {...defaultProps} schedules={[]} />)

      const dropdown = screen.getByLabelText('Select schedule')
      expect(dropdown).toBeInTheDocument()
      expect(screen.getByText('Select a schedule...')).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('has proper ARIA labels for navigation buttons', () => {
      render(<CalendarHeader {...defaultProps} />)

      expect(screen.getByLabelText('Previous')).toHaveAttribute('aria-label', 'Previous')
      expect(screen.getByLabelText('Next')).toHaveAttribute('aria-label', 'Next')
    })

    it('has proper ARIA label for schedule dropdown', () => {
      render(<CalendarHeader {...defaultProps} />)

      expect(screen.getByLabelText('Select schedule')).toHaveAttribute('aria-label', 'Select schedule')
    })

    it('has role="group" for view mode toggle buttons', () => {
      const { container } = render(<CalendarHeader {...defaultProps} />)

      const buttonGroup = container.querySelector('[role="group"]')
      expect(buttonGroup).toBeInTheDocument()
      expect(buttonGroup).toHaveAttribute('aria-label', 'View mode')
    })

    it('has proper aria-pressed attributes on view mode buttons', () => {
      render(<CalendarHeader {...defaultProps} viewMode="week" />)

      expect(screen.getByText('Day')).toHaveAttribute('aria-pressed', 'false')
      expect(screen.getByText('Week')).toHaveAttribute('aria-pressed', 'true')
      expect(screen.getByText('Month')).toHaveAttribute('aria-pressed', 'false')
    })

    it('all buttons have type="button" to prevent form submission', () => {
      const { container } = render(<CalendarHeader {...defaultProps} />)

      const buttons = container.querySelectorAll('button')
      buttons.forEach((button) => {
        expect(button).toHaveAttribute('type', 'button')
      })
    })
  })

  describe('Dark Mode Support', () => {
    it('has dark mode classes on container', () => {
      const { container } = render(<CalendarHeader {...defaultProps} />)

      const header = container.querySelector('.sticky')
      // Component uses dark:bg-gray-900 and dark:border-gray-800
      expect(header).toHaveClass('dark:bg-gray-900')
      expect(header).toHaveClass('dark:border-gray-800')
    })

    it('has dark mode classes on schedule dropdown', () => {
      render(<CalendarHeader {...defaultProps} />)

      const dropdown = screen.getByLabelText('Select schedule')
      expect(dropdown).toHaveClass('dark:border-gray-600')
      expect(dropdown).toHaveClass('dark:bg-gray-700')
      expect(dropdown).toHaveClass('dark:text-gray-200')
    })

    it('has dark mode classes on navigation buttons', () => {
      render(<CalendarHeader {...defaultProps} />)

      const prevButton = screen.getByLabelText('Previous')
      expect(prevButton).toHaveClass('dark:hover:bg-gray-700')
      expect(prevButton).toHaveClass('dark:text-gray-200')

      const todayButton = screen.getByText('Today')
      expect(todayButton).toHaveClass('dark:bg-gray-700')
      expect(todayButton).toHaveClass('dark:border-gray-600')
      expect(todayButton).toHaveClass('dark:text-gray-200')
    })

    it('has dark mode classes on inactive view mode buttons', () => {
      render(<CalendarHeader {...defaultProps} viewMode="month" />)

      const dayButton = screen.getByText('Day')
      expect(dayButton).toHaveClass('dark:bg-gray-700')
      expect(dayButton).toHaveClass('dark:text-gray-200')
      expect(dayButton).toHaveClass('dark:border-gray-600')
    })

    it('has dark mode classes on date range text', () => {
      const { container } = render(<CalendarHeader {...defaultProps} />)

      const dateRange = container.querySelector('.text-base.font-semibold')
      expect(dateRange).toHaveClass('dark:text-gray-100')
    })
  })

  describe('Edge Cases', () => {
    it('handles undefined selectedScheduleId gracefully', () => {
      const props = { ...defaultProps }
      delete props.selectedScheduleId
      render(<CalendarHeader {...props} />)

      const dropdown = screen.getByLabelText('Select schedule')
      expect(dropdown).toHaveValue('')
    })

    it('handles date at year boundary correctly', () => {
      const props = {
        ...defaultProps,
        viewMode: 'day',
        currentDate: new Date(2025, 0, 1), // January 1, 2025
      }
      render(<CalendarHeader {...props} />)

      expect(screen.getByText('January 1, 2025')).toBeInTheDocument()
    })

    it('handles leap year date correctly', () => {
      const props = {
        ...defaultProps,
        viewMode: 'day',
        currentDate: new Date(2024, 1, 29), // February 29, 2024
      }
      render(<CalendarHeader {...props} />)

      expect(screen.getByText('February 29, 2024')).toBeInTheDocument()
    })
  })
})
