import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import TriggerForm from '../TriggerForm';
import { TRIGGER_TYPES, TRIGGER_DEFAULTS } from '../constants';

// Mock all trigger form components
vi.mock('../IntervalTriggerForm', () => ({
  default: ({ value, onChange, disabled, errors }) => (
    <div data-testid="interval-trigger-form">
      <span data-testid="interval-value">{JSON.stringify(value)}</span>
      <button
        data-testid="interval-change"
        onClick={() => onChange({ ...value, interval_minutes: 90 })}
        disabled={disabled}
      >
        Change Interval
      </button>
      {errors?.interval_minutes && (
        <span data-testid="interval-error">{errors.interval_minutes}</span>
      )}
    </div>
  ),
}));

vi.mock('../SolarTriggerForm', () => ({
  default: ({ value, onChange, disabled }) => (
    <div data-testid="solar-trigger-form">
      <span data-testid="solar-value">{JSON.stringify(value)}</span>
      <button
        data-testid="solar-change"
        onClick={() => onChange({ ...value, solar_event: 'sunrise' })}
        disabled={disabled}
      >
        Change Solar
      </button>
    </div>
  ),
}));

vi.mock('../MoonPhaseTriggerForm', () => ({
  default: ({ value, onChange, disabled }) => (
    <div data-testid="moon-phase-trigger-form">
      <span data-testid="moon-value">{JSON.stringify(value)}</span>
      <button
        data-testid="moon-change"
        onClick={() => onChange({ ...value, moon_phase: 'new' })}
        disabled={disabled}
      >
        Change Moon
      </button>
    </div>
  ),
}));

vi.mock('../FixedTimeTriggerForm', () => ({
  default: ({ value, onChange, disabled }) => (
    <div data-testid="fixed-time-trigger-form">
      <span data-testid="fixed-time-value">{JSON.stringify(value)}</span>
      <button
        data-testid="fixed-time-change"
        onClick={() => onChange({ ...value, time_of_day: '18:00' })}
        disabled={disabled}
      >
        Change Fixed Time
      </button>
    </div>
  ),
}));

vi.mock('../SensorTriggerForm', () => ({
  default: ({ value, onChange, disabled }) => (
    <div data-testid="sensor-trigger-form">
      <span data-testid="sensor-value">{JSON.stringify(value)}</span>
      <button
        data-testid="sensor-change"
        onClick={() => onChange({ ...value, threshold: 200 })}
        disabled={disabled}
      >
        Change Sensor
      </button>
    </div>
  ),
}));

describe('TriggerForm', () => {
  let mockOnChange;

  beforeEach(() => {
    mockOnChange = vi.fn();
  });

  describe('Rendering', () => {
    it('renders trigger type selector', () => {
      render(<TriggerForm onChange={mockOnChange} />);

      expect(screen.getByLabelText(/trigger type/i)).toBeInTheDocument();
    });

    it('renders all trigger type options', () => {
      render(<TriggerForm onChange={mockOnChange} />);

      const select = screen.getByLabelText(/trigger type/i);
      const options = Array.from(select.options).map((opt) => opt.value);

      Object.keys(TRIGGER_TYPES).forEach((type) => {
        expect(options).toContain(type);
      });
    });

    it('renders with default interval trigger type', () => {
      render(<TriggerForm onChange={mockOnChange} />);

      expect(screen.getByTestId('interval-trigger-form')).toBeInTheDocument();
    });

    it('renders trigger type descriptions', () => {
      render(<TriggerForm onChange={mockOnChange} />);

      // Check that the description for the default (interval) trigger is shown
      expect(screen.getByText(TRIGGER_TYPES.interval.description)).toBeInTheDocument();
    });
  });

  describe('Trigger Type Selection', () => {
    it('renders solar trigger form when trigger_type is solar', () => {
      const value = {
        trigger_type: 'solar',
        ...TRIGGER_DEFAULTS.solar,
      };
      render(<TriggerForm value={value} onChange={mockOnChange} />);

      expect(screen.getByTestId('solar-trigger-form')).toBeInTheDocument();
      expect(screen.queryByTestId('interval-trigger-form')).not.toBeInTheDocument();
    });

    it('renders moon phase trigger form when trigger_type is moon_phase', () => {
      const value = {
        trigger_type: 'moon_phase',
        ...TRIGGER_DEFAULTS.moon_phase,
      };
      render(<TriggerForm value={value} onChange={mockOnChange} />);

      expect(screen.getByTestId('moon-phase-trigger-form')).toBeInTheDocument();
    });

    it('renders fixed time trigger form when trigger_type is fixed_time', () => {
      const value = {
        trigger_type: 'fixed_time',
        ...TRIGGER_DEFAULTS.fixed_time,
      };
      render(<TriggerForm value={value} onChange={mockOnChange} />);

      expect(screen.getByTestId('fixed-time-trigger-form')).toBeInTheDocument();
    });

    it('renders sensor trigger form when trigger_type is sensor', () => {
      const value = {
        trigger_type: 'sensor',
        ...TRIGGER_DEFAULTS.sensor,
      };
      render(<TriggerForm value={value} onChange={mockOnChange} />);

      expect(screen.getByTestId('sensor-trigger-form')).toBeInTheDocument();
    });

    it('shows description for solar trigger type', () => {
      const value = {
        trigger_type: 'solar',
        ...TRIGGER_DEFAULTS.solar,
      };
      render(<TriggerForm value={value} onChange={mockOnChange} />);

      expect(screen.getByText(TRIGGER_TYPES.solar.description)).toBeInTheDocument();
    });

    it('calls onChange with default values when trigger type changed', () => {
      render(<TriggerForm onChange={mockOnChange} />);

      const select = screen.getByLabelText(/trigger type/i);
      fireEvent.change(select, { target: { value: 'solar' } });

      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({
          trigger_type: 'solar',
        })
      );
    });
  });

  describe('Value Propagation', () => {
    it('passes value to interval trigger form', () => {
      const value = {
        trigger_type: 'interval',
        interval_minutes: 120,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: null,
      };

      render(<TriggerForm value={value} onChange={mockOnChange} />);

      const intervalValue = screen.getByTestId('interval-value');
      expect(intervalValue).toHaveTextContent('"interval_minutes":120');
    });

    it('passes value to solar trigger form', () => {
      const value = {
        trigger_type: 'solar',
        solar_event: 'sunrise',
        offset_minutes: 30,
        days_of_week: [0, 1, 2],
      };

      render(<TriggerForm value={value} onChange={mockOnChange} />);

      const solarValue = screen.getByTestId('solar-value');
      expect(solarValue).toHaveTextContent('"solar_event":"sunrise"');
    });

    it('passes value to moon phase trigger form', () => {
      const value = {
        trigger_type: 'moon_phase',
        moon_phase: 'full',
        time_of_day: '20:00',
        offset_days: 0,
      };

      render(<TriggerForm value={value} onChange={mockOnChange} />);

      const moonValue = screen.getByTestId('moon-value');
      expect(moonValue).toHaveTextContent('"moon_phase":"full"');
    });

    it('passes value to fixed time trigger form', () => {
      const value = {
        trigger_type: 'fixed_time',
        time_of_day: '12:00',
        days_of_week: null,
      };

      render(<TriggerForm value={value} onChange={mockOnChange} />);

      const fixedTimeValue = screen.getByTestId('fixed-time-value');
      expect(fixedTimeValue).toHaveTextContent('"time_of_day":"12:00"');
    });

    it('passes value to sensor trigger form', () => {
      const value = {
        trigger_type: 'sensor',
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      };

      render(<TriggerForm value={value} onChange={mockOnChange} />);

      const sensorValue = screen.getByTestId('sensor-value');
      expect(sensorValue).toHaveTextContent('"sensor_type":"light"');
    });
  });

  describe('onChange Propagation', () => {
    it('propagates onChange from interval trigger form', () => {
      const value = {
        trigger_type: 'interval',
        interval_minutes: 60,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: null,
      };

      render(<TriggerForm value={value} onChange={mockOnChange} />);

      const changeButton = screen.getByTestId('interval-change');
      fireEvent.click(changeButton);

      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({
          interval_minutes: 90,
        })
      );
    });

    it('propagates onChange from solar trigger form', () => {
      const value = {
        trigger_type: 'solar',
        solar_event: 'sunset',
        offset_minutes: 0,
        days_of_week: null,
      };

      render(<TriggerForm value={value} onChange={mockOnChange} />);

      const changeButton = screen.getByTestId('solar-change');
      fireEvent.click(changeButton);

      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({
          solar_event: 'sunrise',
        })
      );
    });

    it('propagates onChange from moon phase trigger form', () => {
      const value = {
        trigger_type: 'moon_phase',
        moon_phase: 'full',
        time_of_day: '20:00',
        offset_days: 0,
      };

      render(<TriggerForm value={value} onChange={mockOnChange} />);

      const changeButton = screen.getByTestId('moon-change');
      fireEvent.click(changeButton);

      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({
          moon_phase: 'new',
        })
      );
    });

    it('propagates onChange from fixed time trigger form', () => {
      const value = {
        trigger_type: 'fixed_time',
        time_of_day: '12:00',
        days_of_week: null,
      };

      render(<TriggerForm value={value} onChange={mockOnChange} />);

      const changeButton = screen.getByTestId('fixed-time-change');
      fireEvent.click(changeButton);

      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({
          time_of_day: '18:00',
        })
      );
    });

    it('propagates onChange from sensor trigger form', () => {
      const value = {
        trigger_type: 'sensor',
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      };

      render(<TriggerForm value={value} onChange={mockOnChange} />);

      const changeButton = screen.getByTestId('sensor-change');
      fireEvent.click(changeButton);

      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({
          threshold: 200,
        })
      );
    });
  });

  describe('Disabled State', () => {
    it('disables trigger type selector when disabled', () => {
      render(<TriggerForm onChange={mockOnChange} disabled={true} />);

      const select = screen.getByLabelText(/trigger type/i);
      expect(select).toBeDisabled();
    });

    it('passes disabled state to interval trigger form', () => {
      const value = {
        trigger_type: 'interval',
        interval_minutes: 60,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: null,
      };

      render(<TriggerForm value={value} onChange={mockOnChange} disabled={true} />);

      const changeButton = screen.getByTestId('interval-change');
      expect(changeButton).toBeDisabled();
    });

    it('passes disabled state to solar trigger form', () => {
      const value = {
        trigger_type: 'solar',
        solar_event: 'sunset',
        offset_minutes: 0,
        days_of_week: null,
      };

      render(<TriggerForm value={value} onChange={mockOnChange} disabled={true} />);

      const changeButton = screen.getByTestId('solar-change');
      expect(changeButton).toBeDisabled();
    });
  });

  describe('Error Propagation', () => {
    it('passes errors to interval trigger form', () => {
      const value = {
        trigger_type: 'interval',
        interval_minutes: 60,
        time_window: { start_time: '21:00', end_time: '05:00' },
        days_of_week: null,
      };
      const errors = {
        interval_minutes: 'Invalid interval',
      };

      render(<TriggerForm value={value} onChange={mockOnChange} errors={errors} />);

      expect(screen.getByTestId('interval-error')).toHaveTextContent('Invalid interval');
    });
  });

  describe('Dark Mode Styling', () => {
    it('applies dark mode classes to trigger type selector', () => {
      render(<TriggerForm onChange={mockOnChange} />);

      const select = screen.getByLabelText(/trigger type/i);
      expect(select).toHaveClass('dark:bg-gray-800', 'dark:text-white', 'dark:border-gray-600');
    });

    it('applies dark mode classes to header', () => {
      render(<TriggerForm onChange={mockOnChange} />);

      const header = screen.getByText('Trigger Configuration');
      expect(header).toHaveClass('dark:text-white');
    });

    it('applies dark mode classes to description', () => {
      render(<TriggerForm onChange={mockOnChange} />);

      const description = screen.getByText(TRIGGER_TYPES.interval.description);
      expect(description).toHaveClass('dark:text-gray-400');
    });
  });

  describe('Default Values', () => {
    it('uses interval defaults when no value provided', () => {
      render(<TriggerForm onChange={mockOnChange} />);

      const intervalValue = screen.getByTestId('interval-value');
      expect(intervalValue).toHaveTextContent('"interval_minutes"');
    });

    it('provides default values when switching trigger types', () => {
      render(<TriggerForm onChange={mockOnChange} />);

      const select = screen.getByLabelText(/trigger type/i);
      fireEvent.change(select, { target: { value: 'solar' } });

      // Should call onChange with solar defaults
      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({
          trigger_type: 'solar',
          solar_event: expect.any(String),
          offset_minutes: expect.any(Number),
        })
      );
    });
  });
});
