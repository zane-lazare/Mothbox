/**
 * InlineActionRow - Inline action editing row for scheduler
 *
 * Per unified-scheduler-mockup.html design, displays inline dropdowns
 * for action type and name selection without modal dialogs.
 *
 * @module components/scheduler/ScheduleEditor/InlineActionRow
 */

import { TrashIcon } from '@heroicons/react/24/outline'
import { ACTION_NAMES, ACTION_LIMITS } from './constants'
import type { RoutineAction } from './scheduler-types'

/**
 * Get display label for action type
 */
function getActionTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    gpio: 'GPIO',
    camera: 'Camera',
    gps_sync: 'GPS Sync',
    service: 'Service',
  }
  return labels[type] || type || ''
}

/**
 * Get display label for action name
 */
function getActionNameLabel(name: string): string {
  const labels: Record<string, string> = {
    attract_on: 'Attract On',
    attract_off: 'Attract Off',
    flash_on: 'Flash On',
    flash_off: 'Flash Off',
    takephoto: 'Take Photo',
    sync: 'Sync',
    backup: 'Backup',
    update_display: 'Update Display',
  }
  return labels[name] || name || ''
}

interface InlineActionRowProps {
  /** Action object with action_type, action_name, offset_minutes */
  action: RoutineAction
  /** Index in parent list for data-testid */
  index: number
  /** Callback when action is updated */
  onChange: (action: RoutineAction) => void
  /** Callback when action is deleted */
  onDelete: (index: number) => void
  /** Whether editing is disabled */
  disabled?: boolean
}

export default function InlineActionRow({
  action,
  index,
  onChange,
  onDelete,
  disabled = false,
}: InlineActionRowProps) {
  const actionType = action?.action_type || ''
  const actionName = action?.action_name || ''
  const offsetMinutes = action?.offset_minutes ?? 0

  /**
   * Handle action type change
   * Reset action_name when type changes since names are type-specific
   */
  const handleTypeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newType = e.target.value
    onChange({
      ...action,
      action_type: newType,
      action_name: '', // Reset name when type changes
    })
  }

  /**
   * Handle action name change
   */
  const handleNameChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onChange({
      ...action,
      action_name: e.target.value,
    })
  }

  /**
   * Handle offset change
   */
  const handleOffsetChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(e.target.value, 10)
    const clampedValue = Math.max(
      ACTION_LIMITS.MIN_OFFSET_MINUTES,
      Math.min(isNaN(value) ? 0 : value, ACTION_LIMITS.MAX_OFFSET_MINUTES)
    )
    onChange({
      ...action,
      offset_minutes: clampedValue,
    })
  }

  /**
   * Handle delete button click
   */
  const handleDelete = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    onDelete(index)
  }

  // Get available action names for the selected type
  const availableNames = ACTION_NAMES[actionType] || []

  return (
    <div
      className="flex items-center gap-2 p-2 bg-white dark:bg-gray-800
                 border border-gray-200 dark:border-gray-700 rounded-lg"
      data-testid={`action-row-${index}`}
    >
      {/* Action Type Select */}
      <select
        data-testid="action-type"
        value={actionType}
        onChange={handleTypeChange}
        disabled={disabled}
        className="flex-1 min-w-0 bg-transparent border border-gray-300 dark:border-gray-600
                   rounded px-2 py-1.5 text-sm text-gray-900 dark:text-white
                   focus:border-blue-500 focus:outline-none
                   disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <option value="">Select type</option>
        <option value="gpio">{getActionTypeLabel('gpio')}</option>
        <option value="camera">{getActionTypeLabel('camera')}</option>
        <option value="gps_sync">{getActionTypeLabel('gps_sync')}</option>
        <option value="service">{getActionTypeLabel('service')}</option>
      </select>

      {/* Action Name Select */}
      <select
        data-testid="action-name"
        value={actionName}
        onChange={handleNameChange}
        disabled={disabled || !actionType}
        className="flex-1 min-w-0 bg-transparent border border-gray-300 dark:border-gray-600
                   rounded px-2 py-1.5 text-sm text-gray-900 dark:text-white
                   focus:border-blue-500 focus:outline-none
                   disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <option value="">Select action</option>
        {availableNames.map((name) => (
          <option key={name} value={name}>
            {getActionNameLabel(name)}
          </option>
        ))}
      </select>

      {/* Offset Input */}
      <div className="flex items-center gap-1">
        <span className="text-xs text-gray-500 dark:text-gray-400">+</span>
        <input
          type="number"
          data-testid="action-offset"
          value={offsetMinutes}
          onChange={handleOffsetChange}
          disabled={disabled}
          min={ACTION_LIMITS.MIN_OFFSET_MINUTES}
          max={ACTION_LIMITS.MAX_OFFSET_MINUTES}
          className="w-14 bg-transparent border border-gray-300 dark:border-gray-600
                     rounded px-2 py-1.5 text-sm text-gray-900 dark:text-white text-center
                     focus:border-blue-500 focus:outline-none
                     disabled:opacity-50 disabled:cursor-not-allowed"
        />
        <span className="text-xs text-gray-500 dark:text-gray-400">min</span>
      </div>

      {/* Delete Button */}
      <button
        type="button"
        onClick={handleDelete}
        disabled={disabled}
        aria-label="Delete action"
        className="p-1 text-gray-400 hover:text-red-600 dark:hover:text-red-400
                   disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:text-gray-400"
      >
        <TrashIcon className="w-4 h-4" />
      </button>
    </div>
  )
}
