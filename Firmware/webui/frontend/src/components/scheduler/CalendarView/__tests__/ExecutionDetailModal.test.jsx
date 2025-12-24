import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ExecutionDetailModal from '../ExecutionDetailModal';

// Mock child components
vi.mock('../MoonPhaseIcon', () => ({
  default: ({ phase, size }) => (
    <div data-testid="moon-phase-icon" data-phase={phase.phase_name} data-size={size}>
      {phase.phase_name}
    </div>
  ),
}));

vi.mock('../calendarUtils', () => ({
  formatTime: (isoString) => {
    // Simple mock: extract time portion
    const date = new Date(isoString);
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  },
  getPatternColor: (patternId) => {
    // Return predictable colors for testing
    const colors = {
      'pattern-1': 'bg-blue-500',
      'pattern-2': 'bg-red-500',
      'pattern-3': 'bg-green-500',
    };
    return colors[patternId] || 'bg-gray-500';
  },
}));

describe('ExecutionDetailModal', () => {
  const mockOnClose = vi.fn();

  const mockExecution = {
    pattern_id: 'pattern-1',
    pattern_name: 'Night Photography',
    start_time: '2025-01-15T20:00:00',
    end_time: '2025-01-15T22:00:00',
    trigger_info: 'Triggered by sunset',
    actions: [
      {
        time: '2025-01-15T20:00:00',
        action_name: 'Turn on lights',
        action_type: 'gpio',
        offset_minutes: 0,
        description: 'Enable attract lights',
      },
      {
        time: '2025-01-15T20:15:00',
        action_name: 'Take photo',
        action_type: 'camera',
        offset_minutes: 15,
        description: 'Capture image',
      },
      {
        time: '2025-01-15T20:30:00',
        action_name: 'Sync GPS',
        action_type: 'gps_sync',
        offset_minutes: 30,
        description: 'Update GPS data',
      },
    ],
  };

  const mockMoonPhase = {
    phase_name: 'Full Moon',
    illumination: 1.0,
  };

  beforeEach(() => {
    mockOnClose.mockClear();
  });

  describe('Rendering', () => {
    it('renders when isOpen is true', () => {
      render(
        <ExecutionDetailModal
          isOpen={true}
          onClose={mockOnClose}
          execution={mockExecution}
          moonPhase={mockMoonPhase}
        />
      );

      expect(screen.getByText('Night Photography')).toBeInTheDocument();
    });

    it('does not render when isOpen is false', () => {
      const { container } = render(
        <ExecutionDetailModal
          isOpen={false}
          onClose={mockOnClose}
          execution={mockExecution}
          moonPhase={mockMoonPhase}
        />
      );

      expect(container.firstChild).toBeNull();
    });

    it('does not render when execution is null', () => {
      const { container } = render(
        <ExecutionDetailModal
          isOpen={true}
          onClose={mockOnClose}
          execution={null}
          moonPhase={mockMoonPhase}
        />
      );

      expect(container.firstChild).toBeNull();
    });

    it('has proper accessibility attributes', () => {
      render(
        <ExecutionDetailModal
          isOpen={true}
          onClose={mockOnClose}
          execution={mockExecution}
          moonPhase={mockMoonPhase}
        />
      );

      const dialog = screen.getByRole('dialog');
      expect(dialog).toHaveAttribute('aria-modal', 'true');
      expect(dialog).toHaveAttribute('aria-labelledby', 'modal-title');
    });
  });

  describe('Pattern Information', () => {
    it('shows pattern name with color indicator', () => {
      render(
        <ExecutionDetailModal
          isOpen={true}
          onClose={mockOnClose}
          execution={mockExecution}
          moonPhase={mockMoonPhase}
        />
      );

      expect(screen.getByText('Night Photography')).toBeInTheDocument();
      const colorIndicator = screen.getByText('Night Photography').previousSibling;
      expect(colorIndicator).toHaveClass('bg-blue-500');
    });

    it('applies different colors for different pattern IDs', () => {
      const execution2 = { ...mockExecution, pattern_id: 'pattern-2' };

      const { rerender } = render(
        <ExecutionDetailModal
          isOpen={true}
          onClose={mockOnClose}
          execution={mockExecution}
          moonPhase={null}
        />
      );

      let colorIndicator = screen.getByText('Night Photography').previousSibling;
      expect(colorIndicator).toHaveClass('bg-blue-500');

      rerender(
        <ExecutionDetailModal
          isOpen={true}
          onClose={mockOnClose}
          execution={execution2}
          moonPhase={null}
        />
      );

      colorIndicator = screen.getByText('Night Photography').previousSibling;
      expect(colorIndicator).toHaveClass('bg-red-500');
    });
  });

  describe('Time Information', () => {
    it('shows start and end times', () => {
      render(
        <ExecutionDetailModal
          isOpen={true}
          onClose={mockOnClose}
          execution={mockExecution}
          moonPhase={mockMoonPhase}
        />
      );

      // Check that times are displayed (mocked formatTime returns locale time)
      const timeDisplay = screen.getByText(/08:00 PM - 10:00 PM/i);
      expect(timeDisplay).toBeInTheDocument();
    });
  });

  describe('Trigger Information', () => {
    it('shows trigger info when present', () => {
      render(
        <ExecutionDetailModal
          isOpen={true}
          onClose={mockOnClose}
          execution={mockExecution}
          moonPhase={mockMoonPhase}
        />
      );

      expect(screen.getByText('Triggered by sunset')).toBeInTheDocument();
    });

    it('does not show trigger info section when not present', () => {
      const executionNoTrigger = { ...mockExecution, trigger_info: null };

      render(
        <ExecutionDetailModal
          isOpen={true}
          onClose={mockOnClose}
          execution={executionNoTrigger}
          moonPhase={mockMoonPhase}
        />
      );

      expect(screen.queryByText('Triggered by sunset')).not.toBeInTheDocument();
    });
  });

  describe('Moon Phase', () => {
    it('shows moon phase when present', () => {
      render(
        <ExecutionDetailModal
          isOpen={true}
          onClose={mockOnClose}
          execution={mockExecution}
          moonPhase={mockMoonPhase}
        />
      );

      expect(screen.getByTestId('moon-phase-icon')).toBeInTheDocument();
      expect(screen.getByTestId('moon-phase-icon')).toHaveAttribute(
        'data-phase',
        'Full Moon'
      );
      expect(screen.getByTestId('moon-phase-icon')).toHaveAttribute('data-size', 'md');

      // Check for the span with text-sm class (the label, not the icon mock content)
      const moonPhaseLabel = screen.getByText('Full Moon', {
        selector: 'span.text-sm'
      });
      expect(moonPhaseLabel).toBeInTheDocument();
    });

    it('does not show moon phase section when not present', () => {
      render(
        <ExecutionDetailModal
          isOpen={true}
          onClose={mockOnClose}
          execution={mockExecution}
          moonPhase={null}
        />
      );

      expect(screen.queryByTestId('moon-phase-icon')).not.toBeInTheDocument();
    });
  });

  describe('Actions List', () => {
    it('lists all actions with offsets', () => {
      render(
        <ExecutionDetailModal
          isOpen={true}
          onClose={mockOnClose}
          execution={mockExecution}
          moonPhase={mockMoonPhase}
        />
      );

      expect(screen.getByText('Actions')).toBeInTheDocument();
      expect(screen.getByText('Turn on lights')).toBeInTheDocument();
      expect(screen.getByText('Take photo')).toBeInTheDocument();
      expect(screen.getByText('Sync GPS')).toBeInTheDocument();

      expect(screen.getByText('+0m')).toBeInTheDocument();
      expect(screen.getByText('+15m')).toBeInTheDocument();
      expect(screen.getByText('+30m')).toBeInTheDocument();
    });

    it('shows action type badges with correct colors', () => {
      render(
        <ExecutionDetailModal
          isOpen={true}
          onClose={mockOnClose}
          execution={mockExecution}
          moonPhase={mockMoonPhase}
        />
      );

      const gpioBadge = screen.getByText('gpio');
      expect(gpioBadge).toHaveClass('bg-yellow-100', 'text-yellow-800');

      const cameraBadge = screen.getByText('camera');
      expect(cameraBadge).toHaveClass('bg-green-100', 'text-green-800');

      const gpsSyncBadge = screen.getByText('gps_sync');
      expect(gpsSyncBadge).toHaveClass('bg-blue-100', 'text-blue-800');
    });

    it('handles service action type', () => {
      const executionWithService = {
        ...mockExecution,
        actions: [
          {
            time: '2025-01-15T20:00:00',
            action_name: 'Start service',
            action_type: 'service',
            offset_minutes: 0,
          },
        ],
      };

      render(
        <ExecutionDetailModal
          isOpen={true}
          onClose={mockOnClose}
          execution={executionWithService}
          moonPhase={null}
        />
      );

      const serviceBadge = screen.getByText('service');
      expect(serviceBadge).toHaveClass('bg-purple-100', 'text-purple-800');
    });

    it('handles unknown action type with default color', () => {
      const executionWithUnknown = {
        ...mockExecution,
        actions: [
          {
            time: '2025-01-15T20:00:00',
            action_name: 'Unknown action',
            action_type: 'unknown_type',
            offset_minutes: 0,
          },
        ],
      };

      render(
        <ExecutionDetailModal
          isOpen={true}
          onClose={mockOnClose}
          execution={executionWithUnknown}
          moonPhase={null}
        />
      );

      const unknownBadge = screen.getByText('unknown_type');
      expect(unknownBadge).toHaveClass('bg-gray-100', 'text-gray-800');
    });

    it('does not show actions section when empty', () => {
      const executionNoActions = { ...mockExecution, actions: [] };

      render(
        <ExecutionDetailModal
          isOpen={true}
          onClose={mockOnClose}
          execution={executionNoActions}
          moonPhase={mockMoonPhase}
        />
      );

      expect(screen.queryByText('Actions')).not.toBeInTheDocument();
    });

    it('does not show actions section when undefined', () => {
      const executionNoActions = { ...mockExecution, actions: undefined };

      render(
        <ExecutionDetailModal
          isOpen={true}
          onClose={mockOnClose}
          execution={executionNoActions}
          moonPhase={mockMoonPhase}
        />
      );

      expect(screen.queryByText('Actions')).not.toBeInTheDocument();
    });
  });

  describe('Close Interactions', () => {
    it('closes on close button click', () => {
      render(
        <ExecutionDetailModal
          isOpen={true}
          onClose={mockOnClose}
          execution={mockExecution}
          moonPhase={mockMoonPhase}
        />
      );

      const closeButton = screen.getByLabelText('Close');
      fireEvent.click(closeButton);

      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });

    it('attaches event listener when modal is open', () => {
      const addEventListenerSpy = vi.spyOn(window, 'addEventListener');
      const removeEventListenerSpy = vi.spyOn(window, 'removeEventListener');

      render(
        <ExecutionDetailModal
          isOpen={true}
          onClose={mockOnClose}
          execution={mockExecution}
          moonPhase={mockMoonPhase}
        />
      );

      // Verify addEventListener was called for keydown when modal is open
      expect(addEventListenerSpy).toHaveBeenCalledWith('keydown', expect.any(Function));

      addEventListenerSpy.mockRestore();
      removeEventListenerSpy.mockRestore();
    });

    it('closes on ESC key press', () => {
      render(
        <ExecutionDetailModal
          isOpen={true}
          onClose={mockOnClose}
          execution={mockExecution}
          moonPhase={mockMoonPhase}
        />
      );

      fireEvent.keyDown(window, { key: 'Escape' });

      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });

    it('does not attach event listener when modal is closed', () => {
      const addEventListenerSpy = vi.spyOn(window, 'addEventListener');
      const removeEventListenerSpy = vi.spyOn(window, 'removeEventListener');

      render(
        <ExecutionDetailModal
          isOpen={false}
          onClose={mockOnClose}
          execution={mockExecution}
          moonPhase={mockMoonPhase}
        />
      );

      // Verify addEventListener was not called for keydown when modal is closed
      expect(addEventListenerSpy).not.toHaveBeenCalledWith('keydown', expect.any(Function));

      fireEvent.keyDown(window, { key: 'Escape' });
      expect(mockOnClose).not.toHaveBeenCalled();

      addEventListenerSpy.mockRestore();
      removeEventListenerSpy.mockRestore();
    });

    it('closes on backdrop click', () => {
      render(
        <ExecutionDetailModal
          isOpen={true}
          onClose={mockOnClose}
          execution={mockExecution}
          moonPhase={mockMoonPhase}
        />
      );

      const backdrop = screen.getByRole('dialog').parentElement;
      fireEvent.click(backdrop);

      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });

    it('does not close on modal content click', () => {
      render(
        <ExecutionDetailModal
          isOpen={true}
          onClose={mockOnClose}
          execution={mockExecution}
          moonPhase={mockMoonPhase}
        />
      );

      const modalContent = screen.getByRole('dialog');
      fireEvent.click(modalContent);

      expect(mockOnClose).not.toHaveBeenCalled();
    });

    it('cleans up event listeners on unmount', () => {
      const { unmount } = render(
        <ExecutionDetailModal
          isOpen={true}
          onClose={mockOnClose}
          execution={mockExecution}
          moonPhase={mockMoonPhase}
        />
      );

      unmount();

      // After unmount, ESC should not trigger onClose
      fireEvent.keyDown(window, { key: 'Escape' });
      expect(mockOnClose).not.toHaveBeenCalled();
    });
  });

  describe('Edge Cases', () => {
    it('handles execution with minimal data', () => {
      const minimalExecution = {
        pattern_id: 'pattern-1',
        pattern_name: 'Minimal Pattern',
        start_time: '2025-01-15T20:00:00',
        end_time: '2025-01-15T22:00:00',
      };

      render(
        <ExecutionDetailModal
          isOpen={true}
          onClose={mockOnClose}
          execution={minimalExecution}
          moonPhase={null}
        />
      );

      expect(screen.getByText('Minimal Pattern')).toBeInTheDocument();
      expect(screen.queryByText('Actions')).not.toBeInTheDocument();
    });

    it('renders multiple actions correctly', () => {
      const executionManyActions = {
        ...mockExecution,
        actions: Array.from({ length: 10 }, (_, i) => ({
          time: `2025-01-15T20:${i.toString().padStart(2, '0')}:00`,
          action_name: `Action ${i + 1}`,
          action_type: i % 2 === 0 ? 'gpio' : 'camera',
          offset_minutes: i * 5,
        })),
      };

      render(
        <ExecutionDetailModal
          isOpen={true}
          onClose={mockOnClose}
          execution={executionManyActions}
          moonPhase={null}
        />
      );

      expect(screen.getByText('Action 1')).toBeInTheDocument();
      expect(screen.getByText('Action 10')).toBeInTheDocument();
    });
  });

  describe('Focus Trap', () => {
    it('focuses the close button when modal opens', () => {
      render(
        <ExecutionDetailModal
          isOpen={true}
          onClose={mockOnClose}
          execution={mockExecution}
          moonPhase={null}
        />
      );

      // The close button should receive focus when modal opens
      const closeButton = screen.getByLabelText('Close');
      expect(document.activeElement).toBe(closeButton);
    });

    it('traps focus within modal on Tab', () => {
      render(
        <ExecutionDetailModal
          isOpen={true}
          onClose={mockOnClose}
          execution={mockExecution}
          moonPhase={null}
        />
      );

      const closeButton = screen.getByLabelText('Close');

      // Focus should be on close button (the only focusable element)
      expect(document.activeElement).toBe(closeButton);

      // Tab should keep focus on close button (only one focusable element)
      fireEvent.keyDown(window, { key: 'Tab' });
      expect(document.activeElement).toBe(closeButton);
    });

    it('traps focus within modal on Shift+Tab', () => {
      render(
        <ExecutionDetailModal
          isOpen={true}
          onClose={mockOnClose}
          execution={mockExecution}
          moonPhase={null}
        />
      );

      const closeButton = screen.getByLabelText('Close');

      // Focus should be on close button
      expect(document.activeElement).toBe(closeButton);

      // Shift+Tab should keep focus on close button (only one focusable element)
      fireEvent.keyDown(window, { key: 'Tab', shiftKey: true });
      expect(document.activeElement).toBe(closeButton);
    });
  });
});
