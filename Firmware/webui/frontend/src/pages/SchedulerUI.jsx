import { useState } from 'react'
import { SchedulerProvider } from '../contexts/SchedulerContext'
import { useSchedules } from '../hooks/useSchedules'
import SchedulerHeader from '../components/scheduler/SchedulerHeader'
import SchedulerToolbar from '../components/scheduler/SchedulerToolbar'
import SchedulerTabs from '../components/scheduler/SchedulerTabs'
import ActiveScheduleBanner from '../components/scheduler/ActiveScheduleBanner'
import ScheduleListPlaceholder from '../components/scheduler/ScheduleListPlaceholder'
import CalendarViewPlaceholder from '../components/scheduler/CalendarViewPlaceholder'
import LoadingSpinner from '../components/LoadingSpinner'

function SchedulerUIContent() {
  const [activeTab, setActiveTab] = useState('schedules')
  const { isLoading, error } = useSchedules()

  if (isLoading) {
    return (
      <div className="flex justify-center items-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-12 text-red-600">
        Error loading schedules: {error.message}
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto space-y-4 px-4 py-2">
      <SchedulerHeader>
        <SchedulerToolbar />
      </SchedulerHeader>
      <ActiveScheduleBanner />
      <SchedulerTabs activeTab={activeTab} onTabChange={setActiveTab} />
      {activeTab === 'schedules' && (
        <div id="schedules-panel" role="tabpanel">
          <ScheduleListPlaceholder />
        </div>
      )}
      {activeTab === 'calendar' && (
        <div id="calendar-panel" role="tabpanel">
          <CalendarViewPlaceholder />
        </div>
      )}
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
