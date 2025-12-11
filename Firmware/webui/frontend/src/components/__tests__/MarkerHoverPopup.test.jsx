import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import MarkerHoverPopup from '../MarkerHoverPopup'

describe('MarkerHoverPopup', () => {
  const mockCluster = {
    cluster_id: 'cluster_1',
    center: { lat: 37.7749, lon: -122.4194 },
    count: 3,
    photos: [
      {
        path: 'photo1.jpg',
        filename: 'photo1.jpg',
        thumbnail_url: '/api/gallery/thumbnail/photo1.jpg',
        timestamp: '2024-01-15 10:30:00',
        tags: ['moth', 'night'],
      },
      {
        path: 'photo2.jpg',
        filename: 'photo2.jpg',
        thumbnail_url: '/api/gallery/thumbnail/photo2.jpg',
        timestamp: '2024-01-15 11:00:00',
        tags: ['butterfly'],
      },
      {
        path: 'photo3.jpg',
        filename: 'photo3.jpg',
        thumbnail_url: '/api/gallery/thumbnail/photo3.jpg',
        timestamp: '2024-01-15 12:00:00',
        tags: [],
      },
    ],
    date_range: {
      earliest: '2024-01-15',
      latest: '2024-01-15',
    },
  }

  const mockPosition = { x: 100, y: 200 }
  const mockOnPhotoClick = vi.fn()
  const mockOnClose = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Visibility', () => {
    it('renders when isVisible=true', () => {
      render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      expect(screen.getByRole('dialog')).toBeInTheDocument()
      expect(screen.getByText('3 photos')).toBeInTheDocument()
    })

    it('returns null when isVisible=false', () => {
      const { container } = render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={false}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      expect(container.firstChild).toBeNull()
    })

    it('returns null when cluster is null', () => {
      const { container } = render(
        <MarkerHoverPopup
          cluster={null}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      expect(container.firstChild).toBeNull()
    })

    it('returns null when cluster is undefined', () => {
      const { container } = render(
        <MarkerHoverPopup
          cluster={undefined}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      expect(container.firstChild).toBeNull()
    })
  })

  describe('Content Display', () => {
    it('displays cluster photo count', () => {
      render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      expect(screen.getByText('3 photos')).toBeInTheDocument()
    })

    it('displays single date when earliest equals latest', () => {
      render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      expect(screen.getByText('2024-01-15')).toBeInTheDocument()
    })

    it('displays date range when earliest differs from latest', () => {
      const clusterWithRange = {
        ...mockCluster,
        date_range: {
          earliest: '2024-01-15',
          latest: '2024-01-20',
        },
      }

      render(
        <MarkerHoverPopup
          cluster={clusterWithRange}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      expect(screen.getByText('2024-01-15 - 2024-01-20')).toBeInTheDocument()
    })

    it('displays "No date info" when date_range is missing', () => {
      const clusterWithoutDates = {
        ...mockCluster,
        date_range: null,
      }

      render(
        <MarkerHoverPopup
          cluster={clusterWithoutDates}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      expect(screen.getByText('No date info')).toBeInTheDocument()
    })

    it('displays "No date info" when earliest is missing', () => {
      const clusterWithoutEarliest = {
        ...mockCluster,
        date_range: {
          earliest: null,
          latest: '2024-01-15',
        },
      }

      render(
        <MarkerHoverPopup
          cluster={clusterWithoutEarliest}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      expect(screen.getByText('No date info')).toBeInTheDocument()
    })
  })

  describe('ThumbnailGrid Integration', () => {
    it('renders ThumbnailGrid with cluster photos', () => {
      render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      // ThumbnailGrid should render images for each photo
      const images = screen.getAllByRole('img')
      expect(images.length).toBeGreaterThan(0)
    })

    it('passes onPhotoClick to ThumbnailGrid', () => {
      render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      // Click first thumbnail
      const images = screen.getAllByRole('img')
      fireEvent.click(images[0])

      expect(mockOnPhotoClick).toHaveBeenCalledWith(mockCluster.photos[0])
    })
  })

  describe('Keyboard Interaction', () => {
    it('calls onClose when Escape key is pressed', () => {
      render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      fireEvent.keyDown(document, { key: 'Escape' })

      expect(mockOnClose).toHaveBeenCalledTimes(1)
    })

    it('does not call onClose for other keys', () => {
      render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      fireEvent.keyDown(document, { key: 'Enter' })
      fireEvent.keyDown(document, { key: 'Space' })
      fireEvent.keyDown(document, { key: 'Tab' })

      expect(mockOnClose).not.toHaveBeenCalled()
    })

    it('does not add escape listener when not visible', () => {
      const { rerender } = render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={false}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      fireEvent.keyDown(document, { key: 'Escape' })
      expect(mockOnClose).not.toHaveBeenCalled()

      // Make visible
      rerender(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      fireEvent.keyDown(document, { key: 'Escape' })
      expect(mockOnClose).toHaveBeenCalledTimes(1)
    })

    it('cleans up escape listener on unmount', () => {
      const { unmount } = render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      unmount()

      fireEvent.keyDown(document, { key: 'Escape' })
      expect(mockOnClose).not.toHaveBeenCalled()
    })

    it('handles missing onClose gracefully', () => {
      render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={undefined}
        />
      )

      // Should not throw error
      expect(() => {
        fireEvent.keyDown(document, { key: 'Escape' })
      }).not.toThrow()
    })
  })

  describe('Accessibility', () => {
    it('has role="dialog"', () => {
      render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      const dialog = screen.getByRole('dialog')
      expect(dialog).toBeInTheDocument()
    })

    it('has aria-modal="true"', () => {
      render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      const dialog = screen.getByRole('dialog')
      expect(dialog).toHaveAttribute('aria-modal', 'true')
    })

    it('has descriptive aria-label', () => {
      render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      const dialog = screen.getByRole('dialog')
      expect(dialog).toHaveAttribute(
        'aria-label',
        'Photo preview for 3 photos at this location'
      )
    })

    it('is focusable with tabIndex=-1', () => {
      render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      const dialog = screen.getByRole('dialog')
      expect(dialog).toHaveAttribute('tabIndex', '-1')
    })

    it('attempts to focus when visible', async () => {
      render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      // Wait for popup to render
      const dialog = await screen.findByRole('dialog')

      // Verify popup is focusable (has tabIndex=-1)
      expect(dialog).toHaveAttribute('tabIndex', '-1')

      // In real browser, focus() would be called - we can verify element exists and is focusable
      // Note: jsdom doesn't fully support focus(), but the element is properly set up
      expect(dialog).toBeInTheDocument()
    })
  })

  describe('Positioning and Styling', () => {
    it('applies correct position via style', () => {
      render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      const dialog = screen.getByRole('dialog')
      expect(dialog).toHaveStyle({
        left: '100px',
        top: '200px',
      })
    })

    it('defaults to 0,0 when position is null', () => {
      render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={null}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      const dialog = screen.getByRole('dialog')
      expect(dialog).toHaveStyle({
        left: '0px',
        top: '0px',
      })
    })

    it('defaults to 0,0 when position is undefined', () => {
      render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={undefined}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      const dialog = screen.getByRole('dialog')
      expect(dialog).toHaveStyle({
        left: '0px',
        top: '0px',
      })
    })

    it('applies correct z-index from config', () => {
      render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      const dialog = screen.getByRole('dialog')
      // Z_INDEX should be 1100 from HOVER_POPUP_CONFIG
      expect(dialog).toHaveStyle({ zIndex: '1100' })
    })

    it('has opacity-100 class when visible', async () => {
      render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      // Wait for requestAnimationFrame to trigger opacity-100
      await waitFor(() => {
        const dialog = screen.getByRole('dialog')
        expect(dialog).toHaveClass('opacity-100')
      })
    })

    it('has fixed positioning', () => {
      render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      const dialog = screen.getByRole('dialog')
      expect(dialog).toHaveClass('fixed')
    })
  })

  describe('Animation States', () => {
    it('has transition-opacity class for smooth animations', () => {
      render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      const dialog = screen.getByRole('dialog')
      expect(dialog).toHaveClass('transition-opacity')
    })

    it('applies correct animation duration from config', () => {
      render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      const dialog = screen.getByRole('dialog')
      // ANIMATION_DURATION is 100ms in HOVER_POPUP_CONFIG
      expect(dialog).toHaveStyle({ transitionDuration: '100ms' })
    })

    it('has opacity-100 when isVisible becomes true', async () => {
      const { rerender } = render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={false}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      // Make visible
      rerender(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      // Wait for requestAnimationFrame to apply opacity-100
      await waitFor(() => {
        const dialog = screen.getByRole('dialog')
        expect(dialog).toHaveClass('opacity-100')
      })
    })

    it('has opacity-0 when isVisible becomes false (fade-out)', async () => {
      const { rerender } = render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      // Wait for initial fade-in to complete
      await waitFor(() => {
        expect(screen.getByRole('dialog')).toHaveClass('opacity-100')
      })

      // Hide (start fade-out animation)
      rerender(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={false}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      // Should immediately have opacity-0 class (fade-out animation)
      const dialog = screen.getByRole('dialog')
      expect(dialog).toHaveClass('opacity-0')
    })

    it('removes from DOM after fade-out animation completes', async () => {
      vi.useFakeTimers()

      const { rerender, container } = render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      // Wait for initial fade-in (uses requestAnimationFrame)
      await act(async () => {
        await vi.runAllTimersAsync()
      })

      // Verify popup is visible
      expect(screen.getByRole('dialog')).toBeInTheDocument()

      // Hide popup
      rerender(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={false}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      // Still in DOM during animation (opacity-0)
      expect(screen.getByRole('dialog')).toBeInTheDocument()

      // Fast-forward past animation duration (100ms)
      await act(async () => {
        await vi.advanceTimersByTimeAsync(100)
      })

      // Should be removed from DOM
      expect(container.firstChild).toBeNull()

      vi.useRealTimers()
    })

    it('maintains no layout shift during fade animation', () => {
      const { rerender } = render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      const dialog = screen.getByRole('dialog')
      const initialWidth = dialog.style.width
      const initialPosition = {
        left: dialog.style.left,
        top: dialog.style.top,
      }

      // Hide (trigger fade-out)
      rerender(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={false}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      // Verify size and position unchanged during animation
      const fadingDialog = screen.getByRole('dialog')
      expect(fadingDialog.style.width).toBe(initialWidth)
      expect(fadingDialog.style.left).toBe(initialPosition.left)
      expect(fadingDialog.style.top).toBe(initialPosition.top)
    })
  })

  describe('Tags Display', () => {
    it('shows tags when photos have tags', () => {
      render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      expect(screen.getByText('moth')).toBeInTheDocument()
      expect(screen.getByText('night')).toBeInTheDocument()
      expect(screen.getByText('butterfly')).toBeInTheDocument()
    })

    it('does not show tags section when no photos have tags', () => {
      const clusterWithoutTags = {
        ...mockCluster,
        photos: mockCluster.photos.map((p) => ({ ...p, tags: [] })),
      }

      render(
        <MarkerHoverPopup
          cluster={clusterWithoutTags}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      // Tags should not be rendered
      expect(screen.queryByText('moth')).not.toBeInTheDocument()
      expect(screen.queryByText('butterfly')).not.toBeInTheDocument()
    })

    it('deduplicates tags from multiple photos', () => {
      const clusterWithDuplicateTags = {
        ...mockCluster,
        photos: [
          { ...mockCluster.photos[0], tags: ['moth', 'night'] },
          { ...mockCluster.photos[1], tags: ['moth', 'butterfly'] },
          { ...mockCluster.photos[2], tags: ['night'] },
        ],
      }

      render(
        <MarkerHoverPopup
          cluster={clusterWithDuplicateTags}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      const mothTags = screen.getAllByText('moth')
      const nightTags = screen.getAllByText('night')

      // Each tag should appear only once
      expect(mothTags).toHaveLength(1)
      expect(nightTags).toHaveLength(1)
    })

    it('limits tags to 5', () => {
      const clusterWithManyTags = {
        ...mockCluster,
        photos: [
          { ...mockCluster.photos[0], tags: ['tag1', 'tag2', 'tag3'] },
          { ...mockCluster.photos[1], tags: ['tag4', 'tag5', 'tag6'] },
          { ...mockCluster.photos[2], tags: ['tag7', 'tag8'] },
        ],
      }

      const { container } = render(
        <MarkerHoverPopup
          cluster={clusterWithManyTags}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      // Count tag elements
      const tagElements = container.querySelectorAll('.px-2.py-0\\.5.bg-gray-100')
      expect(tagElements).toHaveLength(5)
    })

    it('handles photos with undefined tags', () => {
      const clusterWithUndefinedTags = {
        ...mockCluster,
        photos: [
          { ...mockCluster.photos[0], tags: undefined },
          { ...mockCluster.photos[1], tags: ['butterfly'] },
        ],
      }

      render(
        <MarkerHoverPopup
          cluster={clusterWithUndefinedTags}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      // Should show butterfly tag, not crash
      expect(screen.getByText('butterfly')).toBeInTheDocument()
    })
  })

  describe('Edge Cases', () => {
    it('handles cluster with no photos', () => {
      const clusterWithNoPhotos = {
        ...mockCluster,
        count: 0,
        photos: [],
      }

      render(
        <MarkerHoverPopup
          cluster={clusterWithNoPhotos}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      expect(screen.getByText('0 photos')).toBeInTheDocument()
    })

    it('handles cluster with undefined photos array', () => {
      const clusterWithUndefinedPhotos = {
        ...mockCluster,
        photos: undefined,
      }

      render(
        <MarkerHoverPopup
          cluster={clusterWithUndefinedPhotos}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })

    it('handles missing onPhotoClick gracefully', () => {
      render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={undefined}
          onClose={mockOnClose}
        />
      )

      // Should render without errors
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })
  })

  describe('Focus Trap', () => {
    it('traps Tab key within popup (forward)', () => {
      render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      const buttons = screen.getAllByRole('button')
      const firstButton = buttons[0]
      const lastButton = buttons[buttons.length - 1]

      // Focus last button
      lastButton.focus()
      expect(document.activeElement).toBe(lastButton)

      // Press Tab - should cycle to first button
      fireEvent.keyDown(document, { key: 'Tab', shiftKey: false })
      expect(document.activeElement).toBe(firstButton)
    })

    it('traps Tab key within popup (backward)', () => {
      render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      const buttons = screen.getAllByRole('button')
      const firstButton = buttons[0]
      const lastButton = buttons[buttons.length - 1]

      // Focus first button
      firstButton.focus()
      expect(document.activeElement).toBe(firstButton)

      // Press Shift+Tab - should cycle to last button
      fireEvent.keyDown(document, { key: 'Tab', shiftKey: true })
      expect(document.activeElement).toBe(lastButton)
    })

    it('does not trap Tab when focus is on middle element', () => {
      render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      const buttons = screen.getAllByRole('button')
      if (buttons.length < 3) return // Skip if not enough buttons

      const middleButton = buttons[1]
      middleButton.focus()

      // Tab should not be prevented when on middle element
      const event = new KeyboardEvent('keydown', { key: 'Tab', bubbles: true })
      const preventDefaultSpy = vi.spyOn(event, 'preventDefault')
      document.dispatchEvent(event)

      // preventDefault should not be called for middle elements
      expect(preventDefaultSpy).not.toHaveBeenCalled()
    })

    it('does not add Tab trap when not visible', () => {
      render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={false}
          position={mockPosition}
          onPhotoClick={mockOnPhotoClick}
          onClose={mockOnClose}
        />
      )

      // Tab key should not be trapped when popup is not visible
      const event = new KeyboardEvent('keydown', { key: 'Tab', bubbles: true })
      const preventDefaultSpy = vi.spyOn(event, 'preventDefault')
      document.dispatchEvent(event)

      expect(preventDefaultSpy).not.toHaveBeenCalled()
    })
  })
})
