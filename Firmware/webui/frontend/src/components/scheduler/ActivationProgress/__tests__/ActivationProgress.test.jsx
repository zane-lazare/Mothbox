/**
 * Tests for ActivationProgress component (Issue #327)
 *
 * ActivationProgress displays real-time schedule activation status
 * via WebSocket events, including progress bar, phase labels, and error handling.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ActivationProgress from '../ActivationProgress'
import { PHASE_LABELS } from '../constants'

// Mock socket.io-client
const mockSocket = {
  on: vi.fn(),
  off: vi.fn(),
  disconnect: vi.fn(),
}

vi.mock('socket.io-client', () => ({
  io: vi.fn(() => mockSocket),
}))

/**
 * Helper to simulate WebSocket progress events
 * Wraps state updates in act() to avoid React warnings
 * @param {Object} data - Event data with schedule_id, phase, progress, and optional error
 */
const simulateProgressEvent = (data) => {
  const handler = mockSocket.on.mock.calls.find(
    (call) => call[0] === 'schedule:activation_progress'
  )?.[1]
  act(() => {
    handler?.(data)
  })
}

describe('ActivationProgress', () => {
  beforeEach(() => {
    mockSocket.on.mockClear()
    mockSocket.off.mockClear()
    mockSocket.disconnect.mockClear()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  // ==========================================================================
  // Rendering Tests
  // ==========================================================================

  describe('Rendering', () => {
    it('renders with data-testid="activation-progress"', () => {
      render(<ActivationProgress scheduleId="sched-1" />)
      expect(screen.getByTestId('activation-progress')).toBeInTheDocument()
    })

    it('shows activating state initially', () => {
      render(<ActivationProgress scheduleId="sched-1" />)
      expect(screen.getByText('Activating')).toBeInTheDocument()
    })

    it('renders progress bar', () => {
      render(<ActivationProgress scheduleId="sched-1" />)
      expect(screen.getByTestId('activation-progress-bar')).toBeInTheDocument()
    })

    it('renders phase label', () => {
      render(<ActivationProgress scheduleId="sched-1" />)
      expect(screen.getByTestId('activation-phase')).toBeInTheDocument()
    })

    it('shows initial phase label', () => {
      render(<ActivationProgress scheduleId="sched-1" />)
      expect(screen.getByTestId('activation-phase')).toHaveTextContent(
        PHASE_LABELS.checking_conflicts
      )
    })

    it('shows initial progress of 0%', () => {
      render(<ActivationProgress scheduleId="sched-1" />)
      expect(screen.getByText('0%')).toBeInTheDocument()
    })
  })

  // ==========================================================================
  // Progress Updates
  // ==========================================================================

  describe('Progress Updates', () => {
    it('updates progress bar when receiving progress events', async () => {
      render(<ActivationProgress scheduleId="sched-1" />)

      simulateProgressEvent({
        schedule_id: 'sched-1',
        phase: 'generating_cron',
        progress: 30,
      })

      await waitFor(() => {
        const progressBar = screen.getByTestId('activation-progress-bar')
        expect(progressBar).toHaveStyle({ width: '30%' })
      })
    })

    it('updates progress percentage text', async () => {
      render(<ActivationProgress scheduleId="sched-1" />)

      simulateProgressEvent({
        schedule_id: 'sched-1',
        phase: 'applying_cron',
        progress: 60,
      })

      await waitFor(() => {
        expect(screen.getByText('60%')).toBeInTheDocument()
      })
    })

    it('updates phase label for each phase', async () => {
      render(<ActivationProgress scheduleId="sched-1" />)

      simulateProgressEvent({
        schedule_id: 'sched-1',
        phase: 'generating_cron',
        progress: 30,
      })

      await waitFor(() => {
        expect(screen.getByTestId('activation-phase')).toHaveTextContent(
          PHASE_LABELS.generating_cron
        )
      })
    })

    it('displays applying_cron phase correctly', async () => {
      render(<ActivationProgress scheduleId="sched-1" />)

      simulateProgressEvent({
        schedule_id: 'sched-1',
        phase: 'applying_cron',
        progress: 60,
      })

      await waitFor(() => {
        expect(screen.getByTestId('activation-phase')).toHaveTextContent('Writing crontab...')
      })
    })

    it('displays updating_state phase correctly', async () => {
      render(<ActivationProgress scheduleId="sched-1" />)

      simulateProgressEvent({
        schedule_id: 'sched-1',
        phase: 'updating_state',
        progress: 90,
      })

      await waitFor(() => {
        expect(screen.getByTestId('activation-phase')).toHaveTextContent('Updating state...')
      })
    })

    it('falls back to raw phase name if label not found', async () => {
      render(<ActivationProgress scheduleId="sched-1" />)

      simulateProgressEvent({
        schedule_id: 'sched-1',
        phase: 'unknown_phase',
        progress: 50,
      })

      await waitFor(() => {
        expect(screen.getByTestId('activation-phase')).toHaveTextContent('unknown_phase')
      })
    })
  })

  // ==========================================================================
  // Complete State
  // ==========================================================================

  describe('Complete State', () => {
    it('shows complete state when phase is complete', async () => {
      render(<ActivationProgress scheduleId="sched-1" />)

      simulateProgressEvent({
        schedule_id: 'sched-1',
        phase: 'complete',
        progress: 100,
      })

      await waitFor(() => {
        expect(screen.getByText('Activated')).toBeInTheDocument()
      })
    })

    it('calls onComplete callback when phase is complete', async () => {
      const onComplete = vi.fn()
      render(<ActivationProgress scheduleId="sched-1" onComplete={onComplete} />)

      simulateProgressEvent({
        schedule_id: 'sched-1',
        phase: 'complete',
        progress: 100,
      })

      await waitFor(() => {
        expect(onComplete).toHaveBeenCalledTimes(1)
      })
    })
  })

  // ==========================================================================
  // Error State
  // ==========================================================================

  describe('Error State', () => {
    it('shows error state when phase is failed', async () => {
      render(<ActivationProgress scheduleId="sched-1" />)

      simulateProgressEvent({
        schedule_id: 'sched-1',
        phase: 'failed',
        progress: 0,
        error: 'Could not write to crontab',
      })

      await waitFor(() => {
        expect(screen.getByTestId('activation-error')).toBeInTheDocument()
      })
    })

    it('displays error message', async () => {
      render(<ActivationProgress scheduleId="sched-1" />)

      simulateProgressEvent({
        schedule_id: 'sched-1',
        phase: 'failed',
        progress: 0,
        error: 'Could not write to crontab',
      })

      await waitFor(() => {
        expect(screen.getByText('Could not write to crontab')).toBeInTheDocument()
      })
    })

    it('shows "Failed" label in error state', async () => {
      render(<ActivationProgress scheduleId="sched-1" />)

      simulateProgressEvent({
        schedule_id: 'sched-1',
        phase: 'failed',
        progress: 0,
      })

      await waitFor(() => {
        expect(screen.getByText('Failed')).toBeInTheDocument()
      })
    })

    it('shows Retry button in error state', async () => {
      render(<ActivationProgress scheduleId="sched-1" />)

      simulateProgressEvent({
        schedule_id: 'sched-1',
        phase: 'failed',
        progress: 0,
      })

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument()
      })
    })

    it('calls onError callback when phase is failed', async () => {
      const onError = vi.fn()
      render(<ActivationProgress scheduleId="sched-1" onError={onError} />)

      simulateProgressEvent({
        schedule_id: 'sched-1',
        phase: 'failed',
        progress: 0,
        error: 'Could not write to crontab',
      })

      await waitFor(() => {
        expect(onError).toHaveBeenCalledTimes(1)
        expect(onError).toHaveBeenCalledWith('Could not write to crontab')
      })
    })

    it('uses default error message when none provided', async () => {
      const onError = vi.fn()
      render(<ActivationProgress scheduleId="sched-1" onError={onError} />)

      simulateProgressEvent({
        schedule_id: 'sched-1',
        phase: 'failed',
        progress: 0,
      })

      await waitFor(() => {
        expect(onError).toHaveBeenCalledWith('Activation failed')
        expect(screen.getByText('Activation failed')).toBeInTheDocument()
      })
    })
  })

  // ==========================================================================
  // Retry Functionality
  // ==========================================================================

  describe('Retry Functionality', () => {
    it('calls onRetry when Retry button is clicked', async () => {
      const user = userEvent.setup()
      const onRetry = vi.fn()
      render(<ActivationProgress scheduleId="sched-1" onRetry={onRetry} />)

      simulateProgressEvent({
        schedule_id: 'sched-1',
        phase: 'failed',
        progress: 0,
      })

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /retry/i }))

      expect(onRetry).toHaveBeenCalledTimes(1)
    })

    it('resets to activating state when Retry is clicked', async () => {
      const user = userEvent.setup()
      render(<ActivationProgress scheduleId="sched-1" />)

      simulateProgressEvent({
        schedule_id: 'sched-1',
        phase: 'failed',
        progress: 0,
      })

      await waitFor(() => {
        expect(screen.getByTestId('activation-error')).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /retry/i }))

      await waitFor(() => {
        expect(screen.queryByTestId('activation-error')).not.toBeInTheDocument()
        expect(screen.getByText('Activating')).toBeInTheDocument()
      })
    })
  })

  // ==========================================================================
  // Schedule ID Filtering
  // ==========================================================================

  describe('Schedule ID Filtering', () => {
    it('ignores progress events for other schedules', async () => {
      const onComplete = vi.fn()
      render(<ActivationProgress scheduleId="sched-1" onComplete={onComplete} />)

      // Send event for different schedule
      simulateProgressEvent({
        schedule_id: 'sched-2',
        phase: 'complete',
        progress: 100,
      })

      // Wait a bit to ensure no state change
      await new Promise((resolve) => setTimeout(resolve, 50))

      // Should still be in activating state
      expect(screen.getByText('Activating')).toBeInTheDocument()
      expect(onComplete).not.toHaveBeenCalled()
    })

    it('processes events for matching schedule', async () => {
      const onComplete = vi.fn()
      render(<ActivationProgress scheduleId="sched-1" onComplete={onComplete} />)

      simulateProgressEvent({
        schedule_id: 'sched-1',
        phase: 'complete',
        progress: 100,
      })

      await waitFor(() => {
        expect(onComplete).toHaveBeenCalledTimes(1)
      })
    })
  })

  // ==========================================================================
  // Socket Cleanup
  // ==========================================================================

  describe('Socket Cleanup', () => {
    it('disconnects socket on unmount', () => {
      const { unmount } = render(<ActivationProgress scheduleId="sched-1" />)

      unmount()

      expect(mockSocket.disconnect).toHaveBeenCalledTimes(1)
    })

    it('registers event listener on mount', () => {
      render(<ActivationProgress scheduleId="sched-1" />)

      expect(mockSocket.on).toHaveBeenCalledWith(
        'schedule:activation_progress',
        expect.any(Function)
      )
    })
  })

  // ==========================================================================
  // Accessibility
  // ==========================================================================

  describe('Accessibility', () => {
    it('progress bar has role="progressbar"', () => {
      render(<ActivationProgress scheduleId="sched-1" />)
      expect(screen.getByRole('progressbar')).toBeInTheDocument()
    })

    it('progress bar has aria-valuenow', () => {
      render(<ActivationProgress scheduleId="sched-1" />)
      expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '0')
    })

    it('progress bar has aria-valuemin and aria-valuemax', () => {
      render(<ActivationProgress scheduleId="sched-1" />)
      const progressBar = screen.getByRole('progressbar')
      expect(progressBar).toHaveAttribute('aria-valuemin', '0')
      expect(progressBar).toHaveAttribute('aria-valuemax', '100')
    })

    it('progress bar has aria-label', () => {
      render(<ActivationProgress scheduleId="sched-1" />)
      expect(screen.getByRole('progressbar')).toHaveAttribute('aria-label', 'Activation progress')
    })

    it('updates aria-valuenow with progress', async () => {
      render(<ActivationProgress scheduleId="sched-1" />)

      simulateProgressEvent({
        schedule_id: 'sched-1',
        phase: 'generating_cron',
        progress: 30,
      })

      await waitFor(() => {
        expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '30')
      })
    })
  })

  // ==========================================================================
  // Dark Mode
  // ==========================================================================

  describe('Dark Mode', () => {
    it('has dark mode classes on progress bar container', () => {
      render(<ActivationProgress scheduleId="sched-1" />)
      const container = screen.getByTestId('activation-progress-bar').parentElement
      expect(container).toHaveClass('bg-gray-800')
    })

    it('has dark mode classes on error state', async () => {
      render(<ActivationProgress scheduleId="sched-1" />)

      simulateProgressEvent({
        schedule_id: 'sched-1',
        phase: 'failed',
        progress: 0,
      })

      await waitFor(() => {
        const wrapper = screen.getByTestId('activation-progress')
        expect(wrapper).toHaveClass('border-red-900/50')
      })
    })
  })

  // ==========================================================================
  // Edge Cases
  // ==========================================================================

  describe('Edge Cases', () => {
    it('handles missing onComplete callback gracefully', async () => {
      render(<ActivationProgress scheduleId="sched-1" />)

      // Should not throw
      simulateProgressEvent({
        schedule_id: 'sched-1',
        phase: 'complete',
        progress: 100,
      })

      await waitFor(() => {
        expect(screen.getByText('Activated')).toBeInTheDocument()
      })
    })

    it('handles missing onError callback gracefully', async () => {
      render(<ActivationProgress scheduleId="sched-1" />)

      // Should not throw
      simulateProgressEvent({
        schedule_id: 'sched-1',
        phase: 'failed',
        progress: 0,
      })

      await waitFor(() => {
        expect(screen.getByTestId('activation-error')).toBeInTheDocument()
      })
    })

    it('handles missing onRetry callback gracefully', async () => {
      const user = userEvent.setup()
      render(<ActivationProgress scheduleId="sched-1" />)

      simulateProgressEvent({
        schedule_id: 'sched-1',
        phase: 'failed',
        progress: 0,
      })

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument()
      })

      // Should not throw
      await user.click(screen.getByRole('button', { name: /retry/i }))

      await waitFor(() => {
        expect(screen.getByText('Activating')).toBeInTheDocument()
      })
    })
  })
})
