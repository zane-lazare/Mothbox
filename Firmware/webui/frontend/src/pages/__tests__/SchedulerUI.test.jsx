import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import SchedulerUI from '../SchedulerUI'

// Mock all hooks and components
vi.mock('../../hooks/useSchedules', () => ({
  useSchedules: vi.fn(),
  useActiveSchedule: vi.fn(),
  useDeactivateSchedule: vi.fn(),
  useCreateSchedule: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useUpdateSchedule: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
}))

vi.mock('../../contexts/SchedulerContext', () => ({
  SchedulerProvider: ({ children }) => <div data-testid="scheduler-provider">{children}</div>,
  useSchedulerContext: vi.fn(() => ({
    state: { schedules: [], activeSchedule: null },
    scheduleActions: { setSchedules: vi.fn(), setActiveSchedule: vi.fn() }
  })),
}))

vi.mock('../../components/scheduler/SchedulerHeader', () => ({
  default: ({ children }) => <div data-testid="scheduler-header">{children}</div>
}))

vi.mock('../../components/scheduler/SchedulerToolbar', () => ({
  default: () => <div data-testid="scheduler-toolbar">Toolbar</div>
}))

vi.mock('../../components/scheduler/ActiveScheduleBanner', () => ({
  default: () => <div data-testid="active-schedule-banner">Active Schedule</div>
}))

vi.mock('../../components/scheduler/ScheduleList', () => ({
  ScheduleList: () => <div data-testid="schedule-list">Schedule List</div>
}))

vi.mock('../../components/scheduler/CalendarView', () => ({
  default: () => <div data-testid="calendar-view">Calendar View</div>
}))

vi.mock('../../components/LoadingSpinner', () => ({
  default: ({ size }) => <div data-testid="loading-spinner" data-size={size}>Loading...</div>
}))

vi.mock('../../components/scheduler/ScheduleEditor', () => ({
  ScheduleEditor: () => <div data-testid="schedule-editor">Schedule Editor</div>
}))

// Import the mocked hooks to configure them
import { useSchedules } from '../../hooks/useSchedules'

// Create QueryClient wrapper
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  })
  return ({ children }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}

describe('SchedulerUI', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Default mock implementation - success state
    useSchedules.mockReturnValue({
      isLoading: false,
      error: null,
      data: []
    })
  })

  it('renders SchedulerHeader with title', () => {
    render(<SchedulerUI />, { wrapper: createWrapper() })

    expect(screen.getByTestId('scheduler-header')).toBeInTheDocument()
  })

  it('renders SchedulerToolbar', () => {
    render(<SchedulerUI />, { wrapper: createWrapper() })

    expect(screen.getByTestId('scheduler-toolbar')).toBeInTheDocument()
  })

  it('renders two-column layout with ScheduleList and CalendarView', () => {
    render(<SchedulerUI />, { wrapper: createWrapper() })

    // Both should be visible in two-column layout
    expect(screen.getByTestId('schedule-list')).toBeInTheDocument()
    expect(screen.getByTestId('calendar-view')).toBeInTheDocument()
  })

  it('renders ScheduleEditor', () => {
    render(<SchedulerUI />, { wrapper: createWrapper() })

    expect(screen.getByTestId('schedule-editor')).toBeInTheDocument()
  })

  it('renders ActiveScheduleBanner', () => {
    render(<SchedulerUI />, { wrapper: createWrapper() })

    expect(screen.getByTestId('active-schedule-banner')).toBeInTheDocument()
  })

  it('wraps content in SchedulerProvider', () => {
    render(<SchedulerUI />, { wrapper: createWrapper() })

    expect(screen.getByTestId('scheduler-provider')).toBeInTheDocument()
  })
})
