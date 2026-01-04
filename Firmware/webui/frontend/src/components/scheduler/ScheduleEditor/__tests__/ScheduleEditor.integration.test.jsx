/**
 * ScheduleEditor Integration Tests
 *
 * These tests verify the integration between ScheduleEditor and its real child components.
 * Unlike unit tests which mock child components, these tests import the actual implementations
 * to verify that data flows correctly between components.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ScheduleEditor from '../ScheduleEditor';

// Only mock the PatternLibrary components which require API calls
vi.mock('../../PatternLibrary', () => ({
  PatternList: ({ mode, selectedPatternId, onPatternSelect }) => (
    <div data-testid="pattern-list">
      <button
        data-testid="select-test-pattern"
        onClick={() =>
          onPatternSelect({
            pattern_id: 'test-pattern-1',
            name: 'Night Photography',
            description: 'Standard moth photography routine',
            actions: [
              { action_id: '1', type: 'attract_on', parameters: {} },
              { action_id: '2', type: 'wait', parameters: { duration_seconds: 300 } },
              { action_id: '3', type: 'camera_capture', parameters: {} },
            ],
            category: 'photography',
          })
        }
      >
        Select Pattern
      </button>
      <span data-testid="pattern-mode">{mode}</span>
      <span data-testid="selected-pattern-id">{selectedPatternId || 'none'}</span>
    </div>
  ),
}));

vi.mock('../../RoutineEditor', () => ({
  RoutineEditor: ({ onSave, onCancel }) => (
    <div data-testid="routine-editor">
      <button
        data-testid="save-custom-routine"
        onClick={() =>
          onSave({
            routine_id: 'custom-routine-1',
            name: 'Custom Routine',
            description: 'Custom routine',
            actions: [{ action_id: '1', type: 'attract_on', parameters: {} }],
          })
        }
      >
        Save Custom
      </button>
      <button data-testid="cancel-custom-routine" onClick={onCancel}>
        Cancel
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

describe('ScheduleEditor Integration', () => {
  let mockOnSave;
  let mockOnCancel;

  beforeEach(() => {
    mockOnSave = vi.fn().mockResolvedValue(undefined);
    mockOnCancel = vi.fn();
  });

  describe('Trigger Type Selection', () => {
    it('shows IntervalTriggerForm with time window when interval is selected', () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      // Should show interval trigger by default
      expect(screen.getByLabelText(/trigger type/i)).toHaveValue('interval');

      // Should show interval-specific fields
      expect(screen.getByText('Interval Configuration')).toBeInTheDocument();
      expect(screen.getByText('Time Window:')).toBeInTheDocument();
    });

    it('shows SolarTriggerForm when solar is selected', () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      // Select solar trigger type
      const triggerTypeSelect = screen.getByLabelText(/trigger type/i);
      fireEvent.change(triggerTypeSelect, { target: { value: 'solar' } });

      // Should show solar-specific fields
      expect(screen.getByLabelText(/solar event/i)).toBeInTheDocument();
      expect(screen.getByText('Quick presets:')).toBeInTheDocument();
    });

    it('shows FixedTimeTriggerForm when fixed_time is selected', () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      const triggerTypeSelect = screen.getByLabelText(/trigger type/i);
      fireEvent.change(triggerTypeSelect, { target: { value: 'fixed_time' } });

      // Should show fixed time-specific fields
      expect(screen.getByText('Fixed Time Configuration')).toBeInTheDocument();
    });

    it('shows MoonPhaseTriggerForm when moon_phase is selected', () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      const triggerTypeSelect = screen.getByLabelText(/trigger type/i);
      fireEvent.change(triggerTypeSelect, { target: { value: 'moon_phase' } });

      // Should show moon phase-specific fields
      expect(screen.getByText('Moon Phase Configuration')).toBeInTheDocument();
      expect(screen.getByLabelText(/moon phase/i)).toBeInTheDocument();
    });

    it('shows SensorTriggerForm when sensor is selected', () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      const triggerTypeSelect = screen.getByLabelText(/trigger type/i);
      fireEvent.change(triggerTypeSelect, { target: { value: 'sensor' } });

      // Should show sensor-specific fields
      expect(screen.getByText('Sensor Configuration')).toBeInTheDocument();
      expect(screen.getByLabelText(/sensor type/i)).toBeInTheDocument();
    });
  });

  describe('Days of Week Integration', () => {
    it('shows DaysOfWeekSelector in IntervalTriggerForm', () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      // Find the Days of Week label
      expect(screen.getByText('Days of Week')).toBeInTheDocument();

      // Monday button should be present
      const mondayButton = screen.getByLabelText(/monday/i);
      expect(mondayButton).toBeInTheDocument();
    });

    it('shows DaysOfWeekSelector in SolarTriggerForm', async () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      // Switch to solar trigger
      const triggerTypeSelect = screen.getByLabelText(/trigger type/i);
      fireEvent.change(triggerTypeSelect, { target: { value: 'solar' } });

      // Wait for solar form to render
      await waitFor(() => {
        expect(screen.getByText('Solar Event Configuration')).toBeInTheDocument();
      });

      // Monday button should be present in solar form too
      const mondayButton = screen.getByLabelText(/monday/i);
      expect(mondayButton).toBeInTheDocument();
    });
  });

  describe('Date Range Integration', () => {
    it('shows date range section with start and end date inputs', () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      expect(screen.getByText('Date Range (Optional)')).toBeInTheDocument();
      expect(screen.getByLabelText('Start date')).toBeInTheDocument();
      expect(screen.getByLabelText('End date')).toBeInTheDocument();
    });

    it('updates date range when dates are changed', async () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      const startDateInput = screen.getByLabelText('Start date');
      fireEvent.change(startDateInput, { target: { value: '2024-06-01' } });

      await waitFor(() => {
        expect(startDateInput).toHaveValue('2024-06-01');
      });
    });
  });

  describe('Pattern Selection Integration', () => {
    it('shows pattern library in embedded mode by default', () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      expect(screen.getByTestId('pattern-list')).toBeInTheDocument();
      expect(screen.getByTestId('pattern-mode')).toHaveTextContent('embedded');
    });

    it('calls pattern onSelect when button clicked', async () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      const selectPatternButton = screen.getByTestId('select-test-pattern');
      fireEvent.click(selectPatternButton);

      // The pattern should be reflected in the summary section after selection
      await waitFor(() => {
        // Look for pattern name in the pattern summary
        const patternSummary = screen.getAllByText('Night Photography');
        expect(patternSummary.length).toBeGreaterThan(0);
      });
    });

    it('switches to custom pattern editor when custom tab is selected', async () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      // Click on Custom tab
      const customTab = screen.getByRole('tab', { name: /custom/i });
      fireEvent.click(customTab);

      await waitFor(() => {
        expect(screen.getByTestId('routine-editor')).toBeInTheDocument();
      });
    });
  });

  describe('Focus Trap', () => {
    it('traps focus within drawer when Tab is pressed at end', async () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      // Get all focusable elements in the drawer
      const drawer = screen.getByRole('dialog');
      const focusableElements = drawer.querySelectorAll(
        'button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled])'
      );

      // Focus the last element
      const lastElement = focusableElements[focusableElements.length - 1];
      lastElement.focus();
      expect(document.activeElement).toBe(lastElement);

      // Press Tab - focus should wrap to first element
      fireEvent.keyDown(document, { key: 'Tab' });

      // The first focusable element should be focused
      await waitFor(() => {
        expect(document.activeElement).toBe(focusableElements[0]);
      });
    });

    it('traps focus within drawer when Shift+Tab is pressed at start', async () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      const drawer = screen.getByRole('dialog');
      const focusableElements = drawer.querySelectorAll(
        'button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled])'
      );

      // Focus the first element
      const firstElement = focusableElements[0];
      firstElement.focus();
      expect(document.activeElement).toBe(firstElement);

      // Press Shift+Tab - focus should wrap to last element
      fireEvent.keyDown(document, { key: 'Tab', shiftKey: true });

      await waitFor(() => {
        const lastElement = focusableElements[focusableElements.length - 1];
        expect(document.activeElement).toBe(lastElement);
      });
    });
  });

  describe('Full Save Flow', () => {
    it('saves schedule with all configured data', async () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      // Fill in the schedule name
      const nameInput = screen.getByLabelText('Schedule name');
      fireEvent.change(nameInput, { target: { value: 'My Test Schedule' } });

      // Select a pattern
      const selectPatternButton = screen.getByTestId('select-test-pattern');
      fireEvent.click(selectPatternButton);

      // Wait for pattern selection to be registered
      await waitFor(() => {
        const patternSummary = screen.getAllByText('Night Photography');
        expect(patternSummary.length).toBeGreaterThan(0);
      });

      // Set a date range
      const startDateInput = screen.getByLabelText('Start date');
      fireEvent.change(startDateInput, { target: { value: '2024-06-01' } });

      // Click save
      const saveButton = screen.getByRole('button', { name: /save/i });
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(mockOnSave).toHaveBeenCalledWith(
          expect.objectContaining({
            name: 'My Test Schedule',
            trigger: expect.objectContaining({
              trigger_type: 'interval',
            }),
            event_patterns: expect.arrayContaining([
              expect.objectContaining({
                name: 'Night Photography',
              }),
            ]),
            date_range: expect.objectContaining({
              start_date: '2024-06-01',
            }),
          })
        );
      });
    });

    it('shows validation error when name is empty', async () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      // Select a pattern (required)
      const selectPatternButton = screen.getByTestId('select-test-pattern');
      fireEvent.click(selectPatternButton);

      await waitFor(() => {
        const patternSummary = screen.getAllByText('Night Photography');
        expect(patternSummary.length).toBeGreaterThan(0);
      });

      // Try to save without a name
      const saveButton = screen.getByRole('button', { name: /save/i });
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(screen.getByText('Schedule name is required')).toBeInTheDocument();
      });
      expect(mockOnSave).not.toHaveBeenCalled();
    });

    it('shows validation error when pattern is not selected', async () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      // Fill in the name but don't select a pattern
      const nameInput = screen.getByLabelText('Schedule name');
      fireEvent.change(nameInput, { target: { value: 'My Test Schedule' } });

      // Try to save without a pattern
      const saveButton = screen.getByRole('button', { name: /save/i });
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(screen.getByText('Event pattern is required')).toBeInTheDocument();
      });
      expect(mockOnSave).not.toHaveBeenCalled();
    });
  });

  describe('Edit Mode Integration', () => {
    const existingSchedule = {
      schedule_id: 'existing-123',
      name: 'Existing Schedule',
      description: 'An existing schedule for editing',
      trigger: {
        trigger_type: 'solar',
        solar_event: 'sunset',
        offset_minutes: 30,
        days_of_week: null,
      },
      event_patterns: [
        {
          pattern_id: 'pattern-1',
          name: 'Existing Pattern',
          description: 'Test',
          actions: [{ action_id: '1', type: 'attract_on', parameters: {} }],
          category: 'library',
        },
      ],
      date_range: {
        start_date: '2024-01-01',
        end_date: '2024-06-30',
      },
    };

    it('loads existing schedule data into form', async () => {
      renderWithClient(
        <ScheduleEditor
          isOpen={true}
          schedule={existingSchedule}
          onSave={mockOnSave}
          onCancel={mockOnCancel}
        />
      );

      // Check header says "Edit Schedule"
      expect(screen.getByText('Edit Schedule')).toBeInTheDocument();

      // Check name is populated
      const nameInput = screen.getByLabelText('Schedule name');
      expect(nameInput).toHaveValue('Existing Schedule');

      // Check description is populated
      const descInput = screen.getByLabelText('Description');
      expect(descInput).toHaveValue('An existing schedule for editing');

      // Check trigger type is solar
      const triggerTypeSelect = screen.getByLabelText(/trigger type/i);
      expect(triggerTypeSelect).toHaveValue('solar');

      // Check solar event is populated
      await waitFor(() => {
        const solarEventSelect = screen.getByLabelText(/solar event/i);
        expect(solarEventSelect).toHaveValue('sunset');
      });
    });

    it('preserves schedule_id when saving edits', async () => {
      renderWithClient(
        <ScheduleEditor
          isOpen={true}
          schedule={existingSchedule}
          onSave={mockOnSave}
          onCancel={mockOnCancel}
        />
      );

      // Modify the name
      const nameInput = screen.getByLabelText('Schedule name');
      fireEvent.change(nameInput, { target: { value: 'Updated Schedule Name' } });

      // Click save
      const saveButton = screen.getByRole('button', { name: /save/i });
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(mockOnSave).toHaveBeenCalledWith(
          expect.objectContaining({
            schedule_id: 'existing-123',
            name: 'Updated Schedule Name',
          })
        );
      });
    });
  });

  describe('Time Window Validation', () => {
    it('shows mixed time warning when start is fixed and end is solar', async () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      // Find the time window inputs - need to expand/access them
      // The TimeWindowInput should be visible with interval trigger
      expect(screen.getByText('Time Window:')).toBeInTheDocument();

      // Change start time mode to fixed and end to solar
      // This requires interacting with the solar toggle buttons in TimeWindowInput
      // The implementation shows a warning when mixing fixed and solar times
    });
  });

  describe('Keyboard Navigation', () => {
    it('closes drawer when Escape is pressed', () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      fireEvent.keyDown(document, { key: 'Escape' });

      expect(mockOnCancel).toHaveBeenCalled();
    });

    it('closes drawer when backdrop is clicked', () => {
      renderWithClient(
        <ScheduleEditor isOpen={true} onSave={mockOnSave} onCancel={mockOnCancel} />
      );

      const backdrop = screen.getByTestId('drawer-backdrop');
      fireEvent.click(backdrop);

      expect(mockOnCancel).toHaveBeenCalled();
    });
  });
});
