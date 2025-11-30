/**
 * MarkerHoverPopup Integration Tests
 *
 * Tests for the complete hover popup workflow including desktop hover,
 * keyboard navigation, and edge case handling.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import MarkerHoverPopup from '../MarkerHoverPopup'
import { HOVER_POPUP_CONFIG } from '../../constants/config'

describe('MarkerHoverPopup Integration Tests', () => {
  // Mock cluster with realistic data
  const mockCluster = {
    cluster_id: 'cluster_37.7749N_122.4194W_5',
    center: { lat: 37.7749, lon: -122.4194 },
    count: 15,
    photos: Array.from({ length: 15 }, (_, i) => ({
      path: `photo_${i}.jpg`,
      filename: `photo_${i}.jpg`,
      lat: 37.7749 + i * 0.0001,
      lon: -122.4194 + i * 0.0001,
      timestamp: `2024-01-${15 + i}T10:00:00`,
      tags: i % 3 === 0 ? ['moth', 'night'] : null,
    })),
    date_range: {
      earliest: '2024-01-15',
      latest: '2024-01-29',
    },
  }

  const mockPosition = { x: 100, y: 100 }

  beforeEach(() => {
    // Mock requestAnimationFrame for synchronous testing
    vi.spyOn(window, 'requestAnimationFrame').mockImplementation((cb) => {
      cb(0)
      return 0
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Desktop hover workflow', () => {
    it('shows popup with cluster data on hover', () => {
      render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={vi.fn()}
          onClose={vi.fn()}
        />
      )

      // Verify popup is rendered
      expect(screen.getByRole('dialog')).toBeInTheDocument()

      // Verify cluster data displayed
      expect(screen.getByText('15 photos')).toBeInTheDocument()
      expect(screen.getByText(/2024-01-15.*2024-01-29/)).toBeInTheDocument()

      // Verify thumbnails (max 9 shown from config)
      const buttons = screen.getAllByRole('button')
      expect(buttons.length).toBe(HOVER_POPUP_CONFIG.MAX_PHOTOS)

      // Verify "+N more" indicator
      expect(screen.getByText('+6 more photos')).toBeInTheDocument()
    })

    it('triggers onPhotoClick when thumbnail clicked', () => {
      const onPhotoClick = vi.fn()

      render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={onPhotoClick}
          onClose={vi.fn()}
        />
      )

      // Click first thumbnail
      const buttons = screen.getAllByRole('button')
      fireEvent.click(buttons[0])

      expect(onPhotoClick).toHaveBeenCalledTimes(1)
      expect(onPhotoClick).toHaveBeenCalledWith(mockCluster.photos[0])
    })

    it('closes popup on Escape key', () => {
      const onClose = vi.fn()

      render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={vi.fn()}
          onClose={onClose}
        />
      )

      // Press Escape
      fireEvent.keyDown(document, { key: 'Escape' })

      expect(onClose).toHaveBeenCalledTimes(1)
    })
  })

  describe('Keyboard navigation workflow', () => {
    it('navigates thumbnails with arrow keys', () => {
      render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={vi.fn()}
          onClose={vi.fn()}
        />
      )

      const buttons = screen.getAllByRole('button')

      // Focus first button
      buttons[0].focus()
      expect(document.activeElement).toBe(buttons[0])

      // Arrow right
      fireEvent.keyDown(buttons[0], { key: 'ArrowRight' })
      expect(document.activeElement).toBe(buttons[1])

      // Arrow down (move by 3 in grid)
      fireEvent.keyDown(buttons[1], { key: 'ArrowDown' })
      expect(document.activeElement).toBe(buttons[4])
    })

    it('activates thumbnail with Enter key', () => {
      const onPhotoClick = vi.fn()

      render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={onPhotoClick}
          onClose={vi.fn()}
        />
      )

      const buttons = screen.getAllByRole('button')
      buttons[0].focus()

      fireEvent.keyDown(buttons[0], { key: 'Enter' })

      expect(onPhotoClick).toHaveBeenCalledTimes(1)
      expect(onPhotoClick).toHaveBeenCalledWith(mockCluster.photos[0])
    })

    it('activates thumbnail with Space key', () => {
      const onPhotoClick = vi.fn()

      render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={onPhotoClick}
          onClose={vi.fn()}
        />
      )

      const buttons = screen.getAllByRole('button')
      buttons[2].focus()

      fireEvent.keyDown(buttons[2], { key: ' ' })

      expect(onPhotoClick).toHaveBeenCalledTimes(1)
      expect(onPhotoClick).toHaveBeenCalledWith(mockCluster.photos[2])
    })

    it('navigates to first/last with Home/End keys', () => {
      render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={vi.fn()}
          onClose={vi.fn()}
        />
      )

      const buttons = screen.getAllByRole('button')

      // Focus middle button
      buttons[4].focus()

      // Home key -> first button
      fireEvent.keyDown(buttons[4], { key: 'Home' })
      expect(document.activeElement).toBe(buttons[0])

      // End key -> last button
      fireEvent.keyDown(buttons[0], { key: 'End' })
      expect(document.activeElement).toBe(buttons[8])
    })
  })

  describe('Edge cases', () => {
    it('handles cluster with tags correctly', () => {
      render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={vi.fn()}
          onClose={vi.fn()}
        />
      )

      // Check that tags are displayed (photos at indices 0, 3, 6, 9, 12 have tags)
      expect(screen.getByText('moth')).toBeInTheDocument()
      expect(screen.getByText('night')).toBeInTheDocument()
    })

    it('handles empty cluster gracefully', () => {
      const emptyCluster = {
        ...mockCluster,
        count: 0,
        photos: [],
      }

      render(
        <MarkerHoverPopup
          cluster={emptyCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={vi.fn()}
          onClose={vi.fn()}
        />
      )

      expect(screen.getByText('0 photos')).toBeInTheDocument()
      expect(screen.getByText('No photos available')).toBeInTheDocument()
    })

    it('handles very large cluster with "+N more" indicator', () => {
      const largeCluster = {
        ...mockCluster,
        count: 150,
        photos: Array.from({ length: 150 }, (_, i) => ({
          path: `photo_${i}.jpg`,
          filename: `photo_${i}.jpg`,
          lat: 37.7749,
          lon: -122.4194,
          timestamp: '2024-01-15T10:00:00',
        })),
      }

      render(
        <MarkerHoverPopup
          cluster={largeCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={vi.fn()}
          onClose={vi.fn()}
        />
      )

      // Should only show max photos from config
      const buttons = screen.getAllByRole('button')
      expect(buttons.length).toBe(HOVER_POPUP_CONFIG.MAX_PHOTOS)

      // Should show correct remaining count
      expect(screen.getByText('+141 more photos')).toBeInTheDocument()
    })

    it('handles cluster with no date range', () => {
      const clusterNoDate = {
        ...mockCluster,
        date_range: null,
      }

      render(
        <MarkerHoverPopup
          cluster={clusterNoDate}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={vi.fn()}
          onClose={vi.fn()}
        />
      )

      expect(screen.getByText('No date info')).toBeInTheDocument()
    })

    it('handles cluster with same date range (single date)', () => {
      const singleDateCluster = {
        ...mockCluster,
        date_range: {
          earliest: '2024-01-15',
          latest: '2024-01-15',
        },
      }

      render(
        <MarkerHoverPopup
          cluster={singleDateCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={vi.fn()}
          onClose={vi.fn()}
        />
      )

      // Should show single date, not range
      expect(screen.getByText('2024-01-15')).toBeInTheDocument()
    })

    it('handles missing optional callbacks gracefully', () => {
      expect(() => {
        render(
          <MarkerHoverPopup
            cluster={mockCluster}
            isVisible={true}
            position={mockPosition}
            onPhotoClick={undefined}
            onClose={undefined}
          />
        )
      }).not.toThrow()

      // Try clicking thumbnail without callback
      const buttons = screen.getAllByRole('button')
      expect(() => {
        fireEvent.click(buttons[0])
      }).not.toThrow()

      // Try pressing Escape without callback
      expect(() => {
        fireEvent.keyDown(document, { key: 'Escape' })
      }).not.toThrow()
    })
  })

  describe('Complete user workflows', () => {
    it('complete workflow: show popup -> navigate thumbnails -> click photo', () => {
      const onPhotoClick = vi.fn()
      const onClose = vi.fn()

      render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={onPhotoClick}
          onClose={onClose}
        />
      )

      // Verify popup is visible
      expect(screen.getByRole('dialog')).toBeInTheDocument()

      // Navigate through thumbnails with keyboard
      const buttons = screen.getAllByRole('button')
      buttons[0].focus()

      fireEvent.keyDown(buttons[0], { key: 'ArrowRight' })
      expect(document.activeElement).toBe(buttons[1])

      fireEvent.keyDown(buttons[1], { key: 'ArrowRight' })
      expect(document.activeElement).toBe(buttons[2])

      // Click thumbnail with Enter
      fireEvent.keyDown(buttons[2], { key: 'Enter' })
      expect(onPhotoClick).toHaveBeenCalledWith(mockCluster.photos[2])

      // Close with Escape
      fireEvent.keyDown(document, { key: 'Escape' })
      expect(onClose).toHaveBeenCalledTimes(1)
    })

    it('complete workflow: show popup -> click thumbnail -> close', () => {
      const onPhotoClick = vi.fn()
      const onClose = vi.fn()

      render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={onPhotoClick}
          onClose={onClose}
        />
      )

      // Click thumbnail directly
      const buttons = screen.getAllByRole('button')
      fireEvent.click(buttons[5])

      expect(onPhotoClick).toHaveBeenCalledWith(mockCluster.photos[5])

      // Press Escape to close
      fireEvent.keyDown(document, { key: 'Escape' })
      expect(onClose).toHaveBeenCalledTimes(1)
    })

    it('accessibility workflow: popup has proper ARIA attributes', () => {
      render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={vi.fn()}
          onClose={vi.fn()}
        />
      )

      const dialog = screen.getByRole('dialog')

      expect(dialog).toHaveAttribute('tabIndex', '-1')
      expect(dialog).toHaveAttribute('role', 'dialog')
      expect(dialog).toHaveAttribute('aria-modal', 'true')
      expect(dialog).toHaveAttribute(
        'aria-label',
        'Photo preview for 15 photos at this location'
      )
    })
  })

  describe('Styling and configuration', () => {
    it('applies correct z-index from config', () => {
      render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={vi.fn()}
          onClose={vi.fn()}
        />
      )

      const dialog = screen.getByRole('dialog')
      expect(dialog).toHaveStyle({ zIndex: '1100' })
    })

    it('applies correct popup width from config', () => {
      render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={mockPosition}
          onPhotoClick={vi.fn()}
          onClose={vi.fn()}
        />
      )

      const dialog = screen.getByRole('dialog')
      expect(dialog).toHaveStyle({ width: `${HOVER_POPUP_CONFIG.POPUP_WIDTH}px` })
    })

    it('applies position from props', () => {
      const customPosition = { x: 250, y: 350 }

      render(
        <MarkerHoverPopup
          cluster={mockCluster}
          isVisible={true}
          position={customPosition}
          onPhotoClick={vi.fn()}
          onClose={vi.fn()}
        />
      )

      const dialog = screen.getByRole('dialog')
      expect(dialog).toHaveStyle({ left: '250px', top: '350px' })
    })
  })
})
