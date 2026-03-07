import { useMemo, useRef } from 'react'
import { PlusIcon } from '@heroicons/react/24/outline'
import InlineActionRow from './InlineActionRow'
// @ts-expect-error -- .js module
import { generateUUID } from '../../../utils/uuid'
import type { RoutineAction } from './scheduler-types'

interface ActionListProps {
  /** Array of actions */
  actions?: RoutineAction[]
  /** Callback when actions change */
  onActionsChange: (actions: RoutineAction[]) => void
  /** Disable all interactions */
  disabled?: boolean
  /** Whether to show explicit seconds timing vs auto-stagger */
  useSecondsTiming?: boolean
}

/**
 * ActionList Component
 *
 * Displays a list of inline action rows with add/edit/delete capabilities.
 * Per unified-scheduler-mockup.html design, uses inline editing instead of modals.
 */
export default function ActionList({
  actions = [],
  onActionsChange,
  disabled = false,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  useSecondsTiming = false,
}: ActionListProps) {
  // Track generated IDs for actions without stable IDs from parent
  // Uses content-based key to ensure same logical action gets same ID
  const generatedIdsRef = useRef(new Map<string, string>())

  // Ensure all actions have stable IDs
  // Uses a ref to maintain consistent IDs for actions that lack them
  const actionsWithIds = useMemo(
    () =>
      actions.map((action, index) => {
        if (action.id) return action
        // Create a stable key from action content and index
        // Include index to handle new empty actions with same content
        const contentKey = `${action.action_type || ''}:${action.action_name || ''}:${action.offset_minutes || 0}:${index}`
        if (!generatedIdsRef.current.has(contentKey)) {
          generatedIdsRef.current.set(contentKey, generateUUID())
        }
        return { ...action, id: generatedIdsRef.current.get(contentKey) }
      }),
    [actions]
  )

  /**
   * Add a new empty action to the list
   * Per mockup design, immediately adds an inline row for editing
   */
  function handleAddAction() {
    const newAction: RoutineAction = {
      id: generateUUID(),
      action_type: '',
      action_name: '',
      offset_minutes: 0,
    }
    onActionsChange([...actionsWithIds, newAction])
  }

  /**
   * Update an action at the given index
   */
  function handleActionChange(index: number, updatedAction: RoutineAction) {
    const newActions = actionsWithIds.map((action, i) =>
      i === index ? { ...updatedAction, id: action.id } : action
    )
    onActionsChange(newActions)
  }

  /**
   * Delete an action at the given index
   */
  function handleActionDelete(index: number) {
    const newActions = actionsWithIds.filter((_, i) => i !== index)
    onActionsChange(newActions)
  }

  return (
    <div className="space-y-2">
      {/* Action List or Empty State */}
      {actionsWithIds.length === 0 ? (
        <div className="text-center py-4">
          <p className="text-sm text-gray-500 dark:text-gray-400">
            No actions yet. Add your first action to get started.
          </p>
        </div>
      ) : (
        <div className="space-y-2" data-testid="action-list">
          {actionsWithIds.map((action, index) => (
            <InlineActionRow
              key={action.id}
              action={action}
              index={index}
              onChange={(updatedAction) => handleActionChange(index, updatedAction)}
              onDelete={() => handleActionDelete(index)}
              disabled={disabled}
            />
          ))}
        </div>
      )}

      {/* Add Action Button */}
      <button
        type="button"
        onClick={handleAddAction}
        disabled={disabled}
        data-testid="add-action"
        className="w-full flex items-center justify-center gap-2 px-4 py-3
                   text-sm font-medium text-blue-600 dark:text-blue-400
                   bg-blue-50 dark:bg-blue-900/20 border-2 border-dashed
                   border-blue-300 dark:border-blue-700 rounded-lg
                   hover:bg-blue-100 dark:hover:bg-blue-900/30
                   disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <PlusIcon className="w-5 h-5" />
        Add Action
      </button>
    </div>
  )
}
