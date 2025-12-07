import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import PhotoListItem from '../PhotoListItem'

// Mock useProgressiveImage hook to provide loaded image state
vi.mock('../../hooks/useProgressiveImage', () => ({
  default: vi.fn(() => ({
    src: 'https://example.com/api/photos/thumbnail/20250106/test-photo.jpg',
    isLoading: false,
    error: null,
    stage: 'loaded'
  }))
}))

// Mock QuickTagButton to avoid useSidecarMetadata hook dependency
vi.mock('../gallery/QuickTagButton', () => ({
  default: ({ filename, onDropdownOpenChange, className }) => (
    <button
      data-testid="quick-tag-button"
      data-filename={filename}
      className={className}
      onClick={(e) => {
        e.stopPropagation()
        onDropdownOpenChange?.(true)
      }}
    >
      Tag
    </button>
  )
}))

/**
 * Test suite for PhotoListItem component
 *
 * Tests the list view photo card component that displays photos
 * in a horizontal layout with thumbnail and metadata.
 */
describe('PhotoListItem', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })
  const mockPhoto = {
    path: '20250106/test-photo.jpg',
    filename: 'test-photo.jpg',
    date: '2025-01-06T15:30:00Z',
  }

  describe('Rendering', () => {
    it('renders photo with thumbnail image', () => {
      render(<PhotoListItem photo={mockPhoto} onClick={() => {}} />)

      const img = screen.getByRole('img', { name: /test-photo.jpg/i })
      expect(img).toBeInTheDocument()
      expect(img).toHaveAttribute('src', expect.stringContaining('test-photo.jpg'))
    })

    it('displays filename', () => {
      render(<PhotoListItem photo={mockPhoto} onClick={() => {}} />)

      expect(screen.getByText('test-photo.jpg')).toBeInTheDocument()
    })

    it('displays formatted date', () => {
      render(<PhotoListItem photo={mockPhoto} onClick={() => {}} />)

      // Date should be formatted (not raw ISO string)
      // Format is: "Jan 7, 2025, 04:30 AM" (or similar depending on locale)
      const dateText = screen.getByText(/Jan.*\d+.*2025/)
      expect(dateText).toBeInTheDocument()
    })

    it('displays file size when provided', () => {
      const photoWithSize = { ...mockPhoto, size: 2097152 } // 2 MB (2 * 1024 * 1024)

      render(<PhotoListItem photo={photoWithSize} onClick={() => {}} />)

      // Size should be formatted (e.g., "2.0 MB")
      expect(screen.getByText(/2\.0\s*MB/i)).toBeInTheDocument()
    })
  })

  describe('Layout', () => {
    it('uses horizontal layout (image + metadata side-by-side)', () => {
      render(<PhotoListItem photo={mockPhoto} onClick={() => {}} />)

      // Main button should use flex layout for horizontal arrangement
      const button = screen.getByRole('button', { name: /View photo/i })
      expect(button).toHaveClass('flex')
    })

    it('image is appropriately sized for list view', () => {
      render(<PhotoListItem photo={mockPhoto} onClick={() => {}} />)

      const img = screen.getByRole('img')
      // Should have specific width/height classes (not full width like grid)
      expect(img).toHaveClass('w-48')
    })

    it('metadata displays in column layout', () => {
      render(<PhotoListItem photo={mockPhoto} onClick={() => {}} />)

      const filename = screen.getByText('test-photo.jpg')
      const metadata = filename.closest('div')

      // Metadata container should be flex-col
      expect(metadata).toHaveClass('flex-col')
    })
  })

  describe('Interaction', () => {
    it('clicking photo triggers onClick callback', async () => {
      const user = userEvent.setup()
      const onClick = vi.fn()

      render(<PhotoListItem photo={mockPhoto} onClick={onClick} />)

      // Use the main photo button (with aria-label), not the QuickTagButton
      const card = screen.getByRole('button', { name: /View photo/i })
      await user.click(card)

      expect(onClick).toHaveBeenCalledWith(mockPhoto)
      expect(onClick).toHaveBeenCalledTimes(1)
    })

    it('keyboard interaction with Enter triggers onClick', async () => {
      const user = userEvent.setup()
      const onClick = vi.fn()

      render(<PhotoListItem photo={mockPhoto} onClick={onClick} />)

      // Use the main photo button (with aria-label), not the QuickTagButton
      const card = screen.getByRole('button', { name: /View photo/i })
      card.focus()
      await user.keyboard('{Enter}')

      expect(onClick).toHaveBeenCalledWith(mockPhoto)
    })
  })

  describe('Accessibility', () => {
    it('has proper semantic HTML', () => {
      render(<PhotoListItem photo={mockPhoto} onClick={() => {}} />)

      // Should have a main button for click interaction
      const button = screen.getByRole('button', { name: /View photo/i })
      expect(button).toBeInTheDocument()

      // Image should have alt text
      const img = screen.getByRole('img')
      expect(img).toHaveAttribute('alt', expect.any(String))
    })

    it('has accessible label describing the photo', () => {
      render(<PhotoListItem photo={mockPhoto} onClick={() => {}} />)

      const button = screen.getByRole('button', { name: /View photo/i })
      expect(button).toHaveAttribute('aria-label', expect.stringContaining('test-photo.jpg'))
    })

    it('provides hover state for better UX', () => {
      render(<PhotoListItem photo={mockPhoto} onClick={() => {}} />)

      const button = screen.getByRole('button', { name: /View photo/i })

      // Should have hover classes
      expect(button).toHaveClass('hover:shadow-md')
    })
  })
})
