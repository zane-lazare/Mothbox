/**
 * ScheduleList - Container for displaying and managing all schedules (Issue #266)
 *
 * Displays schedules in a responsive grid with loading/error/empty states.
 * Handles schedule activation, deactivation, editing, and deletion with
 * confirmation dialogs and toast notifications.
 *
 * @module components/scheduler/ScheduleList/ScheduleList
 */

import { useState } from 'react'
import PropTypes from 'prop-types'
import { CalendarDaysIcon } from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'
import {
  useSchedules,
  useActiveSchedule,
  useActivateSchedule,
  useDeactivateSchedule,
  useDeleteSchedule,
} from '../../../hooks/useSchedules'
import ScheduleCard from './ScheduleCard'
import ConfirmDialog from '../../common/ConfirmDialog'
import LoadingSpinner from '../../LoadingSpinner'
import { SCHEDULER_LAYOUT_CONFIG } from '../../../constants/config'

/** Toast message constants for i18n and consistency */
const TOAST_MESSAGES = {
  ACTIVATE_SUCCESS: 'Schedule activated successfully',
  ACTIVATE_ERROR: (msg) => `Failed to activate schedule: ${msg}`,
  DEACTIVATE_SUCCESS: 'Schedule deactivated successfully',
  DEACTIVATE_ERROR: (msg) => `Failed to deactivate schedule: ${msg}`,
  DELETE_SUCCESS: 'Schedule deleted successfully',
  DELETE_ERROR: (msg) => `Failed to delete schedule: ${msg}`,
}

export function ScheduleList({ onEditSchedule, variant = 'default' }) {
  // Select grid classes based on variant (sidebar vs full-page)
  const gridClasses = variant === 'sidebar'
    ? SCHEDULER_LAYOUT_CONFIG.SIDEBAR_GRID
    : SCHEDULER_LAYOUT_CONFIG.DEFAULT_GRID
  const { data, isLoading, error, refetch } = useSchedules()
  const { data: activeData } = useActiveSchedule()
  const { mutate: activate } = useActivateSchedule()
  const { mutate: deactivate, isPending: isDeactivating } = useDeactivateSchedule()
  const { mutate: deleteSchedule, isPending: isDeleting } = useDeleteSchedule()

  const [activatingId, setActivatingId] = useState(null)
  const [deleteConfirmation, setDeleteConfirmation] = useState({
    isOpen: false,
    schedule: null,
  })

  const schedules = data?.schedules || []
  const activeScheduleId = activeData?.active_schedule?.schedule_id || null

  const handleActivate = (schedule) => {
    setActivatingId(schedule.schedule_id)
    activate(
      { id: schedule.schedule_id },
      {
        onSuccess: () => {
          toast.success(TOAST_MESSAGES.ACTIVATE_SUCCESS)
          setActivatingId(null)
        },
        onError: (error) => {
          toast.error(TOAST_MESSAGES.ACTIVATE_ERROR(error.message))
          setActivatingId(null)
        },
      }
    )
  }

  const handleDeactivate = () => {
    deactivate(undefined, {
      onSuccess: () => {
        toast.success(TOAST_MESSAGES.DEACTIVATE_SUCCESS)
      },
      onError: (error) => {
        toast.error(TOAST_MESSAGES.DEACTIVATE_ERROR(error.message))
      },
    })
  }

  const handleDeleteClick = (schedule) => {
    setDeleteConfirmation({
      isOpen: true,
      schedule,
    })
  }

  const handleDeleteConfirm = () => {
    if (!deleteConfirmation.schedule) return

    deleteSchedule(deleteConfirmation.schedule.schedule_id, {
      onSuccess: () => {
        toast.success(TOAST_MESSAGES.DELETE_SUCCESS)
        setDeleteConfirmation({ isOpen: false, schedule: null })
      },
      onError: (error) => {
        toast.error(TOAST_MESSAGES.DELETE_ERROR(error.message))
        setDeleteConfirmation({ isOpen: false, schedule: null })
      },
    })
  }

  const handleDeleteCancel = () => {
    setDeleteConfirmation({ isOpen: false, schedule: null })
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-[200px]">
        <LoadingSpinner />
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-red-600 mb-4">Failed to load schedules: {error.message}</p>
        <button
          onClick={refetch}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
        >
          Retry
        </button>
      </div>
    )
  }

  // Empty state
  if (schedules.length === 0) {
    return (
      <div className="text-center py-12">
        <CalendarDaysIcon className="w-16 h-16 mx-auto mb-4 text-gray-400" />
        <p className="text-gray-500 text-lg">No schedules yet</p>
        <p className="text-gray-400 text-sm mt-2">Create a schedule to get started</p>
      </div>
    )
  }

  // List state
  return (
    <>
      <div role="list" className={gridClasses}>
        {schedules.map((schedule) => (
          <ScheduleCard
            key={schedule.schedule_id}
            schedule={schedule}
            isActive={schedule.schedule_id === activeScheduleId}
            isActivating={schedule.schedule_id === activatingId}
            isDeactivating={isDeactivating && schedule.schedule_id === activeScheduleId}
            isDeleting={isDeleting && deleteConfirmation.schedule?.schedule_id === schedule.schedule_id}
            onActivate={handleActivate}
            onDeactivate={handleDeactivate}
            onEdit={onEditSchedule}
            onDelete={handleDeleteClick}
          />
        ))}
      </div>

      <ConfirmDialog
        isOpen={deleteConfirmation.isOpen}
        title="Delete Schedule"
        message={
          deleteConfirmation.schedule
            ? `Are you sure you want to delete "${deleteConfirmation.schedule.name}"? This action cannot be undone.`
            : ''
        }
        onConfirm={handleDeleteConfirm}
        onClose={handleDeleteCancel}
      />
    </>
  )
}

ScheduleList.propTypes = {
  /** Callback when a schedule is selected for editing */
  onEditSchedule: PropTypes.func.isRequired,
  /** Layout variant: 'default' for full-page grid, 'sidebar' for vertical stack */
  variant: PropTypes.oneOf(['default', 'sidebar']),
}
