import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import SchedulerTabs from '../SchedulerTabs'

describe('SchedulerTabs', () => {
  it('renders Schedules tab', () => {
    render(
      <SchedulerTabs
        activeTab="schedules"
        onTabChange={vi.fn()}
      />
    )

    expect(screen.getByRole('tab', { name: /schedules/i })).toBeInTheDocument()
  })

  it('renders Calendar tab', () => {
    render(
      <SchedulerTabs
        activeTab="schedules"
        onTabChange={vi.fn()}
      />
    )

    expect(screen.getByRole('tab', { name: /calendar/i })).toBeInTheDocument()
  })

  it('applies active styling to selected tab', () => {
    render(
      <SchedulerTabs
        activeTab="schedules"
        onTabChange={vi.fn()}
      />
    )

    const schedulesTab = screen.getByRole('tab', { name: /schedules/i })
    expect(schedulesTab).toHaveClass('border-blue-500', 'text-blue-600')
  })

  it('applies inactive styling to unselected tab', () => {
    render(
      <SchedulerTabs
        activeTab="schedules"
        onTabChange={vi.fn()}
      />
    )

    const calendarTab = screen.getByRole('tab', { name: /calendar/i })
    expect(calendarTab).toHaveClass('border-transparent', 'text-gray-500')
  })

  it('calls onTabChange with "schedules" when Schedules clicked', async () => {
    const mockOnTabChange = vi.fn()
    const user = userEvent.setup()

    render(
      <SchedulerTabs
        activeTab="calendar"
        onTabChange={mockOnTabChange}
      />
    )

    await user.click(screen.getByRole('tab', { name: /schedules/i }))
    expect(mockOnTabChange).toHaveBeenCalledWith('schedules')
  })

  it('calls onTabChange with "calendar" when Calendar clicked', async () => {
    const mockOnTabChange = vi.fn()
    const user = userEvent.setup()

    render(
      <SchedulerTabs
        activeTab="schedules"
        onTabChange={mockOnTabChange}
      />
    )

    await user.click(screen.getByRole('tab', { name: /calendar/i }))
    expect(mockOnTabChange).toHaveBeenCalledWith('calendar')
  })

  it('has role="tablist" on container', () => {
    render(
      <SchedulerTabs
        activeTab="schedules"
        onTabChange={vi.fn()}
      />
    )

    expect(screen.getByRole('tablist')).toBeInTheDocument()
  })

  it('tabs have role="tab"', () => {
    render(
      <SchedulerTabs
        activeTab="schedules"
        onTabChange={vi.fn()}
      />
    )

    const tabs = screen.getAllByRole('tab')
    expect(tabs).toHaveLength(2)
  })

  it('selected tab has aria-selected="true"', () => {
    render(
      <SchedulerTabs
        activeTab="schedules"
        onTabChange={vi.fn()}
      />
    )

    const schedulesTab = screen.getByRole('tab', { name: /schedules/i })
    expect(schedulesTab).toHaveAttribute('aria-selected', 'true')
  })

  it('unselected tab has aria-selected="false"', () => {
    render(
      <SchedulerTabs
        activeTab="schedules"
        onTabChange={vi.fn()}
      />
    )

    const calendarTab = screen.getByRole('tab', { name: /calendar/i })
    expect(calendarTab).toHaveAttribute('aria-selected', 'false')
  })
})
