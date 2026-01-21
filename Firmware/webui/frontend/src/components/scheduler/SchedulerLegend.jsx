/**
 * SchedulerLegend - Unified action type legend for scheduler UI
 *
 * Single source of truth for the scheduler key/legend, displayed below
 * the ActiveScheduleBanner. Shows action type colors and conflict indicators.
 *
 * @module components/scheduler/SchedulerLegend
 */

import { memo } from 'react'
import {
  ACTION_TYPE_COLORS,
  ACTION_TYPE_LABELS,
  CONFLICT_COLORS,
} from './constants'

/**
 * Legend items derived from shared constants
 */
const LEGEND_ITEMS = [
  ...Object.entries(ACTION_TYPE_COLORS).map(([type, colors]) => ({
    color: colors.solid,
    label: ACTION_TYPE_LABELS[type],
  })),
  { color: CONFLICT_COLORS.error.ring, label: 'Collision', isRing: true },
  { color: CONFLICT_COLORS.warning.ring, label: 'Warning', isRing: true },
]

/**
 * SchedulerLegend component
 *
 * Displays a horizontal row of action type indicators with their labels.
 * Memoized since LEGEND_ITEMS is static and never changes.
 *
 * @returns {JSX.Element} Legend row component
 */
const SchedulerLegend = memo(function SchedulerLegend() {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-500 dark:text-gray-400 px-1">
      <span className="font-medium">Key:</span>
      {LEGEND_ITEMS.map((item) => (
        <div key={item.label} className="flex items-center gap-1.5">
          <span
            className={`w-2 h-2 rounded-full ${item.color} ${item.isRing ? 'bg-transparent' : ''}`}
          />
          <span>{item.label}</span>
        </div>
      ))}
    </div>
  )
})

export default SchedulerLegend
