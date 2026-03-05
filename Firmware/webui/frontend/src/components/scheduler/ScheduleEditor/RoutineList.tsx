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
import { PlusIcon } from '@heroicons/react/24/outline'
import RoutineCard from './RoutineCard'
import NewRoutineCard from './NewRoutineCard'
import type { Routine } from './scheduler-types'

interface RoutineListProps {
  /** Array of routine objects */
  routines: Routine[];
  /** Callback when a routine is updated */
  onRoutineUpdate: (routine: Routine) => void;
  /** Callback when a routine is deleted */
  onRoutineDelete: (routineId: string) => void;
  /** Callback when a new routine is added */
  onRoutineAdd: (routine: Routine) => void;
  /** Whether new routine form is visible */
  isAddingRoutine?: boolean;
  /** Callback to show new routine form */
  onStartAddRoutine: () => void;
  /** Callback to hide new routine form */
  onCancelAddRoutine: () => void;
  /** Whether editing is disabled */
  disabled?: boolean;
  /** Whether to show explicit seconds timing vs auto-stagger */
  useSecondsTiming?: boolean;
}

/**
 * RoutineList component
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
  useSecondsTiming = false,
}: RoutineListProps) {

  /**
   * Handle new routine completion
   */
  const handleNewRoutineComplete = useCallback(
    (routine: Routine) => {
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
          onUpdate={onRoutineUpdate}
          onDelete={onRoutineDelete}
          disabled={disabled}
          useSecondsTiming={useSecondsTiming}
        />
      ))}

      {/* New Routine Card (when adding) */}
      {isAddingRoutine && (
        <NewRoutineCard
          onComplete={handleNewRoutineComplete}
          onCancel={onCancelAddRoutine}
          disabled={disabled}
          useSecondsTiming={useSecondsTiming}
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

export default memo(RoutineList)
