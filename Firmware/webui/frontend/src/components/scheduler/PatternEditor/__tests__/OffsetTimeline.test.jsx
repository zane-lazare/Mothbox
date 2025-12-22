import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import OffsetTimeline from '../OffsetTimeline'

describe('OffsetTimeline', () => {
  describe('Empty State', () => {
    it('should render empty state message when actions array is empty', () => {
      render(<OffsetTimeline actions={[]} />)
      expect(screen.getByText(/no actions/i)).toBeInTheDocument()
    })

    it('should render empty state message when actions is undefined', () => {
      render(<OffsetTimeline />)
      expect(screen.getByText(/no actions/i)).toBeInTheDocument()
    })
  })

  describe('Timeline Rendering', () => {
    const sampleActions = [
      { action_type: 'gpio', action_name: 'attract_on', offset_minutes: 0 },
      { action_type: 'camera', action_name: 'takephoto', offset_minutes: 5 },
      { action_type: 'gpio', action_name: 'attract_off', offset_minutes: 15 }
    ]

    it('should render timeline with markers for each action', () => {
      render(<OffsetTimeline actions={sampleActions} />)

      // Should have 3 markers
      const markers = screen.getAllByRole('button')
      expect(markers).toHaveLength(3)
    })

    it('should display duration labels', () => {
      render(<OffsetTimeline actions={sampleActions} />)

      expect(screen.getByText('0min')).toBeInTheDocument()
      expect(screen.getByText('15min')).toBeInTheDocument()
    })

    it('should render timeline bar', () => {
      const { container } = render(<OffsetTimeline actions={sampleActions} />)

      // Check for timeline bar element
      const timeline = container.querySelector('[data-testid="timeline-bar"]')
      expect(timeline).toBeInTheDocument()
    })
  })

  describe('Marker Positioning', () => {
    it('should position markers at correct percentage of duration', () => {
      const actions = [
        { action_type: 'gpio', action_name: 'action1', offset_minutes: 0 },
        { action_type: 'camera', action_name: 'action2', offset_minutes: 5 },
        { action_type: 'gpio', action_name: 'action3', offset_minutes: 10 }
      ]

      const { container } = render(<OffsetTimeline actions={actions} />)

      const markers = container.querySelectorAll('[data-testid^="timeline-marker-"]')

      // Markers are buttons, but their parents (divs) have the left positioning
      // First marker at 0% (left: 0%)
      expect(markers[0].parentElement).toHaveStyle({ left: '0%' })

      // Second marker at 50% (5 out of 10)
      expect(markers[1].parentElement).toHaveStyle({ left: '50%' })

      // Third marker at 100% (10 out of 10)
      expect(markers[2].parentElement).toHaveStyle({ left: '100%' })
    })

    it('should handle single action at offset 0', () => {
      const actions = [
        { action_type: 'gpio', action_name: 'action1', offset_minutes: 0 }
      ]

      const { container } = render(<OffsetTimeline actions={actions} />)

      const marker = container.querySelector('[data-testid="timeline-marker-0"]')
      expect(marker.parentElement).toHaveStyle({ left: '0%' })
    })
  })

  describe('Duration Calculation', () => {
    it('should calculate duration from max offset when not provided', () => {
      const actions = [
        { action_type: 'gpio', action_name: 'action1', offset_minutes: 0 },
        { action_type: 'camera', action_name: 'action2', offset_minutes: 20 }
      ]

      render(<OffsetTimeline actions={actions} />)

      expect(screen.getByText('20min')).toBeInTheDocument()
    })

    it('should respect custom duration prop', () => {
      const actions = [
        { action_type: 'gpio', action_name: 'action1', offset_minutes: 0 },
        { action_type: 'camera', action_name: 'action2', offset_minutes: 10 }
      ]

      render(<OffsetTimeline actions={actions} duration={30} />)

      expect(screen.getByText('30min')).toBeInTheDocument()
    })

    it('should default to 1 minute duration when all offsets are 0', () => {
      const actions = [
        { action_type: 'gpio', action_name: 'action1', offset_minutes: 0 }
      ]

      render(<OffsetTimeline actions={actions} />)

      expect(screen.getByText('1min')).toBeInTheDocument()
    })
  })

  describe('Action Type Icons', () => {
    it('should render BoltIcon for gpio actions', () => {
      const actions = [
        { action_type: 'gpio', action_name: 'attract_on', offset_minutes: 0 }
      ]

      render(<OffsetTimeline actions={actions} />)

      const marker = screen.getByRole('button')
      expect(marker).toHaveAttribute('aria-label', expect.stringContaining('gpio'))
    })

    it('should render CameraIcon for camera actions', () => {
      const actions = [
        { action_type: 'camera', action_name: 'takephoto', offset_minutes: 0 }
      ]

      render(<OffsetTimeline actions={actions} />)

      const marker = screen.getByRole('button')
      expect(marker).toHaveAttribute('aria-label', expect.stringContaining('camera'))
    })

    it('should render MapPinIcon for gps_sync actions', () => {
      const actions = [
        { action_type: 'gps_sync', action_name: 'sync_gps', offset_minutes: 0 }
      ]

      render(<OffsetTimeline actions={actions} />)

      const marker = screen.getByRole('button')
      expect(marker).toHaveAttribute('aria-label', expect.stringContaining('gps_sync'))
    })

    it('should render CogIcon for service actions', () => {
      const actions = [
        { action_type: 'service', action_name: 'restart', offset_minutes: 0 }
      ]

      render(<OffsetTimeline actions={actions} />)

      const marker = screen.getByRole('button')
      expect(marker).toHaveAttribute('aria-label', expect.stringContaining('service'))
    })

    it('should render CogIcon for unknown action types', () => {
      const actions = [
        { action_type: 'unknown', action_name: 'test', offset_minutes: 0 }
      ]

      const { container } = render(<OffsetTimeline actions={actions} />)

      const marker = container.querySelector('[data-testid="timeline-marker-0"]')
      expect(marker).toBeInTheDocument()
    })
  })

  describe('Tooltips', () => {
    it('should show action details on hover', async () => {
      const user = userEvent.setup()
      const actions = [
        {
          action_type: 'gpio',
          action_name: 'attract_on',
          offset_minutes: 5,
          description: 'Turn on attract lights'
        }
      ]

      render(<OffsetTimeline actions={actions} />)

      const marker = screen.getByRole('button')
      await user.hover(marker)

      expect(await screen.findByText('attract_on')).toBeInTheDocument()
      expect(await screen.findByText(/gpio at 5 minutes/i)).toBeInTheDocument()
      expect(await screen.findByText('Turn on attract lights')).toBeInTheDocument()
    })

    it('should show tooltip without description field', async () => {
      const user = userEvent.setup()
      const actions = [
        {
          action_type: 'camera',
          action_name: 'takephoto',
          offset_minutes: 10
        }
      ]

      render(<OffsetTimeline actions={actions} />)

      const marker = screen.getByRole('button')
      await user.hover(marker)

      expect(await screen.findByText('takephoto')).toBeInTheDocument()
      expect(await screen.findByText(/camera at 10 minutes/i)).toBeInTheDocument()
    })

    it('should hide tooltip on mouse leave', async () => {
      const user = userEvent.setup()
      const actions = [
        { action_type: 'gpio', action_name: 'attract_on', offset_minutes: 5 }
      ]

      render(<OffsetTimeline actions={actions} />)

      const marker = screen.getByRole('button')
      await user.hover(marker)

      const tooltip = await screen.findByText('attract_on')
      expect(tooltip).toBeInTheDocument()

      await user.unhover(marker)

      // Tooltip should be removed or hidden (exact text match to avoid false positives)
      expect(screen.queryByText(/gpio at 5 minutes/i)).not.toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('should have aria-labels on markers', () => {
      const actions = [
        { action_type: 'gpio', action_name: 'attract_on', offset_minutes: 5 }
      ]

      render(<OffsetTimeline actions={actions} />)

      const marker = screen.getByRole('button')
      expect(marker).toHaveAttribute('aria-label')
    })

    it('should have descriptive aria-label content', () => {
      const actions = [
        { action_type: 'camera', action_name: 'takephoto', offset_minutes: 10 }
      ]

      render(<OffsetTimeline actions={actions} />)

      const marker = screen.getByRole('button')
      const ariaLabel = marker.getAttribute('aria-label')

      expect(ariaLabel).toContain('camera')
      expect(ariaLabel).toContain('takephoto')
      expect(ariaLabel).toContain('10')
    })

    it('should have proper role for timeline container', () => {
      const actions = [
        { action_type: 'gpio', action_name: 'attract_on', offset_minutes: 0 }
      ]

      const { container } = render(<OffsetTimeline actions={actions} />)

      const timeline = container.querySelector('[role="region"]')
      expect(timeline).toBeInTheDocument()
      expect(timeline).toHaveAttribute('aria-label', expect.stringContaining('timeline'))
    })
  })

  describe('Dark Mode', () => {
    it('should apply dark mode classes to timeline bar', () => {
      const actions = [
        { action_type: 'gpio', action_name: 'attract_on', offset_minutes: 0 }
      ]

      const { container } = render(<OffsetTimeline actions={actions} />)

      const timeline = container.querySelector('[data-testid="timeline-bar"]')
      expect(timeline).toHaveClass('dark:bg-gray-700')
    })

    it('should apply dark mode classes to markers', () => {
      const actions = [
        { action_type: 'gpio', action_name: 'attract_on', offset_minutes: 0 }
      ]

      render(<OffsetTimeline actions={actions} />)

      const marker = screen.getByRole('button')
      expect(marker).toHaveClass('dark:bg-blue-900')
    })

    it('should apply dark mode classes to duration labels', () => {
      const actions = [
        { action_type: 'gpio', action_name: 'attract_on', offset_minutes: 0 }
      ]

      const { container } = render(<OffsetTimeline actions={actions} />)

      const labels = container.querySelectorAll('.text-gray-600')
      labels.forEach(label => {
        expect(label).toHaveClass('dark:text-gray-400')
      })
    })
  })

  describe('Edge Cases', () => {
    it('should handle actions with same offset', () => {
      const actions = [
        { action_type: 'gpio', action_name: 'action1', offset_minutes: 5 },
        { action_type: 'camera', action_name: 'action2', offset_minutes: 5 },
        { action_type: 'gps_sync', action_name: 'action3', offset_minutes: 5 }
      ]

      const { container } = render(<OffsetTimeline actions={actions} />)

      const markers = container.querySelectorAll('[data-testid^="timeline-marker-"]')
      expect(markers).toHaveLength(3)

      // All should be at the same position (parent divs hold the left positioning)
      markers.forEach(marker => {
        expect(marker.parentElement).toHaveStyle({ left: '100%' })
      })
    })

    it('should handle fractional offset values', () => {
      const actions = [
        { action_type: 'gpio', action_name: 'action1', offset_minutes: 0 },
        { action_type: 'camera', action_name: 'action2', offset_minutes: 2.5 },
        { action_type: 'gpio', action_name: 'action3', offset_minutes: 5 }
      ]

      const { container } = render(<OffsetTimeline actions={actions} />)

      const markers = container.querySelectorAll('[data-testid^="timeline-marker-"]')
      expect(markers[1].parentElement).toHaveStyle({ left: '50%' })
    })

    it('should handle large offset values', () => {
      const actions = [
        { action_type: 'gpio', action_name: 'action1', offset_minutes: 0 },
        { action_type: 'camera', action_name: 'action2', offset_minutes: 1440 } // 24 hours
      ]

      render(<OffsetTimeline actions={actions} />)

      expect(screen.getByText('1440min')).toBeInTheDocument()
    })

    it('should sort actions by offset for display', () => {
      const actions = [
        { action_type: 'gpio', action_name: 'action3', offset_minutes: 15 },
        { action_type: 'camera', action_name: 'action1', offset_minutes: 0 },
        { action_type: 'gps_sync', action_name: 'action2', offset_minutes: 5 }
      ]

      const { container } = render(<OffsetTimeline actions={actions} />)

      const markers = container.querySelectorAll('[data-testid^="timeline-marker-"]')

      // Markers should be in order by offset (parent divs hold the left positioning)
      expect(markers[0].parentElement).toHaveStyle({ left: '0%' })
      expect(markers[1].parentElement).toHaveStyle({ left: '33.33333333333333%' })
      expect(markers[2].parentElement).toHaveStyle({ left: '100%' })
    })
  })

  describe('Responsive Behavior', () => {
    it('should render timeline with relative positioning', () => {
      const actions = [
        { action_type: 'gpio', action_name: 'attract_on', offset_minutes: 0 }
      ]

      const { container } = render(<OffsetTimeline actions={actions} />)

      const timeline = container.querySelector('[data-testid="timeline-bar"]')
      expect(timeline?.parentElement).toHaveClass('relative')
    })

    it('should position markers absolutely within timeline', () => {
      const actions = [
        { action_type: 'gpio', action_name: 'attract_on', offset_minutes: 0 }
      ]

      const { container } = render(<OffsetTimeline actions={actions} />)

      const marker = container.querySelector('[data-testid="timeline-marker-0"]')
      // The parent div has the absolute positioning, not the button itself
      expect(marker.parentElement).toHaveClass('absolute')
    })
  })
})
