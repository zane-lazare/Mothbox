import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import PhotoListItem from '../PhotoListItem'

/**
 * Test suite for PhotoListItem component
 *
 * Tests the list view photo card component that displays photos
 * in a horizontal layout with thumbnail and metadata.
 */
describe('PhotoListItem', () => {
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
      const { container } = render(<PhotoListItem photo={mockPhoto} onClick={() => {}} />)

      // Container should use flex layout
      const card = container.firstChild
      expect(card).toHaveClass('flex')
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

      const card = screen.getByRole('button')
      await user.click(card)

      expect(onClick).toHaveBeenCalledWith(mockPhoto)
      expect(onClick).toHaveBeenCalledTimes(1)
    })

    it('keyboard interaction with Enter triggers onClick', async () => {
      const user = userEvent.setup()
      const onClick = vi.fn()

      render(<PhotoListItem photo={mockPhoto} onClick={onClick} />)

      const card = screen.getByRole('button')
      card.focus()
      await user.keyboard('{Enter}')

      expect(onClick).toHaveBeenCalledWith(mockPhoto)
    })
  })

  describe('Accessibility', () => {
    it('has proper semantic HTML', () => {
      render(<PhotoListItem photo={mockPhoto} onClick={() => {}} />)

      // Should be a button for click interaction
      const button = screen.getByRole('button')
      expect(button).toBeInTheDocument()

      // Image should have alt text
      const img = screen.getByRole('img')
      expect(img).toHaveAttribute('alt', expect.any(String))
    })

    it('has accessible label describing the photo', () => {
      render(<PhotoListItem photo={mockPhoto} onClick={() => {}} />)

      const button = screen.getByRole('button')
      expect(button).toHaveAttribute('aria-label', expect.stringContaining('test-photo.jpg'))
    })

    it('provides hover state for better UX', () => {
      render(<PhotoListItem photo={mockPhoto} onClick={() => {}} />)

      const button = screen.getByRole('button')

      // Should have hover classes
      expect(button).toHaveClass('hover:shadow-md')
    })
  })
})
