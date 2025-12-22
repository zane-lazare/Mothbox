import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import toast from 'react-hot-toast'
import SchedulerToolbar from '../SchedulerToolbar'

// Mock react-hot-toast
vi.mock('react-hot-toast', () => ({
  default: { info: vi.fn(), success: vi.fn(), error: vi.fn() }
}))

describe('SchedulerToolbar', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders "New Schedule" button', () => {
    render(<SchedulerToolbar />)

    const button = screen.getByRole('button', { name: /new schedule/i })
    expect(button).toBeInTheDocument()
  })

  it('calls onNewSchedule when clicked', async () => {
    const user = userEvent.setup()
    const onNewSchedule = vi.fn()

    render(<SchedulerToolbar onNewSchedule={onNewSchedule} />)

    const button = screen.getByRole('button', { name: /new schedule/i })
    await user.click(button)

    expect(onNewSchedule).toHaveBeenCalledTimes(1)
  })

  it('shows PlusIcon', () => {
    render(<SchedulerToolbar />)

    const button = screen.getByRole('button', { name: /new schedule/i })
    const svg = button.querySelector('svg')

    expect(svg).toBeInTheDocument()
  })

  it('applies disabled state when isCreating', () => {
    render(<SchedulerToolbar isCreating={true} />)

    const button = screen.getByRole('button', { name: /new schedule/i })
    expect(button).toBeDisabled()
  })

  it('shows toast when clicked without onNewSchedule prop', async () => {
    const user = userEvent.setup()

    render(<SchedulerToolbar />)

    const button = screen.getByRole('button', { name: /new schedule/i })
    await user.click(button)

    expect(toast.info).toHaveBeenCalledWith('Schedule editor coming in Issue #227')
  })

  it('does not show toast when onNewSchedule is provided', async () => {
    const user = userEvent.setup()
    const onNewSchedule = vi.fn()

    render(<SchedulerToolbar onNewSchedule={onNewSchedule} />)

    const button = screen.getByRole('button', { name: /new schedule/i })
    await user.click(button)

    expect(toast.info).not.toHaveBeenCalled()
    expect(onNewSchedule).toHaveBeenCalledTimes(1)
  })

  it('does not call onNewSchedule when disabled', async () => {
    const user = userEvent.setup()
    const onNewSchedule = vi.fn()

    render(<SchedulerToolbar onNewSchedule={onNewSchedule} isCreating={true} />)

    const button = screen.getByRole('button', { name: /new schedule/i })
    await user.click(button)

    expect(onNewSchedule).not.toHaveBeenCalled()
  })

  it('applies correct button styles', () => {
    render(<SchedulerToolbar />)

    const button = screen.getByRole('button', { name: /new schedule/i })

    expect(button).toHaveClass('bg-blue-600')
    expect(button).toHaveClass('text-white')
    expect(button).toHaveClass('px-4')
    expect(button).toHaveClass('py-2')
    expect(button).toHaveClass('rounded-lg')
    expect(button).toHaveClass('hover:bg-blue-700')
  })

  it('applies disabled styles when isCreating', () => {
    render(<SchedulerToolbar isCreating={true} />)

    const button = screen.getByRole('button', { name: /new schedule/i })

    expect(button).toHaveClass('disabled:bg-gray-400')
    expect(button).toHaveClass('disabled:cursor-not-allowed')
  })

  it('defaults isCreating to false', () => {
    render(<SchedulerToolbar />)

    const button = screen.getByRole('button', { name: /new schedule/i })
    expect(button).not.toBeDisabled()
  })
})
