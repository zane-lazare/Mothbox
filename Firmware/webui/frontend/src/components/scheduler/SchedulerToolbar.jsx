import PropTypes from 'prop-types'
import { PlusIcon } from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'

/**
 * Toolbar component for scheduler interface with "New Schedule" action button.
 *
 * @component
 * @example
 * <SchedulerToolbar onNewSchedule={() => setShowEditor(true)} />
 *
 * @param {Object} props - Component props
 * @param {Function} [props.onNewSchedule] - Callback when "New Schedule" button is clicked. If not provided, shows info toast.
 * @param {boolean} [props.isCreating=false] - Whether a schedule is currently being created (disables button)
 * @returns {JSX.Element} Toolbar with "New Schedule" button
 */
function SchedulerToolbar({ onNewSchedule, isCreating = false }) {
  /**
   * Handles "New Schedule" button click.
   * Calls onNewSchedule callback if provided, otherwise shows info toast.
   */
  const handleNewSchedule = () => {
    if (onNewSchedule) {
      onNewSchedule()
    } else {
      toast.info('Schedule editor coming in Issue #227')
    }
  }

  return (
    <div className="flex justify-between items-center mb-6">
      <button
        onClick={handleNewSchedule}
        disabled={isCreating}
        className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center gap-2"
      >
        <PlusIcon className="h-5 w-5" />
        New Schedule
      </button>
    </div>
  )
}

SchedulerToolbar.propTypes = {
  onNewSchedule: PropTypes.func,
  isCreating: PropTypes.bool,
}

export default SchedulerToolbar
