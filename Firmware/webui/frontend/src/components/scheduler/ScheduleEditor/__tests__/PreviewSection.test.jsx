import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import PreviewSection from '../PreviewSection';

describe('PreviewSection', () => {
  const mockPattern = {
    pattern_id: 'pattern-123',
    name: 'Night Photography Session',
    description: 'Standard moth photography routine',
    actions: [
      { action_id: '1', type: 'attract_on', parameters: {} },
      { action_id: '2', type: 'wait', parameters: { duration_seconds: 300 } },
      { action_id: '3', type: 'camera_capture', parameters: {} },
      { action_id: '4', type: 'attract_off', parameters: {} },
    ],
    category: 'photography',
    tags: ['moth', 'night'],
  };

  const mockIntervalTrigger = {
    type: 'interval',
    interval_minutes: 60,
    time_window: {
      start_time: '21:00',
      end_time: '05:00',
      start_offset_minutes: 0,
      end_offset_minutes: 0,
    },
    days_of_week: null,
  };

  const mockSolarTrigger = {
    type: 'solar',
    solar_event: 'sunset',
    offset_minutes: 30,
    days_of_week: [0, 1, 2, 3, 4], // Mon-Fri
  };

  const mockFixedTimeTrigger = {
    type: 'fixed_time',
    time: '21:00',
    days_of_week: null,
  };

  const mockDateRange = {
    start_date: '2024-06-01',
    end_date: '2024-08-31',
  };

  describe('Rendering', () => {
    it('renders section header', () => {
      render(
        <PreviewSection
          trigger={mockIntervalTrigger}
          dateRange={mockDateRange}
          pattern={mockPattern}
        />
      );

      expect(screen.getByText('Schedule Preview')).toBeInTheDocument();
    });

    it('shows "No trigger configured" when no trigger', () => {
      render(
        <PreviewSection
          trigger={null}
          dateRange={mockDateRange}
          pattern={mockPattern}
        />
      );

      expect(screen.getByText('No trigger configured')).toBeInTheDocument();
    });

    it('shows "No pattern selected" when no pattern', () => {
      render(
        <PreviewSection
          trigger={mockIntervalTrigger}
          dateRange={mockDateRange}
          pattern={null}
        />
      );

      expect(screen.getByText('No pattern selected')).toBeInTheDocument();
    });

    it('renders when both trigger and pattern are null', () => {
      render(
        <PreviewSection
          trigger={null}
          dateRange={mockDateRange}
          pattern={null}
        />
      );

      expect(screen.getByText('Schedule Preview')).toBeInTheDocument();
      expect(screen.getByText('No trigger configured')).toBeInTheDocument();
    });

    it('renders when disabled', () => {
      render(
        <PreviewSection
          trigger={mockIntervalTrigger}
          dateRange={mockDateRange}
          pattern={mockPattern}
          disabled={true}
        />
      );

      expect(screen.getByText('Schedule Preview')).toBeInTheDocument();
    });
  });

  describe('Pattern Information Display', () => {
    it('displays pattern name and action count', () => {
      render(
        <PreviewSection
          trigger={mockIntervalTrigger}
          dateRange={mockDateRange}
          pattern={mockPattern}
        />
      );

      expect(screen.getByText('Night Photography Session')).toBeInTheDocument();
      expect(screen.getByText('4 actions')).toBeInTheDocument();
    });

    it('displays singular "action" for single action pattern', () => {
      const singleActionPattern = {
        ...mockPattern,
        actions: [{ action_id: '1', type: 'attract_on', parameters: {} }],
      };

      render(
        <PreviewSection
          trigger={mockIntervalTrigger}
          dateRange={mockDateRange}
          pattern={singleActionPattern}
        />
      );

      expect(screen.getByText('1 action')).toBeInTheDocument();
    });

    it('calculates and displays total pattern duration', () => {
      // Mock pattern with wait actions totaling 600 seconds (10 minutes)
      const patternWithDuration = {
        ...mockPattern,
        actions: [
          { action_id: '1', type: 'wait', parameters: { duration_seconds: 300 } },
          { action_id: '2', type: 'wait', parameters: { duration_seconds: 300 } },
        ],
      };

      render(
        <PreviewSection
          trigger={mockIntervalTrigger}
          dateRange={mockDateRange}
          pattern={patternWithDuration}
        />
      );

      expect(screen.getByText(/Duration:/)).toBeInTheDocument();
      expect(screen.getByText(/10 minutes/)).toBeInTheDocument();
    });

    it('displays hours and minutes for longer durations', () => {
      const patternWithLongDuration = {
        ...mockPattern,
        actions: [
          { action_id: '1', type: 'wait', parameters: { duration_seconds: 3900 } }, // 65 minutes = 1h 5m
        ],
      };

      render(
        <PreviewSection
          trigger={mockIntervalTrigger}
          dateRange={mockDateRange}
          pattern={patternWithLongDuration}
        />
      );

      expect(screen.getByText(/1 hour 5 minutes/)).toBeInTheDocument();
    });

    it('handles pattern with no wait actions (instant duration)', () => {
      const instantPattern = {
        ...mockPattern,
        actions: [
          { action_id: '1', type: 'attract_on', parameters: {} },
          { action_id: '2', type: 'camera_capture', parameters: {} },
        ],
      };

      render(
        <PreviewSection
          trigger={mockIntervalTrigger}
          dateRange={mockDateRange}
          pattern={instantPattern}
        />
      );

      expect(screen.getByText(/Duration:/)).toBeInTheDocument();
      expect(screen.getByText(/instant/i)).toBeInTheDocument();
    });
  });

  describe('Execution Preview Times', () => {
    it('shows execution preview times section', () => {
      render(
        <PreviewSection
          trigger={mockIntervalTrigger}
          dateRange={mockDateRange}
          pattern={mockPattern}
        />
      );

      expect(screen.getByText('Next Executions:')).toBeInTheDocument();
    });

    it('displays next 5 execution times by default', () => {
      render(
        <PreviewSection
          trigger={mockIntervalTrigger}
          dateRange={mockDateRange}
          pattern={mockPattern}
        />
      );

      // Mock data should show 5 execution times
      const executionItems = screen.getAllByRole('listitem');
      expect(executionItems).toHaveLength(5);
    });

    it('formats execution times with date and time', () => {
      render(
        <PreviewSection
          trigger={mockIntervalTrigger}
          dateRange={mockDateRange}
          pattern={mockPattern}
        />
      );

      // Should show formatted date/time strings
      // Example: "Jun 1, 2024, 9:00 PM"
      const executionItems = screen.getAllByRole('listitem');
      expect(executionItems[0]).toHaveTextContent(/2024/);
      expect(executionItems[0]).toHaveTextContent(/PM|AM/);
    });
  });

  describe('Interval Trigger Preview', () => {
    it('handles interval trigger preview', () => {
      render(
        <PreviewSection
          trigger={mockIntervalTrigger}
          dateRange={mockDateRange}
          pattern={mockPattern}
        />
      );

      // Should show interval-specific information (60 minutes = 1 hour)
      expect(screen.getByText(/Every 1 hour/i)).toBeInTheDocument();
      expect(screen.getByText(/21:00/)).toBeInTheDocument();
      expect(screen.getByText(/05:00/)).toBeInTheDocument();
    });

    it('shows interval with hours formatting', () => {
      const hourlyTrigger = {
        ...mockIntervalTrigger,
        interval_minutes: 120,
      };

      render(
        <PreviewSection
          trigger={hourlyTrigger}
          dateRange={mockDateRange}
          pattern={mockPattern}
        />
      );

      expect(screen.getByText(/Every 2 hours/i)).toBeInTheDocument();
    });
  });

  describe('Solar Trigger Preview', () => {
    it('handles solar trigger preview', () => {
      render(
        <PreviewSection
          trigger={mockSolarTrigger}
          dateRange={mockDateRange}
          pattern={mockPattern}
        />
      );

      // Should show solar event information
      expect(screen.getByText(/sunset/i)).toBeInTheDocument();
    });

    it('shows solar event offset when present', () => {
      render(
        <PreviewSection
          trigger={mockSolarTrigger}
          dateRange={mockDateRange}
          pattern={mockPattern}
        />
      );

      expect(screen.getByText(/30 minutes after/i)).toBeInTheDocument();
    });

    it('handles negative offset (before event)', () => {
      const beforeSunsetTrigger = {
        ...mockSolarTrigger,
        offset_minutes: -30,
      };

      render(
        <PreviewSection
          trigger={beforeSunsetTrigger}
          dateRange={mockDateRange}
          pattern={mockPattern}
        />
      );

      expect(screen.getByText(/30 minutes before/i)).toBeInTheDocument();
    });
  });

  describe('Fixed Time Trigger Preview', () => {
    it('handles fixed time trigger preview', () => {
      render(
        <PreviewSection
          trigger={mockFixedTimeTrigger}
          dateRange={mockDateRange}
          pattern={mockPattern}
        />
      );

      expect(screen.getByText(/Daily at 21:00/i)).toBeInTheDocument();
    });

    it('shows days of week when specified', () => {
      const weekdayTrigger = {
        ...mockFixedTimeTrigger,
        days_of_week: [0, 1, 2, 3, 4], // Mon-Fri
      };

      render(
        <PreviewSection
          trigger={weekdayTrigger}
          dateRange={mockDateRange}
          pattern={mockPattern}
        />
      );

      expect(screen.getByText(/Mon, Tue, Wed, Thu, Fri/)).toBeInTheDocument();
    });
  });

  describe('Date Constraints Display', () => {
    it('shows date constraints info when both dates provided', () => {
      render(
        <PreviewSection
          trigger={mockIntervalTrigger}
          dateRange={mockDateRange}
          pattern={mockPattern}
        />
      );

      // Check for the Active Period section which contains both dates
      expect(screen.getByText('Active Period:')).toBeInTheDocument();
      // Dates are in separate text nodes, check the container includes both
      const activePeriodLabel = screen.getByText('Active Period:');
      const dateContainer = activePeriodLabel.parentElement;
      expect(dateContainer).toHaveTextContent('Jun 1, 2024');
      expect(dateContainer).toHaveTextContent('Aug 31, 2024');
    });

    it('shows "No end date" when end_date is null', () => {
      const openEndedRange = {
        start_date: '2024-06-01',
        end_date: null,
      };

      render(
        <PreviewSection
          trigger={mockIntervalTrigger}
          dateRange={openEndedRange}
          pattern={mockPattern}
        />
      );

      expect(screen.getByText(/No end date/i)).toBeInTheDocument();
    });

    it('shows "No start date" when start_date is null', () => {
      const noStartRange = {
        start_date: null,
        end_date: '2024-08-31',
      };

      render(
        <PreviewSection
          trigger={mockIntervalTrigger}
          dateRange={noStartRange}
          pattern={mockPattern}
        />
      );

      expect(screen.getByText(/No start date/i)).toBeInTheDocument();
    });

    it('handles null dateRange', () => {
      render(
        <PreviewSection
          trigger={mockIntervalTrigger}
          dateRange={null}
          pattern={mockPattern}
        />
      );

      // Should still render without crashing
      expect(screen.getByText('Schedule Preview')).toBeInTheDocument();
    });
  });

  describe('Dark Mode Styling', () => {
    it('applies dark mode classes to section header', () => {
      render(
        <PreviewSection
          trigger={mockIntervalTrigger}
          dateRange={mockDateRange}
          pattern={mockPattern}
        />
      );

      const header = screen.getByText('Schedule Preview');
      expect(header).toHaveClass('dark:text-white');
    });

    it('applies dark mode classes to pattern info card', () => {
      const { container } = render(
        <PreviewSection
          trigger={mockIntervalTrigger}
          dateRange={mockDateRange}
          pattern={mockPattern}
        />
      );

      const patternCard = container.querySelector('.dark\\:bg-gray-800');
      expect(patternCard).toBeInTheDocument();
    });

    it('applies dark mode classes to execution list', () => {
      render(
        <PreviewSection
          trigger={mockIntervalTrigger}
          dateRange={mockDateRange}
          pattern={mockPattern}
        />
      );

      const executionItems = screen.getAllByRole('listitem');
      executionItems.forEach((item) => {
        expect(item).toHaveClass('dark:text-gray-300');
      });
    });

    it('applies dark mode classes to date constraint text', () => {
      render(
        <PreviewSection
          trigger={mockIntervalTrigger}
          dateRange={mockDateRange}
          pattern={mockPattern}
        />
      );

      // Find the date constraint container by looking for Active Period
      const activePeriodLabel = screen.getByText('Active Period:');
      const dateContainer = activePeriodLabel.parentElement;
      expect(dateContainer).toHaveClass('dark:text-gray-400');
    });
  });

  describe('Accessibility', () => {
    it('includes aria-label for section', () => {
      const { container } = render(
        <PreviewSection
          trigger={mockIntervalTrigger}
          dateRange={mockDateRange}
          pattern={mockPattern}
        />
      );

      const section = container.querySelector('[aria-label="Schedule preview"]');
      expect(section).toBeInTheDocument();
    });

    it('includes aria-label for execution list', () => {
      render(
        <PreviewSection
          trigger={mockIntervalTrigger}
          dateRange={mockDateRange}
          pattern={mockPattern}
        />
      );

      const list = screen.getByRole('list', { name: /next execution times/i });
      expect(list).toBeInTheDocument();
    });

    it('uses semantic HTML list for executions', () => {
      render(
        <PreviewSection
          trigger={mockIntervalTrigger}
          dateRange={mockDateRange}
          pattern={mockPattern}
        />
      );

      const list = screen.getByRole('list');
      const items = screen.getAllByRole('listitem');

      expect(list).toBeInTheDocument();
      expect(items.length).toBeGreaterThan(0);
    });
  });

  describe('Edge Cases', () => {
    it('handles undefined trigger gracefully', () => {
      render(
        <PreviewSection
          trigger={undefined}
          dateRange={mockDateRange}
          pattern={mockPattern}
        />
      );

      expect(screen.getByText('No trigger configured')).toBeInTheDocument();
    });

    it('handles undefined pattern gracefully', () => {
      render(
        <PreviewSection
          trigger={mockIntervalTrigger}
          dateRange={mockDateRange}
          pattern={undefined}
        />
      );

      expect(screen.getByText('No pattern selected')).toBeInTheDocument();
    });

    it('handles pattern with empty actions array', () => {
      const emptyPattern = {
        ...mockPattern,
        actions: [],
      };

      render(
        <PreviewSection
          trigger={mockIntervalTrigger}
          dateRange={mockDateRange}
          pattern={emptyPattern}
        />
      );

      expect(screen.getByText('0 actions')).toBeInTheDocument();
    });

    it('handles sensor trigger type (not supported for preview)', () => {
      const sensorTrigger = {
        type: 'sensor',
        sensor_type: 'light_level',
        threshold: 100,
      };

      render(
        <PreviewSection
          trigger={sensorTrigger}
          dateRange={mockDateRange}
          pattern={mockPattern}
        />
      );

      // Should show message about preview not available
      expect(screen.getByText(/preview not available/i)).toBeInTheDocument();
    });

    it('handles moon_phase trigger type', () => {
      const moonTrigger = {
        type: 'moon_phase',
        phase: 'full_moon',
        offset_days: 0,
        time: '21:00',
      };

      render(
        <PreviewSection
          trigger={moonTrigger}
          dateRange={mockDateRange}
          pattern={mockPattern}
        />
      );

      expect(screen.getByText(/full moon/i)).toBeInTheDocument();
    });
  });
});
