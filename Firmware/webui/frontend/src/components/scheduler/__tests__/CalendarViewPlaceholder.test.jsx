import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import CalendarViewPlaceholder from '../CalendarViewPlaceholder'

describe('CalendarViewPlaceholder', () => {
  it('renders placeholder message', () => {
    render(<CalendarViewPlaceholder />)
    expect(screen.getByText('Calendar View')).toBeInTheDocument()
    expect(screen.getByText(/Issue #229/)).toBeInTheDocument()
  })

  it('renders icon', () => {
    const { container } = render(<CalendarViewPlaceholder />)
    const icon = container.querySelector('svg')
    expect(icon).toBeInTheDocument()
    expect(icon).toHaveClass('h-16', 'w-16')
  })

  it('has proper styling', () => {
    const { container } = render(<CalendarViewPlaceholder />)
    const wrapper = container.firstChild
    expect(wrapper).toHaveClass('bg-white', 'rounded-lg', 'shadow')
  })
})
