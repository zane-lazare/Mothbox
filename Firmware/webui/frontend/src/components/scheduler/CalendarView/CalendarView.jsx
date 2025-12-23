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
import CalendarHeader from './CalendarHeader'
import CalendarGrid from './CalendarGrid'
import ExecutionDetailModal from './ExecutionDetailModal'
import LoadingSpinner from '../../LoadingSpinner'
import { useSchedules, useSchedulePreview } from '../../../hooks/useSchedules'
import { getDateKey } from './calendarUtils'

const VIEW_MODE_STORAGE_KEY = 'mothbox-calendar-view-mode'

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
    switch (viewMode) {
      case 'month':
        return 35
      case 'week':
        return 7
      case 'day':
        return 1
      default:
        return 35
    }
  }, [viewMode])

  // Fetch schedule preview (only when schedule is selected)
  const {
    data: previewData,
    isLoading: previewLoading,
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

      {previewLoading ? (
        <div className="flex justify-center items-center h-64">
          <LoadingSpinner />
        </div>
      ) : (
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
