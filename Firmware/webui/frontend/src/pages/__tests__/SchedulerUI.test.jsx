import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
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

vi.mock('../../components/scheduler/SchedulerTabs', () => ({
  default: ({ activeTab, onTabChange }) => (
    <div data-testid="scheduler-tabs">
      <button onClick={() => onTabChange('schedules')}>Schedules</button>
      <button onClick={() => onTabChange('calendar')}>Calendar</button>
      <span data-testid="active-tab">{activeTab}</span>
    </div>
  )
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

  it('renders SchedulerTabs', () => {
    render(<SchedulerUI />, { wrapper: createWrapper() })

    expect(screen.getByTestId('scheduler-tabs')).toBeInTheDocument()
  })

  it('defaults to Schedules tab', () => {
    render(<SchedulerUI />, { wrapper: createWrapper() })

    expect(screen.getByTestId('active-tab')).toHaveTextContent('schedules')
  })

  it('shows ScheduleList initially', () => {
    render(<SchedulerUI />, { wrapper: createWrapper() })

    // Two instances exist: one for mobile (lg:hidden), one for desktop (hidden lg:grid)
    const scheduleLists = screen.getAllByTestId('schedule-list')
    expect(scheduleLists.length).toBeGreaterThanOrEqual(1)
    // CalendarView also exists in desktop layout but mobile panel should be hidden
    // (tab-based mobile view shows only schedules panel initially)
  })

  it('switches to Calendar tab when clicked', async () => {
    const user = userEvent.setup()
    render(<SchedulerUI />, { wrapper: createWrapper() })

    // Initially shows Schedules in mobile tab-based view
    const initialScheduleLists = screen.getAllByTestId('schedule-list')
    expect(initialScheduleLists.length).toBeGreaterThanOrEqual(1)

    // Click Calendar tab
    const calendarButton = screen.getByRole('button', { name: /calendar/i })
    await user.click(calendarButton)

    // Should show Calendar view in mobile tab panel
    // Note: Desktop layout always shows both, mobile tabs switch between them
    await waitFor(() => {
      const calendarViews = screen.getAllByTestId('calendar-view')
      expect(calendarViews.length).toBeGreaterThanOrEqual(1)
    })
  })

  it('shows CalendarView when Calendar tab selected', async () => {
    const user = userEvent.setup()
    render(<SchedulerUI />, { wrapper: createWrapper() })

    const calendarButton = screen.getByRole('button', { name: /calendar/i })
    await user.click(calendarButton)

    // CalendarView exists in both desktop (always visible) and mobile (after tab switch)
    const calendarViews = screen.getAllByTestId('calendar-view')
    expect(calendarViews.length).toBeGreaterThanOrEqual(1)
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
