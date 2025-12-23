import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import MoonPhaseTriggerForm from '../MoonPhaseTriggerForm';
import { MOON_PHASES, SCHEDULE_LIMITS } from '../constants';

describe('MoonPhaseTriggerForm', () => {
  let mockOnChange;

  beforeEach(() => {
    mockOnChange = vi.fn();
  });

  describe('Rendering', () => {
    it('renders with default values', () => {
      render(<MoonPhaseTriggerForm onChange={mockOnChange} />);

      expect(screen.getByText('Moon Phase Configuration')).toBeInTheDocument();
      expect(screen.getByLabelText(/moon phase/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/time of day/i)).toBeInTheDocument();
      expect(screen.getByLabelText('Offset in days')).toBeInTheDocument();
      expect(screen.getByText('Preview:')).toBeInTheDocument();
    });

    it('renders with provided value', () => {
      const value = {
        moon_phase: 'new',
        time_of_day: '21:30',
        offset_days: 2,
      };

      render(<MoonPhaseTriggerForm value={value} onChange={mockOnChange} />);

      const moonPhaseSelect = screen.getByLabelText(/moon phase/i);
      expect(moonPhaseSelect).toHaveValue('new');

      const timeInput = screen.getByLabelText(/time of day/i);
      expect(timeInput).toHaveValue('21:30');

      const offsetInput = screen.getByLabelText('Offset in days');
      expect(offsetInput).toHaveValue(2);
    });

    it('renders all moon phases in dropdown', () => {
      render(<MoonPhaseTriggerForm onChange={mockOnChange} />);

      const moonPhaseSelect = screen.getByLabelText(/moon phase/i);
      const options = Array.from(moonPhaseSelect.options).map((opt) => opt.value);

      MOON_PHASES.forEach((phase) => {
        expect(options).toContain(phase.value);
      });
    });
  });

  describe('Moon Phase Selection', () => {
    it('updates moon_phase on selection change', () => {
      const value = {
        moon_phase: 'full',
        time_of_day: '20:00',
        offset_days: 0,
      };

      render(<MoonPhaseTriggerForm value={value} onChange={mockOnChange} />);

      const moonPhaseSelect = screen.getByLabelText(/moon phase/i);
      fireEvent.change(moonPhaseSelect, { target: { value: 'new' } });

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        moon_phase: 'new',
      });
    });

    it('shows label for selected moon phase', () => {
      const value = {
        moon_phase: 'full',
        time_of_day: '20:00',
        offset_days: 0,
      };

      render(<MoonPhaseTriggerForm value={value} onChange={mockOnChange} />);

      const fullMoonPhase = MOON_PHASES.find((p) => p.value === 'full');
      expect(screen.getByRole('option', { name: fullMoonPhase.label })).toBeInTheDocument();
    });
  });

  describe('Time of Day Input', () => {
    it('updates time_of_day on input change', () => {
      const value = {
        moon_phase: 'full',
        time_of_day: '20:00',
        offset_days: 0,
      };

      render(<MoonPhaseTriggerForm value={value} onChange={mockOnChange} />);

      const timeInput = screen.getByLabelText(/time of day/i);
      fireEvent.change(timeInput, { target: { value: '22:30' } });

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        time_of_day: '22:30',
      });
    });

    it('validates time format (HH:MM)', () => {
      render(<MoonPhaseTriggerForm onChange={mockOnChange} />);

      const timeInput = screen.getByLabelText(/time of day/i);
      expect(timeInput).toHaveAttribute('type', 'time');
      expect(timeInput).toHaveAttribute('pattern', '[0-9]{2}:[0-9]{2}');
    });

    it('shows error message for invalid time', () => {
      const errors = {
        time_of_day: 'Time must be in HH:MM format',
      };

      render(<MoonPhaseTriggerForm onChange={mockOnChange} errors={errors} />);

      expect(screen.getByText(errors.time_of_day)).toBeInTheDocument();
    });
  });

  describe('Offset Days Input', () => {
    it('updates offset_days on input change', () => {
      const value = {
        moon_phase: 'full',
        time_of_day: '20:00',
        offset_days: 0,
      };

      render(<MoonPhaseTriggerForm value={value} onChange={mockOnChange} />);

      const offsetInput = screen.getByLabelText('Offset in days');
      fireEvent.change(offsetInput, { target: { value: '3' } });

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        offset_days: 3,
      });
    });

    it('allows negative offset values', () => {
      const value = {
        moon_phase: 'full',
        time_of_day: '20:00',
        offset_days: 0,
      };

      render(<MoonPhaseTriggerForm value={value} onChange={mockOnChange} />);

      const offsetInput = screen.getByLabelText('Offset in days');
      fireEvent.change(offsetInput, { target: { value: '-3' } });

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        offset_days: -3,
      });
    });

    it('respects min and max offset limits', () => {
      render(<MoonPhaseTriggerForm onChange={mockOnChange} />);

      const offsetInput = screen.getByLabelText('Offset in days');
      expect(offsetInput).toHaveAttribute('min', String(-SCHEDULE_LIMITS.MAX_OFFSET_DAYS));
      expect(offsetInput).toHaveAttribute('max', String(SCHEDULE_LIMITS.MAX_OFFSET_DAYS));
    });

    it('shows error message for invalid offset', () => {
      const errors = {
        offset_days: 'Offset must be between -7 and 7 days',
      };

      render(<MoonPhaseTriggerForm onChange={mockOnChange} errors={errors} />);

      expect(screen.getByText(errors.offset_days)).toBeInTheDocument();
    });
  });

  describe('Numeric Input Validation', () => {
    it('does not call onChange for NaN input', () => {
      const value = {
        moon_phase: 'full',
        time_of_day: '20:00',
        offset_days: 0,
      };

      render(<MoonPhaseTriggerForm value={value} onChange={mockOnChange} />);

      const offsetInput = screen.getByLabelText('Offset in days');
      fireEvent.change(offsetInput, { target: { value: 'abc' } });

      expect(mockOnChange).not.toHaveBeenCalled();
    });

    it('does not call onChange for empty input', () => {
      const value = {
        moon_phase: 'full',
        time_of_day: '20:00',
        offset_days: 2,
      };

      render(<MoonPhaseTriggerForm value={value} onChange={mockOnChange} />);

      const offsetInput = screen.getByLabelText('Offset in days');
      fireEvent.change(offsetInput, { target: { value: '' } });

      expect(mockOnChange).not.toHaveBeenCalled();
    });

    it('does not call onChange for values below minimum', () => {
      const value = {
        moon_phase: 'full',
        time_of_day: '20:00',
        offset_days: 0,
      };

      render(<MoonPhaseTriggerForm value={value} onChange={mockOnChange} />);

      const offsetInput = screen.getByLabelText('Offset in days');
      fireEvent.change(offsetInput, { target: { value: String(-SCHEDULE_LIMITS.MAX_OFFSET_DAYS - 1) } });

      expect(mockOnChange).not.toHaveBeenCalled();
    });

    it('does not call onChange for values above maximum', () => {
      const value = {
        moon_phase: 'full',
        time_of_day: '20:00',
        offset_days: 0,
      };

      render(<MoonPhaseTriggerForm value={value} onChange={mockOnChange} />);

      const offsetInput = screen.getByLabelText('Offset in days');
      fireEvent.change(offsetInput, { target: { value: String(SCHEDULE_LIMITS.MAX_OFFSET_DAYS + 1) } });

      expect(mockOnChange).not.toHaveBeenCalled();
    });

    it('accepts valid values within symmetric range (negative)', () => {
      const value = {
        moon_phase: 'full',
        time_of_day: '20:00',
        offset_days: 0,
      };

      render(<MoonPhaseTriggerForm value={value} onChange={mockOnChange} />);

      const offsetInput = screen.getByLabelText('Offset in days');
      fireEvent.change(offsetInput, { target: { value: '-3' } });

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        offset_days: -3,
      });
    });

    it('accepts boundary value at minimum', () => {
      const value = {
        moon_phase: 'full',
        time_of_day: '20:00',
        offset_days: 0,
      };

      render(<MoonPhaseTriggerForm value={value} onChange={mockOnChange} />);

      const offsetInput = screen.getByLabelText('Offset in days');
      fireEvent.change(offsetInput, { target: { value: String(-SCHEDULE_LIMITS.MAX_OFFSET_DAYS) } });

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        offset_days: -SCHEDULE_LIMITS.MAX_OFFSET_DAYS,
      });
    });

    it('accepts boundary value at zero', () => {
      const value = {
        moon_phase: 'full',
        time_of_day: '20:00',
        offset_days: 2,
      };

      render(<MoonPhaseTriggerForm value={value} onChange={mockOnChange} />);

      const offsetInput = screen.getByLabelText('Offset in days');
      fireEvent.change(offsetInput, { target: { value: '0' } });

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        offset_days: 0,
      });
    });

    it('accepts boundary value at maximum', () => {
      const value = {
        moon_phase: 'full',
        time_of_day: '20:00',
        offset_days: 0,
      };

      render(<MoonPhaseTriggerForm value={value} onChange={mockOnChange} />);

      const offsetInput = screen.getByLabelText('Offset in days');
      fireEvent.change(offsetInput, { target: { value: String(SCHEDULE_LIMITS.MAX_OFFSET_DAYS) } });

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        offset_days: SCHEDULE_LIMITS.MAX_OFFSET_DAYS,
      });
    });
  });

  describe('Quick Offset Presets', () => {
    it('renders quick offset preset buttons', () => {
      render(<MoonPhaseTriggerForm onChange={mockOnChange} />);

      expect(screen.getByLabelText('Set offset to -1 days')).toBeInTheDocument();
      expect(screen.getByLabelText('Set offset to 0 days')).toBeInTheDocument();
      expect(screen.getByLabelText('Set offset to 1 days')).toBeInTheDocument();
    });

    it('sets offset to -1 when -1 day preset clicked', () => {
      const value = {
        moon_phase: 'full',
        time_of_day: '20:00',
        offset_days: 0,
      };

      render(<MoonPhaseTriggerForm value={value} onChange={mockOnChange} />);

      const presetNeg1 = screen.getByLabelText('Set offset to -1 days');
      fireEvent.click(presetNeg1);

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        offset_days: -1,
      });
    });

    it('sets offset to 0 when "No offset" preset clicked', () => {
      const value = {
        moon_phase: 'full',
        time_of_day: '20:00',
        offset_days: 2,
      };

      render(<MoonPhaseTriggerForm value={value} onChange={mockOnChange} />);

      const presetZero = screen.getByLabelText('Set offset to 0 days');
      fireEvent.click(presetZero);

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        offset_days: 0,
      });
    });

    it('sets offset to +1 when +1 day preset clicked', () => {
      const value = {
        moon_phase: 'full',
        time_of_day: '20:00',
        offset_days: 0,
      };

      render(<MoonPhaseTriggerForm value={value} onChange={mockOnChange} />);

      const presetPos1 = screen.getByLabelText('Set offset to 1 days');
      fireEvent.click(presetPos1);

      expect(mockOnChange).toHaveBeenCalledWith({
        ...value,
        offset_days: 1,
      });
    });

    it('highlights selected preset', () => {
      const value = {
        moon_phase: 'full',
        time_of_day: '20:00',
        offset_days: 1,
      };

      render(<MoonPhaseTriggerForm value={value} onChange={mockOnChange} />);

      const presetPos1 = screen.getByLabelText('Set offset to 1 days');
      expect(presetPos1).toHaveClass('bg-blue-500');
    });
  });

  describe('Preview Text Generation', () => {
    it('generates preview for moon phase without offset', () => {
      const value = {
        moon_phase: 'full',
        time_of_day: '20:00',
        offset_days: 0,
      };

      render(<MoonPhaseTriggerForm value={value} onChange={mockOnChange} />);

      expect(screen.getByText('On Full Moon at 20:00')).toBeInTheDocument();
    });

    it('generates preview with positive offset', () => {
      const value = {
        moon_phase: 'full',
        time_of_day: '20:00',
        offset_days: 2,
      };

      render(<MoonPhaseTriggerForm value={value} onChange={mockOnChange} />);

      expect(screen.getByText('2 days after Full Moon at 20:00')).toBeInTheDocument();
    });

    it('generates preview with negative offset', () => {
      const value = {
        moon_phase: 'full',
        time_of_day: '20:00',
        offset_days: -3,
      };

      render(<MoonPhaseTriggerForm value={value} onChange={mockOnChange} />);

      expect(screen.getByText('3 days before Full Moon at 20:00')).toBeInTheDocument();
    });

    it('generates preview with singular day offset', () => {
      const value = {
        moon_phase: 'new',
        time_of_day: '22:00',
        offset_days: 1,
      };

      render(<MoonPhaseTriggerForm value={value} onChange={mockOnChange} />);

      expect(screen.getByText('1 day after New Moon at 22:00')).toBeInTheDocument();
    });

    it('generates preview for different moon phases', () => {
      const value = {
        moon_phase: 'waxing_crescent',
        time_of_day: '19:30',
        offset_days: 0,
      };

      render(<MoonPhaseTriggerForm value={value} onChange={mockOnChange} />);

      expect(screen.getByText('On Waxing Crescent at 19:30')).toBeInTheDocument();
    });
  });

  describe('Disabled State', () => {
    it('disables moon phase select when disabled prop is true', () => {
      render(<MoonPhaseTriggerForm onChange={mockOnChange} disabled={true} />);

      const moonPhaseSelect = screen.getByLabelText(/moon phase/i);
      expect(moonPhaseSelect).toBeDisabled();
    });

    it('disables time input when disabled prop is true', () => {
      render(<MoonPhaseTriggerForm onChange={mockOnChange} disabled={true} />);

      const timeInput = screen.getByLabelText(/time of day/i);
      expect(timeInput).toBeDisabled();
    });

    it('disables offset input when disabled prop is true', () => {
      render(<MoonPhaseTriggerForm onChange={mockOnChange} disabled={true} />);

      const offsetInput = screen.getByLabelText('Offset in days');
      expect(offsetInput).toBeDisabled();
    });

    it('disables preset buttons when disabled prop is true', () => {
      render(<MoonPhaseTriggerForm onChange={mockOnChange} disabled={true} />);

      const presetZero = screen.getByLabelText('Set offset to 0 days');
      expect(presetZero).toBeDisabled();
    });

    it('does not disable inputs when disabled prop is false', () => {
      render(<MoonPhaseTriggerForm onChange={mockOnChange} disabled={false} />);

      const moonPhaseSelect = screen.getByLabelText(/moon phase/i);
      const timeInput = screen.getByLabelText(/time of day/i);
      const offsetInput = screen.getByLabelText('Offset in days');

      expect(moonPhaseSelect).not.toBeDisabled();
      expect(timeInput).not.toBeDisabled();
      expect(offsetInput).not.toBeDisabled();
    });
  });

  describe('Dark Mode Styling', () => {
    it('applies dark mode classes to moon phase select', () => {
      render(<MoonPhaseTriggerForm onChange={mockOnChange} />);

      const moonPhaseSelect = screen.getByLabelText(/moon phase/i);
      expect(moonPhaseSelect).toHaveClass('dark:bg-gray-800', 'dark:text-white', 'dark:border-gray-600');
    });

    it('applies dark mode classes to time input', () => {
      render(<MoonPhaseTriggerForm onChange={mockOnChange} />);

      const timeInput = screen.getByLabelText(/time of day/i);
      expect(timeInput).toHaveClass('dark:bg-gray-800', 'dark:text-white', 'dark:border-gray-600');
    });

    it('applies dark mode classes to offset input', () => {
      render(<MoonPhaseTriggerForm onChange={mockOnChange} />);

      const offsetInput = screen.getByLabelText('Offset in days');
      expect(offsetInput).toHaveClass('dark:bg-gray-800', 'dark:text-white', 'dark:border-gray-600');
    });

    it('applies dark mode classes to labels', () => {
      render(<MoonPhaseTriggerForm onChange={mockOnChange} />);

      const header = screen.getByText('Moon Phase Configuration');
      expect(header).toHaveClass('dark:text-white');
    });

    it('applies dark mode classes to preset buttons', () => {
      render(<MoonPhaseTriggerForm onChange={mockOnChange} />);

      // Test non-selected preset button (default offset is 0, so +1 is not selected)
      const presetPlus1 = screen.getByLabelText('Set offset to 1 days');
      expect(presetPlus1).toHaveClass('dark:bg-gray-700', 'dark:text-gray-300');
    });

    it('applies dark mode classes to preview text', () => {
      const value = {
        moon_phase: 'full',
        time_of_day: '20:00',
        offset_days: 0,
      };

      render(<MoonPhaseTriggerForm value={value} onChange={mockOnChange} />);

      const previewText = screen.getByText('On Full Moon at 20:00');
      expect(previewText).toHaveClass('dark:text-gray-300', 'dark:bg-gray-800');
    });
  });

  describe('onChange Callback', () => {
    it('calls onChange with complete trigger object when moon phase changes', () => {
      const value = {
        moon_phase: 'full',
        time_of_day: '20:00',
        offset_days: 2,
      };

      render(<MoonPhaseTriggerForm value={value} onChange={mockOnChange} />);

      const moonPhaseSelect = screen.getByLabelText(/moon phase/i);
      fireEvent.change(moonPhaseSelect, { target: { value: 'new' } });

      expect(mockOnChange).toHaveBeenCalledWith({
        moon_phase: 'new',
        time_of_day: '20:00',
        offset_days: 2,
      });
    });

    it('calls onChange with complete trigger object when time changes', () => {
      const value = {
        moon_phase: 'full',
        time_of_day: '20:00',
        offset_days: 0,
      };

      render(<MoonPhaseTriggerForm value={value} onChange={mockOnChange} />);

      const timeInput = screen.getByLabelText(/time of day/i);
      fireEvent.change(timeInput, { target: { value: '23:45' } });

      expect(mockOnChange).toHaveBeenCalledWith({
        moon_phase: 'full',
        time_of_day: '23:45',
        offset_days: 0,
      });
    });

    it('calls onChange with complete trigger object when offset changes', () => {
      const value = {
        moon_phase: 'full',
        time_of_day: '20:00',
        offset_days: 0,
      };

      render(<MoonPhaseTriggerForm value={value} onChange={mockOnChange} />);

      const offsetInput = screen.getByLabelText('Offset in days');
      fireEvent.change(offsetInput, { target: { value: '5' } });

      expect(mockOnChange).toHaveBeenCalledWith({
        moon_phase: 'full',
        time_of_day: '20:00',
        offset_days: 5,
      });
    });
  });
});
