import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import ActivationPanel from '../ActivationPanel'

// Mock hooks
vi.mock('../../../../hooks/useSchedules', () => ({
  useActiveSchedule: vi.fn(),
  useActivateSchedule: vi.fn(),
  useDeactivateSchedule: vi.fn(),
  useSchedulePreview: vi.fn(),
}))

vi.mock('../../ActivationProgress/ActivationProgress', () => ({
  default: vi.fn(() => <div data-testid="activation-progress" />),
}))

// eslint-disable-next-line @typescript-eslint/ban-ts-comment
// @ts-expect-error -- .js module
import { useActiveSchedule, useActivateSchedule, useDeactivateSchedule, useSchedulePreview } from '../../../../hooks/useSchedules'

describe('ActivationPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useActivateSchedule.mockReturnValue({ mutate: vi.fn() })
    useDeactivateSchedule.mockReturnValue({ mutate: vi.fn(), isPending: false })
    useSchedulePreview.mockReturnValue({ data: null })
  })

  describe('coordinate source stat (Issue #382)', () => {
    it('shows "Approx. location" with amber dot for timezone source', () => {
      useActiveSchedule.mockReturnValue({
        data: {
          active_schedule: { schedule_id: 'sched-1' },
          coordinates_source: 'timezone',
        },
        refetch: vi.fn(),
      })

      render(
        <ActivationPanel scheduleId="sched-1" routineCount={2} hasUnsavedChanges={false} />
      )

      const stat = screen.getByTestId('coord-source-stat')
      expect(stat).toHaveTextContent('Approx. location')
    })

    it('shows "GPS" with green dot for gps source', () => {
      useActiveSchedule.mockReturnValue({
        data: {
          active_schedule: { schedule_id: 'sched-1' },
          coordinates_source: 'gps',
        },
        refetch: vi.fn(),
      })

      render(
        <ActivationPanel scheduleId="sched-1" routineCount={2} hasUnsavedChanges={false} />
      )

      const stat = screen.getByTestId('coord-source-stat')
      expect(stat).toHaveTextContent('GPS')
    })

    it('shows "Manual" with blue dot for explicit source', () => {
      useActiveSchedule.mockReturnValue({
        data: {
          active_schedule: { schedule_id: 'sched-1' },
          coordinates_source: 'explicit',
        },
        refetch: vi.fn(),
      })

      render(
        <ActivationPanel scheduleId="sched-1" routineCount={2} hasUnsavedChanges={false} />
      )

      const stat = screen.getByTestId('coord-source-stat')
      expect(stat).toHaveTextContent('Manual')
    })

    it('does not show coordinate stat when schedule is inactive', () => {
      useActiveSchedule.mockReturnValue({
        data: { active_schedule: null },
        refetch: vi.fn(),
      })

      render(
        <ActivationPanel scheduleId="sched-1" routineCount={2} hasUnsavedChanges={false} />
      )

      expect(screen.queryByTestId('coord-source-stat')).not.toBeInTheDocument()
    })
  })
})
