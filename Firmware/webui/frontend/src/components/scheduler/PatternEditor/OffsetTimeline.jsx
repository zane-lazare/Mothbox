import { useState } from 'react'
import PropTypes from 'prop-types'
import {
  BoltIcon,
  CameraIcon,
  MapPinIcon,
  CogIcon,
} from '@heroicons/react/24/solid'

const actionTypeIcons = {
  gpio: BoltIcon,
  camera: CameraIcon,
  gps_sync: MapPinIcon,
  service: CogIcon,
}

const OffsetTimeline = ({ actions = [], duration }) => {
  const [hoveredMarkerIndex, setHoveredMarkerIndex] = useState(null)

  // Handle empty actions
  if (!actions || actions.length === 0) {
    return (
      <div className="flex items-center justify-center py-8 text-gray-500 dark:text-gray-400">
        <p>No actions to display</p>
      </div>
    )
  }

  // Sort actions by offset for consistent display
  const sortedActions = [...actions].sort((a, b) => a.offset_minutes - b.offset_minutes)

  // Calculate duration: use prop, or max offset, or default to 1
  const maxOffset = Math.max(...sortedActions.map(a => a.offset_minutes), 0)
  const timelineDuration = duration ?? (maxOffset > 0 ? maxOffset : 1)

  // Calculate marker positions
  const getMarkerPosition = (offsetMinutes) => {
    if (timelineDuration === 0) return 0
    return (offsetMinutes / timelineDuration) * 100
  }

  return (
    <div
      role="region"
      aria-label="Action timeline visualization"
      className="w-full py-4"
    >
      {/* Duration labels */}
      <div className="flex justify-between mb-2 text-sm text-gray-600 dark:text-gray-400">
        <span>0min</span>
        <span>{timelineDuration}min</span>
      </div>

      {/* Timeline container */}
      <div className="relative w-full">
        {/* Timeline bar */}
        <div
          data-testid="timeline-bar"
          className="h-2 bg-gray-300 dark:bg-gray-700 rounded-full"
        />

        {/* Markers */}
        {sortedActions.map((action, index) => {
          const Icon = actionTypeIcons[action.action_type] || CogIcon
          const position = getMarkerPosition(action.offset_minutes)
          const isHovered = hoveredMarkerIndex === index

          return (
            <div
              key={index}
              className="absolute"
              style={{
                left: `${position}%`,
                top: '50%',
                transform: 'translate(-50%, -50%)',
              }}
            >
              <button
                type="button"
                data-testid={`timeline-marker-${index}`}
                aria-label={`${action.action_type} action: ${action.action_name} at ${action.offset_minutes}min`}
                className="flex items-center justify-center w-8 h-8 bg-blue-100 dark:bg-blue-900 rounded-full border-2 border-blue-600 dark:border-blue-300 hover:scale-110 transition-transform"
                onMouseEnter={() => setHoveredMarkerIndex(index)}
                onMouseLeave={() => setHoveredMarkerIndex(null)}
              >
                <Icon className="w-4 h-4 text-blue-600 dark:text-blue-300" />
              </button>

              {/* Tooltip */}
              {isHovered && (
                <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 px-3 py-2 bg-gray-900 dark:bg-gray-800 text-white text-sm rounded shadow-lg whitespace-nowrap z-10">
                  <div className="font-semibold">{action.action_name}</div>
                  <div className="text-gray-300 dark:text-gray-400">
                    {action.action_type} at {action.offset_minutes} minutes
                  </div>
                  {action.description && (
                    <div className="text-gray-400 dark:text-gray-500 text-xs mt-1">
                      {action.description}
                    </div>
                  )}
                  {/* Tooltip arrow */}
                  <div className="absolute left-1/2 -translate-x-1/2 top-full w-0 h-0 border-l-4 border-l-transparent border-r-4 border-r-transparent border-t-4 border-t-gray-900 dark:border-t-gray-800" />
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

OffsetTimeline.propTypes = {
  actions: PropTypes.arrayOf(
    PropTypes.shape({
      action_type: PropTypes.oneOf(['gpio', 'camera', 'gps_sync', 'service']).isRequired,
      action_name: PropTypes.string.isRequired,
      offset_minutes: PropTypes.number.isRequired,
      description: PropTypes.string,
    })
  ),
  duration: PropTypes.number,
}

export default OffsetTimeline
