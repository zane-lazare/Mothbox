import PropTypes from 'prop-types'
import { useMemo } from 'react'

/**
 * Color mapping for action types.
 * Uses same colors as routineUtils for consistency.
 */
const ACTION_COLORS = {
  gpio: 'bg-orange-500/20 text-orange-400',
  camera: 'bg-blue-500/20 text-blue-400',
  hdr: 'bg-purple-500/20 text-purple-400',
  gps_sync: 'bg-green-500/20 text-green-400',
  service: 'bg-gray-500/20 text-gray-400',
}

/**
 * Get color classes for an action.
 */
function getActionColor(actionType) {
  return ACTION_COLORS[actionType] || ACTION_COLORS.camera
}

/**
 * Format time as HH:MM
 */
function formatTime(date) {
  return date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

/**
 * MiniTimeline Component
 *
 * Compact timeline showing schedule execution preview.
 * Only displays hours with executions, with gap indicators for skipped hours.
 *
 * @component
 * @example
 * <MiniTimeline executions={previewData.executions} conflicts={previewData.conflicts} />
 */
function MiniTimeline({ executions = [], conflicts = [] }) {
  // Flatten all actions from executions and group by hour
  const hourlyGroups = useMemo(() => {
    if (!executions?.length) return []

    // Collect all individual actions with their times and types
    const allActions = []
    executions.forEach(exec => {
      // Use actions within each execution for granular times
      if (exec.actions?.length) {
        exec.actions.forEach(action => {
          const date = new Date(action.time)
          allActions.push({
            date,
            hour: date.getHours(),
            timeStr: formatTime(date),
            actionType: action.action_type || 'camera',
            executionId: exec.execution_id,
          })
        })
      } else {
        // Fallback to execution start time if no actions
        const date = new Date(exec.start_time)
        allActions.push({
          date,
          hour: date.getHours(),
          timeStr: formatTime(date),
          actionType: 'camera',
          executionId: exec.execution_id,
        })
      }
    })

    // Sort actions by time
    allActions.sort((a, b) => a.date - b.date)

    // Group by hour
    const grouped = {}
    allActions.forEach(action => {
      if (!grouped[action.hour]) {
        grouped[action.hour] = []
      }
      grouped[action.hour].push(action)
    })

    // Sort hours and build result with gap indicators
    const sortedHours = Object.keys(grouped).map(Number).sort((a, b) => a - b)
    const result = []

    sortedHours.forEach((hour, index) => {
      // Add "continues" row if gap > 1 hour
      if (index > 0 && hour - sortedHours[index - 1] > 1) {
        result.push({ type: 'gap', key: `gap-${index}` })
      }
      result.push({
        type: 'hour',
        key: `hour-${hour}`,
        hour,
        hourStr: hour.toString().padStart(2, '0') + ':00',
        actions: grouped[hour],
      })
    })

    return result
  }, [executions])

  // Count total actions
  const totalActions = useMemo(() => {
    return hourlyGroups.reduce((sum, item) => {
      return sum + (item.type === 'hour' ? item.actions.length : 0)
    }, 0)
  }, [hourlyGroups])

  if (!executions?.length) {
    return (
      <div className="text-sm text-gray-500 dark:text-gray-400 italic p-4">
        Add routines to see preview
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs text-gray-500 dark:text-gray-400">Preview</span>
        <span className="text-xs text-gray-600 dark:text-gray-500">
          {totalActions} execution{totalActions !== 1 ? 's' : ''}
        </span>
      </div>

      <div className="border border-gray-200 dark:border-gray-800 rounded-lg divide-y divide-gray-200 dark:divide-gray-800 max-h-64 overflow-y-auto">
        {hourlyGroups.map((item) => {
          if (item.type === 'gap') {
            return (
              <div key={item.key} className="flex p-2 text-gray-400 dark:text-gray-700">
                <span className="w-12 text-xs">...</span>
                <span className="text-xs">continues</span>
              </div>
            )
          }

          return (
            <div key={item.key} className="flex p-2">
              <span className="w-12 text-xs text-gray-500 dark:text-gray-600 shrink-0">
                {item.hourStr}
              </span>
              <div className="flex gap-1 flex-wrap">
                {item.actions.map((action, i) => {
                  const colorClass = getActionColor(action.actionType)
                  const hasConflict = conflicts?.some(
                    (c) => c.execution_id === action.executionId
                  )

                  return (
                    <span
                      key={`${action.timeStr}-${i}`}
                      className={`text-xs px-1.5 py-0.5 rounded ${colorClass} ${
                        hasConflict ? 'ring-1 ring-red-400' : ''
                      }`}
                      title={action.actionType}
                    >
                      {action.timeStr}
                    </span>
                  )
                })}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

MiniTimeline.propTypes = {
  /** Array of execution objects from preview API */
  executions: PropTypes.arrayOf(
    PropTypes.shape({
      start_time: PropTypes.string,
      end_time: PropTypes.string,
      routine_id: PropTypes.string,
      routine_name: PropTypes.string,
      actions: PropTypes.arrayOf(
        PropTypes.shape({
          time: PropTypes.string,
          action_name: PropTypes.string,
          action_type: PropTypes.string,
        })
      ),
    })
  ),
  /** Array of conflict objects from preview API */
  conflicts: PropTypes.array,
}

export default MiniTimeline
