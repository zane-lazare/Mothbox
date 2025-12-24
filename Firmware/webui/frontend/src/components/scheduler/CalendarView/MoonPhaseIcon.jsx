/**
 * MoonPhaseIcon - Display moon phase with visual styling and tooltip (Issue #228)
 *
 * Renders a moon icon with phase-specific styling and illumination information.
 * Used in the Calendar View to display moon phase triggers.
 *
 * @module components/scheduler/CalendarView/MoonPhaseIcon
 */

import { memo } from 'react'
import PropTypes from 'prop-types'
import { MoonIcon } from '@heroicons/react/24/outline'

/**
 * Size classes for the icon
 * @constant {Object<string, string>}
 */
const SIZE_CLASSES = {
  sm: 'h-4 w-4',
  md: 'h-5 w-5',
  lg: 'h-6 w-6',
}

/**
 * Get color and fill classes for a specific moon phase
 *
 * @param {string} phase - Phase identifier (e.g., 'new', 'full', 'waxing_crescent')
 * @returns {Object} Object with color and fill classes
 */
function getPhaseStyles(phase) {
  switch (phase) {
    case 'new':
      // New moon: Gray outline only
      return {
        color: 'text-gray-400 dark:text-gray-500',
        fill: '',
      }

    case 'waxing_crescent':
      // Early waxing: Light yellow, no fill
      return {
        color: 'text-yellow-200 dark:text-yellow-300',
        fill: '',
      }

    case 'first_quarter':
      // First quarter: Medium yellow, partially filled
      return {
        color: 'text-yellow-300 dark:text-yellow-400',
        fill: 'fill-yellow-100 dark:fill-yellow-900/30',
      }

    case 'waxing_gibbous':
      // Late waxing: Bright yellow, mostly filled
      return {
        color: 'text-yellow-300 dark:text-yellow-300',
        fill: 'fill-yellow-200 dark:fill-yellow-800/40',
      }

    case 'full':
      // Full moon: Bright yellow, completely filled
      return {
        color: 'text-yellow-300 dark:text-yellow-300',
        fill: 'fill-yellow-300 dark:fill-yellow-400',
      }

    case 'waning_gibbous':
      // Early waning: Bright yellow, mostly filled
      return {
        color: 'text-yellow-300 dark:text-yellow-400',
        fill: 'fill-yellow-200 dark:fill-yellow-800/40',
      }

    case 'last_quarter':
      // Last quarter: Medium yellow, partially filled
      return {
        color: 'text-yellow-300 dark:text-yellow-400',
        fill: 'fill-yellow-100 dark:fill-yellow-900/30',
      }

    case 'waning_crescent':
      // Late waning: Light yellow, no fill
      return {
        color: 'text-yellow-200 dark:text-yellow-300',
        fill: '',
      }

    default:
      // Unknown phase: Gray outline
      return {
        color: 'text-gray-400 dark:text-gray-500',
        fill: '',
      }
  }
}

/**
 * MoonPhaseIcon component
 *
 * @param {Object} props - Component props
 * @param {Object} props.phase - Moon phase data
 * @param {string} props.phase.phase - Phase identifier (e.g., 'new', 'full')
 * @param {string} props.phase.phase_name - Human-readable phase name
 * @param {number} props.phase.illumination - Illumination percentage (0-1)
 * @param {'sm'|'md'|'lg'} [props.size='sm'] - Icon size
 * @returns {JSX.Element} Moon phase icon with tooltip
 *
 * @example
 * <MoonPhaseIcon
 *   phase={{
 *     phase: 'full',
 *     phase_name: 'Full Moon',
 *     illumination: 1.0
 *   }}
 *   size="md"
 * />
 */
function MoonPhaseIcon({ phase, size = 'sm' }) {
  // Handle missing phase data
  if (!phase || !phase.phase) {
    return (
      <MoonIcon
        className={`${SIZE_CLASSES[size]} text-gray-400 dark:text-gray-500`}
        aria-hidden="true"
      />
    )
  }

  const styles = getPhaseStyles(phase.phase)
  const sizeClass = SIZE_CLASSES[size] || SIZE_CLASSES.sm
  const illuminationPercent = Math.round((phase.illumination || 0) * 100)

  // Tooltip text with phase name and illumination
  const tooltipText = phase.phase_name
    ? `${phase.phase_name} (${illuminationPercent}% illuminated)`
    : `${illuminationPercent}% illuminated`

  return (
    <div className="relative group inline-block">
      <MoonIcon
        className={`${sizeClass} ${styles.color} ${styles.fill}`}
        aria-hidden="true"
      />

      {/* Tooltip */}
      <div
        role="tooltip"
        className="absolute z-10 invisible group-hover:visible opacity-0 group-hover:opacity-100 transition-opacity duration-200 bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 text-xs font-medium text-white bg-gray-900 dark:bg-gray-700 rounded shadow-lg whitespace-nowrap pointer-events-none"
      >
        {tooltipText}
        {/* Tooltip arrow */}
        <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-px border-4 border-transparent border-t-gray-900 dark:border-t-gray-700" />
      </div>
    </div>
  )
}

MoonPhaseIcon.propTypes = {
  phase: PropTypes.shape({
    phase: PropTypes.oneOf([
      'new',
      'waxing_crescent',
      'first_quarter',
      'waxing_gibbous',
      'full',
      'waning_gibbous',
      'last_quarter',
      'waning_crescent',
    ]),
    phase_name: PropTypes.string,
    illumination: PropTypes.number,
  }),
  size: PropTypes.oneOf(['sm', 'md', 'lg']),
}

export default memo(MoonPhaseIcon)
