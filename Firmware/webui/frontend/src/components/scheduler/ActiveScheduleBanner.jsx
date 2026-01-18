import PropTypes from 'prop-types'
import toast from 'react-hot-toast'
import { CheckCircleIcon, ExclamationTriangleIcon } from '@heroicons/react/24/solid'
import { useActiveSchedule, useDeactivateSchedule, useSchedulePreview } from '../../hooks/useSchedules'

/**
 * Format time as HH:MM
 * @param {string} isoString - ISO date string
 * @returns {string} Formatted time
 */
function formatTime(isoString) {
  if (!isoString) return ''
  const date = new Date(isoString)
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })
}

/**
 * Get display name for an action
 * @param {Object} execution - Execution object with action info
 * @returns {string} Human-readable action name
 */
function getActionDisplayName(execution) {
  if (!execution) return ''
  // execution has: routine_name, action_type, action_name
  const actionName = execution.action_name || execution.action_type || ''
  // Convert snake_case to Title Case
  return actionName.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

/**
 * ActiveScheduleBanner displays a banner when a schedule is currently active.
 * Provides a button to deactivate the current schedule.
 *
 * @component
 * @example
 * return (
 *   <ActiveScheduleBanner />
 * )
 */
function ActiveScheduleBanner() {
  const { data } = useActiveSchedule()
  const { mutate: deactivate, isPending } = useDeactivateSchedule({
    onSuccess: () => {
      toast.success('Schedule deactivated successfully')
    },
    onError: (error) => {
      toast.error(`Failed to deactivate: ${error.message}`)
    },
  })

  // Fetch next execution for active schedule (only 1 day preview for efficiency)
  const scheduleId = data?.active_schedule?.schedule_id
  const { data: previewData } = useSchedulePreview(
    scheduleId,
    { days: 1 },
    { enabled: !!scheduleId }
  )

  // Don't render if no active schedule
  if (!data?.active_schedule) {
    return null
  }

  const { name } = data.active_schedule
  const coordinatesSource = data?.coordinates_source

  // Get next execution from preview
  const nextExecution = previewData?.executions?.[0]
  const nextTime = nextExecution ? formatTime(nextExecution.scheduled_time) : null
  const nextAction = nextExecution ? getActionDisplayName(nextExecution) : null

  const handleDeactivate = () => {
    deactivate()
  }

  return (
    <div
      role="status"
      data-testid="active-schedule-banner"
      className="bg-green-50 border border-green-200 rounded-lg p-4"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <CheckCircleIcon className="h-5 w-5 text-green-600" />
            <span className="text-green-900 font-medium">
              Active: <span className="font-normal">{name}</span>
            </span>
          </div>
          {nextTime && nextAction && (
            <span className="text-gray-500 text-sm" data-testid="next-execution">
              Next: {nextTime} {nextAction}
            </span>
          )}
        </div>

        <button
          onClick={handleDeactivate}
          disabled={isPending}
          className="px-4 py-2 text-sm font-medium text-red-700 bg-red-50 border border-red-200 rounded-md hover:bg-red-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isPending ? 'Deactivating...' : 'Deactivate'}
        </button>
      </div>

      {/* Warning when using timezone approximation for coordinates (Issue #331) */}
      {coordinatesSource === 'timezone' && (
        <div
          className="mt-3 px-3 py-2 bg-amber-100 border border-amber-200 rounded text-sm text-amber-800 flex items-center gap-2"
          data-testid="timezone-warning"
        >
          <ExclamationTriangleIcon className="h-4 w-4 flex-shrink-0" />
          <span>
            Using approximate location from system timezone. Solar times may be inaccurate.
            Sync GPS for precise scheduling.
          </span>
        </div>
      )}
    </div>
  )
}

ActiveScheduleBanner.propTypes = {}

export default ActiveScheduleBanner
