import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import EventPatternSelector from '../EventPatternSelector';

// Mock PatternList
vi.mock('../../PatternLibrary', () => ({
  PatternList: ({ onPatternSelect, selectedPatternId, mode }) => (
    <div data-testid="pattern-list">
      <span data-testid="pattern-list-mode">{mode}</span>
      <span data-testid="pattern-list-selected">{selectedPatternId || 'none'}</span>
      <button
        data-testid="select-pattern-btn"
        onClick={() =>
          onPatternSelect({
            pattern_id: 'builtin-1',
            name: 'UV Capture Cycle',
            description: 'Standard UV capture cycle',
            actions: [
              { action_type: 'uv_on', offset_minutes: 0 },
              { action_type: 'take_photo', offset_minutes: 5 },
              { action_type: 'uv_off', offset_minutes: 15 },
            ],
            category: 'built-in',
            tags: ['capture', 'uv'],
          })
        }
      >
        Select UV Capture
      </button>
    </div>
  ),
}));

// Mock PatternEditor
vi.mock('../../PatternEditor', () => ({
  PatternEditor: ({ pattern, onSave, onCancel }) => (
    <div data-testid="pattern-editor">
      <span data-testid="editor-pattern-name">{pattern?.name || 'new'}</span>
      <button
        data-testid="save-pattern-btn"
        onClick={() =>
          onSave({
            pattern_id: 'custom-1',
            name: 'Custom Pattern',
            description: 'My custom pattern',
            actions: [{ action_type: 'take_photo', offset_minutes: 0 }],
            category: 'user',
            tags: ['custom'],
          })
        }
      >
        Save Pattern
      </button>
      <button data-testid="cancel-pattern-btn" onClick={onCancel}>
        Cancel
      </button>
    </div>
  ),
}));

// Helper to render with QueryClient
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

const renderWithClient = (ui) => {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
};

describe('EventPatternSelector', () => {
  let mockOnChange;

  beforeEach(() => {
    mockOnChange = vi.fn();
  });

  describe('Rendering', () => {
    it('renders section header', () => {
      renderWithClient(<EventPatternSelector onChange={mockOnChange} />);

      expect(screen.getByText('Event Pattern')).toBeInTheDocument();
    });

    it('renders source selection tabs', () => {
      renderWithClient(<EventPatternSelector onChange={mockOnChange} />);

      expect(screen.getByRole('tab', { name: /library/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /custom/i })).toBeInTheDocument();
    });

    it('shows Library tab as active by default', () => {
      renderWithClient(<EventPatternSelector onChange={mockOnChange} />);

      const libraryTab = screen.getByRole('tab', { name: /library/i });
      expect(libraryTab).toHaveAttribute('aria-selected', 'true');
    });

    it('renders PatternList in library mode', () => {
      renderWithClient(<EventPatternSelector onChange={mockOnChange} />);

      expect(screen.getByTestId('pattern-list')).toBeInTheDocument();
      expect(screen.getByTestId('pattern-list-mode')).toHaveTextContent(
        'embedded'
      );
    });
  });

  describe('Library Mode', () => {
    it('passes selectedPatternId to PatternList', () => {
      const value = {
        source: 'library',
        pattern: {
          pattern_id: 'test-pattern-123',
          name: 'Test Pattern',
          actions: [],
        },
      };

      renderWithClient(
        <EventPatternSelector value={value} onChange={mockOnChange} />
      );

      expect(screen.getByTestId('pattern-list-selected')).toHaveTextContent(
        'test-pattern-123'
      );
    });

    it('calls onChange when pattern is selected from library', () => {
      renderWithClient(<EventPatternSelector onChange={mockOnChange} />);

      const selectButton = screen.getByTestId('select-pattern-btn');
      fireEvent.click(selectButton);

      expect(mockOnChange).toHaveBeenCalledWith({
        source: 'library',
        pattern: expect.objectContaining({
          pattern_id: 'builtin-1',
          name: 'UV Capture Cycle',
        }),
      });
    });

    it('displays selected pattern summary', () => {
      const value = {
        source: 'library',
        pattern: {
          pattern_id: 'builtin-1',
          name: 'UV Capture Cycle',
          description: 'Standard UV capture cycle',
          actions: [
            { action_type: 'uv_on', offset_minutes: 0 },
            { action_type: 'take_photo', offset_minutes: 5 },
            { action_type: 'uv_off', offset_minutes: 15 },
          ],
        },
      };

      renderWithClient(
        <EventPatternSelector value={value} onChange={mockOnChange} />
      );

      expect(screen.getByText('UV Capture Cycle')).toBeInTheDocument();
      expect(screen.getByText('3 actions')).toBeInTheDocument();
    });
  });

  describe('Custom Mode', () => {
    it('switches to custom mode when Custom tab is clicked', () => {
      renderWithClient(<EventPatternSelector onChange={mockOnChange} />);

      const customTab = screen.getByRole('tab', { name: /custom/i });
      fireEvent.click(customTab);

      expect(customTab).toHaveAttribute('aria-selected', 'true');
      expect(screen.getByTestId('pattern-editor')).toBeInTheDocument();
    });

    it('shows PatternEditor in custom mode', () => {
      const value = {
        source: 'custom',
        pattern: {
          pattern_id: 'custom-1',
          name: 'My Custom Pattern',
          actions: [],
        },
      };

      renderWithClient(
        <EventPatternSelector value={value} onChange={mockOnChange} />
      );

      expect(screen.getByTestId('pattern-editor')).toBeInTheDocument();
    });

    it('passes existing pattern to PatternEditor in custom mode', () => {
      const value = {
        source: 'custom',
        pattern: {
          pattern_id: 'custom-1',
          name: 'My Custom Pattern',
          actions: [],
        },
      };

      renderWithClient(
        <EventPatternSelector value={value} onChange={mockOnChange} />
      );

      expect(screen.getByTestId('editor-pattern-name')).toHaveTextContent(
        'My Custom Pattern'
      );
    });

    it('calls onChange when custom pattern is saved', () => {
      renderWithClient(<EventPatternSelector onChange={mockOnChange} />);

      // Switch to custom mode
      const customTab = screen.getByRole('tab', { name: /custom/i });
      fireEvent.click(customTab);

      // Save pattern
      const saveButton = screen.getByTestId('save-pattern-btn');
      fireEvent.click(saveButton);

      expect(mockOnChange).toHaveBeenCalledWith({
        source: 'custom',
        pattern: expect.objectContaining({
          pattern_id: 'custom-1',
          name: 'Custom Pattern',
        }),
      });
    });

    it('cancels custom pattern editing and returns to library mode', () => {
      renderWithClient(<EventPatternSelector onChange={mockOnChange} />);

      // Switch to custom mode
      const customTab = screen.getByRole('tab', { name: /custom/i });
      fireEvent.click(customTab);

      // Cancel
      const cancelButton = screen.getByTestId('cancel-pattern-btn');
      fireEvent.click(cancelButton);

      // Should be back to library mode
      const libraryTab = screen.getByRole('tab', { name: /library/i });
      expect(libraryTab).toHaveAttribute('aria-selected', 'true');
    });
  });

  describe('Tab Switching', () => {
    it('preserves library selection when switching to custom and back', () => {
      renderWithClient(<EventPatternSelector onChange={mockOnChange} />);

      // Select a pattern from library
      const selectButton = screen.getByTestId('select-pattern-btn');
      fireEvent.click(selectButton);

      // Switch to custom mode
      const customTab = screen.getByRole('tab', { name: /custom/i });
      fireEvent.click(customTab);

      // Switch back to library mode
      const libraryTab = screen.getByRole('tab', { name: /library/i });
      fireEvent.click(libraryTab);

      // Selection should be preserved via onChange calls
      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({
          source: 'library',
        })
      );
    });

    it('updates source in value when switching tabs', () => {
      const value = {
        source: 'library',
        pattern: null,
      };

      renderWithClient(
        <EventPatternSelector value={value} onChange={mockOnChange} />
      );

      // Switch to custom mode
      const customTab = screen.getByRole('tab', { name: /custom/i });
      fireEvent.click(customTab);

      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({
          source: 'custom',
        })
      );
    });
  });

  describe('Disabled State', () => {
    it('disables tabs when disabled', () => {
      renderWithClient(
        <EventPatternSelector onChange={mockOnChange} disabled={true} />
      );

      const libraryTab = screen.getByRole('tab', { name: /library/i });
      const customTab = screen.getByRole('tab', { name: /custom/i });

      expect(libraryTab).toBeDisabled();
      expect(customTab).toBeDisabled();
    });
  });

  describe('Pattern Summary', () => {
    it('shows pattern name in summary', () => {
      const value = {
        source: 'library',
        pattern: {
          pattern_id: 'test-1',
          name: 'Test Pattern Name',
          actions: [],
        },
      };

      renderWithClient(
        <EventPatternSelector value={value} onChange={mockOnChange} />
      );

      expect(screen.getByText('Test Pattern Name')).toBeInTheDocument();
    });

    it('shows action count in summary', () => {
      const value = {
        source: 'library',
        pattern: {
          pattern_id: 'test-1',
          name: 'Test Pattern',
          actions: [
            { action_type: 'uv_on', offset_minutes: 0 },
            { action_type: 'take_photo', offset_minutes: 5 },
          ],
        },
      };

      renderWithClient(
        <EventPatternSelector value={value} onChange={mockOnChange} />
      );

      expect(screen.getByText('2 actions')).toBeInTheDocument();
    });

    it('shows singular "action" for single action', () => {
      const value = {
        source: 'library',
        pattern: {
          pattern_id: 'test-1',
          name: 'Test Pattern',
          actions: [{ action_type: 'take_photo', offset_minutes: 0 }],
        },
      };

      renderWithClient(
        <EventPatternSelector value={value} onChange={mockOnChange} />
      );

      expect(screen.getByText('1 action')).toBeInTheDocument();
    });

    it('shows "No pattern selected" when no pattern', () => {
      renderWithClient(<EventPatternSelector onChange={mockOnChange} />);

      expect(screen.getByText(/no pattern selected/i)).toBeInTheDocument();
    });

    it('allows clearing selected pattern', () => {
      const value = {
        source: 'library',
        pattern: {
          pattern_id: 'test-1',
          name: 'Test Pattern',
          actions: [],
        },
      };

      renderWithClient(
        <EventPatternSelector value={value} onChange={mockOnChange} />
      );

      const clearButton = screen.getByRole('button', { name: /clear/i });
      fireEvent.click(clearButton);

      expect(mockOnChange).toHaveBeenCalledWith({
        source: 'library',
        pattern: null,
      });
    });
  });

  describe('Dark Mode', () => {
    it('applies dark mode classes to section header', () => {
      renderWithClient(<EventPatternSelector onChange={mockOnChange} />);

      const header = screen.getByText('Event Pattern');
      expect(header).toHaveClass('dark:text-white');
    });

    it('applies dark mode classes to tabs', () => {
      renderWithClient(<EventPatternSelector onChange={mockOnChange} />);

      const libraryTab = screen.getByRole('tab', { name: /library/i });
      // Active tab should have dark mode styling
      expect(libraryTab.className).toMatch(/dark:/);
    });
  });

  describe('Error Handling', () => {
    it('shows error message when provided', () => {
      const errors = { pattern: 'Pattern is required' };

      renderWithClient(
        <EventPatternSelector onChange={mockOnChange} errors={errors} />
      );

      expect(screen.getByText('Pattern is required')).toBeInTheDocument();
    });
  });

  describe('Default Values', () => {
    it('uses library source by default', () => {
      renderWithClient(<EventPatternSelector onChange={mockOnChange} />);

      const libraryTab = screen.getByRole('tab', { name: /library/i });
      expect(libraryTab).toHaveAttribute('aria-selected', 'true');
    });

    it('uses provided value source', () => {
      const value = {
        source: 'custom',
        pattern: null,
      };

      renderWithClient(
        <EventPatternSelector value={value} onChange={mockOnChange} />
      );

      const customTab = screen.getByRole('tab', { name: /custom/i });
      expect(customTab).toHaveAttribute('aria-selected', 'true');
    });
  });
});
