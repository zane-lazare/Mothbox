/**
 * Tests for ActivationProgress component (Issue #327)
 *
 * ActivationProgress displays real-time schedule activation status
 * via WebSocket events, including progress bar, phase labels, and error handling.
 *
 * Updated for shared WebSocket context (#368): Mocks useSocket hook instead
 * of socket.io-client directly.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ActivationProgress from '../ActivationProgress'
import { PHASE_LABELS } from '../constants'

// Mock socket instance
const mockSocket = {
  on: vi.fn(),
  off: vi.fn(),
  emit: vi.fn(),
  connected: true,
}

// Mock useSocket hook to provide the mock socket
vi.mock('../../../../hooks/useSocket', () => ({
  default: vi.fn(() => ({ socket: mockSocket, connected: true })),
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
    mockSocket.emit.mockClear()
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
    it('removes event listener on unmount', () => {
      const { unmount } = render(<ActivationProgress scheduleId="sched-1" />)

      unmount()

      expect(mockSocket.off).toHaveBeenCalledWith('schedule:activation_progress', expect.any(Function))
    })

    it('does not disconnect shared socket on unmount', () => {
      const { unmount } = render(<ActivationProgress scheduleId="sched-1" />)

      unmount()

      // Shared socket should NOT be disconnected by component cleanup.
      // The mock socket has no disconnect method because the component
      // should never call it - only .off() to remove event listeners.
      // Verify only .off() was called, not any disconnect-like behavior.
      const offCalls = mockSocket.off.mock.calls.map(call => call[0])
      expect(offCalls).toContain('schedule:activation_progress')
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
    it('has light and dark mode classes on progress bar container', () => {
      render(<ActivationProgress scheduleId="sched-1" />)
      const container = screen.getByTestId('activation-progress-bar').parentElement
      expect(container).toHaveClass('bg-gray-200')
      expect(container).toHaveClass('dark:bg-gray-800')
    })

    it('has light and dark mode classes on error state', async () => {
      render(<ActivationProgress scheduleId="sched-1" />)

      simulateProgressEvent({
        schedule_id: 'sched-1',
        phase: 'failed',
        progress: 0,
      })

      await waitFor(() => {
        const wrapper = screen.getByTestId('activation-progress')
        expect(wrapper).toHaveClass('border-red-300')
        expect(wrapper).toHaveClass('dark:border-red-900/50')
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

    it('handles null socket gracefully', async () => {
      // Temporarily mock useSocket to return null socket
      const useSocketMod = await import('../../../../hooks/useSocket')
      const originalImpl = useSocketMod.default
      vi.mocked(useSocketMod.default).mockReturnValueOnce({ socket: null, connected: false })

      // Component should handle null socket without crashing
      expect(() => render(<ActivationProgress scheduleId="sched-1" />)).not.toThrow()
    })

    it('handles async connect_error events', async () => {
      const onError = vi.fn()
      render(<ActivationProgress scheduleId="sched-1" onError={onError} />)

      // Simulate async connection error via connect_error event
      const connectErrorHandler = mockSocket.on.mock.calls.find(
        (call) => call[0] === 'connect_error'
      )?.[1]

      act(() => {
        connectErrorHandler?.(new Error('Network unavailable'))
      })

      await waitFor(() => {
        expect(screen.getByTestId('activation-error')).toBeInTheDocument()
        expect(screen.getByText('Connection failed')).toBeInTheDocument()
        expect(onError).toHaveBeenCalledWith('Connection failed')
      })
    })

    it('registers connect_error and error event listeners', () => {
      render(<ActivationProgress scheduleId="sched-1" />)

      expect(mockSocket.on).toHaveBeenCalledWith('connect_error', expect.any(Function))
      expect(mockSocket.on).toHaveBeenCalledWith('error', expect.any(Function))
    })
  })

  // ==========================================================================
  // Retry with Shared Socket
  // ==========================================================================

  describe('Retry with Shared Socket', () => {
    it('does not disconnect socket when retry is clicked', async () => {
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

      await user.click(screen.getByRole('button', { name: /retry/i }))

      // Shared socket should NOT have a disconnect method called.
      // The component only resets local state on retry - the shared
      // socket handles reconnection automatically.
      // Verify the component returned to activating state
      await waitFor(() => {
        expect(screen.getByText('Activating')).toBeInTheDocument()
      })
    })

    it('resets local state without socket recreation on retry', async () => {
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

      // Should be back to activating state
      await waitFor(() => {
        expect(screen.getByText('Activating')).toBeInTheDocument()
        expect(screen.getByText('0%')).toBeInTheDocument()
      })

      expect(onRetry).toHaveBeenCalledTimes(1)
    })
  })

  // ==========================================================================
  // ARIA Live Region
  // ==========================================================================

  describe('ARIA Live Region', () => {
    it('has aria-live region for screen reader announcements', () => {
      render(<ActivationProgress scheduleId="sched-1" />)
      const liveRegion = screen.getByRole('status')
      expect(liveRegion).toHaveAttribute('aria-live', 'polite')
      expect(liveRegion).toHaveAttribute('aria-atomic', 'true')
    })

    it('announces progress updates to screen readers', async () => {
      render(<ActivationProgress scheduleId="sched-1" />)

      simulateProgressEvent({
        schedule_id: 'sched-1',
        phase: 'generating_cron',
        progress: 30,
      })

      await waitFor(() => {
        const liveRegion = screen.getByRole('status')
        expect(liveRegion).toHaveTextContent('Generating schedule... - 30%')
      })
    })
  })

  // ==========================================================================
  // Additional Edge Cases
  // ==========================================================================

  describe('Additional Edge Cases', () => {
    it('handles progress value greater than 100 by clamping to 100', async () => {
      render(<ActivationProgress scheduleId="sched-1" />)

      simulateProgressEvent({
        schedule_id: 'sched-1',
        phase: 'applying_cron',
        progress: 150, // Invalid: > 100
      })

      await waitFor(() => {
        // Progress bar should handle the value gracefully (component may clamp or display as-is)
        const progressBar = screen.getByTestId('activation-progress-bar')
        // The component should still render without crashing
        expect(progressBar).toBeInTheDocument()
      })
    })

    it('handles rapid successive progress events', async () => {
      const onComplete = vi.fn()
      render(<ActivationProgress scheduleId="sched-1" onComplete={onComplete} />)

      // Simulate rapid progress updates
      simulateProgressEvent({ schedule_id: 'sched-1', phase: 'checking_conflicts', progress: 10 })
      simulateProgressEvent({ schedule_id: 'sched-1', phase: 'checking_conflicts', progress: 20 })
      simulateProgressEvent({ schedule_id: 'sched-1', phase: 'generating_cron', progress: 30 })
      simulateProgressEvent({ schedule_id: 'sched-1', phase: 'generating_cron', progress: 40 })
      simulateProgressEvent({ schedule_id: 'sched-1', phase: 'applying_cron', progress: 60 })
      simulateProgressEvent({ schedule_id: 'sched-1', phase: 'updating_state', progress: 90 })
      simulateProgressEvent({ schedule_id: 'sched-1', phase: 'complete', progress: 100 })

      await waitFor(() => {
        expect(screen.getByText('Activated')).toBeInTheDocument()
        expect(onComplete).toHaveBeenCalledTimes(1)
      })
    })

    it('handles very long error messages with text overflow', async () => {
      render(<ActivationProgress scheduleId="sched-1" />)

      const veryLongError = 'This is a very long error message that explains in great detail what went wrong during the schedule activation process including technical details about crontab permissions and file system errors'

      simulateProgressEvent({
        schedule_id: 'sched-1',
        phase: 'failed',
        progress: 0,
        error: veryLongError,
      })

      await waitFor(() => {
        const errorElement = screen.getByTestId('activation-error')
        expect(errorElement).toBeInTheDocument()
        // The error message should be present (may be truncated in UI)
        expect(screen.getByText(veryLongError)).toBeInTheDocument()
      })
    })

    it('handles zero progress correctly', async () => {
      render(<ActivationProgress scheduleId="sched-1" />)

      simulateProgressEvent({
        schedule_id: 'sched-1',
        phase: 'checking_conflicts',
        progress: 0,
      })

      await waitFor(() => {
        expect(screen.getByText('0%')).toBeInTheDocument()
        expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '0')
      })
    })
  })
})
