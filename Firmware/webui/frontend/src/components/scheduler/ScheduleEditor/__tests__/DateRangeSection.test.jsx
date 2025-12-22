import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import DateRangeSection from '../DateRangeSection';

describe('DateRangeSection', () => {
  const mockOnChange = vi.fn();

  const defaultProps = {
    value: {
      start_date: null,
      end_date: null,
    },
    onChange: mockOnChange,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should render start date and end date inputs', () => {
      render(<DateRangeSection {...defaultProps} />);

      expect(screen.getByLabelText(/start date/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/end date/i)).toBeInTheDocument();
    });

    it('should render with null values', () => {
      render(<DateRangeSection {...defaultProps} />);

      const startDateInput = screen.getByLabelText(/start date/i);
      const endDateInput = screen.getByLabelText(/end date/i);

      expect(startDateInput).toHaveValue('');
      expect(endDateInput).toHaveValue('');
    });

    it('should render with date values', () => {
      const propsWithDates = {
        ...defaultProps,
        value: {
          start_date: '2024-01-01',
          end_date: '2024-12-31',
        },
      };

      const { container } = render(<DateRangeSection {...propsWithDates} />);

      const startDateInput = container.querySelector('#start-date');
      const endDateInput = container.querySelector('#end-date');

      expect(startDateInput).toHaveValue('2024-01-01');
      expect(endDateInput).toHaveValue('2024-12-31');
    });

    it('should render clear buttons when dates are set', () => {
      const propsWithDates = {
        ...defaultProps,
        value: {
          start_date: '2024-01-01',
          end_date: '2024-12-31',
        },
      };

      render(<DateRangeSection {...propsWithDates} />);

      const clearButtons = screen.getAllByRole('button', { name: /clear/i });
      expect(clearButtons).toHaveLength(2);
    });

    it('should not render clear buttons when dates are null', () => {
      render(<DateRangeSection {...defaultProps} />);

      const clearButtons = screen.queryAllByRole('button', { name: /clear/i });
      expect(clearButtons).toHaveLength(0);
    });

    it('should show error messages from props', () => {
      const errorProps = {
        ...defaultProps,
        errors: {
          start_date: 'Start date is required',
          end_date: 'End date is required',
        },
      };

      render(<DateRangeSection {...errorProps} />);

      expect(screen.getByText('Start date is required')).toBeInTheDocument();
      expect(screen.getByText('End date is required')).toBeInTheDocument();
    });

    it('should respect disabled state', () => {
      render(<DateRangeSection {...defaultProps} disabled={true} />);

      const startDateInput = screen.getByLabelText(/start date/i);
      const endDateInput = screen.getByLabelText(/end date/i);

      expect(startDateInput).toBeDisabled();
      expect(endDateInput).toBeDisabled();
    });

    it('should apply dark mode styling', () => {
      document.documentElement.classList.add('dark');
      render(<DateRangeSection {...defaultProps} />);

      const startDateInput = screen.getByLabelText(/start date/i);
      expect(startDateInput).toHaveClass('dark:bg-gray-800');

      document.documentElement.classList.remove('dark');
    });
  });

  describe('Date Input', () => {
    it('should handle manual start date input', async () => {
      const user = userEvent.setup();
      render(<DateRangeSection {...defaultProps} />);

      const startDateInput = screen.getByLabelText(/start date/i);

      await user.type(startDateInput, '2024-06-15');

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith({
          start_date: '2024-06-15',
          end_date: null,
        });
      });
    });

    it('should handle manual end date input', async () => {
      const user = userEvent.setup();
      render(<DateRangeSection {...defaultProps} />);

      const endDateInput = screen.getByLabelText(/end date/i);

      await user.type(endDateInput, '2024-12-31');

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith({
          start_date: null,
          end_date: '2024-12-31',
        });
      });
    });

    it('should preserve existing values when changing one field', async () => {
      const user = userEvent.setup();
      const propsWithStartDate = {
        ...defaultProps,
        value: {
          start_date: '2024-01-01',
          end_date: null,
        },
      };

      render(<DateRangeSection {...propsWithStartDate} />);

      const endDateInput = screen.getByLabelText(/end date/i);
      await user.type(endDateInput, '2024-12-31');

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith({
          start_date: '2024-01-01',
          end_date: '2024-12-31',
        });
      });
    });
  });

  describe('Clear Functionality', () => {
    it('should clear start date when clear button clicked', async () => {
      const user = userEvent.setup();
      const propsWithDates = {
        ...defaultProps,
        value: {
          start_date: '2024-01-01',
          end_date: '2024-12-31',
        },
      };

      render(<DateRangeSection {...propsWithDates} />);

      const clearButtons = screen.getAllByRole('button', { name: /clear/i });
      const clearStartButton = clearButtons[0]; // First clear button is for start date

      await user.click(clearStartButton);

      expect(mockOnChange).toHaveBeenCalledWith({
        start_date: null,
        end_date: '2024-12-31',
      });
    });

    it('should clear end date when clear button clicked', async () => {
      const user = userEvent.setup();
      const propsWithDates = {
        ...defaultProps,
        value: {
          start_date: '2024-01-01',
          end_date: '2024-12-31',
        },
      };

      render(<DateRangeSection {...propsWithDates} />);

      const clearButtons = screen.getAllByRole('button', { name: /clear/i });
      const clearEndButton = clearButtons[1]; // Second clear button is for end date

      await user.click(clearEndButton);

      expect(mockOnChange).toHaveBeenCalledWith({
        start_date: '2024-01-01',
        end_date: null,
      });
    });

    it('should disable clear buttons when disabled prop is true', () => {
      const propsWithDates = {
        ...defaultProps,
        value: {
          start_date: '2024-01-01',
          end_date: '2024-12-31',
        },
        disabled: true,
      };

      render(<DateRangeSection {...propsWithDates} />);

      const clearButtons = screen.getAllByRole('button', { name: /clear/i });
      clearButtons.forEach((button) => {
        expect(button).toBeDisabled();
      });
    });
  });

  describe('Validation', () => {
    it('should show validation error when end_date < start_date', () => {
      const invalidProps = {
        ...defaultProps,
        value: {
          start_date: '2024-12-31',
          end_date: '2024-01-01',
        },
      };

      render(<DateRangeSection {...invalidProps} />);

      expect(screen.getByText(/end date must be greater than or equal to start date/i)).toBeInTheDocument();
    });

    it('should not show validation error when end_date >= start_date', () => {
      const validProps = {
        ...defaultProps,
        value: {
          start_date: '2024-01-01',
          end_date: '2024-12-31',
        },
      };

      render(<DateRangeSection {...validProps} />);

      expect(screen.queryByText(/end date must be greater than or equal to start date/i)).not.toBeInTheDocument();
    });

    it('should not show validation error when start_date is null', () => {
      const validProps = {
        ...defaultProps,
        value: {
          start_date: null,
          end_date: '2024-12-31',
        },
      };

      render(<DateRangeSection {...validProps} />);

      expect(screen.queryByText(/end date must be greater than or equal to start date/i)).not.toBeInTheDocument();
    });

    it('should not show validation error when end_date is null', () => {
      const validProps = {
        ...defaultProps,
        value: {
          start_date: '2024-01-01',
          end_date: null,
        },
      };

      render(<DateRangeSection {...validProps} />);

      expect(screen.queryByText(/end date must be greater than or equal to start date/i)).not.toBeInTheDocument();
    });

    it('should not show validation error when both dates are equal', () => {
      const validProps = {
        ...defaultProps,
        value: {
          start_date: '2024-06-15',
          end_date: '2024-06-15',
        },
      };

      render(<DateRangeSection {...validProps} />);

      expect(screen.queryByText(/end date must be greater than or equal to start date/i)).not.toBeInTheDocument();
    });
  });

  describe('Default Values', () => {
    it('should handle missing value prop gracefully', () => {
      const minimalProps = {
        onChange: mockOnChange,
      };

      render(<DateRangeSection {...minimalProps} />);

      expect(screen.getByLabelText(/start date/i)).toHaveValue('');
      expect(screen.getByLabelText(/end date/i)).toHaveValue('');
    });

    it('should default disabled to false', () => {
      render(<DateRangeSection {...defaultProps} />);

      const startDateInput = screen.getByLabelText(/start date/i);
      expect(startDateInput).not.toBeDisabled();
    });

    it('should default errors to empty object', () => {
      render(<DateRangeSection {...defaultProps} />);

      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels for date inputs', () => {
      render(<DateRangeSection {...defaultProps} />);

      expect(screen.getByLabelText(/start date/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/end date/i)).toBeInTheDocument();
    });

    it('should associate labels with inputs', () => {
      render(<DateRangeSection {...defaultProps} />);

      const startDateInput = screen.getByLabelText(/start date/i);
      const endDateInput = screen.getByLabelText(/end date/i);

      expect(startDateInput).toHaveAttribute('id', 'start-date');
      expect(endDateInput).toHaveAttribute('id', 'end-date');
    });

    it('should have clear button labels for screen readers', () => {
      const propsWithDates = {
        ...defaultProps,
        value: {
          start_date: '2024-01-01',
          end_date: '2024-12-31',
        },
      };

      render(<DateRangeSection {...propsWithDates} />);

      const clearButtons = screen.getAllByRole('button', { name: /clear/i });
      expect(clearButtons).toHaveLength(2);
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty string start_date gracefully', () => {
      const emptyProps = {
        ...defaultProps,
        value: {
          start_date: '',
          end_date: '2024-12-31',
        },
      };

      render(<DateRangeSection {...emptyProps} />);

      expect(screen.getByLabelText(/start date/i)).toHaveValue('');
    });

    it('should handle empty string end_date gracefully', () => {
      const emptyProps = {
        ...defaultProps,
        value: {
          start_date: '2024-01-01',
          end_date: '',
        },
      };

      render(<DateRangeSection {...emptyProps} />);

      expect(screen.getByLabelText(/end date/i)).toHaveValue('');
    });

    it('should handle invalid date format gracefully', () => {
      const invalidProps = {
        ...defaultProps,
        value: {
          start_date: 'invalid-date',
          end_date: '2024-12-31',
        },
      };

      // Should not crash
      expect(() => render(<DateRangeSection {...invalidProps} />)).not.toThrow();
    });
  });
});
