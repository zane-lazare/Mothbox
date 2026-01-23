import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import RoutineEditor from '../RoutineEditor'
import { ROUTINE_LIMITS } from '../constants'

// Create hoisted mocks that can be controlled per-test
const mockMutateAsync = vi.hoisted(() => vi.fn())
const mockIsPending = vi.hoisted(() => ({ value: false }))

// Mock the hooks using the hoisted mocks
vi.mock('@/hooks/useRoutines', () => ({
  useValidateRoutine: () => ({
    mutateAsync: mockMutateAsync,
    isPending: mockIsPending.value,
    error: null
  }),
  useRoutineDuration: () => 30
}))

// Mock sub-components
vi.mock('../ActionList', () => ({
  default: ({ actions, onActionsChange }) => (
    <div data-testid="action-list">
      <button
        onClick={() => onActionsChange([
          ...actions,
          { action_id: 'action-1', action_type: 'capture_photo', offset_minutes: 0 }
        ])}
      >
        Add Mock Action
      </button>
      <div data-testid="action-count">{actions.length}</div>
    </div>
  )
}))

vi.mock('../OffsetTimeline', () => ({
  default: ({ actions }) => (
    <div data-testid="offset-timeline">
      Timeline with {actions.length} actions
    </div>
  )
}))

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false }
    }
  })
  return ({ children }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}

describe('RoutineEditor', () => {
  const mockOnSave = vi.fn()
  const mockOnCancel = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    // Default to successful validation
    mockMutateAsync.mockResolvedValue({ valid: true })
    mockIsPending.value = false
  })

  describe('Create Mode', () => {
    it('renders with empty form when routine prop is undefined', () => {
      render(
        <RoutineEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
        { wrapper: createWrapper() }
      )

      expect(screen.getByText('Create Routine')).toBeInTheDocument()
      expect(screen.getByLabelText(/routine name/i)).toHaveValue('')
      expect(screen.getByLabelText(/description/i)).toHaveValue('')
      expect(screen.getByTestId('action-count')).toHaveTextContent('0')
    })

    it('shows save and cancel buttons', () => {
      render(
        <RoutineEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
        { wrapper: createWrapper() }
      )

      expect(screen.getByRole('button', { name: /save routine/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
    })
  })

  describe('Edit Mode', () => {
    const existingRoutine = {
      routine_id: 'routine-123',
      name: 'Night Photography',
      description: 'Automated night photography sequence',
      actions: [
        { action_id: 'action-1', action_type: 'capture_photo', offset_minutes: 0 },
        { action_id: 'action-2', action_type: 'capture_photo', offset_minutes: 5 }
      ],
      tags: ['night', 'auto'],
      category: 'photography'
    }

    it('renders with form populated from routine prop', () => {
      render(
        <RoutineEditor
          routine={existingRoutine}
          onSave={mockOnSave}
          onCancel={mockOnCancel}
        />,
        { wrapper: createWrapper() }
      )

      expect(screen.getByText('Edit Routine')).toBeInTheDocument()
      expect(screen.getByLabelText(/routine name/i)).toHaveValue('Night Photography')
      expect(screen.getByLabelText(/description/i)).toHaveValue('Automated night photography sequence')
      expect(screen.getByTestId('action-count')).toHaveTextContent('2')
    })

    it('displays existing tags as chips', () => {
      render(
        <RoutineEditor
          routine={existingRoutine}
          onSave={mockOnSave}
          onCancel={mockOnCancel}
        />,
        { wrapper: createWrapper() }
      )

      expect(screen.getByText('night')).toBeInTheDocument()
      expect(screen.getByText('auto')).toBeInTheDocument()
    })
  })

  describe('Form Inputs', () => {
    it('updates name field on user input', async () => {
      const user = userEvent.setup()
      render(
        <RoutineEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
        { wrapper: createWrapper() }
      )

      const nameInput = screen.getByLabelText(/routine name/i)
      await user.type(nameInput, 'My Routine')

      expect(nameInput).toHaveValue('My Routine')
    })

    it('updates description field on user input', async () => {
      const user = userEvent.setup()
      render(
        <RoutineEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
        { wrapper: createWrapper() }
      )

      const descInput = screen.getByLabelText(/description/i)
      await user.type(descInput, 'Test description')

      expect(descInput).toHaveValue('Test description')
    })

    it('enforces max chars on name field', async () => {
      const user = userEvent.setup()
      render(
        <RoutineEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
        { wrapper: createWrapper() }
      )

      const nameInput = screen.getByLabelText(/routine name/i)
      const longName = 'a'.repeat(ROUTINE_LIMITS.NAME_MAX_LENGTH + 50)

      await user.type(nameInput, longName)

      expect(nameInput.value.length).toBeLessThanOrEqual(ROUTINE_LIMITS.NAME_MAX_LENGTH)
    })

    it('enforces max chars on description field', async () => {
      const user = userEvent.setup()
      render(
        <RoutineEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
        { wrapper: createWrapper() }
      )

      const descInput = screen.getByLabelText(/description/i)
      const longDesc = 'a'.repeat(ROUTINE_LIMITS.DESCRIPTION_MAX_LENGTH + 500)

      await user.type(descInput, longDesc)

      expect(descInput.value.length).toBeLessThanOrEqual(ROUTINE_LIMITS.DESCRIPTION_MAX_LENGTH)
    })
  })

  describe('Name Validation', () => {
    it('shows error when name is empty on save', async () => {
      const user = userEvent.setup()
      render(
        <RoutineEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
        { wrapper: createWrapper() }
      )

      const saveButton = screen.getByRole('button', { name: /save routine/i })
      await user.click(saveButton)

      expect(screen.getByText(/routine name is required/i)).toBeInTheDocument()
      expect(mockOnSave).not.toHaveBeenCalled()
    })

    it('clears error when name is entered', async () => {
      const user = userEvent.setup()
      render(
        <RoutineEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
        { wrapper: createWrapper() }
      )

      // Trigger error
      const saveButton = screen.getByRole('button', { name: /save routine/i })
      await user.click(saveButton)
      expect(screen.getByText(/routine name is required/i)).toBeInTheDocument()

      // Enter name
      const nameInput = screen.getByLabelText(/routine name/i)
      await user.type(nameInput, 'Valid Name')

      expect(screen.queryByText(/routine name is required/i)).not.toBeInTheDocument()
    })
  })

  describe('Tags Management', () => {
    it('adds new tag when user types and presses Enter', async () => {
      const user = userEvent.setup()
      render(
        <RoutineEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
        { wrapper: createWrapper() }
      )

      const tagInput = screen.getByPlaceholderText(/add tag/i)
      await user.type(tagInput, 'newtag{Enter}')

      expect(screen.getByText('newtag')).toBeInTheDocument()
      expect(tagInput).toHaveValue('') // Input should be cleared
    })

    it('prevents duplicate tags', async () => {
      const user = userEvent.setup()
      render(
        <RoutineEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
        { wrapper: createWrapper() }
      )

      const tagInput = screen.getByPlaceholderText(/add tag/i)
      await user.type(tagInput, 'tag1{Enter}')
      await user.type(tagInput, 'tag1{Enter}')

      const tags = screen.getAllByText('tag1')
      expect(tags).toHaveLength(1) // Only one chip
    })

    it('removes tag when remove button clicked', async () => {
      const user = userEvent.setup()
      const routine = {
        name: 'Test',
        actions: [],
        tags: ['removeme']
      }

      render(
        <RoutineEditor
          routine={routine}
          onSave={mockOnSave}
          onCancel={mockOnCancel}
        />,
        { wrapper: createWrapper() }
      )

      expect(screen.getByText('removeme')).toBeInTheDocument()

      const removeButton = screen.getByLabelText(/remove tag removeme/i)
      await user.click(removeButton)

      expect(screen.queryByText('removeme')).not.toBeInTheDocument()
    })

    it('trims whitespace from tags', async () => {
      const user = userEvent.setup()
      render(
        <RoutineEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
        { wrapper: createWrapper() }
      )

      const tagInput = screen.getByPlaceholderText(/add tag/i)
      await user.type(tagInput, '  spaced  {Enter}')

      expect(screen.getByText('spaced')).toBeInTheDocument()
    })
  })

  describe('ActionList Integration', () => {
    it('updates actions when ActionList changes', async () => {
      const user = userEvent.setup()
      render(
        <RoutineEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
        { wrapper: createWrapper() }
      )

      expect(screen.getByTestId('action-count')).toHaveTextContent('0')

      const addButton = screen.getByText('Add Mock Action')
      await user.click(addButton)

      expect(screen.getByTestId('action-count')).toHaveTextContent('1')
    })

    it('passes actions to ActionList component', () => {
      const routine = {
        name: 'Test',
        actions: [
          { action_id: 'a1', action_type: 'capture_photo', offset_minutes: 0 }
        ]
      }

      render(
        <RoutineEditor
          routine={routine}
          onSave={mockOnSave}
          onCancel={mockOnCancel}
        />,
        { wrapper: createWrapper() }
      )

      expect(screen.getByTestId('action-count')).toHaveTextContent('1')
    })
  })

  describe('OffsetTimeline Integration', () => {
    it('passes current actions to OffsetTimeline', () => {
      const routine = {
        name: 'Test',
        actions: [
          { action_id: 'a1', action_type: 'capture_photo', offset_minutes: 0 },
          { action_id: 'a2', action_type: 'capture_photo', offset_minutes: 5 }
        ]
      }

      render(
        <RoutineEditor
          routine={routine}
          onSave={mockOnSave}
          onCancel={mockOnCancel}
        />,
        { wrapper: createWrapper() }
      )

      expect(screen.getByTestId('offset-timeline')).toHaveTextContent('Timeline with 2 actions')
    })

    it('updates timeline when actions change', async () => {
      const user = userEvent.setup()
      render(
        <RoutineEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
        { wrapper: createWrapper() }
      )

      expect(screen.getByTestId('offset-timeline')).toHaveTextContent('Timeline with 0 actions')

      const addButton = screen.getByText('Add Mock Action')
      await user.click(addButton)

      expect(screen.getByTestId('offset-timeline')).toHaveTextContent('Timeline with 1 actions')
    })
  })

  describe('Duration Display', () => {
    it('displays duration from useRoutineDuration hook', () => {
      render(
        <RoutineEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
        { wrapper: createWrapper() }
      )

      expect(screen.getByText(/duration: 30 minutes/i)).toBeInTheDocument()
    })
  })

  describe('Save Functionality', () => {
    it('calls useValidateRoutine before saving', async () => {
      const user = userEvent.setup()
      render(
        <RoutineEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
        { wrapper: createWrapper() }
      )

      const nameInput = screen.getByLabelText(/routine name/i)
      await user.type(nameInput, 'Test Routine')

      const saveButton = screen.getByRole('button', { name: /save routine/i })
      await user.click(saveButton)

      await waitFor(() => {
        expect(mockMutateAsync).toHaveBeenCalled()
      })
    })

    it('calls onSave with routine data on successful validation', async () => {
      const user = userEvent.setup()
      render(
        <RoutineEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
        { wrapper: createWrapper() }
      )

      const nameInput = screen.getByLabelText(/routine name/i)
      await user.type(nameInput, 'Test Routine')

      const descInput = screen.getByLabelText(/description/i)
      await user.type(descInput, 'Test description')

      const saveButton = screen.getByRole('button', { name: /save routine/i })
      await user.click(saveButton)

      await waitFor(() => {
        expect(mockOnSave).toHaveBeenCalledWith(
          expect.objectContaining({
            name: 'Test Routine',
            description: 'Test description',
            actions: [],
            tags: []
          })
        )
      })
    })

    it('generates routine_id for new routines', async () => {
      // Mock crypto.randomUUID
      const mockUUID = 'test-uuid-123'
      const randomUUIDSpy = vi.spyOn(crypto, 'randomUUID').mockReturnValue(mockUUID)

      const user = userEvent.setup()
      render(
        <RoutineEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
        { wrapper: createWrapper() }
      )

      const nameInput = screen.getByLabelText(/routine name/i)
      await user.type(nameInput, 'Test Routine')

      const saveButton = screen.getByRole('button', { name: /save routine/i })
      await user.click(saveButton)

      await waitFor(() => {
        expect(mockOnSave).toHaveBeenCalledWith(
          expect.objectContaining({
            routine_id: mockUUID
          })
        )
      })

      randomUUIDSpy.mockRestore()
    })

    it('preserves routine_id for existing routines', async () => {
      const existingRoutine = {
        routine_id: 'existing-123',
        name: 'Existing',
        actions: []
      }

      const user = userEvent.setup()
      render(
        <RoutineEditor
          routine={existingRoutine}
          onSave={mockOnSave}
          onCancel={mockOnCancel}
        />,
        { wrapper: createWrapper() }
      )

      const saveButton = screen.getByRole('button', { name: /save routine/i })
      await user.click(saveButton)

      await waitFor(() => {
        expect(mockOnSave).toHaveBeenCalledWith(
          expect.objectContaining({
            routine_id: 'existing-123'
          })
        )
      })
    })

    it('shows validation error message on save failure', async () => {
      // Configure mock to return validation failure
      mockMutateAsync.mockResolvedValue({
        valid: false,
        errors: ['Invalid action offset']
      })

      const user = userEvent.setup()
      render(
        <RoutineEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
        { wrapper: createWrapper() }
      )

      const nameInput = screen.getByLabelText(/routine name/i)
      await user.type(nameInput, 'Test Routine')

      const saveButton = screen.getByRole('button', { name: /save routine/i })
      await user.click(saveButton)

      await waitFor(() => {
        expect(screen.getByText(/invalid action offset/i)).toBeInTheDocument()
        expect(mockOnSave).not.toHaveBeenCalled()
      })
    })

    it('disables save button while validation is pending', async () => {
      // Configure isPending to be true for this test
      mockIsPending.value = true
      mockMutateAsync.mockImplementation(() => new Promise(() => {})) // Never resolves

      render(
        <RoutineEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
        { wrapper: createWrapper() }
      )

      const saveButton = screen.getByRole('button', { name: /saving/i })
      expect(saveButton).toBeDisabled()
    })
  })

  describe('Cancel Functionality', () => {
    it('calls onCancel when cancel button clicked', async () => {
      const user = userEvent.setup()
      render(
        <RoutineEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
        { wrapper: createWrapper() }
      )

      const cancelButton = screen.getByRole('button', { name: /cancel/i })
      await user.click(cancelButton)

      expect(mockOnCancel).toHaveBeenCalled()
    })
  })

  describe('Dark Mode Styling', () => {
    it('applies dark mode classes to container', () => {
      render(
        <RoutineEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
        { wrapper: createWrapper() }
      )

      // Check for dark mode classes on inputs
      const nameInput = screen.getByLabelText(/routine name/i)
      expect(nameInput.className).toContain('dark:bg-gray-800')
      expect(nameInput.className).toContain('dark:text-white')
    })

    it('applies dark mode classes to buttons', () => {
      render(
        <RoutineEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
        { wrapper: createWrapper() }
      )

      const cancelButton = screen.getByRole('button', { name: /cancel/i })
      expect(cancelButton.className).toContain('dark:border-gray-600')
      expect(cancelButton.className).toContain('dark:text-gray-300')
    })

    it('applies dark mode classes to labels', () => {
      const { container } = render(
        <RoutineEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
        { wrapper: createWrapper() }
      )

      const labels = container.querySelectorAll('label')
      labels.forEach(label => {
        expect(label.className).toContain('dark:text-gray-300')
      })
    })
  })
})
