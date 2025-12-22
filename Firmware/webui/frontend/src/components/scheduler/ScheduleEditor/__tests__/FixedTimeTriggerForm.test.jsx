import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import FixedTimeTriggerForm from '../FixedTimeTriggerForm';

// Mock DaysOfWeekSelector component
vi.mock('../DaysOfWeekSelector', () => ({
  default: ({ value, onChange, disabled }) => (
    <div data-testid="days-of-week-selector">
      <button
        data-testid="toggle-monday"
        onClick={() => {
          const currentDays = value || [0, 1, 2, 3, 4, 5, 6];
          const newDays = currentDays.includes(0)
            ? currentDays.filter((d) => d !== 0)
            : [...currentDays, 0].sort((a, b) => a - b);
          onChange(newDays.length === 7 ? null : newDays);
        }}
        disabled={disabled}
      >
        Monday
      </button>
      <button
        data-testid="toggle-all-days"
        onClick={() => onChange(null)}
        disabled={disabled}
      >
        All Days
      </button>
    </div>
  ),
}));

describe('FixedTimeTriggerForm', () => {
  let mockOnChange;

  beforeEach(() => {
    mockOnChange = vi.fn();
  });

  describe('Rendering', () => {
    it('renders with default values', () => {
      render(<FixedTimeTriggerForm onChange={mockOnChange} />);

      expect(screen.getByText('Fixed Time Configuration')).toBeInTheDocument();
      expect(screen.getByLabelText(/time of day/i)).toBeInTheDocument();
      expect(screen.getByText('Preview:')).toBeInTheDocument();
    });

    it('renders with provided value', () => {
      const value = {
        time_of_day: '18:30',
        days_of_week: [0, 1, 2],
      };

      render(<FixedTimeTriggerForm value={value} onChange={mockOnChange} />);

      const timeInput = screen.getByLabelText(/time of day/i);
      expect(timeInput).toHaveValue('18:30');
    });

    it('renders DaysOfWeekSelector component', () => {
      render(<FixedTimeTriggerForm onChange={mockOnChange} />);

      expect(screen.getByTestId('days-of-week-selector')).toBeInTheDocument();
    });
  });

  describe('Time of Day Input', () => {
    it('updates time_of_day on input change', () => {
      const value = {
        time_of_day: '12:00',
        days_of_week: null,
      };

      render(<FixedTimeTriggerForm value={value} onChange={mockOnChange} />);

      const timeInput = screen.getByLabelText(/time of day/i);
      fireEvent.change(timeInput, { target: { value: '18:30' } });

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        time_of_day: '18:30',
      });
    });

    it('accepts valid HH:MM format', () => {
      const value = {
        time_of_day: '12:00',
        days_of_week: null,
      };

      render(<FixedTimeTriggerForm value={value} onChange={mockOnChange} />);

      const timeInput = screen.getByLabelText(/time of day/i);
      fireEvent.change(timeInput, { target: { value: '23:59' } });

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        time_of_day: '23:59',
      });
    });

    it('accepts midnight (00:00)', () => {
      const value = {
        time_of_day: '12:00',
        days_of_week: null,
      };

      render(<FixedTimeTriggerForm value={value} onChange={mockOnChange} />);

      const timeInput = screen.getByLabelText(/time of day/i);
      fireEvent.change(timeInput, { target: { value: '00:00' } });

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        time_of_day: '00:00',
      });
    });

    it('shows error message for invalid time', () => {
      const errors = {
        time_of_day: 'Time must be in HH:MM format',
      };

      render(<FixedTimeTriggerForm onChange={mockOnChange} errors={errors} />);

      expect(screen.getByText(errors.time_of_day)).toBeInTheDocument();
    });
  });

  describe('Quick Time Presets', () => {
    it('renders quick time preset buttons', () => {
      render(<FixedTimeTriggerForm onChange={mockOnChange} />);

      expect(screen.getByLabelText('Set time to 06:00')).toBeInTheDocument();
      expect(screen.getByLabelText('Set time to 12:00')).toBeInTheDocument();
      expect(screen.getByLabelText('Set time to 18:00')).toBeInTheDocument();
      expect(screen.getByLabelText('Set time to 21:00')).toBeInTheDocument();
    });

    it('sets time to 06:00 when 6 AM preset clicked', () => {
      const value = {
        time_of_day: '12:00',
        days_of_week: null,
      };

      render(<FixedTimeTriggerForm value={value} onChange={mockOnChange} />);

      const preset6AM = screen.getByLabelText('Set time to 06:00');
      fireEvent.click(preset6AM);

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        time_of_day: '06:00',
      });
    });

    it('sets time to 12:00 when 12 PM preset clicked', () => {
      const value = {
        time_of_day: '18:00',
        days_of_week: null,
      };

      render(<FixedTimeTriggerForm value={value} onChange={mockOnChange} />);

      const preset12PM = screen.getByLabelText('Set time to 12:00');
      fireEvent.click(preset12PM);

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        time_of_day: '12:00',
      });
    });

    it('sets time to 18:00 when 6 PM preset clicked', () => {
      const value = {
        time_of_day: '12:00',
        days_of_week: null,
      };

      render(<FixedTimeTriggerForm value={value} onChange={mockOnChange} />);

      const preset6PM = screen.getByLabelText('Set time to 18:00');
      fireEvent.click(preset6PM);

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        time_of_day: '18:00',
      });
    });

    it('sets time to 21:00 when 9 PM preset clicked', () => {
      const value = {
        time_of_day: '12:00',
        days_of_week: null,
      };

      render(<FixedTimeTriggerForm value={value} onChange={mockOnChange} />);

      const preset9PM = screen.getByLabelText('Set time to 21:00');
      fireEvent.click(preset9PM);

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        time_of_day: '21:00',
      });
    });

    it('highlights selected preset', () => {
      const value = {
        time_of_day: '18:00',
        days_of_week: null,
      };

      render(<FixedTimeTriggerForm value={value} onChange={mockOnChange} />);

      const preset6PM = screen.getByLabelText('Set time to 18:00');
      expect(preset6PM).toHaveClass('bg-blue-500');
    });

    it('does not highlight non-selected presets', () => {
      const value = {
        time_of_day: '18:00',
        days_of_week: null,
      };

      render(<FixedTimeTriggerForm value={value} onChange={mockOnChange} />);

      const preset12PM = screen.getByLabelText('Set time to 12:00');
      expect(preset12PM).toHaveClass('bg-gray-100');
      expect(preset12PM).not.toHaveClass('bg-blue-500');
    });
  });

  describe('DaysOfWeekSelector Integration', () => {
    it('passes days_of_week value to DaysOfWeekSelector', () => {
      const value = {
        time_of_day: '12:00',
        days_of_week: [0, 2, 4],
      };

      render(<FixedTimeTriggerForm value={value} onChange={mockOnChange} />);

      expect(screen.getByTestId('days-of-week-selector')).toBeInTheDocument();
    });

    it('calls onChange when DaysOfWeekSelector changes', () => {
      const value = {
        time_of_day: '12:00',
        days_of_week: null,
      };

      render(<FixedTimeTriggerForm value={value} onChange={mockOnChange} />);

      const mondayToggle = screen.getByTestId('toggle-monday');
      fireEvent.click(mondayToggle);

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        days_of_week: [1, 2, 3, 4, 5, 6],
      });
    });

    it('passes disabled state to DaysOfWeekSelector', () => {
      render(<FixedTimeTriggerForm onChange={mockOnChange} disabled={true} />);

      const mondayToggle = screen.getByTestId('toggle-monday');
      expect(mondayToggle).toBeDisabled();
    });
  });

  describe('Preview Text Generation', () => {
    it('generates preview for time without days', () => {
      const value = {
        time_of_day: '12:00',
        days_of_week: null,
      };

      render(<FixedTimeTriggerForm value={value} onChange={mockOnChange} />);

      expect(screen.getByText('At 12:00')).toBeInTheDocument();
    });

    it('generates preview for time with all days', () => {
      const value = {
        time_of_day: '18:30',
        days_of_week: [0, 1, 2, 3, 4, 5, 6],
      };

      render(<FixedTimeTriggerForm value={value} onChange={mockOnChange} />);

      expect(screen.getByText('At 18:30')).toBeInTheDocument();
    });

    it('generates preview with specific days', () => {
      const value = {
        time_of_day: '06:00',
        days_of_week: [0, 2, 4],
      };

      render(<FixedTimeTriggerForm value={value} onChange={mockOnChange} />);

      expect(screen.getByText('At 06:00 on Mon, Wed, Fri')).toBeInTheDocument();
    });

    it('generates preview for weekdays only', () => {
      const value = {
        time_of_day: '09:00',
        days_of_week: [0, 1, 2, 3, 4],
      };

      render(<FixedTimeTriggerForm value={value} onChange={mockOnChange} />);

      expect(screen.getByText('At 09:00 on Mon, Tue, Wed, Thu, Fri')).toBeInTheDocument();
    });

    it('generates preview for weekends only', () => {
      const value = {
        time_of_day: '10:00',
        days_of_week: [5, 6],
      };

      render(<FixedTimeTriggerForm value={value} onChange={mockOnChange} />);

      expect(screen.getByText('At 10:00 on Sat, Sun')).toBeInTheDocument();
    });

    it('generates preview for midnight', () => {
      const value = {
        time_of_day: '00:00',
        days_of_week: null,
      };

      render(<FixedTimeTriggerForm value={value} onChange={mockOnChange} />);

      expect(screen.getByText('At 00:00')).toBeInTheDocument();
    });

    it('generates preview for end of day', () => {
      const value = {
        time_of_day: '23:59',
        days_of_week: null,
      };

      render(<FixedTimeTriggerForm value={value} onChange={mockOnChange} />);

      expect(screen.getByText('At 23:59')).toBeInTheDocument();
    });
  });

  describe('Disabled State', () => {
    it('disables time input when disabled prop is true', () => {
      render(<FixedTimeTriggerForm onChange={mockOnChange} disabled={true} />);

      const timeInput = screen.getByLabelText(/time of day/i);
      expect(timeInput).toBeDisabled();
    });

    it('disables preset buttons when disabled prop is true', () => {
      render(<FixedTimeTriggerForm onChange={mockOnChange} disabled={true} />);

      const preset12PM = screen.getByLabelText('Set time to 12:00');
      expect(preset12PM).toBeDisabled();
    });

    it('does not disable inputs when disabled prop is false', () => {
      render(<FixedTimeTriggerForm onChange={mockOnChange} disabled={false} />);

      const timeInput = screen.getByLabelText(/time of day/i);
      expect(timeInput).not.toBeDisabled();
    });
  });

  describe('Dark Mode Styling', () => {
    it('applies dark mode classes to time input', () => {
      render(<FixedTimeTriggerForm onChange={mockOnChange} />);

      const timeInput = screen.getByLabelText(/time of day/i);
      expect(timeInput).toHaveClass('dark:bg-gray-800', 'dark:text-white', 'dark:border-gray-600');
    });

    it('applies dark mode classes to labels', () => {
      render(<FixedTimeTriggerForm onChange={mockOnChange} />);

      const header = screen.getByText('Fixed Time Configuration');
      expect(header).toHaveClass('dark:text-white');
    });

    it('applies dark mode classes to preset buttons', () => {
      render(<FixedTimeTriggerForm onChange={mockOnChange} />);

      // Test non-selected preset button (default time is 12:00, so 18:00 is not selected)
      const preset6PM = screen.getByLabelText('Set time to 18:00');
      expect(preset6PM).toHaveClass('dark:bg-gray-700', 'dark:text-gray-300');
    });

    it('applies dark mode classes to preview text', () => {
      const value = {
        time_of_day: '12:00',
        days_of_week: null,
      };

      render(<FixedTimeTriggerForm value={value} onChange={mockOnChange} />);

      const previewText = screen.getByText('At 12:00');
      expect(previewText).toHaveClass('dark:text-gray-400', 'dark:bg-gray-800');
    });
  });

  describe('onChange Callback', () => {
    it('calls onChange with complete trigger object when time changes', () => {
      const value = {
        time_of_day: '12:00',
        days_of_week: [0, 1, 2],
      };

      render(<FixedTimeTriggerForm value={value} onChange={mockOnChange} />);

      const timeInput = screen.getByLabelText(/time of day/i);
      fireEvent.change(timeInput, { target: { value: '18:30' } });

      expect(mockOnChange).toHaveBeenCalledWith({
        time_of_day: '18:30',
        days_of_week: [0, 1, 2],
      });
    });

    it('calls onChange with complete trigger object when preset clicked', () => {
      const value = {
        time_of_day: '12:00',
        days_of_week: null,
      };

      render(<FixedTimeTriggerForm value={value} onChange={mockOnChange} />);

      const preset6PM = screen.getByLabelText('Set time to 18:00');
      fireEvent.click(preset6PM);

      expect(mockOnChange).toHaveBeenCalledWith({
        time_of_day: '18:00',
        days_of_week: null,
      });
    });

    it('calls onChange with complete trigger object when days change', () => {
      const value = {
        time_of_day: '12:00',
        days_of_week: null,
      };

      render(<FixedTimeTriggerForm value={value} onChange={mockOnChange} />);

      const allDaysButton = screen.getByTestId('toggle-all-days');
      fireEvent.click(allDaysButton);

      expect(mockOnChange).toHaveBeenCalledWith({
        time_of_day: '12:00',
        days_of_week: null,
      });
    });
  });
});
