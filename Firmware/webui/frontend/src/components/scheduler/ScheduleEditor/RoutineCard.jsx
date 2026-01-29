/**
 * RoutineCard - Collapsible card displaying a routine with inline editing
 *
 * Per unified-scheduler-mockup.html, displays:
 * - Collapsed: color dot + auto-generated name + trigger label + chevron
 * - Expanded: TriggerSelector + ActionList for inline editing
 *
 * @module components/scheduler/ScheduleEditor/RoutineCard
 */

import { useState, useCallback, memo, useMemo } from 'react'
import PropTypes from 'prop-types'
import { ChevronDownIcon, TrashIcon } from '@heroicons/react/24/outline'
import TriggerSelector from '../TriggerSelector'
import ActionList from '../RoutineEditor/ActionList'
import TriggerLabel from './TriggerLabel'
import { generateRoutineName, getActionColor } from '@/utils/routineUtils'
import { RoutinePropType } from './propTypes'

/**
 * RoutineCard component
 *
 * @param {Object} props - Component props
 * @param {Object} props.routine - Routine object with trigger and actions
 * @param {number} props.index - Index in parent list (for data-testid)
 * @param {Function} props.onUpdate - Callback when routine is updated
 * @param {Function} props.onDelete - Callback when routine is deleted
 * @param {boolean} [props.disabled=false] - Whether editing is disabled
 * @param {boolean} [props.defaultExpanded=false] - Whether card starts expanded
 * @returns {JSX.Element} Routine card component
 *
 * @example
 * <RoutineCard
 *   routine={{ trigger: { trigger_type: 'solar' }, actions: [] }}
 *   index={0}
 *   onUpdate={(updated) => console.log(updated)}
 *   onDelete={(id) => console.log('delete', id)}
 * />
 */
function RoutineCard({
  routine,
  index,
  onUpdate,
  onDelete,
  disabled = false,
  defaultExpanded = false,
  useSecondsTiming = false,
}) {
  const [expanded, setExpanded] = useState(defaultExpanded)

  // Memoize display name to avoid recalculating on every render
  const displayName = useMemo(() => generateRoutineName(routine), [routine])

  // Memoize action colors for all actions (deduplicated)
  const actionColors = useMemo(() => {
    if (!routine.actions?.length) return ['bg-gray-400']
    const colors = routine.actions.map(action => getActionColor(action))
    // Remove duplicates while preserving order
    return [...new Set(colors)]
  }, [routine.actions])

  /**
   * Toggle card expansion
   */
  const handleToggle = useCallback(() => {
    setExpanded((prev) => !prev)
  }, [])

  /**
   * Handle delete button click
   */
  const handleDelete = useCallback(
    (e) => {
      e.stopPropagation()
      onDelete(routine.routine_id)
    },
    [onDelete, routine.routine_id]
  )

  /**
   * Handle trigger change
   */
  const handleTriggerChange = useCallback(
    (newTrigger) => {
      onUpdate({
        ...routine,
        trigger: newTrigger,
      })
    },
    [onUpdate, routine]
  )

  /**
   * Handle actions change
   */
  const handleActionsChange = useCallback(
    (newActions) => {
      onUpdate({
        ...routine,
        actions: newActions,
      })
    },
    [onUpdate, routine]
  )

  return (
    <div
      className={`border rounded transition-colors ${
        expanded
          ? 'border-gray-700 dark:border-gray-600'
          : 'border-gray-800 dark:border-gray-700'
      }`}
      data-testid={`routine-${index}`}
    >
      {/* Header - Always visible */}
      <div
        className="flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-gray-800/30 dark:hover:bg-gray-700/30"
        onClick={handleToggle}
        role="button"
        aria-expanded={expanded}
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            handleToggle()
          }
        }}
      >
        {/* Left side: color dots + name */}
        <div className="flex items-center gap-3 min-w-0">
          {/* Action type color dots */}
          <div className="flex items-center gap-1 flex-shrink-0" aria-hidden="true">
            {actionColors.map((colorClass, i) => (
              <div
                key={i}
                className={`w-1.5 h-1.5 rounded-full ${colorClass}`}
              />
            ))}
          </div>
          {/* Auto-generated name */}
          <span
            className="text-sm text-gray-900 dark:text-gray-100 truncate"
            data-testid="routine-name"
          >
            {displayName}
          </span>
        </div>

        {/* Right side: trigger label + chevron + delete */}
        <div className="flex items-center gap-2 flex-shrink-0">
          <TriggerLabel trigger={routine.trigger} />
          <ChevronDownIcon
            className={`w-4 h-4 text-gray-600 dark:text-gray-400 transition-transform ${
              expanded ? 'rotate-180' : ''
            }`}
            aria-hidden="true"
          />
          <button
            type="button"
            onClick={handleDelete}
            disabled={disabled}
            className="p-1 text-gray-600 hover:text-red-400 dark:text-gray-400 dark:hover:text-red-400 disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="Delete routine"
            data-testid={`delete-routine-${index}`}
          >
            <TrashIcon className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Body - Collapsible content */}
      <div
        className={`overflow-hidden transition-all duration-200 ease-out ${
          expanded ? 'max-h-screen' : 'max-h-0'
        }`}
      >
        <div className="px-4 pb-4 pt-2 border-t border-gray-800 dark:border-gray-700 space-y-4">
          {/* Trigger Selector */}
          <div>
            <label className="block text-xs text-gray-500 dark:text-gray-400 mb-2">
              Trigger
            </label>
            <TriggerSelector
              trigger={routine.trigger}
              onChange={handleTriggerChange}
              disabled={disabled}
            />
          </div>

          {/* Action List */}
          <div>
            <label className="block text-xs text-gray-500 dark:text-gray-400 mb-2">
              Actions
            </label>
            <ActionList
              actions={routine.actions || []}
              onActionsChange={handleActionsChange}
              disabled={disabled}
              useSecondsTiming={useSecondsTiming}
            />
          </div>
        </div>
      </div>
    </div>
  )
}

RoutineCard.propTypes = {
  /** Routine object with trigger and actions */
  routine: RoutinePropType.isRequired,
  /** Index in parent list for data-testid */
  index: PropTypes.number.isRequired,
  /** Callback when routine is updated */
  onUpdate: PropTypes.func.isRequired,
  /** Callback when routine is deleted */
  onDelete: PropTypes.func.isRequired,
  /** Whether editing is disabled */
  disabled: PropTypes.bool,
  /** Whether card starts expanded */
  defaultExpanded: PropTypes.bool,
  /** Whether to show explicit seconds timing vs auto-stagger */
  useSecondsTiming: PropTypes.bool,
}

export default memo(RoutineCard)
