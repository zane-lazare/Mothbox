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
import { ScheduleCard } from './ScheduleCard'
import { ConfirmDialog } from '../../common/ConfirmDialog'
import LoadingSpinner from '../../LoadingSpinner'

export function ScheduleList({ onEditSchedule }) {
  const { data, isLoading, error, refetch } = useSchedules()
  const { data: activeData } = useActiveSchedule()
  const { mutate: activate, isPending: isActivating } = useActivateSchedule()
  const { mutate: deactivate, isPending: isDeactivating } = useDeactivateSchedule()
  const { mutate: deleteSchedule, isPending: isDeleting } = useDeleteSchedule()

  const [activatingId, setActivatingId] = useState(null)
  const [deleteConfirmation, setDeleteConfirmation] = useState({
    isOpen: false,
    schedule: null,
  })

  const schedules = data?.schedules || []
  const activeScheduleId = activeData?.active_schedule?.id || null

  const handleActivate = (scheduleId) => {
    setActivatingId(scheduleId)
    activate(
      { id: scheduleId },
      {
        onSuccess: () => {
          toast.success('Schedule activated successfully')
          setActivatingId(null)
        },
        onError: (error) => {
          toast.error(`Failed to activate schedule: ${error.message}`)
          setActivatingId(null)
        },
      }
    )
  }

  const handleDeactivate = () => {
    deactivate(undefined, {
      onSuccess: () => {
        toast.success('Schedule deactivated successfully')
      },
      onError: (error) => {
        toast.error(`Failed to deactivate schedule: ${error.message}`)
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

    deleteSchedule(deleteConfirmation.schedule.id, {
      onSuccess: () => {
        toast.success('Schedule deleted successfully')
        setDeleteConfirmation({ isOpen: false, schedule: null })
      },
      onError: (error) => {
        toast.error(`Failed to delete schedule: ${error.message}`)
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
      <div
        role="list"
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
      >
        {schedules.map((schedule) => (
          <ScheduleCard
            key={schedule.id}
            schedule={schedule}
            isActive={schedule.id === activeScheduleId}
            isActivating={schedule.id === activatingId}
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
        onCancel={handleDeleteCancel}
      />
    </>
  )
}

ScheduleList.propTypes = {
  onEditSchedule: PropTypes.func.isRequired,
}
