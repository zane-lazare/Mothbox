/**
 * CalendarView - Main calendar view container (Issue #228)
 *
 * Container component that manages calendar state, data fetching,
 * and orchestrates child components (CalendarHeader, CalendarGrid, ExecutionDetailModal).
 *
 * Features:
 * - View mode switching (month/week/day) with localStorage persistence
 * - Schedule selection and preview
 * - Date navigation
 * - Execution detail modal
 * - Moon phase data integration
 *
 * @module components/scheduler/CalendarView
 */

import { useState, useMemo, useCallback, useEffect } from 'react'
import { CalendarDaysIcon, ExclamationCircleIcon } from '@heroicons/react/24/outline'
import CalendarHeader from './CalendarHeader'
import CalendarGrid from './CalendarGrid'
import ExecutionDetailModal from './ExecutionDetailModal'
import LoadingSpinner from '../../LoadingSpinner'
import { useSchedules, useSchedulePreview } from '../../../hooks/useSchedules'
import { getDateKey } from './calendarUtils'

const VIEW_MODE_STORAGE_KEY = 'mothbox-calendar-view-mode'

/**
 * Number of days to fetch for each view mode.
 * Month: 35 days covers 5 weeks which is sufficient for most month views
 * (some months need 6 weeks, but 5 covers the main content)
 */
const PREVIEW_DAYS = {
  month: 35,
  week: 7,
  day: 1,
}

/**
 * CalendarView component
 *
 * @returns {JSX.Element} Calendar view container
 *
 * @example
 * <CalendarView />
 */
export function CalendarView() {
  // State management
  const [viewMode, setViewMode] = useState(() => {
    const stored = localStorage.getItem(VIEW_MODE_STORAGE_KEY)
    return stored || 'month'
  })
  const [currentDate, setCurrentDate] = useState(() => new Date())
  const [selectedScheduleId, setSelectedScheduleId] = useState(null)
  const [selectedExecution, setSelectedExecution] = useState(null)
  const [isModalOpen, setIsModalOpen] = useState(false)

  // Fetch schedules list
  const { data: schedulesData, isLoading: schedulesLoading } = useSchedules()
  const schedules = schedulesData?.schedules || []

  // Calculate preview days based on view mode
  const previewDays = useMemo(() => {
    return PREVIEW_DAYS[viewMode] || PREVIEW_DAYS.month
  }, [viewMode])

  // Fetch schedule preview (only when schedule is selected)
  const {
    data: previewData,
    isLoading: previewLoading,
    isError: previewError,
    error: previewErrorDetails,
    refetch: refetchPreview,
  } = useSchedulePreview(
    selectedScheduleId,
    { days: previewDays },
    { enabled: !!selectedScheduleId }
  )

  // Persist view mode to localStorage
  useEffect(() => {
    localStorage.setItem(VIEW_MODE_STORAGE_KEY, viewMode)
  }, [viewMode])

  // Handlers
  const handleViewModeChange = useCallback((mode) => {
    setViewMode(mode)
  }, [])

  const handleNavigate = useCallback(
    (direction) => {
      setCurrentDate((prev) => {
        const newDate = new Date(prev)
        switch (direction) {
          case 'today':
            return new Date()
          case 'prev':
            if (viewMode === 'month') {
              newDate.setMonth(newDate.getMonth() - 1)
            } else if (viewMode === 'week') {
              newDate.setDate(newDate.getDate() - 7)
            } else {
              newDate.setDate(newDate.getDate() - 1)
            }
            return newDate
          case 'next':
            if (viewMode === 'month') {
              newDate.setMonth(newDate.getMonth() + 1)
            } else if (viewMode === 'week') {
              newDate.setDate(newDate.getDate() + 7)
            } else {
              newDate.setDate(newDate.getDate() + 1)
            }
            return newDate
          default:
            return prev
        }
      })
    },
    [viewMode]
  )

  const handleScheduleSelect = useCallback((id) => {
    setSelectedScheduleId(id || null)
  }, [])

  const handleCellClick = useCallback((date) => {
    setCurrentDate(date)
    setViewMode('day')
  }, [])

  const handleExecutionClick = useCallback((execution) => {
    setSelectedExecution(execution)
    setIsModalOpen(true)
  }, [])

  const handleCloseModal = useCallback(() => {
    setIsModalOpen(false)
    setSelectedExecution(null)
  }, [])

  // Get moon phase for selected execution's date
  const executionMoonPhase = useMemo(() => {
    if (!selectedExecution || !previewData?.moon_phases) return null
    if (!selectedExecution.start_time || typeof selectedExecution.start_time !== 'string') {
      console.warn('Invalid start_time in execution:', selectedExecution)
      return null
    }
    const dateKey = getDateKey(selectedExecution.start_time)
    return previewData.moon_phases[dateKey] || null
  }, [selectedExecution, previewData])

  // Loading state
  if (schedulesLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <LoadingSpinner />
      </div>
    )
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
      <CalendarHeader
        viewMode={viewMode}
        currentDate={currentDate}
        onViewModeChange={handleViewModeChange}
        onNavigate={handleNavigate}
        schedules={schedules}
        selectedScheduleId={selectedScheduleId}
        onScheduleSelect={handleScheduleSelect}
      />

      {!selectedScheduleId && (
        <div className="flex flex-col items-center justify-center h-64 text-center">
          <CalendarDaysIcon className="h-16 w-16 text-gray-300 dark:text-gray-600 mb-4" />
          <p className="text-lg text-gray-600 dark:text-gray-400 mb-2">
            No schedule selected
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-500">
            Select a schedule from the dropdown above to view its execution preview
          </p>
        </div>
      )}

      {previewError && selectedScheduleId && (
        <div className="flex flex-col items-center justify-center h-64 text-center">
          <ExclamationCircleIcon className="h-12 w-12 text-red-500 dark:text-red-400 mb-4" />
          <p className="text-gray-700 dark:text-gray-300 mb-2">
            Failed to load schedule preview
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
            {previewErrorDetails?.message || 'An error occurred'}
          </p>
          <button
            onClick={() => refetchPreview()}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600
                       focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            Retry
          </button>
        </div>
      )}

      {!previewError && previewLoading && selectedScheduleId && (
        <div className="flex justify-center items-center h-64">
          <LoadingSpinner />
        </div>
      )}

      {!previewError && !previewLoading && selectedScheduleId && (
        <CalendarGrid
          viewMode={viewMode}
          currentDate={currentDate}
          executions={previewData?.executions || []}
          moonPhases={previewData?.moon_phases || {}}
          onCellClick={handleCellClick}
          onExecutionClick={handleExecutionClick}
        />
      )}

      <ExecutionDetailModal
        isOpen={isModalOpen}
        onClose={handleCloseModal}
        execution={selectedExecution}
        moonPhase={executionMoonPhase}
      />
    </div>
  )
}

export default CalendarView
