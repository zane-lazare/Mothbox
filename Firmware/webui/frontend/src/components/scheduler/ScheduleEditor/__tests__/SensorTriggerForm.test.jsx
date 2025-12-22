import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import SensorTriggerForm from '../SensorTriggerForm';
import { SENSOR_TYPES, SENSOR_COMPARISONS, SCHEDULE_LIMITS } from '../constants';

describe('SensorTriggerForm', () => {
  let mockOnChange;

  beforeEach(() => {
    mockOnChange = vi.fn();
  });

  describe('Rendering', () => {
    it('renders with default values', () => {
      render(<SensorTriggerForm onChange={mockOnChange} />);

      expect(screen.getByText('Sensor Configuration')).toBeInTheDocument();
      expect(screen.getByLabelText(/sensor type/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/comparison/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/threshold/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/cooldown.*minutes/i)).toBeInTheDocument();
      expect(screen.getByText('Preview:')).toBeInTheDocument();
    });

    it('renders with provided value', () => {
      const value = {
        sensor_type: 'temperature',
        comparison: 'gte',
        threshold: 25,
        cooldown_minutes: 10,
      };

      render(<SensorTriggerForm value={value} onChange={mockOnChange} />);

      const sensorTypeSelect = screen.getByLabelText(/sensor type/i);
      expect(sensorTypeSelect).toHaveValue('temperature');

      const comparisonSelect = screen.getByLabelText(/comparison/i);
      expect(comparisonSelect).toHaveValue('gte');

      const thresholdInput = screen.getByLabelText(/threshold/i);
      expect(thresholdInput).toHaveValue(25);

      const cooldownInput = screen.getByLabelText(/cooldown.*minutes/i);
      expect(cooldownInput).toHaveValue(10);
    });

    it('renders all sensor types in dropdown', () => {
      render(<SensorTriggerForm onChange={mockOnChange} />);

      const sensorTypeSelect = screen.getByLabelText(/sensor type/i);
      const options = Array.from(sensorTypeSelect.options).map((opt) => opt.value);

      SENSOR_TYPES.forEach((type) => {
        expect(options).toContain(type.value);
      });
    });

    it('renders all comparison operators in dropdown', () => {
      render(<SensorTriggerForm onChange={mockOnChange} />);

      const comparisonSelect = screen.getByLabelText(/comparison/i);
      const options = Array.from(comparisonSelect.options).map((opt) => opt.value);

      SENSOR_COMPARISONS.forEach((comp) => {
        expect(options).toContain(comp.value);
      });
    });
  });

  describe('Sensor Type Selection', () => {
    it('updates sensor_type on selection change', () => {
      const value = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      };

      render(<SensorTriggerForm value={value} onChange={mockOnChange} />);

      const sensorTypeSelect = screen.getByLabelText(/sensor type/i);
      fireEvent.change(sensorTypeSelect, { target: { value: 'temperature' } });

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        sensor_type: 'temperature',
      });
    });

    it('shows description for selected sensor type', () => {
      const value = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      };

      render(<SensorTriggerForm value={value} onChange={mockOnChange} />);

      const lightSensor = SENSOR_TYPES.find((s) => s.value === 'light');
      expect(screen.getByText(lightSensor.description)).toBeInTheDocument();
    });

    it('updates description when sensor type changes', () => {
      const value = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      };

      const { rerender } = render(
        <SensorTriggerForm value={value} onChange={mockOnChange} />
      );

      // Verify light description shows
      const lightSensor = SENSOR_TYPES.find((s) => s.value === 'light');
      expect(screen.getByText(lightSensor.description)).toBeInTheDocument();

      // Change to temperature
      const newValue = { ...value, sensor_type: 'temperature' };
      rerender(<SensorTriggerForm value={newValue} onChange={mockOnChange} />);

      // Verify temperature description shows
      const tempSensor = SENSOR_TYPES.find((s) => s.value === 'temperature');
      expect(screen.getByText(tempSensor.description)).toBeInTheDocument();
    });
  });

  describe('Comparison Selection', () => {
    it('updates comparison on selection change', () => {
      const value = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      };

      render(<SensorTriggerForm value={value} onChange={mockOnChange} />);

      const comparisonSelect = screen.getByLabelText(/comparison/i);
      fireEvent.change(comparisonSelect, { target: { value: 'gte' } });

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        comparison: 'gte',
      });
    });

    it('shows comparison symbol in option labels', () => {
      render(<SensorTriggerForm onChange={mockOnChange} />);

      const comparisonSelect = screen.getByLabelText(/comparison/i);

      SENSOR_COMPARISONS.forEach((comp) => {
        const option = Array.from(comparisonSelect.options).find(
          (opt) => opt.value === comp.value
        );
        expect(option.textContent).toContain(comp.symbol);
      });
    });
  });

  describe('Threshold Input', () => {
    it('updates threshold on input change', () => {
      const value = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      };

      render(<SensorTriggerForm value={value} onChange={mockOnChange} />);

      const thresholdInput = screen.getByLabelText(/threshold/i);
      fireEvent.change(thresholdInput, { target: { value: '50' } });

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        threshold: 50,
      });
    });

    it('converts threshold to number', () => {
      const value = {
        sensor_type: 'temperature',
        comparison: 'gte',
        threshold: 20,
        cooldown_minutes: 5,
      };

      render(<SensorTriggerForm value={value} onChange={mockOnChange} />);

      const thresholdInput = screen.getByLabelText(/threshold/i);
      fireEvent.change(thresholdInput, { target: { value: '25' } });

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        threshold: 25,
      });
      expect(typeof mockOnChange.mock.calls[0][0].threshold).toBe('number');
    });
  });

  describe('Cooldown Input', () => {
    it('updates cooldown_minutes on input change', () => {
      const value = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      };

      render(<SensorTriggerForm value={value} onChange={mockOnChange} />);

      const cooldownInput = screen.getByLabelText(/cooldown.*minutes/i);
      fireEvent.change(cooldownInput, { target: { value: '10' } });

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        cooldown_minutes: 10,
      });
    });

    it('respects cooldown limits', () => {
      render(<SensorTriggerForm onChange={mockOnChange} />);

      const cooldownInput = screen.getByLabelText(/cooldown.*minutes/i);
      expect(cooldownInput).toHaveAttribute('min', '0');
      expect(cooldownInput).toHaveAttribute('max', String(SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES));
    });

    it('converts cooldown to number', () => {
      const value = {
        sensor_type: 'motion',
        comparison: 'eq',
        threshold: 1,
        cooldown_minutes: 5,
      };

      render(<SensorTriggerForm value={value} onChange={mockOnChange} />);

      const cooldownInput = screen.getByLabelText(/cooldown.*minutes/i);
      fireEvent.change(cooldownInput, { target: { value: '15' } });

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        cooldown_minutes: 15,
      });
      expect(typeof mockOnChange.mock.calls[0][0].cooldown_minutes).toBe('number');
    });
  });

  describe('Preview Text Generation', () => {
    it('generates preview for light sensor with less than comparison', () => {
      const value = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      };

      render(<SensorTriggerForm value={value} onChange={mockOnChange} />);

      expect(screen.getByText(/When light < 100 lux, cooldown: 5 min/i)).toBeInTheDocument();
    });

    it('generates preview for temperature sensor with greater than or equal comparison', () => {
      const value = {
        sensor_type: 'temperature',
        comparison: 'gte',
        threshold: 25,
        cooldown_minutes: 10,
      };

      render(<SensorTriggerForm value={value} onChange={mockOnChange} />);

      expect(screen.getByText(/When temperature ≥ 25 °C, cooldown: 10 min/i)).toBeInTheDocument();
    });

    it('generates preview for motion sensor with equal comparison', () => {
      const value = {
        sensor_type: 'motion',
        comparison: 'eq',
        threshold: 1,
        cooldown_minutes: 2,
      };

      render(<SensorTriggerForm value={value} onChange={mockOnChange} />);

      expect(screen.getByText(/When motion = 1, cooldown: 2 min/i)).toBeInTheDocument();
    });

    it('generates preview with greater than comparison', () => {
      const value = {
        sensor_type: 'light',
        comparison: 'gt',
        threshold: 500,
        cooldown_minutes: 3,
      };

      render(<SensorTriggerForm value={value} onChange={mockOnChange} />);

      expect(screen.getByText(/When light > 500 lux, cooldown: 3 min/i)).toBeInTheDocument();
    });

    it('generates preview with less than or equal comparison', () => {
      const value = {
        sensor_type: 'temperature',
        comparison: 'lte',
        threshold: 15,
        cooldown_minutes: 7,
      };

      render(<SensorTriggerForm value={value} onChange={mockOnChange} />);

      expect(screen.getByText(/When temperature ≤ 15 °C, cooldown: 7 min/i)).toBeInTheDocument();
    });

    it('updates preview when sensor type changes', () => {
      const value = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      };

      const { rerender } = render(
        <SensorTriggerForm value={value} onChange={mockOnChange} />
      );

      expect(screen.getByText(/When light < 100 lux, cooldown: 5 min/i)).toBeInTheDocument();

      const newValue = { ...value, sensor_type: 'temperature' };
      rerender(<SensorTriggerForm value={newValue} onChange={mockOnChange} />);

      expect(screen.getByText(/When temperature < 100 °C, cooldown: 5 min/i)).toBeInTheDocument();
    });

    it('updates preview when comparison changes', () => {
      const value = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      };

      const { rerender } = render(
        <SensorTriggerForm value={value} onChange={mockOnChange} />
      );

      expect(screen.getByText(/When light < 100 lux, cooldown: 5 min/i)).toBeInTheDocument();

      const newValue = { ...value, comparison: 'gte' };
      rerender(<SensorTriggerForm value={newValue} onChange={mockOnChange} />);

      expect(screen.getByText(/When light ≥ 100 lux, cooldown: 5 min/i)).toBeInTheDocument();
    });

    it('updates preview when threshold changes', () => {
      const value = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      };

      const { rerender } = render(
        <SensorTriggerForm value={value} onChange={mockOnChange} />
      );

      expect(screen.getByText(/When light < 100 lux, cooldown: 5 min/i)).toBeInTheDocument();

      const newValue = { ...value, threshold: 200 };
      rerender(<SensorTriggerForm value={newValue} onChange={mockOnChange} />);

      expect(screen.getByText(/When light < 200 lux, cooldown: 5 min/i)).toBeInTheDocument();
    });

    it('updates preview when cooldown changes', () => {
      const value = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      };

      const { rerender } = render(
        <SensorTriggerForm value={value} onChange={mockOnChange} />
      );

      expect(screen.getByText(/When light < 100 lux, cooldown: 5 min/i)).toBeInTheDocument();

      const newValue = { ...value, cooldown_minutes: 15 };
      rerender(<SensorTriggerForm value={newValue} onChange={mockOnChange} />);

      expect(screen.getByText(/When light < 100 lux, cooldown: 15 min/i)).toBeInTheDocument();
    });
  });

  describe('Disabled State', () => {
    it('disables sensor type select when disabled prop is true', () => {
      render(<SensorTriggerForm onChange={mockOnChange} disabled={true} />);

      const sensorTypeSelect = screen.getByLabelText(/sensor type/i);
      expect(sensorTypeSelect).toBeDisabled();
    });

    it('disables comparison select when disabled prop is true', () => {
      render(<SensorTriggerForm onChange={mockOnChange} disabled={true} />);

      const comparisonSelect = screen.getByLabelText(/comparison/i);
      expect(comparisonSelect).toBeDisabled();
    });

    it('disables threshold input when disabled prop is true', () => {
      render(<SensorTriggerForm onChange={mockOnChange} disabled={true} />);

      const thresholdInput = screen.getByLabelText(/threshold/i);
      expect(thresholdInput).toBeDisabled();
    });

    it('disables cooldown input when disabled prop is true', () => {
      render(<SensorTriggerForm onChange={mockOnChange} disabled={true} />);

      const cooldownInput = screen.getByLabelText(/cooldown.*minutes/i);
      expect(cooldownInput).toBeDisabled();
    });

    it('does not disable inputs when disabled prop is false', () => {
      render(<SensorTriggerForm onChange={mockOnChange} disabled={false} />);

      const sensorTypeSelect = screen.getByLabelText(/sensor type/i);
      const comparisonSelect = screen.getByLabelText(/comparison/i);
      const thresholdInput = screen.getByLabelText(/threshold/i);
      const cooldownInput = screen.getByLabelText(/cooldown.*minutes/i);

      expect(sensorTypeSelect).not.toBeDisabled();
      expect(comparisonSelect).not.toBeDisabled();
      expect(thresholdInput).not.toBeDisabled();
      expect(cooldownInput).not.toBeDisabled();
    });
  });

  describe('Dark Mode Styling', () => {
    it('applies dark mode classes to sensor type select', () => {
      render(<SensorTriggerForm onChange={mockOnChange} />);

      const sensorTypeSelect = screen.getByLabelText(/sensor type/i);
      expect(sensorTypeSelect).toHaveClass('dark:bg-gray-800', 'dark:text-white', 'dark:border-gray-600');
    });

    it('applies dark mode classes to comparison select', () => {
      render(<SensorTriggerForm onChange={mockOnChange} />);

      const comparisonSelect = screen.getByLabelText(/comparison/i);
      expect(comparisonSelect).toHaveClass('dark:bg-gray-800', 'dark:text-white', 'dark:border-gray-600');
    });

    it('applies dark mode classes to threshold input', () => {
      render(<SensorTriggerForm onChange={mockOnChange} />);

      const thresholdInput = screen.getByLabelText(/threshold/i);
      expect(thresholdInput).toHaveClass('dark:bg-gray-800', 'dark:text-white', 'dark:border-gray-600');
    });

    it('applies dark mode classes to cooldown input', () => {
      render(<SensorTriggerForm onChange={mockOnChange} />);

      const cooldownInput = screen.getByLabelText(/cooldown.*minutes/i);
      expect(cooldownInput).toHaveClass('dark:bg-gray-800', 'dark:text-white', 'dark:border-gray-600');
    });

    it('applies dark mode classes to labels', () => {
      render(<SensorTriggerForm onChange={mockOnChange} />);

      const header = screen.getByText('Sensor Configuration');
      expect(header).toHaveClass('dark:text-white');
    });

    it('applies dark mode classes to preview text', () => {
      const value = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      };

      render(<SensorTriggerForm value={value} onChange={mockOnChange} />);

      const previewText = screen.getByText(/When light < 100 lux, cooldown: 5 min/i);
      expect(previewText).toHaveClass('dark:text-gray-400', 'dark:bg-gray-800');
    });
  });

  describe('onChange Callback', () => {
    it('calls onChange with complete trigger object when sensor type changes', () => {
      const value = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      };

      render(<SensorTriggerForm value={value} onChange={mockOnChange} />);

      const sensorTypeSelect = screen.getByLabelText(/sensor type/i);
      fireEvent.change(sensorTypeSelect, { target: { value: 'temperature' } });

      expect(mockOnChange).toHaveBeenCalledWith({
        sensor_type: 'temperature',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      });
    });

    it('calls onChange with complete trigger object when comparison changes', () => {
      const value = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      };

      render(<SensorTriggerForm value={value} onChange={mockOnChange} />);

      const comparisonSelect = screen.getByLabelText(/comparison/i);
      fireEvent.change(comparisonSelect, { target: { value: 'gte' } });

      expect(mockOnChange).toHaveBeenCalledWith({
        sensor_type: 'light',
        comparison: 'gte',
        threshold: 100,
        cooldown_minutes: 5,
      });
    });

    it('calls onChange with complete trigger object when threshold changes', () => {
      const value = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      };

      render(<SensorTriggerForm value={value} onChange={mockOnChange} />);

      const thresholdInput = screen.getByLabelText(/threshold/i);
      fireEvent.change(thresholdInput, { target: { value: '200' } });

      expect(mockOnChange).toHaveBeenCalledWith({
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 200,
        cooldown_minutes: 5,
      });
    });

    it('calls onChange with complete trigger object when cooldown changes', () => {
      const value = {
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 5,
      };

      render(<SensorTriggerForm value={value} onChange={mockOnChange} />);

      const cooldownInput = screen.getByLabelText(/cooldown.*minutes/i);
      fireEvent.change(cooldownInput, { target: { value: '10' } });

      expect(mockOnChange).toHaveBeenCalledWith({
        sensor_type: 'light',
        comparison: 'lt',
        threshold: 100,
        cooldown_minutes: 10,
      });
    });
  });

  describe('Numeric Input Validation', () => {
    describe('Threshold Validation', () => {
      it('does not call onChange for NaN threshold input', () => {
        const value = {
          sensor_type: 'light',
          comparison: 'lt',
          threshold: 100,
          cooldown_minutes: 5,
        };

        render(<SensorTriggerForm value={value} onChange={mockOnChange} />);

        const thresholdInput = screen.getByLabelText(/threshold/i);
        fireEvent.change(thresholdInput, { target: { value: 'abc' } });

        expect(mockOnChange).not.toHaveBeenCalled();
      });

      it('does not call onChange for empty threshold input', () => {
        const value = {
          sensor_type: 'light',
          comparison: 'lt',
          threshold: 100,
          cooldown_minutes: 5,
        };

        render(<SensorTriggerForm value={value} onChange={mockOnChange} />);

        const thresholdInput = screen.getByLabelText(/threshold/i);
        fireEvent.change(thresholdInput, { target: { value: '' } });

        expect(mockOnChange).not.toHaveBeenCalled();
      });

      it('does not call onChange for negative threshold input', () => {
        const value = {
          sensor_type: 'light',
          comparison: 'lt',
          threshold: 100,
          cooldown_minutes: 5,
        };

        render(<SensorTriggerForm value={value} onChange={mockOnChange} />);

        const thresholdInput = screen.getByLabelText(/threshold/i);
        fireEvent.change(thresholdInput, { target: { value: '-10' } });

        expect(mockOnChange).not.toHaveBeenCalled();
      });

      it('accepts valid threshold input', () => {
        const value = {
          sensor_type: 'light',
          comparison: 'lt',
          threshold: 100,
          cooldown_minutes: 5,
        };

        render(<SensorTriggerForm value={value} onChange={mockOnChange} />);

        const thresholdInput = screen.getByLabelText(/threshold/i);
        fireEvent.change(thresholdInput, { target: { value: '250' } });

        expect(mockOnChange).toHaveBeenCalledWith({
          ...value,
          threshold: 250,
        });
      });

      it('accepts zero as valid threshold', () => {
        const value = {
          sensor_type: 'light',
          comparison: 'lt',
          threshold: 100,
          cooldown_minutes: 5,
        };

        render(<SensorTriggerForm value={value} onChange={mockOnChange} />);

        const thresholdInput = screen.getByLabelText(/threshold/i);
        fireEvent.change(thresholdInput, { target: { value: '0' } });

        expect(mockOnChange).toHaveBeenCalledWith({
          ...value,
          threshold: 0,
        });
      });
    });

    describe('Cooldown Validation', () => {
      it('does not call onChange for NaN cooldown input', () => {
        const value = {
          sensor_type: 'light',
          comparison: 'lt',
          threshold: 100,
          cooldown_minutes: 5,
        };

        render(<SensorTriggerForm value={value} onChange={mockOnChange} />);

        const cooldownInput = screen.getByLabelText(/cooldown.*minutes/i);
        fireEvent.change(cooldownInput, { target: { value: 'abc' } });

        expect(mockOnChange).not.toHaveBeenCalled();
      });

      it('does not call onChange for empty cooldown input', () => {
        const value = {
          sensor_type: 'light',
          comparison: 'lt',
          threshold: 100,
          cooldown_minutes: 5,
        };

        render(<SensorTriggerForm value={value} onChange={mockOnChange} />);

        const cooldownInput = screen.getByLabelText(/cooldown.*minutes/i);
        fireEvent.change(cooldownInput, { target: { value: '' } });

        expect(mockOnChange).not.toHaveBeenCalled();
      });

      it('does not call onChange for negative cooldown input', () => {
        const value = {
          sensor_type: 'light',
          comparison: 'lt',
          threshold: 100,
          cooldown_minutes: 5,
        };

        render(<SensorTriggerForm value={value} onChange={mockOnChange} />);

        const cooldownInput = screen.getByLabelText(/cooldown.*minutes/i);
        fireEvent.change(cooldownInput, { target: { value: '-5' } });

        expect(mockOnChange).not.toHaveBeenCalled();
      });

      it('does not call onChange for cooldown exceeding max', () => {
        const value = {
          sensor_type: 'light',
          comparison: 'lt',
          threshold: 100,
          cooldown_minutes: 5,
        };

        render(<SensorTriggerForm value={value} onChange={mockOnChange} />);

        const cooldownInput = screen.getByLabelText(/cooldown.*minutes/i);
        fireEvent.change(cooldownInput, {
          target: { value: String(SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES + 1) },
        });

        expect(mockOnChange).not.toHaveBeenCalled();
      });

      it('accepts valid cooldown input', () => {
        const value = {
          sensor_type: 'light',
          comparison: 'lt',
          threshold: 100,
          cooldown_minutes: 5,
        };

        render(<SensorTriggerForm value={value} onChange={mockOnChange} />);

        const cooldownInput = screen.getByLabelText(/cooldown.*minutes/i);
        fireEvent.change(cooldownInput, { target: { value: '30' } });

        expect(mockOnChange).toHaveBeenCalledWith({
          ...value,
          cooldown_minutes: 30,
        });
      });

      it('accepts zero as valid cooldown', () => {
        const value = {
          sensor_type: 'light',
          comparison: 'lt',
          threshold: 100,
          cooldown_minutes: 5,
        };

        render(<SensorTriggerForm value={value} onChange={mockOnChange} />);

        const cooldownInput = screen.getByLabelText(/cooldown.*minutes/i);
        fireEvent.change(cooldownInput, { target: { value: '0' } });

        expect(mockOnChange).toHaveBeenCalledWith({
          ...value,
          cooldown_minutes: 0,
        });
      });

      it('accepts max cooldown value', () => {
        const value = {
          sensor_type: 'light',
          comparison: 'lt',
          threshold: 100,
          cooldown_minutes: 5,
        };

        render(<SensorTriggerForm value={value} onChange={mockOnChange} />);

        const cooldownInput = screen.getByLabelText(/cooldown.*minutes/i);
        fireEvent.change(cooldownInput, {
          target: { value: String(SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES) },
        });

        expect(mockOnChange).toHaveBeenCalledWith({
          ...value,
          cooldown_minutes: SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES,
        });
      });
    });
  });
});
