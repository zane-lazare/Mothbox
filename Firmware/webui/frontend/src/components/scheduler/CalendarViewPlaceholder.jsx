import { CalendarDaysIcon } from '@heroicons/react/24/outline'

/**
 * CalendarViewPlaceholder - Temporary placeholder for calendar view.
 * Will be replaced with full implementation in Issue #229.
 */
export default function CalendarViewPlaceholder() {
  return (
    <div className="bg-white rounded-lg shadow p-12 text-center">
      <CalendarDaysIcon className="h-16 w-16 mx-auto text-gray-300 mb-4" />
      <h3 className="text-lg font-medium text-gray-500 mb-2">Calendar View</h3>
      <p className="text-sm text-gray-400">
        Full implementation coming in Issue #229
      </p>
    </div>
  )
}
