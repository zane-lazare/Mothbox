import PropTypes from 'prop-types'
import { CheckCircleIcon } from '@heroicons/react/24/solid'
import { useActiveSchedule, useDeactivateSchedule } from '../../hooks/useSchedules'

/**
 * ActiveScheduleBanner displays a banner when a schedule is currently active.
 * Provides a button to deactivate the current schedule.
 *
 * @component
 * @example
 * return (
 *   <ActiveScheduleBanner />
 * )
 */
function ActiveScheduleBanner() {
  const { data } = useActiveSchedule()
  const { mutate: deactivate, isPending } = useDeactivateSchedule()

  // Don't render if no active schedule
  if (!data?.active_schedule) {
    return null
  }

  const { name } = data.active_schedule

  const handleDeactivate = () => {
    deactivate()
  }

  return (
    <div
      role="status"
      className="bg-green-50 border border-green-200 rounded-lg p-4 flex items-center justify-between"
    >
      <div className="flex items-center gap-2">
        <CheckCircleIcon className="h-5 w-5 text-green-600" />
        <span className="text-green-900 font-medium">
          Active: <span className="font-normal">{name}</span>
        </span>
      </div>

      <button
        onClick={handleDeactivate}
        disabled={isPending}
        className="px-4 py-2 text-sm font-medium text-red-700 bg-red-50 border border-red-200 rounded-md hover:bg-red-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {isPending ? 'Deactivating...' : 'Deactivate'}
      </button>
    </div>
  )
}

ActiveScheduleBanner.propTypes = {}

export default ActiveScheduleBanner
