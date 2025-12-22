import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import PatternFilters from '../PatternFilters';

describe('PatternFilters', () => {
  const defaultProps = {
    category: 'all',
    onCategoryChange: vi.fn(),
    selectedTags: [],
    onTagsChange: vi.fn(),
    availableTags: [
      { tag: 'moth', count: 5 },
      { tag: 'uv', count: 3 },
      { tag: 'nightly', count: 2 },
      { tag: 'capture', count: 7 },
    ],
    searchQuery: '',
    onSearchChange: vi.fn(),
    viewMode: 'grid',
    onViewModeChange: vi.fn(),
    showViewToggle: true,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Category Filter', () => {
    it('renders three category buttons: All, Built-in, User', () => {
      render(<PatternFilters {...defaultProps} />);

      expect(screen.getByRole('button', { name: /all/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /built-in/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /user/i })).toBeInTheDocument();
    });

    it('"All" button is selected when category="all"', () => {
      render(<PatternFilters {...defaultProps} category="all" />);

      const allButton = screen.getByRole('button', { name: /all/i });
      expect(allButton).toHaveAttribute('aria-pressed', 'true');
    });

    it('"Built-in" button is selected when category="built-in"', () => {
      render(<PatternFilters {...defaultProps} category="built-in" />);

      const builtInButton = screen.getByRole('button', { name: /built-in/i });
      expect(builtInButton).toHaveAttribute('aria-pressed', 'true');
    });

    it('"User" button is selected when category="user"', () => {
      render(<PatternFilters {...defaultProps} category="user" />);

      const userButton = screen.getByRole('button', { name: /user/i });
      expect(userButton).toHaveAttribute('aria-pressed', 'true');
    });

    it('clicking category button calls onCategoryChange with new value', async () => {
      const user = userEvent.setup();
      render(<PatternFilters {...defaultProps} category="all" />);

      const builtInButton = screen.getByRole('button', { name: /built-in/i });
      await user.click(builtInButton);

      expect(defaultProps.onCategoryChange).toHaveBeenCalledWith('built-in');
    });

    it('selected category has distinct visual style', () => {
      render(<PatternFilters {...defaultProps} category="user" />);

      const userButton = screen.getByRole('button', { name: /user/i });
      const allButton = screen.getByRole('button', { name: /all/i });

      // Selected button should have blue background
      expect(userButton).toHaveClass('bg-blue-600');
      expect(userButton).toHaveClass('text-white');

      // Unselected button should have gray background
      expect(allButton).toHaveClass('bg-gray-100');
      expect(allButton).not.toHaveClass('text-white');
    });
  });

  describe('Tag Filter', () => {
    it('renders available tags as chips', () => {
      render(<PatternFilters {...defaultProps} />);

      expect(screen.getByText(/moth/)).toBeInTheDocument();
      expect(screen.getByText(/uv/)).toBeInTheDocument();
      expect(screen.getByText(/nightly/)).toBeInTheDocument();
      expect(screen.getByText(/capture/)).toBeInTheDocument();
    });

    it('tags show count in parentheses', () => {
      render(<PatternFilters {...defaultProps} />);

      expect(screen.getByText(/moth/)).toHaveTextContent('moth (5)');
      expect(screen.getByText(/uv/)).toHaveTextContent('uv (3)');
      expect(screen.getByText(/nightly/)).toHaveTextContent('nightly (2)');
      expect(screen.getByText(/capture/)).toHaveTextContent('capture (7)');
    });

    it('clicking unselected tag calls onTagsChange with tag added', async () => {
      const user = userEvent.setup();
      render(<PatternFilters {...defaultProps} selectedTags={[]} />);

      const mothTag = screen.getByText(/moth/).closest('button');
      await user.click(mothTag);

      expect(defaultProps.onTagsChange).toHaveBeenCalledWith(['moth']);
    });

    it('clicking selected tag calls onTagsChange with tag removed', async () => {
      const user = userEvent.setup();
      render(<PatternFilters {...defaultProps} selectedTags={['moth', 'uv']} />);

      const mothTag = screen.getByText(/moth/).closest('button');
      await user.click(mothTag);

      expect(defaultProps.onTagsChange).toHaveBeenCalledWith(['uv']);
    });

    it('selected tags have distinct styling', () => {
      render(<PatternFilters {...defaultProps} selectedTags={['moth']} />);

      const mothTag = screen.getByText(/moth/).closest('button');
      const uvTag = screen.getByText(/uv/).closest('button');

      // Selected tag should have blue background
      expect(mothTag).toHaveClass('bg-blue-600');
      expect(mothTag).toHaveClass('text-white');

      // Unselected tag should have gray background
      expect(uvTag).toHaveClass('bg-gray-100');
      expect(uvTag).not.toHaveClass('text-white');
    });

    it('empty availableTags renders nothing for tags section', () => {
      const { container } = render(
        <PatternFilters {...defaultProps} availableTags={[]} />
      );

      // Tags section should not exist or be empty
      const tagButtons = container.querySelectorAll('button[data-testid^="tag-"]');
      expect(tagButtons).toHaveLength(0);
    });

    it('multiple tags can be selected simultaneously', async () => {
      const user = userEvent.setup();
      render(<PatternFilters {...defaultProps} selectedTags={['moth']} />);

      const uvTag = screen.getByText(/uv/).closest('button');
      await user.click(uvTag);

      expect(defaultProps.onTagsChange).toHaveBeenCalledWith(['moth', 'uv']);
    });
  });

  describe('Search Filter', () => {
    it('renders search input with placeholder', () => {
      render(<PatternFilters {...defaultProps} />);

      const searchInput = screen.getByPlaceholderText(/search patterns/i);
      expect(searchInput).toBeInTheDocument();
    });

    it('search input shows current searchQuery value', () => {
      render(<PatternFilters {...defaultProps} searchQuery="moth" />);

      const searchInput = screen.getByPlaceholderText(/search patterns/i);
      expect(searchInput).toHaveValue('moth');
    });

    it('typing updates search value', async () => {
      const user = userEvent.setup();
      render(<PatternFilters {...defaultProps} />);

      const searchInput = screen.getByPlaceholderText(/search patterns/i);
      await user.type(searchInput, 'test');

      expect(searchInput).toHaveValue('test');
    });

    it('search is debounced (300ms) - onSearchChange not called immediately', async () => {
      const user = userEvent.setup();
      render(<PatternFilters {...defaultProps} />);

      const searchInput = screen.getByPlaceholderText(/search patterns/i);
      await user.type(searchInput, 'test');

      // Should not be called immediately
      expect(defaultProps.onSearchChange).not.toHaveBeenCalled();
    });

    it('search debounce calls onSearchChange after 300ms', async () => {
      const user = userEvent.setup();
      render(<PatternFilters {...defaultProps} />);

      const searchInput = screen.getByPlaceholderText(/search patterns/i);
      await user.type(searchInput, 'test');

      // Wait for debounce
      await waitFor(
        () => {
          expect(defaultProps.onSearchChange).toHaveBeenCalledWith('test');
        },
        { timeout: 500 }
      );
    });

    it('clear button appears when searchQuery is not empty', () => {
      render(<PatternFilters {...defaultProps} searchQuery="moth" />);

      const clearButton = screen.getByRole('button', { name: /clear search/i });
      expect(clearButton).toBeInTheDocument();
    });

    it('clear button clears searchQuery', async () => {
      const user = userEvent.setup();
      render(
        <PatternFilters {...defaultProps} searchQuery="moth" />
      );

      const clearButton = screen.getByRole('button', { name: /clear search/i });
      await user.click(clearButton);

      expect(defaultProps.onSearchChange).toHaveBeenCalledWith('');
    });

    it('empty searchQuery hides clear button', () => {
      render(<PatternFilters {...defaultProps} searchQuery="" />);

      const clearButton = screen.queryByRole('button', { name: /clear search/i });
      expect(clearButton).not.toBeInTheDocument();
    });
  });

  describe('View Mode Toggle', () => {
    it('renders grid and list view buttons when showViewToggle=true', () => {
      render(<PatternFilters {...defaultProps} showViewToggle={true} />);

      expect(screen.getByRole('button', { name: /grid view/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /list view/i })).toBeInTheDocument();
    });

    it('grid button selected when viewMode="grid"', () => {
      render(<PatternFilters {...defaultProps} viewMode="grid" />);

      const gridButton = screen.getByRole('button', { name: /grid view/i });
      expect(gridButton).toHaveAttribute('aria-pressed', 'true');
    });

    it('list button selected when viewMode="list"', () => {
      render(<PatternFilters {...defaultProps} viewMode="list" />);

      const listButton = screen.getByRole('button', { name: /list view/i });
      expect(listButton).toHaveAttribute('aria-pressed', 'true');
    });

    it('clicking toggles call onViewModeChange', async () => {
      const user = userEvent.setup();
      render(<PatternFilters {...defaultProps} viewMode="grid" />);

      const listButton = screen.getByRole('button', { name: /list view/i });
      await user.click(listButton);

      expect(defaultProps.onViewModeChange).toHaveBeenCalledWith('list');
    });

    it('toggle hidden when showViewToggle=false', () => {
      render(<PatternFilters {...defaultProps} showViewToggle={false} />);

      expect(
        screen.queryByRole('button', { name: /grid view/i })
      ).not.toBeInTheDocument();
      expect(
        screen.queryByRole('button', { name: /list view/i })
      ).not.toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('category buttons have aria-pressed attribute', () => {
      render(<PatternFilters {...defaultProps} category="built-in" />);

      const allButton = screen.getByRole('button', { name: /all/i });
      const builtInButton = screen.getByRole('button', { name: /built-in/i });
      const userButton = screen.getByRole('button', { name: /user/i });

      expect(allButton).toHaveAttribute('aria-pressed', 'false');
      expect(builtInButton).toHaveAttribute('aria-pressed', 'true');
      expect(userButton).toHaveAttribute('aria-pressed', 'false');
    });

    it('search input has proper label', () => {
      render(<PatternFilters {...defaultProps} />);

      const searchInput = screen.getByRole('textbox', { name: /search patterns/i });
      expect(searchInput).toBeInTheDocument();
    });

    it('view toggle buttons have aria-labels', () => {
      render(<PatternFilters {...defaultProps} />);

      expect(screen.getByRole('button', { name: /grid view/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /list view/i })).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('handles undefined availableTags gracefully', () => {
      render(
        <PatternFilters {...defaultProps} availableTags={undefined} />
      );

      // Should not crash and should render other components
      expect(screen.getByRole('button', { name: /all/i })).toBeInTheDocument();
    });

    it('handles undefined selectedTags gracefully', () => {
      render(<PatternFilters {...defaultProps} selectedTags={undefined} />);

      // Should not crash
      expect(screen.getByRole('button', { name: /all/i })).toBeInTheDocument();
    });

    it('handles empty searchQuery', () => {
      render(<PatternFilters {...defaultProps} searchQuery="" />);

      const searchInput = screen.getByPlaceholderText(/search patterns/i);
      expect(searchInput).toHaveValue('');
    });
  });
});
