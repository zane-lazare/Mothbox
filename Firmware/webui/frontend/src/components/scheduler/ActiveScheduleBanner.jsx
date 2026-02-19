import { useState, useRef, useEffect } from 'react'
import PropTypes from 'prop-types'
import toast from 'react-hot-toast'
import { CheckCircleIcon, ExclamationTriangleIcon, PlayIcon, InformationCircleIcon, SignalIcon, SignalSlashIcon } from '@heroicons/react/24/solid'
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
  // Track coordinates source to drive conditional refetch (Issue #382)
  // Polls every 60s only while waiting for GPS fix (source === 'timezone')
  const [coordinatesSource, setCoordinatesSource] = useState(null)
  const { data } = useActiveSchedule({
    refetchInterval: coordinatesSource === 'timezone' ? 60 * 1000 : false,
  })
  const { data: schedulesData } = useSchedules({ include_builtin: true })
  const { mutate: deactivate, isPending: isDeactivating } = useDeactivateSchedule({
    onError: (error) => {
      toast.error(`Failed to deactivate: ${error.message}`)
    },
  })
  const { mutate: activate } = useActivateSchedule()

  const activeSchedule = data?.active_schedule

  // Track previous coordinates source for transition detection (Issue #382)
  const prevCoordinatesSourceRef = useRef(data?.coordinates_source)
  useEffect(() => {
    const currentSource = data?.coordinates_source
    const prevSource = prevCoordinatesSourceRef.current
    if (prevSource === 'timezone' && currentSource === 'gps') {
      toast.success('GPS fix acquired — solar times updated')
    }
    prevCoordinatesSourceRef.current = currentSource
    // Update state to re-evaluate refetchInterval (stops polling after GPS acquired)
    setCoordinatesSource(currentSource ?? null)
  }, [data?.coordinates_source])

  const schedules = schedulesData?.schedules || []

  // Find first enabled schedule (when no active schedule)
  const enabledSchedule = !activeSchedule
    ? schedules.find((s) => s.enabled)
    : null

  // Fetch next actions from persisted entries (Issue #331)
  // Uses pre-expanded cron entries stored in active_state.json instead of preview API
  const { data: nextActionsData, isError: nextActionsError } = useNextActions(
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
    const displaySource = data?.coordinates_source
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
          {nextActionsError ? (
            <span className={TEXT_STYLES.meta}>
              <ExclamationTriangleIcon className="h-4 w-4 inline mr-1 text-yellow-500" />
              Failed to load next actions
            </span>
          ) : nextTime && nextActionName ? (
            <span data-testid="next-execution">
              Next: {nextTime} {nextActionName}
            </span>
          ) : null}
          {/* Coordinate source display (Issue #382) */}
          {displaySource === 'timezone' && (
            <span data-testid="location-info" className="flex items-center gap-1 text-amber-700">
              <SignalSlashIcon className="h-4 w-4 animate-pulse" />
              Using {timezoneName || 'system locale'}. Waiting for GPS...
            </span>
          )}
          {displaySource === 'gps' && (
            <span data-testid="location-info" className="flex items-center gap-1 text-green-700">
              <SignalIcon className="h-4 w-4" />
              GPS: {latitude?.toFixed(3)}, {longitude?.toFixed(3)}
            </span>
          )}
          {displaySource === 'explicit' && (
            <span data-testid="location-info" className="flex items-center gap-1">
              {latitude?.toFixed(3)}, {longitude?.toFixed(3)}
            </span>
          )}
        </div>
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
