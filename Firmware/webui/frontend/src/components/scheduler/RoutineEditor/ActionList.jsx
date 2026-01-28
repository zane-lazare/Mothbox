import { useState, useMemo, useRef, useEffect } from 'react'
import PropTypes from 'prop-types'
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors
} from '@dnd-kit/core'
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import {
  BoltIcon,
  CameraIcon,
  MapPinIcon,
  CogIcon,
  PlusIcon,
  PencilIcon,
  TrashIcon
} from '@heroicons/react/24/outline'
import ActionForm from './ActionForm'
import { generateUUID } from '../../../utils/uuid'
import { ACTION_LIMITS } from './constants'

/**
 * Get icon component for action type
 */
function getActionIcon(type) {
  switch (type) {
    case 'gpio':
      return BoltIcon
    case 'camera':
      return CameraIcon
    case 'gps_sync':
      return MapPinIcon
    case 'service':
      return CogIcon
    default:
      return CogIcon
  }
}

/**
 * Sortable wrapper for individual action items
 */
function SortableAction({
  action,
  onEdit,
  onDelete,
  disabled = false,
  useSecondsTiming = false,
  staggerSeconds = 0,
  sameMinuteCount = 1
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition
  } = useSortable({ id: action.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition
  }

  const IconComponent = getActionIcon(action.action_type)

  // Create separate handler to prevent drag on button clicks
  const handleEditClick = (e) => {
    e.preventDefault()
    e.stopPropagation()
    onEdit(action)
  }

  const handleDeleteClick = (e) => {
    e.preventDefault()
    e.stopPropagation()
    onDelete(action)
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      data-sortable="true"
      className="flex items-center gap-3 p-3 bg-white dark:bg-gray-800
                 border border-gray-200 dark:border-gray-700 rounded-lg
                 hover:bg-gray-50 dark:hover:bg-gray-750 cursor-move"
    >
      {/* Drag Handle */}
      <div {...attributes} {...listeners} className="flex-1 flex items-center gap-3 min-w-0">
        {/* Icon */}
        <div className="flex-shrink-0">
          <IconComponent className="w-5 h-5 text-gray-500 dark:text-gray-400" />
        </div>

        {/* Offset Badge */}
        <div className="flex-shrink-0 flex items-center gap-1">
          <span className="px-2 py-1 text-xs font-medium bg-blue-100 dark:bg-blue-900
                           text-blue-800 dark:text-blue-200 rounded">
            +{action.offset_minutes}min
          </span>
          {/* Show seconds timing badge */}
          {useSecondsTiming && (
            <span className="px-2 py-1 text-xs font-medium bg-purple-100 dark:bg-purple-900
                             text-purple-800 dark:text-purple-200 rounded">
              +{action.offset_seconds ?? 0}s
            </span>
          )}
          {/* Show auto-stagger badge when NOT using seconds timing and multiple actions share same minute */}
          {!useSecondsTiming && sameMinuteCount > 1 && staggerSeconds > 0 && (
            <span className="px-2 py-1 text-xs font-medium bg-amber-100 dark:bg-amber-900
                             text-amber-800 dark:text-amber-200 rounded"
                  title="Auto-staggered to prevent GPIO conflicts">
              +{staggerSeconds}s stagger
            </span>
          )}
        </div>

        {/* Action Details */}
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100">
            {action.action_name}
          </h4>
          {action.description && (
            <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
              {action.description}
            </p>
          )}
        </div>
      </div>

      {/* Action Buttons (outside drag handle) */}
      <div className="flex items-center gap-2 flex-shrink-0">
        <button
          type="button"
          onClick={handleEditClick}
          onPointerDown={(e) => e.stopPropagation()}
          disabled={disabled}
          aria-label="Edit action"
          className="p-1 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400
                     disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:text-gray-400"
        >
          <PencilIcon className="w-4 h-4" />
        </button>
        <button
          type="button"
          onClick={handleDeleteClick}
          onPointerDown={(e) => e.stopPropagation()}
          disabled={disabled}
          aria-label="Delete action"
          className="p-1 text-gray-400 hover:text-red-600 dark:hover:text-red-400
                     disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:text-gray-400"
        >
          <TrashIcon className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}

SortableAction.propTypes = {
  action: PropTypes.object.isRequired,
  onEdit: PropTypes.func.isRequired,
  onDelete: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
  useSecondsTiming: PropTypes.bool,
  staggerSeconds: PropTypes.number,
  sameMinuteCount: PropTypes.number
}

/**
 * Delete confirmation dialog
 */
function DeleteConfirmDialog({ action, onConfirm, onCancel, isOpen = true }) {
  // Refs for focus management
  const modalRef = useRef(null)
  const previousActiveElement = useRef(null)

  // Handle Escape key to close dialog
  useEffect(() => {
    if (!isOpen) return
    const handleEscape = (e) => {
      if (e.key === 'Escape') onCancel()
    }
    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [isOpen, onCancel])

  // Focus management: move focus to modal on open, restore on close
  useEffect(() => {
    if (isOpen) {
      // Store the currently focused element before opening
      previousActiveElement.current = document.activeElement
      // Focus the modal after render
      if (modalRef.current) {
        modalRef.current.focus()
      }
    } else {
      // Restore focus to the previously focused element
      if (previousActiveElement.current && document.body.contains(previousActiveElement.current)) {
        previousActiveElement.current.focus()
      }
    }
  }, [isOpen])

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-dialog-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
    >
      <div
        ref={modalRef}
        tabIndex={-1}
        className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-md w-full mx-4 focus:outline-none"
      >
        <h3 id="delete-dialog-title" className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
          Delete Action
        </h3>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
          Are you sure you want to delete this action?
        </p>
        <p className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-6">
          {action.action_name}
        </p>
        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            aria-label="Cancel"
            className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300
                       bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600
                       rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            aria-label="Delete"
            className="px-4 py-2 text-sm font-medium text-white
                       bg-red-600 hover:bg-red-700 rounded-lg"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  )
}

DeleteConfirmDialog.propTypes = {
  action: PropTypes.object.isRequired,
  onConfirm: PropTypes.func.isRequired,
  onCancel: PropTypes.func.isRequired,
  isOpen: PropTypes.bool
}

/**
 * Calculate stagger info for actions (which actions share minutes, what stagger to show)
 */
function calculateStaggerInfo(actions, useSecondsTiming) {
  const staggerInfo = {}

  // Group actions by offset_minutes
  const minuteGroups = {}
  actions.forEach((action, idx) => {
    const minute = action.offset_minutes ?? 0
    if (!minuteGroups[minute]) {
      minuteGroups[minute] = []
    }
    minuteGroups[minute].push(idx)
  })

  // Calculate stagger for each action
  actions.forEach((action, idx) => {
    const minute = action.offset_minutes ?? 0
    const group = minuteGroups[minute]
    const positionInGroup = group.indexOf(idx)

    staggerInfo[idx] = {
      sameMinuteCount: group.length,
      staggerSeconds: useSecondsTiming
        ? (action.offset_seconds ?? 0)
        : positionInGroup * ACTION_LIMITS.DEFAULT_STAGGER_SECONDS
    }
  })

  return staggerInfo
}

/**
 * ActionList Component
 *
 * Displays a sortable list of pattern actions with add/edit/delete capabilities.
 * Uses @dnd-kit for drag-and-drop reordering.
 *
 * @param {Object} props
 * @param {Array<PatternAction>} props.actions - Array of actions
 * @param {Function} props.onActionsChange - Callback when actions change
 * @param {boolean} props.disabled - Disable all interactions
 * @param {boolean} props.useSecondsTiming - Show explicit seconds vs auto-stagger badges
 */
export default function ActionList({ actions = [], onActionsChange, disabled = false, useSecondsTiming = false }) {
  const [isFormOpen, setIsFormOpen] = useState(false)
  const [editingAction, setEditingAction] = useState(null)
  const [deletingAction, setDeletingAction] = useState(null)

  // Setup drag-and-drop sensors
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates
    })
  )

  // Track generated IDs for actions without stable IDs from parent
  // Uses content-based key to ensure same logical action gets same ID
  const generatedIdsRef = useRef(new Map())

  // Ensure all actions have stable IDs
  // Uses a ref to maintain consistent IDs for actions that lack them
  const actionsWithIds = useMemo(() =>
    actions.map(action => {
      if (action.id) return action
      // Create a stable key from action content
      const contentKey = `${action.action_type}:${action.action_name}:${action.offset_minutes}`
      if (!generatedIdsRef.current.has(contentKey)) {
        generatedIdsRef.current.set(contentKey, generateUUID())
      }
      return { ...action, id: generatedIdsRef.current.get(contentKey) }
    }),
    [actions]
  )

  // Sort actions by offset for display (memoized to prevent re-sorting on every render)
  const sortedActions = useMemo(() =>
    [...actionsWithIds].sort((a, b) => a.offset_minutes - b.offset_minutes),
    [actionsWithIds]
  )

  // Calculate stagger info for display
  const staggerInfo = useMemo(() =>
    calculateStaggerInfo(sortedActions, useSecondsTiming),
    [sortedActions, useSecondsTiming]
  )

  /**
   * Handle drag end event
   */
  function handleDragEnd(event) {
    try {
      const { active, over } = event

      if (!over || active.id === over.id) {
        return
      }

      const oldIndex = actionsWithIds.findIndex(a => a.id === active.id)
      const newIndex = actionsWithIds.findIndex(a => a.id === over.id)

      const reorderedActions = arrayMove(actionsWithIds, oldIndex, newIndex)
      onActionsChange(reorderedActions)
    } catch (error) {
      console.error('Drag operation failed:', error)
    }
  }

  /**
   * Open form to add new action
   */
  function handleAddAction() {
    setEditingAction(null)
    setIsFormOpen(true)
  }

  /**
   * Open form to edit existing action
   */
  function handleEditAction(action) {
    setEditingAction(action)
    setIsFormOpen(true)
  }

  /**
   * Show delete confirmation
   */
  function handleDeleteClick(action) {
    setDeletingAction(action)
  }

  /**
   * Confirm deletion
   */
  function handleDeleteConfirm() {
    if (!deletingAction) return

    const updatedActions = actionsWithIds.filter(a => a.id !== deletingAction.id)
    onActionsChange(updatedActions)
    setDeletingAction(null)
  }

  /**
   * Cancel deletion
   */
  function handleDeleteCancel() {
    setDeletingAction(null)
  }

  /**
   * Handle form save (add or edit)
   */
  function handleFormSave(actionData) {
    if (editingAction) {
      // Update existing action
      const updatedActions = actionsWithIds.map(a =>
        a.id === editingAction.id ? { ...actionData, id: editingAction.id } : a
      )
      onActionsChange(updatedActions)
    } else {
      // Add new action
      const newAction = {
        ...actionData,
        id: actionData.id || generateUUID()
      }
      onActionsChange([...actionsWithIds, newAction])
    }

    setIsFormOpen(false)
    setEditingAction(null)
  }

  /**
   * Handle form cancel
   */
  function handleFormCancel() {
    setIsFormOpen(false)
    setEditingAction(null)
  }

  return (
    <div className="space-y-4">
      {/* Action List or Empty State */}
      {sortedActions.length === 0 ? (
        <div className="text-center py-8">
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
            No actions yet. Add your first action to get started.
          </p>
        </div>
      ) : (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={handleDragEnd}
        >
          <div data-testid="action-list-dnd">
            <SortableContext
              items={sortedActions.map(a => a.id)}
              strategy={verticalListSortingStrategy}
            >
              <div className="space-y-2">
                {sortedActions.map((action, idx) => (
                  <SortableAction
                    key={action.id}
                    action={action}
                    onEdit={handleEditAction}
                    onDelete={handleDeleteClick}
                    disabled={disabled}
                    useSecondsTiming={useSecondsTiming}
                    staggerSeconds={staggerInfo[idx]?.staggerSeconds ?? 0}
                    sameMinuteCount={staggerInfo[idx]?.sameMinuteCount ?? 1}
                  />
                ))}
              </div>
            </SortableContext>
          </div>
        </DndContext>
      )}

      {/* Add Action Button */}
      <button
        type="button"
        onClick={handleAddAction}
        disabled={disabled}
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

      {/* Action Form Modal */}
      <ActionForm
        action={editingAction}
        onSave={handleFormSave}
        onCancel={handleFormCancel}
        isOpen={isFormOpen}
        useSecondsTiming={useSecondsTiming}
      />

      {/* Delete Confirmation Dialog */}
      {deletingAction && (
        <DeleteConfirmDialog
          action={deletingAction}
          onConfirm={handleDeleteConfirm}
          onCancel={handleDeleteCancel}
        />
      )}
    </div>
  )
}

ActionList.propTypes = {
  actions: PropTypes.arrayOf(PropTypes.object),
  onActionsChange: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
  /** When true, shows explicit offset_seconds; when false, shows auto-stagger info */
  useSecondsTiming: PropTypes.bool
}
