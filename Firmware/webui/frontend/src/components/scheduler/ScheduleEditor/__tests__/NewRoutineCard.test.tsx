import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import NewRoutineCard from '../NewRoutineCard'

// Mock TriggerForm
vi.mock('../TriggerForm', () => ({
  default: vi.fn(({ value, onChange, disabled }) => (
    <div data-testid="mock-trigger-form">
      <span>Trigger: {value?.trigger_type}</span>
      <button
        onClick={() => onChange({ trigger_type: 'solar', solar_event: 'dusk', offset_minutes: 0 })}
        disabled={disabled}
      >
        Change to Solar
      </button>
    </div>
  )),
}))

// Mock ActionList
vi.mock('../ActionList', () => ({
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

// Mock PreConditionForm
vi.mock('../PreConditionForm', () => ({
  default: vi.fn(({ preCondition, onChange, disabled }) => (
    <div data-testid="mock-pre-condition-form">
      <span data-testid="pre-condition-status">
        {preCondition ? 'enabled' : 'disabled'}
      </span>
      <button
        onClick={() =>
          onChange({
            trigger_type: 'sensor',
            sensor_type: 'light',
            comparison: 'lt',
            threshold: 100,
            cooldown_minutes: 5,
          })
        }
        disabled={disabled}
        data-testid="enable-pre-condition"
      >
        Enable Pre-Condition
      </button>
      <button
        onClick={() => onChange(null)}
        disabled={disabled}
        data-testid="disable-pre-condition"
      >
        Disable Pre-Condition
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

    it('renders TriggerForm', () => {
      render(<NewRoutineCard {...defaultProps} />)
      expect(screen.getByTestId('mock-trigger-form')).toBeInTheDocument()
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
        trigger: {
          trigger_type: 'interval',
          interval_minutes: 60,
          time_window_start: '00:00',
          time_window_end: '23:59',
          days_of_week: [0, 1, 2, 3, 4, 5, 6],
        },
        actions: [{ id: 'new', action_type: 'camera', action_name: 'takephoto' }],
        pre_condition: null,
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
          trigger: { trigger_type: 'solar', solar_event: 'dusk', offset_minutes: 0 },
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
    it('disables TriggerForm when disabled', () => {
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

  describe('pre-condition integration', () => {
    it('renders PreConditionForm', () => {
      render(<NewRoutineCard {...defaultProps} />)
      expect(screen.getByTestId('mock-pre-condition-form')).toBeInTheDocument()
    })

    it('initializes with no pre-condition', () => {
      render(<NewRoutineCard {...defaultProps} />)
      expect(screen.getByTestId('pre-condition-status')).toHaveTextContent('disabled')
    })

    it('includes pre_condition in saved routine when set', async () => {
      const user = userEvent.setup()
      const onComplete = vi.fn()
      render(<NewRoutineCard {...defaultProps} onComplete={onComplete} />)

      // Enable pre-condition
      await user.click(screen.getByTestId('enable-pre-condition'))

      // Add an action
      await user.click(screen.getByText('Add Action'))

      // Save
      await user.click(screen.getByTestId('save-routine'))

      expect(onComplete).toHaveBeenCalledWith(
        expect.objectContaining({
          pre_condition: {
            trigger_type: 'sensor',
            sensor_type: 'light',
            comparison: 'lt',
            threshold: 100,
            cooldown_minutes: 5,
          },
        })
      )
    })

    it('saves routine without pre_condition when not set', async () => {
      const user = userEvent.setup()
      const onComplete = vi.fn()
      render(<NewRoutineCard {...defaultProps} onComplete={onComplete} />)

      // Add an action (no pre-condition)
      await user.click(screen.getByText('Add Action'))

      // Save
      await user.click(screen.getByTestId('save-routine'))

      const savedRoutine = onComplete.mock.calls[0][0]
      expect(savedRoutine.pre_condition).toBeNull()
    })
  })
})
