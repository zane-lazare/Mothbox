import { useState } from 'react'
import PropTypes from 'prop-types'
import toast from 'react-hot-toast'
import { CheckCircleIcon, ExclamationTriangleIcon, PlayIcon, InformationCircleIcon } from '@heroicons/react/24/solid'
import {
  useActiveSchedule,
  useDeactivateSchedule,
  useNextActions,
  useSchedules,
  useActivateSchedule,
} from '../../hooks/useSchedules'
import { TEXT_STYLES, BUTTON_STYLES } from './constants'

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
 * @param {Object} action - Action object from preview API
 * @returns {string} Human-readable action name
 */
function getActionDisplayName(action) {
  if (!action) return ''
  // action has: time, action_name, action_type, offset_minutes, description
  const actionName = action.action_name || action.action_type || ''
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
  const [isActivating, setIsActivating] = useState(false)
  const { data } = useActiveSchedule()
  const { data: schedulesData } = useSchedules({ include_builtin: true })
  const { mutate: deactivate, isPending: isDeactivating } = useDeactivateSchedule({
    onError: (error) => {
      toast.error(`Failed to deactivate: ${error.message}`)
    },
  })
  const { mutate: activate } = useActivateSchedule()

  const activeSchedule = data?.active_schedule
  const schedules = schedulesData?.schedules || []

  // Find first enabled schedule (when no active schedule)
  const enabledSchedule = !activeSchedule
    ? schedules.find((s) => s.enabled)
    : null

  // Fetch next actions from persisted entries (Issue #331)
  // Uses pre-expanded cron entries stored in active_state.json instead of preview API
  const { data: nextActionsData } = useNextActions(
    { limit: 5 },
    {
      enabled: !!activeSchedule,
      refetchInterval: 60 * 1000, // Refresh every 60 seconds to filter past actions
    }
  )

  const handleDeactivate = () => {
    deactivate()
  }

  const handleActivate = (schedule) => {
    setIsActivating(true)
    activate(
      { id: schedule.schedule_id },
      {
        onSuccess: () => {
          setIsActivating(false)
        },
        onError: (error) => {
          toast.error(`Failed to activate: ${error.message}`)
          setIsActivating(false)
        },
      }
    )
  }

  // State 1: Active schedule (green banner)
  if (activeSchedule) {
    const { name } = activeSchedule
    const coordinatesSource = data?.coordinates_source
    const latitude = data?.latitude
    const longitude = data?.longitude
    const timezoneName = data?.timezone_name

    // Get next FUTURE action from persisted entries - already filtered by API
    // Next actions API structure: { actions: [{ time, action_name, action_type }] }
    const now = new Date()
    const futureActions = (nextActionsData?.actions || [])
      .filter((action) => new Date(action.time) > now)
    const nextAction = futureActions[0] || null
    const nextTime = nextAction ? formatTime(nextAction.time) : null
    const nextActionName = nextAction ? getActionDisplayName(nextAction) : null

    return (
      <div
        role="status"
        data-testid="active-schedule-banner"
        className="bg-green-50 border border-green-200 rounded-lg p-4"
      >
        {/* Top row: Active schedule name and Deactivate button */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircleIcon className="h-4 w-4 text-green-600" />
            <span className={`${TEXT_STYLES.titleSize} text-green-900`}>
              Active: <span className="font-normal">{name}</span>
            </span>
          </div>

          <button
            onClick={handleDeactivate}
            disabled={isDeactivating}
            className={`${BUTTON_STYLES.base} text-red-700 bg-red-50 border border-red-200 hover:bg-red-100`}
          >
            {isDeactivating ? 'Deactivating...' : 'Deactivate'}
          </button>
        </div>

        {/* Second row: Next action and time/location info */}
        <div className={`mt-2 flex items-center gap-4 ${TEXT_STYLES.description}`}>
          {nextTime && nextActionName && (
            <span data-testid="next-execution">
              Next: {nextTime} {nextActionName}
            </span>
          )}
          {coordinatesSource && (
            <span data-testid="location-info">
              {coordinatesSource === 'gps' &&
                `Time: Using GPS ${latitude?.toFixed(3)}, ${longitude?.toFixed(3)}`}
              {coordinatesSource === 'timezone' &&
                `Time: Using System Locale: ${timezoneName}`}
            </span>
          )}
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

  // State 2: Enabled but not active (red banner with activate button)
  if (enabledSchedule) {
    return (
      <div
        role="status"
        data-testid="enabled-schedule-banner"
        className="bg-red-50 border border-red-200 rounded-lg p-4"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ExclamationTriangleIcon className="h-4 w-4 text-red-600" />
            <span className={`${TEXT_STYLES.titleSize} text-red-900`}>
              Ready: <span className="font-normal">{enabledSchedule.name}</span>
            </span>
          </div>

          <button
            onClick={() => handleActivate(enabledSchedule)}
            disabled={isActivating}
            className={`${BUTTON_STYLES.base} text-white bg-green-600 hover:bg-green-700`}
          >
            <PlayIcon className="h-4 w-4" aria-hidden="true" />
            {isActivating ? 'Activating...' : 'Activate'}
          </button>
        </div>
      </div>
    )
  }

  // State 3: No enabled schedule (blue banner)
  return (
    <div
      role="status"
      data-testid="no-enabled-schedule-banner"
      className="bg-blue-50 border border-blue-200 rounded-lg p-4"
    >
      <div className="flex items-center gap-2">
        <InformationCircleIcon className="h-4 w-4 text-blue-600" />
        <span className={`${TEXT_STYLES.titleSize} text-blue-900`}>No schedule is enabled</span>
      </div>
    </div>
  )
}

ActiveScheduleBanner.propTypes = {}

export default ActiveScheduleBanner
