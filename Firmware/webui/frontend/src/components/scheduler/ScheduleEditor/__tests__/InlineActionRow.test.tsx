import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import InlineActionRow from '../InlineActionRow'
import type { RoutineAction } from '../scheduler-types'

describe('InlineActionRow', () => {
  let mockOnChange: ReturnType<typeof vi.fn<(action: RoutineAction) => void>>
  let mockOnDelete: ReturnType<typeof vi.fn<(index: number) => void>>

  const defaultAction: RoutineAction = {
    id: 'action-1',
    action_type: 'gpio',
    action_name: 'attract_on',
    offset_minutes: 0,
  }

  beforeEach(() => {
    mockOnChange = vi.fn<(action: RoutineAction) => void>()
    mockOnDelete = vi.fn<(index: number) => void>()
  })

  describe('Rendering', () => {
    it('renders action type select with correct value', () => {
      render(
        <InlineActionRow
          action={defaultAction}
          index={0}
          onChange={mockOnChange}
          onDelete={mockOnDelete}
        />
      )

      const typeSelect = screen.getByTestId('action-type') as HTMLSelectElement
      expect(typeSelect.value).toBe('gpio')
    })

    it('renders action name select with correct value', () => {
      render(
        <InlineActionRow
          action={defaultAction}
          index={0}
          onChange={mockOnChange}
          onDelete={mockOnDelete}
        />
      )

      const nameSelect = screen.getByTestId('action-name') as HTMLSelectElement
      expect(nameSelect.value).toBe('attract_on')
    })

    it('renders offset input with correct value', () => {
      const action: RoutineAction = { ...defaultAction, offset_minutes: 15 }
      render(
        <InlineActionRow
          action={action}
          index={0}
          onChange={mockOnChange}
          onDelete={mockOnDelete}
        />
      )

      const offsetInput = screen.getByTestId('action-offset') as HTMLInputElement
      expect(offsetInput.value).toBe('15')
    })

    it('renders with correct data-testid based on index', () => {
      render(
        <InlineActionRow
          action={defaultAction}
          index={3}
          onChange={mockOnChange}
          onDelete={mockOnDelete}
        />
      )

      expect(screen.getByTestId('action-row-3')).toBeInTheDocument()
    })

    it('renders delete button with aria-label', () => {
      render(
        <InlineActionRow
          action={defaultAction}
          index={0}
          onChange={mockOnChange}
          onDelete={mockOnDelete}
        />
      )

      expect(screen.getByLabelText('Delete action')).toBeInTheDocument()
    })
  })

  describe('Action Type Change', () => {
    it('calls onChange with new type and resets action_name', async () => {
      const user = userEvent.setup()
      render(
        <InlineActionRow
          action={defaultAction}
          index={0}
          onChange={mockOnChange}
          onDelete={mockOnDelete}
        />
      )

      await user.selectOptions(screen.getByTestId('action-type'), 'camera')

      expect(mockOnChange).toHaveBeenCalledWith({
        ...defaultAction,
        action_type: 'camera',
        action_name: '',
      })
    })

    it('populates action name options based on selected type', () => {
      const action: RoutineAction = {
        id: 'action-1',
        action_type: 'service',
        action_name: '',
        offset_minutes: 0,
      }

      render(
        <InlineActionRow
          action={action}
          index={0}
          onChange={mockOnChange}
          onDelete={mockOnDelete}
        />
      )

      const nameSelect = screen.getByTestId('action-name')
      const options = nameSelect.querySelectorAll('option')
      // "Select action" + "backup" + "update_display"
      expect(options).toHaveLength(3)
      expect(options[1].value).toBe('backup')
      expect(options[2].value).toBe('update_display')
    })
  })

  describe('Action Name Change', () => {
    it('calls onChange with new action name', async () => {
      const user = userEvent.setup()
      render(
        <InlineActionRow
          action={defaultAction}
          index={0}
          onChange={mockOnChange}
          onDelete={mockOnDelete}
        />
      )

      await user.selectOptions(screen.getByTestId('action-name'), 'flash_on')

      expect(mockOnChange).toHaveBeenCalledWith({
        ...defaultAction,
        action_name: 'flash_on',
      })
    })

    it('disables name select when no type selected', () => {
      const action: RoutineAction = {
        id: 'action-1',
        action_type: '',
        action_name: '',
        offset_minutes: 0,
      }

      render(
        <InlineActionRow
          action={action}
          index={0}
          onChange={mockOnChange}
          onDelete={mockOnDelete}
        />
      )

      expect(screen.getByTestId('action-name')).toBeDisabled()
    })
  })

  describe('Offset Change', () => {
    it('calls onChange with new offset value', async () => {
      const user = userEvent.setup()
      render(
        <InlineActionRow
          action={defaultAction}
          index={0}
          onChange={mockOnChange}
          onDelete={mockOnDelete}
        />
      )

      const offsetInput = screen.getByTestId('action-offset')
      await user.clear(offsetInput)
      await user.type(offsetInput, '5')

      // Since this is a controlled component with mocked onChange,
      // verify onChange was called with a numeric offset_minutes
      expect(mockOnChange).toHaveBeenCalled()
      const lastCall = mockOnChange.mock.calls[mockOnChange.mock.calls.length - 1][0]
      expect(typeof lastCall.offset_minutes).toBe('number')
      expect(lastCall.offset_minutes).toBeGreaterThanOrEqual(0)
    })

    it('clamps offset to max value', async () => {
      const user = userEvent.setup()
      render(
        <InlineActionRow
          action={defaultAction}
          index={0}
          onChange={mockOnChange}
          onDelete={mockOnDelete}
        />
      )

      const offsetInput = screen.getByTestId('action-offset')
      await user.clear(offsetInput)
      await user.type(offsetInput, '9999')

      // Should be clamped to 1440
      const lastCall = mockOnChange.mock.calls[mockOnChange.mock.calls.length - 1][0]
      expect(lastCall.offset_minutes).toBeLessThanOrEqual(1440)
    })
  })

  describe('Delete', () => {
    it('calls onDelete with index when delete button clicked', async () => {
      const user = userEvent.setup()
      render(
        <InlineActionRow
          action={defaultAction}
          index={2}
          onChange={mockOnChange}
          onDelete={mockOnDelete}
        />
      )

      await user.click(screen.getByLabelText('Delete action'))

      expect(mockOnDelete).toHaveBeenCalledWith(2)
    })
  })

  describe('Disabled State', () => {
    it('disables all inputs when disabled', () => {
      render(
        <InlineActionRow
          action={defaultAction}
          index={0}
          onChange={mockOnChange}
          onDelete={mockOnDelete}
          disabled={true}
        />
      )

      expect(screen.getByTestId('action-type')).toBeDisabled()
      expect(screen.getByTestId('action-name')).toBeDisabled()
      expect(screen.getByTestId('action-offset')).toBeDisabled()
      expect(screen.getByLabelText('Delete action')).toBeDisabled()
    })

    it('enables all inputs when not disabled', () => {
      render(
        <InlineActionRow
          action={defaultAction}
          index={0}
          onChange={mockOnChange}
          onDelete={mockOnDelete}
          disabled={false}
        />
      )

      expect(screen.getByTestId('action-type')).not.toBeDisabled()
      expect(screen.getByTestId('action-name')).not.toBeDisabled()
      expect(screen.getByTestId('action-offset')).not.toBeDisabled()
      expect(screen.getByLabelText('Delete action')).not.toBeDisabled()
    })
  })

  describe('Edge Cases', () => {
    it('handles action with missing fields gracefully', () => {
      const action = { id: 'action-1' } as RoutineAction

      render(
        <InlineActionRow
          action={action}
          index={0}
          onChange={mockOnChange}
          onDelete={mockOnDelete}
        />
      )

      const typeSelect = screen.getByTestId('action-type') as HTMLSelectElement
      expect(typeSelect.value).toBe('')

      const nameSelect = screen.getByTestId('action-name') as HTMLSelectElement
      expect(nameSelect.value).toBe('')
    })

    it('handles offset_minutes of 0 correctly', () => {
      const action: RoutineAction = { ...defaultAction, offset_minutes: 0 }

      render(
        <InlineActionRow
          action={action}
          index={0}
          onChange={mockOnChange}
          onDelete={mockOnDelete}
        />
      )

      const offsetInput = screen.getByTestId('action-offset') as HTMLInputElement
      expect(offsetInput.value).toBe('0')
    })
  })
})
