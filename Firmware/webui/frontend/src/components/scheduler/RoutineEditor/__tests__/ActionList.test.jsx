import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ActionList from '../ActionList'

// Mock InlineActionRow component
vi.mock('../InlineActionRow', () => ({
  default: vi.fn(({ action, index, onChange, onDelete, disabled }) => (
    <div data-testid={`action-row-${index}`}>
      <span data-testid="action-type">{action?.action_type || 'empty-type'}</span>
      <span data-testid="action-name">{action?.action_name || 'empty-name'}</span>
      <span data-testid="action-offset">{action?.offset_minutes ?? 0}</span>
      <span data-testid="action-id">{action?.id || 'no-id'}</span>
      <span data-testid="action-disabled">{disabled ? 'disabled' : 'enabled'}</span>
      <button
        onClick={() => onChange({ ...action, action_name: 'updated-name' })}
        data-testid="change-action"
      >
        Change
      </button>
      <button onClick={onDelete} data-testid="delete-action">
        Delete
      </button>
    </div>
  ))
}))

// Mock uuid generation to return predictable IDs
vi.mock('../../../../utils/uuid', () => ({
  generateUUID: vi.fn(() => `uuid-${Date.now()}-${Math.random().toString(36).slice(2)}`)
}))

describe('ActionList', () => {
  let mockOnActionsChange

  beforeEach(() => {
    mockOnActionsChange = vi.fn()
    vi.clearAllMocks()
  })

  describe('Empty State', () => {
    it('shows empty state message when no actions', () => {
      render(<ActionList actions={[]} onActionsChange={mockOnActionsChange} />)

      expect(screen.getByText(/no actions yet/i)).toBeInTheDocument()
    })

    it('shows Add Action button in empty state', () => {
      render(<ActionList actions={[]} onActionsChange={mockOnActionsChange} />)

      expect(screen.getByTestId('add-action')).toBeInTheDocument()
      expect(screen.getByTestId('add-action')).toHaveTextContent('Add Action')
    })

    it('does not render action list when empty', () => {
      render(<ActionList actions={[]} onActionsChange={mockOnActionsChange} />)

      expect(screen.queryByTestId('action-list')).not.toBeInTheDocument()
    })
  })

  describe('Action Rendering', () => {
    const mockActions = [
      {
        id: 'action-1',
        action_type: 'gpio',
        action_name: 'attract_on',
        offset_minutes: 0
      },
      {
        id: 'action-2',
        action_type: 'camera',
        action_name: 'takephoto',
        offset_minutes: 5
      },
      {
        id: 'action-3',
        action_type: 'gps_sync',
        action_name: 'sync',
        offset_minutes: 10
      }
    ]

    it('renders InlineActionRow for each action', () => {
      render(<ActionList actions={mockActions} onActionsChange={mockOnActionsChange} />)

      expect(screen.getByTestId('action-row-0')).toBeInTheDocument()
      expect(screen.getByTestId('action-row-1')).toBeInTheDocument()
      expect(screen.getByTestId('action-row-2')).toBeInTheDocument()
    })

    it('renders action list container when actions exist', () => {
      render(<ActionList actions={mockActions} onActionsChange={mockOnActionsChange} />)

      expect(screen.getByTestId('action-list')).toBeInTheDocument()
    })

    it('shows Add Action button when actions exist', () => {
      render(<ActionList actions={mockActions} onActionsChange={mockOnActionsChange} />)

      expect(screen.getByTestId('add-action')).toBeInTheDocument()
    })

    it('passes action data to InlineActionRow', () => {
      render(<ActionList actions={mockActions} onActionsChange={mockOnActionsChange} />)

      const row0 = screen.getByTestId('action-row-0')
      expect(within(row0).getByTestId('action-type')).toHaveTextContent('gpio')
      expect(within(row0).getByTestId('action-name')).toHaveTextContent('attract_on')
      expect(within(row0).getByTestId('action-offset')).toHaveTextContent('0')

      const row1 = screen.getByTestId('action-row-1')
      expect(within(row1).getByTestId('action-type')).toHaveTextContent('camera')
      expect(within(row1).getByTestId('action-name')).toHaveTextContent('takephoto')
      expect(within(row1).getByTestId('action-offset')).toHaveTextContent('5')
    })
  })

  describe('Add Action', () => {
    it('adds new empty action when Add Action is clicked', async () => {
      const user = userEvent.setup()
      render(<ActionList actions={[]} onActionsChange={mockOnActionsChange} />)

      await user.click(screen.getByTestId('add-action'))

      expect(mockOnActionsChange).toHaveBeenCalledTimes(1)
      const newActions = mockOnActionsChange.mock.calls[0][0]
      expect(newActions).toHaveLength(1)
      expect(newActions[0]).toMatchObject({
        action_type: '',
        action_name: '',
        offset_minutes: 0
      })
    })

    it('new action has generated ID', async () => {
      const user = userEvent.setup()
      render(<ActionList actions={[]} onActionsChange={mockOnActionsChange} />)

      await user.click(screen.getByTestId('add-action'))

      const newActions = mockOnActionsChange.mock.calls[0][0]
      expect(newActions[0].id).toBeTruthy()
      expect(typeof newActions[0].id).toBe('string')
    })

    it('appends new action to existing actions', async () => {
      const user = userEvent.setup()
      const existingActions = [
        { id: 'existing-1', action_type: 'gpio', action_name: 'attract_on', offset_minutes: 0 }
      ]

      render(<ActionList actions={existingActions} onActionsChange={mockOnActionsChange} />)

      await user.click(screen.getByTestId('add-action'))

      const newActions = mockOnActionsChange.mock.calls[0][0]
      expect(newActions).toHaveLength(2)
      expect(newActions[0]).toMatchObject({ id: 'existing-1' })
      expect(newActions[1]).toMatchObject({
        action_type: '',
        action_name: '',
        offset_minutes: 0
      })
    })
  })

  describe('Delete Action', () => {
    it('removes action when delete is clicked', async () => {
      const user = userEvent.setup()
      const actions = [
        { id: 'action-1', action_type: 'gpio', action_name: 'attract_on', offset_minutes: 0 },
        { id: 'action-2', action_type: 'camera', action_name: 'takephoto', offset_minutes: 5 }
      ]

      render(<ActionList actions={actions} onActionsChange={mockOnActionsChange} />)

      // Delete first action
      const row0 = screen.getByTestId('action-row-0')
      await user.click(within(row0).getByTestId('delete-action'))

      expect(mockOnActionsChange).toHaveBeenCalledTimes(1)
      const newActions = mockOnActionsChange.mock.calls[0][0]
      expect(newActions).toHaveLength(1)
      expect(newActions[0].id).toBe('action-2')
    })

    it('removes correct action from middle of list', async () => {
      const user = userEvent.setup()
      const actions = [
        { id: 'action-1', action_type: 'gpio', action_name: 'attract_on', offset_minutes: 0 },
        { id: 'action-2', action_type: 'camera', action_name: 'takephoto', offset_minutes: 5 },
        { id: 'action-3', action_type: 'gps_sync', action_name: 'sync', offset_minutes: 10 }
      ]

      render(<ActionList actions={actions} onActionsChange={mockOnActionsChange} />)

      // Delete middle action
      const row1 = screen.getByTestId('action-row-1')
      await user.click(within(row1).getByTestId('delete-action'))

      const newActions = mockOnActionsChange.mock.calls[0][0]
      expect(newActions).toHaveLength(2)
      expect(newActions[0].id).toBe('action-1')
      expect(newActions[1].id).toBe('action-3')
    })

    it('handles deleting last action', async () => {
      const user = userEvent.setup()
      const actions = [
        { id: 'action-1', action_type: 'gpio', action_name: 'attract_on', offset_minutes: 0 }
      ]

      render(<ActionList actions={actions} onActionsChange={mockOnActionsChange} />)

      await user.click(within(screen.getByTestId('action-row-0')).getByTestId('delete-action'))

      const newActions = mockOnActionsChange.mock.calls[0][0]
      expect(newActions).toHaveLength(0)
    })
  })

  describe('Update Action', () => {
    it('updates action when onChange is called', async () => {
      const user = userEvent.setup()
      const actions = [
        { id: 'action-1', action_type: 'gpio', action_name: 'attract_on', offset_minutes: 0 }
      ]

      render(<ActionList actions={actions} onActionsChange={mockOnActionsChange} />)

      // Click change button (from mock)
      const row0 = screen.getByTestId('action-row-0')
      await user.click(within(row0).getByTestId('change-action'))

      expect(mockOnActionsChange).toHaveBeenCalledTimes(1)
      const newActions = mockOnActionsChange.mock.calls[0][0]
      expect(newActions[0]).toMatchObject({
        id: 'action-1',
        action_name: 'updated-name'
      })
    })

    it('preserves other actions when updating one', async () => {
      const user = userEvent.setup()
      const actions = [
        { id: 'action-1', action_type: 'gpio', action_name: 'attract_on', offset_minutes: 0 },
        { id: 'action-2', action_type: 'camera', action_name: 'takephoto', offset_minutes: 5 }
      ]

      render(<ActionList actions={actions} onActionsChange={mockOnActionsChange} />)

      // Change first action
      await user.click(within(screen.getByTestId('action-row-0')).getByTestId('change-action'))

      const newActions = mockOnActionsChange.mock.calls[0][0]
      expect(newActions).toHaveLength(2)
      expect(newActions[0].action_name).toBe('updated-name')
      expect(newActions[1]).toMatchObject({
        id: 'action-2',
        action_type: 'camera',
        action_name: 'takephoto'
      })
    })

    it('preserves action ID during update', async () => {
      const user = userEvent.setup()
      const actions = [
        { id: 'action-1', action_type: 'gpio', action_name: 'attract_on', offset_minutes: 0 }
      ]

      render(<ActionList actions={actions} onActionsChange={mockOnActionsChange} />)

      await user.click(within(screen.getByTestId('action-row-0')).getByTestId('change-action'))

      const newActions = mockOnActionsChange.mock.calls[0][0]
      expect(newActions[0].id).toBe('action-1')
    })
  })

  describe('Disabled State', () => {
    it('passes disabled=false by default', () => {
      const actions = [
        { id: 'action-1', action_type: 'gpio', action_name: 'attract_on', offset_minutes: 0 }
      ]

      render(<ActionList actions={actions} onActionsChange={mockOnActionsChange} />)

      expect(within(screen.getByTestId('action-row-0')).getByTestId('action-disabled')).toHaveTextContent('enabled')
    })

    it('passes disabled=true to InlineActionRow when disabled', () => {
      const actions = [
        { id: 'action-1', action_type: 'gpio', action_name: 'attract_on', offset_minutes: 0 }
      ]

      render(<ActionList actions={actions} onActionsChange={mockOnActionsChange} disabled={true} />)

      expect(within(screen.getByTestId('action-row-0')).getByTestId('action-disabled')).toHaveTextContent('disabled')
    })

    it('disables Add Action button when disabled', () => {
      render(<ActionList actions={[]} onActionsChange={mockOnActionsChange} disabled={true} />)

      expect(screen.getByTestId('add-action')).toBeDisabled()
    })
  })

  describe('Stable ID Generation', () => {
    it('generates IDs for actions without IDs', () => {
      const actionsWithoutIds = [
        { action_type: 'gpio', action_name: 'attract_on', offset_minutes: 0 },
        { action_type: 'camera', action_name: 'takephoto', offset_minutes: 5 }
      ]

      render(<ActionList actions={actionsWithoutIds} onActionsChange={mockOnActionsChange} />)

      // Actions should still render
      expect(screen.getByTestId('action-row-0')).toBeInTheDocument()
      expect(screen.getByTestId('action-row-1')).toBeInTheDocument()

      // Check that IDs were generated
      const row0Id = within(screen.getByTestId('action-row-0')).getByTestId('action-id').textContent
      const row1Id = within(screen.getByTestId('action-row-1')).getByTestId('action-id').textContent

      expect(row0Id).not.toBe('no-id')
      expect(row1Id).not.toBe('no-id')
      expect(row0Id).not.toBe(row1Id) // Different IDs
    })

    it('preserves existing IDs', () => {
      const actions = [
        { id: 'my-existing-id', action_type: 'gpio', action_name: 'attract_on', offset_minutes: 0 }
      ]

      render(<ActionList actions={actions} onActionsChange={mockOnActionsChange} />)

      const row0Id = within(screen.getByTestId('action-row-0')).getByTestId('action-id').textContent
      expect(row0Id).toBe('my-existing-id')
    })
  })

  describe('Edge Cases', () => {
    it('handles undefined actions prop', () => {
      render(<ActionList onActionsChange={mockOnActionsChange} />)

      expect(screen.getByText(/no actions yet/i)).toBeInTheDocument()
      expect(screen.getByTestId('add-action')).toBeInTheDocument()
    })

    it('handles actions with missing fields', () => {
      const actions = [
        { id: 'action-1' } // Missing action_type, action_name, offset_minutes
      ]

      render(<ActionList actions={actions} onActionsChange={mockOnActionsChange} />)

      // Should still render without crashing
      expect(screen.getByTestId('action-row-0')).toBeInTheDocument()
    })

    it('handles empty action array', () => {
      render(<ActionList actions={[]} onActionsChange={mockOnActionsChange} />)

      expect(screen.getByText(/no actions yet/i)).toBeInTheDocument()
    })
  })
})
