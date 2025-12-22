import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import PatternCard from '../PatternCard';

describe('PatternCard', () => {
  const mockPattern = {
    pattern_id: 'test-pattern-1',
    name: 'Night Photography',
    description: 'Automated photography session during nighttime hours with multiple camera actions.',
    actions: [
      { action_type: 'camera.capture', action_name: 'Take Photo', offset_minutes: 0 },
      { action_type: 'gpio.on', action_name: 'Lights On', offset_minutes: 5 },
      { action_type: 'gpio.off', action_name: 'Lights Off', offset_minutes: 10 },
    ],
    category: 'built-in',
    tags: ['photography', 'night', 'automated'],
    duration_minutes: 15,
  };

  const mockOnClick = vi.fn();
  const mockOnSelect = vi.fn();

  beforeEach(() => {
    mockOnClick.mockClear();
    mockOnSelect.mockClear();
  });

  describe('Rendering Tests', () => {
    it('renders pattern name correctly', () => {
      render(<PatternCard pattern={mockPattern} onClick={mockOnClick} onSelect={mockOnSelect} />);
      expect(screen.getByText('Night Photography')).toBeInTheDocument();
    });

    it('renders description correctly', () => {
      render(<PatternCard pattern={mockPattern} onClick={mockOnClick} onSelect={mockOnSelect} />);
      expect(
        screen.getByText('Automated photography session during nighttime hours with multiple camera actions.')
      ).toBeInTheDocument();
    });

    it('renders description truncated to 2 lines if long', () => {
      const longPattern = {
        ...mockPattern,
        description:
          'This is a very long description that should be truncated to two lines with an ellipsis at the end. It contains multiple sentences and should demonstrate the line-clamp-2 behavior properly. This text goes on and on.',
      };
      const { container } = render(
        <PatternCard pattern={longPattern} onClick={mockOnClick} onSelect={mockOnSelect} />
      );
      const descElement = container.querySelector('.line-clamp-2');
      expect(descElement).toBeInTheDocument();
    });

    it('renders action count correctly', () => {
      render(<PatternCard pattern={mockPattern} onClick={mockOnClick} onSelect={mockOnSelect} />);
      expect(screen.getByText('3 actions')).toBeInTheDocument();
    });

    it('renders duration correctly', () => {
      render(<PatternCard pattern={mockPattern} onClick={mockOnClick} onSelect={mockOnSelect} />);
      expect(screen.getByText('15 min')).toBeInTheDocument();
    });

    it('renders category badge for built-in patterns', () => {
      render(<PatternCard pattern={mockPattern} onClick={mockOnClick} onSelect={mockOnSelect} />);
      expect(screen.getByText('built-in')).toBeInTheDocument();
    });

    it('renders category badge for user patterns with different styling', () => {
      const userPattern = { ...mockPattern, category: 'user' };
      render(<PatternCard pattern={userPattern} onClick={mockOnClick} onSelect={mockOnSelect} />);
      const badge = screen.getByText('user');
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass('bg-purple-100');
    });

    it('renders tags using TagChip component', () => {
      render(<PatternCard pattern={mockPattern} onClick={mockOnClick} onSelect={mockOnSelect} />);
      expect(screen.getByText('photography')).toBeInTheDocument();
      expect(screen.getByText('night')).toBeInTheDocument();
      expect(screen.getByText('automated')).toBeInTheDocument();
    });

    it('handles missing tags gracefully', () => {
      const patternNoTags = { ...mockPattern, tags: [] };
      const { container } = render(
        <PatternCard pattern={patternNoTags} onClick={mockOnClick} onSelect={mockOnSelect} />
      );
      expect(container.querySelector('.flex.flex-wrap.gap-1')).toBeInTheDocument();
    });

    it('handles missing description gracefully', () => {
      const patternNoDesc = { ...mockPattern, description: '' };
      render(<PatternCard pattern={patternNoDesc} onClick={mockOnClick} onSelect={mockOnSelect} />);
      // Should still render without error
      expect(screen.getByText('Night Photography')).toBeInTheDocument();
    });
  });

  describe('Interaction Tests', () => {
    it('calls onClick when card is clicked', async () => {
      const user = userEvent.setup();
      render(<PatternCard pattern={mockPattern} onClick={mockOnClick} onSelect={mockOnSelect} />);

      const card = screen.getByRole('article');
      await user.click(card);

      expect(mockOnClick).toHaveBeenCalledTimes(1);
      expect(mockOnClick).toHaveBeenCalledWith(mockPattern);
    });

    it('calls onSelect when "Use Pattern" button is clicked', async () => {
      const user = userEvent.setup();
      render(<PatternCard pattern={mockPattern} onClick={mockOnClick} onSelect={mockOnSelect} />);

      const button = screen.getByRole('button', { name: /use pattern/i });
      await user.click(button);

      expect(mockOnSelect).toHaveBeenCalledTimes(1);
      expect(mockOnSelect).toHaveBeenCalledWith(mockPattern);
    });

    it('button click does NOT trigger card onClick (stopPropagation)', async () => {
      const user = userEvent.setup();
      render(<PatternCard pattern={mockPattern} onClick={mockOnClick} onSelect={mockOnSelect} />);

      const button = screen.getByRole('button', { name: /use pattern/i });
      await user.click(button);

      expect(mockOnSelect).toHaveBeenCalledTimes(1);
      expect(mockOnClick).not.toHaveBeenCalled();
    });

    it('card is focusable with tabIndex=0', () => {
      render(<PatternCard pattern={mockPattern} onClick={mockOnClick} onSelect={mockOnSelect} />);
      const card = screen.getByRole('article');
      expect(card).toHaveAttribute('tabIndex', '0');
    });

    it('Enter key triggers onClick', async () => {
      const user = userEvent.setup();
      render(<PatternCard pattern={mockPattern} onClick={mockOnClick} onSelect={mockOnSelect} />);

      const card = screen.getByRole('article');
      card.focus();
      await user.keyboard('{Enter}');

      expect(mockOnClick).toHaveBeenCalledTimes(1);
      expect(mockOnClick).toHaveBeenCalledWith(mockPattern);
    });

    it('Space key triggers onClick', async () => {
      const user = userEvent.setup();
      render(<PatternCard pattern={mockPattern} onClick={mockOnClick} onSelect={mockOnSelect} />);

      const card = screen.getByRole('article');
      card.focus();
      await user.keyboard(' ');

      expect(mockOnClick).toHaveBeenCalledTimes(1);
      expect(mockOnClick).toHaveBeenCalledWith(mockPattern);
    });
  });

  describe('Visual State Tests', () => {
    it('isSelected=true shows selection ring/border', () => {
      render(
        <PatternCard pattern={mockPattern} onClick={mockOnClick} onSelect={mockOnSelect} isSelected={true} />
      );
      const card = screen.getByRole('article');
      expect(card).toHaveClass('ring-2');
      expect(card).toHaveClass('ring-blue-500');
    });

    it('isSelected=false does not show selection ring', () => {
      render(
        <PatternCard pattern={mockPattern} onClick={mockOnClick} onSelect={mockOnSelect} isSelected={false} />
      );
      const card = screen.getByRole('article');
      expect(card).not.toHaveClass('ring-2');
    });

    it('has hover state visual feedback', () => {
      render(<PatternCard pattern={mockPattern} onClick={mockOnClick} onSelect={mockOnSelect} />);
      const card = screen.getByRole('article');
      expect(card).toHaveClass('hover:shadow-lg');
    });

    it('has dark mode classes applied', () => {
      render(<PatternCard pattern={mockPattern} onClick={mockOnClick} onSelect={mockOnSelect} />);
      const card = screen.getByRole('article');
      expect(card).toHaveClass('dark:bg-gray-800');
      expect(card).toHaveClass('dark:border-gray-700');
    });
  });

  describe('Accessibility Tests', () => {
    it('has aria-label with pattern name', () => {
      render(<PatternCard pattern={mockPattern} onClick={mockOnClick} onSelect={mockOnSelect} />);
      const card = screen.getByRole('article');
      expect(card).toHaveAttribute('aria-label', 'Pattern: Night Photography');
    });

    it('button has accessible label "Use Pattern"', () => {
      render(<PatternCard pattern={mockPattern} onClick={mockOnClick} onSelect={mockOnSelect} />);
      const button = screen.getByRole('button', { name: /use pattern/i });
      expect(button).toBeInTheDocument();
    });

    it('card has cursor-pointer class for visual feedback', () => {
      render(<PatternCard pattern={mockPattern} onClick={mockOnClick} onSelect={mockOnSelect} />);
      const card = screen.getByRole('article');
      expect(card).toHaveClass('cursor-pointer');
    });
  });
});
