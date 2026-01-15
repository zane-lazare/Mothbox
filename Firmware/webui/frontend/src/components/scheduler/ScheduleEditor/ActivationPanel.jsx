/**
 * ActivationPanel - Schedule activation UI for editor drawer (Issue #331)
 *
 * Displays activation status, activate/deactivate controls, progress during
 * activation, and schedule statistics (routines count, executions, next time).
 *
 * @module components/scheduler/ScheduleEditor/ActivationPanel
 */

import { useState, useCallback } from 'react'
import PropTypes from 'prop-types'
import toast from 'react-hot-toast'
import {
  useActiveSchedule,
  useActivateSchedule,
  useDeactivateSchedule,
  useSchedulePreview,
} from '../../../hooks/useSchedules'
import ActivationProgress from '../ActivationProgress/ActivationProgress'

/**
 * Format time as HH:MM
 * @param {string} isoString - ISO date string
 * @returns {string} Formatted time
 */
function formatTime(isoString) {
  if (!isoString) return '--:--'
  const date = new Date(isoString)
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })
}

/**
 * ActivationPanel component
 *
 * @param {Object} props - Component props
 * @param {string} props.scheduleId - ID of the schedule being edited
 * @param {number} props.routineCount - Number of routines in the schedule
 * @param {boolean} props.hasUnsavedChanges - Whether there are unsaved changes
 * @returns {JSX.Element} Activation panel
 */
export default function ActivationPanel({ scheduleId, routineCount, hasUnsavedChanges }) {
  const [isActivating, setIsActivating] = useState(false)

  // Check if this schedule is the active one
  const { data: activeData, refetch: refetchActive } = useActiveSchedule()
  const isActive = activeData?.active_schedule?.schedule_id === scheduleId

  // Get preview data for stats
  const { data: previewData } = useSchedulePreview(
    scheduleId,
    { days: 1 },
    { enabled: !!scheduleId && !hasUnsavedChanges }
  )

  // Activation mutation
  const { mutate: activate } = useActivateSchedule({
    onMutate: () => {
      setIsActivating(true)
    },
    onError: (error) => {
      setIsActivating(false)
      toast.error(`Activation failed: ${error.message}`)
    },
  })

  // Deactivation mutation
  const { mutate: deactivate, isPending: isDeactivating } = useDeactivateSchedule({
    onSuccess: () => {
      toast.success('Schedule deactivated')
    },
    onError: (error) => {
      toast.error(`Deactivation failed: ${error.message}`)
    },
  })

  // Handle activation complete
  const handleActivationComplete = useCallback(() => {
    setIsActivating(false)
    refetchActive()
    toast.success('Schedule activated')
  }, [refetchActive])

  // Handle activation error
  const handleActivationError = useCallback(() => {
    setIsActivating(false)
  }, [])

  // Handle retry
  const handleRetry = useCallback(() => {
    if (scheduleId) {
      activate({ id: scheduleId })
    }
  }, [scheduleId, activate])

  // Handle activate click
  const handleActivate = () => {
    console.log('[ActivationPanel] handleActivate called, scheduleId:', scheduleId)
    if (scheduleId) {
      activate({ id: scheduleId })
    } else {
      console.error('[ActivationPanel] scheduleId is falsy, not activating')
    }
  }

  // Handle deactivate click
  const handleDeactivate = () => {
    deactivate()
  }

  // Calculate stats
  const executionCount = previewData?.total || 0
  const nextExecution = previewData?.executions?.[0]
  const nextTime = nextExecution ? formatTime(nextExecution.scheduled_time) : '--:--'

  // Show progress during activation
  if (isActivating) {
    return (
      <div
        data-testid="activation-panel"
        className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 space-y-4"
      >
        <ActivationProgress
          scheduleId={scheduleId}
          onComplete={handleActivationComplete}
          onError={handleActivationError}
          onRetry={handleRetry}
        />
      </div>
    )
  }

  return (
    <div
      data-testid="activation-panel"
      className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 space-y-4"
    >
      {/* Status and button */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div
            className={`w-2 h-2 rounded-full ${
              isActive ? 'bg-green-500' : 'bg-gray-400'
            }`}
          />
          <span
            className={`text-xs ${
              isActive
                ? 'text-green-600 dark:text-green-400'
                : 'text-gray-500 dark:text-gray-400'
            }`}
          >
            {isActive ? 'Active' : 'Inactive'}
          </span>
        </div>

        {isActive ? (
          <button
            type="button"
            onClick={handleDeactivate}
            disabled={isDeactivating}
            className="text-sm text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 disabled:opacity-50"
          >
            {isDeactivating ? 'Deactivating...' : 'Deactivate'}
          </button>
        ) : (
          <button
            type="button"
            onClick={handleActivate}
            disabled={hasUnsavedChanges || !scheduleId}
            title={hasUnsavedChanges ? 'Save changes before activating' : ''}
            className="text-sm px-3 py-1.5 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Activate
          </button>
        )}
      </div>

      {/* Unsaved changes warning */}
      {hasUnsavedChanges && !isActive && (
        <p className="text-xs text-amber-600 dark:text-amber-400">
          Save changes before activating
        </p>
      )}

      {/* Stats (only show when not activating and schedule exists) */}
      {scheduleId && !hasUnsavedChanges && (
        <div className="grid grid-cols-3 gap-4 pt-2 border-t border-gray-200 dark:border-gray-700">
          <div className="text-center">
            <div className="text-lg text-gray-900 dark:text-white">{routineCount}</div>
            <div className="text-xs text-gray-500 dark:text-gray-400">Routines</div>
          </div>
          <div className="text-center">
            <div className="text-lg text-gray-900 dark:text-white">{executionCount}</div>
            <div className="text-xs text-gray-500 dark:text-gray-400">Executions</div>
          </div>
          <div className="text-center">
            <div className="text-lg text-gray-900 dark:text-white">{nextTime}</div>
            <div className="text-xs text-gray-500 dark:text-gray-400">Next</div>
          </div>
        </div>
      )}
    </div>
  )
}

ActivationPanel.propTypes = {
  /** ID of the schedule being edited (null for new schedules) */
  scheduleId: PropTypes.string,
  /** Number of routines in the schedule */
  routineCount: PropTypes.number.isRequired,
  /** Whether there are unsaved changes in the editor */
  hasUnsavedChanges: PropTypes.bool.isRequired,
}
