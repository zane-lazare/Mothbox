import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import PatternEditor from '../PatternEditor'

// Mock the hooks
vi.mock('@/hooks/useEventPatterns', () => ({
  useValidatePattern: () => ({
    mutateAsync: vi.fn().mockResolvedValue({ valid: true }),
    isPending: false,
    error: null
  }),
  usePatternDuration: () => ({
    data: 30,
    isLoading: false
  })
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

describe('PatternEditor', () => {
  const mockOnSave = vi.fn()
  const mockOnCancel = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Create Mode', () => {
    it('renders with empty form when pattern prop is undefined', () => {
      render(
        <PatternEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
        { wrapper: createWrapper() }
      )

      expect(screen.getByText('Create Pattern')).toBeInTheDocument()
      expect(screen.getByLabelText(/pattern name/i)).toHaveValue('')
      expect(screen.getByLabelText(/description/i)).toHaveValue('')
      expect(screen.getByTestId('action-count')).toHaveTextContent('0')
    })

    it('shows save and cancel buttons', () => {
      render(
        <PatternEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
        { wrapper: createWrapper() }
      )

      expect(screen.getByRole('button', { name: /save pattern/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
    })
  })

  describe('Edit Mode', () => {
    const existingPattern = {
      pattern_id: 'pattern-123',
      name: 'Night Photography',
      description: 'Automated night photography sequence',
      actions: [
        { action_id: 'action-1', action_type: 'capture_photo', offset_minutes: 0 },
        { action_id: 'action-2', action_type: 'capture_photo', offset_minutes: 5 }
      ],
      tags: ['night', 'auto'],
      category: 'photography'
    }

    it('renders with form populated from pattern prop', () => {
      render(
        <PatternEditor
          pattern={existingPattern}
          onSave={mockOnSave}
          onCancel={mockOnCancel}
        />,
        { wrapper: createWrapper() }
      )

      expect(screen.getByText('Edit Pattern')).toBeInTheDocument()
      expect(screen.getByLabelText(/pattern name/i)).toHaveValue('Night Photography')
      expect(screen.getByLabelText(/description/i)).toHaveValue('Automated night photography sequence')
      expect(screen.getByTestId('action-count')).toHaveTextContent('2')
    })

    it('displays existing tags as chips', () => {
      render(
        <PatternEditor
          pattern={existingPattern}
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
        <PatternEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
        { wrapper: createWrapper() }
      )

      const nameInput = screen.getByLabelText(/pattern name/i)
      await user.type(nameInput, 'My Pattern')

      expect(nameInput).toHaveValue('My Pattern')
    })

    it('updates description field on user input', async () => {
      const user = userEvent.setup()
      render(
        <PatternEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
        { wrapper: createWrapper() }
      )

      const descInput = screen.getByLabelText(/description/i)
      await user.type(descInput, 'Test description')

      expect(descInput).toHaveValue('Test description')
    })

    it('enforces max 200 chars on name field', async () => {
      const user = userEvent.setup()
      render(
        <PatternEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
        { wrapper: createWrapper() }
      )

      const nameInput = screen.getByLabelText(/pattern name/i)
      const longName = 'a'.repeat(250)

      await user.type(nameInput, longName)

      expect(nameInput.value.length).toBeLessThanOrEqual(200)
    })

    it('enforces max 2000 chars on description field', async () => {
      const user = userEvent.setup()
      render(
        <PatternEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
        { wrapper: createWrapper() }
      )

      const descInput = screen.getByLabelText(/description/i)
      const longDesc = 'a'.repeat(2500)

      await user.type(descInput, longDesc)

      expect(descInput.value.length).toBeLessThanOrEqual(2000)
    })
  })

  describe('Name Validation', () => {
    it('shows error when name is empty on save', async () => {
      const user = userEvent.setup()
      render(
        <PatternEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
        { wrapper: createWrapper() }
      )

      const saveButton = screen.getByRole('button', { name: /save pattern/i })
      await user.click(saveButton)

      expect(screen.getByText(/pattern name is required/i)).toBeInTheDocument()
      expect(mockOnSave).not.toHaveBeenCalled()
    })

    it('clears error when name is entered', async () => {
      const user = userEvent.setup()
      render(
        <PatternEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
        { wrapper: createWrapper() }
      )

      // Trigger error
      const saveButton = screen.getByRole('button', { name: /save pattern/i })
      await user.click(saveButton)
      expect(screen.getByText(/pattern name is required/i)).toBeInTheDocument()

      // Enter name
      const nameInput = screen.getByLabelText(/pattern name/i)
      await user.type(nameInput, 'Valid Name')

      expect(screen.queryByText(/pattern name is required/i)).not.toBeInTheDocument()
    })
  })

  describe('Tags Management', () => {
    it('adds new tag when user types and presses Enter', async () => {
      const user = userEvent.setup()
      render(
        <PatternEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
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
        <PatternEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
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
      const pattern = {
        name: 'Test',
        actions: [],
        tags: ['removeme']
      }

      render(
        <PatternEditor
          pattern={pattern}
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
        <PatternEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
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
        <PatternEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
        { wrapper: createWrapper() }
      )

      expect(screen.getByTestId('action-count')).toHaveTextContent('0')

      const addButton = screen.getByText('Add Mock Action')
      await user.click(addButton)

      expect(screen.getByTestId('action-count')).toHaveTextContent('1')
    })

    it('passes actions to ActionList component', () => {
      const pattern = {
        name: 'Test',
        actions: [
          { action_id: 'a1', action_type: 'capture_photo', offset_minutes: 0 }
        ]
      }

      render(
        <PatternEditor
          pattern={pattern}
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
      const pattern = {
        name: 'Test',
        actions: [
          { action_id: 'a1', action_type: 'capture_photo', offset_minutes: 0 },
          { action_id: 'a2', action_type: 'capture_photo', offset_minutes: 5 }
        ]
      }

      render(
        <PatternEditor
          pattern={pattern}
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
        <PatternEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
        { wrapper: createWrapper() }
      )

      expect(screen.getByTestId('offset-timeline')).toHaveTextContent('Timeline with 0 actions')

      const addButton = screen.getByText('Add Mock Action')
      await user.click(addButton)

      expect(screen.getByTestId('offset-timeline')).toHaveTextContent('Timeline with 1 actions')
    })
  })

  describe('Duration Display', () => {
    it('displays duration from usePatternDuration hook', () => {
      render(
        <PatternEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
        { wrapper: createWrapper() }
      )

      expect(screen.getByText(/duration: 30 minutes/i)).toBeInTheDocument()
    })
  })

  describe('Save Functionality', () => {
    it('calls useValidatePattern before saving', async () => {
      const mockMutateAsync = vi.fn().mockResolvedValue({ valid: true })
      vi.mocked(await import('@/hooks/useEventPatterns')).useValidatePattern = () => ({
        mutateAsync: mockMutateAsync,
        isPending: false,
        error: null
      })

      const user = userEvent.setup()
      render(
        <PatternEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
        { wrapper: createWrapper() }
      )

      const nameInput = screen.getByLabelText(/pattern name/i)
      await user.type(nameInput, 'Test Pattern')

      const saveButton = screen.getByRole('button', { name: /save pattern/i })
      await user.click(saveButton)

      await waitFor(() => {
        expect(mockMutateAsync).toHaveBeenCalled()
      })
    })

    it('calls onSave with pattern data on successful validation', async () => {
      const mockMutateAsync = vi.fn().mockResolvedValue({ valid: true })
      vi.mocked(await import('@/hooks/useEventPatterns')).useValidatePattern = () => ({
        mutateAsync: mockMutateAsync,
        isPending: false,
        error: null
      })

      const user = userEvent.setup()
      render(
        <PatternEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
        { wrapper: createWrapper() }
      )

      const nameInput = screen.getByLabelText(/pattern name/i)
      await user.type(nameInput, 'Test Pattern')

      const descInput = screen.getByLabelText(/description/i)
      await user.type(descInput, 'Test description')

      const saveButton = screen.getByRole('button', { name: /save pattern/i })
      await user.click(saveButton)

      await waitFor(() => {
        expect(mockOnSave).toHaveBeenCalledWith(
          expect.objectContaining({
            name: 'Test Pattern',
            description: 'Test description',
            actions: [],
            tags: []
          })
        )
      })
    })

    it('generates pattern_id for new patterns', async () => {
      const mockMutateAsync = vi.fn().mockResolvedValue({ valid: true })
      vi.mocked(await import('@/hooks/useEventPatterns')).useValidatePattern = () => ({
        mutateAsync: mockMutateAsync,
        isPending: false,
        error: null
      })

      // Mock crypto.randomUUID
      const mockUUID = 'test-uuid-123'
      const randomUUIDSpy = vi.spyOn(crypto, 'randomUUID').mockReturnValue(mockUUID)

      const user = userEvent.setup()
      render(
        <PatternEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
        { wrapper: createWrapper() }
      )

      const nameInput = screen.getByLabelText(/pattern name/i)
      await user.type(nameInput, 'Test Pattern')

      const saveButton = screen.getByRole('button', { name: /save pattern/i })
      await user.click(saveButton)

      await waitFor(() => {
        expect(mockOnSave).toHaveBeenCalledWith(
          expect.objectContaining({
            pattern_id: mockUUID
          })
        )
      })

      randomUUIDSpy.mockRestore()
    })

    it('preserves pattern_id for existing patterns', async () => {
      const mockMutateAsync = vi.fn().mockResolvedValue({ valid: true })
      vi.mocked(await import('@/hooks/useEventPatterns')).useValidatePattern = () => ({
        mutateAsync: mockMutateAsync,
        isPending: false,
        error: null
      })

      const existingPattern = {
        pattern_id: 'existing-123',
        name: 'Existing',
        actions: []
      }

      const user = userEvent.setup()
      render(
        <PatternEditor
          pattern={existingPattern}
          onSave={mockOnSave}
          onCancel={mockOnCancel}
        />,
        { wrapper: createWrapper() }
      )

      const saveButton = screen.getByRole('button', { name: /save pattern/i })
      await user.click(saveButton)

      await waitFor(() => {
        expect(mockOnSave).toHaveBeenCalledWith(
          expect.objectContaining({
            pattern_id: 'existing-123'
          })
        )
      })
    })

    it('shows validation error message on save failure', async () => {
      const mockMutateAsync = vi.fn().mockResolvedValue({
        valid: false,
        errors: ['Invalid action offset']
      })
      vi.mocked(await import('@/hooks/useEventPatterns')).useValidatePattern = () => ({
        mutateAsync: mockMutateAsync,
        isPending: false,
        error: null
      })

      const user = userEvent.setup()
      render(
        <PatternEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
        { wrapper: createWrapper() }
      )

      const nameInput = screen.getByLabelText(/pattern name/i)
      await user.type(nameInput, 'Test Pattern')

      const saveButton = screen.getByRole('button', { name: /save pattern/i })
      await user.click(saveButton)

      await waitFor(() => {
        expect(screen.getByText(/invalid action offset/i)).toBeInTheDocument()
        expect(mockOnSave).not.toHaveBeenCalled()
      })
    })

    it('disables save button while validation is pending', async () => {
      const mockMutateAsync = vi.fn(() => new Promise(() => {})) // Never resolves
      vi.mocked(await import('@/hooks/useEventPatterns')).useValidatePattern = () => ({
        mutateAsync: mockMutateAsync,
        isPending: true,
        error: null
      })

      render(
        <PatternEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
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
        <PatternEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
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
        <PatternEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
        { wrapper: createWrapper() }
      )

      // Check for dark mode classes on inputs
      const nameInput = screen.getByLabelText(/pattern name/i)
      expect(nameInput.className).toContain('dark:bg-gray-800')
      expect(nameInput.className).toContain('dark:text-white')
    })

    it('applies dark mode classes to buttons', () => {
      render(
        <PatternEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
        { wrapper: createWrapper() }
      )

      const cancelButton = screen.getByRole('button', { name: /cancel/i })
      expect(cancelButton.className).toContain('dark:border-gray-600')
      expect(cancelButton.className).toContain('dark:text-gray-300')
    })

    it('applies dark mode classes to labels', () => {
      const { container } = render(
        <PatternEditor onSave={mockOnSave} onCancel={mockOnCancel} />,
        { wrapper: createWrapper() }
      )

      const labels = container.querySelectorAll('label')
      labels.forEach(label => {
        expect(label.className).toContain('dark:text-gray-300')
      })
    })
  })
})
