import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import RangeSlider from '../RangeSlider';

describe('RangeSlider', () => {
  const defaultProps = {
    min: 0,
    max: 100,
    value: { min: 25, max: 75 },
    onChange: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders with default values', () => {
      render(<RangeSlider {...defaultProps} />);

      expect(screen.getByTestId('range-slider')).toBeInTheDocument();
      expect(screen.getByTestId('range-slider-min-handle')).toBeInTheDocument();
      expect(screen.getByTestId('range-slider-max-handle')).toBeInTheDocument();
    });

    it('renders without input fields when showInputs is false', () => {
      render(<RangeSlider {...defaultProps} showInputs={false} />);

      expect(screen.queryByTestId('range-slider-min-input')).not.toBeInTheDocument();
      expect(screen.queryByTestId('range-slider-max-input')).not.toBeInTheDocument();
    });

    it('renders input fields by default', () => {
      render(<RangeSlider {...defaultProps} />);

      const minInput = screen.getByTestId('range-slider-min-input');
      const maxInput = screen.getByTestId('range-slider-max-input');

      expect(minInput).toBeInTheDocument();
      expect(maxInput).toBeInTheDocument();
      expect(minInput).toHaveValue(25);
      expect(maxInput).toHaveValue(75);
    });

    it('applies disabled styles when disabled', () => {
      render(<RangeSlider {...defaultProps} disabled />);

      const minHandle = screen.getByTestId('range-slider-min-handle');
      const maxHandle = screen.getByTestId('range-slider-max-handle');
      const minInput = screen.getByTestId('range-slider-min-input');
      const maxInput = screen.getByTestId('range-slider-max-input');

      expect(minHandle).toHaveClass('cursor-not-allowed');
      expect(maxHandle).toHaveClass('cursor-not-allowed');
      expect(minInput).toBeDisabled();
      expect(maxInput).toBeDisabled();
    });

    it('displays formatted values with custom formatValue', async () => {
      const user = userEvent.setup();
      const formatValue = (val) => `$${val}`;

      render(<RangeSlider {...defaultProps} formatValue={formatValue} />);

      const minHandle = screen.getByTestId('range-slider-min-handle');

      // Hover to show tooltip
      await user.hover(minHandle);

      await waitFor(() => {
        expect(screen.getByText('$25')).toBeInTheDocument();
      });
    });
  });

  describe('Input Field Interaction', () => {
    it('updates min value via input field', async () => {
      const user = userEvent.setup();
      render(<RangeSlider {...defaultProps} />);

      const minInput = screen.getByTestId('range-slider-min-input');
      await user.clear(minInput);
      await user.type(minInput, '30');
      minInput.blur();

      expect(defaultProps.onChange).toHaveBeenCalledWith({ min: 30, max: 75 });
    });

    it('updates max value via input field', async () => {
      const user = userEvent.setup();
      render(<RangeSlider {...defaultProps} />);

      const maxInput = screen.getByTestId('range-slider-max-input');
      await user.clear(maxInput);
      await user.type(maxInput, '80');
      maxInput.blur();

      expect(defaultProps.onChange).toHaveBeenCalledWith({ min: 25, max: 80 });
    });

    it('prevents min from exceeding max via input', async () => {
      const user = userEvent.setup();
      render(<RangeSlider {...defaultProps} />);

      const minInput = screen.getByTestId('range-slider-min-input');
      await user.clear(minInput);
      await user.type(minInput, '90');
      minInput.blur();

      // Min should be clamped to max
      expect(defaultProps.onChange).toHaveBeenCalledWith({ min: 75, max: 75 });
    });

    it('prevents max from going below min via input', async () => {
      const user = userEvent.setup();
      render(<RangeSlider {...defaultProps} />);

      const maxInput = screen.getByTestId('range-slider-max-input');
      await user.clear(maxInput);
      await user.type(maxInput, '10');
      maxInput.blur();

      // Max should be clamped to min
      expect(defaultProps.onChange).toHaveBeenCalledWith({ min: 25, max: 25 });
    });

    it('respects step increment in input fields', async () => {
      const user = userEvent.setup();
      render(<RangeSlider {...defaultProps} step={5} />);

      const minInput = screen.getByTestId('range-slider-min-input');
      await user.clear(minInput);
      await user.type(minInput, '33');
      minInput.blur();

      // Should round to nearest step (35)
      expect(defaultProps.onChange).toHaveBeenCalledWith({ min: 35, max: 75 });
    });

    it('clamps input values to min/max bounds', async () => {
      const user = userEvent.setup();
      render(<RangeSlider {...defaultProps} />);

      const minInput = screen.getByTestId('range-slider-min-input');
      await user.clear(minInput);
      await user.type(minInput, '-50');
      minInput.blur();

      // Should clamp to min (0)
      expect(defaultProps.onChange).toHaveBeenCalledWith({ min: 0, max: 75 });
    });

    it('ignores invalid input values', async () => {
      const user = userEvent.setup();
      render(<RangeSlider {...defaultProps} />);

      const minInput = screen.getByTestId('range-slider-min-input');
      const originalValue = minInput.value;
      await user.clear(minInput);
      await user.type(minInput, 'abc');
      minInput.blur();

      // onChange should not be called for invalid input
      expect(defaultProps.onChange).not.toHaveBeenCalled();
      // Input should be reset to original value
      expect(minInput.value).toBe(originalValue);
    });
  });

  describe('Keyboard Navigation', () => {
    it('increments min value with arrow right', () => {
      render(<RangeSlider {...defaultProps} step={1} />);

      const minHandle = screen.getByTestId('range-slider-min-handle');
      minHandle.focus();
      fireEvent.keyDown(minHandle, { key: 'ArrowRight' });

      expect(defaultProps.onChange).toHaveBeenCalledWith({ min: 26, max: 75 });
    });

    it('decrements min value with arrow left', () => {
      render(<RangeSlider {...defaultProps} step={1} />);

      const minHandle = screen.getByTestId('range-slider-min-handle');
      minHandle.focus();
      fireEvent.keyDown(minHandle, { key: 'ArrowLeft' });

      expect(defaultProps.onChange).toHaveBeenCalledWith({ min: 24, max: 75 });
    });

    it('increments max value with arrow up', () => {
      render(<RangeSlider {...defaultProps} step={1} />);

      const maxHandle = screen.getByTestId('range-slider-max-handle');
      maxHandle.focus();
      fireEvent.keyDown(maxHandle, { key: 'ArrowUp' });

      expect(defaultProps.onChange).toHaveBeenCalledWith({ min: 25, max: 76 });
    });

    it('decrements max value with arrow down', () => {
      render(<RangeSlider {...defaultProps} step={1} />);

      const maxHandle = screen.getByTestId('range-slider-max-handle');
      maxHandle.focus();
      fireEvent.keyDown(maxHandle, { key: 'ArrowDown' });

      expect(defaultProps.onChange).toHaveBeenCalledWith({ min: 25, max: 74 });
    });

    it('moves min to start with Home key', () => {
      render(<RangeSlider {...defaultProps} />);

      const minHandle = screen.getByTestId('range-slider-min-handle');
      minHandle.focus();
      fireEvent.keyDown(minHandle, { key: 'Home' });

      expect(defaultProps.onChange).toHaveBeenCalledWith({ min: 0, max: 75 });
    });

    it('moves max to end with End key', () => {
      render(<RangeSlider {...defaultProps} />);

      const maxHandle = screen.getByTestId('range-slider-max-handle');
      maxHandle.focus();
      fireEvent.keyDown(maxHandle, { key: 'End' });

      expect(defaultProps.onChange).toHaveBeenCalledWith({ min: 25, max: 100 });
    });

    it('prevents min from exceeding max with keyboard', () => {
      render(<RangeSlider {...defaultProps} value={{ min: 74, max: 75 }} step={1} />);

      const minHandle = screen.getByTestId('range-slider-min-handle');
      minHandle.focus();
      fireEvent.keyDown(minHandle, { key: 'ArrowRight' });

      // Min should stay at max when trying to exceed
      expect(defaultProps.onChange).toHaveBeenCalledWith({ min: 75, max: 75 });
    });

    it('prevents max from going below min with keyboard', () => {
      render(<RangeSlider {...defaultProps} value={{ min: 25, max: 26 }} step={1} />);

      const maxHandle = screen.getByTestId('range-slider-max-handle');
      maxHandle.focus();
      fireEvent.keyDown(maxHandle, { key: 'ArrowDown' });

      // Max should stay at min when trying to go below
      expect(defaultProps.onChange).toHaveBeenCalledWith({ min: 25, max: 25 });
    });

    it('respects step size in keyboard navigation', () => {
      render(<RangeSlider {...defaultProps} step={10} />);

      const minHandle = screen.getByTestId('range-slider-min-handle');
      minHandle.focus();
      fireEvent.keyDown(minHandle, { key: 'ArrowRight' });

      expect(defaultProps.onChange).toHaveBeenCalledWith({ min: 35, max: 75 });
    });

    it('does not respond to keyboard when disabled', () => {
      render(<RangeSlider {...defaultProps} disabled />);

      const minHandle = screen.getByTestId('range-slider-min-handle');
      minHandle.focus();
      fireEvent.keyDown(minHandle, { key: 'ArrowRight' });

      expect(defaultProps.onChange).not.toHaveBeenCalled();
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA labels on handles', () => {
      render(<RangeSlider {...defaultProps} label="Price Range" />);

      const minHandle = screen.getByTestId('range-slider-min-handle');
      const maxHandle = screen.getByTestId('range-slider-max-handle');

      expect(minHandle).toHaveAttribute('aria-label', 'Price Range minimum');
      expect(maxHandle).toHaveAttribute('aria-label', 'Price Range maximum');
    });

    it('has proper ARIA values on handles', () => {
      render(<RangeSlider {...defaultProps} />);

      const minHandle = screen.getByTestId('range-slider-min-handle');
      const maxHandle = screen.getByTestId('range-slider-max-handle');

      expect(minHandle).toHaveAttribute('aria-valuemin', '0');
      expect(minHandle).toHaveAttribute('aria-valuemax', '100');
      expect(minHandle).toHaveAttribute('aria-valuenow', '25');

      expect(maxHandle).toHaveAttribute('aria-valuemin', '0');
      expect(maxHandle).toHaveAttribute('aria-valuemax', '100');
      expect(maxHandle).toHaveAttribute('aria-valuenow', '75');
    });

    it('has proper ARIA disabled state', () => {
      render(<RangeSlider {...defaultProps} disabled />);

      const minHandle = screen.getByTestId('range-slider-min-handle');
      const maxHandle = screen.getByTestId('range-slider-max-handle');

      expect(minHandle).toHaveAttribute('aria-disabled', 'true');
      expect(maxHandle).toHaveAttribute('aria-disabled', 'true');
    });

    it('has proper role on handles', () => {
      render(<RangeSlider {...defaultProps} />);

      const minHandle = screen.getByTestId('range-slider-min-handle');
      const maxHandle = screen.getByTestId('range-slider-max-handle');

      expect(minHandle).toHaveAttribute('role', 'slider');
      expect(maxHandle).toHaveAttribute('role', 'slider');
    });

    it('has proper ARIA labels on input fields', () => {
      render(<RangeSlider {...defaultProps} label="ISO Range" />);

      const minInput = screen.getByTestId('range-slider-min-input');
      const maxInput = screen.getByTestId('range-slider-max-input');

      expect(minInput).toHaveAttribute('aria-label', 'ISO Range minimum value');
      expect(maxInput).toHaveAttribute('aria-label', 'ISO Range maximum value');
    });

    it('handles can receive keyboard focus', () => {
      render(<RangeSlider {...defaultProps} />);

      const minHandle = screen.getByTestId('range-slider-min-handle');
      const maxHandle = screen.getByTestId('range-slider-max-handle');

      expect(minHandle).toHaveAttribute('tabindex', '0');
      expect(maxHandle).toHaveAttribute('tabindex', '0');
    });

    it('disabled handles cannot receive keyboard focus', () => {
      render(<RangeSlider {...defaultProps} disabled />);

      const minHandle = screen.getByTestId('range-slider-min-handle');
      const maxHandle = screen.getByTestId('range-slider-max-handle');

      expect(minHandle).toHaveAttribute('tabindex', '-1');
      expect(maxHandle).toHaveAttribute('tabindex', '-1');
    });
  });

  describe('Dark Mode', () => {
    it('applies dark mode classes to track', () => {
      const { container } = render(<RangeSlider {...defaultProps} />);

      const track = container.querySelector('.bg-gray-200');
      expect(track).toHaveClass('dark:bg-gray-700');
    });

    it('applies dark mode classes to handles', () => {
      render(<RangeSlider {...defaultProps} />);

      const minHandle = screen.getByTestId('range-slider-min-handle');
      expect(minHandle).toHaveClass('dark:bg-gray-800');
      expect(minHandle).toHaveClass('dark:border-blue-600');
    });

    it('applies dark mode classes to input fields', () => {
      render(<RangeSlider {...defaultProps} />);

      const minInput = screen.getByTestId('range-slider-min-input');
      expect(minInput).toHaveClass('dark:bg-gray-800');
      expect(minInput).toHaveClass('dark:border-gray-600');
      expect(minInput).toHaveClass('dark:text-gray-100');
    });
  });

  describe('Visual Feedback', () => {
    it('shows tooltip on min handle hover', async () => {
      const user = userEvent.setup();
      render(<RangeSlider {...defaultProps} />);

      const minHandle = screen.getByTestId('range-slider-min-handle');
      await user.hover(minHandle);

      await waitFor(() => {
        expect(screen.getByText('25')).toBeInTheDocument();
      });
    });

    it('shows tooltip on max handle hover', async () => {
      const user = userEvent.setup();
      render(<RangeSlider {...defaultProps} />);

      const maxHandle = screen.getByTestId('range-slider-max-handle');
      await user.hover(maxHandle);

      await waitFor(() => {
        expect(screen.getByText('75')).toBeInTheDocument();
      });
    });

    it('hides tooltip on mouse leave', async () => {
      const user = userEvent.setup();
      render(<RangeSlider {...defaultProps} />);

      const minHandle = screen.getByTestId('range-slider-min-handle');

      await user.hover(minHandle);
      await waitFor(() => {
        expect(screen.getByText('25')).toBeInTheDocument();
      });

      await user.unhover(minHandle);
      await waitFor(() => {
        expect(screen.queryByText('25')).not.toBeInTheDocument();
      });
    });
  });

  describe('Edge Cases', () => {
    it('handles min and max being equal', () => {
      render(<RangeSlider {...defaultProps} value={{ min: 50, max: 50 }} />);

      const minInput = screen.getByTestId('range-slider-min-input');
      const maxInput = screen.getByTestId('range-slider-max-input');

      expect(minInput).toHaveValue(50);
      expect(maxInput).toHaveValue(50);
    });

    it('handles full range selection', () => {
      render(<RangeSlider {...defaultProps} value={{ min: 0, max: 100 }} />);

      const minInput = screen.getByTestId('range-slider-min-input');
      const maxInput = screen.getByTestId('range-slider-max-input');

      expect(minInput).toHaveValue(0);
      expect(maxInput).toHaveValue(100);
    });

    it('handles zero range (min equals max)', () => {
      render(<RangeSlider min={50} max={50} value={{ min: 50, max: 50 }} onChange={vi.fn()} />);

      expect(screen.getByTestId('range-slider')).toBeInTheDocument();
    });

    it('handles fractional step values', async () => {
      render(<RangeSlider {...defaultProps} step={0.5} />);

      const minHandle = screen.getByTestId('range-slider-min-handle');
      minHandle.focus();
      fireEvent.keyDown(minHandle, { key: 'ArrowRight' });

      expect(defaultProps.onChange).toHaveBeenCalledWith({ min: 25.5, max: 75 });
    });

    it('handles large step values', () => {
      render(<RangeSlider {...defaultProps} step={25} />);

      const minHandle = screen.getByTestId('range-slider-min-handle');
      minHandle.focus();
      fireEvent.keyDown(minHandle, { key: 'ArrowRight' });

      expect(defaultProps.onChange).toHaveBeenCalledWith({ min: 50, max: 75 });
    });
  });
});
