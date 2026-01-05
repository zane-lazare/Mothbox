/**
 * RoutineList - Container for displaying and managing multiple routine cards
 *
 * Per unified-scheduler-mockup.html, displays:
 * - List of RoutineCard components
 * - Add Routine button with dashed border
 * - NewRoutineCard when adding a new routine
 * - Empty state when no routines
 *
 * @module components/scheduler/ScheduleEditor/RoutineList
 */

import { memo, useCallback } from 'react'
import PropTypes from 'prop-types'
import { PlusIcon } from '@heroicons/react/24/outline'
import RoutineCard from './RoutineCard'
import NewRoutineCard from './NewRoutineCard'

/**
 * RoutineList component
 *
 * @param {Object} props - Component props
 * @param {Array} props.routines - Array of routine objects
 * @param {Function} props.onRoutineUpdate - Callback when a routine is updated
 * @param {Function} props.onRoutineDelete - Callback when a routine is deleted
 * @param {Function} props.onRoutineAdd - Callback when a new routine is added
 * @param {boolean} [props.isAddingRoutine=false] - Whether new routine form is visible
 * @param {Function} props.onStartAddRoutine - Callback to show new routine form
 * @param {Function} props.onCancelAddRoutine - Callback to hide new routine form
 * @param {boolean} [props.disabled=false] - Whether editing is disabled
 * @returns {JSX.Element} Routine list component
 *
 * @example
 * <RoutineList
 *   routines={[{ routine_id: '1', trigger: {...}, actions: [...] }]}
 *   onRoutineUpdate={(routine) => console.log('update', routine)}
 *   onRoutineDelete={(id) => console.log('delete', id)}
 *   onRoutineAdd={(routine) => console.log('add', routine)}
 *   isAddingRoutine={false}
 *   onStartAddRoutine={() => setIsAdding(true)}
 *   onCancelAddRoutine={() => setIsAdding(false)}
 * />
 */
function RoutineList({
  routines = [],
  onRoutineUpdate,
  onRoutineDelete,
  onRoutineAdd,
  isAddingRoutine = false,
  onStartAddRoutine,
  onCancelAddRoutine,
  disabled = false,
}) {
  /**
   * Handle routine update
   */
  const handleUpdate = useCallback(
    (routine) => {
      onRoutineUpdate(routine)
    },
    [onRoutineUpdate]
  )

  /**
   * Handle routine delete
   */
  const handleDelete = useCallback(
    (routineId) => {
      onRoutineDelete(routineId)
    },
    [onRoutineDelete]
  )

  /**
   * Handle new routine completion
   */
  const handleNewRoutineComplete = useCallback(
    (routine) => {
      onRoutineAdd(routine)
      onCancelAddRoutine()
    },
    [onRoutineAdd, onCancelAddRoutine]
  )

  /**
   * Handle add button click
   */
  const handleAddClick = useCallback(() => {
    onStartAddRoutine()
  }, [onStartAddRoutine])

  // Empty state
  if (routines.length === 0 && !isAddingRoutine) {
    return (
      <div data-testid="routine-list">
        <div
          className="text-center py-8 border border-dashed border-gray-800 dark:border-gray-700 rounded-lg"
          data-testid="routine-list-empty"
        >
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
            No routines configured
          </p>
          <button
            type="button"
            onClick={handleAddClick}
            disabled={disabled}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-400 dark:hover:text-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
            data-testid="add-routine"
          >
            <PlusIcon className="w-4 h-4" />
            Add Routine
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-2" data-testid="routine-list">
      {/* Existing Routines */}
      {routines.map((routine, index) => (
        <RoutineCard
          key={routine.routine_id}
          routine={routine}
          index={index}
          onUpdate={handleUpdate}
          onDelete={handleDelete}
          disabled={disabled}
        />
      ))}

      {/* New Routine Card (when adding) */}
      {isAddingRoutine && (
        <NewRoutineCard
          onComplete={handleNewRoutineComplete}
          onCancel={onCancelAddRoutine}
          disabled={disabled}
        />
      )}

      {/* Add Routine Button */}
      {!isAddingRoutine && (
        <button
          type="button"
          onClick={handleAddClick}
          disabled={disabled}
          className="w-full py-3 border border-dashed border-gray-800 dark:border-gray-700 rounded text-sm text-gray-600 dark:text-gray-500 hover:border-gray-600 dark:hover:border-gray-500 hover:text-gray-400 dark:hover:text-gray-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          data-testid="add-routine"
        >
          <span className="inline-flex items-center gap-2">
            <PlusIcon className="w-4 h-4" />
            Add Routine
          </span>
        </button>
      )}
    </div>
  )
}

RoutineList.propTypes = {
  /** Array of routine objects */
  routines: PropTypes.arrayOf(
    PropTypes.shape({
      routine_id: PropTypes.string.isRequired,
      name: PropTypes.string,
      trigger: PropTypes.object,
      actions: PropTypes.arrayOf(PropTypes.object),
    })
  ),
  /** Callback when a routine is updated */
  onRoutineUpdate: PropTypes.func.isRequired,
  /** Callback when a routine is deleted */
  onRoutineDelete: PropTypes.func.isRequired,
  /** Callback when a new routine is added */
  onRoutineAdd: PropTypes.func.isRequired,
  /** Whether new routine form is visible */
  isAddingRoutine: PropTypes.bool,
  /** Callback to show new routine form */
  onStartAddRoutine: PropTypes.func.isRequired,
  /** Callback to hide new routine form */
  onCancelAddRoutine: PropTypes.func.isRequired,
  /** Whether editing is disabled */
  disabled: PropTypes.bool,
}

export default memo(RoutineList)
