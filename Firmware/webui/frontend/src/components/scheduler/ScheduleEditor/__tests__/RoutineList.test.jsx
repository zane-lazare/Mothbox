import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import RoutineList from '../RoutineList'

// Mock RoutineCard
vi.mock('../RoutineCard', () => ({
  default: vi.fn(({ routine, index, onUpdate, onDelete, disabled }) => (
    <div data-testid={`routine-${index}`}>
      <span>Routine: {routine.routine_id}</span>
      <button onClick={() => onUpdate({ ...routine, updated: true })} disabled={disabled}>
        Update
      </button>
      <button onClick={() => onDelete(routine.routine_id)} disabled={disabled}>
        Delete
      </button>
    </div>
  )),
}))

// Mock NewRoutineCard
vi.mock('../NewRoutineCard', () => ({
  default: vi.fn(({ onComplete, onCancel, disabled }) => (
    <div data-testid="new-routine-card">
      <button
        onClick={() =>
          onComplete({
            routine_id: 'new-routine',
            trigger: { trigger_type: 'interval' },
            actions: [{ id: '1', action_type: 'camera' }],
          })
        }
        disabled={disabled}
      >
        Complete
      </button>
      <button onClick={onCancel} disabled={disabled}>
        Cancel New
      </button>
    </div>
  )),
}))

describe('RoutineList', () => {
  const defaultProps = {
    routines: [],
    onRoutineUpdate: vi.fn(),
    onRoutineDelete: vi.fn(),
    onRoutineAdd: vi.fn(),
    isAddingRoutine: false,
    onStartAddRoutine: vi.fn(),
    onCancelAddRoutine: vi.fn(),
  }

  const mockRoutines = [
    {
      routine_id: 'routine-1',
      trigger: { trigger_type: 'solar', solar_event: 'dusk' },
      actions: [{ id: '1', action_type: 'gpio', action_name: 'attract_on' }],
    },
    {
      routine_id: 'routine-2',
      trigger: { trigger_type: 'interval', interval_minutes: 15 },
      actions: [{ id: '2', action_type: 'camera', action_name: 'takephoto' }],
    },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('rendering', () => {
    it('renders routine-list container', () => {
      render(<RoutineList {...defaultProps} />)
      expect(screen.getByTestId('routine-list')).toBeInTheDocument()
    })

    it('renders empty state when no routines', () => {
      render(<RoutineList {...defaultProps} routines={[]} />)
      expect(screen.getByTestId('routine-list-empty')).toBeInTheDocument()
      expect(screen.getByText('No routines configured')).toBeInTheDocument()
    })

    it('renders add button in empty state', () => {
      render(<RoutineList {...defaultProps} routines={[]} />)
      expect(screen.getByTestId('add-routine')).toBeInTheDocument()
    })

    it('renders routine cards when routines exist', () => {
      render(<RoutineList {...defaultProps} routines={mockRoutines} />)
      expect(screen.getByTestId('routine-0')).toBeInTheDocument()
      expect(screen.getByTestId('routine-1')).toBeInTheDocument()
    })

    it('renders add button at bottom when routines exist', () => {
      render(<RoutineList {...defaultProps} routines={mockRoutines} />)
      expect(screen.getByTestId('add-routine')).toBeInTheDocument()
    })

    it('renders NewRoutineCard when isAddingRoutine is true', () => {
      render(<RoutineList {...defaultProps} routines={mockRoutines} isAddingRoutine={true} />)
      expect(screen.getByTestId('new-routine-card')).toBeInTheDocument()
    })

    it('hides add button when isAddingRoutine is true', () => {
      render(<RoutineList {...defaultProps} routines={mockRoutines} isAddingRoutine={true} />)
      expect(screen.queryByTestId('add-routine')).not.toBeInTheDocument()
    })
  })

  describe('data-testid attributes', () => {
    it('has routine-list on container', () => {
      render(<RoutineList {...defaultProps} routines={mockRoutines} />)
      expect(screen.getByTestId('routine-list')).toBeInTheDocument()
    })

    it('has routine-list-empty on empty state', () => {
      render(<RoutineList {...defaultProps} routines={[]} />)
      expect(screen.getByTestId('routine-list-empty')).toBeInTheDocument()
    })

    it('has add-routine on add button', () => {
      render(<RoutineList {...defaultProps} routines={mockRoutines} />)
      expect(screen.getByTestId('add-routine')).toBeInTheDocument()
    })
  })

  describe('add routine flow', () => {
    it('calls onStartAddRoutine when add button clicked', async () => {
      const user = userEvent.setup()
      const onStartAddRoutine = vi.fn()
      render(<RoutineList {...defaultProps} onStartAddRoutine={onStartAddRoutine} />)

      await user.click(screen.getByTestId('add-routine'))

      expect(onStartAddRoutine).toHaveBeenCalled()
    })

    it('calls onRoutineAdd and onCancelAddRoutine when NewRoutineCard completes', async () => {
      const user = userEvent.setup()
      const onRoutineAdd = vi.fn()
      const onCancelAddRoutine = vi.fn()
      render(
        <RoutineList
          {...defaultProps}
          isAddingRoutine={true}
          onRoutineAdd={onRoutineAdd}
          onCancelAddRoutine={onCancelAddRoutine}
        />
      )

      await user.click(screen.getByText('Complete'))

      expect(onRoutineAdd).toHaveBeenCalledWith({
        routine_id: 'new-routine',
        trigger: { trigger_type: 'interval' },
        actions: [{ id: '1', action_type: 'camera' }],
      })
      expect(onCancelAddRoutine).toHaveBeenCalled()
    })

    it('calls onCancelAddRoutine when NewRoutineCard cancelled', async () => {
      const user = userEvent.setup()
      const onCancelAddRoutine = vi.fn()
      render(
        <RoutineList
          {...defaultProps}
          isAddingRoutine={true}
          onCancelAddRoutine={onCancelAddRoutine}
        />
      )

      await user.click(screen.getByText('Cancel New'))

      expect(onCancelAddRoutine).toHaveBeenCalled()
    })
  })

  describe('update routine', () => {
    it('calls onRoutineUpdate when routine is updated', async () => {
      const user = userEvent.setup()
      const onRoutineUpdate = vi.fn()
      render(
        <RoutineList {...defaultProps} routines={mockRoutines} onRoutineUpdate={onRoutineUpdate} />
      )

      await user.click(screen.getAllByText('Update')[0])

      expect(onRoutineUpdate).toHaveBeenCalledWith({
        ...mockRoutines[0],
        updated: true,
      })
    })
  })

  describe('delete routine', () => {
    it('calls onRoutineDelete when routine is deleted', async () => {
      const user = userEvent.setup()
      const onRoutineDelete = vi.fn()
      render(
        <RoutineList {...defaultProps} routines={mockRoutines} onRoutineDelete={onRoutineDelete} />
      )

      await user.click(screen.getAllByText('Delete')[0])

      expect(onRoutineDelete).toHaveBeenCalledWith('routine-1')
    })
  })

  describe('disabled state', () => {
    it('disables add button when disabled is true', () => {
      render(<RoutineList {...defaultProps} disabled={true} />)
      expect(screen.getByTestId('add-routine')).toBeDisabled()
    })

    it('passes disabled to RoutineCard components', () => {
      render(<RoutineList {...defaultProps} routines={mockRoutines} disabled={true} />)
      // Check that buttons in mocked RoutineCard are disabled
      expect(screen.getAllByText('Update')[0]).toBeDisabled()
      expect(screen.getAllByText('Delete')[0]).toBeDisabled()
    })

    it('passes disabled to NewRoutineCard', () => {
      render(<RoutineList {...defaultProps} isAddingRoutine={true} disabled={true} />)
      expect(screen.getByText('Complete')).toBeDisabled()
      expect(screen.getByText('Cancel New')).toBeDisabled()
    })
  })
})
