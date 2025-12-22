import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import IntervalTriggerForm from '../IntervalTriggerForm';
import { SCHEDULE_LIMITS } from '../constants';

// Mock child components
vi.mock('../TimeWindowInput', () => ({
  default: ({ value, onChange, disabled, errors }) => (
    <div data-testid="time-window-input">
      <input
        data-testid="time-window-start"
        value={value.start_time}
        onChange={(e) => onChange({ ...value, start_time: e.target.value })}
        disabled={disabled}
      />
      <input
        data-testid="time-window-end"
        value={value.end_time}
        onChange={(e) => onChange({ ...value, end_time: e.target.value })}
        disabled={disabled}
      />
      {errors.start_time && <span data-testid="error-start">{errors.start_time}</span>}
      {errors.end_time && <span data-testid="error-end">{errors.end_time}</span>}
    </div>
  ),
}));

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

describe('IntervalTriggerForm', () => {
  let mockOnChange;

  beforeEach(() => {
    mockOnChange = vi.fn();
  });

  describe('Rendering', () => {
    it('renders with default values', () => {
      render(<IntervalTriggerForm onChange={mockOnChange} />);

      expect(screen.getByText('Interval Configuration')).toBeInTheDocument();
      expect(screen.getByLabelText('Interval in minutes')).toBeInTheDocument();
      expect(screen.getByText('Quick presets:')).toBeInTheDocument();
      expect(screen.getByText('Time Window:')).toBeInTheDocument();
      expect(screen.getByText('Preview:')).toBeInTheDocument();
    });

    it('renders with provided value', () => {
      const value = {
        interval_minutes: 120,
        time_window: {
          start_time: '21:00',
          end_time: '05:00',
          start_offset_minutes: 0,
          end_offset_minutes: 0,
        },
        days_of_week: [0, 1, 2], // Mon, Tue, Wed
      };

      render(<IntervalTriggerForm value={value} onChange={mockOnChange} />);

      const intervalInput = screen.getByLabelText('Interval in minutes');
      expect(intervalInput).toHaveValue(120);
    });

    it('renders all quick preset buttons', () => {
      render(<IntervalTriggerForm onChange={mockOnChange} />);

      expect(screen.getByLabelText('Set interval to 15 min')).toBeInTheDocument();
      expect(screen.getByLabelText('Set interval to 30 min')).toBeInTheDocument();
      expect(screen.getByLabelText('Set interval to 60 min')).toBeInTheDocument();
      expect(screen.getByLabelText('Set interval to 2 hours')).toBeInTheDocument();
      expect(screen.getByLabelText('Set interval to 4 hours')).toBeInTheDocument();
    });

    it('renders TimeWindowInput component', () => {
      render(<IntervalTriggerForm onChange={mockOnChange} />);

      expect(screen.getByTestId('time-window-input')).toBeInTheDocument();
    });

    it('renders DaysOfWeekSelector component', () => {
      render(<IntervalTriggerForm onChange={mockOnChange} />);

      expect(screen.getByTestId('days-of-week-selector')).toBeInTheDocument();
    });
  });

  describe('Interval Input', () => {
    it('updates interval_minutes on input change', () => {
      const value = {
        interval_minutes: 60,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: null,
      };

      render(<IntervalTriggerForm value={value} onChange={mockOnChange} />);

      const intervalInput = screen.getByLabelText('Interval in minutes');
      fireEvent.change(intervalInput, { target: { value: '90' } });

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        interval_minutes: 90,
      });
    });

    it('respects min and max interval limits', () => {
      render(<IntervalTriggerForm onChange={mockOnChange} />);

      const intervalInput = screen.getByLabelText('Interval in minutes');
      expect(intervalInput).toHaveAttribute('min', String(SCHEDULE_LIMITS.MIN_INTERVAL_MINUTES));
      expect(intervalInput).toHaveAttribute('max', String(SCHEDULE_LIMITS.MAX_INTERVAL_MINUTES));
    });

    it('shows error message for invalid interval', () => {
      const errors = {
        interval_minutes: 'Interval must be between 1 and 10080 minutes',
      };

      render(<IntervalTriggerForm onChange={mockOnChange} errors={errors} />);

      expect(screen.getByText(errors.interval_minutes)).toBeInTheDocument();
    });
  });

  describe('Quick Preset Buttons', () => {
    it('sets interval to 15 minutes when 15 min preset clicked', () => {
      const value = {
        interval_minutes: 60,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: null,
      };

      render(<IntervalTriggerForm value={value} onChange={mockOnChange} />);

      const preset15 = screen.getByLabelText('Set interval to 15 min');
      fireEvent.click(preset15);

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        interval_minutes: 15,
      });
    });

    it('sets interval to 30 minutes when 30 min preset clicked', () => {
      const value = {
        interval_minutes: 60,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: null,
      };

      render(<IntervalTriggerForm value={value} onChange={mockOnChange} />);

      const preset30 = screen.getByLabelText('Set interval to 30 min');
      fireEvent.click(preset30);

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        interval_minutes: 30,
      });
    });

    it('sets interval to 60 minutes when 60 min preset clicked', () => {
      const value = {
        interval_minutes: 30,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: null,
      };

      render(<IntervalTriggerForm value={value} onChange={mockOnChange} />);

      const preset60 = screen.getByLabelText('Set interval to 60 min');
      fireEvent.click(preset60);

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        interval_minutes: 60,
      });
    });

    it('sets interval to 120 minutes when 2 hours preset clicked', () => {
      const value = {
        interval_minutes: 60,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: null,
      };

      render(<IntervalTriggerForm value={value} onChange={mockOnChange} />);

      const preset2h = screen.getByLabelText('Set interval to 2 hours');
      fireEvent.click(preset2h);

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        interval_minutes: 120,
      });
    });

    it('sets interval to 240 minutes when 4 hours preset clicked', () => {
      const value = {
        interval_minutes: 60,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: null,
      };

      render(<IntervalTriggerForm value={value} onChange={mockOnChange} />);

      const preset4h = screen.getByLabelText('Set interval to 4 hours');
      fireEvent.click(preset4h);

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        interval_minutes: 240,
      });
    });

    it('highlights selected preset', () => {
      const value = {
        interval_minutes: 60,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: null,
      };

      render(<IntervalTriggerForm value={value} onChange={mockOnChange} />);

      const preset60 = screen.getByLabelText('Set interval to 60 min');
      expect(preset60).toHaveClass('bg-blue-500');
    });
  });

  describe('TimeWindowInput Integration', () => {
    it('passes time_window value to TimeWindowInput', () => {
      const value = {
        interval_minutes: 60,
        time_window: {
          start_time: '21:00',
          end_time: '05:00',
          start_offset_minutes: 30,
          end_offset_minutes: -15,
        },
        days_of_week: null,
      };

      render(<IntervalTriggerForm value={value} onChange={mockOnChange} />);

      const startInput = screen.getByTestId('time-window-start');
      const endInput = screen.getByTestId('time-window-end');

      expect(startInput).toHaveValue('21:00');
      expect(endInput).toHaveValue('05:00');
    });

    it('calls onChange when TimeWindowInput changes', () => {
      const value = {
        interval_minutes: 60,
        time_window: {
          start_time: '21:00',
          end_time: '05:00',
        },
        days_of_week: null,
      };

      render(<IntervalTriggerForm value={value} onChange={mockOnChange} />);

      const startInput = screen.getByTestId('time-window-start');
      fireEvent.change(startInput, { target: { value: '20:00' } });

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        time_window: {
          ...value.time_window,
          start_time: '20:00',
        },
      });
    });

    it('passes errors to TimeWindowInput', () => {
      const errors = {
        time_window: {
          start_time: 'Invalid start time',
          end_time: 'Invalid end time',
        },
      };

      render(<IntervalTriggerForm onChange={mockOnChange} errors={errors} />);

      expect(screen.getByTestId('error-start')).toHaveTextContent('Invalid start time');
      expect(screen.getByTestId('error-end')).toHaveTextContent('Invalid end time');
    });

    it('passes disabled state to TimeWindowInput', () => {
      render(<IntervalTriggerForm onChange={mockOnChange} disabled={true} />);

      const startInput = screen.getByTestId('time-window-start');
      const endInput = screen.getByTestId('time-window-end');

      expect(startInput).toBeDisabled();
      expect(endInput).toBeDisabled();
    });
  });

  describe('DaysOfWeekSelector Integration', () => {
    it('passes days_of_week value to DaysOfWeekSelector', () => {
      const value = {
        interval_minutes: 60,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: [0, 2, 4], // Mon, Wed, Fri
      };

      render(<IntervalTriggerForm value={value} onChange={mockOnChange} />);

      expect(screen.getByTestId('days-of-week-selector')).toBeInTheDocument();
    });

    it('calls onChange when DaysOfWeekSelector changes', () => {
      const value = {
        interval_minutes: 60,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: null,
      };

      render(<IntervalTriggerForm value={value} onChange={mockOnChange} />);

      const mondayToggle = screen.getByTestId('toggle-monday');
      fireEvent.click(mondayToggle);

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        days_of_week: [1, 2, 3, 4, 5, 6], // All except Monday
      });
    });

    it('passes disabled state to DaysOfWeekSelector', () => {
      render(<IntervalTriggerForm onChange={mockOnChange} disabled={true} />);

      const mondayToggle = screen.getByTestId('toggle-monday');
      expect(mondayToggle).toBeDisabled();
    });
  });

  describe('Preview Text Generation', () => {
    it('generates preview for minutes interval with fixed time window', () => {
      const value = {
        interval_minutes: 30,
        time_window: {
          start_time: '21:00',
          end_time: '05:00',
        },
        days_of_week: null,
      };

      render(<IntervalTriggerForm value={value} onChange={mockOnChange} />);

      expect(screen.getByText('Every 30 minutes from 21:00 to 05:00')).toBeInTheDocument();
    });

    it('generates preview for hour interval', () => {
      const value = {
        interval_minutes: 120,
        time_window: {
          start_time: '21:00',
          end_time: '05:00',
        },
        days_of_week: null,
      };

      render(<IntervalTriggerForm value={value} onChange={mockOnChange} />);

      expect(screen.getByText('Every 2 hours from 21:00 to 05:00')).toBeInTheDocument();
    });

    it('generates preview with solar events', () => {
      const value = {
        interval_minutes: 60,
        time_window: {
          start_time: 'sunset',
          end_time: 'sunrise',
          start_offset_minutes: 30,
          end_offset_minutes: -15,
        },
        days_of_week: null,
      };

      render(<IntervalTriggerForm value={value} onChange={mockOnChange} />);

      // 60 minutes formats as "1 hour"
      expect(screen.getByText('Every 1 hour from sunset+30 to sunrise-15')).toBeInTheDocument();
    });

    it('generates preview with specific days', () => {
      const value = {
        interval_minutes: 60,
        time_window: {
          start_time: '21:00',
          end_time: '05:00',
        },
        days_of_week: [0, 2, 4], // Mon, Wed, Fri
      };

      render(<IntervalTriggerForm value={value} onChange={mockOnChange} />);

      // 60 minutes formats as "1 hour"
      expect(screen.getByText('Every 1 hour from 21:00 to 05:00 on Mon, Wed, Fri')).toBeInTheDocument();
    });

    it('generates preview without days when all days selected', () => {
      const value = {
        interval_minutes: 60,
        time_window: {
          start_time: '21:00',
          end_time: '05:00',
        },
        days_of_week: null,
      };

      render(<IntervalTriggerForm value={value} onChange={mockOnChange} />);

      // 60 minutes formats as "1 hour"
      expect(screen.getByText('Every 1 hour from 21:00 to 05:00')).toBeInTheDocument();
    });

    it('handles singular "minute" in preview', () => {
      const value = {
        interval_minutes: 1,
        time_window: {
          start_time: '21:00',
          end_time: '05:00',
        },
        days_of_week: null,
      };

      render(<IntervalTriggerForm value={value} onChange={mockOnChange} />);

      expect(screen.getByText('Every 1 minute from 21:00 to 05:00')).toBeInTheDocument();
    });

    it('handles singular "hour" in preview', () => {
      const value = {
        interval_minutes: 60,
        time_window: {
          start_time: '21:00',
          end_time: '05:00',
        },
        days_of_week: null,
      };

      render(<IntervalTriggerForm value={value} onChange={mockOnChange} />);

      // 60 minutes formats as "1 hour" (singular)
      expect(screen.getByText('Every 1 hour from 21:00 to 05:00')).toBeInTheDocument();
    });

    it('formats mixed hours and minutes in preview', () => {
      const value = {
        interval_minutes: 90, // 1h 30m
        time_window: {
          start_time: '21:00',
          end_time: '05:00',
        },
        days_of_week: null,
      };

      render(<IntervalTriggerForm value={value} onChange={mockOnChange} />);

      expect(screen.getByText('Every 1h 30m from 21:00 to 05:00')).toBeInTheDocument();
    });
  });

  describe('Disabled State', () => {
    it('disables interval input when disabled prop is true', () => {
      render(<IntervalTriggerForm onChange={mockOnChange} disabled={true} />);

      const intervalInput = screen.getByLabelText('Interval in minutes');
      expect(intervalInput).toBeDisabled();
    });

    it('disables preset buttons when disabled prop is true', () => {
      render(<IntervalTriggerForm onChange={mockOnChange} disabled={true} />);

      const preset15 = screen.getByLabelText('Set interval to 15 min');
      const preset30 = screen.getByLabelText('Set interval to 30 min');

      expect(preset15).toBeDisabled();
      expect(preset30).toBeDisabled();
    });

    it('does not disable inputs when disabled prop is false', () => {
      render(<IntervalTriggerForm onChange={mockOnChange} disabled={false} />);

      const intervalInput = screen.getByLabelText('Interval in minutes');
      expect(intervalInput).not.toBeDisabled();
    });
  });

  describe('Dark Mode Styling', () => {
    it('applies dark mode classes to interval input', () => {
      render(<IntervalTriggerForm onChange={mockOnChange} />);

      const intervalInput = screen.getByLabelText('Interval in minutes');
      expect(intervalInput).toHaveClass('dark:bg-gray-800', 'dark:text-white', 'dark:border-gray-600');
    });

    it('applies dark mode classes to preset buttons', () => {
      render(<IntervalTriggerForm onChange={mockOnChange} />);

      const preset15 = screen.getByLabelText('Set interval to 15 min');
      expect(preset15).toHaveClass('dark:bg-gray-700', 'dark:text-gray-300');
    });

    it('applies dark mode classes to labels', () => {
      render(<IntervalTriggerForm onChange={mockOnChange} />);

      const header = screen.getByText('Interval Configuration');
      expect(header).toHaveClass('dark:text-white');
    });

    it('applies dark mode classes to preview text', () => {
      const value = {
        interval_minutes: 60,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: null,
      };

      render(<IntervalTriggerForm value={value} onChange={mockOnChange} />);

      // 60 minutes formats as "1 hour"
      const previewText = screen.getByText('Every 1 hour from 21:00 to 05:00');
      expect(previewText).toHaveClass('dark:text-gray-400', 'dark:bg-gray-800');
    });
  });

  describe('onChange Callback', () => {
    it('calls onChange with complete trigger object when interval changes', () => {
      const value = {
        interval_minutes: 60,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: [0, 1, 2],
      };

      render(<IntervalTriggerForm value={value} onChange={mockOnChange} />);

      const intervalInput = screen.getByLabelText('Interval in minutes');
      fireEvent.change(intervalInput, { target: { value: '90' } });

      expect(mockOnChange).toHaveBeenCalledWith({
        interval_minutes: 90,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: [0, 1, 2],
      });
    });

    it('calls onChange with complete trigger object when time window changes', () => {
      const value = {
        interval_minutes: 60,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: null,
      };

      render(<IntervalTriggerForm value={value} onChange={mockOnChange} />);

      const startInput = screen.getByTestId('time-window-start');
      fireEvent.change(startInput, { target: { value: '20:00' } });

      expect(mockOnChange).toHaveBeenCalledWith({
        interval_minutes: 60,
        time_window: { start_time: '20:00', end_time: '05:00' },
        days_of_week: null,
      });
    });

    it('calls onChange with complete trigger object when days change', () => {
      const value = {
        interval_minutes: 60,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: null,
      };

      render(<IntervalTriggerForm value={value} onChange={mockOnChange} />);

      const allDaysButton = screen.getByTestId('toggle-all-days');
      fireEvent.click(allDaysButton);

      expect(mockOnChange).toHaveBeenCalledWith({
        interval_minutes: 60,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: null,
      });
    });
  });
});
