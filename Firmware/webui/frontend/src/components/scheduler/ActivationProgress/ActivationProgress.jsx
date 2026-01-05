/**
 * ActivationProgress - Real-time schedule activation status (Issue #327)
 *
 * Displays activation progress via WebSocket events:
 * - Spinner and progress bar during activation
 * - Phase labels for current operation
 * - Error state with retry option
 *
 * The component manages its own Socket.io connection and listens for
 * `schedule:activation_progress` events filtered by scheduleId.
 *
 * @important Only one ActivationProgress should be rendered at a time.
 * Multiple instances will create separate WebSocket connections.
 * The scheduler UI enforces single-schedule activation.
 *
 * @module components/scheduler/ActivationProgress/ActivationProgress
 */

import React, { useState, useEffect, useRef } from 'react'
import PropTypes from 'prop-types'
import { io } from 'socket.io-client'
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
  const [state, setState] = useState('activating')
  const [progress, setProgress] = useState(0)
  const [phase, setPhase] = useState('checking_conflicts')
  const [errorMessage, setErrorMessage] = useState('')
  const [reconnectTrigger, setReconnectTrigger] = useState(0)
  const socketRef = useRef(null)

  // Store latest callbacks in refs to avoid effect re-runs when parent re-renders
  const onCompleteRef = useRef(onComplete)
  const onErrorRef = useRef(onError)

  // Update refs on every render to avoid stale closures in WebSocket handler.
  // This is intentional - refs capture the latest callback without triggering effect re-runs.
  useEffect(() => {
    onCompleteRef.current = onComplete
    onErrorRef.current = onError
  })

  useEffect(() => {
    // Setup WebSocket connection using window.location.origin for robust URL handling
    const wsUrl = window.location.origin

    try {
      socketRef.current = io(wsUrl, {
        transports: ['websocket', 'polling'],
      })

      socketRef.current.on('schedule:activation_progress', (data) => {
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
      })
    } catch (error) {
      // Handle WebSocket connection failure gracefully
      console.error('WebSocket connection failed:', error)
      setState('error')
      setErrorMessage('Connection failed')
      onErrorRef.current?.('Connection failed')
    }

    return () => {
      if (socketRef.current) {
        socketRef.current.off('schedule:activation_progress')
        socketRef.current.disconnect()
      }
    }
  }, [scheduleId, reconnectTrigger])

  const handleRetryClick = () => {
    // Disconnect old socket to prevent stale messages from previous attempt
    if (socketRef.current) {
      socketRef.current.off('schedule:activation_progress')
      socketRef.current.disconnect()
      socketRef.current = null
    }

    // Reset state for retry
    setState('activating')
    setProgress(0)
    setPhase('checking_conflicts')
    setErrorMessage('')

    // Force effect re-run to reconnect socket
    setReconnectTrigger((prev) => prev + 1)

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
