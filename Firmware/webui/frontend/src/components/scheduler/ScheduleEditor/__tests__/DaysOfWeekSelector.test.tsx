import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import DaysOfWeekSelector from '../DaysOfWeekSelector';

describe('DaysOfWeekSelector', () => {
  let mockOnChange: any;
  let user: ReturnType<typeof userEvent.setup>;

  beforeEach(() => {
    mockOnChange = vi.fn();
    user = userEvent.setup();
  });

  describe('Rendering', () => {
    it('renders all 7 day buttons', () => {
      render(<DaysOfWeekSelector value={[]} onChange={mockOnChange} />);

      expect(screen.getByRole('button', { name: 'Monday' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Tuesday' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Wednesday' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Thursday' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Friday' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Saturday' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Sunday' })).toBeInTheDocument();
    });

    it('renders "All Days" button', () => {
      render(<DaysOfWeekSelector value={[]} onChange={mockOnChange} />);

      expect(screen.getByRole('button', { name: 'All Days' })).toBeInTheDocument();
    });

    it('renders label text', () => {
      render(<DaysOfWeekSelector value={[]} onChange={mockOnChange} />);

      expect(screen.getByText('Days of Week')).toBeInTheDocument();
    });
  });

  describe('Selected State Display', () => {
    it('shows correct selected state for days in value array', () => {
      render(<DaysOfWeekSelector value={[0, 1, 2]} onChange={mockOnChange} />);

      // Monday, Tuesday, Wednesday selected
      expect(screen.getByRole('button', { name: 'Monday' })).toHaveAttribute(
        'aria-pressed',
        'true'
      );
      expect(screen.getByRole('button', { name: 'Tuesday' })).toHaveAttribute(
        'aria-pressed',
        'true'
      );
      expect(screen.getByRole('button', { name: 'Wednesday' })).toHaveAttribute(
        'aria-pressed',
        'true'
      );

      // Thursday-Sunday not selected
      expect(screen.getByRole('button', { name: 'Thursday' })).toHaveAttribute(
        'aria-pressed',
        'false'
      );
      expect(screen.getByRole('button', { name: 'Friday' })).toHaveAttribute(
        'aria-pressed',
        'false'
      );
      expect(screen.getByRole('button', { name: 'Saturday' })).toHaveAttribute(
        'aria-pressed',
        'false'
      );
      expect(screen.getByRole('button', { name: 'Sunday' })).toHaveAttribute(
        'aria-pressed',
        'false'
      );
    });

    it('shows all days selected when value is null', () => {
      render(<DaysOfWeekSelector value={null} onChange={mockOnChange} />);

      // All day buttons should be pressed
      expect(screen.getByRole('button', { name: 'Monday' })).toHaveAttribute(
        'aria-pressed',
        'true'
      );
      expect(screen.getByRole('button', { name: 'Tuesday' })).toHaveAttribute(
        'aria-pressed',
        'true'
      );
      expect(screen.getByRole('button', { name: 'Wednesday' })).toHaveAttribute(
        'aria-pressed',
        'true'
      );
      expect(screen.getByRole('button', { name: 'Thursday' })).toHaveAttribute(
        'aria-pressed',
        'true'
      );
      expect(screen.getByRole('button', { name: 'Friday' })).toHaveAttribute(
        'aria-pressed',
        'true'
      );
      expect(screen.getByRole('button', { name: 'Saturday' })).toHaveAttribute(
        'aria-pressed',
        'true'
      );
      expect(screen.getByRole('button', { name: 'Sunday' })).toHaveAttribute(
        'aria-pressed',
        'true'
      );

      // All Days button should also be pressed
      expect(screen.getByRole('button', { name: 'All Days' })).toHaveAttribute(
        'aria-pressed',
        'true'
      );
    });

    it('shows all days selected when value contains all 7 days', () => {
      render(
        <DaysOfWeekSelector
          value={[0, 1, 2, 3, 4, 5, 6]}
          onChange={mockOnChange}
        />
      );

      expect(screen.getByRole('button', { name: 'All Days' })).toHaveAttribute(
        'aria-pressed',
        'true'
      );
    });

    it('shows no days selected when value is empty array', () => {
      render(<DaysOfWeekSelector value={[]} onChange={mockOnChange} allowEmpty />);

      // No day buttons should be pressed
      expect(screen.getByRole('button', { name: 'Monday' })).toHaveAttribute(
        'aria-pressed',
        'false'
      );
      expect(screen.getByRole('button', { name: 'Tuesday' })).toHaveAttribute(
        'aria-pressed',
        'false'
      );
      expect(screen.getByRole('button', { name: 'Wednesday' })).toHaveAttribute(
        'aria-pressed',
        'false'
      );
      expect(screen.getByRole('button', { name: 'Thursday' })).toHaveAttribute(
        'aria-pressed',
        'false'
      );
      expect(screen.getByRole('button', { name: 'Friday' })).toHaveAttribute(
        'aria-pressed',
        'false'
      );
      expect(screen.getByRole('button', { name: 'Saturday' })).toHaveAttribute(
        'aria-pressed',
        'false'
      );
      expect(screen.getByRole('button', { name: 'Sunday' })).toHaveAttribute(
        'aria-pressed',
        'false'
      );

      // All Days button should not be pressed
      expect(screen.getByRole('button', { name: 'All Days' })).toHaveAttribute(
        'aria-pressed',
        'false'
      );
    });
  });

  describe('User Interactions - Individual Days', () => {
    it('toggles individual day on click (select)', async () => {
      render(<DaysOfWeekSelector value={[0, 1]} onChange={mockOnChange} />);

      await user.click(screen.getByRole('button', { name: 'Wednesday' }));

      expect(mockOnChange).toHaveBeenCalledTimes(1);
      expect(mockOnChange).toHaveBeenCalledWith([0, 1, 2]);
    });

    it('toggles individual day on click (deselect)', async () => {
      render(<DaysOfWeekSelector value={[0, 1, 2]} onChange={mockOnChange} />);

      await user.click(screen.getByRole('button', { name: 'Tuesday' }));

      expect(mockOnChange).toHaveBeenCalledTimes(1);
      expect(mockOnChange).toHaveBeenCalledWith([0, 2]);
    });

    it('adds day to selection when clicking unselected day', async () => {
      render(<DaysOfWeekSelector value={[5, 6]} onChange={mockOnChange} />);

      await user.click(screen.getByRole('button', { name: 'Monday' }));

      expect(mockOnChange).toHaveBeenCalledWith([0, 5, 6]);
    });

    it('removes day from selection when clicking selected day', async () => {
      render(<DaysOfWeekSelector value={[0, 1, 2, 3]} onChange={mockOnChange} />);

      await user.click(screen.getByRole('button', { name: 'Wednesday' }));

      expect(mockOnChange).toHaveBeenCalledWith([0, 1, 3]);
    });

    it('converts to null when selecting 7th day (all days)', async () => {
      render(
        <DaysOfWeekSelector value={[0, 1, 2, 3, 4, 5]} onChange={mockOnChange} />
      );

      await user.click(screen.getByRole('button', { name: 'Sunday' }));

      expect(mockOnChange).toHaveBeenCalledWith(null);
    });

    it('maintains sorted order when selecting days', async () => {
      render(<DaysOfWeekSelector value={[1, 3, 5]} onChange={mockOnChange} />);

      // Click Thursday (3 is already selected, so we add Friday first)
      await user.click(screen.getByRole('button', { name: 'Monday' }));

      expect(mockOnChange).toHaveBeenCalledWith([0, 1, 3, 5]);
    });

    it('handles selecting days from null (all days) state', async () => {
      render(<DaysOfWeekSelector value={null} onChange={mockOnChange} />);

      // Clicking a day when all are selected should deselect that day
      await user.click(screen.getByRole('button', { name: 'Wednesday' }));

      expect(mockOnChange).toHaveBeenCalledWith([0, 1, 3, 4, 5, 6]);
    });
  });

  describe('All Days Button', () => {
    it('sets value to null when clicking "All Days" button', async () => {
      render(<DaysOfWeekSelector value={[0, 1, 2]} onChange={mockOnChange} />);

      await user.click(screen.getByRole('button', { name: 'All Days' }));

      expect(mockOnChange).toHaveBeenCalledWith(null);
    });

    it('sets value to null when clicking "All Days" from empty state', async () => {
      render(<DaysOfWeekSelector value={[]} onChange={mockOnChange} allowEmpty />);

      await user.click(screen.getByRole('button', { name: 'All Days' }));

      expect(mockOnChange).toHaveBeenCalledWith(null);
    });

    it('sets value to null when clicking "All Days" from partial selection', async () => {
      render(<DaysOfWeekSelector value={[5, 6]} onChange={mockOnChange} />);

      await user.click(screen.getByRole('button', { name: 'All Days' }));

      expect(mockOnChange).toHaveBeenCalledWith(null);
    });

    it('is idempotent when clicking "All Days" multiple times', async () => {
      render(<DaysOfWeekSelector value={null} onChange={mockOnChange} />);

      await user.click(screen.getByRole('button', { name: 'All Days' }));
      await user.click(screen.getByRole('button', { name: 'All Days' }));

      expect(mockOnChange).toHaveBeenCalledTimes(2);
      expect(mockOnChange).toHaveBeenNthCalledWith(1, null);
      expect(mockOnChange).toHaveBeenNthCalledWith(2, null);
    });
  });

  describe('Empty Selection Validation', () => {
    it('prevents empty selection when allowEmpty=false (default)', async () => {
      render(<DaysOfWeekSelector value={[3]} onChange={mockOnChange} />);

      // Try to deselect the last day
      await user.click(screen.getByRole('button', { name: 'Thursday' }));

      // onChange should not be called
      expect(mockOnChange).not.toHaveBeenCalled();
    });

    it('allows empty selection when allowEmpty=true', async () => {
      render(
        <DaysOfWeekSelector value={[3]} onChange={mockOnChange} allowEmpty />
      );

      // Deselect the last day
      await user.click(screen.getByRole('button', { name: 'Thursday' }));

      expect(mockOnChange).toHaveBeenCalledWith([]);
    });

    it('prevents deselecting second-to-last day when allowEmpty=false', async () => {
      const { rerender } = render(
        <DaysOfWeekSelector value={[2, 3]} onChange={mockOnChange} />
      );

      // Deselect one day (still has one left)
      await user.click(screen.getByRole('button', { name: 'Wednesday' }));
      expect(mockOnChange).toHaveBeenCalledWith([3]);

      // Now rerender with single day and try to deselect - should be prevented
      mockOnChange.mockClear();
      rerender(<DaysOfWeekSelector value={[3]} onChange={mockOnChange} />);

      await user.click(screen.getByRole('button', { name: 'Thursday' }));
      expect(mockOnChange).not.toHaveBeenCalled();
    });
  });

  describe('Compact Mode', () => {
    it('shows single-letter labels when compact=true', () => {
      render(<DaysOfWeekSelector value={[]} onChange={mockOnChange} compact />);

      expect(screen.getByRole('button', { name: 'Monday' })).toHaveTextContent('M');
      expect(screen.getByRole('button', { name: 'Tuesday' })).toHaveTextContent('T');
      expect(screen.getByRole('button', { name: 'Wednesday' })).toHaveTextContent('W');
      expect(screen.getByRole('button', { name: 'Thursday' })).toHaveTextContent('T');
      expect(screen.getByRole('button', { name: 'Friday' })).toHaveTextContent('F');
      expect(screen.getByRole('button', { name: 'Saturday' })).toHaveTextContent('S');
      expect(screen.getByRole('button', { name: 'Sunday' })).toHaveTextContent('S');
    });

    it('shows short labels when compact=false (default)', () => {
      render(<DaysOfWeekSelector value={[]} onChange={mockOnChange} />);

      expect(screen.getByRole('button', { name: 'Monday' })).toHaveTextContent('Mon');
      expect(screen.getByRole('button', { name: 'Tuesday' })).toHaveTextContent('Tue');
      expect(screen.getByRole('button', { name: 'Wednesday' })).toHaveTextContent('Wed');
      expect(screen.getByRole('button', { name: 'Thursday' })).toHaveTextContent('Thu');
      expect(screen.getByRole('button', { name: 'Friday' })).toHaveTextContent('Fri');
      expect(screen.getByRole('button', { name: 'Saturday' })).toHaveTextContent('Sat');
      expect(screen.getByRole('button', { name: 'Sunday' })).toHaveTextContent('Sun');
    });

    it('compact mode buttons still have full aria-label', () => {
      render(<DaysOfWeekSelector value={[]} onChange={mockOnChange} compact />);

      // Even in compact mode, aria-label should be full day name
      expect(screen.getByRole('button', { name: 'Monday' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Tuesday' })).toBeInTheDocument();
    });
  });

  describe('Disabled State', () => {
    it('respects disabled state on all buttons', () => {
      render(<DaysOfWeekSelector value={[0]} onChange={mockOnChange} disabled />);

      expect(screen.getByRole('button', { name: 'Monday' })).toBeDisabled();
      expect(screen.getByRole('button', { name: 'Tuesday' })).toBeDisabled();
      expect(screen.getByRole('button', { name: 'Wednesday' })).toBeDisabled();
      expect(screen.getByRole('button', { name: 'Thursday' })).toBeDisabled();
      expect(screen.getByRole('button', { name: 'Friday' })).toBeDisabled();
      expect(screen.getByRole('button', { name: 'Saturday' })).toBeDisabled();
      expect(screen.getByRole('button', { name: 'Sunday' })).toBeDisabled();
      expect(screen.getByRole('button', { name: 'All Days' })).toBeDisabled();
    });

    it('does not call onChange when disabled and clicked', async () => {
      render(<DaysOfWeekSelector value={[0]} onChange={mockOnChange} disabled />);

      await user.click(screen.getByRole('button', { name: 'Tuesday' }));

      expect(mockOnChange).not.toHaveBeenCalled();
    });

    it('applies opacity styling when disabled', () => {
      render(<DaysOfWeekSelector value={[0]} onChange={mockOnChange} disabled />);

      const mondayButton = screen.getByRole('button', { name: 'Monday' });
      expect(mondayButton).toHaveClass('opacity-50');
      expect(mondayButton).toHaveClass('cursor-not-allowed');
    });
  });

  describe('Accessibility', () => {
    it('has correct aria-pressed attributes for selected days', () => {
      render(<DaysOfWeekSelector value={[0, 2, 4]} onChange={mockOnChange} />);

      expect(screen.getByRole('button', { name: 'Monday' })).toHaveAttribute(
        'aria-pressed',
        'true'
      );
      expect(screen.getByRole('button', { name: 'Tuesday' })).toHaveAttribute(
        'aria-pressed',
        'false'
      );
      expect(screen.getByRole('button', { name: 'Wednesday' })).toHaveAttribute(
        'aria-pressed',
        'true'
      );
      expect(screen.getByRole('button', { name: 'Thursday' })).toHaveAttribute(
        'aria-pressed',
        'false'
      );
      expect(screen.getByRole('button', { name: 'Friday' })).toHaveAttribute(
        'aria-pressed',
        'true'
      );
    });

    it('has correct aria-pressed for All Days button', () => {
      const { rerender } = render(
        <DaysOfWeekSelector value={[0, 1]} onChange={mockOnChange} />
      );

      expect(screen.getByRole('button', { name: 'All Days' })).toHaveAttribute(
        'aria-pressed',
        'false'
      );

      rerender(<DaysOfWeekSelector value={null} onChange={mockOnChange} />);

      expect(screen.getByRole('button', { name: 'All Days' })).toHaveAttribute(
        'aria-pressed',
        'true'
      );
    });

    it('has aria-label for each day button', () => {
      render(<DaysOfWeekSelector value={[]} onChange={mockOnChange} />);

      expect(screen.getByRole('button', { name: 'Monday' })).toHaveAttribute(
        'aria-label',
        'Monday'
      );
      expect(screen.getByRole('button', { name: 'Tuesday' })).toHaveAttribute(
        'aria-label',
        'Tuesday'
      );
      expect(screen.getByRole('button', { name: 'Wednesday' })).toHaveAttribute(
        'aria-label',
        'Wednesday'
      );
    });

    it('buttons are keyboard accessible', async () => {
      render(<DaysOfWeekSelector value={[]} onChange={mockOnChange} />);

      const mondayButton = screen.getByRole('button', { name: 'Monday' });
      mondayButton.focus();

      expect(mondayButton).toHaveFocus();
    });
  });

  describe('Dark Mode Styling', () => {
    it('applies dark mode classes to buttons', () => {
      render(<DaysOfWeekSelector value={[0]} onChange={mockOnChange} />);

      const mondayButton = screen.getByRole('button', { name: 'Monday' });
      expect(mondayButton.className).toContain('dark:');
    });

    it('applies dark mode classes to All Days button', () => {
      render(<DaysOfWeekSelector value={[0]} onChange={mockOnChange} />);

      const allDaysButton = screen.getByRole('button', { name: 'All Days' });
      expect(allDaysButton.className).toContain('dark:');
    });

    it('applies dark mode classes to label', () => {
      render(<DaysOfWeekSelector value={[0]} onChange={mockOnChange} />);

      const label = screen.getByText('Days of Week');
      expect(label.className).toContain('dark:text-gray-300');
    });
  });

  describe('Edge Cases', () => {
    it('handles undefined value as null (all days)', () => {
      render(<DaysOfWeekSelector value={undefined as any} onChange={mockOnChange} />);

      // All days should be shown as selected
      expect(screen.getByRole('button', { name: 'Monday' })).toHaveAttribute(
        'aria-pressed',
        'true'
      );
      expect(screen.getByRole('button', { name: 'All Days' })).toHaveAttribute(
        'aria-pressed',
        'true'
      );
    });

    it('handles out-of-order value array', () => {
      render(<DaysOfWeekSelector value={[5, 2, 0]} onChange={mockOnChange} />);

      expect(screen.getByRole('button', { name: 'Monday' })).toHaveAttribute(
        'aria-pressed',
        'true'
      );
      expect(screen.getByRole('button', { name: 'Wednesday' })).toHaveAttribute(
        'aria-pressed',
        'true'
      );
      expect(screen.getByRole('button', { name: 'Saturday' })).toHaveAttribute(
        'aria-pressed',
        'true'
      );
    });

    it('handles duplicate values in array', () => {
      render(<DaysOfWeekSelector value={[0, 0, 1, 1]} onChange={mockOnChange} />);

      // Should still work correctly despite duplicates
      expect(screen.getByRole('button', { name: 'Monday' })).toHaveAttribute(
        'aria-pressed',
        'true'
      );
      expect(screen.getByRole('button', { name: 'Tuesday' })).toHaveAttribute(
        'aria-pressed',
        'true'
      );
    });

    it('does not break with invalid day values in array', () => {
      // This shouldn't happen in practice, but component should be resilient
      render(<DaysOfWeekSelector value={[0, 1, 99]} onChange={mockOnChange} />);

      // Valid days should still work
      expect(screen.getByRole('button', { name: 'Monday' })).toHaveAttribute(
        'aria-pressed',
        'true'
      );
      expect(screen.getByRole('button', { name: 'Tuesday' })).toHaveAttribute(
        'aria-pressed',
        'true'
      );
    });
  });
});
