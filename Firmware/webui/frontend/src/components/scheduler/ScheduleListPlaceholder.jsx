import { ListBulletIcon } from '@heroicons/react/24/outline'

/**
 * ScheduleListPlaceholder - Temporary placeholder for schedule list.
 * Will be replaced with full implementation in Issue #226.
 */
export default function ScheduleListPlaceholder() {
  return (
    <div className="bg-white rounded-lg shadow p-12 text-center">
      <ListBulletIcon className="h-16 w-16 mx-auto text-gray-300 mb-4" />
      <h3 className="text-lg font-medium text-gray-500 mb-2">Schedule List</h3>
      <p className="text-sm text-gray-400">
        Full implementation coming in Issue #226
      </p>
    </div>
  )
}
