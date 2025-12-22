import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ScheduleEditor from '../ScheduleEditor';

// Mock child components
vi.mock('../TriggerForm', () => ({
  default: ({ value, onChange, disabled }) => (
    <div data-testid="trigger-form">
      <span data-testid="trigger-value">{JSON.stringify(value)}</span>
      <button
        data-testid="trigger-change"
        onClick={() =>
          onChange({
            trigger_type: 'interval',
            interval_minutes: 120,
          })
        }
        disabled={disabled}
      >
        Change Trigger
      </button>
    </div>
  ),
}));

vi.mock('../EventPatternSelector', () => ({
  default: ({ value, onChange, disabled, errors }) => (
    <div data-testid="event-pattern-selector">
      <span data-testid="pattern-value">{JSON.stringify(value)}</span>
      <button
        data-testid="pattern-select"
        onClick={() =>
          onChange({
            source: 'library',
            pattern: {
              pattern_id: 'test-1',
              name: 'Test Pattern',
              actions: [{ action_type: 'take_photo', offset_minutes: 0 }],
            },
          })
        }
        disabled={disabled}
      >
        Select Pattern
      </button>
      {errors?.pattern && (
        <span data-testid="pattern-error" className="text-red-600">
          {errors.pattern}
        </span>
      )}
    </div>
  ),
}));

vi.mock('../DateRangeSection', () => ({
  default: ({ value, onChange, disabled }) => (
    <div data-testid="date-range-section">
      <span data-testid="date-value">{JSON.stringify(value)}</span>
      <button
        data-testid="date-change"
        onClick={() =>
          onChange({
            start_date: '2024-01-01',
            end_date: '2024-12-31',
          })
        }
        disabled={disabled}
      >
        Change Dates
      </button>
    </div>
  ),
}));

vi.mock('../PreviewSection', () => ({
  default: ({ trigger, dateRange, pattern }) => (
    <div data-testid="preview-section">
      <span data-testid="preview-trigger">{trigger?.trigger_type || 'none'}</span>
      <span data-testid="preview-pattern">{pattern?.name || 'none'}</span>
      <span data-testid="preview-dates">
        {dateRange?.start_date || 'none'} - {dateRange?.end_date || 'none'}
      </span>
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
    it('renders all section components', () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      expect(screen.getByTestId('trigger-form')).toBeInTheDocument();
      expect(screen.getByTestId('event-pattern-selector')).toBeInTheDocument();
      expect(screen.getByTestId('date-range-section')).toBeInTheDocument();
      expect(screen.getByTestId('preview-section')).toBeInTheDocument();
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
        trigger: { trigger_type: 'interval', interval_minutes: 60 },
        event_patterns: [],
        date_range: {},
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
    });

    it('populates form with existing schedule data', () => {
      const schedule = {
        schedule_id: 'sched-1',
        name: 'My Schedule',
        description: 'A test schedule',
        trigger: { trigger_type: 'solar', solar_event: 'sunset' },
        event_patterns: [{ pattern_id: 'p1', name: 'Pattern 1', actions: [] }],
        date_range: { start_date: '2024-01-01', end_date: null },
      };

      renderWithClient(
        <ScheduleEditor
          isOpen={true}
          schedule={schedule}
          onSave={mockOnSave}
          onCancel={mockOnCancel}
        />
      );

      const nameInput = screen.getByLabelText(/schedule name/i);
      expect(nameInput).toHaveValue('My Schedule');

      const descInput = screen.getByLabelText(/description/i);
      expect(descInput).toHaveValue('A test schedule');
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

  describe('Child Component Integration', () => {
    it('passes trigger value to TriggerForm', () => {
      const schedule = {
        schedule_id: 'sched-1',
        name: 'Test',
        trigger: { trigger_type: 'interval', interval_minutes: 30 },
        event_patterns: [],
        date_range: {},
      };

      renderWithClient(
        <ScheduleEditor
          isOpen={true}
          schedule={schedule}
          onSave={mockOnSave}
          onCancel={mockOnCancel}
        />
      );

      const triggerValue = screen.getByTestId('trigger-value');
      expect(triggerValue).toHaveTextContent('"interval_minutes":30');
    });

    it('updates trigger when TriggerForm changes', () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      const changeButton = screen.getByTestId('trigger-change');
      fireEvent.click(changeButton);

      // Verify the preview section receives updated trigger
      const previewTrigger = screen.getByTestId('preview-trigger');
      expect(previewTrigger).toHaveTextContent('interval');
    });

    it('updates pattern when EventPatternSelector changes', () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      const selectButton = screen.getByTestId('pattern-select');
      fireEvent.click(selectButton);

      // Verify the preview section receives updated pattern
      const previewPattern = screen.getByTestId('preview-pattern');
      expect(previewPattern).toHaveTextContent('Test Pattern');
    });

    it('updates date range when DateRangeSection changes', () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      const changeButton = screen.getByTestId('date-change');
      fireEvent.click(changeButton);

      // Verify the preview section receives updated dates
      const previewDates = screen.getByTestId('preview-dates');
      expect(previewDates).toHaveTextContent('2024-01-01');
    });
  });

  describe('Validation', () => {
    it('shows error when saving without name', async () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      const saveButton = screen.getByRole('button', { name: /save/i });
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(screen.getByText(/schedule name is required/i)).toBeInTheDocument();
      });
      expect(mockOnSave).not.toHaveBeenCalled();
    });

    it('shows error when saving without pattern', async () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      // Fill in name but not pattern
      const nameInput = screen.getByLabelText(/schedule name/i);
      fireEvent.change(nameInput, { target: { value: 'Test Schedule' } });

      const saveButton = screen.getByRole('button', { name: /save/i });
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(screen.getByText(/event pattern is required/i)).toBeInTheDocument();
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

      // Select a pattern
      const selectButton = screen.getByTestId('pattern-select');
      fireEvent.click(selectButton);

      // Save
      const saveButton = screen.getByRole('button', { name: /save/i });
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(mockOnSave).toHaveBeenCalledWith(
          expect.objectContaining({
            name: 'Test Schedule',
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

      const selectButton = screen.getByTestId('pattern-select');
      fireEvent.click(selectButton);

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

      const selectButton = screen.getByTestId('pattern-select');
      fireEvent.click(selectButton);

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
});
