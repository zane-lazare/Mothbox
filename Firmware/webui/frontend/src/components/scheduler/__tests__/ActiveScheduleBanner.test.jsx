import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ActiveScheduleBanner from '../ActiveScheduleBanner'

// Mock the hooks
vi.mock('../../../hooks/useSchedules', () => ({
  useActiveSchedule: vi.fn(),
  useDeactivateSchedule: vi.fn(),
}))

// Import after mock to get mocked versions
import { useActiveSchedule, useDeactivateSchedule } from '../../../hooks/useSchedules'

describe('ActiveScheduleBanner', () => {
  beforeEach(() => {
    // Reset mocks before each test
    vi.clearAllMocks()

    // Default mock implementations
    useActiveSchedule.mockReturnValue({
      data: null,
      isLoading: false
    })
    useDeactivateSchedule.mockReturnValue({
      mutate: vi.fn(),
      isPending: false
    })
  })

  it('renders nothing when no active schedule', () => {
    useActiveSchedule.mockReturnValue({
      data: null,
      isLoading: false
    })

    const { container } = render(<ActiveScheduleBanner />)
    expect(container.firstChild).toBeNull()
  })

  it('renders nothing when active_schedule is undefined', () => {
    useActiveSchedule.mockReturnValue({
      data: {},
      isLoading: false
    })

    const { container } = render(<ActiveScheduleBanner />)
    expect(container.firstChild).toBeNull()
  })

  it('renders banner with schedule name when active', () => {
    useActiveSchedule.mockReturnValue({
      data: {
        active_schedule: {
          id: 'sched-1',
          name: 'Night Photography'
        }
      },
      isLoading: false
    })

    render(<ActiveScheduleBanner />)

    expect(screen.getByText(/Active:/)).toBeInTheDocument()
    expect(screen.getByText('Night Photography')).toBeInTheDocument()
  })

  it('shows green styling for active state', () => {
    useActiveSchedule.mockReturnValue({
      data: {
        active_schedule: {
          id: 'sched-1',
          name: 'Night Photography'
        }
      },
      isLoading: false
    })

    const { container } = render(<ActiveScheduleBanner />)

    const banner = container.querySelector('[role="status"]')
    expect(banner).toHaveClass('bg-green-50', 'border-green-200', 'rounded-lg')
  })

  it('renders Deactivate button', () => {
    useActiveSchedule.mockReturnValue({
      data: {
        active_schedule: {
          id: 'sched-1',
          name: 'Night Photography'
        }
      },
      isLoading: false
    })

    render(<ActiveScheduleBanner />)

    const button = screen.getByRole('button', { name: /deactivate/i })
    expect(button).toBeInTheDocument()
  })

  it('calls deactivate mutation on button click', async () => {
    const user = userEvent.setup()
    const mockMutate = vi.fn()

    useActiveSchedule.mockReturnValue({
      data: {
        active_schedule: {
          id: 'sched-1',
          name: 'Night Photography'
        }
      },
      isLoading: false
    })

    useDeactivateSchedule.mockReturnValue({
      mutate: mockMutate,
      isPending: false
    })

    render(<ActiveScheduleBanner />)

    const button = screen.getByRole('button', { name: /deactivate/i })
    await user.click(button)

    expect(mockMutate).toHaveBeenCalledTimes(1)
  })

  it('shows loading state during deactivation', () => {
    useActiveSchedule.mockReturnValue({
      data: {
        active_schedule: {
          id: 'sched-1',
          name: 'Night Photography'
        }
      },
      isLoading: false
    })

    useDeactivateSchedule.mockReturnValue({
      mutate: vi.fn(),
      isPending: true
    })

    render(<ActiveScheduleBanner />)

    expect(screen.getByText(/deactivating/i)).toBeInTheDocument()
  })

  it('disables button during deactivation', () => {
    useActiveSchedule.mockReturnValue({
      data: {
        active_schedule: {
          id: 'sched-1',
          name: 'Night Photography'
        }
      },
      isLoading: false
    })

    useDeactivateSchedule.mockReturnValue({
      mutate: vi.fn(),
      isPending: true
    })

    render(<ActiveScheduleBanner />)

    const button = screen.getByRole('button', { name: /deactivating/i })
    expect(button).toBeDisabled()
  })

  it('has role="status" for accessibility', () => {
    useActiveSchedule.mockReturnValue({
      data: {
        active_schedule: {
          id: 'sched-1',
          name: 'Night Photography'
        }
      },
      isLoading: false
    })

    render(<ActiveScheduleBanner />)

    const banner = screen.getByRole('status')
    expect(banner).toBeInTheDocument()
  })

  it('renders CheckCircle icon when active', () => {
    useActiveSchedule.mockReturnValue({
      data: {
        active_schedule: {
          id: 'sched-1',
          name: 'Night Photography'
        }
      },
      isLoading: false
    })

    const { container } = render(<ActiveScheduleBanner />)

    // Check for SVG icon
    const icon = container.querySelector('svg')
    expect(icon).toBeInTheDocument()
  })
})
