import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import TimeWindowInput from '../TimeWindowInput';
import { SOLAR_EVENTS } from '../constants';

describe('TimeWindowInput', () => {
  const mockOnChange = vi.fn();

  const defaultProps = {
    value: {
      start_time: '21:00',
      end_time: '05:00',
      start_offset_minutes: 0,
      end_offset_minutes: 0,
    },
    onChange: mockOnChange,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should render with fixed time values', () => {
      render(<TimeWindowInput {...defaultProps} />);

      expect(screen.getByLabelText(/start time \(fixed\)/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/end time \(fixed\)/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/start time \(fixed\)/i)).toHaveValue('21:00');
      expect(screen.getByLabelText(/end time \(fixed\)/i)).toHaveValue('05:00');
    });

    it('should render with solar event values', () => {
      const solarProps = {
        ...defaultProps,
        value: {
          start_time: 'sunset',
          end_time: 'sunrise',
          start_offset_minutes: 30,
          end_offset_minutes: -30,
        },
      };

      render(<TimeWindowInput {...solarProps} />);

      expect(screen.getByLabelText(/start time \(solar event\)/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/end time \(solar event\)/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/start time \(solar event\)/i)).toHaveValue('sunset');
      expect(screen.getByLabelText(/end time \(solar event\)/i)).toHaveValue('sunrise');
    });

    it('should render solar event type toggles when showSolarEvents is true', () => {
      render(<TimeWindowInput {...defaultProps} showSolarEvents={true} />);

      const radios = screen.getAllByRole('radio');
      expect(radios.length).toBeGreaterThan(0);
      expect(screen.getAllByText(/fixed time/i)).toHaveLength(2);
      expect(screen.getAllByText(/solar event/i)).toHaveLength(2);
    });

    it('should not render solar event type toggles when showSolarEvents is false', () => {
      render(<TimeWindowInput {...defaultProps} showSolarEvents={false} />);

      expect(screen.queryByText(/solar event/i)).not.toBeInTheDocument();
      // Should only show time inputs without type selection
      expect(screen.getByLabelText(/start time \(fixed\)/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/end time \(fixed\)/i)).toBeInTheDocument();
    });

    it('should show preview text for solar events', () => {
      const solarProps = {
        ...defaultProps,
        value: {
          start_time: 'sunset',
          end_time: 'sunrise',
          start_offset_minutes: 30,
          end_offset_minutes: -30,
        },
      };

      render(<TimeWindowInput {...solarProps} />);

      expect(screen.getByText(/30 minutes after sunset/i)).toBeInTheDocument();
      expect(screen.getByText(/30 minutes before sunrise/i)).toBeInTheDocument();
    });

    it('should show "at" preview for zero offset', () => {
      const solarProps = {
        ...defaultProps,
        value: {
          start_time: 'sunset',
          end_time: 'sunrise',
          start_offset_minutes: 0,
          end_offset_minutes: 0,
        },
      };

      render(<TimeWindowInput {...solarProps} />);

      expect(screen.getByText(/at sunset/i)).toBeInTheDocument();
      expect(screen.getByText(/at sunrise/i)).toBeInTheDocument();
    });

    it('should show error messages when provided', () => {
      const errorProps = {
        ...defaultProps,
        errors: {
          start_time: 'Start time is required',
          end_time: 'End time is required',
          general: 'Invalid time window',
        },
      };

      render(<TimeWindowInput {...errorProps} />);

      expect(screen.getByText('Start time is required')).toBeInTheDocument();
      expect(screen.getByText('End time is required')).toBeInTheDocument();
      expect(screen.getByText('Invalid time window')).toBeInTheDocument();
    });

    it('should respect disabled state', () => {
      render(<TimeWindowInput {...defaultProps} disabled={true} />);

      const startTimeInput = screen.getByLabelText(/start time \(fixed\)/i);
      const endTimeInput = screen.getByLabelText(/end time \(fixed\)/i);

      expect(startTimeInput).toBeDisabled();
      expect(endTimeInput).toBeDisabled();
    });

    it('should apply dark mode styling', () => {
      document.documentElement.classList.add('dark');
      render(<TimeWindowInput {...defaultProps} />);

      const startTimeInput = screen.getByLabelText(/start time \(fixed\)/i);
      expect(startTimeInput).toHaveClass('dark:bg-gray-800');

      document.documentElement.classList.remove('dark');
    });
  });

  describe('Time Type Switching', () => {
    it('should switch from fixed time to solar event for start time', async () => {
      const user = userEvent.setup();
      render(<TimeWindowInput {...defaultProps} />);

      // Initially fixed time
      expect(screen.getByLabelText(/start time \(fixed\)/i)).toBeInTheDocument();

      // Click solar event radio
      const radios = screen.getAllByRole('radio');
      const startSolarRadio = radios.find(
        (radio) => !radio.checked && radio.parentElement.textContent.includes('Solar Event')
      );
      await user.click(startSolarRadio);

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith(
          expect.objectContaining({
            start_time: SOLAR_EVENTS[0].value,
            start_offset_minutes: 0,
          })
        );
      });
    });

    it('should switch from solar event to fixed time for start time', async () => {
      const user = userEvent.setup();
      const solarProps = {
        ...defaultProps,
        value: {
          start_time: 'sunset',
          end_time: '05:00',
          start_offset_minutes: 30,
          end_offset_minutes: 0,
        },
      };

      render(<TimeWindowInput {...solarProps} />);

      // Initially solar event
      expect(screen.getByLabelText(/start time \(solar event\)/i)).toBeInTheDocument();

      // Click fixed time radio for start
      const radios = screen.getAllByRole('radio');
      const startFixedRadio = radios[0]; // First radio is start fixed time
      await user.click(startFixedRadio);

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith(
          expect.objectContaining({
            start_time: '',
            start_offset_minutes: 0,
          })
        );
      });
    });

    it('should switch from fixed time to solar event for end time', async () => {
      const user = userEvent.setup();
      render(<TimeWindowInput {...defaultProps} />);

      // Click solar event radio for end time
      const radios = screen.getAllByRole('radio');
      // End time solar radio is the 4th radio (start fixed, start solar, end fixed, end solar)
      const endSolarRadio = radios[3];
      await user.click(endSolarRadio);

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith(
          expect.objectContaining({
            end_time: SOLAR_EVENTS[0].value,
            end_offset_minutes: 0,
          })
        );
      });
    });

    it('should switch from solar event to fixed time for end time', async () => {
      const user = userEvent.setup();
      const solarProps = {
        ...defaultProps,
        value: {
          start_time: '21:00',
          end_time: 'sunrise',
          start_offset_minutes: 0,
          end_offset_minutes: -30,
        },
      };

      render(<TimeWindowInput {...solarProps} />);

      // Click fixed time radio for end
      const radios = screen.getAllByRole('radio');
      const endFixedRadio = radios[2]; // Third radio is end fixed time
      await user.click(endFixedRadio);

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith(
          expect.objectContaining({
            end_time: '',
            end_offset_minutes: 0,
          })
        );
      });
    });
  });

  describe('Fixed Time Input', () => {
    it('should update start_time on change', async () => {
      const user = userEvent.setup();
      render(<TimeWindowInput {...defaultProps} />);

      const startTimeInput = screen.getByLabelText(/start time \(fixed\)/i);

      // Click and type to update (testing library behavior varies by browser)
      await user.click(startTimeInput);
      await user.keyboard('{Control>}a{/Control}'); // Select all
      await user.keyboard('22:30');

      // Check that onChange was called with a time update
      expect(mockOnChange).toHaveBeenCalled();
      const calls = mockOnChange.mock.calls;
      const hasTimeUpdate = calls.some(([value]) =>
        value.start_time && value.start_time !== defaultProps.value.start_time
      );
      expect(hasTimeUpdate).toBe(true);
    });

    it('should update end_time on change', async () => {
      const user = userEvent.setup();
      render(<TimeWindowInput {...defaultProps} />);

      const endTimeInput = screen.getByLabelText(/end time \(fixed\)/i);

      // Click and type to update (testing library behavior varies by browser)
      await user.click(endTimeInput);
      await user.keyboard('{Control>}a{/Control}'); // Select all
      await user.keyboard('06:30');

      // Check that onChange was called with a time update
      expect(mockOnChange).toHaveBeenCalled();
      const calls = mockOnChange.mock.calls;
      const hasTimeUpdate = calls.some(([value]) =>
        value.end_time && value.end_time !== defaultProps.value.end_time
      );
      expect(hasTimeUpdate).toBe(true);
    });

    it('should validate TIME_FORMAT_REGEX for fixed times', () => {
      const validTimeProps = {
        ...defaultProps,
        value: {
          start_time: '23:59',
          end_time: '00:00',
          start_offset_minutes: 0,
          end_offset_minutes: 0,
        },
      };

      const { rerender } = render(<TimeWindowInput {...validTimeProps} />);

      // Should show fixed time inputs for valid HH:MM format
      expect(screen.getByLabelText(/start time \(fixed\)/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/end time \(fixed\)/i)).toBeInTheDocument();

      // Invalid format should be treated as solar event
      const invalidTimeProps = {
        ...defaultProps,
        value: {
          start_time: 'sunset',
          end_time: '25:00', // Invalid hours
          start_offset_minutes: 0,
          end_offset_minutes: 0,
        },
      };

      rerender(<TimeWindowInput {...invalidTimeProps} />);

      // Should show solar event input for start (not HH:MM format)
      expect(screen.getByLabelText(/start time \(solar event\)/i)).toBeInTheDocument();
    });
  });

  describe('Solar Event Input', () => {
    const solarProps = {
      ...defaultProps,
      value: {
        start_time: 'sunset',
        end_time: 'sunrise',
        start_offset_minutes: 30,
        end_offset_minutes: -30,
      },
    };

    it('should update start solar event on change', async () => {
      const user = userEvent.setup();
      render(<TimeWindowInput {...solarProps} />);

      const startEventSelect = screen.getByLabelText(/start time \(solar event\)/i);
      await user.selectOptions(startEventSelect, 'civil_dusk');

      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({
          start_time: 'civil_dusk',
        })
      );
    });

    it('should update end solar event on change', async () => {
      const user = userEvent.setup();
      render(<TimeWindowInput {...solarProps} />);

      const endEventSelect = screen.getByLabelText(/end time \(solar event\)/i);
      await user.selectOptions(endEventSelect, 'civil_dawn');

      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({
          end_time: 'civil_dawn',
        })
      );
    });

    it('should update start offset value', async () => {
      const user = userEvent.setup();

      const zeroOffsetProps = {
        ...defaultProps,
        value: {
          start_time: 'sunset',
          end_time: 'sunrise',
          start_offset_minutes: 0,
          end_offset_minutes: 0,
        },
      };

      render(<TimeWindowInput {...zeroOffsetProps} />);

      const startOffsetInput = screen.getByLabelText(/start time offset/i);

      // Use fireEvent for more predictable input behavior
      await user.click(startOffsetInput);
      await user.keyboard('{Control>}a{/Control}'); // Select all
      await user.keyboard('60');

      // Check that onChange was called and offset was updated
      expect(mockOnChange).toHaveBeenCalled();
      // Check that at least one call has the offset set to a number
      const calls = mockOnChange.mock.calls;
      const hasOffsetUpdate = calls.some(([value]) =>
        typeof value.start_offset_minutes === 'number' && value.start_offset_minutes !== 0
      );
      expect(hasOffsetUpdate).toBe(true);
    });

    it('should update end offset value', async () => {
      const user = userEvent.setup();

      const zeroOffsetProps = {
        ...defaultProps,
        value: {
          start_time: 'sunset',
          end_time: 'sunrise',
          start_offset_minutes: 0,
          end_offset_minutes: 0,
        },
      };

      render(<TimeWindowInput {...zeroOffsetProps} />);

      const endOffsetInput = screen.getByLabelText(/end time offset/i);

      // Use keyboard for more predictable input behavior
      await user.click(endOffsetInput);
      await user.keyboard('{Control>}a{/Control}'); // Select all
      await user.keyboard('-60');

      // Check that onChange was called and offset was updated
      expect(mockOnChange).toHaveBeenCalled();
      // Check that at least one call has the offset set to a negative number
      const calls = mockOnChange.mock.calls;
      const hasOffsetUpdate = calls.some(([value]) =>
        typeof value.end_offset_minutes === 'number' && value.end_offset_minutes !== 0
      );
      expect(hasOffsetUpdate).toBe(true);
    });

    it('should enforce offset range -120 to +120', () => {
      render(<TimeWindowInput {...solarProps} />);

      const startOffsetInput = screen.getByLabelText(/start time offset/i);
      const endOffsetInput = screen.getByLabelText(/end time offset/i);

      expect(startOffsetInput).toHaveAttribute('min', '-120');
      expect(startOffsetInput).toHaveAttribute('max', '120');
      expect(endOffsetInput).toHaveAttribute('min', '-120');
      expect(endOffsetInput).toHaveAttribute('max', '120');
    });

    it('should display all solar events in dropdown', () => {
      render(<TimeWindowInput {...solarProps} />);

      const startEventSelect = screen.getByLabelText(/start time \(solar event\)/i);
      const options = Array.from(startEventSelect.options).map(opt => opt.value);

      SOLAR_EVENTS.forEach((event) => {
        expect(options).toContain(event.value);
      });
    });

    it('should show preview with singular "minute"', () => {
      const singularProps = {
        ...defaultProps,
        value: {
          start_time: 'sunset',
          end_time: 'sunrise',
          start_offset_minutes: 1,
          end_offset_minutes: -1,
        },
      };

      render(<TimeWindowInput {...singularProps} />);

      expect(screen.getByText(/1 minute after sunset/i)).toBeInTheDocument();
      expect(screen.getByText(/1 minute before sunrise/i)).toBeInTheDocument();
    });

    it('should show preview with plural "minutes"', () => {
      const pluralProps = {
        ...defaultProps,
        value: {
          start_time: 'sunset',
          end_time: 'sunrise',
          start_offset_minutes: 45,
          end_offset_minutes: -45,
        },
      };

      render(<TimeWindowInput {...pluralProps} />);

      expect(screen.getByText(/45 minutes after sunset/i)).toBeInTheDocument();
      expect(screen.getByText(/45 minutes before sunrise/i)).toBeInTheDocument();
    });
  });

  describe('Default Values', () => {
    it('should handle missing value prop gracefully', () => {
      const minimalProps = {
        onChange: mockOnChange,
      };

      render(<TimeWindowInput {...minimalProps} />);

      expect(screen.getByLabelText(/start time \(fixed\)/i)).toHaveValue('');
      expect(screen.getByLabelText(/end time \(fixed\)/i)).toHaveValue('');
    });

    it('should default offset to 0 if not provided', () => {
      const propsWithoutOffsets = {
        ...defaultProps,
        value: {
          start_time: 'sunset',
          end_time: 'sunrise',
        },
      };

      render(<TimeWindowInput {...propsWithoutOffsets} />);

      const startOffsetInput = screen.getByLabelText(/start time offset/i);
      const endOffsetInput = screen.getByLabelText(/end time offset/i);

      expect(startOffsetInput).toHaveValue(0);
      expect(endOffsetInput).toHaveValue(0);
    });

    it('should default disabled to false', () => {
      render(<TimeWindowInput {...defaultProps} />);

      const startTimeInput = screen.getByLabelText(/start time \(fixed\)/i);
      expect(startTimeInput).not.toBeDisabled();
    });

    it('should default showSolarEvents to true', () => {
      render(<TimeWindowInput {...defaultProps} />);

      expect(screen.getAllByText(/solar event/i)).toHaveLength(2);
    });

    it('should default errors to empty object', () => {
      render(<TimeWindowInput {...defaultProps} />);

      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels for time inputs', () => {
      render(<TimeWindowInput {...defaultProps} />);

      expect(screen.getByLabelText(/start time \(fixed\)/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/end time \(fixed\)/i)).toBeInTheDocument();
    });

    it('should have proper ARIA labels for offset inputs', () => {
      const solarProps = {
        ...defaultProps,
        value: {
          start_time: 'sunset',
          end_time: 'sunrise',
          start_offset_minutes: 0,
          end_offset_minutes: 0,
        },
      };

      render(<TimeWindowInput {...solarProps} />);

      expect(screen.getByLabelText(/start time offset \(minutes\)/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/end time offset \(minutes\)/i)).toBeInTheDocument();
    });

    it('should associate labels with inputs', () => {
      const solarProps = {
        ...defaultProps,
        value: {
          start_time: 'sunset',
          end_time: 'sunrise',
          start_offset_minutes: 0,
          end_offset_minutes: 0,
        },
      };

      render(<TimeWindowInput {...solarProps} />);

      const startOffsetInput = screen.getByLabelText(/start time offset/i);
      const endOffsetInput = screen.getByLabelText(/end time offset/i);

      expect(startOffsetInput).toHaveAttribute('id', 'start_offset');
      expect(endOffsetInput).toHaveAttribute('id', 'end_offset');
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty start_time gracefully', () => {
      const emptyProps = {
        ...defaultProps,
        value: {
          start_time: '',
          end_time: '05:00',
          start_offset_minutes: 0,
          end_offset_minutes: 0,
        },
      };

      render(<TimeWindowInput {...emptyProps} />);

      expect(screen.getByLabelText(/start time \(fixed\)/i)).toHaveValue('');
    });

    it('should handle empty end_time gracefully', () => {
      const emptyProps = {
        ...defaultProps,
        value: {
          start_time: '21:00',
          end_time: '',
          start_offset_minutes: 0,
          end_offset_minutes: 0,
        },
      };

      render(<TimeWindowInput {...emptyProps} />);

      expect(screen.getByLabelText(/end time \(fixed\)/i)).toHaveValue('');
    });

    it('should handle negative offset correctly', () => {
      const negativeProps = {
        ...defaultProps,
        value: {
          start_time: 'sunset',
          end_time: 'sunrise',
          start_offset_minutes: -90,
          end_offset_minutes: -45,
        },
      };

      render(<TimeWindowInput {...negativeProps} />);

      expect(screen.getByText(/90 minutes before sunset/i)).toBeInTheDocument();
      expect(screen.getByText(/45 minutes before sunrise/i)).toBeInTheDocument();
    });

    it('should handle positive offset correctly', () => {
      const positiveProps = {
        ...defaultProps,
        value: {
          start_time: 'sunset',
          end_time: 'sunrise',
          start_offset_minutes: 90,
          end_offset_minutes: 45,
        },
      };

      render(<TimeWindowInput {...positiveProps} />);

      expect(screen.getByText(/90 minutes after sunset/i)).toBeInTheDocument();
      expect(screen.getByText(/45 minutes after sunrise/i)).toBeInTheDocument();
    });
  });
});
