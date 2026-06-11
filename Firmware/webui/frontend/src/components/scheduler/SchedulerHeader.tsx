import React from 'react'

export interface SchedulerHeaderProps {
  children?: React.ReactNode
}

/**
 * SchedulerHeader Component
 *
 * Header component for the scheduler page with title and optional toolbar area.
 * Features responsive layout that switches from column (mobile) to row (desktop).
 *
 * @component
 * @param {Object} props - Component props
 * @param {React.ReactNode} props.children - Optional toolbar content (rendered on the right side)
 * @returns {JSX.Element} Rendered header component
 *
 * @example
 * <SchedulerHeader>
 *   <button>Add Schedule</button>
 * </SchedulerHeader>
 */
function SchedulerHeader({ children }: SchedulerHeaderProps) {
  return (
    <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
      <h2 className="text-xl font-bold text-gray-900">Scheduler</h2>
      {children && (
        <div className="flex items-center gap-2">
          {children}
        </div>
      )}
    </div>
  )
}

export default SchedulerHeader
