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

import { useState, useMemo, useCallback, useEffect, startTransition } from 'react'
import { CalendarDaysIcon, ExclamationCircleIcon } from '@heroicons/react/24/outline'
import CalendarHeader from './CalendarHeader'
import CalendarGrid from './CalendarGrid'
import ExecutionDetailModal from './ExecutionDetailModal'
import LoadingSpinner from '../../LoadingSpinner'
import { useSchedules, useSchedulePreview, useActiveSchedule } from '../../../hooks/useSchedules'
import { getDateKey } from './calendarUtils'
import { PANEL_STYLES } from '../constants'

const VIEW_MODE_STORAGE_KEY = 'mothbox-calendar-view-mode'

type ViewMode = 'month' | 'week' | 'day'

/**
 * Valid view mode values.
 * Used to validate localStorage values before using them.
 */
const VALID_VIEW_MODES: ViewMode[] = ['month', 'week', 'day']

/**
 * Number of days to fetch for each view mode.
 * Month: 42 days covers full 6-week grid (7 days × 6 weeks)
 * Day: 2 days to capture overnight schedules that span midnight
 */
const PREVIEW_DAYS: Record<ViewMode, number> = {
  month: 42,
  week: 7,
  day: 2,
}

interface Execution {
  id?: string
  pattern_id: string
  pattern_name: string
  start_time: string
  end_time?: string
  trigger_info?: string
  actions?: Array<{
    action_type?: string
    type?: string
    action_name?: string
    offset_minutes?: number
  }>
}

/**
 * CalendarView component
 *
 * @example
 * <CalendarView />
 */
export function CalendarView() {
  // State management
  const [viewMode, setViewMode] = useState<ViewMode>(() => {
    const stored = localStorage.getItem(VIEW_MODE_STORAGE_KEY)
    return VALID_VIEW_MODES.includes(stored as ViewMode) ? (stored as ViewMode) : 'month'
  })
  const [currentDate, setCurrentDate] = useState<Date>(() => new Date())
  const [selectedScheduleId, setSelectedScheduleId] = useState<string | null>(null)
  const [selectedExecution, setSelectedExecution] = useState<Execution | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)
  // Pattern offset for week view (0, 7, 14, etc.) - tracks which 7-day window we're viewing
  const [patternOffset, setPatternOffset] = useState(0)

  // Fetch schedules list (include built-in schedules for dropdown)
  const { data: schedulesData, isLoading: schedulesLoading } = useSchedules({ include_builtin: true })
  const schedules = schedulesData?.schedules || []

  // Fetch active schedule for auto-selection
  const { data: activeData } = useActiveSchedule()

  // Auto-select schedule on mount: prefer active, fall back to enabled
  useEffect(() => {
    // Don't override if user has already selected a schedule
    if (selectedScheduleId) return

    // Prefer active schedule
    if (activeData?.active_schedule?.schedule_id) {
      setSelectedScheduleId(activeData.active_schedule.schedule_id)
      return
    }

    // Fall back to first enabled schedule
    const enabledSchedule = schedules.find((s) => s.enabled)
    if (enabledSchedule?.schedule_id) {
      setSelectedScheduleId(enabledSchedule.schedule_id)
    }
  }, [activeData?.active_schedule?.schedule_id, schedules, selectedScheduleId])

  // Calculate preview days based on view mode
  const previewDays = useMemo(() => {
    return PREVIEW_DAYS[viewMode] || PREVIEW_DAYS.month
  }, [viewMode])

  // Get browser timezone for cycle detection
  const browserTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone

  // Fetch schedule preview (only when schedule is selected)
  const {
    data: previewData,
    isLoading: previewLoading,
    isError: previewError,
    error: previewErrorDetails,
    refetch: refetchPreview,
  } = useSchedulePreview(
    selectedScheduleId,
    { days: previewDays, tz: browserTimezone },
    { enabled: !!selectedScheduleId }
  )

  // Persist view mode to localStorage
  useEffect(() => {
    localStorage.setItem(VIEW_MODE_STORAGE_KEY, viewMode)
  }, [viewMode])

  // Compute max pattern days from cycle info (for week view navigation bounds)
  const maxPatternDays = useMemo(() => {
    return previewData?.cycle_info?.suggested_preview_days ?? 7
  }, [previewData?.cycle_info])

  // Reset pattern offset when schedule changes
  useEffect(() => {
    setPatternOffset(0)
  }, [selectedScheduleId])

  // Handlers
  const handleViewModeChange = useCallback((mode: ViewMode) => {
    setViewMode(mode)
  }, [])

  const handleNavigate = useCallback(
    (direction: 'prev' | 'next' | 'today') => {
      // Week view uses pattern offset instead of date navigation
      if (viewMode === 'week') {
        if (direction === 'prev') {
          setPatternOffset(prev => Math.max(0, prev - 7))
        } else if (direction === 'next') {
          setPatternOffset(prev => Math.min(maxPatternDays - 7, prev + 7))
        }
        // 'today' is not applicable in week view (no Today button shown)
        return
      }

      // Month and day views use date navigation
      setCurrentDate((prev) => {
        const newDate = new Date(prev)
        switch (direction) {
          case 'today':
            return new Date()
          case 'prev':
            if (viewMode === 'month') {
              // Preserve day-of-month when navigating months (e.g., Jan 30 → Dec 30)
              const originalDay = prev.getDate()
              newDate.setDate(1) // Set to 1st to avoid overflow during month change
              newDate.setMonth(newDate.getMonth() - 1)
              // Clamp to last day of month if original day exceeds it
              const lastDayOfMonth = new Date(newDate.getFullYear(), newDate.getMonth() + 1, 0).getDate()
              newDate.setDate(Math.min(originalDay, lastDayOfMonth))
            } else {
              newDate.setDate(newDate.getDate() - 1)
            }
            return newDate
          case 'next':
            if (viewMode === 'month') {
              // Preserve day-of-month when navigating months (e.g., Jan 31 → Feb 28/29)
              const originalDay = prev.getDate()
              newDate.setDate(1) // Set to 1st to avoid overflow during month change
              newDate.setMonth(newDate.getMonth() + 1)
              // Clamp to last day of month if original day exceeds it
              const lastDayOfMonth = new Date(newDate.getFullYear(), newDate.getMonth() + 1, 0).getDate()
              newDate.setDate(Math.min(originalDay, lastDayOfMonth))
            } else {
              newDate.setDate(newDate.getDate() + 1)
            }
            return newDate
          default:
            return prev
        }
      })
    },
    [viewMode, maxPatternDays]
  )

  const handleScheduleSelect = useCallback((id: string | null) => {
    setSelectedScheduleId(id || null)
  }, [])

  const handleCellClick = useCallback((date: Date) => {
    // Use startTransition to batch non-urgent state updates and reduce re-renders
    startTransition(() => {
      setCurrentDate(date)
      setViewMode('day')
    })
  }, [])

  const handleExecutionClick = useCallback((execution: Execution) => {
    setSelectedExecution(execution)
    setIsModalOpen(true)
  }, [])

  const handleCloseModal = useCallback(() => {
    setIsModalOpen(false)
    setSelectedExecution(null)
  }, [])

  // Get moon phase for selected execution's date
  // Using specific moon_phases dependency instead of entire previewData object
  const moonPhases = previewData?.moon_phases
  const executionMoonPhase = useMemo(() => {
    if (!selectedExecution || !moonPhases) return null
    if (!selectedExecution.start_time || typeof selectedExecution.start_time !== 'string') {
      if (import.meta.env.DEV) {
        console.warn('Invalid start_time in execution:', selectedExecution)
      }
      return null
    }
    const dateKey = getDateKey(selectedExecution.start_time)
    return moonPhases[dateKey] || null
  }, [selectedExecution, moonPhases])

  // Loading state
  if (schedulesLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <LoadingSpinner />
      </div>
    )
  }

  return (
    <div className={PANEL_STYLES.container} aria-hidden={isModalOpen}>
      <CalendarHeader
        viewMode={viewMode}
        currentDate={currentDate}
        onViewModeChange={handleViewModeChange}
        onNavigate={handleNavigate}
        schedules={schedules}
        selectedScheduleId={selectedScheduleId}
        onScheduleSelect={handleScheduleSelect}
        patternOffset={patternOffset}
        maxPatternDays={maxPatternDays}
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
            {(previewErrorDetails as Error)?.message || 'An error occurred'}
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
          conflicts={previewData?.conflicts || []}
          moonPhases={previewData?.moon_phases || {}}
          cycleInfo={previewData?.cycle_info || null}
          onCellClick={handleCellClick}
          onExecutionClick={handleExecutionClick}
          patternOffset={patternOffset}
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
