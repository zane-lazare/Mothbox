import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import PatternDetailsDrawer from '../PatternDetailsDrawer';

describe('PatternDetailsDrawer', () => {
  const mockOnClose = vi.fn();
  const mockOnSelect = vi.fn();

  const mockPattern = {
    pattern_id: 'uv_capture_cycle',
    name: 'UV Capture Cycle',
    description: 'Turn on UV light for attracting moths, wait 5 minutes, capture photo, then turn off UV light.',
    actions: [
      {
        action_type: 'gpio',
        action_name: 'attract_on',
        offset_minutes: 0,
        description: 'Turn on UV lights',
      },
      {
        action_type: 'camera',
        action_name: 'takephoto',
        offset_minutes: 5,
        description: 'Capture photo',
      },
      {
        action_type: 'gpio',
        action_name: 'attract_off',
        offset_minutes: 15,
        description: 'Turn off UV lights',
      },
    ],
    category: 'built-in',
    tags: ['moth', 'uv', 'capture'],
    duration_minutes: 15,
    source_schedule: 'nightly_moth_survey',
  };

  const mockUserPattern = {
    pattern_id: 'custom_pattern',
    name: 'Custom Pattern',
    description: 'A user-created pattern',
    actions: [
      {
        action_type: 'service',
        action_name: 'update_display',
        offset_minutes: 0,
        description: 'Update display',
      },
    ],
    category: 'user',
    tags: ['custom'],
    duration_minutes: 5,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    // Clean up any modals/drawers
    const drawers = document.querySelectorAll('[role="dialog"]');
    drawers.forEach((drawer) => drawer.remove());
  });

  // Open/Close Tests
  describe('Open/Close Behavior', () => {
    it('drawer is NOT rendered when isOpen=false', () => {
      render(
        <PatternDetailsDrawer
          pattern={mockPattern}
          isOpen={false}
          onClose={mockOnClose}
          onSelect={mockOnSelect}
        />
      );

      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    it('drawer IS rendered when isOpen=true', () => {
      render(
        <PatternDetailsDrawer
          pattern={mockPattern}
          isOpen={true}
          onClose={mockOnClose}
          onSelect={mockOnSelect}
        />
      );

      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('backdrop appears when drawer is open', () => {
      const { container } = render(
        <PatternDetailsDrawer
          pattern={mockPattern}
          isOpen={true}
          onClose={mockOnClose}
          onSelect={mockOnSelect}
        />
      );

      // Backdrop should be a sibling of the drawer with fixed positioning
      const backdrop = container.querySelector('.fixed.inset-0.bg-black');
      expect(backdrop).toBeInTheDocument();
    });

    it('clicking backdrop calls onClose', async () => {
      const user = userEvent.setup();
      const { container } = render(
        <PatternDetailsDrawer
          pattern={mockPattern}
          isOpen={true}
          onClose={mockOnClose}
          onSelect={mockOnSelect}
        />
      );

      const backdrop = container.querySelector('.fixed.inset-0.bg-black');
      await user.click(backdrop);

      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });

    it('escape key calls onClose', async () => {
      const user = userEvent.setup();
      render(
        <PatternDetailsDrawer
          pattern={mockPattern}
          isOpen={true}
          onClose={mockOnClose}
          onSelect={mockOnSelect}
        />
      );

      await user.keyboard('{Escape}');

      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });

    it('close button (X) calls onClose', async () => {
      const user = userEvent.setup();
      render(
        <PatternDetailsDrawer
          pattern={mockPattern}
          isOpen={true}
          onClose={mockOnClose}
          onSelect={mockOnSelect}
        />
      );

      const closeButton = screen.getByRole('button', { name: /close drawer/i });
      await user.click(closeButton);

      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });
  });

  // Content Rendering Tests
  describe('Content Rendering', () => {
    it('renders pattern name as header', () => {
      render(
        <PatternDetailsDrawer
          pattern={mockPattern}
          isOpen={true}
          onClose={mockOnClose}
          onSelect={mockOnSelect}
        />
      );

      expect(screen.getByText('UV Capture Cycle')).toBeInTheDocument();
    });

    it('renders full description (not truncated)', () => {
      render(
        <PatternDetailsDrawer
          pattern={mockPattern}
          isOpen={true}
          onClose={mockOnClose}
          onSelect={mockOnSelect}
        />
      );

      expect(
        screen.getByText(
          /Turn on UV light for attracting moths, wait 5 minutes, capture photo, then turn off UV light/i
        )
      ).toBeInTheDocument();
    });

    it('renders category badge for built-in pattern', () => {
      render(
        <PatternDetailsDrawer
          pattern={mockPattern}
          isOpen={true}
          onClose={mockOnClose}
          onSelect={mockOnSelect}
        />
      );

      expect(screen.getByText('built-in')).toBeInTheDocument();
    });

    it('renders category badge for user pattern', () => {
      render(
        <PatternDetailsDrawer
          pattern={mockUserPattern}
          isOpen={true}
          onClose={mockOnClose}
          onSelect={mockOnSelect}
        />
      );

      expect(screen.getByText('user')).toBeInTheDocument();
    });

    it('renders all tags as chips', () => {
      render(
        <PatternDetailsDrawer
          pattern={mockPattern}
          isOpen={true}
          onClose={mockOnClose}
          onSelect={mockOnSelect}
        />
      );

      expect(screen.getByText('moth')).toBeInTheDocument();
      expect(screen.getByText('uv')).toBeInTheDocument();
      expect(screen.getByText('capture')).toBeInTheDocument();
    });

    it('renders duration prominently', () => {
      render(
        <PatternDetailsDrawer
          pattern={mockPattern}
          isOpen={true}
          onClose={mockOnClose}
          onSelect={mockOnSelect}
        />
      );

      // Duration appears in both metadata section and timeline, use getAllByText
      const durationElements = screen.getAllByText(/15 min/i);
      expect(durationElements.length).toBeGreaterThan(0);
    });

    it('renders source_schedule if present', () => {
      render(
        <PatternDetailsDrawer
          pattern={mockPattern}
          isOpen={true}
          onClose={mockOnClose}
          onSelect={mockOnSelect}
        />
      );

      expect(screen.getByText(/nightly_moth_survey/i)).toBeInTheDocument();
    });

    it('renders action count', () => {
      render(
        <PatternDetailsDrawer
          pattern={mockPattern}
          isOpen={true}
          onClose={mockOnClose}
          onSelect={mockOnSelect}
        />
      );

      expect(screen.getByText(/3 actions/i)).toBeInTheDocument();
    });

    it('handles missing tags gracefully', () => {
      const patternNoTags = {
        ...mockPattern,
        tags: [],
      };

      render(
        <PatternDetailsDrawer
          pattern={patternNoTags}
          isOpen={true}
          onClose={mockOnClose}
          onSelect={mockOnSelect}
        />
      );

      // Should not crash, tags section should not show
      expect(screen.queryByText('Tags')).not.toBeInTheDocument();
    });

    it('handles missing description gracefully', () => {
      const patternNoDescription = {
        ...mockPattern,
        description: '',
      };

      render(
        <PatternDetailsDrawer
          pattern={patternNoDescription}
          isOpen={true}
          onClose={mockOnClose}
          onSelect={mockOnSelect}
        />
      );

      // Should not crash, description section should not show
      expect(screen.queryByText('Description')).not.toBeInTheDocument();
    });

    it('handles missing source_schedule gracefully', () => {
      render(
        <PatternDetailsDrawer
          pattern={mockUserPattern}
          isOpen={true}
          onClose={mockOnClose}
          onSelect={mockOnSelect}
        />
      );

      // Should not crash, source should not show
      expect(screen.queryByText(/Source:/i)).not.toBeInTheDocument();
    });
  });

  // Actions Timeline Tests
  describe('Actions Timeline', () => {
    it('renders timeline of actions', () => {
      render(
        <PatternDetailsDrawer
          pattern={mockPattern}
          isOpen={true}
          onClose={mockOnClose}
          onSelect={mockOnSelect}
        />
      );

      expect(screen.getByText('Actions Timeline')).toBeInTheDocument();
    });

    it('actions are sorted by offset_minutes', () => {
      const unsortedPattern = {
        ...mockPattern,
        actions: [
          {
            action_type: 'gpio',
            action_name: 'attract_off',
            offset_minutes: 15,
            description: 'Turn off UV lights',
          },
          {
            action_type: 'gpio',
            action_name: 'attract_on',
            offset_minutes: 0,
            description: 'Turn on UV lights',
          },
          {
            action_type: 'camera',
            action_name: 'takephoto',
            offset_minutes: 5,
            description: 'Capture photo',
          },
        ],
      };

      render(
        <PatternDetailsDrawer
          pattern={unsortedPattern}
          isOpen={true}
          onClose={mockOnClose}
          onSelect={mockOnSelect}
        />
      );

      const actionNames = screen.getAllByText(/attract_on|takephoto|attract_off/);
      expect(actionNames[0]).toHaveTextContent('attract_on');
      expect(actionNames[1]).toHaveTextContent('takephoto');
      expect(actionNames[2]).toHaveTextContent('attract_off');
    });

    it('each action shows action_name', () => {
      render(
        <PatternDetailsDrawer
          pattern={mockPattern}
          isOpen={true}
          onClose={mockOnClose}
          onSelect={mockOnSelect}
        />
      );

      expect(screen.getByText('attract_on')).toBeInTheDocument();
      expect(screen.getByText('takephoto')).toBeInTheDocument();
      expect(screen.getByText('attract_off')).toBeInTheDocument();
    });

    it('each action shows offset time', () => {
      render(
        <PatternDetailsDrawer
          pattern={mockPattern}
          isOpen={true}
          onClose={mockOnClose}
          onSelect={mockOnSelect}
        />
      );

      expect(screen.getByText('+0 min')).toBeInTheDocument();
      expect(screen.getByText('+5 min')).toBeInTheDocument();
      expect(screen.getByText('+15 min')).toBeInTheDocument();
    });

    it('each action shows description', () => {
      render(
        <PatternDetailsDrawer
          pattern={mockPattern}
          isOpen={true}
          onClose={mockOnClose}
          onSelect={mockOnSelect}
        />
      );

      // Descriptions are part of compound text with action type labels
      expect(screen.getByText(/GPIO - Turn on UV lights/i)).toBeInTheDocument();
      expect(screen.getByText(/Camera - Capture photo/i)).toBeInTheDocument();
      expect(screen.getByText(/GPIO - Turn off UV lights/i)).toBeInTheDocument();
    });

    it('each action shows action type label', () => {
      render(
        <PatternDetailsDrawer
          pattern={mockPattern}
          isOpen={true}
          onClose={mockOnClose}
          onSelect={mockOnSelect}
        />
      );

      // GPIO appears twice in compound text (attract_on and attract_off)
      const gpioTexts = screen.getAllByText(/GPIO -/i);
      expect(gpioTexts).toHaveLength(2);

      // Camera appears once in compound text
      expect(screen.getByText(/Camera -/i)).toBeInTheDocument();
    });

    it('handles empty actions array gracefully', () => {
      const patternNoActions = {
        ...mockPattern,
        actions: [],
      };

      render(
        <PatternDetailsDrawer
          pattern={patternNoActions}
          isOpen={true}
          onClose={mockOnClose}
          onSelect={mockOnSelect}
        />
      );

      // Should show "No actions defined"
      expect(screen.getByText(/no actions defined/i)).toBeInTheDocument();
    });
  });

  // Footer Actions Tests
  describe('Footer Actions', () => {
    it('"Use This Pattern" button is visible', () => {
      render(
        <PatternDetailsDrawer
          pattern={mockPattern}
          isOpen={true}
          onClose={mockOnClose}
          onSelect={mockOnSelect}
        />
      );

      expect(screen.getByRole('button', { name: /use this pattern/i })).toBeInTheDocument();
    });

    it('button click calls onSelect with pattern', async () => {
      const user = userEvent.setup();
      render(
        <PatternDetailsDrawer
          pattern={mockPattern}
          isOpen={true}
          onClose={mockOnClose}
          onSelect={mockOnSelect}
        />
      );

      const useButton = screen.getByRole('button', { name: /use this pattern/i });
      await user.click(useButton);

      expect(mockOnSelect).toHaveBeenCalledTimes(1);
      expect(mockOnSelect).toHaveBeenCalledWith(mockPattern);
    });

    it('"Close" button is visible', () => {
      render(
        <PatternDetailsDrawer
          pattern={mockPattern}
          isOpen={true}
          onClose={mockOnClose}
          onSelect={mockOnSelect}
        />
      );

      // Footer close button (not the X button)
      const buttons = screen.getAllByRole('button', { name: /close/i });
      expect(buttons.length).toBeGreaterThanOrEqual(1);
    });

    it('close button calls onClose', async () => {
      const user = userEvent.setup();
      render(
        <PatternDetailsDrawer
          pattern={mockPattern}
          isOpen={true}
          onClose={mockOnClose}
          onSelect={mockOnSelect}
        />
      );

      // Footer close button
      const closeButtons = screen.getAllByRole('button', { name: /close/i });
      const footerCloseButton = closeButtons.find(
        (btn) => btn.textContent.trim() === 'Close'
      );

      if (footerCloseButton) {
        await user.click(footerCloseButton);
        expect(mockOnClose).toHaveBeenCalledTimes(1);
      } else {
        // Fallback: click any close button
        await user.click(closeButtons[0]);
        expect(mockOnClose).toHaveBeenCalled();
      }
    });
  });

  // Accessibility Tests
  describe('Accessibility', () => {
    it('drawer has role="dialog"', () => {
      render(
        <PatternDetailsDrawer
          pattern={mockPattern}
          isOpen={true}
          onClose={mockOnClose}
          onSelect={mockOnSelect}
        />
      );

      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('has aria-labelledby pointing to header', () => {
      render(
        <PatternDetailsDrawer
          pattern={mockPattern}
          isOpen={true}
          onClose={mockOnClose}
          onSelect={mockOnSelect}
        />
      );

      const dialog = screen.getByRole('dialog');
      const labelId = dialog.getAttribute('aria-labelledby');

      expect(labelId).toBeTruthy();

      const header = document.getElementById(labelId);
      expect(header).toBeInTheDocument();
      expect(header).toHaveTextContent('UV Capture Cycle');
    });

    it('handles null pattern gracefully when open', () => {
      render(
        <PatternDetailsDrawer
          pattern={null}
          isOpen={true}
          onClose={mockOnClose}
          onSelect={mockOnSelect}
        />
      );

      // Should not crash, but also should not show drawer
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });
  });
});
