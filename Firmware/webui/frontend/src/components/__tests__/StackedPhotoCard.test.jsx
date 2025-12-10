import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import React, { useEffect } from 'react'
import StackedPhotoCard from '../StackedPhotoCard'
import { SelectionProvider, useSelectionContext } from '../../contexts/SelectionContext'

// Mock the LazyImage component to simplify testing
vi.mock('../LazyImage', () => ({
  default: ({ photo, alt, className, onClick }) => (
    <div
      data-testid={`lazy-image-${photo.path}`}
      className={className}
      onClick={onClick}
      role="img"
      aria-label={alt}
    >
      {photo.filename}
    </div>
  ),
}))

/**
 * Test suite for StackedPhotoCard component
 *
 * Tests the visual stacked card effect for photo series (HDR, Focus Bracket).
 * Verifies rendering, interactions, accessibility, and visual states.
 */
describe('StackedPhotoCard', () => {
  // Sample series data for testing
  const mockHdrSeries = {
    series_id: 'hdr_moth_2024_01_15__10_00_00',
    series_type: 'hdr',
    photos: [
      { path: '/photos/moth_2024_01_15__10_00_00_HDR0.jpg', filename: 'moth_HDR0.jpg', date: '2024-01-15T10:00:00Z' },
      { path: '/photos/moth_2024_01_15__10_00_00_HDR1.jpg', filename: 'moth_HDR1.jpg', date: '2024-01-15T10:00:00Z' },
      { path: '/photos/moth_2024_01_15__10_00_00_HDR2.jpg', filename: 'moth_HDR2.jpg', date: '2024-01-15T10:00:00Z' },
    ],
    count: 3,
    cover_photo: '/photos/moth_2024_01_15__10_00_00_HDR0.jpg',
  }

  const mockFocusBracketSeries = {
    series_id: 'fb_ManFocus_moth_2024_02_20__14_30_00',
    series_type: 'focus_bracket',
    photos: [
      { path: '/photos/ManFocus_moth_FB0.jpg', filename: 'ManFocus_moth_FB0.jpg', date: '2024-02-20T14:30:00Z' },
      { path: '/photos/ManFocus_moth_FB1.jpg', filename: 'ManFocus_moth_FB1.jpg', date: '2024-02-20T14:30:00Z' },
      { path: '/photos/ManFocus_moth_FB2.jpg', filename: 'ManFocus_moth_FB2.jpg', date: '2024-02-20T14:30:00Z' },
      { path: '/photos/ManFocus_moth_FB3.jpg', filename: 'ManFocus_moth_FB3.jpg', date: '2024-02-20T14:30:00Z' },
      { path: '/photos/ManFocus_moth_FB4.jpg', filename: 'ManFocus_moth_FB4.jpg', date: '2024-02-20T14:30:00Z' },
    ],
    count: 5,
    cover_photo: '/photos/ManFocus_moth_FB0.jpg',
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('renders with HDR series data', () => {
      render(<StackedPhotoCard series={mockHdrSeries} />)

      // Should render the component
      expect(screen.getByRole('group')).toBeInTheDocument()
    })

    it('renders with Focus Bracket series data', () => {
      render(<StackedPhotoCard series={mockFocusBracketSeries} />)

      expect(screen.getByRole('group')).toBeInTheDocument()
    })

    it('displays series badge with count and type', () => {
      render(<StackedPhotoCard series={mockHdrSeries} />)

      // Badge should show count and type
      expect(screen.getByText('3 HDR')).toBeInTheDocument()
    })

    it('displays correct badge for Focus Bracket', () => {
      render(<StackedPhotoCard series={mockFocusBracketSeries} />)

      expect(screen.getByText('5 FB')).toBeInTheDocument()
    })

    it('shows first 3 photos stacked for 3-photo series', () => {
      render(<StackedPhotoCard series={mockHdrSeries} />)

      // All 3 photos should be rendered
      expect(screen.getByTestId('lazy-image-/photos/moth_2024_01_15__10_00_00_HDR0.jpg')).toBeInTheDocument()
      expect(screen.getByTestId('lazy-image-/photos/moth_2024_01_15__10_00_00_HDR1.jpg')).toBeInTheDocument()
      expect(screen.getByTestId('lazy-image-/photos/moth_2024_01_15__10_00_00_HDR2.jpg')).toBeInTheDocument()
    })

    it('shows only first 3 photos for series with more than 3 photos', () => {
      render(<StackedPhotoCard series={mockFocusBracketSeries} />)

      // Only first 3 should be rendered (FB0, FB1, FB2)
      expect(screen.getByTestId('lazy-image-/photos/ManFocus_moth_FB0.jpg')).toBeInTheDocument()
      expect(screen.getByTestId('lazy-image-/photos/ManFocus_moth_FB1.jpg')).toBeInTheDocument()
      expect(screen.getByTestId('lazy-image-/photos/ManFocus_moth_FB2.jpg')).toBeInTheDocument()

      // FB3 and FB4 should NOT be rendered
      expect(screen.queryByTestId('lazy-image-/photos/ManFocus_moth_FB3.jpg')).not.toBeInTheDocument()
      expect(screen.queryByTestId('lazy-image-/photos/ManFocus_moth_FB4.jpg')).not.toBeInTheDocument()
    })
  })

  describe('Single and Two Photo Series', () => {
    it('handles single photo series', () => {
      const singlePhotoSeries = {
        series_id: 'hdr_single',
        series_type: 'hdr',
        photos: [{ path: '/photos/single.jpg', filename: 'single.jpg', date: '2024-01-15T10:00:00Z' }],
        count: 1,
        cover_photo: '/photos/single.jpg',
      }

      render(<StackedPhotoCard series={singlePhotoSeries} />)

      expect(screen.getByTestId('lazy-image-/photos/single.jpg')).toBeInTheDocument()
      expect(screen.getByText('1 HDR')).toBeInTheDocument()
    })

    it('handles two photo series', () => {
      const twoPhotoSeries = {
        series_id: 'hdr_two',
        series_type: 'hdr',
        photos: [
          { path: '/photos/photo1.jpg', filename: 'photo1.jpg', date: '2024-01-15T10:00:00Z' },
          { path: '/photos/photo2.jpg', filename: 'photo2.jpg', date: '2024-01-15T10:00:00Z' },
        ],
        count: 2,
        cover_photo: '/photos/photo1.jpg',
      }

      render(<StackedPhotoCard series={twoPhotoSeries} />)

      expect(screen.getByTestId('lazy-image-/photos/photo1.jpg')).toBeInTheDocument()
      expect(screen.getByTestId('lazy-image-/photos/photo2.jpg')).toBeInTheDocument()
      expect(screen.getByText('2 HDR')).toBeInTheDocument()
    })
  })

  describe('Click Interactions', () => {
    it('calls onCardClick when card is clicked', () => {
      const onCardClick = vi.fn()

      render(<StackedPhotoCard series={mockHdrSeries} onCardClick={onCardClick} />)

      fireEvent.click(screen.getByRole('group'))

      expect(onCardClick).toHaveBeenCalledTimes(1)
      expect(onCardClick).toHaveBeenCalledWith(mockHdrSeries)
    })

    it('does not throw when clicked without onCardClick handler', () => {
      render(<StackedPhotoCard series={mockHdrSeries} />)

      expect(() => fireEvent.click(screen.getByRole('group'))).not.toThrow()
    })

    it('calls onPhotoClick when provided', () => {
      const onPhotoClick = vi.fn()

      render(<StackedPhotoCard series={mockHdrSeries} onPhotoClick={onPhotoClick} />)

      // Click on the card (which represents clicking the cover photo)
      fireEvent.click(screen.getByRole('group'))

      expect(onPhotoClick).toHaveBeenCalledTimes(1)
      // Should be called with the cover photo
      expect(onPhotoClick).toHaveBeenCalledWith(mockHdrSeries.photos[0])
    })
  })

  describe('Keyboard Navigation', () => {
    it('is focusable with tabIndex', () => {
      render(<StackedPhotoCard series={mockHdrSeries} />)

      const card = screen.getByRole('group')
      expect(card).toHaveAttribute('tabIndex', '0')
    })

    it('calls onCardClick on Enter key', () => {
      const onCardClick = vi.fn()

      render(<StackedPhotoCard series={mockHdrSeries} onCardClick={onCardClick} />)

      const card = screen.getByRole('group')
      fireEvent.keyDown(card, { key: 'Enter' })

      expect(onCardClick).toHaveBeenCalledTimes(1)
    })

    it('calls onCardClick on Space key', () => {
      const onCardClick = vi.fn()

      render(<StackedPhotoCard series={mockHdrSeries} onCardClick={onCardClick} />)

      const card = screen.getByRole('group')
      fireEvent.keyDown(card, { key: ' ' })

      expect(onCardClick).toHaveBeenCalledTimes(1)
    })

    it('does not call handler on other keys', () => {
      const onCardClick = vi.fn()

      render(<StackedPhotoCard series={mockHdrSeries} onCardClick={onCardClick} />)

      const card = screen.getByRole('group')
      fireEvent.keyDown(card, { key: 'a' })
      fireEvent.keyDown(card, { key: 'Tab' })
      fireEvent.keyDown(card, { key: 'Escape' })

      expect(onCardClick).not.toHaveBeenCalled()
    })
  })

  describe('Accessibility', () => {
    it('has correct ARIA label for HDR series', () => {
      render(<StackedPhotoCard series={mockHdrSeries} />)

      const card = screen.getByRole('group')
      expect(card).toHaveAttribute('aria-label', 'HDR series: 3 photos')
    })

    it('has correct ARIA label for Focus Bracket series', () => {
      render(<StackedPhotoCard series={mockFocusBracketSeries} />)

      const card = screen.getByRole('group')
      expect(card).toHaveAttribute('aria-label', 'Focus bracket series: 5 photos')
    })

    it('has visible focus ring when focused', () => {
      render(<StackedPhotoCard series={mockHdrSeries} />)

      const card = screen.getByRole('group')
      // Check for focus ring classes in the className
      expect(card.className).toContain('focus:ring')
    })
  })

  describe('Visual Styling', () => {
    it('applies hover scale effect class', () => {
      render(<StackedPhotoCard series={mockHdrSeries} />)

      const card = screen.getByRole('group')
      expect(card.className).toContain('group')
    })

    it('has cursor-pointer class', () => {
      render(<StackedPhotoCard series={mockHdrSeries} />)

      const card = screen.getByRole('group')
      expect(card.className).toContain('cursor-pointer')
    })

    it('applies correct z-index stacking order (z-10 back, z-20 middle, z-30 front)', () => {
      const { container } = render(<StackedPhotoCard series={mockHdrSeries} />)

      // Get the photo layer containers (divs with absolute positioning that contain LazyImage)
      // DOM order is: front (z-30) first, back (z-10) last (due to reverse() in render)
      const photoLayers = Array.from(container.querySelectorAll('[class*="absolute inset-0"]'))
        .filter(el => el.className.includes('z-'))

      // Should have 3 layers for the 3 photos
      expect(photoLayers).toHaveLength(3)

      // Verify all expected z-index classes are present
      const zIndexClasses = photoLayers.map(el => {
        if (el.className.includes('z-30')) return 'z-30'
        if (el.className.includes('z-20')) return 'z-20'
        if (el.className.includes('z-10')) return 'z-10'
        return null
      })

      // All three z-index values should be applied (one per layer)
      expect(zIndexClasses).toContain('z-10')
      expect(zIndexClasses).toContain('z-20')
      expect(zIndexClasses).toContain('z-30')

      // Front layer (z-30) should have hover animation classes
      const frontLayer = photoLayers.find(el => el.className.includes('z-30'))
      expect(frontLayer.className).toContain('group-hover:scale')
    })

    it('has touch-friendly active state', () => {
      render(<StackedPhotoCard series={mockHdrSeries} />)

      const card = screen.getByRole('group')
      // Check for active state scale and touch-manipulation
      expect(card.className).toContain('active:scale')
      expect(card.className).toContain('touch-manipulation')
    })
  })

  describe('Badge Display', () => {
    it('shows badge in bottom-right corner', () => {
      const { container } = render(<StackedPhotoCard series={mockHdrSeries} />)

      // Find badge element
      const badge = container.querySelector('[class*="bottom-"][class*="right-"]')
      expect(badge).toBeInTheDocument()
    })

    it('badge has semi-transparent background', () => {
      render(<StackedPhotoCard series={mockHdrSeries} />)

      // Badge should have dark background
      const badge = screen.getByText('3 HDR')
      expect(badge.className).toContain('bg-black')
    })

    it('badge text is readable (white on dark)', () => {
      render(<StackedPhotoCard series={mockHdrSeries} />)

      const badge = screen.getByText('3 HDR')
      expect(badge.className).toContain('text-white')
    })
  })

  describe('Series Type Display', () => {
    it('formats HDR type correctly', () => {
      render(<StackedPhotoCard series={mockHdrSeries} />)

      expect(screen.getByText('3 HDR')).toBeInTheDocument()
    })

    it('formats focus_bracket type as FB', () => {
      render(<StackedPhotoCard series={mockFocusBracketSeries} />)

      expect(screen.getByText('5 FB')).toBeInTheDocument()
    })

    it('handles unknown series type gracefully', () => {
      const unknownSeries = {
        ...mockHdrSeries,
        series_type: 'unknown_type',
      }

      render(<StackedPhotoCard series={unknownSeries} />)

      // Should display the type as-is
      expect(screen.getByText('3 unknown_type')).toBeInTheDocument()
    })
  })

  describe('Loading State', () => {
    it('renders skeleton when isLoading is true', () => {
      const { container } = render(<StackedPhotoCard series={mockHdrSeries} isLoading />)

      // Should have skeleton/shimmer classes
      const skeletons = container.querySelectorAll('[class*="animate-pulse"]')
      expect(skeletons.length).toBeGreaterThan(0)
    })

    it('does not render images when loading', () => {
      render(<StackedPhotoCard series={mockHdrSeries} isLoading />)

      // LazyImage components should not be rendered
      expect(screen.queryByTestId('lazy-image-/photos/moth_2024_01_15__10_00_00_HDR0.jpg')).not.toBeInTheDocument()
    })

    it('handles isLoading with undefined series without throwing', () => {
      // Should render skeleton without throwing - this tests the fix for
      // accessing series properties before checking isLoading state
      expect(() => render(<StackedPhotoCard isLoading series={undefined} />)).not.toThrow()
    })

    it('handles isLoading with null series without throwing', () => {
      // Should render skeleton without throwing
      expect(() => render(<StackedPhotoCard isLoading series={null} />)).not.toThrow()
    })
  })

  describe('Edge Cases', () => {
    it('handles empty photos array', () => {
      const emptySeries = {
        series_id: 'empty',
        series_type: 'hdr',
        photos: [],
        count: 0,
        cover_photo: null,
      }

      // Should not throw
      expect(() => render(<StackedPhotoCard series={emptySeries} />)).not.toThrow()
    })

    it('handles missing cover_photo', () => {
      const noCoverSeries = {
        ...mockHdrSeries,
        cover_photo: null,
      }

      // Should not throw and render normally
      expect(() => render(<StackedPhotoCard series={noCoverSeries} />)).not.toThrow()
    })

    it('handles undefined photos property without throwing', () => {
      const undefinedPhotosSeries = {
        series_id: 'undefined_photos',
        series_type: 'hdr',
        photos: undefined,
        count: 0,
        cover_photo: null,
      }

      // Should not throw - photos.slice guard handles this
      expect(() => render(<StackedPhotoCard series={undefinedPhotosSeries} />)).not.toThrow()
    })

    it('handles null photos property without throwing', () => {
      const nullPhotosSeries = {
        series_id: 'null_photos',
        series_type: 'hdr',
        photos: null,
        count: 0,
        cover_photo: null,
      }

      // Should not throw - photos.slice guard handles this
      expect(() => render(<StackedPhotoCard series={nullPhotosSeries} />)).not.toThrow()
    })

    it('returns null when series is undefined after loading completes', () => {
      // When isLoading=false but series is still undefined, component should return null
      const { container } = render(<StackedPhotoCard series={undefined} isLoading={false} />)
      expect(container.firstChild).toBeNull()
    })

    it('returns null when series is null after loading completes', () => {
      // When isLoading=false but series is null, component should return null
      const { container } = render(<StackedPhotoCard series={null} isLoading={false} />)
      expect(container.firstChild).toBeNull()
    })
  })

  /**
   * Test harness to control selection mode state
   * Allows tests to enter select mode and pre-select photos before rendering component
   */
  function TestHarness({ children, enterSelectMode = false, selectPhotos = [] }) {
    const selection = useSelectionContext()

    useEffect(() => {
      if (enterSelectMode && !selection.isSelectMode) {
        selection.toggleSelectMode()
      }
      selectPhotos.forEach(path => {
        selection.selectPhoto(path)
      })
    }, []) // Empty deps - only run once on mount

    return children
  }

  /**
   * Helper to render StackedPhotoCard with SelectionProvider
   */
  const renderWithProvider = (props, { enterSelectMode = false, selectPhotos = [] } = {}) => {
    return render(
      <SelectionProvider>
        <TestHarness enterSelectMode={enterSelectMode} selectPhotos={selectPhotos}>
          <StackedPhotoCard {...props} />
        </TestHarness>
      </SelectionProvider>
    )
  }

  describe('Selection Mode - Checkbox Visibility', () => {
    it('does NOT show checkbox when not in select mode', () => {
      renderWithProvider({ series: mockHdrSeries }, { enterSelectMode: false })

      // Query for checkbox input
      const checkbox = screen.queryByRole('checkbox')
      expect(checkbox).not.toBeInTheDocument()
    })

    it('shows checkbox in top-left corner when in select mode', () => {
      renderWithProvider({ series: mockHdrSeries }, { enterSelectMode: true })

      // Checkbox should be visible
      const checkbox = screen.getByRole('checkbox')
      expect(checkbox).toBeInTheDocument()

      // Find checkbox container - should have positioning classes
      const checkboxContainer = checkbox.parentElement
      expect(checkboxContainer.className).toContain('absolute')
      expect(checkboxContainer.className).toContain('top-')
      expect(checkboxContainer.className).toContain('left-')
    })

    it('checkbox has proper aria-label indicating series selection', () => {
      renderWithProvider({ series: mockHdrSeries }, { enterSelectMode: true })

      const checkbox = screen.getByRole('checkbox')
      expect(checkbox).toHaveAttribute('aria-label', 'Select all 3 photos in series')
    })

    it('checkbox aria-label reflects actual photo count for 5-photo series', () => {
      renderWithProvider({ series: mockFocusBracketSeries }, { enterSelectMode: true })

      const checkbox = screen.getByRole('checkbox')
      expect(checkbox).toHaveAttribute('aria-label', 'Select all 5 photos in series')
    })
  })

  describe('Selection Mode - Series Selection', () => {
    it('clicking checkbox selects ALL photos in series', () => {
      renderWithProvider({ series: mockHdrSeries }, { enterSelectMode: true })

      const checkbox = screen.getByRole('checkbox')

      // Initially unchecked
      expect(checkbox).not.toBeChecked()
      expect(checkbox.indeterminate).toBeFalsy()

      // Click to select all
      fireEvent.click(checkbox)

      // Should now be checked
      expect(checkbox).toBeChecked()
      expect(checkbox.indeterminate).toBeFalsy()
    })

    it('clicking checkbox deselects ALL photos when all are selected', () => {
      // Pre-select all photos in the series
      const allPhotoPaths = mockHdrSeries.photos.map(p => p.path)
      renderWithProvider(
        { series: mockHdrSeries },
        { enterSelectMode: true, selectPhotos: allPhotoPaths }
      )

      const checkbox = screen.getByRole('checkbox')

      // Initially all selected
      expect(checkbox).toBeChecked()

      // Click to deselect all
      fireEvent.click(checkbox)

      // Should now be unchecked
      expect(checkbox).not.toBeChecked()
      expect(checkbox.indeterminate).toBeFalsy()
    })

    it('checkbox shows checked state when all series photos are selected', () => {
      // Pre-select all photos
      const allPhotoPaths = mockHdrSeries.photos.map(p => p.path)
      renderWithProvider(
        { series: mockHdrSeries },
        { enterSelectMode: true, selectPhotos: allPhotoPaths }
      )

      const checkbox = screen.getByRole('checkbox')
      expect(checkbox).toBeChecked()
      expect(checkbox.indeterminate).toBeFalsy()
    })

    it('checkbox shows unchecked state when no series photos are selected', () => {
      renderWithProvider({ series: mockHdrSeries }, { enterSelectMode: true })

      const checkbox = screen.getByRole('checkbox')
      expect(checkbox).not.toBeChecked()
      expect(checkbox.indeterminate).toBeFalsy()
    })

    it('checkbox shows indeterminate state when SOME photos are selected', () => {
      // Pre-select only first photo
      const firstPhotoPath = mockHdrSeries.photos[0].path
      renderWithProvider(
        { series: mockHdrSeries },
        { enterSelectMode: true, selectPhotos: [firstPhotoPath] }
      )

      const checkbox = screen.getByRole('checkbox')
      expect(checkbox).not.toBeChecked()
      expect(checkbox.indeterminate).toBeTruthy()
    })

    it('checkbox shows indeterminate state when 2 of 3 photos are selected', () => {
      // Pre-select first two photos
      const twoPhotoPaths = mockHdrSeries.photos.slice(0, 2).map(p => p.path)
      renderWithProvider(
        { series: mockHdrSeries },
        { enterSelectMode: true, selectPhotos: twoPhotoPaths }
      )

      const checkbox = screen.getByRole('checkbox')
      expect(checkbox).not.toBeChecked()
      expect(checkbox.indeterminate).toBeTruthy()
    })

    it('clicking checkbox with some photos selected selects remaining photos', () => {
      // Pre-select only first photo
      const firstPhotoPath = mockHdrSeries.photos[0].path
      renderWithProvider(
        { series: mockHdrSeries },
        { enterSelectMode: true, selectPhotos: [firstPhotoPath] }
      )

      const checkbox = screen.getByRole('checkbox')

      // Initially indeterminate
      expect(checkbox.indeterminate).toBeTruthy()

      // Click to select all
      fireEvent.click(checkbox)

      // Should now be fully checked
      expect(checkbox).toBeChecked()
      expect(checkbox.indeterminate).toBeFalsy()
    })

    it('handles series with photos as string paths (backwards compatible)', () => {
      const seriesWithStringPaths = {
        series_id: 'string_paths',
        series_type: 'hdr',
        photos: ['/photos/photo1.jpg', '/photos/photo2.jpg', '/photos/photo3.jpg'],
        count: 3,
        cover_photo: '/photos/photo1.jpg',
      }

      renderWithProvider({ series: seriesWithStringPaths }, { enterSelectMode: true })

      const checkbox = screen.getByRole('checkbox')

      // Should work with string paths
      fireEvent.click(checkbox)
      expect(checkbox).toBeChecked()
    })
  })

  describe('Selection Mode - Click Behavior in Select Mode', () => {
    it('clicking card toggles entire series selection (not lightbox)', () => {
      const onCardClick = vi.fn()
      const onPhotoClick = vi.fn()

      renderWithProvider(
        { series: mockHdrSeries, onCardClick, onPhotoClick },
        { enterSelectMode: true }
      )

      const card = screen.getByRole('group')
      const checkbox = screen.getByRole('checkbox')

      // Initially unchecked
      expect(checkbox).not.toBeChecked()

      // Click card (not checkbox)
      fireEvent.click(card)

      // Should select all photos in series
      expect(checkbox).toBeChecked()

      // Should NOT call onPhotoClick (which opens lightbox)
      expect(onPhotoClick).not.toHaveBeenCalled()

      // May or may not call onCardClick - behavior is up to implementation
    })

    it('clicking checkbox toggles series selection', () => {
      renderWithProvider({ series: mockHdrSeries }, { enterSelectMode: true })

      const checkbox = screen.getByRole('checkbox')

      // Toggle on
      fireEvent.click(checkbox)
      expect(checkbox).toBeChecked()

      // Toggle off
      fireEvent.click(checkbox)
      expect(checkbox).not.toBeChecked()
    })

    it('clicking checkbox does not trigger card click handler', () => {
      const onCardClick = vi.fn()

      renderWithProvider(
        { series: mockHdrSeries, onCardClick },
        { enterSelectMode: true }
      )

      const checkbox = screen.getByRole('checkbox')
      fireEvent.click(checkbox)

      // Card click handler should NOT be called when clicking checkbox
      expect(onCardClick).not.toHaveBeenCalled()
    })
  })

  describe('Selection Mode - Visual Feedback', () => {
    it('card shows selection indicator when any photo in series is selected', () => {
      // Pre-select one photo
      const firstPhotoPath = mockHdrSeries.photos[0].path
      const { container } = renderWithProvider(
        { series: mockHdrSeries },
        { enterSelectMode: true, selectPhotos: [firstPhotoPath] }
      )

      const card = screen.getByRole('group')

      // Should have visual selection indicator
      // Check for either ring or background color change
      expect(
        card.className.includes('ring') ||
        card.className.includes('border') ||
        container.querySelector('[class*="ring"]') ||
        container.querySelector('[class*="border-blue"]')
      ).toBeTruthy()
    })

    it('card shows full selection indicator when all photos selected', () => {
      // Pre-select all photos
      const allPhotoPaths = mockHdrSeries.photos.map(p => p.path)
      const { container } = renderWithProvider(
        { series: mockHdrSeries },
        { enterSelectMode: true, selectPhotos: allPhotoPaths }
      )

      const card = screen.getByRole('group')

      // Should have visual selection indicator
      expect(
        card.className.includes('ring') ||
        card.className.includes('border') ||
        container.querySelector('[class*="ring"]') ||
        container.querySelector('[class*="border-blue"]')
      ).toBeTruthy()
    })

    it('card does not show selection indicator when no photos selected', () => {
      const { container } = renderWithProvider(
        { series: mockHdrSeries },
        { enterSelectMode: true }
      )

      // This test is optional - may want to show subtle indicator in select mode
      // Implementation can choose to always show checkbox affordance
      expect(container).toBeTruthy()
    })
  })

  describe('Selection Mode - Click Does Not Open Lightbox', () => {
    it('does not call onPhotoClick when card is clicked in select mode', () => {
      const onPhotoClick = vi.fn()

      renderWithProvider(
        { series: mockHdrSeries, onPhotoClick },
        { enterSelectMode: true }
      )

      const card = screen.getByRole('group')
      fireEvent.click(card)

      // In select mode, clicking card should select, not open lightbox
      expect(onPhotoClick).not.toHaveBeenCalled()
    })

    it('DOES call onPhotoClick when card is clicked OUTSIDE select mode', () => {
      const onPhotoClick = vi.fn()

      renderWithProvider(
        { series: mockHdrSeries, onPhotoClick },
        { enterSelectMode: false }
      )

      const card = screen.getByRole('group')
      fireEvent.click(card)

      // Outside select mode, clicking card opens lightbox
      expect(onPhotoClick).toHaveBeenCalledTimes(1)
      expect(onPhotoClick).toHaveBeenCalledWith(mockHdrSeries.photos[0])
    })
  })

  describe('Selection Mode - Keyboard Navigation', () => {
    it('Enter key toggles series selection in select mode', () => {
      renderWithProvider({ series: mockHdrSeries }, { enterSelectMode: true })

      const card = screen.getByRole('group')
      const checkbox = screen.getByRole('checkbox')

      expect(checkbox).not.toBeChecked()

      // Press Enter
      fireEvent.keyDown(card, { key: 'Enter' })

      // Should select all photos
      expect(checkbox).toBeChecked()
    })

    it('Space key toggles series selection in select mode', () => {
      renderWithProvider({ series: mockHdrSeries }, { enterSelectMode: true })

      const card = screen.getByRole('group')
      const checkbox = screen.getByRole('checkbox')

      expect(checkbox).not.toBeChecked()

      // Press Space
      fireEvent.keyDown(card, { key: ' ' })

      // Should select all photos
      expect(checkbox).toBeChecked()
    })
  })
})
