import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import ScheduleListPlaceholder from '../ScheduleListPlaceholder'

describe('ScheduleListPlaceholder', () => {
  it('renders placeholder message', () => {
    render(<ScheduleListPlaceholder />)
    expect(screen.getByText('Schedule List')).toBeInTheDocument()
    expect(screen.getByText(/Issue #266/)).toBeInTheDocument()
  })

  it('renders icon', () => {
    const { container } = render(<ScheduleListPlaceholder />)
    const icon = container.querySelector('svg')
    expect(icon).toBeInTheDocument()
    expect(icon).toHaveClass('h-16', 'w-16')
  })

  it('has proper styling', () => {
    const { container } = render(<ScheduleListPlaceholder />)
    const wrapper = container.firstChild
    expect(wrapper).toHaveClass('bg-white', 'rounded-lg', 'shadow')
  })
})
