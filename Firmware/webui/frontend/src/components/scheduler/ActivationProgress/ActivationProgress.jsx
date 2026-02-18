/**
 * ActivationProgress - Real-time schedule activation status (Issue #327)
 *
 * Displays activation progress via WebSocket events:
 * - Spinner and progress bar during activation
 * - Phase labels for current operation
 * - Error state with retry option
 *
 * Uses the shared Socket.io connection from SocketProvider (#368).
 * Registers and unregisters event handlers without disconnecting the socket.
 *
 * @module components/scheduler/ActivationProgress/ActivationProgress
 */

import React, { useState, useEffect, useRef } from 'react'
import PropTypes from 'prop-types'
import useSocket from '../../../hooks/useSocket'
import { PHASE_LABELS } from './constants'

/**
 * ActivationProgress component
 *
 * @param {Object} props - Component props
 * @param {string} props.scheduleId - ID of the schedule being activated
 * @param {Function} [props.onComplete] - Callback when activation succeeds
 * @param {Function} [props.onError] - Callback when activation fails (receives error message)
 * @param {Function} [props.onRetry] - Callback when user clicks Retry button
 * @returns {JSX.Element} Activation progress display
 *
 * @example
 * <ActivationProgress
 *   scheduleId="sched-123"
 *   onComplete={() => toast.success('Activated!')}
 *   onError={(msg) => toast.error(msg)}
 *   onRetry={() => activateMutation.mutate()}
 * />
 */
export default function ActivationProgress({
  scheduleId,
  onComplete,
  onError,
  onRetry,
}) {
  const { socket } = useSocket()
  const [state, setState] = useState('activating')
  const [progress, setProgress] = useState(0)
  const [phase, setPhase] = useState('checking_conflicts')
  const [errorMessage, setErrorMessage] = useState('')

  // Store latest callbacks in refs to avoid effect re-runs when parent re-renders
  const onCompleteRef = useRef(onComplete)
  const onErrorRef = useRef(onError)

  // Update refs on every render to avoid stale closures in WebSocket handler.
  // Pattern explanation: This effect has no dependency array intentionally.
  // - Refs capture the latest callback on every render
  // - No dependencies means this runs after every render (not just on prop changes)
  // - This prevents stale closures in async WebSocket handlers without triggering socket reconnects
  // See: https://react.dev/reference/react/useRef#referencing-a-value-with-a-ref
  useEffect(() => {
    onCompleteRef.current = onComplete
    onErrorRef.current = onError
  })

  // Register event handlers on the shared socket
  useEffect(() => {
    if (!socket) return

    const handleConnectionError = () => {
      setState('error')
      setErrorMessage('Connection failed')
      onErrorRef.current?.('Connection failed')
    }

    const handleProgress = (data) => {
      // Filter events for this specific schedule
      if (data.schedule_id !== scheduleId) return

      setProgress(data.progress)
      setPhase(data.phase)

      if (data.phase === 'complete') {
        setState('complete')
        onCompleteRef.current?.()
      } else if (data.phase === 'failed') {
        setState('error')
        const msg = data.error || 'Activation failed'
        setErrorMessage(msg)
        onErrorRef.current?.(msg)
      }
    }

    socket.on('connect_error', handleConnectionError)
    socket.on('error', handleConnectionError)
    socket.on('schedule:activation_progress', handleProgress)

    return () => {
      socket.off('schedule:activation_progress', handleProgress)
      socket.off('connect_error', handleConnectionError)
      socket.off('error', handleConnectionError)
    }
  }, [socket, scheduleId])

  const handleRetryClick = () => {
    // Reset local state for retry - the shared socket handles reconnection
    setState('activating')
    setProgress(0)
    setPhase('checking_conflicts')
    setErrorMessage('')

    onRetry?.()
  }

  // Error state
  if (state === 'error') {
    return (
      <div
        data-testid="activation-progress"
        className="border border-red-300 dark:border-red-900/50 rounded-lg p-4 space-y-3 bg-red-50 dark:bg-transparent"
      >
        <div data-testid="activation-error" className="flex items-center justify-between">
          <span className="text-xs text-red-600 dark:text-red-400">Failed</span>
          <button
            type="button"
            onClick={handleRetryClick}
            className="text-sm text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white"
          >
            Retry
          </button>
        </div>
        <div className="text-xs text-gray-600 dark:text-gray-500">{errorMessage}</div>
      </div>
    )
  }

  // Complete state - minimal display, parent handles full active UI
  if (state === 'complete') {
    return (
      <div data-testid="activation-progress" className="space-y-2">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-green-500 rounded-full" />
          <span className="text-xs text-green-600 dark:text-green-400">Activated</span>
        </div>
      </div>
    )
  }

  // Activating state - progress bar with phase label
  return (
    <div data-testid="activation-progress" className="space-y-2">
      {/* ARIA live region for screen reader announcements */}
      <div role="status" aria-live="polite" aria-atomic="true" className="sr-only">
        {PHASE_LABELS[phase] || phase} - {progress}%
      </div>
      <div className="flex items-center gap-2">
        <div
          className="w-3 h-3 border-2 border-blue-500 dark:border-blue-400 border-t-transparent rounded-full animate-spin"
          aria-hidden="true"
        />
        <span className="text-xs text-blue-600 dark:text-blue-400">Activating</span>
      </div>
      <div className="h-1 bg-gray-200 dark:bg-gray-800 rounded-full overflow-hidden">
        <div
          data-testid="activation-progress-bar"
          className="h-full bg-blue-500 transition-all duration-300"
          style={{ width: `${progress}%` }}
          role="progressbar"
          aria-valuenow={progress}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Activation progress"
        />
      </div>
      <div className="flex justify-between text-xs">
        <span data-testid="activation-phase" className="text-gray-600 dark:text-gray-500">
          {PHASE_LABELS[phase] || phase}
        </span>
        <span className="text-gray-500 dark:text-gray-600">{progress}%</span>
      </div>
    </div>
  )
}

ActivationProgress.propTypes = {
  scheduleId: PropTypes.string.isRequired,
  onComplete: PropTypes.func,
  onError: PropTypes.func,
  onRetry: PropTypes.func,
}
