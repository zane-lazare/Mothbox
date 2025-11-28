import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import StackedPhotoCard from '../StackedPhotoCard'

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

    it('front layer has z-30 for proper stacking', () => {
      const { container } = render(<StackedPhotoCard series={mockHdrSeries} />)

      // Check that z-index classes are applied
      const layers = container.querySelectorAll('[class*="z-"]')
      expect(layers.length).toBeGreaterThan(0)
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
      const { container } = render(<StackedPhotoCard series={mockHdrSeries} />)

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
  })
})
