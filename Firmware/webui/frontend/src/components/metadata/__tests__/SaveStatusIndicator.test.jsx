import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react'
import SaveStatusIndicator from '../SaveStatusIndicator'

describe('SaveStatusIndicator', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  it('test_renders_nothing_when_idle', () => {
    const { container } = render(<SaveStatusIndicator status="idle" />)
    expect(container.firstChild).toBeNull()
  })

  it('test_shows_saving_state', () => {
    render(<SaveStatusIndicator status="saving" />)

    expect(screen.getByText('Saving...')).toBeInTheDocument()

    // Check for spinner (animated rotating element)
    const spinner = screen.getByRole('status').querySelector('.animate-spin')
    expect(spinner).toBeInTheDocument()
  })

  it('test_shows_saved_state_with_checkmark', () => {
    render(<SaveStatusIndicator status="saved" />)

    expect(screen.getByText('Saved')).toBeInTheDocument()

    // Check for checkmark icon (SVG with specific class)
    const icon = screen.getByRole('status').querySelector('svg')
    expect(icon).toBeInTheDocument()
    expect(icon).toHaveClass('text-green-500')
  })

  it('test_shows_error_state_with_message', () => {
    render(<SaveStatusIndicator status="error" />)

    expect(screen.getByText('Save failed')).toBeInTheDocument()

    // Check for error icon (SVG with red color)
    const icon = screen.getByRole('status').querySelector('svg')
    expect(icon).toBeInTheDocument()
    expect(icon).toHaveClass('text-red-500')
  })

  it('test_shows_retry_button_on_error', () => {
    const onRetry = vi.fn()
    render(<SaveStatusIndicator status="error" onRetry={onRetry} />)

    const retryButton = screen.getByRole('button', { name: /retry/i })
    expect(retryButton).toBeInTheDocument()
  })

  it('test_retry_button_calls_onRetry', () => {
    const onRetry = vi.fn()
    render(<SaveStatusIndicator status="error" onRetry={onRetry} />)

    const retryButton = screen.getByRole('button', { name: /retry/i })
    fireEvent.click(retryButton)

    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it('test_hides_after_timeout_on_success', async () => {
    const { rerender } = render(<SaveStatusIndicator status="idle" />)

    // Change to saved
    rerender(<SaveStatusIndicator status="saved" />)
    expect(screen.getByText('Saved')).toBeInTheDocument()

    // Fast-forward time by 2000ms wrapped in act
    await act(async () => {
      vi.advanceTimersByTime(2000)
    })

    // Component should be hidden
    expect(screen.queryByText('Saved')).not.toBeInTheDocument()
  })

  it('test_accessible_status_announcements', () => {
    render(<SaveStatusIndicator status="saving" />)

    const statusElement = screen.getByRole('status')
    expect(statusElement).toHaveAttribute('aria-live', 'polite')
  })

  it('test_custom_error_message', () => {
    const customError = 'Network connection failed'
    render(<SaveStatusIndicator status="error" errorMessage={customError} />)

    expect(screen.getByText(customError)).toBeInTheDocument()
    expect(screen.queryByText('Save failed')).not.toBeInTheDocument()
  })

  it('test_no_retry_button_when_onRetry_not_provided', () => {
    render(<SaveStatusIndicator status="error" />)

    expect(screen.queryByRole('button', { name: /retry/i })).not.toBeInTheDocument()
  })

  it('test_transitions_from_saving_to_saved', () => {
    const { rerender } = render(<SaveStatusIndicator status="saving" />)
    expect(screen.getByText('Saving...')).toBeInTheDocument()

    rerender(<SaveStatusIndicator status="saved" />)
    expect(screen.getByText('Saved')).toBeInTheDocument()
    expect(screen.queryByText('Saving...')).not.toBeInTheDocument()
  })

  it('test_does_not_auto_hide_error_state', async () => {
    render(<SaveStatusIndicator status="error" />)

    expect(screen.getByText('Save failed')).toBeInTheDocument()

    // Fast-forward time
    await act(async () => {
      vi.advanceTimersByTime(5000)
    })

    // Error should still be visible
    expect(screen.getByText('Save failed')).toBeInTheDocument()
  })

  it('test_clears_timeout_when_transitioning_from_saved', async () => {
    const { rerender } = render(<SaveStatusIndicator status="saved" />)

    // Advance time partway
    await act(async () => {
      vi.advanceTimersByTime(1000)
    })

    // Change status before timeout completes
    rerender(<SaveStatusIndicator status="saving" />)

    // Advance remaining time
    await act(async () => {
      vi.advanceTimersByTime(1000)
    })

    // Should still show saving, not be hidden
    expect(screen.getByText('Saving...')).toBeInTheDocument()
  })
})
