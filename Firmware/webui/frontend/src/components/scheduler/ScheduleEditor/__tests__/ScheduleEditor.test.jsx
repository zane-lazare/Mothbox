import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ScheduleEditor from '../ScheduleEditor';

// Mock child components
vi.mock('../RoutineList', () => ({
  default: ({
    routines,
    onRoutineDelete,
    onRoutineAdd,
    disabled,
  }) => (
    <div data-testid="routine-list">
      <span data-testid="routines-count">{routines?.length ?? 0}</span>
      <button
        data-testid="add-routine"
        onClick={() => {
          onRoutineAdd({
            routine_id: 'routine-1',
            name: 'Test Routine',
            trigger: { trigger_type: 'interval', interval_minutes: 15 },
            actions: [{ action_type: 'camera', action_name: 'takephoto' }],
          });
        }}
        disabled={disabled}
      >
        Add Routine
      </button>
      <button
        data-testid="delete-routine"
        onClick={() => onRoutineDelete('routine-1')}
        disabled={disabled}
      >
        Delete Routine
      </button>
    </div>
  ),
}));

// Helper to render with QueryClient
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

const renderWithClient = (ui) => {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
};

describe('ScheduleEditor', () => {
  let mockOnSave;
  let mockOnCancel;

  beforeEach(() => {
    mockOnSave = vi.fn();
    mockOnCancel = vi.fn();
  });

  describe('Rendering', () => {
    it('renders RoutineList component', () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      expect(screen.getByTestId('routine-list')).toBeInTheDocument();
    });

    it('renders schedule name input', () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      expect(screen.getByLabelText(/schedule name/i)).toBeInTheDocument();
    });

    it('renders description textarea', () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      expect(screen.getByLabelText(/description/i)).toBeInTheDocument();
    });

    it('renders save and cancel buttons', () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      expect(screen.getByRole('button', { name: /save/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
    });

    it('renders header with title', () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      expect(screen.getByText(/create schedule/i)).toBeInTheDocument();
    });

    it('shows "Edit Schedule" title when editing existing schedule', () => {
      const schedule = {
        schedule_id: 'sched-1',
        name: 'Existing Schedule',
        description: 'Test description',
        routines: [],
      };

      renderWithClient(
        <ScheduleEditor
          isOpen={true}
          schedule={schedule}
          onSave={mockOnSave}
          onCancel={mockOnCancel}
        />
      );

      expect(screen.getByText(/edit schedule/i)).toBeInTheDocument();
    });
  });

  describe('Form State', () => {
    it('initializes with default values for new schedule', () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      const nameInput = screen.getByLabelText(/schedule name/i);
      expect(nameInput).toHaveValue('');
      expect(screen.getByTestId('routines-count')).toHaveTextContent('0');
    });

    it('shows loading state in edit mode while fetching schedule data', () => {
      const schedule = {
        schedule_id: 'sched-1',
        name: 'My Schedule',
        description: 'A test schedule',
        routines: [],
      };

      renderWithClient(
        <ScheduleEditor
          isOpen={true}
          schedule={schedule}
          onSave={mockOnSave}
          onCancel={mockOnCancel}
        />
      );

      // In edit mode, component fetches fresh data from API
      // Without API mock, it should show loading state
      expect(screen.getByText(/loading schedule/i)).toBeInTheDocument();
    });

    it('updates name when typed', () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      const nameInput = screen.getByLabelText(/schedule name/i);
      fireEvent.change(nameInput, { target: { value: 'New Schedule Name' } });

      expect(nameInput).toHaveValue('New Schedule Name');
    });

    it('updates description when typed', () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      const descInput = screen.getByLabelText(/description/i);
      fireEvent.change(descInput, { target: { value: 'New description' } });

      expect(descInput).toHaveValue('New description');
    });
  });

  describe('Routine Management', () => {
    it('adds routine when RoutineList onRoutineAdd is called', () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      expect(screen.getByTestId('routines-count')).toHaveTextContent('0');

      const addButton = screen.getByTestId('add-routine');
      fireEvent.click(addButton);

      expect(screen.getByTestId('routines-count')).toHaveTextContent('1');
    });
  });

  describe('Validation', () => {
    it('shows error when saving without name', async () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      // Add a routine first
      const addButton = screen.getByTestId('add-routine');
      fireEvent.click(addButton);

      const saveButton = screen.getByRole('button', { name: /save/i });
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(screen.getByText(/schedule name is required/i)).toBeInTheDocument();
      });
      expect(mockOnSave).not.toHaveBeenCalled();
    });

    it('shows error when saving without routines', async () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      // Fill in name but no routines
      const nameInput = screen.getByLabelText(/schedule name/i);
      fireEvent.change(nameInput, { target: { value: 'Test Schedule' } });

      const saveButton = screen.getByRole('button', { name: /save/i });
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(screen.getByText(/at least one routine is required/i)).toBeInTheDocument();
      });
      expect(mockOnSave).not.toHaveBeenCalled();
    });
  });

  describe('Save and Cancel', () => {
    it('calls onSave with schedule data when valid', async () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      // Fill in required fields
      const nameInput = screen.getByLabelText(/schedule name/i);
      fireEvent.change(nameInput, { target: { value: 'Test Schedule' } });

      // Add a routine
      const addButton = screen.getByTestId('add-routine');
      fireEvent.click(addButton);

      // Save
      const saveButton = screen.getByRole('button', { name: /save/i });
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(mockOnSave).toHaveBeenCalledWith(
          expect.objectContaining({
            name: 'Test Schedule',
            routines: expect.arrayContaining([
              expect.objectContaining({
                routine_id: 'routine-1',
              }),
            ]),
          })
        );
      });
    });

    it('calls onCancel when cancel button clicked', () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      fireEvent.click(cancelButton);

      expect(mockOnCancel).toHaveBeenCalled();
    });

    it('calls onCancel when backdrop clicked', () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      const backdrop = screen.getByTestId('drawer-backdrop');
      fireEvent.click(backdrop);

      expect(mockOnCancel).toHaveBeenCalled();
    });

    it('calls onCancel when Escape key pressed', () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      fireEvent.keyDown(document, { key: 'Escape' });

      expect(mockOnCancel).toHaveBeenCalled();
    });
  });

  describe('Open/Close State', () => {
    it('does not render when isOpen is false', () => {
      renderWithClient(
        <ScheduleEditor isOpen={false} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      expect(screen.queryByTestId('schedule-editor-drawer')).not.toBeInTheDocument();
    });

    it('renders when isOpen is true', () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      expect(screen.getByTestId('schedule-editor-drawer')).toBeInTheDocument();
    });
  });

  describe('Loading State', () => {
    it('disables save button when saving', async () => {
      // Mock slow save
      mockOnSave.mockImplementation(() => new Promise(() => {}));

      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      // Fill required fields
      const nameInput = screen.getByLabelText(/schedule name/i);
      fireEvent.change(nameInput, { target: { value: 'Test' } });

      const addButton = screen.getByTestId('add-routine');
      fireEvent.click(addButton);

      const saveButton = screen.getByRole('button', { name: /save/i });
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(saveButton).toBeDisabled();
      });
    });

    it('shows loading indicator when saving', async () => {
      mockOnSave.mockImplementation(() => new Promise(() => {}));

      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      // Fill required fields
      const nameInput = screen.getByLabelText(/schedule name/i);
      fireEvent.change(nameInput, { target: { value: 'Test' } });

      const addButton = screen.getByTestId('add-routine');
      fireEvent.click(addButton);

      const saveButton = screen.getByRole('button', { name: /save/i });
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(screen.getByText(/saving/i)).toBeInTheDocument();
      });
    });
  });

  describe('Accessibility', () => {
    it('has accessible drawer role', () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('has aria-label on drawer', () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      expect(screen.getByRole('dialog')).toHaveAttribute(
        'aria-label',
        expect.stringMatching(/schedule editor/i)
      );
    });

    it('focuses name input when opened', async () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      await waitFor(() => {
        expect(screen.getByLabelText(/schedule name/i)).toHaveFocus();
      });
    });

    it('traps focus within drawer - Tab from last element goes to first', async () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      // Wait for drawer to be rendered
      await waitFor(() => {
        expect(screen.getByTestId('schedule-editor-drawer')).toBeInTheDocument();
      });

      // Focus the Save button (last focusable element in footer)
      const saveButton = screen.getByRole('button', { name: /save/i });
      saveButton.focus();
      expect(saveButton).toHaveFocus();

      // Simulate Tab key press
      fireEvent.keyDown(document, { key: 'Tab' });

      // Focus should wrap to first focusable element (close button in header)
      await waitFor(() => {
        const closeButton = screen.getByRole('button', { name: /close/i });
        expect(closeButton).toHaveFocus();
      });
    });

    it('traps focus within drawer - Shift+Tab from first element goes to last', async () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      // Wait for drawer to be rendered
      await waitFor(() => {
        expect(screen.getByTestId('schedule-editor-drawer')).toBeInTheDocument();
      });

      // Focus the close button (first focusable element in header)
      const closeButton = screen.getByRole('button', { name: /close/i });
      closeButton.focus();
      expect(closeButton).toHaveFocus();

      // Simulate Shift+Tab key press
      fireEvent.keyDown(document, { key: 'Tab', shiftKey: true });

      // Focus should wrap to last focusable element (Save button)
      await waitFor(() => {
        const saveButton = screen.getByRole('button', { name: /save/i });
        expect(saveButton).toHaveFocus();
      });
    });
  });

  describe('Dark Mode', () => {
    it('applies dark mode classes to drawer', () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      const drawer = screen.getByTestId('schedule-editor-drawer');
      expect(drawer.className).toMatch(/dark:/);
    });

    it('applies dark mode classes to header', () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      const header = screen.getByText(/create schedule/i);
      expect(header).toHaveClass('dark:text-white');
    });
  });

  describe('Error Message Sanitization', () => {
    it('displays known error codes as user-friendly messages', async () => {
      const knownError = new Error();
      knownError.code = 'NETWORK_ERROR';
      mockOnSave.mockRejectedValue(knownError);

      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      // Fill required fields
      const nameInput = screen.getByLabelText(/schedule name/i);
      fireEvent.change(nameInput, { target: { value: 'Test' } });

      const addButton = screen.getByTestId('add-routine');
      fireEvent.click(addButton);

      const saveButton = screen.getByRole('button', { name: /save/i });
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(screen.getByText(/unable to save.*connection/i)).toBeInTheDocument();
      });
    });

    it('truncates long error messages to 200 characters plus ellipsis', async () => {
      const longMessage = 'A'.repeat(300);
      mockOnSave.mockRejectedValue(new Error(longMessage));

      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      // Fill required fields
      const nameInput = screen.getByLabelText(/schedule name/i);
      fireEvent.change(nameInput, { target: { value: 'Test' } });

      const addButton = screen.getByTestId('add-routine');
      fireEvent.click(addButton);

      const saveButton = screen.getByRole('button', { name: /save/i });
      fireEvent.click(saveButton);

      await waitFor(() => {
        const errorElement = screen.getByText(/A{50,}/);
        // The error should be truncated to 200 chars + "..." (203 total)
        expect(errorElement.textContent.length).toBeLessThanOrEqual(203);
        expect(errorElement.textContent).toMatch(/\.\.\.$/);
      });
    });

    it('strips HTML tags from error messages for defense-in-depth', async () => {
      // HTML tags are stripped as defense-in-depth (React also auto-escapes)
      const xssMessage = '<script>alert("xss")</script>';
      mockOnSave.mockRejectedValue(new Error(xssMessage));

      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      // Fill required fields
      const nameInput = screen.getByLabelText(/schedule name/i);
      fireEvent.change(nameInput, { target: { value: 'Test' } });

      const addButton = screen.getByTestId('add-routine');
      fireEvent.click(addButton);

      const saveButton = screen.getByRole('button', { name: /save/i });
      fireEvent.click(saveButton);

      await waitFor(() => {
        // Error should be displayed with HTML tags stripped
        const errorContainer = document.querySelector('.text-red-600, .text-red-400');
        expect(errorContainer).toBeInTheDocument();
        // HTML tags should be stripped, leaving only the text content
        expect(errorContainer.textContent).toBe('alert("xss")');
        expect(errorContainer.textContent).not.toContain('<');
        expect(errorContainer.textContent).not.toContain('>');
      });
    });

    it('handles validation errors with user-friendly message', async () => {
      const validationError = new Error();
      validationError.code = 'VALIDATION_ERROR';
      mockOnSave.mockRejectedValue(validationError);

      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      // Fill required fields
      const nameInput = screen.getByLabelText(/schedule name/i);
      fireEvent.change(nameInput, { target: { value: 'Test' } });

      const addButton = screen.getByTestId('add-routine');
      fireEvent.click(addButton);

      const saveButton = screen.getByRole('button', { name: /save/i });
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(screen.getByText(/fix the errors above/i)).toBeInTheDocument();
      });
    });

    it('handles server errors with user-friendly message', async () => {
      const serverError = new Error();
      serverError.code = 'SERVER_ERROR';
      mockOnSave.mockRejectedValue(serverError);

      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      // Fill required fields
      const nameInput = screen.getByLabelText(/schedule name/i);
      fireEvent.change(nameInput, { target: { value: 'Test' } });

      const addButton = screen.getByTestId('add-routine');
      fireEvent.click(addButton);

      const saveButton = screen.getByRole('button', { name: /save/i });
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(screen.getByText(/server error.*try again/i)).toBeInTheDocument();
      });
    });

    it('uses fallback message when error has no message', async () => {
      mockOnSave.mockRejectedValue(new Error());

      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      // Fill required fields
      const nameInput = screen.getByLabelText(/schedule name/i);
      fireEvent.change(nameInput, { target: { value: 'Test' } });

      const addButton = screen.getByTestId('add-routine');
      fireEvent.click(addButton);

      const saveButton = screen.getByRole('button', { name: /save/i });
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(screen.getByText(/failed to save schedule/i)).toBeInTheDocument();
      });
    });
  });
});
