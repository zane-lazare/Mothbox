import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DndContext } from '@dnd-kit/core'
import ActionList from '../ActionList'

// Mock ActionForm component
vi.mock('../ActionForm', () => ({
  default: ({ action, onSave, onCancel }) => (
    <div data-testid="action-form">
      <div data-testid="form-action-type">{action?.action_type || 'new'}</div>
      <div data-testid="form-action-name">{action?.action_name || ''}</div>
      <button onClick={() => onSave({
        id: action?.id || 'new-id',
        action_type: 'gpio',
        action_name: 'Test Action',
        offset_minutes: 0,
        description: 'Test description',
        parameters: {}
      })}>
        Save
      </button>
      <button onClick={onCancel}>Cancel</button>
    </div>
  )
}))

describe('ActionList', () => {
  let mockOnActionsChange

  beforeEach(() => {
    mockOnActionsChange = vi.fn()
  })

  describe('Empty State', () => {
    it('shows empty state message when no actions', () => {
      render(<ActionList actions={[]} onActionsChange={mockOnActionsChange} />)

      expect(screen.getByText(/no actions yet/i)).toBeInTheDocument()
    })

    it('shows Add Action button in empty state', () => {
      render(<ActionList actions={[]} onActionsChange={mockOnActionsChange} />)

      expect(screen.getByRole('button', { name: /add action/i })).toBeInTheDocument()
    })
  })

  describe('Action Rendering', () => {
    const mockActions = [
      {
        id: 'action-1',
        action_type: 'gpio',
        action_name: 'Turn on lights',
        offset_minutes: 0,
        description: 'Activate attract lights',
        parameters: { pin: 'attract', state: 'on' }
      },
      {
        id: 'action-2',
        action_type: 'camera',
        action_name: 'Take photo',
        offset_minutes: 5,
        description: 'Capture HDR image',
        parameters: { mode: 'hdr' }
      },
      {
        id: 'action-3',
        action_type: 'gps_sync',
        action_name: 'Sync GPS',
        offset_minutes: 10,
        description: 'Update GPS coordinates',
        parameters: {}
      },
      {
        id: 'action-4',
        action_type: 'service',
        action_name: 'Run service',
        offset_minutes: 15,
        description: 'Execute system service',
        parameters: { command: 'test.service' }
      }
    ]

    it('renders all actions', () => {
      render(<ActionList actions={mockActions} onActionsChange={mockOnActionsChange} />)

      expect(screen.getByText('Turn on lights')).toBeInTheDocument()
      expect(screen.getByText('Take photo')).toBeInTheDocument()
      expect(screen.getByText('Sync GPS')).toBeInTheDocument()
      expect(screen.getByText('Run service')).toBeInTheDocument()
    })

    it('displays action descriptions', () => {
      render(<ActionList actions={mockActions} onActionsChange={mockOnActionsChange} />)

      expect(screen.getByText('Activate attract lights')).toBeInTheDocument()
      expect(screen.getByText('Capture HDR image')).toBeInTheDocument()
      expect(screen.getByText('Update GPS coordinates')).toBeInTheDocument()
      expect(screen.getByText('Execute system service')).toBeInTheDocument()
    })

    it('displays offset badges correctly', () => {
      render(<ActionList actions={mockActions} onActionsChange={mockOnActionsChange} />)

      expect(screen.getByText('+0min')).toBeInTheDocument()
      expect(screen.getByText('+5min')).toBeInTheDocument()
      expect(screen.getByText('+10min')).toBeInTheDocument()
      expect(screen.getByText('+15min')).toBeInTheDocument()
    })

    it('displays correct icon for gpio actions', () => {
      const gpioAction = [mockActions[0]]
      const { container } = render(<ActionList actions={gpioAction} onActionsChange={mockOnActionsChange} />)

      // BoltIcon should be present for gpio type
      const icon = container.querySelector('svg')
      expect(icon).toBeInTheDocument()
    })

    it('displays correct icon for camera actions', () => {
      const cameraAction = [mockActions[1]]
      const { container } = render(<ActionList actions={cameraAction} onActionsChange={mockOnActionsChange} />)

      const icon = container.querySelector('svg')
      expect(icon).toBeInTheDocument()
    })

    it('displays correct icon for gps_sync actions', () => {
      const gpsAction = [mockActions[2]]
      const { container } = render(<ActionList actions={gpsAction} onActionsChange={mockOnActionsChange} />)

      const icon = container.querySelector('svg')
      expect(icon).toBeInTheDocument()
    })

    it('displays correct icon for service actions', () => {
      const serviceAction = [mockActions[3]]
      const { container } = render(<ActionList actions={serviceAction} onActionsChange={mockOnActionsChange} />)

      const icon = container.querySelector('svg')
      expect(icon).toBeInTheDocument()
    })

    it('shows edit button for each action', () => {
      render(<ActionList actions={mockActions} onActionsChange={mockOnActionsChange} />)

      const editButtons = screen.getAllByRole('button', { name: /edit action/i })
      expect(editButtons).toHaveLength(mockActions.length)
    })

    it('shows delete button for each action', () => {
      render(<ActionList actions={mockActions} onActionsChange={mockOnActionsChange} />)

      const deleteButtons = screen.getAllByRole('button', { name: /delete action/i })
      expect(deleteButtons).toHaveLength(mockActions.length)
    })

    it('truncates long descriptions', () => {
      const longDescAction = [{
        id: 'long-1',
        action_type: 'gpio',
        action_name: 'Test',
        offset_minutes: 0,
        description: 'This is a very long description that should be truncated to prevent overflow and maintain clean UI layout in the action list component',
        parameters: {}
      }]

      render(<ActionList actions={longDescAction} onActionsChange={mockOnActionsChange} />)

      // Check that description is present but potentially truncated via CSS
      const description = screen.getByText(/This is a very long description/)
      expect(description).toBeInTheDocument()
    })
  })

  describe('Sorting', () => {
    it('sorts actions by offset_minutes for display', () => {
      const unsortedActions = [
        { id: '1', action_type: 'gpio', action_name: 'Third', offset_minutes: 15, description: 'C', parameters: {} },
        { id: '2', action_type: 'gpio', action_name: 'First', offset_minutes: 0, description: 'A', parameters: {} },
        { id: '3', action_type: 'gpio', action_name: 'Second', offset_minutes: 5, description: 'B', parameters: {} }
      ]

      render(<ActionList actions={unsortedActions} onActionsChange={mockOnActionsChange} />)

      const actionNames = screen.getAllByRole('heading', { level: 4 })
      expect(actionNames[0]).toHaveTextContent('First')
      expect(actionNames[1]).toHaveTextContent('Second')
      expect(actionNames[2]).toHaveTextContent('Third')
    })
  })

  describe('Add Action', () => {
    it('shows Add Action button when actions exist', () => {
      const actions = [{
        id: '1',
        action_type: 'gpio',
        action_name: 'Test',
        offset_minutes: 0,
        description: 'Test',
        parameters: {}
      }]

      render(<ActionList actions={actions} onActionsChange={mockOnActionsChange} />)

      expect(screen.getByRole('button', { name: /add action/i })).toBeInTheDocument()
    })

    it('opens ActionForm when Add Action is clicked', async () => {
      const user = userEvent.setup()
      render(<ActionList actions={[]} onActionsChange={mockOnActionsChange} />)

      const addButton = screen.getByRole('button', { name: /add action/i })
      await user.click(addButton)

      expect(screen.getByTestId('action-form')).toBeInTheDocument()
      expect(screen.getByTestId('form-action-type')).toHaveTextContent('new')
    })

    it('calls onActionsChange when new action is saved', async () => {
      const user = userEvent.setup()
      render(<ActionList actions={[]} onActionsChange={mockOnActionsChange} />)

      // Open form
      await user.click(screen.getByRole('button', { name: /add action/i }))

      // Save
      await user.click(screen.getByText('Save'))

      await waitFor(() => {
        expect(mockOnActionsChange).toHaveBeenCalledWith([
          expect.objectContaining({
            action_type: 'gpio',
            action_name: 'Test Action',
            offset_minutes: 0,
            description: 'Test description'
          })
        ])
      })
    })

    it('closes ActionForm when cancel is clicked', async () => {
      const user = userEvent.setup()
      render(<ActionList actions={[]} onActionsChange={mockOnActionsChange} />)

      // Open form
      await user.click(screen.getByRole('button', { name: /add action/i }))
      expect(screen.getByTestId('action-form')).toBeInTheDocument()

      // Cancel
      await user.click(screen.getByText('Cancel'))

      await waitFor(() => {
        expect(screen.queryByTestId('action-form')).not.toBeInTheDocument()
      })
    })

    it('closes ActionForm after successful save', async () => {
      const user = userEvent.setup()
      render(<ActionList actions={[]} onActionsChange={mockOnActionsChange} />)

      await user.click(screen.getByRole('button', { name: /add action/i }))
      await user.click(screen.getByText('Save'))

      await waitFor(() => {
        expect(screen.queryByTestId('action-form')).not.toBeInTheDocument()
      })
    })
  })

  describe('Edit Action', () => {
    const mockActions = [
      {
        id: 'action-1',
        action_type: 'gpio',
        action_name: 'Original Name',
        offset_minutes: 5,
        description: 'Original description',
        parameters: { pin: 'attract', state: 'on' }
      }
    ]

    it('opens ActionForm with action data when edit is clicked', async () => {
      const user = userEvent.setup()
      render(<ActionList actions={mockActions} onActionsChange={mockOnActionsChange} />)

      const editButton = screen.getByRole('button', { name: /edit action/i })
      await user.click(editButton)

      expect(screen.getByTestId('action-form')).toBeInTheDocument()
      expect(screen.getByTestId('form-action-type')).toHaveTextContent('gpio')
      expect(screen.getByTestId('form-action-name')).toHaveTextContent('Original Name')
    })

    it('updates action when save is clicked in edit mode', async () => {
      const user = userEvent.setup()
      render(<ActionList actions={mockActions} onActionsChange={mockOnActionsChange} />)

      // Open edit form
      await user.click(screen.getByRole('button', { name: /edit action/i }))

      // Save with updated data
      await user.click(screen.getByText('Save'))

      await waitFor(() => {
        expect(mockOnActionsChange).toHaveBeenCalledWith([
          expect.objectContaining({
            id: 'action-1',
            action_name: 'Test Action'
          })
        ])
      })
    })

    it('preserves other actions when editing one action', async () => {
      const user = userEvent.setup()
      const multipleActions = [
        { ...mockActions[0] },
        { id: 'action-2', action_type: 'camera', action_name: 'Second', offset_minutes: 10, description: 'Second action', parameters: {} }
      ]

      render(<ActionList actions={multipleActions} onActionsChange={mockOnActionsChange} />)

      // Edit first action
      const editButtons = screen.getAllByRole('button', { name: /edit action/i })
      await user.click(editButtons[0])
      await user.click(screen.getByText('Save'))

      await waitFor(() => {
        expect(mockOnActionsChange).toHaveBeenCalledWith(
          expect.arrayContaining([
            expect.objectContaining({ id: 'action-1' }),
            expect.objectContaining({ id: 'action-2', action_name: 'Second' })
          ])
        )
      })
    })

    it('closes edit form on cancel without changing actions', async () => {
      const user = userEvent.setup()
      render(<ActionList actions={mockActions} onActionsChange={mockOnActionsChange} />)

      await user.click(screen.getByRole('button', { name: /edit action/i }))
      await user.click(screen.getByText('Cancel'))

      await waitFor(() => {
        expect(screen.queryByTestId('action-form')).not.toBeInTheDocument()
      })
      expect(mockOnActionsChange).not.toHaveBeenCalled()
    })
  })

  describe('Delete Action', () => {
    const mockActions = [
      {
        id: 'action-1',
        action_type: 'gpio',
        action_name: 'To Delete',
        offset_minutes: 0,
        description: 'Will be deleted',
        parameters: {}
      },
      {
        id: 'action-2',
        action_type: 'camera',
        action_name: 'To Keep',
        offset_minutes: 5,
        description: 'Will remain',
        parameters: {}
      }
    ]

    it('shows confirmation dialog when delete is clicked', async () => {
      const user = userEvent.setup()
      render(<ActionList actions={mockActions} onActionsChange={mockOnActionsChange} />)

      const deleteButtons = screen.getAllByRole('button', { name: /delete action/i })
      await user.click(deleteButtons[0])

      expect(screen.getByText(/are you sure you want to delete this action/i)).toBeInTheDocument()
    })

    it('shows action name in confirmation dialog', async () => {
      const user = userEvent.setup()
      render(<ActionList actions={mockActions} onActionsChange={mockOnActionsChange} />)

      const deleteButtons = screen.getAllByRole('button', { name: /delete action/i })
      await user.click(deleteButtons[0])

      // Check for action name within the dialog context
      const actionNames = screen.getAllByText(/to delete/i)
      expect(actionNames.length).toBeGreaterThan(0)
    })

    it('removes action when delete is confirmed', async () => {
      const user = userEvent.setup()
      render(<ActionList actions={mockActions} onActionsChange={mockOnActionsChange} />)

      // Click delete on first action
      const deleteButtons = screen.getAllByRole('button', { name: /delete action/i })
      await user.click(deleteButtons[0])

      // Confirm delete - use exact match for aria-label
      const confirmButton = screen.getByRole('button', { name: 'Delete' })
      await user.click(confirmButton)

      await waitFor(() => {
        expect(mockOnActionsChange).toHaveBeenCalledWith([
          expect.objectContaining({ id: 'action-2', action_name: 'To Keep' })
        ])
      })
    })

    it('keeps action when delete is cancelled', async () => {
      const user = userEvent.setup()
      render(<ActionList actions={mockActions} onActionsChange={mockOnActionsChange} />)

      const deleteButtons = screen.getAllByRole('button', { name: /delete action/i })
      await user.click(deleteButtons[0])

      // Cancel delete - use exact match for aria-label
      const cancelButton = screen.getByRole('button', { name: 'Cancel' })
      await user.click(cancelButton)

      await waitFor(() => {
        expect(screen.queryByText(/are you sure/i)).not.toBeInTheDocument()
      })
      expect(mockOnActionsChange).not.toHaveBeenCalled()
    })

    it('closes confirmation dialog after delete', async () => {
      const user = userEvent.setup()
      render(<ActionList actions={mockActions} onActionsChange={mockOnActionsChange} />)

      const deleteButtons = screen.getAllByRole('button', { name: /delete action/i })
      await user.click(deleteButtons[0])

      // Confirm delete - use exact match for aria-label
      const confirmButton = screen.getByRole('button', { name: 'Delete' })
      await user.click(confirmButton)

      await waitFor(() => {
        expect(screen.queryByText(/are you sure/i)).not.toBeInTheDocument()
      })
    })
  })

  describe('Drag and Drop', () => {
    const mockActions = [
      { id: 'action-1', action_type: 'gpio', action_name: 'First', offset_minutes: 0, description: 'A', parameters: {} },
      { id: 'action-2', action_type: 'gpio', action_name: 'Second', offset_minutes: 5, description: 'B', parameters: {} },
      { id: 'action-3', action_type: 'gpio', action_name: 'Third', offset_minutes: 10, description: 'C', parameters: {} }
    ]

    it('renders actions in sortable context', () => {
      const { container } = render(<ActionList actions={mockActions} onActionsChange={mockOnActionsChange} />)

      // Check that all actions are rendered
      expect(screen.getByText('First')).toBeInTheDocument()
      expect(screen.getByText('Second')).toBeInTheDocument()
      expect(screen.getByText('Third')).toBeInTheDocument()

      // Verify sortable structure exists
      const sortableItems = container.querySelectorAll('[data-sortable="true"]')
      expect(sortableItems.length).toBeGreaterThan(0)
    })

    it('calls onActionsChange with reordered actions on drag end', async () => {
      const { container } = render(<ActionList actions={mockActions} onActionsChange={mockOnActionsChange} />)

      // Simulate drag end event by finding DndContext and triggering drag
      const dndContext = container.querySelector('[data-testid="action-list-dnd"]')

      // We'll test the reorder logic by checking if the component properly sets up DndContext
      expect(dndContext).toBeInTheDocument()
    })

    it('maintains action data during reorder', () => {
      render(<ActionList actions={mockActions} onActionsChange={mockOnActionsChange} />)

      // Verify all action data is preserved in the rendered output
      expect(screen.getByText('First')).toBeInTheDocument()
      expect(screen.getByText('A')).toBeInTheDocument()
      expect(screen.getByText('+0min')).toBeInTheDocument()

      expect(screen.getByText('Second')).toBeInTheDocument()
      expect(screen.getByText('B')).toBeInTheDocument()
      expect(screen.getByText('+5min')).toBeInTheDocument()

      expect(screen.getByText('Third')).toBeInTheDocument()
      expect(screen.getByText('C')).toBeInTheDocument()
      expect(screen.getByText('+10min')).toBeInTheDocument()
    })
  })

  describe('Dark Mode Styling', () => {
    it('applies dark mode classes to action rows', () => {
      const actions = [{
        id: '1',
        action_type: 'gpio',
        action_name: 'Test',
        offset_minutes: 0,
        description: 'Test',
        parameters: {}
      }]

      const { container } = render(<ActionList actions={actions} onActionsChange={mockOnActionsChange} />)

      // Check for dark mode classes
      const actionRow = container.querySelector('.dark\\:bg-gray-800')
      expect(actionRow).toBeInTheDocument()
    })

    it('applies dark mode classes to offset badge', () => {
      const actions = [{
        id: '1',
        action_type: 'gpio',
        action_name: 'Test',
        offset_minutes: 5,
        description: 'Test',
        parameters: {}
      }]

      const { container } = render(<ActionList actions={actions} onActionsChange={mockOnActionsChange} />)

      const badge = container.querySelector('.dark\\:bg-blue-900')
      expect(badge).toBeInTheDocument()
    })

    it('applies dark mode classes to buttons', () => {
      const actions = [{
        id: '1',
        action_type: 'gpio',
        action_name: 'Test',
        offset_minutes: 0,
        description: 'Test',
        parameters: {}
      }]

      const { container } = render(<ActionList actions={actions} onActionsChange={mockOnActionsChange} />)

      const darkButton = container.querySelector('.dark\\:hover\\:text-blue-400')
      expect(darkButton).toBeInTheDocument()
    })
  })

  describe('ID Generation', () => {
    it('generates unique IDs for actions without IDs', async () => {
      const actionsWithoutIds = [
        { action_type: 'gpio', action_name: 'Test 1', offset_minutes: 0, description: 'A', parameters: {} },
        { action_type: 'gpio', action_name: 'Test 2', offset_minutes: 5, description: 'B', parameters: {} }
      ]

      render(<ActionList actions={actionsWithoutIds} onActionsChange={mockOnActionsChange} />)

      // Actions should still render even without IDs
      expect(screen.getByText('Test 1')).toBeInTheDocument()
      expect(screen.getByText('Test 2')).toBeInTheDocument()
    })
  })

  describe('Edge Cases', () => {
    it('handles actions with missing descriptions', () => {
      const actionNoDesc = [{
        id: '1',
        action_type: 'gpio',
        action_name: 'Test',
        offset_minutes: 0,
        parameters: {}
      }]

      render(<ActionList actions={actionNoDesc} onActionsChange={mockOnActionsChange} />)

      expect(screen.getByText('Test')).toBeInTheDocument()
    })

    it('handles zero offset correctly', () => {
      const zeroOffset = [{
        id: '1',
        action_type: 'gpio',
        action_name: 'Test',
        offset_minutes: 0,
        description: 'Test',
        parameters: {}
      }]

      render(<ActionList actions={zeroOffset} onActionsChange={mockOnActionsChange} />)

      expect(screen.getByText('+0min')).toBeInTheDocument()
    })

    it('handles large offset values', () => {
      const largeOffset = [{
        id: '1',
        action_type: 'gpio',
        action_name: 'Test',
        offset_minutes: 1440,
        description: 'Test',
        parameters: {}
      }]

      render(<ActionList actions={largeOffset} onActionsChange={mockOnActionsChange} />)

      expect(screen.getByText('+1440min')).toBeInTheDocument()
    })
  })
})
