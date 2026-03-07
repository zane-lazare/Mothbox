import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import TriggerForm from '../TriggerForm';
import { TRIGGER_TYPES, TRIGGER_DEFAULTS } from '../constants';

// Mock all trigger form components
vi.mock('../IntervalTriggerForm', () => ({
  default: ({ value, onChange, disabled, errors }: any) => (
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
  default: ({ value, onChange, disabled }: any) => (
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
  default: ({ value, onChange, disabled }: any) => (
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
  default: ({ value, onChange, disabled }: any) => (
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
  default: ({ value, onChange, disabled }: any) => (
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

vi.mock('../RecurringDaysTriggerForm', () => ({
  default: ({ value, onChange, disabled }: any) => (
    <div data-testid="recurring-days-trigger-form">
      <span data-testid="recurring-days-value">{JSON.stringify(value)}</span>
      <button
        data-testid="recurring-days-change"
        onClick={() => onChange({ ...value, time: '21:00' })}
        disabled={disabled}
      >
        Change Recurring Days
      </button>
    </div>
  ),
}));

// Mock ExpertModeToggle
vi.mock('../../ExpertMode/ExpertModeToggle', () => ({
  default: ({ mode, onChange }: any) => (
    <div data-testid="expert-mode-toggle">
      <button
        data-testid="toggle-visual"
        onClick={() => onChange('visual')}
        aria-pressed={mode === 'visual'}
      >
        Visual
      </button>
      <button
        data-testid="toggle-expert"
        onClick={() => onChange('expert')}
        aria-pressed={mode === 'expert'}
      >
        Expert
      </button>
    </div>
  ),
}));

// Mock CronExpressionInput
vi.mock('../../ExpertMode/CronExpressionInput', () => ({
  default: ({ value, onChange, disabled }: any) => (
    <div data-testid="cron-expression-input">
      <input
        data-testid="cron-input"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
      />
    </div>
  ),
}));

describe('TriggerForm', () => {
  let mockOnChange: any;

  beforeEach(() => {
    mockOnChange = vi.fn();
  });

  describe('Rendering', () => {
    it('renders trigger type selector', () => {
      render(<TriggerForm onChange={mockOnChange} />);

      expect(screen.getByLabelText(/trigger type/i)).toBeInTheDocument();
    });

    it('renders all trigger type options except cron in visual mode', () => {
      render(<TriggerForm onChange={mockOnChange} />);

      const select = screen.getByLabelText(/trigger type/i);
      const options = Array.from((select as HTMLSelectElement).options).map((opt: HTMLOptionElement) => opt.value);

      // All trigger types except 'cron' should be in the select in visual mode
      Object.keys(TRIGGER_TYPES)
        .filter((type) => type !== 'cron')
        .forEach((type) => {
          expect(options).toContain(type);
        });

      // Cron should NOT be in the select in visual mode
      expect(options).not.toContain('cron');
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
      const value: any = {
        ...TRIGGER_DEFAULTS.solar,
        trigger_type: 'solar',
      };
      render(<TriggerForm value={value} onChange={mockOnChange} />);

      expect(screen.getByTestId('solar-trigger-form')).toBeInTheDocument();
      expect(screen.queryByTestId('interval-trigger-form')).not.toBeInTheDocument();
    });

    it('renders moon phase trigger form when trigger_type is moon_phase', () => {
      const value: any = {
        ...TRIGGER_DEFAULTS.moon_phase,
        trigger_type: 'moon_phase',
      };
      render(<TriggerForm value={value} onChange={mockOnChange} />);

      expect(screen.getByTestId('moon-phase-trigger-form')).toBeInTheDocument();
    });

    it('renders fixed time trigger form when trigger_type is fixed_time', () => {
      const value: any = {
        ...TRIGGER_DEFAULTS.fixed_time,
        trigger_type: 'fixed_time',
      };
      render(<TriggerForm value={value} onChange={mockOnChange} />);

      expect(screen.getByTestId('fixed-time-trigger-form')).toBeInTheDocument();
    });

    it('renders sensor trigger form when trigger_type is sensor', () => {
      const value: any = {
        ...TRIGGER_DEFAULTS.sensor,
        trigger_type: 'sensor',
      };
      render(<TriggerForm value={value} onChange={mockOnChange} />);

      expect(screen.getByTestId('sensor-trigger-form')).toBeInTheDocument();
    });

    it('renders recurring days trigger form when trigger_type is recurring_days', () => {
      const value: any = {
        ...TRIGGER_DEFAULTS.recurring_days,
        trigger_type: 'recurring_days',
      };
      render(<TriggerForm value={value} onChange={mockOnChange} />);

      expect(screen.getByTestId('recurring-days-trigger-form')).toBeInTheDocument();
    });

    it('shows description for solar trigger type', () => {
      const value: any = {
        ...TRIGGER_DEFAULTS.solar,
        trigger_type: 'solar',
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
      const value: any = {
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
      const value: any = {
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
      const value: any = {
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
      const value: any = {
        trigger_type: 'fixed_time',
        time_of_day: '12:00',
        days_of_week: null,
      };

      render(<TriggerForm value={value} onChange={mockOnChange} />);

      const fixedTimeValue = screen.getByTestId('fixed-time-value');
      expect(fixedTimeValue).toHaveTextContent('"time_of_day":"12:00"');
    });

    it('passes value to sensor trigger form', () => {
      const value: any = {
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

    it('passes value to recurring days trigger form', () => {
      const value: any = {
        trigger_type: 'recurring_days',
        days: [0, 5, 6],
        time: '20:00',
      };

      render(<TriggerForm value={value} onChange={mockOnChange} />);

      const recurringDaysValue = screen.getByTestId('recurring-days-value');
      expect(recurringDaysValue).toHaveTextContent('"days":[0,5,6]');
    });
  });

  describe('onChange Propagation', () => {
    it('propagates onChange from interval trigger form', () => {
      const value: any = {
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
      const value: any = {
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
      const value: any = {
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
      const value: any = {
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
      const value: any = {
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

    it('propagates onChange from recurring days trigger form', () => {
      const value: any = {
        trigger_type: 'recurring_days',
        days: [0, 5, 6],
        time: '20:00',
      };

      render(<TriggerForm value={value} onChange={mockOnChange} />);

      const changeButton = screen.getByTestId('recurring-days-change');
      fireEvent.click(changeButton);

      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({
          time: '21:00',
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
      const value: any = {
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
      const value: any = {
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
      const value: any = {
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
      expect(description).toHaveClass('dark:text-gray-300');
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

  describe('Expert Mode (Issue #233)', () => {
    it('renders expert mode toggle', () => {
      render(<TriggerForm onChange={mockOnChange} />);

      expect(screen.getByTestId('expert-mode-toggle')).toBeInTheDocument();
    });

    it('switches to cron input when expert mode enabled', () => {
      render(<TriggerForm onChange={mockOnChange} />);

      // Initially in visual mode
      expect(screen.getByTestId('interval-trigger-form')).toBeInTheDocument();
      expect(screen.queryByTestId('cron-expression-input')).not.toBeInTheDocument();

      // Switch to expert mode
      const expertButton = screen.getByTestId('toggle-expert');
      fireEvent.click(expertButton);

      // Should show cron input and hide trigger forms
      expect(screen.getByTestId('cron-expression-input')).toBeInTheDocument();
      expect(screen.queryByTestId('interval-trigger-form')).not.toBeInTheDocument();
    });

    it('preserves cron expression in trigger value', () => {
      const value: any = {
        trigger_type: 'cron',
        cron_expression: '*/5 * * * *',
      };

      render(<TriggerForm value={value} onChange={mockOnChange} />);

      const cronInput = screen.getByTestId('cron-input');
      expect(cronInput).toHaveValue('*/5 * * * *');
    });

    it('syncs expert mode with trigger_type cron', () => {
      const value: any = {
        trigger_type: 'cron' as const,
        cron_expression: '0 21 * * *',
      };

      render(<TriggerForm value={value} onChange={mockOnChange} />);

      // Should be in expert mode
      const expertButton = screen.getByTestId('toggle-expert');
      expect(expertButton).toHaveAttribute('aria-pressed', 'true');

      // Should show cron input
      expect(screen.getByTestId('cron-expression-input')).toBeInTheDocument();
    });

    it('calls onChange with cron_expression when changed', () => {
      const value: any = {
        trigger_type: 'cron' as const,
        cron_expression: '0 21 * * *',
      };

      render(<TriggerForm value={value} onChange={mockOnChange} />);

      const cronInput = screen.getByTestId('cron-input');
      fireEvent.change(cronInput, { target: { value: '0 */2 * * *' } });

      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({
          trigger_type: 'cron',
          cron_expression: '0 */2 * * *',
        })
      );
    });

    it('switches back to visual mode when clicking visual button', () => {
      const value: any = {
        trigger_type: 'cron' as const,
        cron_expression: '0 21 * * *',
      };

      render(<TriggerForm value={value} onChange={mockOnChange} />);

      // Initially in expert mode
      expect(screen.getByTestId('cron-expression-input')).toBeInTheDocument();

      // Switch to visual mode
      const visualButton = screen.getByTestId('toggle-visual');
      fireEvent.click(visualButton);

      // Should call onChange with interval defaults
      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({
          trigger_type: 'interval',
        })
      );
    });

    it('hides trigger type selector in expert mode', () => {
      render(<TriggerForm onChange={mockOnChange} />);

      // Initially shows trigger type selector
      expect(screen.getByLabelText(/trigger type/i)).toBeInTheDocument();

      // Switch to expert mode
      const expertButton = screen.getByTestId('toggle-expert');
      fireEvent.click(expertButton);

      // Should hide trigger type selector
      expect(screen.queryByLabelText(/trigger type/i)).not.toBeInTheDocument();
    });
  });
});
