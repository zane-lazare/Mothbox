import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import NewRoutineCard from '../NewRoutineCard'

// Mock TriggerSelector
vi.mock('../../TriggerSelector', () => ({
  default: vi.fn(({ trigger, onChange, disabled }) => (
    <div data-testid="mock-trigger-selector">
      <span>Trigger: {trigger?.trigger_type}</span>
      <button
        onClick={() => onChange({ trigger_type: 'solar', solar_event: 'dusk' })}
        disabled={disabled}
      >
        Change to Solar
      </button>
    </div>
  )),
}))

// Mock ActionList
vi.mock('../../RoutineEditor/ActionList', () => ({
  default: vi.fn(({ actions, onActionsChange, disabled }) => (
    <div data-testid="mock-action-list">
      <span data-testid="action-count">Actions: {actions?.length || 0}</span>
      <button
        onClick={() =>
          onActionsChange([
            ...actions,
            { id: 'new', action_type: 'camera', action_name: 'takephoto' },
          ])
        }
        disabled={disabled}
      >
        Add Action
      </button>
      <button onClick={() => onActionsChange([])} disabled={disabled}>
        Clear Actions
      </button>
    </div>
  )),
}))

// Mock uuid
vi.mock('@/utils/uuid', () => ({
  generateUUID: vi.fn(() => 'mock-uuid-123'),
}))

describe('NewRoutineCard', () => {
  const defaultProps = {
    onComplete: vi.fn(),
    onCancel: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('rendering', () => {
    it('renders new-routine-card container', () => {
      render(<NewRoutineCard {...defaultProps} />)
      expect(screen.getByTestId('new-routine-card')).toBeInTheDocument()
    })

    it('renders header with "New Routine" title', () => {
      render(<NewRoutineCard {...defaultProps} />)
      expect(screen.getByText('New Routine')).toBeInTheDocument()
    })

    it('renders TriggerSelector', () => {
      render(<NewRoutineCard {...defaultProps} />)
      expect(screen.getByTestId('mock-trigger-selector')).toBeInTheDocument()
    })

    it('renders ActionList', () => {
      render(<NewRoutineCard {...defaultProps} />)
      expect(screen.getByTestId('mock-action-list')).toBeInTheDocument()
    })

    it('renders Cancel button', () => {
      render(<NewRoutineCard {...defaultProps} />)
      expect(screen.getByText('Cancel')).toBeInTheDocument()
    })

    it('renders save button with data-testid', () => {
      render(<NewRoutineCard {...defaultProps} />)
      expect(screen.getByTestId('save-routine')).toBeInTheDocument()
      expect(screen.getByTestId('save-routine')).toHaveTextContent('Add Routine')
    })

    it('shows hint when no actions added', () => {
      render(<NewRoutineCard {...defaultProps} />)
      expect(
        screen.getByText('Add at least one action to save the routine')
      ).toBeInTheDocument()
    })
  })

  describe('initial state', () => {
    it('initializes with interval trigger', () => {
      render(<NewRoutineCard {...defaultProps} />)
      expect(screen.getByText('Trigger: interval')).toBeInTheDocument()
    })

    it('initializes with empty actions', () => {
      render(<NewRoutineCard {...defaultProps} />)
      expect(screen.getByTestId('action-count')).toHaveTextContent('Actions: 0')
    })

    it('save button is disabled with no actions', () => {
      render(<NewRoutineCard {...defaultProps} />)
      expect(screen.getByTestId('save-routine')).toBeDisabled()
    })
  })

  describe('trigger changes', () => {
    it('updates trigger when changed', async () => {
      const user = userEvent.setup()
      render(<NewRoutineCard {...defaultProps} />)

      await user.click(screen.getByText('Change to Solar'))

      expect(screen.getByText('Trigger: solar')).toBeInTheDocument()
    })
  })

  describe('action changes', () => {
    it('updates actions when added', async () => {
      const user = userEvent.setup()
      render(<NewRoutineCard {...defaultProps} />)

      await user.click(screen.getByText('Add Action'))

      expect(screen.getByTestId('action-count')).toHaveTextContent('Actions: 1')
    })

    it('enables save button when action is added', async () => {
      const user = userEvent.setup()
      render(<NewRoutineCard {...defaultProps} />)

      await user.click(screen.getByText('Add Action'))

      expect(screen.getByTestId('save-routine')).not.toBeDisabled()
    })

    it('hides hint when actions exist', async () => {
      const user = userEvent.setup()
      render(<NewRoutineCard {...defaultProps} />)

      await user.click(screen.getByText('Add Action'))

      expect(
        screen.queryByText('Add at least one action to save the routine')
      ).not.toBeInTheDocument()
    })
  })

  describe('save functionality', () => {
    it('calls onComplete with routine data when saved', async () => {
      const user = userEvent.setup()
      const onComplete = vi.fn()
      render(<NewRoutineCard {...defaultProps} onComplete={onComplete} />)

      // Add an action first
      await user.click(screen.getByText('Add Action'))

      // Click save
      await user.click(screen.getByTestId('save-routine'))

      expect(onComplete).toHaveBeenCalledWith({
        routine_id: 'mock-uuid-123',
        name: '',
        trigger: { trigger_type: 'interval', interval_minutes: 15, time_window: null },
        actions: [{ id: 'new', action_type: 'camera', action_name: 'takephoto' }],
      })
    })

    it('includes updated trigger in saved routine', async () => {
      const user = userEvent.setup()
      const onComplete = vi.fn()
      render(<NewRoutineCard {...defaultProps} onComplete={onComplete} />)

      // Change trigger
      await user.click(screen.getByText('Change to Solar'))

      // Add an action
      await user.click(screen.getByText('Add Action'))

      // Click save
      await user.click(screen.getByTestId('save-routine'))

      expect(onComplete).toHaveBeenCalledWith(
        expect.objectContaining({
          trigger: { trigger_type: 'solar', solar_event: 'dusk' },
        })
      )
    })
  })

  describe('cancel functionality', () => {
    it('calls onCancel when Cancel clicked', async () => {
      const user = userEvent.setup()
      const onCancel = vi.fn()
      render(<NewRoutineCard {...defaultProps} onCancel={onCancel} />)

      await user.click(screen.getByText('Cancel'))

      expect(onCancel).toHaveBeenCalled()
    })
  })

  describe('disabled state', () => {
    it('disables TriggerSelector when disabled', () => {
      render(<NewRoutineCard {...defaultProps} disabled={true} />)
      expect(screen.getByText('Change to Solar')).toBeDisabled()
    })

    it('disables ActionList when disabled', () => {
      render(<NewRoutineCard {...defaultProps} disabled={true} />)
      expect(screen.getByText('Add Action')).toBeDisabled()
    })

    it('disables Cancel button when disabled', () => {
      render(<NewRoutineCard {...defaultProps} disabled={true} />)
      expect(screen.getByText('Cancel')).toBeDisabled()
    })

    it('disables save button when disabled', () => {
      render(<NewRoutineCard {...defaultProps} disabled={true} />)

      // Even with actions, should be disabled
      // Note: We can't add actions when disabled, so save stays disabled
      expect(screen.getByTestId('save-routine')).toBeDisabled()
    })
  })
})
