import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import SolarTriggerForm from '../SolarTriggerForm';
import { SOLAR_EVENTS, SCHEDULE_LIMITS } from '../constants';

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

describe('SolarTriggerForm', () => {
  let mockOnChange;

  beforeEach(() => {
    mockOnChange = vi.fn();
  });

  describe('Rendering', () => {
    it('renders with default values', () => {
      render(<SolarTriggerForm onChange={mockOnChange} />);

      expect(screen.getByText('Solar Event Configuration')).toBeInTheDocument();
      expect(screen.getByLabelText(/solar event/i)).toBeInTheDocument();
      expect(screen.getByLabelText('Offset in minutes')).toBeInTheDocument();
      expect(screen.getByText('Preview:')).toBeInTheDocument();
    });

    it('renders with provided value', () => {
      const value = {
        solar_event: 'sunrise',
        offset_minutes: 30,
        days_of_week: [0, 1, 2],
      };

      render(<SolarTriggerForm value={value} onChange={mockOnChange} />);

      const solarEventSelect = screen.getByLabelText(/solar event/i);
      expect(solarEventSelect).toHaveValue('sunrise');

      const offsetInput = screen.getByLabelText('Offset in minutes');
      expect(offsetInput).toHaveValue(30);
    });

    it('renders all solar events in dropdown', () => {
      render(<SolarTriggerForm onChange={mockOnChange} />);

      const solarEventSelect = screen.getByLabelText(/solar event/i);
      const options = Array.from(solarEventSelect.options).map((opt) => opt.value);

      SOLAR_EVENTS.forEach((event) => {
        expect(options).toContain(event.value);
      });
    });

    it('renders DaysOfWeekSelector component', () => {
      render(<SolarTriggerForm onChange={mockOnChange} />);

      expect(screen.getByTestId('days-of-week-selector')).toBeInTheDocument();
    });
  });

  describe('Solar Event Selection', () => {
    it('updates solar_event on selection change', () => {
      const value = {
        solar_event: 'sunset',
        offset_minutes: 0,
        days_of_week: null,
      };

      render(<SolarTriggerForm value={value} onChange={mockOnChange} />);

      const solarEventSelect = screen.getByLabelText(/solar event/i);
      fireEvent.change(solarEventSelect, { target: { value: 'sunrise' } });

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        solar_event: 'sunrise',
      });
    });

    it('shows description for selected solar event', () => {
      const value = {
        solar_event: 'sunset',
        offset_minutes: 0,
        days_of_week: null,
      };

      render(<SolarTriggerForm value={value} onChange={mockOnChange} />);

      const sunsetEvent = SOLAR_EVENTS.find((e) => e.value === 'sunset');
      expect(screen.getByText(sunsetEvent.description)).toBeInTheDocument();
    });

    it('updates description when solar event changes', () => {
      const value = {
        solar_event: 'sunset',
        offset_minutes: 0,
        days_of_week: null,
      };

      const { rerender } = render(
        <SolarTriggerForm value={value} onChange={mockOnChange} />
      );

      // Verify sunset description shows
      const sunsetEvent = SOLAR_EVENTS.find((e) => e.value === 'sunset');
      expect(screen.getByText(sunsetEvent.description)).toBeInTheDocument();

      // Change to sunrise
      const newValue = { ...value, solar_event: 'sunrise' };
      rerender(<SolarTriggerForm value={newValue} onChange={mockOnChange} />);

      // Verify sunrise description shows
      const sunriseEvent = SOLAR_EVENTS.find((e) => e.value === 'sunrise');
      expect(screen.getByText(sunriseEvent.description)).toBeInTheDocument();
    });
  });

  describe('Offset Input', () => {
    it('updates offset_minutes on input change', () => {
      const value = {
        solar_event: 'sunset',
        offset_minutes: 0,
        days_of_week: null,
      };

      render(<SolarTriggerForm value={value} onChange={mockOnChange} />);

      const offsetInput = screen.getByLabelText('Offset in minutes');
      fireEvent.change(offsetInput, { target: { value: '30' } });

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        offset_minutes: 30,
      });
    });

    it('allows negative offset values', () => {
      const value = {
        solar_event: 'sunset',
        offset_minutes: 0,
        days_of_week: null,
      };

      render(<SolarTriggerForm value={value} onChange={mockOnChange} />);

      const offsetInput = screen.getByLabelText('Offset in minutes');
      fireEvent.change(offsetInput, { target: { value: '-30' } });

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        offset_minutes: -30,
      });
    });

    it('respects min and max offset limits', () => {
      render(<SolarTriggerForm onChange={mockOnChange} />);

      const offsetInput = screen.getByLabelText('Offset in minutes');
      expect(offsetInput).toHaveAttribute('min', String(-SCHEDULE_LIMITS.MAX_OFFSET_MINUTES));
      expect(offsetInput).toHaveAttribute('max', String(SCHEDULE_LIMITS.MAX_OFFSET_MINUTES));
    });

    it('shows error message for invalid offset', () => {
      const errors = {
        offset_minutes: 'Offset must be between -1440 and 1440 minutes',
      };

      render(<SolarTriggerForm onChange={mockOnChange} errors={errors} />);

      expect(screen.getByText(errors.offset_minutes)).toBeInTheDocument();
    });
  });

  describe('Numeric Input Validation', () => {
    it('does not call onChange for NaN input', () => {
      const value = {
        solar_event: 'sunset',
        offset_minutes: 0,
        days_of_week: null,
      };

      render(<SolarTriggerForm value={value} onChange={mockOnChange} />);

      const offsetInput = screen.getByLabelText('Offset in minutes');
      fireEvent.change(offsetInput, { target: { value: 'abc' } });

      expect(mockOnChange).not.toHaveBeenCalled();
    });

    it('does not call onChange for empty input', () => {
      const value = {
        solar_event: 'sunset',
        offset_minutes: 30,
        days_of_week: null,
      };

      render(<SolarTriggerForm value={value} onChange={mockOnChange} />);

      const offsetInput = screen.getByLabelText('Offset in minutes');
      fireEvent.change(offsetInput, { target: { value: '' } });

      expect(mockOnChange).not.toHaveBeenCalled();
    });

    it('does not call onChange for values below minimum', () => {
      const value = {
        solar_event: 'sunset',
        offset_minutes: 0,
        days_of_week: null,
      };

      render(<SolarTriggerForm value={value} onChange={mockOnChange} />);

      const offsetInput = screen.getByLabelText('Offset in minutes');
      fireEvent.change(offsetInput, { target: { value: String(-SCHEDULE_LIMITS.MAX_OFFSET_MINUTES - 1) } });

      expect(mockOnChange).not.toHaveBeenCalled();
    });

    it('does not call onChange for values above maximum', () => {
      const value = {
        solar_event: 'sunset',
        offset_minutes: 0,
        days_of_week: null,
      };

      render(<SolarTriggerForm value={value} onChange={mockOnChange} />);

      const offsetInput = screen.getByLabelText('Offset in minutes');
      fireEvent.change(offsetInput, { target: { value: String(SCHEDULE_LIMITS.MAX_OFFSET_MINUTES + 1) } });

      expect(mockOnChange).not.toHaveBeenCalled();
    });

    it('accepts valid values within symmetric range (negative)', () => {
      const value = {
        solar_event: 'sunset',
        offset_minutes: 0,
        days_of_week: null,
      };

      render(<SolarTriggerForm value={value} onChange={mockOnChange} />);

      const offsetInput = screen.getByLabelText('Offset in minutes');
      fireEvent.change(offsetInput, { target: { value: '-720' } });

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        offset_minutes: -720,
      });
    });

    it('accepts boundary value at minimum', () => {
      const value = {
        solar_event: 'sunset',
        offset_minutes: 0,
        days_of_week: null,
      };

      render(<SolarTriggerForm value={value} onChange={mockOnChange} />);

      const offsetInput = screen.getByLabelText('Offset in minutes');
      fireEvent.change(offsetInput, { target: { value: String(-SCHEDULE_LIMITS.MAX_OFFSET_MINUTES) } });

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        offset_minutes: -SCHEDULE_LIMITS.MAX_OFFSET_MINUTES,
      });
    });

    it('accepts boundary value at zero', () => {
      const value = {
        solar_event: 'sunset',
        offset_minutes: 30,
        days_of_week: null,
      };

      render(<SolarTriggerForm value={value} onChange={mockOnChange} />);

      const offsetInput = screen.getByLabelText('Offset in minutes');
      fireEvent.change(offsetInput, { target: { value: '0' } });

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        offset_minutes: 0,
      });
    });

    it('accepts boundary value at maximum', () => {
      const value = {
        solar_event: 'sunset',
        offset_minutes: 0,
        days_of_week: null,
      };

      render(<SolarTriggerForm value={value} onChange={mockOnChange} />);

      const offsetInput = screen.getByLabelText('Offset in minutes');
      fireEvent.change(offsetInput, { target: { value: String(SCHEDULE_LIMITS.MAX_OFFSET_MINUTES) } });

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        offset_minutes: SCHEDULE_LIMITS.MAX_OFFSET_MINUTES,
      });
    });
  });

  describe('Quick Offset Presets', () => {
    it('renders quick offset preset buttons', () => {
      render(<SolarTriggerForm onChange={mockOnChange} />);

      expect(screen.getByLabelText('Set offset to -60 minutes')).toBeInTheDocument();
      expect(screen.getByLabelText('Set offset to -30 minutes')).toBeInTheDocument();
      expect(screen.getByLabelText('Set offset to 0 minutes')).toBeInTheDocument();
      expect(screen.getByLabelText('Set offset to +30 minutes')).toBeInTheDocument();
      expect(screen.getByLabelText('Set offset to +60 minutes')).toBeInTheDocument();
    });

    it('sets offset to -60 when -1h preset clicked', () => {
      const value = {
        solar_event: 'sunset',
        offset_minutes: 0,
        days_of_week: null,
      };

      render(<SolarTriggerForm value={value} onChange={mockOnChange} />);

      const presetNeg60 = screen.getByLabelText('Set offset to -60 minutes');
      fireEvent.click(presetNeg60);

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        offset_minutes: -60,
      });
    });

    it('sets offset to 0 when "No offset" preset clicked', () => {
      const value = {
        solar_event: 'sunset',
        offset_minutes: 30,
        days_of_week: null,
      };

      render(<SolarTriggerForm value={value} onChange={mockOnChange} />);

      const presetZero = screen.getByLabelText('Set offset to 0 minutes');
      fireEvent.click(presetZero);

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        offset_minutes: 0,
      });
    });

    it('sets offset to +30 when +30m preset clicked', () => {
      const value = {
        solar_event: 'sunset',
        offset_minutes: 0,
        days_of_week: null,
      };

      render(<SolarTriggerForm value={value} onChange={mockOnChange} />);

      const presetPos30 = screen.getByLabelText('Set offset to +30 minutes');
      fireEvent.click(presetPos30);

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        offset_minutes: 30,
      });
    });

    it('highlights selected preset', () => {
      const value = {
        solar_event: 'sunset',
        offset_minutes: 30,
        days_of_week: null,
      };

      render(<SolarTriggerForm value={value} onChange={mockOnChange} />);

      const presetPos30 = screen.getByLabelText('Set offset to +30 minutes');
      expect(presetPos30).toHaveClass('bg-blue-500');
    });
  });

  describe('DaysOfWeekSelector Integration', () => {
    it('passes days_of_week value to DaysOfWeekSelector', () => {
      const value = {
        solar_event: 'sunset',
        offset_minutes: 0,
        days_of_week: [0, 2, 4],
      };

      render(<SolarTriggerForm value={value} onChange={mockOnChange} />);

      expect(screen.getByTestId('days-of-week-selector')).toBeInTheDocument();
    });

    it('calls onChange when DaysOfWeekSelector changes', () => {
      const value = {
        solar_event: 'sunset',
        offset_minutes: 0,
        days_of_week: null,
      };

      render(<SolarTriggerForm value={value} onChange={mockOnChange} />);

      const mondayToggle = screen.getByTestId('toggle-monday');
      fireEvent.click(mondayToggle);

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        days_of_week: [1, 2, 3, 4, 5, 6],
      });
    });

    it('passes disabled state to DaysOfWeekSelector', () => {
      render(<SolarTriggerForm onChange={mockOnChange} disabled={true} />);

      const mondayToggle = screen.getByTestId('toggle-monday');
      expect(mondayToggle).toBeDisabled();
    });
  });

  describe('Preview Text Generation', () => {
    it('generates preview for solar event without offset', () => {
      const value = {
        solar_event: 'sunset',
        offset_minutes: 0,
        days_of_week: null,
      };

      render(<SolarTriggerForm value={value} onChange={mockOnChange} />);

      expect(screen.getByText('At sunset')).toBeInTheDocument();
    });

    it('generates preview with positive offset', () => {
      const value = {
        solar_event: 'sunset',
        offset_minutes: 30,
        days_of_week: null,
      };

      render(<SolarTriggerForm value={value} onChange={mockOnChange} />);

      expect(screen.getByText('30 minutes after sunset')).toBeInTheDocument();
    });

    it('generates preview with negative offset', () => {
      const value = {
        solar_event: 'sunset',
        offset_minutes: -30,
        days_of_week: null,
      };

      render(<SolarTriggerForm value={value} onChange={mockOnChange} />);

      expect(screen.getByText('30 minutes before sunset')).toBeInTheDocument();
    });

    it('generates preview with specific days', () => {
      const value = {
        solar_event: 'sunset',
        offset_minutes: 0,
        days_of_week: [0, 2, 4],
      };

      render(<SolarTriggerForm value={value} onChange={mockOnChange} />);

      expect(screen.getByText('At sunset on Mon, Wed, Fri')).toBeInTheDocument();
    });

    it('generates preview with offset and days', () => {
      const value = {
        solar_event: 'sunrise',
        offset_minutes: -15,
        days_of_week: [5, 6],
      };

      render(<SolarTriggerForm value={value} onChange={mockOnChange} />);

      expect(screen.getByText('15 minutes before sunrise on Sat, Sun')).toBeInTheDocument();
    });

    it('handles large offsets in hours format', () => {
      const value = {
        solar_event: 'sunset',
        offset_minutes: 120,
        days_of_week: null,
      };

      render(<SolarTriggerForm value={value} onChange={mockOnChange} />);

      expect(screen.getByText('2 hours after sunset')).toBeInTheDocument();
    });

    it('handles mixed hours and minutes in preview', () => {
      const value = {
        solar_event: 'sunset',
        offset_minutes: 90,
        days_of_week: null,
      };

      render(<SolarTriggerForm value={value} onChange={mockOnChange} />);

      expect(screen.getByText('1h 30m after sunset')).toBeInTheDocument();
    });
  });

  describe('Disabled State', () => {
    it('disables solar event select when disabled prop is true', () => {
      render(<SolarTriggerForm onChange={mockOnChange} disabled={true} />);

      const solarEventSelect = screen.getByLabelText(/solar event/i);
      expect(solarEventSelect).toBeDisabled();
    });

    it('disables offset input when disabled prop is true', () => {
      render(<SolarTriggerForm onChange={mockOnChange} disabled={true} />);

      const offsetInput = screen.getByLabelText('Offset in minutes');
      expect(offsetInput).toBeDisabled();
    });

    it('disables preset buttons when disabled prop is true', () => {
      render(<SolarTriggerForm onChange={mockOnChange} disabled={true} />);

      const presetZero = screen.getByLabelText('Set offset to 0 minutes');
      expect(presetZero).toBeDisabled();
    });

    it('does not disable inputs when disabled prop is false', () => {
      render(<SolarTriggerForm onChange={mockOnChange} disabled={false} />);

      const solarEventSelect = screen.getByLabelText(/solar event/i);
      const offsetInput = screen.getByLabelText('Offset in minutes');

      expect(solarEventSelect).not.toBeDisabled();
      expect(offsetInput).not.toBeDisabled();
    });
  });

  describe('Dark Mode Styling', () => {
    it('applies dark mode classes to solar event select', () => {
      render(<SolarTriggerForm onChange={mockOnChange} />);

      const solarEventSelect = screen.getByLabelText(/solar event/i);
      expect(solarEventSelect).toHaveClass('dark:bg-gray-800', 'dark:text-white', 'dark:border-gray-600');
    });

    it('applies dark mode classes to offset input', () => {
      render(<SolarTriggerForm onChange={mockOnChange} />);

      const offsetInput = screen.getByLabelText('Offset in minutes');
      expect(offsetInput).toHaveClass('dark:bg-gray-800', 'dark:text-white', 'dark:border-gray-600');
    });

    it('applies dark mode classes to labels', () => {
      render(<SolarTriggerForm onChange={mockOnChange} />);

      const header = screen.getByText('Solar Event Configuration');
      expect(header).toHaveClass('dark:text-white');
    });

    it('applies dark mode classes to preset buttons', () => {
      render(<SolarTriggerForm onChange={mockOnChange} />);

      // Test non-selected preset button (default offset is 0, so +30m is not selected)
      const presetPlus30 = screen.getByLabelText('Set offset to +30 minutes');
      expect(presetPlus30).toHaveClass('dark:bg-gray-700', 'dark:text-gray-300');
    });

    it('applies dark mode classes to preview text', () => {
      const value = {
        solar_event: 'sunset',
        offset_minutes: 0,
        days_of_week: null,
      };

      render(<SolarTriggerForm value={value} onChange={mockOnChange} />);

      const previewText = screen.getByText('At sunset');
      expect(previewText).toHaveClass('dark:text-gray-300', 'dark:bg-gray-800');
    });
  });

  describe('onChange Callback', () => {
    it('calls onChange with complete trigger object when event changes', () => {
      const value = {
        solar_event: 'sunset',
        offset_minutes: 30,
        days_of_week: [0, 1, 2],
      };

      render(<SolarTriggerForm value={value} onChange={mockOnChange} />);

      const solarEventSelect = screen.getByLabelText(/solar event/i);
      fireEvent.change(solarEventSelect, { target: { value: 'sunrise' } });

      expect(mockOnChange).toHaveBeenCalledWith({
        solar_event: 'sunrise',
        offset_minutes: 30,
        days_of_week: [0, 1, 2],
      });
    });

    it('calls onChange with complete trigger object when offset changes', () => {
      const value = {
        solar_event: 'sunset',
        offset_minutes: 0,
        days_of_week: null,
      };

      render(<SolarTriggerForm value={value} onChange={mockOnChange} />);

      const offsetInput = screen.getByLabelText('Offset in minutes');
      fireEvent.change(offsetInput, { target: { value: '45' } });

      expect(mockOnChange).toHaveBeenCalledWith({
        solar_event: 'sunset',
        offset_minutes: 45,
        days_of_week: null,
      });
    });

    it('calls onChange with complete trigger object when days change', () => {
      const value = {
        solar_event: 'sunset',
        offset_minutes: 0,
        days_of_week: null,
      };

      render(<SolarTriggerForm value={value} onChange={mockOnChange} />);

      const allDaysButton = screen.getByTestId('toggle-all-days');
      fireEvent.click(allDaysButton);

      expect(mockOnChange).toHaveBeenCalledWith({
        solar_event: 'sunset',
        offset_minutes: 0,
        days_of_week: null,
      });
    });
  });
});
