import { useState, useCallback } from 'react'
import { SchedulerProvider } from '../contexts/SchedulerContext'
import SchedulerHeader from '../components/scheduler/SchedulerHeader'
import SchedulerToolbar from '../components/scheduler/SchedulerToolbar'
import ActiveScheduleBanner from '../components/scheduler/ActiveScheduleBanner'
import { ScheduleList } from '../components/scheduler/ScheduleList'
import { ScheduleEditor } from '../components/scheduler/ScheduleEditor'
import CalendarView from '../components/scheduler/CalendarView'
import ErrorBoundary from '../components/ErrorBoundary'
import { useCreateSchedule, useUpdateSchedule } from '../hooks/useSchedules'
import toast from 'react-hot-toast'

function SchedulerUIContent() {
  const [editorOpen, setEditorOpen] = useState(false)
  const [editingSchedule, setEditingSchedule] = useState(null)

  const { mutateAsync: createSchedule, isPending: isCreating } = useCreateSchedule()
  const { mutateAsync: updateSchedule, isPending: isUpdating } = useUpdateSchedule()

  /**
   * Handle editing an existing schedule
   * Opens ScheduleEditor with the schedule data
   */
  const handleEditSchedule = useCallback((schedule) => {
    setEditingSchedule(schedule)
    setEditorOpen(true)
  }, [])

  /**
   * Handle creating a new schedule
   * Opens ScheduleEditor with no existing data
   */
  const handleNewSchedule = useCallback(() => {
    setEditingSchedule(null)
    setEditorOpen(true)
  }, [])

  /**
   * Handle saving a schedule (create or update)
   */
  const handleSaveSchedule = useCallback(async (scheduleData) => {
    try {
      if (editingSchedule?.schedule_id) {
        // Update existing schedule
        await updateSchedule({
          id: editingSchedule.schedule_id,
          data: scheduleData,
        })
        toast.success(`Schedule "${scheduleData.name}" updated`)
      } else {
        // Create new schedule
        await createSchedule(scheduleData)
        toast.success(`Schedule "${scheduleData.name}" created`)
      }
      setEditorOpen(false)
      setEditingSchedule(null)
    } catch (error) {
      // Error toast is handled by mutation's onError callback
      // Keep editor open so user can retry
      console.error('Error saving schedule:', error)
    }
  }, [editingSchedule, createSchedule, updateSchedule])

  /**
   * Handle canceling the editor
   */
  const handleCancelEditor = useCallback(() => {
    setEditorOpen(false)
    setEditingSchedule(null)
  }, [])

  return (
    <div className="max-w-7xl mx-auto space-y-4 px-4 py-2">
      <SchedulerHeader>
        <SchedulerToolbar onNewSchedule={handleNewSchedule} />
      </SchedulerHeader>
      <ActiveScheduleBanner />

      {/* Two-column layout - always visible */}
      <div className="grid grid-cols-3 gap-6">
        {/* Left column: Schedule List (1/3 width) */}
        <div className="col-span-1">
          <ErrorBoundary
            errorTitle="Error loading schedules"
            errorMessage="Failed to load the schedule list"
            onReset={() => window.location.reload()}
          >
            <ScheduleList onEditSchedule={handleEditSchedule} variant="sidebar" />
          </ErrorBoundary>
        </div>
        {/* Right column: Calendar/Timeline (2/3 width) */}
        <div className="col-span-2">
          <ErrorBoundary
            errorTitle="Error loading calendar"
            errorMessage="Failed to load the calendar view"
            onReset={() => window.location.reload()}
          >
            <CalendarView />
          </ErrorBoundary>
        </div>
      </div>

      <ScheduleEditor
        isOpen={editorOpen}
        schedule={editingSchedule}
        onSave={handleSaveSchedule}
        onCancel={handleCancelEditor}
        isSaving={isCreating || isUpdating}
      />
    </div>
  )
}

// Wrap in SchedulerProvider to provide schedule state to all child components
export default function SchedulerUI() {
  return (
    <SchedulerProvider>
      <SchedulerUIContent />
    </SchedulerProvider>
  )
}
